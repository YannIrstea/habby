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
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QFileDialog, \
    QSpacerItem, QAbstractItemView, QMessageBox, QComboBox, QInputDialog, QFrame
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
import sys
import os
from io import StringIO
from src_GUI import estimhab_GUI
from src import fstress_mod
from src import hdf5_mod
from src_GUI import preferences_GUI


class FstressW(estimhab_GUI.StatModUseful):
    """
    This class provides the graphical user interface for the habby version of Fstress. The Fstress model is described in
    fstress_mod.py. FstressW just loads the data given by the user. He/She can write this data in the GUI or loads it
    from files. The following files are needed:

    * listriv.txt the list of the river (if the file does not exist, the river is called river1).
    * rivqwh.txt discharge, width, height for two discharge (measured) for each rivers.
    * rivdeb.txt max and min discharge.

    FStress inherits from the class StatModUseful. This class is a "parent" class with some functions which are the same
    for estimhab and fstress. Hence, we can re-use these function without re.writing them (a bit like SubHydroW)
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "fstress"
        self.pref_found = False
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_fstress = self.path_prj
        self.defriver = self.tr('Default River')
        self.name_bio = 'pref_fstress.txt'
        self.latin_filename = 'AbbrevLatinNameInvertebrate.txt'
        self.latin_names = []
        self.found_file = []
        self.riv_name = []
        self.save_ok = True  # just to check if the data was saved without problem
        self.all_inv_name = []
        self.pref_inver = []
        self.qrange = []  # for each river [qmin, qmax]
        self.qhw = []  # for each river [[q1,h1,w1],[q2,h2,w2]]
        self.init_iu()

    def init_iu(self):
        """
        This function is used to initialized an instance of the FstressW() class. It is called by __init__().
        It is very similar to EstihabW but it is possible to get more than one river and it can load the data from
        folder.
        """

        # load data
        l001 = QLabel(self.tr(' <b> Load Data From Files</br>'))
        self.loadtxt = QPushButton(self.tr('Text File: listriv.txt'))
        self.loadtxt.clicked.connect(self.load_txt)
        self.loadh5 = QPushButton(self.tr('HABBY File (.hab)'))
        self.loadh5.clicked.connect(self.load_hdf5_fstress)

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # select river
        l002 = QLabel(self.tr('<b> Rivers or Reaches Names </b>'))
        self.riv = QComboBox()
        self.riv.setCurrentIndex(0)
        self.riv.currentIndexChanged.connect(self.show_data_one_river)
        self.addriv = QPushButton(self.tr('Modify river name'))
        self.addriv.clicked.connect(self.modify_name)
        self.errriv = QPushButton(self.tr('Erase river'))
        self.errriv.clicked.connect(self.erase_name)

        # Data hydrological (QLineEdit in the init of StatModUseful)
        l1 = QLabel(self.tr('<b>Hydrological Data</b>'))
        l2 = QLabel(self.tr('Q [m3/sec]'))
        l3 = QLabel(self.tr('Width [m]'))
        l4 = QLabel(self.tr('Height [m]'))
        l7 = QLabel(self.tr('<b> Discharge range [m3/sec]</b> (Qmin and Qmax)'))

        # data invertabrate type
        l10 = QLabel(self.tr('<b>Available invertebrate species</b>'))
        l11 = QLabel(self.tr('Selected Species'))
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_f.itemClicked.connect(self.add_fish)
        self.selected_aquatic_animal_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_aquatic_animal_listwidget.itemClicked.connect(self.remove_fish)
        self.list_f.itemActivated.connect(self.add_fish)
        self.selected_aquatic_animal_listwidget.itemActivated.connect(self.remove_fish)
        self.fishall = QPushButton(self.tr('Select all species'), self)
        self.fishall.clicked.connect(self.add_all_fish)

        # run model
        self.button1 = QPushButton(self.tr('Save and Run FStress'), self)
        self.button1.setStyleSheet("background-color: #47B5E6; color: black")
        self.button1.clicked.connect(self.runsave_fstress)
        # self.button2 = QPushButton(self.tr('Save river data'), self)
        # self.button2.clicked.connect(self.save_river_data)
        spacer = QSpacerItem(1, 20)

        # find the preference file, show the fish name (eith with latin name or abbreviation),
        # and enable self.button2 if found
        self.load_all_fish()
        self.button1.setEnabled(self.pref_found)  # disable as long as no pref is found

        # see if a model was loaded before. if yes, update GUI and variables
        self.was_loaded_before()

        # add river by default
        if self.riv.count() == 0:
            self.riv.addItem(self.defriver)
            self.riv_name.append(self.defriver)
            self.found_file = [[None, None]]

        # empty frame scrolable
        content_widget = QFrame()

        # layout
        self.layout3 = QGridLayout(content_widget)
        self.layout3.addItem(spacer, 0, 3)
        self.layout3.addWidget(l001, 0, 0)
        self.layout3.addWidget(self.loadtxt, 1, 0)
        self.layout3.addWidget(self.loadh5, 1, 1)
        self.layout3.addItem(spacer, 2, 3)
        self.layout3.addWidget(l002, 3, 0)
        self.layout3.addWidget(self.riv, 4, 0)
        self.layout3.addWidget(self.addriv, 4, 1)
        self.layout3.addWidget(self.errriv, 4, 2)
        self.layout3.addWidget(l1, 5, 0)
        self.layout3.addWidget(l2, 6, 0)
        self.layout3.addWidget(l3, 6, 1)
        self.layout3.addWidget(l4, 6, 2)
        self.layout3.addWidget(self.eq1, 7, 0)
        self.layout3.addWidget(self.ew1, 7, 1)
        self.layout3.addWidget(self.eh1, 7, 2)
        self.layout3.addWidget(self.eq2, 8, 0)
        self.layout3.addWidget(self.ew2, 8, 1)
        self.layout3.addWidget(self.eh2, 8, 2)
        self.layout3.addWidget(l7, 9, 0)
        self.layout3.addWidget(self.eqmin, 10, 0)
        self.layout3.addWidget(self.eqmax, 10, 1)
        self.layout3.addWidget(l10, 11, 0)
        self.layout3.addWidget(l11, 11, 1)
        self.layout3.addWidget(self.list_f, 12, 0)
        self.layout3.addWidget(self.selected_aquatic_animal_listwidget, 12, 1)
        self.layout3.addWidget(self.fishall, 13, 0)
        self.layout3.addWidget(self.button1, 13, 2)
        # self.layout3.addWidget(self.button2, 13, 1)

        # add layout
        # self.setLayout(self.layout3)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

    def was_loaded_before(self):
        """
        This function looks in the xml project file is an hdf5 exists already. If yes, it loads this data
        and show it on the GUI.
        """

        # look in the xml project file if an Fstress model exist
        fnamep = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(fnamep):
            self.send_log.emit("The project is not saved. Save the project in the Start tab before saving FStress data.")
            return

        doc = ET.parse(fnamep)
        root = doc.getroot()
        tree = ET.ElementTree(root)
        child = root.find(".//FStress_data")
        # if we do not have already a FStress a model
        if child is None:
            return
        # if not, get the hdf5 name
        else:
            hdf5_infoname = child.text
        # the name is an absolute path, take it. Otherwise, assume that the file in it the path_hdf5
        if os.path.isabs(hdf5_infoname):
            hdf5_path = os.path.dirname(hdf5_infoname)
            hdf5_name = os.path.basename(hdf5_infoname)
        else:
            hdf5_path = self.find_path_hdf5_est()
            hdf5_name = hdf5_infoname

        # if exists, loads the hdf5
        if os.path.isfile(os.path.join(hdf5_path, hdf5_name)):
            [self.qhw, self.qrange, self.riv_name, self.fish_selected] = fstress_mod.read_fstress_hdf5(hdf5_name, hdf5_path)
        else:
            return

        # and show the results on the gui if it counld be loaded without problem
        if len(self.qhw) > 0 and self.qhw != [-99]:
            self.show_data_one_river()
            self.update_list_riv()

    def modify_name(self):
        """
        This function is used to modify the name of a river. It will only be saved if FStress is run. Otherwise it
        is not kept in the data.
        """

        text, ok = QInputDialog.getText(self, self.tr('Change River Name'),
                                        self.tr('Enter the new river or reach name:'))
        if ok:
            self.riv.setItemText(self.riv.currentIndex(), text)
            try:
                self.riv_name[self.riv.currentIndex()] = text
            except IndexError:
                pass

    def save_river_data(self):
        """
        This function save the data for one river based on the data from the GUI (i.e., after modification by the user).
        It can be used to save the data given directely by the user or modified by him.
        """
        riv = self.riv.currentText()
        ind = self.riv.currentIndex()
        if not riv:
            riv = self.riv_name[0]
            ind = 0
        # case where the river was not loaded before
        if len(self.qhw) == 0 and ind == 0:
            self.qrange.append([])
            self.qhw.append([[], []])
        try:
            self.qrange[ind] = [float(self.eqmin.text()), float(self.eqmax.text())]
            self.qhw[ind][0] = [float(self.eq1.text()), float(self.eh1.text()), float(self.ew1.text())]
            self.qhw[ind][1] = [float(self.eq2.text()), float(self.eh2.text()), float(self.ew2.text())]
        except ValueError:
            self.send_log.emit("Error: The hydrological data cannot be converted to float.")
            self.save_ok = False
            return
        path_hdf5 = self.find_path_hdf5_est()
        fstress_mod.save_fstress(path_hdf5, self.path_prj, self.name_prj, self.name_bio, self.path_bio, self.riv_name,
                                 self.qhw,
                                 self.qrange, self.fish_selected)
        self.save_ok = True

    def erase_name(self):
        """
        This function erases the data from the river selected by the user.
        """
        ind = self.riv.currentIndex()
        del self.riv_name[ind]
        del self.found_file[ind]
        if len(self.qrange) > 0:
            del self.qrange[ind]
        if len(self.qhw) > 0:
            del self.qhw[ind]

        if self.riv.count() == 1:
            self.riv.addItem(self.defriver)
            self.riv_name.append(self.defriver)
            self.found_file = [[None, None]]
            self.qrange = []
            self.qhw = []
        self.update_list_riv()
        self.show_data_one_river()
        if not self.riv.count() == 1:
            path_hdf5 = self.find_path_hdf5_est()
            fstress_mod.save_fstress(path_hdf5, self.path_prj, self.name_prj, self.name_bio, self.path_bio, self.riv_name,
                                     self.qhw,
                                     self.qrange, self.fish_selected)

    def add_all_fish(self):
        """
        This function add the name of all known fish (the ones in Pref.txt) to the QListWidget which cintains selected
        fish. This function was copied from the one in SStathab_GUI.py
        """
        items = []
        for index in range(self.list_f.count()):
            items.append(self.list_f.item(index))
        if items:
            for i in range(0, len(items)):
                # avoid to have the same fish multiple times
                if items[i].text() in self.fish_selected:
                    pass
                else:
                    self.selected_aquatic_animal_listwidget.addItem(items[i].text())
                    self.fish_selected.append(items[i].text())

                    # order the list (careful QLIstWidget do not order as sort from list)
                    if self.fish_selected:
                        self.fish_selected.sort()
                        self.selected_aquatic_animal_listwidget.clear()
                        self.selected_aquatic_animal_listwidget.addItems(self.fish_selected)
                        # bold for selected fish
                        font = QFont()
                        font.setItalic(True)
                        for i in range(0, self.list_f.count()):
                            for f in self.fish_selected:
                                if f == self.list_f.item(i).text():
                                    self.list_f.item(i).setFont(font)

    def update_list_riv(self):
        """
        This function is a small function to update the QCombobox which contains the river name
        """
        # update the QComboBox
        self.riv.clear()
        for r in self.riv_name:
            self.riv.addItem(r)
        self.riv.update()

    def load_txt(self):
        """
        In this function, the user select  a listriv.txt file. This files are loaded and written on the GUI.

        Before it was also possible to select just one qhw file. This is still part of the code, but it is not advised
        to do this as the river name tends to mix each other, which is more trouble to maintain that it worths it.
        If a qhw.txt is loaded and if there are more than one qhw.txt in the folder, we ask the user if all files must
        be loaded.

        The needed text files are the following:

        * listriv.txt is a text file with one river name by line
        * rivnameqhw.txt is a text file with minimum two lines which the measured discharge, height and width for
          2 measureement (necessary)
        * rivernamedeb.txt is a text file which has two lines. The first line is the minimum discharge and the second is
          the maximum discharge to be modelled. It is chosen by the user (necessary to run, but can be given by the user
          on the GUI)

        All data should be in SI unit. We save all the data in the input folder at the end.
        """

        # open file
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_fstress, os.getenv('HOME'))[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            return

        self.found_file = []
        self.riv_name = []
        self.qhw = []
        self.qrange = []

        # see which type of file we have and get the name of all the files
        filename = os.path.basename(filename_path)
        self.path_fstress = os.path.dirname(filename_path)

        # for listriv file
        if filename.lower() == 'listriv.txt':
            # get the river name
            with open(filename_path, 'rt') as f:
                for line in f:
                    if len(line) > 0:
                        self.riv_name.append(line.strip())
            # add the file names (deb and qhw.txt)
            for r in self.riv_name:
                f_found = [None, None]
                # discharge range
                debfilename = r + 'deb.txt'
                if os.path.isfile(os.path.join(self.path_fstress, debfilename)):
                    f_found[1] = debfilename
                elif os.path.isfile(os.path.join(self.path_fstress, r + 'DEB.TXT')):
                    debfilename = r[:-7] + 'DEB.TXT'
                    f_found[1] = debfilename
                else:
                    f_found[1] = None
                # qhw
                qhwname = r + 'qhw.txt'
                if os.path.isfile(os.path.join(self.path_fstress, qhwname)):
                    f_found[0] = qhwname
                elif os.path.isfile(os.path.join(self.path_fstress, r + 'QHW.TXT')):
                    qhwname = r + 'QHW.TXT'
                    f_found[0] = qhwname
                else:
                    self.send_log.emit('Error: qhw file not found for river ' + r + '.')
                    return
                self.found_file.append(f_found)

        # for qhw.txt file ---NOT USED ANYMORE "officialy", but can still be useful to let it open
        # careful there are some bugs if various qwh are loaded one after the others.
        elif filename[-7:].lower() == 'qhw.txt':
            files_all = os.listdir(self.path_fstress)
            nb_found = 0
            for f in files_all:
                if f[-7:].lower() == 'qhw.txt':
                    # get the name of the file and the river name
                    self.riv_name.append(f[:-7])
                    debfilename = f[:-7] + 'deb.txt'
                    if os.path.isfile(os.path.join(self.path_fstress, debfilename)):
                        found_f = [f, debfilename]
                    elif os.path.isfile(os.path.join(self.path_fstress, f[:-7] + 'DEB.TXT')):
                        debfilename = f[:-7] + 'DEB.TXT'
                        found_f = [f, debfilename]
                    else:
                        found_f = [f, None]
                    self.found_file.append(found_f)

                    # if we have more than one qhw, ask the user if we shoud all load them
                    if nb_found == 0:
                        self.msge.setIcon(QMessageBox.Question)
                        self.msge.setWindowTitle(self.tr("Load all files?"))
                        self.msge.setText(self.tr("We found more than one qhw file. Do you want to load all rivers?"))
                        self.msge.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                        self.msge.setDefaultButton(QMessageBox.Yes)
                        retval = self.msge.exec_()
                        self.msge.show()
                        if retval == QMessageBox.No:
                            self.msge.close()
                            if f == filename:
                                break
                            else:
                                self.riv_name = []
                                self.qhw = []
                                self.qrange = []
                        else:
                            self.msge.close()
                    nb_found += 1

        else:
            self.send_log.emit(self.tr('Error: Only listriv file are accepted. Read Fstress documentation for '
                                       'more info.'))
            return

        if len(self.riv_name) == 0:
            self.send_log.emit('Warning: No river found in files.')
            return

        # update the list with the new river
        self.update_list_riv()

        # load the data for all the selected rivers and save it in an hdf5
        for i in range(0, len(self.riv_name)):
            self.load_data_fstress(i)
        path_hdf5 = self.find_path_hdf5_est()
        fstress_mod.save_fstress(path_hdf5, self.path_prj, self.name_prj, self.name_bio, self.path_bio, self.riv_name,
                                 self.qhw,
                                 self.qrange, self.fish_selected)

        # copy the input in the input folder
        input_folder = self.find_path_input_est()
        new_dir = os.path.join(input_folder, 'input_fstress')
        all_files = os.listdir(self.path_fstress)
        paths = [self.path_fstress] * len(all_files)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        hdf5_mod.copy_files(all_files, paths, new_dir)

        # show the data for the selected river
        self.show_data_one_river()

    def load_hdf5_fstress(self):
        """
        This function loads an hdf5 file in the fstress format and add it to the project. This hdf5 file was not part of
        the project previously.
        """

        # open file
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_fstress, os.getenv('HOME'))[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            return

        # see which type of file we have and get the name of all the files
        hdf5_name = os.path.basename(filename_path)
        hdf5_path = os.path.dirname(filename_path)

        # loads this new hdf5
        [self.qhw, self.qrange, self.riv_name, self.fish_selected] = fstress_mod.read_fstress_hdf5(hdf5_name, hdf5_path)

        # show the results on the gui
        if len(self.qhw) > 0 and self.qhw != [-99]:
            self.show_data_one_river()

        # save it in a new name and links this copied hdf5 to the project
        path_hdf5 = self.find_path_hdf5_est()
        fstress_mod.save_fstress(path_hdf5, self.path_prj, self.name_prj, self.name_bio, self.path_bio, self.riv_name,
                                 self.qhw,
                                 self.qrange, self.fish_selected)

    def show_data_one_river(self):
        """
        This function shows the qhw and the [qmin, qmax] data on the GUI for the river selected by the user.
        The river must have been loaded before. It also show the selected fish
        """

        riv = self.riv.currentText()
        ind = self.riv.currentIndex()
        if not riv:
            riv = self.riv_name[0]
            ind = 0

        if len(self.qrange) - 1 >= ind and len(self.qrange[ind]) == 2:
            qmin = self.qrange[ind][0]
            qmax = self.qrange[ind][1]
            self.eqmin.setText(str(qmin))
            self.eqmax.setText(str(qmax))
        else:
            self.eqmin.clear()
            self.eqmax.clear()

        if len(self.qhw) - 1 >= ind:
            data_qhw = self.qhw[ind]
            self.eq1.setText(str(data_qhw[0][0]))
            self.eh1.setText(str(data_qhw[0][1]))
            self.ew1.setText(str(data_qhw[0][2]))
            self.eq2.setText(str(data_qhw[1][0]))
            self.eh2.setText(str(data_qhw[1][1]))
            self.ew2.setText(str(data_qhw[1][2]))

        else:
            self.eq1.clear()
            self.ew1.clear()
            self.eh1.clear()
            self.eq2.clear()
            self.ew2.clear()
            self.eh2.clear()

        for ind, f in enumerate(self.fish_selected):
            for ind2 in range(0, self.list_f.count()):
                item = self.list_f.item(ind2)
                if f == item.text():
                    self.list_f.setCurrentItem(item)
                    self.add_fish()

    def load_data_fstress(self, rind):
        """
        This function loads the data for fstress and add it to the variable self.qrange and self.qhw for the river
        rind.
        :param rind: The indices of the river is self.river_name. So it is which river should be loaded
        """

        # river and file name
        ind = rind
        riv = self.riv_name[ind]

        if not riv:
            riv = self.riv_name[0]
            ind = 0
        if len(self.found_file) == 0 or self.found_file[0][0] is None:
            self.eqmin.clear()
            self.eqmax.clear()
            self.eq1.clear()
            self.ew1.clear()
            self.eh1.clear()
            self.eq2.clear()
            self.ew2.clear()
            self.eh2.clear()
            return

        fnames = self.found_file[ind]

        # discharge range
        if fnames[1] is not None:
            fname_path = os.path.join(self.path_fstress, fnames[1])
            if os.path.isfile(fname_path):
                with open(fname_path, 'rt') as f:
                    data_deb = f.read()
                data_deb = data_deb.split()
                try:
                    data_deb = list(map(float, data_deb))
                except ValueError:
                    self.send_log.emit('Error: Data cannot be converted to float in deb.txt.')
                    return
                qmin = min(data_deb)
                qmax = max(data_deb)

                self.qrange.append([qmin, qmax])
            else:
                self.send_log.emit('Warning: deb.txt file not found.(1)')
                self.qrange.append([])

        else:
            self.send_log.emit('Warning: deb.txt file not found.(2)')
            self.qrange.append([])

        # qhw
        fname_path = os.path.join(self.path_fstress, fnames[0])
        if os.path.isfile(fname_path):
            with open(fname_path, 'rt') as f:
                data_qhw = f.read()
            data_qhw = data_qhw.split()
            # useful to pass in float to check taht we have float
            try:
                data_qhw = list(map(float, data_qhw))
            except ValueError:
                self.send_log.emit('Error: Data cannot be concerted to float in qhw.txt.')
                return
            if len(data_qhw) < 6:
                self.send_log.emit('Error: FStress needs at least two discharge measurement.')
                return
            if len(data_qhw) % 3 != 0:
                self.send_log.emit('Error: One discharge measurement must be composed of three data (q,w, and h).')
                return

            self.qhw.append([[data_qhw[0], data_qhw[1], data_qhw[2]], [data_qhw[3], data_qhw[4], data_qhw[5]]])
        else:
            self.send_log.emit('Error: qhw.txt file not found.(2)')
            self.qhw.append([])

    def load_all_fish(self):
        """
        This function find the preference file, load the preference coefficient for each invertebrate and show their name
        on QListWidget. It is run at the start of the program. FStress cannot be run as long as a preference file is not
        found.
        """

        sys.stdout = mystdout = StringIO()
        [self.pref_inver, self.all_inv_name] = fstress_mod.read_pref(self.path_bio, self.name_bio)
        sys.stdout = sys.__stdout__
        if self.pref_inver != [-99]:
            self.pref_found = True
        else:
            return

        # log
        str_found = mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])

        # see if we can use latin name instead of acronym
        filename_bio = os.path.join(self.path_bio, self.latin_filename)
        if not os.path.isfile(filename_bio):
            self.send_log.emit('Warning: Latin name of invertebrate could not be read (1).')
            # show the fish name as acronym
            self.list_f.addItems(self.all_inv_name)
        else:
            with open(filename_bio, 'rt') as f:
                data_name = f.read()
            data_name = data_name.split('\n')
            data_name = [x for x in data_name if x.strip()]  # erase empty lines or lines with just tab
            for d in range(0, len(data_name)):
                data_name[d] = data_name[d].split('\t')
                if len(data_name[d]) != 2:
                    self.list_f.addItems(self.all_inv_name)
                    self.send_log.emit('Warning: Latin name of invertebrate could not be read (2).')
                    return
            data_name = np.array(data_name)
            names_latin = []
            for abbrev in self.all_inv_name:
                name_latin_here = data_name[data_name[:, 0] == abbrev]
                if len(name_latin_here) > 1:
                    # each name is repeated many time in the data but there are the same name,
                    # so let's just take the first
                    name_latin_here = abbrev + ' ' + name_latin_here[0, 1]
                    names_latin.append(name_latin_here)
                else:
                    names_latin.append(abbrev)
            self.list_f.addItems(names_latin)
            self.latin_names = names_latin

    def runsave_fstress(self):
        """
        This function save the data related to FStress and call the model Fstress. It is the method which makes the
        link between the GUI and fstress_mod.py.
        """

        self.send_log.emit(self.tr('#  Running: FStress'))

        self.save_river_data()
        if not self.save_ok:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("FStress"))
            self.msge.setText(self.tr("FStress data could not be transformed to float. Cannot run FStress."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return

        # get the name of the selected fish
        fish_list = []
        for i in range(0, self.selected_aquatic_animal_listwidget.count()):
            fish_item = self.selected_aquatic_animal_listwidget.item(i)
            # if latin name
            fish_item_latin = fish_item.text()
            foundlatin = False
            for idx, d in enumerate(self.latin_names):
                if d == fish_item_latin:
                    fish_list.append(self.all_inv_name[idx])
                    foundlatin = True
                    break
            # if abbrev
            if not foundlatin:
                fish_item_str = fish_item.text()
                fish_list.append(fish_item_str)

        # check internal logic ( a bit like estihab)
        if not fish_list:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run FStress"))
            self.msge.setText(self.tr("No fish selected. Cannot run FStress."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return

        for i in range(0, len(self.riv_name)):
            if len(self.qrange[i]) < 2:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FStress"))
                self.msge.setText(self.tr("No discharge range. Cannot run FStress."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return
            if self.qrange[i][0] >= self.qrange[i][1]:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FStress"))
                self.msge.setText(self.tr("Minimum dicharge bigger or equal to max discharge. Cannot run FStress."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return
            if self.qhw[i][1][0] == self.qhw[i][0][0]:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FStress"))
                self.msge.setText(self.tr("FStress needs two different measured discharge."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return
            if self.qhw[i][0][2] == self.qhw[i][1][2]:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FStress"))
                self.msge.setText(self.tr("FStress needs two different measured height."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return
            if self.qhw[i][0][1] == self.qhw[i][1][1]:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FStress"))
                self.msge.setText(self.tr("FStress needs two different measured width."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return
            if any(i < 0 for i in self.qhw[i][0]) or any(i < 0 for i in self.qhw[i][1]) \
                    or self.qrange[i][0] < 0 or self.qrange[i][1] < 0:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FStress"))
                self.msge.setText(self.tr("FStress do not accept negative value"))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return
            # check than one qhw is bigger than the other qhw
            if (self.qhw[i][0][0] > self.qhw[i][1][0] and self.qhw[i][0][1] < self.qhw[i][1][1]) \
                    or (self.qhw[i][0][0] > self.qhw[i][1][0] and self.qhw[i][0][2] < self.qhw[i][1][2]) \
                    or (self.qhw[i][1][0] > self.qhw[i][0][0] and self.qhw[i][1][1] < self.qhw[i][0][1]) \
                    or (self.qhw[i][1][0] > self.qhw[i][0][0] and self.qhw[i][1][2] < self.qhw[i][0][2]):
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("run FSTRESS"))
                self.msge.setText(self.tr("Discharge, width, and height data are not coherent \n"))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
                return

            # check if the discharge range is realistic with the result
            self.qall = [self.qhw[i][0][0], self.qhw[i][1][0], self.qrange[i][0], self.qrange[i][1], -99]
            self.check_all_q()

        # run
        sys.stdout = self.mystdout = StringIO()
        [vh, qmod, inv_select] = fstress_mod.run_fstress(self.qhw, self.qrange, self.riv_name, fish_list, self.pref_inver,
                                                         self.all_inv_name, self.name_prj, self.path_prj)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if isinstance(qmod, int):
            if qmod == -99:
                return

        # find the latin name again (might be different as FStress might have failed on some species)
        inv_select_latin = []
        for n in inv_select:
            for idx, n2 in enumerate(self.all_inv_name):
                if n == n2:
                    inv_select_latin.append(self.latin_names[idx])
                    break

        # figures
        self.path_im = self.find_path_im_est()
        project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
        fstress_mod.figure_fstress(qmod, vh, inv_select_latin, self.path_im, self.riv_name, project_preferences)
        plt.show()
        #self.show_fig.emit()
        path_txt = self.find_path_text_est()

        # text file
        # abbreviation written in the textfile so no space in invertebrate name
        fstress_mod.write_txt(qmod, vh, inv_select, path_txt, self.riv_name)

        # log
        str_found = self.mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
        strhydro = np.array_repr(np.array(self.qhw))
        strhydro = strhydro[6:-1]
        self.send_log.emit("py    data = " + strhydro)
        strhydro2 = np.array_repr(np.array(self.qrange))
        strhydro2 = strhydro2[6:-1]
        self.send_log.emit("py    qrange =" + strhydro2)
        fish_list_str = "py    fish_list = ["
        for i in range(0, len(fish_list)):
            fish_list_str += "'" + fish_list[i] + "',"
        fish_list_str = fish_list_str[:-1] + ']'
        self.send_log.emit(fish_list_str)
        riv_name_str = "py    riv_name = ["
        for i in range(0, len(self.riv_name)):
            riv_name_str += "'" + self.riv_name[i] + "',"
        riv_name_str = riv_name_str[:-1] + ']'
        self.send_log.emit(riv_name_str)
        self.send_log.emit("py    [pref_inver, all_inv_name] = fstress.read_pref(path_bio, 'pref_fstress.txt')")
        self.send_log.emit("py    [vh, qmod, inv_select] = fstress.run_fstress(data, qrange, riv_name, fish_list, "
                           "pref_inver, all_inv_name, name_prj, path_prj)")
        self.send_log.emit("py    fstress.figure_fstress(qmod, vh, inv_select,'.', riv_name)")
        self.send_log.emit("restart RUN_FSTRESS")
        self.send_log.emit("restart    path_fstress: " + self.path_fstress)


if __name__ == '__main__':
    pass
