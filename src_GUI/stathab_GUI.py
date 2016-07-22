from io import StringIO
import os
from PyQt5.QtCore import QTranslator, pyqtSignal, Qt, QModelIndex
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,\
    QListWidgetItem, QMessageBox, QCheckBox
from PyQt5.QtGui import QPixmap
import time
import sys
from src import stathab_c
import xml.etree.ElementTree as ET


class StathabW(QWidget):
    """
    A class to load the widget controlling the Stathab model
    """

    send_log = pyqtSignal(str, name='send_log')
    show_fig = pyqtSignal()

    def __init__(self, path_prj, name_prj):

        super().__init__()

        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_im = os.path.join(self.path_prj, 'figures_habby')
        self.path_bio_stathab = './/biologie'
        self.fish_selected = []
        self.dir_name = self.tr("No directory selected")
        self.mystdout = StringIO()
        self.msge = QMessageBox()
        self.firstitemreach = []  # the first item of a reach
        self.list_file = QListWidget()
        self.list_needed = QListWidget()
        self.list_s = QListWidget()
        self.list_re = QListWidget()
        self.list_f = QListWidget()
        # name of all the file
        self.listrivname = 'listriv.txt'
        self.end_file_reach = ['deb.txt', 'qhw.txt', 'gra.txt', 'dis.txt']
        self.name_file_allreach = ['bornh.txt', 'bornv.txt', 'borng.txt', 'Pref.txt']
        self.hdf5_name = self.tr('No hdf5 selected')
        self.mystathab = stathab_c.Stathab(self.name_prj, self.path_prj)
        self.dir_hdf5 = self.path_prj
        self.typeload = 'txt'  # txt or hdf5

        self.init_iu()

    def init_iu(self):

        # see if a directory was selected before for Stathab
        # see if an hdf5 was selected before for Stathab
        # if both are there, reload as the last time
        filename_prj = os.path.join(self.path_prj,self.name_prj + '.xml')
        if os.path.isfile(filename_prj):
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//Stathab")
            if child is not None:
                dirxml = root.find(".//DirStathab")
                if dirxml is not None:
                    self.dir_name = dirxml.text
                hdf5xml = root.find(".//hdf5Stathab")
                if hdf5xml is not None:
                    self.hdf5_name = hdf5xml.text
                typeloadxml = root.find(".//TypeloadStathab")
                if typeloadxml is not None:
                    self.typeload = typeloadxml.text

        # check if there is a path where to save the figures
        if os.path.isfile(filename_prj):
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//" + 'Path_Figure')
            if child is not None:
                self.path_im = child.text
        if not os.path.exists(self.path_im):
            os.makedirs(self.path_im)

        # prepare QLabel
        self.l1 = QLabel(self.tr('Stathab Input Files (.txt)'))
        loadb = QPushButton(self.tr("Select directory"))
        if len(self.dir_name) > 30:
            self.l0 = QLabel('...' + self.dir_name[-30:])
        else:
            self.l0 = QLabel(self.dir_name)
        l2 = QLabel(self.tr("Reaches"))
        self.l3 = QLabel(self.tr("File found"))
        self.l4 = QLabel(self.tr("File still needed"))
        l5 = QLabel(self.tr("Available Fish"))
        l6 = QLabel(self.tr("Selected Fish"))
        self.fishall = QCheckBox(self.tr('Select all fishes'), self)
        loadhdf5b = QPushButton(self.tr("Load data from hdf5"))
        self.runb = QPushButton(self.tr("Save and run Stathab"))
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # connect method with list
        loadb.clicked.connect(self.select_dir)
        loadhdf5b.clicked.connect(self.select_hdf5)
        self.runb.clicked.connect(self.run_stathab_gui)
        self.list_re.itemClicked.connect(self.reach_selected)
        self.list_f.itemClicked.connect(self.add_fish)
        self.list_s.itemClicked.connect(self.remove_fish)
        self.fishall.stateChanged.connect(self.add_all_fish)

        # update label and list
        if self.dir_name != "No directory selected" and self.typeload == 'txt':
            if os.path.isdir(self.dir_name):
                self.load_from_txt_gui()
                if not self.mystathab.load_ok:
                    self.msge.setIcon(QMessageBox.Warning)
                    self.msge.setWindowTitle(self.tr("Stathab"))
                    self.msge.setText(self.mystdout.getvalue())
                    self.msge.setStandardButtons(QMessageBox.Ok)
                    self.msge.show()
            else:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("Stathab"))
                self.msge.setText(self.tr("Stathab: The selected directory for stathab does not exist."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
        if self.hdf5_name != 'No hdf5 selected' and self.typeload == 'hdf5':
            if os.path.isfile(self.hdf5_name):
                self.load_from_hdf5_gui()
                if not self.mystathab.load_ok:
                    self.msge.setIcon(QMessageBox.Warning)
                    self.msge.setWindowTitle(self.tr("Stathab"))
                    self.msge.setText(self.mystdout.getvalue())
                    self.msge.setStandardButtons(QMessageBox.Ok)
                    self.msge.show()
            else:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("Stathab"))
                self.msge.setText(self.tr("Stathab: The selected hdf5 file for stathab does not exist."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()

        # Layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.l1, 0, 0)
        self.layout.addWidget(loadb, 0, 2)
        self.layout.addWidget(self.l0, 0, 1)
        self.layout.addWidget(l2, 1, 0)
        self.layout.addWidget(self.l3, 1, 1)
        self.layout.addWidget(self.l4, 1, 2)
        self.layout.addWidget(self.list_re, 2, 0)
        self.layout.addWidget(self.list_file, 2, 1)
        self.layout.addWidget(self.list_needed, 2, 2)
        self.layout.addWidget(l5, 3, 0)
        self.layout.addWidget(l6, 3, 1)
        self.layout.addWidget(loadhdf5b, 4, 2)
        self.layout.addWidget(self.list_f, 4, 0, 2,1)
        self.layout.addWidget(self.list_s, 4, 1, 2, 1)
        self.layout.addWidget(self.runb, 5, 2)
        self.layout.addWidget(self.fishall, 6, 1)
        self.layout.addWidget(self.cb, 6, 2)
        self.setLayout(self.layout)

    def select_dir(self):
        """
        The function to select the directory and find the files to laod stathab from txt files
        call load_from_txt_gui() when done
        :return:
        """
        # get the directory
        self.dir_name = QFileDialog.getExistingDirectory()
        if self.dir_name == '':  # cancel case
            self.send_log.emit("Warning: No selected directory for stathab\n")
            return

        # clear all list
        self.mystathab = stathab_c.Stathab(self.name_prj, self.path_prj)
        self.list_re.clear()
        self.list_file.clear()
        self.list_s.clear()
        self.list_needed.clear()
        self.list_f.clear()
        self.fish_selected = []
        self.firstitemreach = []

        # save the directory in the project file
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Error: No project saved. Please create a project first in the General tab.')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//Stathab")
            if child is None:
                stathab_element = ET.SubElement(root, "Stathab")
                dirxml = ET.SubElement(stathab_element, "DirStathab")
                dirxml.text = self.dir_name
                typeload = ET.SubElement(stathab_element, "TypeloadStathab")  # last load from txt or hdf5?
                typeload.text = 'txt'
            else:
                dirxml = root.find(".//DirStathab")
                if child is None:
                    dirxml = ET.SubElement(child, "DirStathab")
                    dirxml.text = self.dir_name
                else:
                    dirxml.text = self.dir_name
                dirxml = root.find(".//TypeloadStathab")
                if child is None:
                    dirxml = ET.SubElement(child, "TypeloadStathab")   # last load from txt or hdf5?
                    dirxml.text = 'txt'
                else:
                    dirxml.text = 'txt'
            doc.write(filename_prj)

            # fill the lists with the existing files
            self.load_from_txt_gui()

    def load_from_txt_gui(self):
        """
        The function which update the different lists to reflect the found files
        and which load the txt file using stathab data
        :return:
        """

        # update the labels
        if len(self.dir_name) > 30:
            self.l0.setText('...' + self.dir_name[-30:])
        else:
            self.l0.setText(self.dir_name)
        self.l1.setText(self.tr('Stathab Input Files (.txt)'))
        self.l3.setText(self.tr("File found"))
        self.l4.setText(self.tr("File still needed"))

        # read the reaches name
        sys.stdout = self.mystdout = StringIO()
        name_reach = stathab_c.load_namereach(self.dir_name, self.listrivname)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if name_reach == [-99]:
            self.list_re.clear()
            return
        for r in range(0, len(name_reach)):
            itemr = QListWidgetItem(name_reach[r])
            self.list_re.addItem(itemr)

        # see if the needed file are available
        # by reach
        c = -1
        for r in range(0, len(name_reach)):
            for i in range(0, len(self.end_file_reach)):
                file = os.path.join(self.dir_name, name_reach[r]+self.end_file_reach[i])
                if os.path.isfile(file):
                    itemf = QListWidgetItem(name_reach[r]+self.end_file_reach[i])
                    self.list_file.addItem(itemf)
                    c += 1
                else:
                    itemf = QListWidgetItem(name_reach[r]+self.end_file_reach[i])
                    self.list_needed.addItem(itemf)
                if i == 0: # note the first item to be able to highlight it afterwards
                    self.firstitemreach.append([itemf, c])

            self.list_file.addItem('----------------')
            c += 1

        # all reach
        # first choice> Pref.txt in dir_name is used.
        # default choice: Pref.txt in the biologie folder.
        for i in range(0,len(self.name_file_allreach)):
            file = os.path.join(self.dir_name, self.name_file_allreach[i])
            if os.path.isfile(file):
                itemf = QListWidgetItem(self.name_file_allreach[i])
                self.list_file.addItem(itemf)
                itemf.setBackground(Qt.lightGray)
                # if a custom Pref.txt is present
                if i == len(self.name_file_allreach):
                    self.path_bio_stathab = self.dir_name
            else:
                # usual case: a file is missing
                if i != len(self.name_file_allreach)-1:
                    self.list_needed.addItem(self.name_file_allreach[i])
                # if Pref.txt is missing, let's use the default file
                else: # by default the biological model in the biology folder
                    file = os.path.join(self.path_bio_stathab, self.name_file_allreach[i])
                    if os.path.join(file):
                        itemf = QListWidgetItem(self.name_file_allreach[i] + ' (default)')
                        self.list_file.addItem(itemf)
                        itemf.setBackground(Qt.lightGray)
                    else:
                        self.list_needed.addItem(self.name_file_allreach[i])

        # read the available fish
        sys.stdout = self.mystdout = StringIO()
        [name_fish, blob] = stathab_c.load_pref(self.name_file_allreach[-1], self.path_bio_stathab)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if name_fish == [-99]:
            return
        for r in range(0, len(name_fish)):
            self.list_f.addItem(name_fish[r])

        # load now the text data
        if self.list_needed.count() > 0:
            self.send_log.emit('# Found part of the STATHAB files. Need re-load')
            return
        self.list_needed.addItem('All files found')
        self.send_log.emit('# Found all STATHAB files. Load Now.')
        sys.stdout = self.mystdout = StringIO()
        self.mystathab.load_stathab_from_txt('listriv.txt', self.end_file_reach, self.name_file_allreach, self.dir_name)
        self.mystathab.create_hdf5()

        # log info
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if not self.mystathab.load_ok:
            self.send_log.emit('Error: Could not load stathab data.\n')
            return
        var1 = 'py    var1 = ['
        for i in range(0, len(self.end_file_reach)):
            var1 += "'" + self.end_file_reach[i] + "',"
        var1 = var1[:-1] + "]"
        self.send_log.emit(var1)
        var2 = 'py    var2 = ['
        for i in range(0, len(self.end_file_reach)):
            var2 += "'" + self.name_file_allreach[i] + "',"
        var2 = var2[:-1] + "]"
        self.send_log.emit(var2)
        self.send_log.emit("py    dir_name = '" + self.dir_name + "'")
        self.send_log.emit('py    mystathab = stathab_c.Stathab(name_prj, path_prj)')
        self.send_log.emit("py    mystathab.load_stathab_from_txt('listriv.txt', var1, var2, dir_name)")
        self.send_log.emit("py    self.mystathab.create_hdf5()")
        self.send_log.emit('restart LOAD_STATHAB_FROM_TXT_AND_CREATE_HDF5')

    def select_hdf5(self):
        """
        A function to select the hdf5 and write the data to the xml file
        call load_from_hdf5_gui when finished
        :return:
        """
        self.send_log.emit('# Load stathab file from hdf5.')

        # load the filename
        self.hdf5_name = QFileDialog.getOpenFileName()[0]
        self.dir_hdf5 = os.path.dirname(self.hdf5_name)
        if self.hdf5_name == '':  # cancel case
            self.send_log.emit("Warning: No selected hdf5 file for stathab\n")
            return
        blob, ext = os.path.splitext(self.hdf5_name)
        if ext != '.h5':
            self.send_log.emit("Warning: The file should be of hdf5 type.\n")

        # save the directory in the project file
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Error: No project saved. Please create a project first in the General tab.')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//Stathab")
            if child is None:
                stathab_element = ET.SubElement(root, "Stathab")
                dirxml = ET.SubElement(stathab_element, "hdf5Stathab")
                dirxml.text = self.dir_name
                typeload = ET.SubElement(stathab_element, "TypeloadStathab")  # last load from txt or hdf5?
                typeload.text = 'hdf5'
            else:
                dirxml = root.find(".//hdf5Stathab")
                if dirxml is None:
                    dirxml = ET.SubElement(child, "hdf5Stathab")
                    dirxml.text = self.hdf5_name
                else:
                    dirxml.text = self.hdf5_name
                typeload = root.find(".//TypeloadStathab")
                if typeload is None:
                    typeload = ET.SubElement(child, "TypeloadStathab")   # last load from txt or hdf5?
                    typeload.text = 'hdf5'
                else:
                    typeload.text = 'hdf5'
            doc.write(filename_prj)


        # clear list of the GUI
        self.mystathab = stathab_c.Stathab(self.name_prj, self.path_prj)
        self.list_re.clear()
        self.list_file.clear()
        self.list_s.clear()
        self.list_needed.clear()
        self.fish_selected = []
        self.firstitemreach = []

        # load hdf5 data
        self.load_from_hdf5_gui()

    def load_from_hdf5_gui(self):
        """
        A function to load the data from an hdf5 file, using function from stathab1.py
        :return:
        """
        # update QLabel
        self.l1.setText(self.tr('Stathab Input Files (.hdf5)'))
        if len(self.dir_name) > 30:
            self.l0.setText(self.hdf5_name[-30:])
        else:
            self.l0.setText(self.hdf5_name)
        self.l3.setText(self.tr("Data found"))
        self.l4.setText(self.tr("Data still needed"))

        # load data
        self.send_log.emit('# load stathab from hdf5.')
        sys.stdout = self.mystdout = StringIO()
        self.mystathab.load_stathab_from_hdf5()

        # log info
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if not self.mystathab.load_ok:
            self.send_log.emit('Error: Data from  hdf5 not loaded.\n')
            return
        self.send_log.emit('py    mystathab = stathab_c.Stathab(name_prj, path_prj)')
        self.send_log.emit('py    mystathab.load_stathab_from_hdf5()')
        self.send_log.emit('restart LOAD_STATHAB_FROM_HDF5')

        # update list with name reach
        if len(self.mystathab.name_reach) == 0:
            self.send_log.emit('Error: No name of reach found. \n')
            return
        for r in range(0, len(self.mystathab.name_reach)):
            itemr = QListWidgetItem(self.mystathab.name_reach[r])
            self.list_re.addItem(itemr)

        # update list with name of data
        data_reach = [self.mystathab.qlist, self.mystathab.qwh, self.mystathab.disthmes,
                self.mystathab.qhmoy, self.mystathab.dist_gran]
        data_reach_str = ['qlist', 'qwh', 'dishhmes', 'qhmoy', 'dist_granulo']
        c = -1
        for r in range(0, len(self.mystathab.name_reach)):
            for i in range(0, 5):
                if data_reach[i]:
                    itemr = QListWidgetItem(data_reach_str[i])
                    self.list_file.addItem(itemr)
                    c +=1
                else:
                    self.list_needed.addItem(data_reach_str[i])
                if i == 0:  # note the first item to be able to highlight it afterwards
                    self.firstitemreach.append([itemr, c])
            c += 1
            self.list_file.addItem('----------------')

        # update list with bornes of velocity, height and granola
        lim_str = ['limits height', 'limits velocity', 'limits granulometry']
        for i in range(0, 3):
            if len(self.mystathab.lim_all[i]) > 1:
                itemr = QListWidgetItem(lim_str[i])
                self.list_file.addItem(itemr)
                itemr.setBackground(Qt.lightGray)
            else:
                self.list_needed.addItem(lim_str[i])

        # see if a preference file is available in the same folder than the hdf5 file
        preffile = os.path.join(self.dir_hdf5, self.name_file_allreach[3])
        if os.path.isfile(preffile):
            self.path_bio_stathab = self.dir_hdf5
            itemp = QListWidgetItem(self.name_file_allreach[3])
            self.list_file.addItem(itemp)
            itemp.setBackground(Qt.lightGray)
        else:
            itemp = QListWidgetItem(self.name_file_allreach[3] + '(default)')
            self.list_file.addItem(itemp)
            itemp.setBackground(Qt.lightGray)

        # read the available fish
        sys.stdout = self.mystdout = StringIO()
        [name_fish, blob] = stathab_c.load_pref(self.name_file_allreach[3], self.path_bio_stathab)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if name_fish == [-99]:
            return
        for r in range(0, len(name_fish)):
            self.list_f.addItem(name_fish[r])

        # final check
        if self.list_needed.count() == 0:
            self.list_needed.addItem('All hdf5 data found')
            self.send_log.emit('# Found all STATHAB files.')
        else:
            self.send_log.emit('# Found part of the STATHAB files. Need to re-load.')
            return

    def reach_selected(self):
        """
        A function whicjh indcates which files are linked with which reach
        :return:
        """
        [item_sel, r] = self.firstitemreach[self.list_re.currentRow()]
        self.list_file.setCurrentRow(r)
        self.list_file.scrollToItem(item_sel)

    def send_err_log(self):
        """
        Send the error and warning to the logs
        The stdout was redirected to self.mystdout
        :return:
        """
        str_found = self.mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])

    def add_fish(self):
        items = self.list_f.selectedItems()
        if items:
            for i in range(0,len(items)):
                # avoid to have the same fish multiple times
                if items[i].text() in self.fish_selected:
                    pass
                else:
                    self.list_s.addItem(items[i].text())
                    self.fish_selected.append(items[i].text())

    def remove_fish(self):
        item = self.list_s.takeItem(self.list_s.currentRow())
        self.fish_selected.remove(item.text())
        item = None

    def add_all_fish(self):
        """
        Add all known fish
        :return:
        """
        if self.fishall.isChecked():

            items = []
            for index in range(self.list_f.count()):
                items.append(self.list_f.item(index))
            if items:
                for i in range(0, len(items)):
                    # avoid to have the same fish multiple times
                    if items[i].text() in self.fish_selected:
                        pass
                    else:
                        self.list_s.addItem(items[i].text())
                        self.fish_selected.append(items[i].text())

    def run_stathab_gui(self):
        """
        A function to run stathab based on data loaded before
        :return:
        """
        self.send_log.emit('# Run Stathab from loaded data')
        # get the chosen fish
        self.mystathab.fish_chosen = []
        fish_list = []
        if self.list_s.count() == 0:
            self.send_log.emit('Error: no fish chosen')
            return
        for i in range(0, self.list_s.count()):
            fish_item = self.list_s.item(i)
            fish_item_str = fish_item.text()
            self.mystathab.fish_chosen.append(fish_item_str)
        sys.stdout = self.mystdout = StringIO()
        # run stathab
        self.mystathab.stathab_calc(self.path_bio_stathab, self.name_file_allreach[3])
        sys.stdout = sys.__stdout__
        self.send_err_log()
        # save data and fig
        self.mystathab.path_im = self.path_im
        self.mystathab.savetxt_stathab()
        if self.cb.isChecked():
            self.mystathab.savefig_stahab()
            self.show_fig.emit()

        # log information
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if self.mystathab.disthmes == [-99]:
            return
        self.send_log.emit("py    path_bio = '" + self.path_bio_stathab + "'")
        self.send_log.emit("py    mystathab.stathab_calc(path_bio)")
        self.send_log.emit("py    mystathab.savetxt_stathab()")
        self.send_log.emit("py    mystathab.path_im = '.'")
        self.send_log.emit("py    mystathab.savefig_stahab()")
        self.send_log.emit("restart    RUN_STATHAB_AND_SAVE_RESULTS")

