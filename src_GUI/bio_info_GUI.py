from io import StringIO
from PyQt5.QtCore import QTranslator, pyqtSignal, QThread, Qt, QTimer, QStringListModel, QEvent, QObject
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout,  QLineEdit, QComboBox, QAbstractItemView, \
    QSizePolicy, QScrollArea, QFrame, QCompleter
from PyQt5.QtGui import QPixmap, QFont
from multiprocessing import Process, Queue
import os
import sys
import time
import numpy as np
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import bio_info
from src_GUI import estimhab_GUI
from src import calcul_hab
from src import load_hdf5
from src_GUI import output_fig_GUI


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
        self.lang = lang
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.imfish = ''
        self.keep_data = None
        self.path_im_bio = 'biology/figure_pref/'
        # self.path_bio is defined in StatModUseful.
        self.data_fish = []  # all data concerning the fish
        # attribute from the xml which the user can search the database
        # the name should refect the xml attribute or bio_info.load_xml_name() should be changed
        # can be changed but with caution
        # coorect here for new language by adding an attribute in the form "langue"_common_name
        # stage have to be the first attribute !
        self.attribute_acc = ['Stage', 'French_common_name','English_common_name', 'Code_ONEMA', 'Code_Sandre',
                              'LatinName', 'CdBiologicalModel']
        self.all_run_choice = [self.tr('Coarser Substrate'), self.tr('Dominant Substrate'), self.tr('By Percentage'),
                               self.tr('Neglect Substrate')]
        self.hdf5_merge = []  # the list with the name and path of the hdf5 file
        self.text_ini = []  # the text with the tooltip
        #self.name_database = 'pref_bio.db'
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.running_time = 0
        self.timer.timeout.connect(self.show_image_hab)
        self.plot_new = False
        self.tooltip = []  # the list with tooltip of merge file (useful for chronicle_GUI.py)
        self.ind_current = None

        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        # the available merged data
        l0 = QLabel(self.tr('<b> Substrate and hydraulic data </b>'))
        self.m_all = QComboBox()

        # create lists with the possible fishes
        # right buttons for both QListWidget managed in the MainWindows class
        l1 = QLabel(self.tr('<b> Available Fish and Guild </b>'))
        l2 = QLabel(self.tr('<b> Selected Fish and Guild </b>'))
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_s.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # show information about the fish
        self.list_f.itemClicked.connect(self.show_info_fish_avai)
        self.list_s.itemClicked.connect(self.show_info_fish_sel)
        self.list_f.itemActivated.connect(self.show_info_fish_avai)
        self.list_s.itemActivated.connect(self.show_info_fish_sel)
        # shwo info if movement of the arrow key
        self.list_f.itemSelectionChanged.connect(self.show_info_fish)
        self.list_s.itemSelectionChanged.connect(lambda: self.show_info_fish(True))
        self.list_f.setMinimumWidth(280)

        # run habitat value
        self.l9 = QLabel(' <b> Options for the computation </b>')
        self.l9.setAlignment(Qt.AlignBottom)
        self.choice_run = QComboBox()
        self.choice_run.addItems(self.all_run_choice)
        self.runhab = QPushButton(self.tr('Compute Habitat Value'))
        self.runhab.setStyleSheet("background-color: #31D656")
        self.runhab.clicked.connect(self.run_habitat_value)
        self.butfig = QPushButton(self.tr("Create figure again"))
        self.butfig.clicked.connect(self.recreate_fig)
        if not self.keep_data:
            self.butfig.setDisabled(True)

        # find the path bio
        try:
            try:
                docxml = ET.parse(os.path.join(self.path_prj, self.name_prj + '.xml'))
                root = docxml.getroot()
            except IOError:
                # self.send_log.emit("Warning: the xml p file does not exist \n")
                return
        except ET.ParseError:
            self.send_log.emit("Warning: the xml file is not well-formed.\n")
            return
        pathbio_child = root.find(".//Path_Bio")
        if pathbio_child is not None:
            if os.path.isdir(pathbio_child.text):
                self.path_bio = pathbio_child.text

        # info on preference curve
        l4 = QLabel(self.tr('<b> Information on the suitability curve</b> (Right click on fish name)'))
        l5 = QLabel(self.tr('Latin Name: '))
        self.com_name = QLabel()
        l7 = QLabel(self.tr('ONEMA fish code: '))
        self.fish_code = QLabel('')
        l8 = QLabel(self.tr('Description:'))
        self.descr = QLabel()
        self.pref_curve = QPushButton(self.tr('Show suitability curve'))
        self.pref_curve.clicked.connect(self.show_pref)

        # get a scollable area for the decription which might be long
        self.scroll = QScrollArea()
        self.scroll.setFrameStyle(QFrame.NoFrame)
        self.vbar = self.scroll.verticalScrollBar()
        self.descr.setWordWrap(True)
        self.descr.setMaximumSize(200, 210)
        self.descr.setAlignment(Qt.AlignTop)
        self.descr.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.descr.setTextFormat(Qt.RichText)
        self.scroll.setWidget(self.descr)
        # to have the Qlabel at the right size
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('background-color: white')
        self.vbar.setStyleSheet('background-color: lightGrey')

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # image fish
        self.pic = QLabel()

        # hydrosignature
        self.hs = QPushButton(self.tr('Show Measurement Conditions (Hydrosignature)'))
        self.hs.clicked.connect(self.show_hydrosignature)

        # fill in list of fish
        sys.stdout = self.mystdout = StringIO()
        self.data_fish = bio_info.load_xml_name(self.path_bio, self.attribute_acc)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        # order data fish by alphabetical order on the first column
        ind = self.data_fish[:, 0].argsort()
        self.data_fish = self.data_fish[ind, :]
        self.list_f.addItems(self.data_fish[:,0])

        # erase fish selection
        self.butdel = QPushButton(self.tr("Erase All Selection"))
        self.butdel.clicked.connect(self.remove_all_fish)

        # fish selected fish
        self.add_sel_fish()
        if self.list_s.count() == 0:
            self.runhab.setDisabled(True)

        # search possibility
        l3 = QLabel(self.tr('<b> Search biological models </b>'))
        self.keys = QComboBox()
        self.keys.addItems(self.attribute_acc[:-1])
        self.keys.currentIndexChanged.connect(self.get_autocompletion)
        l02 = QLabel('is equal to')
        l02.setAlignment(Qt.AlignCenter)
        self.cond1 = QLineEdit()
        self.cond1.returnPressed.connect(self.next_completion)
        #self.cond1.returnPressed.connect(self.select_fish)
        self.bs = QPushButton(self.tr('Select suitability curve'))
        self.bs.clicked.connect(self.select_fish)
        # add auto-completion
        self.completer = QCompleter()
        self.model = QStringListModel()
        self.completer.setModel(self.model)
        self.cond1.setCompleter(self.completer)
        self.get_autocompletion()

        # fill hdf5 list
        self.update_merge_list()

        # layout
        self.layout4 = QGridLayout()
        self.layout4.addWidget(l0, 0, 0)
        self.layout4.addWidget(self.m_all, 0, 1, 1, 2)

        self.layout4.addWidget(l1, 2, 0)
        self.layout4.addWidget(l2, 2, 2)
        self.layout4.addWidget(self.list_f, 3, 0, 3, 2)
        self.layout4.addWidget(self.list_s, 3, 2, 3, 1)

        self.layout4.addWidget(l4, 6, 0,1, 3)
        self.layout4.addWidget(l5, 7, 0)
        self.layout4.addWidget(self.com_name, 7, 1)
        self.layout4.addWidget(l7, 8, 0)
        self.layout4.addWidget(self.fish_code,8, 1)
        self.layout4.addWidget(l8,9,0)
        self.layout4.addWidget(self.scroll, 9, 1, 3, 2) # in fact self.descr is in self.scoll
        self.layout4.addWidget(self.pic, 11, 0)
        self.layout4.addWidget(self.l9, 3, 3)
        self.layout4.addWidget(self.choice_run, 4, 3)
        self.layout4.addWidget(self.runhab, 5, 3)
        self.layout4.addWidget(self.butfig, 6, 3)
        self.layout4.addWidget(self.pref_curve, 9, 3)
        self.layout4.addWidget(self.hs, 10, 3)
        self.layout4.addWidget(self.butdel, 2, 3)

        self.layout4.addWidget(l3, 12, 0)
        self.layout4.addWidget(self.keys, 13, 0)
        self.layout4.addWidget(l02,13, 1)
        self.layout4.addWidget(self.cond1, 13, 2)
        self.layout4.addWidget(self.bs, 13, 3)

        # self.layout4.addItem(spacer1, 0, 2)
        # self.layout4.addItem(spacer2, 3, 3)
        self.setLayout(self.layout4)

    def next_completion(self):
        """
        A small function to use the enter key to select the fish with auto-completion.
        Adapted from https://stackoverflow.com/questions/9044001/qcompleter-and-tab-key
        It would be nice to make it work with tab also but it is quite complcated because the tab key is already used by
        PyQt to go from one windows to the next.
        """
        index = self.completer.currentIndex()
        self.completer.popup().setCurrentIndex(index)
        start = self.completer.currentRow()
        if not self.completer.setCurrentRow(start + 1):
            self.completer.setCurrentRow(0)

        self.select_fish()

    def get_autocompletion(self):
        """
        This function updates the auto-complexton model as a function of the QComboxBox next to it with support for
        upper and lower case.
        """
        ind = self.keys.currentIndex()

        if ind == 0:
            string_all = list(set(list(self.data_fish[:, 1]) + list([item.lower() for item in self.data_fish[:, 1]]) +
                                  list([item.upper() for item in self.data_fish[:, 1]])))
        elif ind == 1:
            string_all = list(set(list(self.data_fish[:, 3]) + [item.lower() for item in self.data_fish[:, 3]] +
                                  [item.upper() for item in self.data_fish[:, 3]]))
        elif ind ==2:
            string_all = list(set(list(self.data_fish[:, 4]) + [item.lower() for item in self.data_fish[:, 4]] +
                                  [item.upper() for item in self.data_fish[:, 4]]))
        elif ind == 3:
            string_all = list(set(list(self.data_fish[:, 5]) + [item.lower() for item in self.data_fish[:, 5]] +
                                  [item.upper() for item in self.data_fish[:, 5]]))
        elif ind == 4:
            string_all = list(set(list(self.data_fish[:, 6]) + [item.lower() for item in self.data_fish[:, 6]] +
                                  [item.upper() for item in self.data_fish[:, 6]]))
        elif ind == 5:
            string_all = list(set(list(self.data_fish[:, 7]) + [item.lower() for item in self.data_fish[:, 7]] +
                                  [item.upper() for item in self.data_fish[:, 7]]))
        else:
            string_all = ''

        self.model.setStringList(string_all)

    def show_info_fish(self, select=False):
        """
        This function shows the useful information concerning the selected fish on the GUI.

        :param select:If False, the selected items comes from the QListWidgetcontaining the available fish.
                      If True, the items comes the QListWidget with the selected fish
        """

        # get the file
        if not select:
            i1 = self.list_f.currentItem()  # show the info concerning the one selected fish
            if not i1:
                return
            self.ind_current = self.list_f.currentRow()
        else:
            found_it = False
            i1 = self.list_s.currentItem()
            if not i1:
                return
            for m in range(0, self.list_f.count()):
                self.list_f.setCurrentRow(m)
                if i1.text() == self.list_f.currentItem().text():
                    self.ind_current = m
                    found_it = True
                    break
            if not found_it:
                self.ind_current = None

        if i1 is None:
            return

        name_fish = i1.text()
        name_fish = name_fish.split(':')[0]
        i = np.where(self.data_fish[:, 7] == name_fish)[0]
        if len(i) > 0:
            xmlfile = os.path.join(self.path_bio, self.data_fish[i[0], 2])
        else:
             return

        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file does not exist \n")
                return
        except ET.ParseError:
            print("Warning: the xml file is not well-formed.\n")
            return

        # get the data code ONEMA
        # for the moment only one code alternativ possible
        data = root.find('.//CdAlternative')
        if data is not None:
            if data.attrib['OrgCdAlternative']:
                if data.attrib['OrgCdAlternative'] == 'ONEMA':
                    self.fish_code.setText(data.text)

        # get the latin name
        data = root.find('.//LatinName')
        if data is not None:
            self.com_name.setText(data.text)

        # get the description
        data = root.findall('.//Description')
        if len(data)>0:
            found = False
            for d in data:
                if d.attrib['Language'] == self.lang:
                    self.descr.setText(d.text)
                    found = True
            if not found:
                self.descr.setText(data[0].text)

        # get the image fish
        data = root.find('.//Image')
        if data is not None:
            self.imfish = os.path.join(os.getcwd(), self.path_im_bio, data.text)
            name_imhere = os.path.join(os.getcwd(), self.path_im_bio, data.text)
            if os.path.isfile(name_imhere):
                # use full ABSOLUTE path to the image, not relative
                self.pic.setPixmap(QPixmap(name_imhere).scaled(200, 90, Qt.KeepAspectRatio))  # 800 500
            else:
                self.pic.clear()
        else:
            self.pic.clear()

    def show_info_fish_sel(self):
        """
        This function shows the useful information concerning the already selected fish on the GUI and
        remove fish from the list of selected fish. This is what happens when the user click on the
        second QListWidget (the one called selected fish and guild).
        """

        self.show_info_fish(True)
        self.remove_fish()
        # Enable the button
        if self.list_s.count() > 0:
            self.runhab.setEnabled(True)
        else:
            self.runhab.setEnabled(False)

    def show_info_fish_avai(self):
        """
        This function shows the useful information concerning the available fish on the GUI and
        add the fish to  the selected fish This is what happens when the user click on the
        first QListWidget (the one called available fish).
        """

        self.show_info_fish(False)
        self.add_fish()
        if self.list_s.count() > 0:
            self.runhab.setEnabled(True)
        else:
            self.runhab.setEnabled(False)

    def show_hydrosignature(self):
        """
        This function make the link with function in bio_info.py which allows to load and plot the data related
        to the hydrosignature.
        """

        # get the file
        i = self.list_f.currentRow()
        xmlfile = os.path.join(self.path_bio, self.data_fish[i, 2])
        # do the plot
        sys.stdout = self.mystdout = StringIO()
        bio_info.plot_hydrosignature(xmlfile)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        # show the plot
        self.show_fig.emit()

    def select_fish(self):
        """
        This function selects the fish which corresponds at the chosen criteria by the user. The type of criteria
        is given in the list self.keys and the criteria is given in self.cond1. The condition should exactly
        match the criteria. Signs such as * do not work.
        """
        # get item s to be selected
        i = self.keys.currentIndex() # item type
        cond = self.cond1.text()
        if i == 0:
            i = -1 # i +2=1 for the key called 'stage' which is on the second colum of self.data_type
        data_fish_here = []
        for f in self.data_fish[:, i+2]:
            data_fish_here.append(f.lower())
        data_fish_here = np.array(data_fish_here)
        if cond.lower() in data_fish_here:
            inds = np.where(data_fish_here == cond.lower())[0]
            self.runhab.setEnabled(True)
        else:
            self.send_log.emit(self.tr('Warning: No suitability curve found for the last selection. \n'))
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

        xmlfile = os.path.join(self.path_prj, self.name_prj +'.xml')
        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                self.send_log.emit("Warning: the xml project file does not exist \n")
                return
        except ET.ParseError:
            self.send_log.emit("Warning: the xml project file is not well-formed.\n")
            return

        self.m_all.clear()
        self.tooltip = []
        self.hdf5_merge = []

        # get filename
        files = root.findall('.//hdf5_mergedata')
        files = reversed(files)  # get the newest first

        path_hdf5 = self.find_path_hdf5_est()
        # add it to the list
        if files is not None:
            for idx,f in enumerate(files):
                if os.path.isfile(os.path.join(path_hdf5,f.text)):
                    [sub_ini, hydro_ini] = load_hdf5.get_initial_files(path_hdf5, f.text)
                    hydro_ini = os.path.basename(hydro_ini)
                    textini = 'Hydraulic: '+hydro_ini + '\nSubstrate :' + sub_ini
                    if len(f.text) < 55:
                        self.m_all.addItem(f.text)
                    else:
                        blob = f.text[:55] + '...'
                        self.m_all.addItem(blob)
                    self.m_all.setItemData(idx,textini, Qt.ToolTipRole)
                    self.tooltip.append(textini)
                    name = f.text
                    self.hdf5_merge.append(name)
                else:
                    self.send_log.emit("Warning: One merge hdf5 file was not found by calc_hab \n")
        # a signal to indicates to Chronicle_GUI.py to update the merge file
        self.get_list_merge.emit()

    def show_pref(self):
        """
        This function shows the image of the preference curve of the selected xml file. For this it calls, the functions
        read_pref and figure_pref of bio_info.py. Hence, this function justs makes the link between the GUI and
        the functions effectively doing the image.
        """

        if self.ind_current is None:
            self.send_log.emit("Warning: No fish selected to create suitability curves \n")
            return

        # get the file
        i =  self.ind_current # show the info concerning the one selected fish
        xmlfile = os.path.join(self.path_bio, self.data_fish[i, 2])

        # open the pref
        sys.stdout = self.mystdout = StringIO()
        [h_all, vel_all, sub_all, code_fish, name_fish, stages] = bio_info.read_pref(xmlfile)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        # plot the pref
        fig_dict = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        bio_info.figure_pref(h_all, vel_all, sub_all, code_fish, name_fish, stages, fig_opt=fig_dict)

        # show the image
        self.show_fig.emit()

    def run_habitat_value(self):
        """
        This function runs HABBY to get the habitat value based on the data in a "merged" hdf5 file and the chosen
        preference files.

        We should not add a comma in the name of the selected fish.
        """

        # disable the button
        self.runhab.setDisabled(True)
        self.send_log.emit(" Calculating habitat value... \n")

        # get the figure options and the type of output to be created
        fig_dict = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)

        # erase the memory of the data for the figure
        self.keep_data = None

        # get the name of the xml biological file of the selected fish and the stages to be analyzed
        pref_list = []
        stages_chosen = []
        name_fish = []
        name_fish_sh = [] # because max 10 characters in attribute table of shapefile
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
                    name_fish_sh.append(self.data_fish[j][5][:3]+self.data_fish[j][1][:3])
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
            self.send_log.emit('Error: No merged hydraulic files available \n')
            return

        # get the path where to save the different outputs (function in estimhab_GUI.py)
        path_txt = self.find_path_text_est()
        path_im = self.find_path_im_est()
        path_shp = self.find_path_output_est("Path_Shape")
        path_para = self.find_path_output_est("Path_Paraview")

        # get the type of option choosen for the habitat calculation
        run_choice = self.choice_run.currentIndex()

        # only useful if we want to also show the 2d figure in the GUI
        self.hdf5_file = hdf5_file
        self.path_hdf5 = path_hdf5
        path_im_bioa = os.path.join(os.getcwd(), self.path_im_bio)

        # send the calculation of habitat and the creation of output
        self.timer.start(1000)  # to know when to show image
        self.q4 = Queue()
        self.p4 = Process(target=calcul_hab.calc_hab_and_output, args=(hdf5_file, path_hdf5, pref_list, stages_chosen,
                                                                       name_fish, name_fish_sh, run_choice,
                                                                       self.path_bio, path_txt, path_shp, path_para,
                                                                       path_im, self.q4, False, fig_dict, path_im_bioa,
                                                                       xmlfiles))
        self.p4.start()

        # log
        self.send_log.emit("py    file1='" + hdf5_file + "'")
        self.send_log.emit("py    path1= os.path.join(path_prj, 'fichier_hdf5')")
        self.send_log.emit("py    pref_list= ['" + "', '".join(pref_list) + "']")
        self.send_log.emit("py    stages= ['" + "', '".join(stages_chosen) + "']")
        self.send_log.emit("py    type=" + str(run_choice))
        self.send_log.emit("py    name_fish1 = ['"+ "', '".join(name_fish) + "']")
        self.send_log.emit("py    name_fish2 = ['" + "', '".join(name_fish_sh) + "']")
        self.send_log.emit(
            "py    calcul_hab.calc_hab_and_output(file1, path1 ,pref_list, stages, name_fish1, name_fish2, type, "
            "path_bio, path_prj, path_prj, path_prj, path_prj, [], True, [])")
        self.send_log.emit("restart RUN_HABITAT")
        self.send_log.emit("restart    file1: " + hdf5_file)
        self.send_log.emit("restart    list of preference file: " + ",".join(pref_list))
        self.send_log.emit("restart    stages chosen: " + ",".join(stages_chosen))
        self.send_log.emit("restart    type of calculation: " + str(run_choice))

    def recreate_fig(self):
        """
        This function use show_image_hab() to recreate the habitat figures shown before
        """
        self.plot_new = True
        self.show_image_hab()

    def show_image_hab(self):
        """
        This function is linked with the timer started in run_habitat_value. It is run regulary and
        check if the function on the second thread have finised created the figures. If yes,
        this function create the 1d figure for the HABBY GUI.
        """

        # say in the Stauts bar that the processus is alive
        if self.p4.is_alive():
            self.running_time += 1  # this is useful for GUI to update the running, should be logical with self.Timer()
            # get the langugage
            fig_dict = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
            # send the message
            if fig_dict['language'] == str(1):
                # it is necssary to start this string with Process to see it in the Statusbar
                self.send_log.emit("Processus 'Habitat' fonctionne depuis " + str(self.running_time) + " sec")
            else:
                # it is necssary to start this string with Process to see it in the Statusbar
                self.send_log.emit("Process 'Habitat' is alive and run since " + str(self.running_time) + " sec")

        # when the loading is finished
        if not self.q4.empty() or (self.keep_data is not None and self.plot_new):
            if self.keep_data is None:
                self.timer.stop()
                data_second = self.q4.get()
                self.mystdout = data_second[0]
                area_all = data_second[1]
                spu_all = data_second[2]
                name_fish = data_second[3]
                name_base = data_second[4]
                vh_all_t_sp = data_second[5]
                self.send_err_log()
                self.keep_data = data_second
            else:
                self.timer.stop()
                area_all = self.keep_data[1]
                spu_all = self.keep_data[2]
                name_fish = self.keep_data[3]
                name_base = self.keep_data[4]
                vh_all_t_sp = self.keep_data[5]

            # give the possibility of sending a new simulation
            self.runhab.setDisabled(False)

            if len(name_fish) > 0:
                if isinstance(name_fish[0], int):
                    self.running_time = 0
                    self.send_log.emit("clear status bar")
                    return

            # show one image (relatively quick to create)
            #sys.stdout = self.mystdout = StringIO()
            path_im = self.find_path_im_est()
            fig_dict = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
            sim_name = load_hdf5.load_timestep_name(self.hdf5_file, self.path_hdf5)
            if fig_dict['erase_id'] == 'True':
                erase_id = True
            else:
                erase_id = False
            calcul_hab.save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base, fig_dict, sim_name, erase_id)
            for t in fig_dict['time_step']:
                # if print last and first time step and one time step only, only print it once
                if t == -1 and len(vh_all_t_sp[0]) == 2 and 1 in fig_dict['time_step']:
                    pass
                else:
                    calcul_hab.save_vh_fig_2d(self.hdf5_file, self.path_hdf5, [vh_all_t_sp[0]],
                                              path_im, name_fish, name_base, fig_dict, [t], save_fig=False)

           # sys.stdout = sys.__stdout__
            #self.send_err_log()

            # show figure
            self.show_fig.emit()

            # enable the button to call this function directly again to redo the figure
            self.butfig.setEnabled(True)

            # put the timer back to zero and clear status bar
            self.running_time = 0
            self.send_log.emit("clear status bar")
            self.plot_new= False

        if not self.p4.is_alive():

            # enable the button to call this functin directly again
            self.butfig.setEnabled(True)
            self.timer.stop()

            # put the timer back to zero
            self.running_time = 0
            self.send_log.emit("clear status bar")




if __name__ == '__main__':
    pass