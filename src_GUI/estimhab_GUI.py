"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import os
from src import estimhab
import glob
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QTabWidget, QLineEdit, QTextEdit, QFileDialog,\
    QSpacerItem, QListWidget,  QListWidgetItem, QAbstractItemView, QMessageBox
from PyQt5.QtGui import QFont
import h5py
import sys
from io import StringIO
from src_GUI import output_fig_GUI


class StatModUseful(QWidget):
    """
    This class is not called directly by HABBY, but it is the parent class of EstihabW and FstressW. As fstress and
    estimhab have a similar graphical user interface, this architecture allows to re-use some functions between the
    two classes, which saves a bit of coding.
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    PyQtsignal to write the log.
    """
    show_fig = pyqtSignal()
    """
    PyQtsignal to show the figures.
    """

    def __init__(self):
        self.path_bio = 'biology'
        self.eq1 = QLineEdit()
        self.ew1 = QLineEdit()
        self.eh1 = QLineEdit()
        self.eq2 = QLineEdit()
        self.ew2 = QLineEdit()
        self.eh2 = QLineEdit()
        self.eqmin = QLineEdit()
        self.eqmax = QLineEdit()
        self.list_f = QListWidget()
        self.list_s = QListWidget()
        self.msge = QMessageBox()
        self.fish_selected = []
        self.qall = []  # q1 q2 qmin qmax q50. Value cannot be added directly because of stathab.

        super().__init__()

    def add_fish(self):
        """
        The function is used to select a new fish species (or inverterbrate)
        """
        items = self.list_f.selectedItems()
        ind = []
        if items:
            for i in range(0, len(items)):
                # avoid to have the same fish multiple times
                if items[i].text() in self.fish_selected:
                    pass
                else:
                    self.fish_selected.append(items[i].text())

        # order the list (careful QLIstWidget do not order as sort from list)
        if self.fish_selected:
            self.fish_selected.sort()
            self.list_s.clear()
            self.list_s.addItems(self.fish_selected)
            # bold for selected fish
            font = QFont()
            font.setItalic(True)
            for i in range(0, self.list_f.count()):
                for f in self.fish_selected:
                    if f == self.list_f.item(i).text():
                        self.list_f.item(i).setFont(font)

    def remove_fish(self):
        """
        The function is used to remove fish species (or inverterbates species)
        """
        item = self.list_s.takeItem(self.list_s.currentRow())
        try:
            self.fish_selected.remove(item.text())
        except ValueError:
            pass
        # bold for selected fish
        font = QFont()
        font.setItalic(False)
        for i in range(0, self.list_f.count()):
            if item.text() == self.list_f.item(i).text():
                self.list_f.item(i).setFont(font)
        item = None

    def remove_all_fish(self):
        """
        This function removes all fishes from the selected fish
        """
        self.list_s.clear()
        self.list_f.clear()
        self.fish_selected = []
        self.list_f.addItems(self.data_fish[:, 0])

    def add_sel_fish(self):
        """
        This function loads the xml file and check if some fish were selected before. If yes, we add them to the list
        """

        # open the xml file
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            # get the selected fish
            child = root.find(".//Habitat/Fish_Selected")
            if child is not None:
                fish_selected_b = child.text
                if fish_selected_b is not None:
                    if ',' in fish_selected_b:
                        fish_selected_b = fish_selected_b.split(',')
                    # show it
                    for i in range(0, self.list_f.count()):
                        self.list_f.clearSelection()
                        self.list_f.setCurrentRow(i)
                        items = self.list_f.selectedItems()
                        if items:
                            fish_l = items[0].text()
                            if fish_l in fish_selected_b:  # do not work with space here
                                self.add_fish()

    def find_path_im_est(self):
        """
        A function to find the path where to save the figues. Careful there is similar function in hydro_GUI_2.py.
        Do not mix it up

        :return: path_im a string which indicates the path to the folder where are save the images.
        """
        # to insure the existence of a path
        path_im = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Figure")
            if child is None:
                path_test = os.path.join(self.path_prj, r'/figures')
                if os.path.isdir(path_test):
                    path_im = path_test
                else:
                    path_im = self.path_prj
            else:
                path_im = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText( \
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_im

    def find_path_hdf5_est(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in hydro_GUI_2.py and in
        stathab_c. By default, path_hdf5 is in the project folder in the folder 'fichier_hdf5'.
        """

        path_hdf5 = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Hdf5")
            if child is None:
                path_hdf5 = os.path.join(self.path_prj, r'fichier_hdf5')
            else:
                path_hdf5 = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save the path to the fichier hdf5"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_hdf5

    def find_path_text_est(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_hdf5 is in the project folder in the folder 'fichier_hdf5'.
        """

        path_text = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Text")
            if child is None:
                path_text = os.path.join(self.path_prj, r'/text_output')
            else:
                path_text = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save the path to the fichier text"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_text

    def find_path_output_est(self, att):
        """
        A function to find the path where to save the shapefile, paraview files and other future format. Here, we gave
        the xml attribute as argument so this functin can be used to find all path needed. However, it is less practical
        to use as the function above as one should remember the xml tribute to call this function. However, it can be
        practical to use to add new folder. Careful a similar function is in Hydro_GUI_2.py.

        :param att: the xml attribute (from the xml project file) linked to the path needed, without the .//

        """

        path_out = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//" + att)
            if child is None:
                return self.path_prj
            else:
                path_out = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save the path to the fichier text"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_out

    def find_path_input_est(self):
        """
        A function to find the path where to save the input file. Careful a similar one is in hydro_GUI_2.py. By default,
        path_input indicates the folder 'input' in the project folder.
        """

        path_input = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Input")
            if child is None:
                path_input = os.path.join(self.path_prj, r'/input')
            else:
                path_input = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save the path to the copied inputs"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_input

    def send_err_log(self):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout before calling this function. It only sends the hundred first errors
        to avoid freezing the GUI. A similar function exists in hydro_GUI_2.py. Correct both if necessary.
        """
        max_send = 100
        if self.mystdout is not None:
            str_found = self.mystdout.getvalue()
        else:
            return
        str_found = str_found.split('\n')
        for i in range(0, min(len(str_found), max_send)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
            if i == max_send - 1:
                self.send_log.emit(self.tr('Warning: too many information for the GUI'))

    def check_all_q(self):
        """
        This function checks the range of the different discharge and send a warning if we are out of the range
        estimated reasonable (based on the manual from Estimhab and FStress). This is not used by Stathab.

        It uses the variable self.qall which is a list of float composed of q1, q2, qsim1, qsim2, q50. This function
        only send warning and it used to check the entry before the calculation.
        """

        if self.qall[0] < self.qall[1]:
            q1 = self.qall[0]
            q2 = self.qall[1]
        else:
            q2 = self.qall[0]
            q1 = self.qall[1]

        if q2 < 2*q1:
            self.send_log.emit('Warning: Measured discharge are not very different. The results might '
                               'not be realistic. \n')
        if (self.qall[4] < q1 / 10 or self.qall[4] > 5 * q2) and self.qall[4] != -99:  # q50 not always necessary
            self.send_log.emit('Warning: Q50 should be between q1/10 and 5*q2 for optimum results. \n')
        if self.qall[2] < q1 / 10 or self.qall[2] > 5 * q2:
            self.send_log.emit('Warning: Discharge range should be between q1/10 and 5*q2 for optimum results. (1) \n')
        if self.qall[3] < q1 / 10 or self.qall[3] > 5 * q2:
            self.send_log.emit('Warning: Discharge range should be between q1/10 and 5*q2 for optimum results. (1) \n')



class EstimhabW(StatModUseful):
    """
    The Estimhab class provides the graphical interface for the version of the Estimhab model written in HABBY.
    The Estimhab model is described elsewhere. EstimhabW() just loads the data for Estimhab given by the user.
    """

    save_signal_estimhab = pyqtSignal()
    """
    PyQtsignal to save the Estimhab data.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.eq50 = QLineEdit()
        self.esub = QLineEdit()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_bio_estimhab = os.path.join(self.path_bio, 'estimhab')
        self.VH = []
        self.SPU = []
        self.filenames = []  # a list which link the name of the fish name and the xml file
        self.init_iu()

    def init_iu(self):

        """
        This function is used to initialized an instance of the EstimhabW() class. It is called by __init__().

         **Technical comments and walk-through**

         First we looked if some data for Estimhab was saved before by an user. If yes, we will fill the GUI with
         the information saved before. Estimhab information is saved in hdf5 file format and the path/name of the
         hdf5 file is saved in the xml project file. So we open the xml project file and look if the name of an hdf5
         file was saved for Estimhab. If yes, the hdf5 file is read.

         The format of hdf5 file is relatively simple. Each input data for Estimhab has its own dataset (qmes, hmes,
         wmes, q50, qrange, and substrate).  Then, we have a list of string which are a code for the fish species which
         were analyzed.  All the data contained in hdf5 file is loaded into variable.

         The different label are written on the graphical interface. Then, two QListWidget are modified. The first
         list contains all the fish species on which HABBY has info (see XML Estimhab format for more info).
         The second list is the fish selected by the user on which Estimhab will be run. Here, we link these lists
         with two functions so that the user can select/deselect fish using the mouse. The function name are add_fish()
         and remove_fish().

         Then, we fill the first list. HABBY look up all file of xml type in the “Path_bio” folder (the one indicated in
         the xml project file under the attribute “Path_bio”).  The name are them modified so that the only the name of
         species appears (and not the full path). We set the layout with all the different QLineEdit where the user
         can write the needed data.

         Estimhab model is saved using a function situated in MainWindows_1.py  (frankly, I am not so sure why I did put
         the save function there, but anyway). So the save button just send a signal to MainWindows
         here, which save the data.
        """

        # load the data if it exist already
        self.open_estimhab_hdf5()

        # Data hydrological (QLineEdit in the init of StatModUseful)
        l1 = QLabel(self.tr('<b>Hydrological Data</b>'))
        l2 = QLabel(self.tr('Q [m3/sec]'))
        l3 = QLabel(self.tr('Width [m]'))
        l4 = QLabel(self.tr('Height [m]'))
        l5 = QLabel(self.tr('<b>Median discharge Q50 [m3/sec]</b>'))
        l6 = QLabel(self.tr('<b> Mean substrate size [m] </b>'))
        l7 = QLabel(self.tr('<b> Discharge range [m3/sec] </b> (Qmin and Qmax)'))
        # data fish type
        l10 = QLabel(self.tr('<b>Available Fish and Guild </b>'))
        l11 = QLabel(self.tr('Selected Fish'))

        # create lists with the possible fishes
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_f.itemClicked.connect(self.add_fish)
        self.list_s.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_s.itemClicked.connect(self.remove_fish)
        self.list_f.itemActivated.connect(self.add_fish)
        self.list_s.itemActivated.connect(self.remove_fish)

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # add all fish name from a directory to the QListWidget self.list_f
        self.read_fish_name()

        # send model
        button1 = QPushButton(self.tr('Save and Run ESTIMHAB'), self)
        button1.setStyleSheet("background-color: #31D656")
        button1.clicked.connect(self.save_signal_estimhab.emit)
        button1.clicked.connect(self.run_estmihab)
        # button2 = QPushButton(self.tr('Change folder (fish data)'), self)
        # button2.clicked.connect(self.change_folder)

        #layout
        self.layout3 = QGridLayout()
        self.layout3.addWidget(l1, 0, 0)
        self.layout3.addWidget(l2, 1, 0)
        self.layout3.addWidget(l3, 1, 1)
        self.layout3.addWidget(l4, 1, 2)
        self.layout3.addWidget(self.eq1, 2, 0)
        self.layout3.addWidget(self.ew1, 2, 1)
        self.layout3.addWidget(self.eh1, 2, 2)
        self.layout3.addWidget(self.eq2, 3, 0)
        self.layout3.addWidget(self.ew2, 3, 1)
        self.layout3.addWidget(self.eh2, 3, 2)
        self.layout3.addWidget(l5, 4, 0)
        self.layout3.addWidget(self.eq50, 5, 0)
        self.layout3.addWidget(l6, 4, 1)
        self.layout3.addWidget(self.esub, 5, 1)
        self.layout3.addWidget(l7, 6, 0)
        self.layout3.addWidget(self.eqmin, 7, 0)
        self.layout3.addWidget(self.eqmax, 7, 1)
        self.layout3.addWidget(l10, 8, 0)
        self.layout3.addWidget(l11, 8, 1)
        self.layout3.addWidget(self.list_f, 9, 0)
        self.layout3.addWidget(self.list_s, 9, 1)
        self.layout3.addWidget(button1, 10, 2)
        #self.layout3.addWidget(button2, 10, 0)
        self.setLayout(self.layout3)

    def read_fish_name(self):
        """
        This function reads all latin fish name from the xml files which are contained in the biological directory
        related to estimhab.
        """

        all_xmlfile = glob.glob(os.path.join(self.path_bio_estimhab, r'*.xml'))

        fish_names = []
        for f in all_xmlfile:
            # open xml
            try:
                try:
                    docxml = ET.parse(f)
                    root = docxml.getroot()
                except IOError:
                    print("Warning: the xml file " +f + " could not be open \n")
                    return
            except ET.ParseError:
                print("Warning: the xml file " + f + " is not well-formed.\n")
                return

            # find fish name
            fish_name = root.find(".//LatinName")
            # None is null for python 3
            if fish_name is not None:
                fish_name = fish_name.text.strip()

            # find fish stage
            stage = root.find(".//estimhab/stage")
            # None is null for python 3
            if stage is not None:
                stage = stage.text.strip()
            if stage != 'all_stage':
                fish_name += ' ' + stage

            # add to the list
            item = QListWidgetItem(fish_name)
            self.list_f.addItem(item)

            fish_names.append(fish_name)

        # remember fish name and xml filename
        self.filenames = [fish_names, all_xmlfile]

    def open_estimhab_hdf5(self):
        """
        This function opens the hdf5 data created by estimhab
        """

        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(fname):
            doc = ET.parse(fname)
            root = doc.getroot()
            child = root.find(".//ESTIMHAB_data")
            if child is not None:  # if there is data for ESTIHAB
                fname_h5 = child.text
                path_hdf5 = self.find_path_hdf5_est()
                fname_h5 = os.path.join(path_hdf5, fname_h5)
                if os.path.isfile(fname_h5):
                    file_estimhab = h5py.File(fname_h5, 'r+')
                    # hydrological data
                    dataset_name = ['qmes', 'hmes', 'wmes', 'q50', 'qrange', 'substrate']
                    list_qline = [self.eq1, self.eq2, self.eh1, self.eh2, self.ew1, self.ew2, self.eq50, self.eqmin,
                                  self.eqmax, self.esub]
                    c = 0
                    for i in range(0, len(dataset_name)):
                        dataset = file_estimhab[dataset_name[i]]
                        dataset = list(dataset.values())[0]
                        for j in range(0, len(dataset)):
                            data_str = str(dataset[j])
                            list_qline[c].setText(data_str[1:-1])  # get rid of []
                            c += 1
                    # chosen fish
                    dataset = file_estimhab['fish_type']
                    dataset = list(dataset.values())[0]
                    for i in range(0, len(dataset)):
                        dataset_i = str(dataset[i])
                        self.list_s.addItem(dataset_i[3:-2])
                        self.fish_selected.append(dataset_i[3:-2])

                    file_estimhab.close()
                else:
                    self.msge.setIcon(QMessageBox.Warning)
                    self.msge.setWindowTitle(self.tr("hdf5 ESTIMHAB"))
                    self.msge.setText(self.tr("The hdf5 file related to ESTIMHAB does not exist"))
                    self.msge.setStandardButtons(QMessageBox.Ok)
                    self.msge.show()

    def change_folder(self):
        """
        A small method to change the folder which indicates where is the biological data
        """
        # user find new path
        self.path_bio_estimhab = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        # update list
        self.list_f.clear()
        all_file = glob.glob(os.path.join(self.path_bio_estimhab,r'*.xml'))
        # make it look nicer
        for i in range(0, len(all_file)):
            all_file[i] = all_file[i].replace(self.path_bio_estimhab, "")
            all_file[i] = all_file[i].replace("\\", "")
            all_file[i] = all_file[i].replace(".xml", "")
            item = QListWidgetItem(all_file[i])
            # add them to the menu
            self.list_f.addItem(item)

    def run_estmihab(self):
        """
        A function to execute Estimhab by calling the estimhab function.

        **Technical comment**

        This is the function making the link between the GUI and the source code proper. The source code for Estimhab
        is in src/Estimhab.py.

        This function loads in memory the data given in the graphical interface and call sthe Estimhab model.
        The data could be written by the user now or it could be data which was saved in the hdf5 file before and
        loaded when HABBY was open (and the init function called).  We check that all necessary data is present and
        that the data given makes sense (e.g.,the minimum discharge should not be bigger than the maximal discharge,
        the data should be a float, etc.). We then remove the duplicate fish species (in case the user select one
        specie twice) and the Estimhab model is called. The log is then written (see the paragraph on the log for more
        information). Next, the figures created by Estimmhab are shown. As there is only a short number of outputs
        for Estimhab, we create a figure in all cases (it could be changed by adding a checkbox on the GUI like
        in the Telemac or other hydrological class).

        """
        # prepare data
        try:
            q = [float(self.eq1.text()), float(self.eq2.text())]
            w = [float(self.ew1.text()), float(self.ew2.text())]
            h = [float(self.eh1.text()), float(self.eh2.text())]
            q50 = float(self.eq50.text())
            qrange = [float(self.eqmin.text()), float(self.eqmax.text())]
            substrate = float(self.esub.text())
        except ValueError:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Some data are empty or not float. Cannot run Estimhab"))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return

        # get the list of xml file
        fish_list = []
        fish_name2 = []
        for i in range(0, self.list_s.count()):
            fish_item = self.list_s.item(i)
            fish_item_str = fish_item.text()
            for id, f in enumerate(self.filenames[0]):
                if f == fish_item_str:
                    fish_list.append(os.path.basename(self.filenames[1][id]))
                    fish_name2.append(fish_item_str)


        # check internal logic
        if not fish_list:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("No fish selected. Cannot run Estimhab."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if qrange[0] >= qrange[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Minimum discharge bigger or equal to max discharge. Cannot run Estimhab."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if q[0] == q[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Estimhab needs two different measured discharge."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if h[0] == h[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Estimhab needs two different measured height."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if w[0] == w[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Estimhab needs two different measured width."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if (q[0] > q[1] and h[0] < h[1]) or (q[0] > q[1] and w[0] < w[1]) or (q[1] > q[0] and h[1] < h[0])\
                or (q[1] > q[0] and w[1] < w[0]):
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Discharge, width, and height data are not coherent \n"))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if q[0] < 0 or q[1] < 0 or w[0]< 0 or w[1]< 0 or h[0]< 0 or h[1]< 0 or qrange[0]< 0 or qrange[1]< 0 \
                or substrate < 0 or q50<0:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Negative data found. Could not run estimhab. \n"))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if substrate > 3:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Substrate is too large. Could not run estimhab. \n"))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return

        self.send_log.emit(self.tr('# Run: Estimhab'))

        # check if the discharge range is realistic with the result
        self.qall = [q[0], q[1], qrange[0], qrange[1], q50]
        self.check_all_q()

        # run and save
        path_im = self.find_path_im_est()
        path_txt = self.find_path_text_est()
        fig_opt = output_fig_GUI.  load_fig_option(self.path_prj, self.name_prj)
        sys.stdout = mystdout = StringIO()
        [self.VH, self.SPU] = estimhab.estimhab(q, w, h, q50, qrange, substrate, self.path_bio_estimhab, fish_list,
                                                path_im, True, fig_opt, path_txt, fish_name2)
        self.save_signal_estimhab.emit()

        #log info
        str_found = mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
        self.send_log.emit("py    data = [" + str(q) + ',' + str(w) + ',' + str(h) + ',' + str(q50) +
                           ',' + str(substrate) + ']')
        self.send_log.emit("py    qrange =[" + str(qrange[0]) + ',' + str(qrange[1]) + ']')
        self.send_log.emit("py    path1= os.path.join(os.path.dirname(path_bio),'" + self.path_bio_estimhab + "')")
        fish_list_str = "py    fish_list = ["
        for i in range(0,len(fish_list)):
            fish_list_str += "'" + fish_list[i] + "',"
        fish_list_str = fish_list_str[:-1] + ']'
        self.send_log.emit(fish_list_str)
        self.send_log.emit("py    [VH, SPU] = estimhab.estimhab(data[0], data[1], data[2], data[3] ,"
                           " qrange, data[4], path1, fish_list, '.', True, {}, '.')\n")
        self.send_log.emit("restart RUN_ESTIMHAB")
        self.send_log.emit("restart    q0: " + str(q[0]))
        self.send_log.emit("restart    q1: " + str(q[1]))
        self.send_log.emit("restart    w0: " + str(w[0]))
        self.send_log.emit("restart    w1: " + str(w[1]))
        self.send_log.emit("restart    h0: " + str(h[0]))
        self.send_log.emit("restart    h1: " + str(h[1]))
        self.send_log.emit("restart    q50: " + str(q50))
        self.send_log.emit("restart    sub: " + str(substrate))
        self.send_log.emit("restart    min qrange: " + str(qrange[0]))
        self.send_log.emit("restart    max qrange: " + str(qrange[1]))

        # we always do a figure for estmihab
        if path_im != 'no_path':
            self.show_fig.emit()

if __name__ == '__main__':
    pass
