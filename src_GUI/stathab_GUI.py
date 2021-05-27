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
import os
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QFileDialog, \
    QListWidget, QListWidgetItem, QMessageBox, QAbstractItemView, QFrame
import sys
import copy
from lxml import etree as ET

import src.dev_tools_mod
import src.tools_mod
from src import stathab_mod
from src import hdf5_mod
from src_GUI import estimhab_GUI
from src.project_properties_mod import load_project_properties, save_project_properties
from src.bio_info_mod import get_biomodels_informations_for_database
from src.user_preferences_mod import user_preferences


class StathabW(estimhab_GUI.StatModUseful):
    """
    The class to load and manage the widget controlling the Stathab model.

    **Technical comments**

    The class StathabW makes the link between the data prepared by the user for Stathab and  the Stathab model
    which is in the src folder (stathab_mod.py) using the graphical interface.  Most of the Stathab input are given in
    form of text file. For more info on the preparation of text files for stathab, read the document called
    'stathabinfo.pdf".  To use Stathab in HABBY, all Stathab input should be in the same directory. The user select
    this directory (using the button “loadb”) and HABBY tries to find the file it needs. All found files are added to
    the list called “file found”. If file are missing, they are added to the “file still needed” list.  The user can then
    select the fishes on which it wants to run stathab, then it run it by pressing on the “runb” button.

    If file where loaded before by the user in the same project, StathabW looks for them and load them again. Here we
    can have two cases: a) the data was saved in hdf5 format (as it is done when a stathab run was done) and the path
    to this file noted in the xml project file. b) Only the name of the directory was written in the xml project file,
    indicated that data was loaded but not saved in hdf5 yet. HABBY manages both cases.

    Next, we check in the xml project file where the folder to save the figure (path_im) is. In case, there are
    no path_im saved, Stathab create one folder to save the figure outputs. This should not be the usual case. Generally,
    path_im is created with the xml project file, but you cannot be sure.

    There is a list of error message which are there for the case where the data which was loaded before do not exist
    anymore. For example, somebody erased the directory with the Stathab data in the meantime.  In this case,
    a pop-up message open and warn the user.

    An important attribute of StathabW() is self.mystathab. This is an object fo the stahab class. The stathab model,
    which is in the form of a class and not a function, will be run on this object.

    StathabW inherit StatModUseful, which is a class mostly used to manage the exchange of the fish name between the
    two QListWidget (selected fish and available fish).
    """

    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """
    def __init__(self, path_prj, name_prj, steep=False):

        super().__init__()

        self.tab_name = "stathab"
        self.tab_position = 8
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_im = self.path_prj
        self.path_bio_stathab = './/biology/stathab'
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
        self.name_file_allreach = ['bornh', 'bornv', 'borng', 'Pref_latin.txt']
        self.name_file_allreach_trop = []
        self.hdf5_name = self.tr('No hdf5 selected')
        self.mystathab = stathab_mod.Stathab(self.name_prj, self.path_prj)
        self.dir_hdf5 = self.path_prj
        self.typeload = 'txt'  # txt or hdf5
        self.riverint = 0  # stathab or stathab_steep
        self.model_type = self.tr('Stathab')
        if steep:
            self.riverint = 1
            self.model_type = self.tr('Stathab_steep')
            self.tab_position = 9
        self.selected_aquatic_animal_list = []
        project_properties = load_project_properties(self.path_prj)
        self.dir_name = project_properties[self.model_type]["path"]
        self.init_iu()
        self.fill_selected_models_listwidets(project_properties[self.model_type]["fish_selected"])

    def init_iu(self):
        # see if a directory was selected before for Stathab
        # see if an hdf5 was selected before for Stathab
        # if both are there, reload as the last time
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Warning: Project was not saved. Save the project in the general tab \n')

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
        l6 = QLabel(self.tr("Selected models"))
        # not used anymore (not really helpful). I let it ehre anyway for completness.
        loadhdf5b = QPushButton(self.tr("Load data from hdf5"))
        self.runb = QPushButton(self.tr("Run Stathab"))
        self.runb.setStyleSheet("background-color: #47B5E6; color: black")

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # add a switch for tropical rivers
        self.mystathab.riverint = self.riverint

        # explore_bio_model
        self.explore_bio_model_pushbutton = QPushButton(self.tr('Choose biological models'))
        self.explore_bio_model_pushbutton.clicked.connect(self.open_bio_model_explorer)

        # avoid list which look too big or too small
        size_max = self.frameGeometry().height() / 2.5
        self.list_needed.setMaximumHeight(size_max)
        self.list_re.setMaximumHeight(size_max)
        self.list_file.setMaximumHeight(size_max)
        self.list_f.setMinimumHeight(size_max)  # self.list_f defined in Estmhab_GUI.py
        self.list_f.setMinimumHeight(size_max)

        # connect method with list
        loadb.clicked.connect(self.select_dir)
        loadhdf5b.clicked.connect(self.select_hdf5)
        self.runb.clicked.connect(self.run_stathab_gui)
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
                if not self.mystathab.load_ok:
                    self.send_log.emit('Error: Stathab file could not be loaded.\n')
            else:
                self.msge.setIcon(QMessageBox.Warning)
                self.msge.setWindowTitle(self.tr("Stathab"))
                self.msge.setText(self.tr("Stathab: The selected directory for stathab does not exist."))
                self.msge.setStandardButtons(QMessageBox.Ok)
                self.msge.show()
        elif self.hdf5_name != self.tr('No hdf5 selected') and self.typeload == 'hdf5':
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

        self.change_riv_type()

    def select_dir(self):
        """
        This function is used to select the directory and find the files to laod stathab from txt files. It calls
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
            self.send_log.emit("Warning: No selected directory for stathab\n")
            return

        self.save_xml()

        # clear all list
        self.mystathab = stathab_mod.Stathab(self.name_prj, self.path_prj)
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

    def fill_selected_models_listwidets(self, new_item_text_list):
        # add new item if not exist
        for item_str in new_item_text_list:
            if item_str not in self.fish_selected:
                # filter : remove HEM bio models
                splited_item_str = item_str.split()
                code_bio_model = splited_item_str[-1]
                stage = splited_item_str[-3]
                index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
                model_dict = get_biomodels_informations_for_database(user_preferences.biological_models_dict["path_xml"][index_fish])
                hydraulic_type_available = model_dict["hydraulic_type_available"][model_dict["stage_and_size"].index(stage)]
                if "HV" in hydraulic_type_available:
                    # add it to selected
                    self.selected_aquatic_animal_qtablewidget.addItem(item_str)
                    self.fish_selected.append(item_str)
                else:
                    self.send_log.emit('Warning: ' + item_str + " don't have height and velocity in biological model (not usable with Stathab).")
        self.save_xml()

    def change_riv_type(self):
        """
        This function manage the changes which needs to happends to the GUI when the user want to pass from
        tropical river to temperate river and vice-versa. Indeed the fish species and the input files are not
        the same for tropical and temperate river.
        """
        # clear the different list
        self.mystathab = stathab_mod.Stathab(self.name_prj, self.path_prj)
        self.list_re.clear()
        self.list_file.clear()
        self.list_needed.clear()
        self.list_f.clear()
        self.fish_selected = []
        self.firstitemreach = []
        self.mystathab.riverint = self.riverint

        if self.riverint == 0:
            self.runb.setText(self.tr("Run Stathab"))
        elif self.riverint == 1:
            self.runb.setText(self.tr("Run Stathab steep"))

        # get the new files
        if self.typeload == 'txt':
            self.load_from_txt_gui()
        if self.typeload == 'hdf5':
            self.load_from_hdf5_gui()

    def load_from_txt_gui(self):
        """
        The main roles of load_from_text_gui() are to call the load_function of the stathab class (which is in
        stathab_mod.py in the folder src) and to call the function which create an hdf5 file. However, it does some
        modifications to the GUI before.

        **Technical comments**

        Here is the list of the modifications done to the graphical user interface before calling the load_function of
        Stathab.

        First, it updates the label. Because a new directory was selected, we need to update the label containing the
        directory’s name. We only show the 30 last character of the directory name. In addition, we also need to update
        the other label. Indeed, it is possible that the data used by Stathab would be loaded from an hdf5 file.
        In this case, the labels on the top of the list of file are slightly modified. Here, we insure that we are in
        the “text” version since we will load the data from text file.

        Next, it gets the name of all the reach and adds them to the list of reach name. For this, it calls a function
        from the stathab class (in src). Then, it looks which files are present and add them to the list which contains
        the reach name called self.list_re.

        Afterwards, it checks if the files needed by Stathab are here. The list of file is given in the
        self.end_file_reach list. The form of the file is always the name of the reach + one item of
        self.end_file_reach. If it does not find all files, it add the name of the files not found to self.list_needed,
        so that the user can be aware of which file he needs. The exception is Pref_latin.txt. If HABBY do not find
        it in the directory, it uses the default “Pref_latin.txt” . All files (apart from Pref_latin.txt) should be in
        the same directory. There is also a file called "Pref.txt" file. It is a very similar file as Pref_latin.txt
        and can also be used as intput. The fish name are however in code and not in latin name.

        If the river is temperate, the files needed are not the same than if the river is in the tropic. This is
        accounted using the variable rivint. If rivint is zero, the river is temparate and this function looks for the
        file needed for temperate type (list of file contained in self.end_file_reach and self.name_file_allreach).
        If riverin is equal to 1 or 2, the river is tropical (list of file contained in self.end_file_reach_top and
        biological data in the stathab folder in the biology folder (many files). If the river is temperate,
        all preference coeff are in one file called Pref_latin.txt (also in the stathab folder of the biology folder).

        Then, it calls a method of the Stathab class (in src) which reads the “pref_latin.txt” file and adds the name
        of the fish to the GUI. If the "tropical river" option is selected, it looks which preference file are present
        in self.path_bio_stathab. The name of the tropical preference file needs to be in this form: YuniYh_XXX.csv and
        YuniYh_XX.csv for the univariate case and YbivYXXX.csv for the bivarate where XX is the three letter fish code
        from ONEMA and Y is whatever string. The form of the preference file is the form from the R version of
        stathab 2.

        Next, if all files are present, it loads the data using the method written in Stathab
        (in the src folder). When the data is loaded, it creates an hdf5 file from this data and save the name of this
        new hdf5 file in the xml project file (also using a method in the stathab class). It also copy the input files
        in the "input" folder.

        Finally, it sends the log info as explained in the log section of the documentation
        """
        self.mystathab.riverint = self.riverint

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
        name_reach = stathab_mod.load_namereach(self.dir_name, self.listrivname)
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
                # if a custom Pref.txt is present (for stathab temperate)
                if i == len(self.name_file_allreach) and self.riverint == 0:
                    self.path_bio_stathab = self.dir_name
            elif os.path.isfile(file2):
                itemf = QListWidgetItem(file_name_all_reach_here[i] + '.csv')
                file_name_all_reach_here[i] += '.csv'
                self.list_file.addItem(itemf)
                itemf.setBackground(Qt.lightGray)
                # if a custom Pref.txt is present (for stathab temperate)
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

        # read the name of the available fish
        name_fish = []
        if self.riverint == 0:
            sys.stdout = self.mystdout = StringIO()
            [name_fish, blob] = stathab_mod.load_pref(self.name_file_allreach[-1], self.path_bio_stathab)
            sys.stdout = sys.__stdout__
            self.send_err_log()
        if self.riverint == 1:  # univariate
            filenames = hdf5_mod.get_all_filename(self.path_bio_stathab, '.csv')
            for f in filenames:
                if 'uni' in f and f[-7:-4] not in name_fish:
                    name_fish.append(f[-7:-4])
        if self.riverint == 2:
            filenames = hdf5_mod.get_all_filename(self.path_bio_stathab, '.csv')
            for f in filenames:
                if 'biv' in f:
                    name_fish.append(f[-7:-4])

        if name_fish == [-99]:
            return
        self.list_f.clear()
        for r in range(0, len(name_fish)):
            self.list_f.addItem(name_fish[r])

        # load now the text data, create the hdf5 and write in the project file
        if self.list_needed.count() > 0:
            self.send_log.emit('Error: Found only a part of the needed STATHAB files. '
                               'Need to re-load before execution\n')
            # self.mystathab.save_xml_stathab(True)
            return
        self.list_needed.addItem('All files found')
        self.send_log.emit('# Found all STATHAB files. Load Now.')
        sys.stdout = self.mystdout = StringIO()
        self.mystathab.load_stathab_from_txt(self.listrivname, end_file_reach_here, file_name_all_reach_here,
                                             self.dir_name)
        # self.mystathab.create_hdf5()
        # self.mystathab.save_xml_stathab()
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
        if not self.mystathab.load_ok:
            self.send_log.emit('Error: Could not load stathab data.\n')
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
            for i in range(0, len(self.end_file_reach)):
                if '.txt' in self.name_file_allreach[i]:
                    var2 += "'" + self.name_file_allreach[i] + "',"
                else:
                    var2 += "'" + self.name_file_allreach[i] + ".txt',"
            var2 = var2[:-1] + "]"
        else:
            var2 = 'py    var2 = []'
        self.send_log.emit(var2)
        self.send_log.emit("py    dir_name = '" + self.dir_name + "'")
        self.send_log.emit('py    mystathab = stathab_c.Stathab(name_prj, path_prj)')
        self.send_log.emit("py    mystathab.riverint = " + str(self.riverint))
        self.send_log.emit("py    mystathab.load_stathab_from_txt('listriv', var1, var2, dir_name)")
        self.send_log.emit("py    mystathab.create_hdf5()")
        self.send_log.emit("py    mystathab.save_xml_stathab()")

    def select_hdf5(self):
        """
        This function allows the user to choose an hsdf5 file as input from Stathab.

        **Technical comment**

        This function is for example useful if the user would have created an hdf5 file for a Stathab model in another
        project and he would like to send the same model on other fish species.

        This function writes the name of the new hdf5 file in the xml project file. It also notes that the last data
        loaded was of hdf5 type. This is useful when HABBY is restarting because it is possible to have a
        directory name and the address of an hdf5 file in the part of the xml project file concerning Stathab.
        HABBY should know if the last file loaded was this hdf5 or the files in the directory.
        Finally, it calls the function to load the hdf5 called load_from_hdf5_gui.
        """
        self.send_log.emit('# Load stathab file from hdf5.')

        # load the filename
        self.hdf5_name = QFileDialog.getOpenFileName()[0]
        self.dir_hdf5 = os.path.dirname(self.hdf5_name)
        if self.hdf5_name == '':  # cancel case
            self.send_log.emit("Warning: No selected hdf5 file for stathab\n")
            return
        blob, ext = os.path.splitext(self.hdf5_name)
        if ext != '.hab':
            self.send_log.emit("Warning: The file should be of habby type.\n")

        # save the directory in the project file
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Error: No project saved. Please create a project first in the General tab.')
            return
        else:
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_prj, parser)
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
                    typeload = ET.SubElement(child, "TypeloadStathab")  # last load from txt or hdf5?
                    typeload.text = 'hdf5'
                else:
                    typeload.text = 'hdf5'
            doc.write(filename_prj, pretty_print=True)

        # clear list of the GUI
        self.mystathab = stathab_mod.Stathab(self.name_prj, self.path_prj)
        self.list_re.clear()
        self.list_file.clear()
        self.selected_aquatic_animal_qtablewidget.clear()
        self.list_needed.clear()
        self.fish_selected = []
        self.firstitemreach = []

        # load hdf5 data
        self.load_from_hdf5_gui()

    def load_from_hdf5_gui(self):
        """
        This function calls from the GUI the load_stathab_from_hdf5 function. In addition to call the function to load
        the hdf5, it also updates the GUI according to the info contained in the hdf5.

        **Technical comments**

        This function updates the Qlabel similarly to the function “load_from_txt_gui()”.
        It also loads the data calling the load_stathab_from_hdf5 function from the Stathab class in src. The info
        contains in the hdf5 file are now in the memory in various variables called self.mystathab.”something”.
        HABBY used them to update the GUI. First, it updates the list which contains the name of the reaches
        (self.list_re.). Next, it checks that each of the variable needed exists and that they contain some data.
        Afterwards, HABBY looks which preference file to use. Either, it will use the default preference file
        (contained in HABBY/biology) or a custom preference prepared by the user. This custom preference
        file should be in the same folder than the hdf5 file. When the preference file was found, HABBY reads all
        the fish type which are described and add their name to the self.list_f list which show the available fish
        to the user in the GUI. Finally it checks if all the variables were found or if some were missing
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
        self.send_log.emit('# Loading stathab from hdf5...')
        sys.stdout = self.mystdout = StringIO()
        self.mystathab.load_stathab_from_hdf5()

        # log info
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if self.riverint != self.mystathab.riverint:
            self.send_log.emit('Warning: This river type could not be selected with the current hdf5.')
            self.riverint = self.mystathab.riverint
            self.change_riv_type()
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
        if self.riverint == 0:
            data_reach = [self.mystathab.qlist, self.mystathab.qwh, self.mystathab.disthmes,
                          self.mystathab.qhmoy, self.mystathab.dist_gran]
            data_reach_str = ['qlist', 'qwh', 'dishhmes', 'qhmoy', 'dist_granulo']
        else:
            data_reach = [self.mystathab.qlist, self.mystathab.qwh, self.mystathab.data_ii]
            data_reach_str = ['qlist', 'qwh', 'data_ii']
        c = -1
        for r in range(0, len(self.mystathab.name_reach)):
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
        name_fish = []
        if self.riverint == 0:
            sys.stdout = self.mystdout = StringIO()
            [name_fish, blob] = stathab_mod.load_pref(self.name_file_allreach[-1], self.path_bio_stathab)
            sys.stdout = sys.__stdout__
            self.send_err_log()
        if self.riverint == 1:  # univariate
            filenames = hdf5_mod.get_all_filename(self.path_bio_stathab, '.csv')
            for f in filenames:
                if 'uni' in f and f[-7:-4] not in name_fish:
                    name_fish.append(f[-7:-4])
        if self.riverint == 2:
            filenames = hdf5_mod.get_all_filename(self.path_bio_stathab, '.csv')
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
            self.send_log.emit('# Found all STATHAB files.')
        else:
            self.send_log.emit('# Warning: Could not read all the hdf5 data from Stathab.\n')
            return

    def reach_selected(self):
        """
        A function which indcates which files are linked with which reach.

        **Technical comment**

        This is a small function which only impacts the GUI. When a Stathab model has more than one reach,
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
            project_preferences = load_project_properties(self.path_prj)  # load_project_properties
            project_preferences["path_last_file_loaded"] = self.dir_name  # change value
            project_preferences[self.model_type]["path"] = self.dir_name  # change value
            project_preferences[self.model_type]["fish_selected"] = self.fish_selected  # change value
            save_project_properties(self.path_prj, project_preferences)  # save_project_properties

    def run_stathab_gui(self):
        """
        This is the function which calls the function to run the Stathab model.  First it read the list called
        self.selected_aquatic_animal_qtablewidget. This is the list with the fishes selected by the user. Then, it calls the function to run
        stathab and the one to create the figure if the figures were asked by the user. Finally, it writes the log.
        """
        self.send_log.emit('# Run ' + self.model_type + ' from loaded data')

        # get the chosen fish
        self.mystathab.fish_chosen = []
        fish_list = []
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
            self.mystathab.fish_chosen.append(fish_item_str)
        self.mystathab.path_txt = self.find_path_text_est()

        # check
        for r in range(0, len(self.mystathab.qwh)):
            if self.mystathab.qwh[r][1, 0] < self.mystathab.qwh[r][0, 0] * 2:
                self.send_log.emit('Warning: Measured discharge are too close to each other.'
                                   'Results might be unrealisitc. \n')
            if self.mystathab.qwh[r][1, 0] > 50 or self.mystathab.qwh[r][0, 0] > 50:
                self.send_log.emit('Warning: Discharge is higher then 50m3/s. Results might be unrealisitc \n')
            if self.riverint == 1 or self.riverint == 2:
                if self.mystathab.data_ii[r][0] < 1:
                    self.send_log.emit('Warning: Slope is lower than 1%. Results might be unrealisitc \n')
                if self.mystathab.data_ii[r][0] > 24:
                    self.send_log.emit('Warning: Slope is higher than 24%. Results might be unrealisitc \n')

        # run Stathab
        if self.riverint == 0:
            sys.stdout = self.mystdout = StringIO()
            self.mystathab.stathab_calc(self.path_bio_stathab, self.name_file_allreach[3])
            sys.stdout = sys.__stdout__
            self.send_err_log()
        # run Stathab_steep
        elif self.riverint == 1:
            sys.stdout = self.mystdout = StringIO()
            self.mystathab.stathab_steep_calc(self.path_bio_stathab, by_vol)
            sys.stdout = sys.__stdout__
            self.send_err_log()
        else:
            self.send_log.emit("The river type is not recognized. " + self.model_type + " could not be run.")
            return

        # caught some errors, special cases.
        if self.riverint == 0:
            if len(self.mystathab.disthmes) == 0:  # you cannot use seld.list_needed.count()
                self.send_log.emit("Error: " + self.model_type + " could not be run. Are all files available?")
                return
            if len(self.mystathab.disthmes[0]) == 1:
                if self.mystathab.disthmes[0] == -99:
                    return
        else:
            if len(self.mystathab.data_ii) == 0:
                self.send_log.emit('Error: ' + self.model_type + ' could not be run. Are all files available?')
        if not self.mystathab.load_ok:
            self.send_log.emit('Error: ' + self.model_type + ' could not be run. \n')
            return

        # save data and fig
        self.mystathab.savetxt_stathab()
        self.mystathab.savefig_stahab()

        # log information
        self.send_err_log()


if __name__ == '__main__':
    pass
