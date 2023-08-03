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
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QFileDialog, \
    QAbstractItemView, QMessageBox, QFrame, QListWidget, QListWidgetItem
import sys
import os
from io import StringIO

import src.dev_tools_mod
import src.tools_mod
from src_GUI import estimhab_GUI
from src import fstress_mod
from src.project_properties_mod import load_project_properties, save_project_properties
from src.user_preferences_mod import user_preferences
from src.bio_info_mod import get_biomodels_informations_for_database


class FstressW(estimhab_GUI.StatModUseful):
    """
    The class to load and manage the widget controlling the FStress model.
    """

    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__()

        self.tab_name = "fstress"
        self.tab_position = 10
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_im = self.path_prj
        self.fish_selected = []
        self.mystdout = StringIO()
        self.msge = QMessageBox()
        self.firstitemreach = []  # the first item of a reach
        self.list_file = QListWidget()
        self.list_needed = QListWidget()
        self.list_re = QListWidget()
        # name of all the text file (see stathabinfo.pdf)
        self.listrivname = 'listriv'
        self.end_file_reach = ['deb', 'qhw', 'gra', 'dis']  # .txt or .csv
        self.end_file_reach_trop = ['deb', 'qhw', 'ii']  # .txt or .csv
        self.name_file_allreach = ['bornh',
                                   'bornv']  # old :  self.name_file_allreach = ['bornh', 'bornv', 'borng', 'Pref_latin.txt']
        self.name_file_allreach_trop = []
        self.hdf5_name = self.tr('No hdf5 selected')
        self.myfstress = fstress_mod.FStress(self.name_prj, self.path_prj)
        self.dir_hdf5 = self.path_prj
        self.typeload = 'txt'  # txt or hdf5
        self.model_type = self.tr('FStress')
        self.selected_aquatic_animal_list = []
        project_properties = load_project_properties(self.path_prj)
        self.dir_name = project_properties[self.model_type]["path"]
        self.init_iu()
        self.fill_selected_models_listwidgets(project_properties[self.model_type]["fish_selected"])

    def init_iu(self):
        # see if a directory was selected before for FStress
        # see if an hdf5 was selected before for FStress
        # if both are there, reload as the last time
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Warning: Project was not saved. Save the project in the general tab \n')

        # prepare QLabel
        self.l1 = QLabel(self.tr('FStress Input Files (.txt)'))
        loadb = QPushButton(self.tr("Select directory"))
        if len(self.dir_name) > 30:
            self.l0 = QLabel('...' + self.dir_name[-30:])
        else:
            self.l0 = QLabel(self.dir_name)
        l2 = QLabel(self.tr("Reaches"))
        self.l3 = QLabel(self.tr("File found"))
        self.l4 = QLabel(self.tr("File still needed"))
        l6 = QLabel(self.tr("Selected models"))
        # not used anymore (not really helpful). I let it ehre anyway for completness.
        self.runb = QPushButton(self.tr("Run FStress"))
        self.runb.setStyleSheet("background-color: #47B5E6; color: black")

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # explore_bio_model
        self.explore_bio_model_pushbutton = QPushButton(self.tr('Choose biological models'))
        self.explore_bio_model_pushbutton.clicked.connect(self.open_bio_model_explorer)

        # avoid list which look too big or too small
        size_max = int(self.frameGeometry().height() / 2.5)
        self.list_needed.setMaximumHeight(size_max)
        self.list_re.setMaximumHeight(size_max)
        self.list_file.setMaximumHeight(size_max)
        self.list_f.setMinimumHeight(size_max)  # self.list_f defined in Estmhab_GUI.py
        self.list_f.setMinimumHeight(size_max)

        # connect method with list
        loadb.clicked.connect(self.select_dir)
        self.runb.clicked.connect(self.run_fstress_gui)
        self.list_re.itemClicked.connect(self.reach_selected)
        self.list_f.itemClicked.connect(self.add_fish)
        self.list_f.itemActivated.connect(self.add_fish)
        self.selected_aquatic_animal_qtablewidget.itemClicked.connect(self.remove_fish)
        self.selected_aquatic_animal_qtablewidget.itemActivated.connect(self.remove_fish)
        self.selected_aquatic_animal_qtablewidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # update label and list
        if self.dir_name and self.typeload == 'txt':
            if os.path.isdir(self.dir_name):
                self.load_from_txt_gui()
                if not self.myfstress.load_ok:
                    self.send_log.emit('Error: FStress file could not be loaded.\n')
            else:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("FStress"))
                self.msge.setText(self.tr("FStress: The selected directory for FStress does not exist."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
        elif self.hdf5_name != self.tr('No hdf5 selected') and self.typeload == 'hdf5':
            if os.path.isfile(self.hdf5_name):
                if self.typeload == 'txt':
                    self.load_from_txt_gui()
                if self.typeload == 'hdf5':
                    self.load_from_hdf5_gui()
                if not self.myfstress.load_ok:
                    self.msge.setIcon(QMessageBox.Warning)
                    self.msge.setWindowTitle(self.tr("FStress"))
                    self.msge.setText(self.mystdout.getvalue())
                    self.msge.setStandardButtons(QMessageBox.Ok)
                    self.msge.show()
            else:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("FStress"))
                self.msge.setText(self.tr("FStress: The selected hdf5 file for FStress does not exist."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()

        # empty frame scrolable
        content_widget = QFrame()

        # Layout
        self.layout = QGridLayout(content_widget)
        self.layout.addWidget(self.l1, 0, 0)
        self.layout.addWidget(loadb, 0, 2)
        self.layout.addWidget(self.l0, 0, 1)
        self.layout.addWidget(l2, 1, 0)
        self.layout.addWidget(self.l3, 1, 1)
        self.layout.addWidget(self.l4, 1, 2)
        self.layout.addWidget(self.list_re, 2, 0)
        self.layout.addWidget(self.list_file, 2, 1)
        self.layout.addWidget(self.list_needed, 2, 2)
        self.layout.addWidget(l6, 4, 0)
        self.layout.addWidget(self.selected_aquatic_animal_qtablewidget, 5, 0, 2, 1)
        self.layout.addWidget(self.runb, 7, 2)
        self.layout.addWidget(self.explore_bio_model_pushbutton, 7, 0)

        # self.setLayout(self.layout3)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

        if self.dir_name and self.typeload == 'txt':
            if os.path.isdir(self.dir_name):
                self.change_riv_type()

    def select_dir(self):
        """
        This function is used to select the directory and find the files to laod FStress from txt files. It calls
        load_from_txt_gui() when done.

        """
        # load last dir
        self.project_properties = load_project_properties(self.path_prj)
        if not self.dir_name:
            self.dir_name = self.project_properties["path_last_file_loaded"]
        if not self.dir_name:
            self.dir_name = self.path_prj

        # get the directory
        self.dir_name = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), self.dir_name)
        if self.dir_name == '':  # cancel case
            self.send_log.emit("Warning: No selected directory for FStress\n")
            return

        self.save_xml()

        # clear all list
        self.myfstress = fstress_mod.FStress(self.name_prj, self.path_prj)
        self.list_re.clear()
        self.list_file.clear()
        self.list_needed.clear()
        self.list_f.clear()
        self.firstitemreach = []

        filename_prj = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Error: No project saved. Please create a project first in the General tab.')
            return
        else:
            # fill the lists with the existing files
            self.load_from_txt_gui()

    def open_bio_model_explorer(self):
        self.nativeParentWidget().bio_model_explorer_dialog.open_bio_model_explorer(self.model_type)

    def fill_selected_models_listwidgets(self, new_item_text_list):
        # add new item if not exist
        for item_str in new_item_text_list:
            if item_str not in self.fish_selected:
                # filter : remove HEM bio models
                splited_item_str = item_str.split()
                code_bio_model = splited_item_str[-1]
                stage = splited_item_str[-3]

                # check if user pref curve file has been removed by user (AppData) to remove it in
                if not code_bio_model in user_preferences.biological_models_dict["code_biological_model"]:
                    # remove it
                    continue

                index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
                model_dict = get_biomodels_informations_for_database(
                    user_preferences.biological_models_dict["path_xml"][index_fish])
                hydraulic_type_available = model_dict["hydraulic_type_available"][
                    model_dict["stage_and_size"].index(stage)]
                if ("HV" in hydraulic_type_available) or ("V" in hydraulic_type_available) or (
                        "H" in hydraulic_type_available):
                    # add it to selected
                    self.selected_aquatic_animal_qtablewidget.addItem(item_str)
                    self.fish_selected.append(item_str)
                else:
                    self.send_log.emit('Warning: ' + item_str + " has neither height nor velocity in "
                                                                "biological model (not usable with " +
                                       self.model_type.replace("_", " ") + ").")
        self.save_xml()

    def load_from_txt_gui(self):
        """
        The main roles of load_from_text_gui() are to call the load_function of the FStress class (which is in
        stathab_mod.py in the folder src) and to call the function which create an hdf5 file. However, it does some
        modifications to the GUI before.
        """
        # update the labels
        if len(self.dir_name) > 30:
            self.l0.setText('...' + self.dir_name[-30:])
        else:
            self.l0.setText(self.dir_name)
        self.l1.setText(self.tr('FStress Input Files (.txt)'))
        self.l3.setText(self.tr("File found"))
        self.l4.setText(self.tr("File still needed"))

        # read the reaches name
        sys.stdout = self.mystdout = StringIO()
        # name_reach = stathab_mod.load_namereach(self.dir_name)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if name_reach == [-99]:
            self.list_re.clear()
            return
        for r in range(0, len(name_reach)):
            itemr = QListWidgetItem(name_reach[r])
            self.list_re.addItem(itemr)

        # see if the needed file are available

        # first let's look for the files where one file by reach is needed
        c = -1
        file_name_all_reach_here = []
        end_file_reach_here = []
        for r in range(0, len(name_reach)):
            # see which files are need based on the current river type
            if self.riverint == 0:  # temperate rivers
                end_file_reach_here = copy.deepcopy(self.end_file_reach)
                file_name_all_reach_here = copy.deepcopy(self.name_file_allreach)
            # tropical rivers
            elif self.riverint == 1 or self.riverint == 2:
                end_file_reach_here = copy.deepcopy(self.end_file_reach_trop)
                file_name_all_reach_here = copy.deepcopy(self.name_file_allreach_trop)
            else:
                end_file_reach_here = copy.deepcopy(self.end_file_reach)
                file_name_all_reach_here = copy.deepcopy(self.name_file_allreach)

            for i in range(0, len(end_file_reach_here)):
                file = os.path.join(self.dir_name, name_reach[r] + end_file_reach_here[i] + '.txt')
                file2 = os.path.join(self.dir_name, name_reach[r] + end_file_reach_here[i] + '.csv')
                if os.path.isfile(file):
                    itemf = QListWidgetItem(name_reach[r] + end_file_reach_here[i] + '.txt')
                    end_file_reach_here[i] += '.txt'
                    self.list_file.addItem(itemf)
                    c += 1
                elif os.path.isfile(file2):
                    itemf = QListWidgetItem(name_reach[r] + end_file_reach_here[i] + '.csv')
                    end_file_reach_here[i] += '.csv'
                    self.list_file.addItem(itemf)
                    c += 1
                else:
                    itemf = QListWidgetItem(name_reach[r] + end_file_reach_here[i])
                    self.list_needed.addItem(itemf)
                if i == 0:  # note the first item to be able to highlight it afterwards
                    self.firstitemreach.append([itemf, c])

            self.list_file.addItem('----------------')
            c += 1

        # files for all reaches
        # for the preference file in the case of temperate river:
        # first choice> Pref.txt in dir_name is used.
        # default choice: Pref.txt in the biology folder.
        for i in range(0, len(file_name_all_reach_here)):
            file = os.path.join(self.dir_name, file_name_all_reach_here[i] + '.txt')
            file2 = os.path.join(self.dir_name, file_name_all_reach_here[i] + '.csv')
            if os.path.isfile(file):
                itemf = QListWidgetItem(file_name_all_reach_here[i] + '.txt')
                file_name_all_reach_here[i] += '.txt'
                self.list_file.addItem(itemf)
                itemf.setBackground(Qt.lightGray)
                # if a custom Pref.txt is present (for FStress temperate)
                if i == len(self.name_file_allreach) and self.riverint == 0:
                    self.path_bio_stathab = self.dir_name
            elif os.path.isfile(file2):
                itemf = QListWidgetItem(file_name_all_reach_here[i] + '.csv')
                file_name_all_reach_here[i] += '.csv'
                self.list_file.addItem(itemf)
                itemf.setBackground(Qt.lightGray)
                # if a custom Pref.txt is present (for FStress temperate)
                if i == len(self.name_file_allreach) and self.riverint == 0:
                    self.path_bio_stathab = self.dir_name
            else:
                # case 1: a file is missing
                if i != len(file_name_all_reach_here) - 1:
                    self.list_needed.addItem(file_name_all_reach_here[i])
                # Or: if Pref.txt is missing, let's use the default file (temperate river)
                elif self.riverint == 0:
                    file = os.path.join(self.path_bio_stathab, self.name_file_allreach[i])
                    if os.path.join(file):
                        itemf = QListWidgetItem(self.name_file_allreach[i] + ' (default)')
                        self.list_file.addItem(itemf)
                        itemf.setBackground(Qt.lightGray)
                    else:
                        self.list_needed.addItem(self.name_file_allreach[i])

        # # read the name of the available fish
        # name_fish = []
        # if self.riverint == 0:
        #     sys.stdout = self.mystdout = StringIO()
        #     [name_fish, blob] = stathab_mod.load_pref(self.name_file_allreach[-1], self.path_bio_stathab)
        #     sys.stdout = sys.__stdout__
        #     self.send_err_log()
        # if self.riverint == 1:  # univariate
        #     filenames = hdf5_mod.get_all_filename(self.path_bio_stathab, '.csv')
        #     for f in filenames:
        #         if 'uni' in f and f[-7:-4] not in name_fish:
        #             name_fish.append(f[-7:-4])
        # if self.riverint == 2:
        #     filenames = hdf5_mod.get_all_filename(self.path_bio_stathab, '.csv')
        #     for f in filenames:
        #         if 'biv' in f:
        #             name_fish.append(f[-7:-4])
        #
        # if name_fish == [-99]:
        #     return
        # self.list_f.clear()
        # for r in range(0, len(name_fish)):
        #     self.list_f.addItem(name_fish[r])

        # load now the text data, create the hdf5 and write in the project file
        if self.list_needed.count() > 0:
            if self.riverint == 0:
                if not file_name_all_reach_here or not end_file_reach_here:
                    self.send_log.emit('Error: Found only a part of the needed FStress files. '
                                       'Need to re-load before execution\n')
                    self.myfstress.save_xml_stathab(True)
                    return
            elif self.riverint == 1:
                if not file_name_all_reach_here:
                    self.send_log.emit(
                        'Error: Found only a part of the needed FStress Steep files. '                                       'Need to re-load before execution\n')
                    self.myfstress.save_xml_stathab(True)
                    return
        else:
            self.list_needed.addItem('All files found')
            self.send_log.emit('# Found all FStress files. Run Now.')
            sys.stdout = self.mystdout = StringIO()
            self.myfstress.load_stathab_from_txt(end_file_reach_here, file_name_all_reach_here,
                                                 self.dir_name)
            self.myfstress.create_hdf5()
            self.myfstress.save_xml_stathab()
            sys.stdout = sys.__stdout__
            self.send_err_log()

            # copy the input in the input folder
            input_folder = self.find_path_input_est()
            new_dir = os.path.join(input_folder, 'input_' + self.model_type.lower())
            all_files = os.listdir(self.dir_name)
            paths = [self.dir_name] * len(all_files)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            src.dev_tools_mod.copy_files(all_files, paths, new_dir)

            # log info
            if not self.myfstress.load_ok:
                self.send_log.emit('Error: Could not load FStress data.\n')
                return
            var1 = 'py    var1 = ['
            if self.riverint == 0:
                for i in range(0, len(self.end_file_reach) - 1):  # Pref by default
                    if '.txt' in self.end_file_reach[i]:
                        var1 += "'" + self.end_file_reach[i] + "',"
                    else:
                        var1 += "'" + self.end_file_reach[i] + ".txt',"
            else:
                for i in range(0, len(self.end_file_reach_trop)):
                    var1 += "'" + self.end_file_reach_trop[i] + ".csv',"
            var1 = var1[:-1] + "]"
            self.send_log.emit(var1)
            if self.riverint == 0:
                var2 = 'py    var2 = ['
                for i in range(0, len(self.name_file_allreach)):
                    if '.txt' in self.name_file_allreach[i]:
                        var2 += "'" + self.name_file_allreach[i] + "',"
                    else:
                        var2 += "'" + self.name_file_allreach[i] + ".txt',"
                var2 = var2[:-1] + "]"
            else:
                var2 = 'py    var2 = []'
            self.send_log.emit(var2)
            self.send_log.emit("py    dir_name = '" + self.dir_name + "'")
            self.send_log.emit('py    mystathab = stathab_c.FStress(name_prj, path_prj)')
            self.send_log.emit("py    mystathab.riverint = " + str(self.riverint))
            self.send_log.emit("py    mystathab.load_stathab_from_txt( var1, var2, dir_name)")
            self.send_log.emit("py    mystathab.create_hdf5()")
            self.send_log.emit("py    mystathab.save_xml_stathab()")

    def load_from_hdf5_gui(self):
        """
        This function calls from the GUI the load_stathab_from_hdf5 function. In addition to call the function to load
        the hdf5, it also updates the GUI according to the info contained in the hdf5.
        """
        # update QLabel
        self.l1.setText(self.tr('FStress Input Files (.hdf5)'))
        if len(self.dir_name) > 30:
            self.l0.setText(self.hdf5_name[-30:])
        else:
            self.l0.setText(self.hdf5_name)
        self.l3.setText(self.tr("Data found"))
        self.l4.setText(self.tr("Data still needed"))

        # load data
        self.send_log.emit('# Loading FStress from hdf5...')
        sys.stdout = self.mystdout = StringIO()
        self.myfstress.load_stathab_from_hdf5()

        # log info
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if self.riverint != self.myfstress.riverint:
            self.send_log.emit('Warning: This river type could not be selected with the current hdf5.')
            self.riverint = self.myfstress.riverint
            self.change_riv_type()
        if not self.myfstress.load_ok:
            self.send_log.emit('Error: Data from  hdf5 not loaded.\n')
            return
        self.send_log.emit('py    mystathab = stathab_c.FStress(name_prj, path_prj)')
        self.send_log.emit('py    mystathab.load_stathab_from_hdf5()')
        self.send_log.emit('restart LOAD_STATHAB_FROM_HDF5')

        # update list with name reach
        if len(self.myfstress.name_reach) == 0:
            self.send_log.emit('Error: No name of reach found. \n')
            return
        for r in range(0, len(self.myfstress.name_reach)):
            itemr = QListWidgetItem(self.myfstress.name_reach[r])
            self.list_re.addItem(itemr)

        # update list with name of data
        if self.riverint == 0:
            data_reach = [self.myfstress.qlist, self.myfstress.qwh, self.myfstress.disthmes,
                          self.myfstress.qhmoy, self.myfstress.dist_gran]
            data_reach_str = ['qlist', 'qwh', 'dishhmes', 'qhmoy', 'dist_granulo']
        else:
            data_reach = [self.myfstress.qlist, self.myfstress.qwh, self.myfstress.data_ii]
            data_reach_str = ['qlist', 'qwh', 'data_ii']
        c = -1
        for r in range(0, len(self.myfstress.name_reach)):
            for i in range(0, len(data_reach)):
                if data_reach[i]:
                    itemr = QListWidgetItem(data_reach_str[i])
                    self.list_file.addItem(itemr)
                    c += 1
                else:
                    self.list_needed.addItem(data_reach_str[i])
                if i == 0:  # note the first item to be able to highlight it afterwards
                    self.firstitemreach.append([itemr, c])
            c += 1
            self.list_file.addItem('----------------')

        # update list with bornes of velocity, height and granola
        if self.riverint == 0:
            lim_str = ['limits height', 'limits velocity', 'limits granulometry']
            for i in range(0, 3):
                if len(self.myfstress.lim_all[i]) > 1:
                    itemr = QListWidgetItem(lim_str[i])
                    self.list_file.addItem(itemr)
                    itemr.setBackground(Qt.lightGray)
                else:
                    self.list_needed.addItem(lim_str[i])

            # # see if a preference file is available in the same folder than the hdf5 file
            # preffile = os.path.join(self.dir_hdf5, self.name_file_allreach[3])
            # if os.path.isfile(preffile):
            #     self.path_bio_stathab = self.dir_hdf5
            #     itemp = QListWidgetItem(self.name_file_allreach[3])
            #     self.list_file.addItem(itemp)
            #     itemp.setBackground(Qt.lightGray)
            # else:
            #     itemp = QListWidgetItem(self.name_file_allreach[3] + '(default)')
            #     self.list_file.addItem(itemp)
            #     itemp.setBackground(Qt.lightGray)

        # read the available fish
        name_fish = []
        # if self.riverint == 0:
        #     sys.stdout = self.mystdout = StringIO()
        #     [name_fish, blob] = stathab_mod.load_pref(self.name_file_allreach[-1], self.path_bio_stathab)
        #     sys.stdout = sys.__stdout__
        #     self.send_err_log()
        if self.riverint == 1:  # univariate
            filenames = src.dev_tools_mod.get_all_filename(self.path_bio_stathab, '.csv')
            for f in filenames:
                if 'uni' in f and f[-7:-4] not in name_fish:
                    name_fish.append(f[-7:-4])
        if self.riverint == 2:
            filenames = src.dev_tools_mod.get_all_filename(self.path_bio_stathab, '.csv')
            for f in filenames:
                if 'biv' in f:
                    name_fish.append(f[-7:-4])

        if name_fish == [-99]:
            return
        self.list_f.clear()
        for r in range(0, len(name_fish)):
            self.list_f.addItem(name_fish[r])

        # final check
        if self.list_needed.count() == 1 and self.list_needed.item(0).text() == 'All files found':
            self.list_needed.addItem('All hdf5 data found')
            self.send_log.emit('# Found all FStress files.')
        else:
            self.send_log.emit('# Warning: Could not read all the hdf5 data from FStress.\n')
            return

    def reach_selected(self):
        """
        A function which indcates which files are linked with which reach.

        **Technical comment**

        This is a small function which only impacts the GUI. When a FStress model has more than one reach,
        the user can click on the name of the reach. When he does this, HABBY selects the first file linked
        with this reach and shows it in self.list_f. This first file is highlighted and the list is scrolled
        down so that the files linked with the selected reach are shown. This function manages this. It is connected
        with the list self.list_re, which is the list with the name of the reaches.

        """
        [item_sel, r] = self.firstitemreach[self.list_re.currentRow()]
        self.list_file.setCurrentRow(r)
        self.list_file.scrollToItem(item_sel)

    def send_err_log(self):
        """
        Send the errors and warnings to the logs. It is useful to note that the stdout was redirected to self.mystdout.
        """
        str_found = self.mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])

    def save_xml(self):
        # save the name and the path in the xml .prj file
        if not os.path.isfile(os.path.join(self.path_prj, self.name_prj + ".habby")):
            self.send_log.emit('Error: The project is not saved. '
                               'Save the project in the General tab before saving hydrological data. \n')
        else:
            # change path_last_file_loaded, model_type (path)
            project_properties = load_project_properties(self.path_prj)  # load_project_properties
            project_properties["path_last_file_loaded"] = self.dir_name  # change value
            project_properties[self.model_type]["path"] = self.dir_name  # change value
            project_properties[self.model_type]["fish_selected"] = self.fish_selected  # change value
            save_project_properties(self.path_prj, project_properties)  # save_project_properties

    def run_fstress_gui(self):
        """
        This is the function which calls the function to run the FStress model.  First it read the list called
        self.selected_aquatic_animal_qtablewidget. This is the list with the fishes selected by the user. Then, it calls the function to run
        FStress and the one to create the figure if the figures were asked by the user. Finally, it writes the log.
        """
        self.send_log.emit('# Run ' + self.model_type + ' from loaded data')

        # get the chosen fish
        self.myfstress.fish_chosen = []
        self.myfstress.data_list = []

        by_vol = True
        if self.selected_aquatic_animal_qtablewidget.count() == 0:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.model_type)
            self.msge.setText(self.tr("Unable to load the " + self.model_type + " data !"))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            self.send_log.emit('Error: no fish chosen')
            return
        for i in range(0, self.selected_aquatic_animal_qtablewidget.count()):
            fish_item = self.selected_aquatic_animal_qtablewidget.item(i)
            fish_item_str = fish_item.text()
            self.myfstress.fish_chosen.append(fish_item_str)
        self.myfstress.path_txt = self.find_path_text_est()

        # check
        for r in range(0, len(self.myfstress.qwh)):
            if self.myfstress.qwh[r][1, 0] < self.myfstress.qwh[r][0, 0] * 2:
                self.send_log.emit('Warning: Measured discharge are too close to each other.'
                                   'Results might be unrealisitc. \n')
            if self.myfstress.qwh[r][1, 0] > 50 or self.myfstress.qwh[r][0, 0] > 50:
                self.send_log.emit('Warning: Discharge is higher then 50m3/s. Results might be unrealisitc \n')
            if self.riverint == 1 or self.riverint == 2:
                if self.myfstress.data_ii[r][0] < 1:
                    self.send_log.emit('Warning: Slope is lower than 1%. Results might be unrealisitc \n')
                if self.myfstress.data_ii[r][0] > 24:
                    self.send_log.emit('Warning: Slope is higher than 24%. Results might be unrealisitc \n')

        # run FStress
        if self.riverint == 0:
            sys.stdout = self.mystdout = StringIO()
            self.myfstress.stathab_calc()
            sys.stdout = sys.__stdout__
            self.send_err_log()
        else:
            self.send_log.emit("The river type is not recognized. " + self.model_type + " could not be run.")
            return

        # caught some errors, special cases.
        if self.riverint == 0:
            if len(self.myfstress.disthmes) == 0:  # you cannot use seld.list_needed.count()
                self.send_log.emit("Error: " + self.model_type + " could not be run. Are all files available?")
                return
            if len(self.myfstress.disthmes[0]) == 1:
                if self.myfstress.disthmes[0] == -99:
                    return
        else:
            if len(self.myfstress.data_ii) == 0:
                self.send_log.emit('Error: ' + self.model_type + ' could not be run. Are all files available?')
        if not self.myfstress.load_ok:
            self.send_log.emit('Error: ' + self.model_type + ' could not be run. \n')
            return

        # save data and fig
        self.myfstress.savetxt_stathab()
        self.myfstress.savefig_stahab()

        # log information
        self.send_err_log()


if __name__ == '__main__':
    pass
