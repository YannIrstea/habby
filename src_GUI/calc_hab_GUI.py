"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V /
|  _  ||  _  || ___ \ ___ \ \ /
| | | || | | || |_/ / |_/ / | |
\_| |_/\_| |_/\____/\____/  \_/

Copyright (c) IRSTEA-EDF-AFB 2017-2018

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
from io import StringIO
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QStringListModel
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QLineEdit, \
    QComboBox, QAbstractItemView, \
    QSizePolicy, QScrollArea, QFrame, QCompleter, QTextEdit
from PyQt5.QtGui import QPixmap
from multiprocessing import Process, Queue, Value
import os
import sys
import numpy as np

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import bio_info_mod
from src_GUI import estimhab_GUI
from src import calcul_hab_mod
from src import hdf5_mod
from src import plot_mod
from src_GUI import preferences_GUI
from src_GUI.data_explorer_GUI import MyProcessList


class BioInfo(estimhab_GUI.StatModUseful):
    """
    This class contains the tab with the biological information (the curves of preference). It inherites from
    StatModUseful. StatModuseful is a QWidget, with some practical signal (send_log and show_fig) and some functions
    to find path_im and path_bio (the path where to save image) and to manage lists.
    """
    get_list_merge = pyqtSignal()
    """
     A Pyqtsignal which indicates to chronice_GUI.py that the merge list should be changed. In Main_Windows.py,
     the new list of merge file is found and send to the ChonicleGui class.
    """

    def __init__(self, path_prj, name_prj, lang='French'):
        super().__init__()
        self.tab_name = "calc hab"
        self.lang = lang
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.imfish = ''
        # find the path bio
        try:
            try:
                docxml = ET.parse(os.path.join(self.path_prj, self.name_prj + '.xml'))
                root = docxml.getroot()
            except IOError:
                # self.send_log.emit("Warning: the xml p file does not exist.")
                return
        except ET.ParseError:
            self.send_log.emit("Warning: the xml file is not well-formed.")
            return
        pathbio_child = root.find(".//Path_Bio")
        if pathbio_child is not None:
            if os.path.isdir(pathbio_child.text):
                self.path_bio = pathbio_child.text
        self.path_im_bio = self.path_bio
        # self.path_bio is defined in StatModUseful.
        self.data_fish = []  # all data concerning the fish
        # attribute from the xml which the user can search the database
        # the name should refect the xml attribute or bio_info.load_xml_name() should be changed
        # can be changed but with caution
        # coorect here for new language by adding an attribute in the form "langue"_common_name
        # stage have to be the first attribute !
        self.attribute_acc = ['Stage', 'French_common_name', 'English_common_name', 'Code_ONEMA', 'Code_Sandre',
                              'LatinName', 'CdBiologicalModel']
        self.all_run_choice = [self.tr('Coarser Substrate'), self.tr('Dominant Substrate'), self.tr('By Percentage'),
                               self.tr('Neglect Substrate')]
        self.hdf5_merge = []  # the list with the name and path of the hdf5 file
        self.text_ini = []  # the text with the tooltip
        # self.name_database = 'pref_bio.db'
        self.timer = QTimer()
        self.running_time = 0
        self.timer.timeout.connect(self.show_prog)
        self.plot_new = False
        self.tooltip = []  # the list with tooltip of merge file (useful for chronicle_GUI.py)
        self.ind_current = None
        self.p = Process(target=None)  # second process

        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # the available merged data
        l0 = QLabel(self.tr('<b> Substrate and hydraulic data </b>'))
        self.m_all = QComboBox()

        # create lists with the possible fishes
        # right buttons for both QListWidget managed in the MainWindows class
        selected_fish_label = QLabel(self.tr('<b> Selected models </b>'))
        self.explore_bio_model_pushbutton = QPushButton(self.tr('Explore biological models'))
        self.explore_bio_model_pushbutton.clicked.connect(self.open_bio_model_explorer)

        self.list_s.setSelectionMode(QAbstractItemView.ExtendedSelection)


        # run habitat value
        self.l9 = QLabel(self.tr(' <b> Options for the computation </b>'))
        self.l9.setAlignment(Qt.AlignBottom)
        self.choice_run = QComboBox()
        self.choice_run.addItems(self.all_run_choice)
        self.runhab = QPushButton(self.tr('Compute Habitat Value'))
        self.runhab.setStyleSheet("background-color: #47B5E6; color: black")
        self.runhab.clicked.connect(self.run_habitat_value)


        # fill hdf5 list
        self.update_merge_list()

        # empty frame scrolable
        content_widget = QFrame()

        # layout
        self.layout4 = QGridLayout(content_widget)
        self.layout4.addWidget(l0, 0, 0)
        self.layout4.addWidget(self.m_all, 0, 1, 1, 2)

        self.layout4.addWidget(selected_fish_label, 2, 0)
        self.layout4.addWidget(self.explore_bio_model_pushbutton, 2, 1)
        self.layout4.addWidget(self.list_s, 3, 0, 3, 2)

        self.layout4.addWidget(self.l9, 3, 3)
        self.layout4.addWidget(self.choice_run, 4, 3)
        self.layout4.addWidget(self.runhab, 5, 3)

        # self.setLayout(self.layout4)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

    def open_bio_model_explorer(self):
        self.nativeParentWidget().bio_model_explorer_dialog.open_bio_model_explorer()

    def select_fish(self):
        """
        This function selects the fish which corresponds at the chosen criteria by the user. The type of criteria
        is given in the list self.keys and the criteria is given in self.cond1. The condition should exactly
        match the criteria. Signs such as * do not work.
        """
        # get item s to be selected
        i = self.keys.currentIndex()  # item type
        cond = self.cond1.text()
        if i == 0:
            i = -1  # i +2=1 for the key called 'stage' which is on the second colum of self.data_type
        data_fish_here = []
        for f in self.data_fish[:, i + 2]:
            data_fish_here.append(f.lower())
        data_fish_here = np.array(data_fish_here)
        if cond.lower() in data_fish_here:
            inds = np.where(data_fish_here == cond.lower())[0]
            self.runhab.setEnabled(True)
        else:
            self.send_log.emit(self.tr('Warning: No suitability curve found for the last selection.'))
            return
        # get the new selection
        for ind in inds:
            for i in range(0, self.list_f.count()):
                item = self.list_f.item(i)
                if item.text() == self.data_fish[ind, 0]:
                    break
            self.list_f.setCurrentRow(i)
            # add the fish to the QListView
            self.add_fish()

    def update_merge_list(self):
        """
        This function goes in the projet xml file and gets all available merged data. Usually, it is called
        by Substrate() (when finished to merge some data) or at the start of HABBY.

        We add a "tooltip" which indicates the orginal hydraulic and substrate files.
        """

        xmlfile = os.path.join(self.path_prj, self.name_prj + '.xml')
        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                self.send_log.emit("Warning: the xml project file does not exist.")
                return
        except ET.ParseError:
            self.send_log.emit("Warning: the xml project file is not well-formed.")
            return

        self.m_all.clear()
        self.tooltip = []
        self.hdf5_merge = []

        # get filename
        files = root.findall('.//hdf5_habitat')
        files = reversed(files)  # get the newest first

        path_hdf5 = self.find_path_hdf5_est()
        # add it to the list
        if files is not None:
            for idx, f in enumerate(files):
                if os.path.isfile(os.path.join(path_hdf5, f.text)):
                    [sub_ini, hydro_ini] = hdf5_mod.get_initial_files(path_hdf5, f.text)
                    hydro_ini = os.path.basename(hydro_ini)
                    textini = 'Hydraulic: ' + hydro_ini + '\nSubstrate :' + sub_ini
                    if len(f.text) < 55:
                        self.m_all.addItem(f.text)
                    else:
                        blob = f.text[:55] + '...'
                        self.m_all.addItem(blob)
                    self.m_all.setItemData(idx, textini, Qt.ToolTipRole)
                    self.tooltip.append(textini)
                    name = f.text
                    self.hdf5_merge.append(name)
                else:
                    self.send_log.emit("Warning: " + f.text + ", this .hab file has been deleted by the user.")
                    # TODO : It will be deleted from the .xml file.
        # a signal to indicates to Chronicle_GUI.py to update the merge file
        self.get_list_merge.emit()

    def run_habitat_value(self):
        """
        This function runs HABBY to get the habitat value based on the data in a "merged" hdf5 file and the chosen
        preference files.

        We should not add a comma in the name of the selected fish.
        """

        # disable the button
        self.runhab.setDisabled(True)
        self.send_log.emit(self.tr('# Calculating: habitat value...'))

        # get the figure options and the type of output to be created
        fig_dict = preferences_GUI.load_fig_option(self.path_prj, self.name_prj)

        # get the name of the xml biological file of the selected fish and the stages to be analyzed
        pref_list = []
        stages_chosen = []
        name_fish = []
        name_fish_sh = []  # because max 10 characters in attribute table of shapefile
        name_fish_sel = ''  # for the xml project file
        xmlfiles = []
        for i in range(0, self.list_s.count()):
            fish_item = self.list_s.item(i)
            for j in range(0, self.list_f.count()):
                if self.data_fish[j][0] == fish_item.text():
                    pref_list.append(self.data_fish[j][2])
                    stages_chosen.append(self.data_fish[j][1])
                    if int(fig_dict['fish_name_type']) == 0:  # latin name
                        name_fish.append(self.data_fish[j][7])
                    elif int(fig_dict['fish_name_type']) == 1:  # french common name
                        name_fish.append(self.data_fish[j][3])
                    elif int(fig_dict['fish_name_type']) == 2:  # english common name
                        name_fish.append(self.data_fish[j][4])
                    elif int(fig_dict['fish_name_type']) == 3:  # code onema
                        name_fish.append(self.data_fish[j][5])
                    else:
                        name_fish.append(self.data_fish[j][5])
                    name_fish_sh.append(self.data_fish[j][5][:3] + self.data_fish[j][1][:3])
                    name_fish_sel += fish_item.text() + ','
                    xmlfiles.append(self.data_fish[j][2])

        # save the selected fish in the xml project file
        try:
            try:
                filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
                docxml = ET.parse(filename_path_pro)
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml project file does not exist \n")
                return
        except ET.ParseError:
            print("Warning: the xml project file is not well-formed.\n")
            return
        hab_child = root.find(".//Habitat")
        if hab_child is None:
            blob = ET.SubElement(root, "Habitat")
            hab_child = root.find(".//Habitat")
        fish_child = root.find(".//Habitat/Fish_Selected")
        if fish_child is None:
            blob = ET.SubElement(hab_child, "Fish_Selected")
            fish_child = root.find(".//Habitat/Fish_Selected")
        fish_child.text = name_fish_sel[:-1]  # last comma
        docxml.write(filename_path_pro)

        # get the name of the merged file
        path_hdf5 = self.find_path_hdf5_est()
        ind = self.m_all.currentIndex()
        if len(self.hdf5_merge) > 0:
            hdf5_file = self.hdf5_merge[ind]
        else:
            self.runhab.setDisabled(False)
            self.send_log.emit('Error: No merged hydraulic files available.')
            return

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)

        # get the path where to save the different outputs (function in estimhab_GUI.py)
        path_txt = self.find_path_text_est()
        path_im = self.find_path_im_est()
        path_shp = self.find_path_output_est("Path_Shape")
        path_para = self.find_path_output_est("Path_Visualisation")

        # get the type of option choosen for the habitat calculation
        run_choice = self.choice_run.currentIndex()

        # only useful if we want to also show the 2d figure in the GUI
        self.hdf5_file = hdf5_file
        self.path_hdf5 = path_hdf5
        path_im_bioa = os.path.join(os.getcwd(), self.path_im_bio)

        # send the calculation of habitat and the creation of output
        self.timer.start(100)  # to refresh progress info
        self.q4 = Queue()
        self.progress_value = Value("i", 0)
        self.p = Process(target=calcul_hab_mod.calc_hab_and_output, args=(hdf5_file, path_hdf5, pref_list, stages_chosen,
                                                                          name_fish, name_fish_sh, run_choice,
                                                                          self.path_bio, path_txt, self.progress_value,
                                                                          self.q4, False, fig_dict, path_im_bioa,
                                                                          xmlfiles))
        self.p.name = "Habitat calculation"
        self.p.start()

        # log
        self.send_log.emit("py    file1='" + hdf5_file + "'")
        self.send_log.emit("py    path1= os.path.join(path_prj, 'hdf5')")
        self.send_log.emit("py    pref_list= ['" + "', '".join(pref_list) + "']")
        self.send_log.emit("py    stages= ['" + "', '".join(stages_chosen) + "']")
        self.send_log.emit("py    type=" + str(run_choice))
        self.send_log.emit("py    name_fish1 = ['" + "', '".join(name_fish) + "']")
        self.send_log.emit("py    name_fish2 = ['" + "', '".join(name_fish_sh) + "']")
        self.send_log.emit(
            "py    calcul_hab.calc_hab_and_output(file1, path1 ,pref_list, stages, name_fish1, name_fish2, type, "
            "path_bio, path_prj, path_prj, path_prj, path_prj, [], True, [])")
        self.send_log.emit("restart RUN_HABITAT")
        self.send_log.emit("restart    file1: " + hdf5_file)
        self.send_log.emit("restart    list of preference file: " + ",".join(pref_list))
        self.send_log.emit("restart    stages chosen: " + ",".join(stages_chosen))
        self.send_log.emit("restart    type of calculation: " + str(run_choice))

    def show_prog(self):
        """
        This function is linked with the timer started in run_habitat_value. It is run regulary and
        check if the function on the second thread have finised created the figures. If yes,
        this function create the 1d figure for the HABBY GUI.
        """

        # say in the Stauts bar that the processus is alive
        if self.p.is_alive():
            self.running_time += 0.100  # this is useful for GUI to update the running, should be logical with self.Timer()
            # get the langugage
            fig_dict = preferences_GUI.load_fig_option(self.path_prj, self.name_prj)
            # send the message
            if fig_dict['language'] == str(1):
                # it is necssary to start this string with Process to see it in the Statusbar
                self.send_log.emit("Processus 'Habitat' fonctionne depuis " + str(round(self.running_time)) + " sec.")
            else:
                # it is necssary to start this string with Process to see it in the Statusbar
                self.send_log.emit("Process 'Habitat' is alive and run since " + str(round(self.running_time)) + " sec.")
            self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
            self.nativeParentWidget().kill_process.setVisible(True)

        # when the loading is finished
        if not self.q4.empty():
            self.timer.stop()
            self.mystdout = self.q4.get()
            self.send_err_log()

            # give the possibility of sending a new simulation
            self.runhab.setDisabled(False)

            self.send_log.emit(self.tr('Habitat calculation is finished (computation time = ') + str(round(self.running_time)) + " s).")
            self.send_log.emit(self.tr("Figures can be displayed/exported from 'Data explorer' tab."))

            # put the timer back to zero and clear status bar
            self.running_time = 0
            self.send_log.emit("clear status bar")
            self.plot_new = False
            # refresh plot gui list file
            self.nativeParentWidget().central_widget.data_explorer_tab.refresh_filename()
            self.nativeParentWidget().central_widget.tools_tab.refresh_hab_filenames()
            self.running_time = 0
            self.nativeParentWidget().kill_process.setVisible(False)

        if not self.p.is_alive():
            # enable the button to call this functin directly again
            self.timer.stop()

            # put the timer back to zero
            self.running_time = 0
            self.send_log.emit("clear status bar")


if __name__ == '__main__':
    pass
