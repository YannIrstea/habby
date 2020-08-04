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
import os
import sys
from multiprocessing import Process, Queue, Value
import numpy as np
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, \
    QLabel, QGridLayout, \
    QLineEdit, QFileDialog, \
    QComboBox, QMessageBox, QGroupBox, \
    QAbstractItemView, QScrollArea, QFrame, QVBoxLayout, QSizePolicy, \
    QHBoxLayout

from src.hydraulic_results_manager_mod import HydraulicModelInformation
from src.hydraulic_process_mod import HydraulicSimulationResultsAnalyzer
from src import hdf5_mod
from src import hydraulic_process_mod

from src.project_properties_mod import load_project_properties, save_project_properties
from src_GUI.tools_GUI import QListWidgetClipboard
np.set_printoptions(threshold=np.inf)


class HydrauTab(QScrollArea):
    """
    The class Hydro2W is the second tab of HABBY. It is the class containing
    all the classes/Widgets which are used to load the hydrological data.

    List of model supported by Hydro2W:
    files separetly. However, sometime the file was not found
    *   Telemac (2D)
    *   Hec-Ras (1.5D et 2D)
    *   Rubar BE et 2(1D et 2D)
    *   Mascaret (1D)
    *   River2D (2D)
    *   SW2D (2D)
    *   IBER2D (2D)

    **Technical comments**

    To call the different classes used to load the hydrological data, the user
    selects the name of the hydrological model from a QComboBox call self.mod.
    The method ‘selection_change” calls the class that the user chooses in
    self.mod. All the classes used to load the
    hydrological data are created when HABBY starts and are kept in a stack
    called self.stack. The function selection_change() just changes
    the selected item of the stack based on the user choice on self.mod.

    Any new hydrological model should also be added to the stack and to
    the list of models contained in self.mod

    In addition to the stack containing the hydrological information, hydro2W
    has two buttons. One button open a QMessageBox() which give information
    about the models, using the method “give_info_model”.  It is useful if a
    special type of file is needed to load the data from a model or to give
    extra information about one hydrological model. The text which is shown on
    the QMessageBox is given in one text file for each model.
    These text file are contained in the folder ‘model_hydro” which is
    in the HABBY folder. For the moment,
    there are models for which no text files have been prepared.
    The text file should have the following format:

    *	A short sentence with general info
    *	The keyword:  MORE INFO
    *	All other infomation which are needed.

    The second button allows the user to load an hdf5 file containing
    hydrological data from another project.
    As long as the hdf5 is in the right format, it does not matter from
    which hydrological model it was loaded from  or even if this
    hydrological model is supported by HABBY.
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):

        super(HydrauTab, self).__init__()
        self.tab_name = "hydraulic"
        self.tab_position = 1
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.hydraulic_model_information = HydraulicModelInformation()
        self.model_index = 0
        self.msgi = QMessageBox()
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
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        # frame
        hydrau_frame = QFrame()
        hydrau_frame.setFrameShape(QFrame.NoFrame)
        hydrau_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # model_list
        model_list_title_label = QLabel(self.tr("Select a model"))
        self.model_list_combobox = QComboBox()
        self.model_list_combobox.setMaxVisibleItems(len(self.hydraulic_model_information.name_models_gui_list) + 4)
        self.model_list_combobox.addItems([""] + self.hydraulic_model_information.name_models_gui_list)  # available model
        self.model_list_combobox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.info_model_pushbutton = QPushButton(self.tr('?'))
        self.info_model_pushbutton.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.info_model_pushbutton.clicked.connect(self.give_info_model)

        # model
        model_layout = QHBoxLayout()
        model_layout.addWidget(model_list_title_label)
        model_layout.addWidget(self.model_list_combobox)
        model_layout.addWidget(self.info_model_pushbutton)
        model_layout.addStretch()

        # model_group
        self.model_group = ModelInfoGroup(self.path_prj, self.name_prj, self.send_log, self.tr(""))
        self.model_group.hide()
        self.model_list_combobox.currentIndexChanged.connect(self.model_group.change_model_type_gui)

        # vertical layout
        self.setWidget(hydrau_frame)
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        hydrau_frame.setLayout(global_layout)
        global_layout.addLayout(model_layout)
        global_layout.addWidget(self.model_group)

        # global_layout.addStretch()

    def give_info_model(self):
        """
        A function to show extra information about each hydrological model.
        The information should be in a text file with the same name as the
        model in the model_hydo folder. General info goes as the start
         of the text file. If the text is too long, add the keyword "MORE INFO"
        and add the longer text afterwards.
        The message box will show the supplementary information only
        if the user asks for detailed information.
        """
        self.msgi.setIcon(QMessageBox.Information)
        text_title = self.tr("Information on the hydraulic model")
        mod_name = self.hydraulic_model_information.name_models_gui_list[self.model_list_combobox.currentIndex() - 1]
        mod_filename = self.hydraulic_model_information.attribute_models_list[self.model_list_combobox.currentIndex() - 1]
        website = self.hydraulic_model_information.website_models_list[self.model_list_combobox.currentIndex() - 1]
        self.msgi.setWindowTitle(text_title)
        info_filename = os.path.join('model_hydro', mod_filename + '.txt')
        self.msgi.setStandardButtons(QMessageBox.Ok)
        if os.path.isfile(info_filename):
            with open(info_filename, 'rt', encoding='utf8') as f:
                text = f.read()
            text2 = text.split('MORE INFO')
            self.msgi.setText('<a href="' + website + '">' + mod_name + "</a>" + text2[0])
            self.msgi.setDetailedText(text2[1])
        else:
            self.msgi.setText(self.tr('Choose a type of hydraulic model !         '))
            self.msgi.setDetailedText('No detailed info yet.')
        # detailed text erase the red x
        self.msgi.setEscapeButton(QMessageBox.Ok)
        name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
        self.msgi.setWindowIcon(QIcon(name_icon))
        self.msgi.show()

    def set_suffix_no_cut(self, no_cut_bool):
        if self.hydraulic_model_information.name_models_gui_list[self.model_index]:
            # get class
            current_model_class = getattr(self, self.hydraulic_model_information.attribute_models_list[self.model_index].lower())
            # get hdf5_name
            current_hdf5_name = current_model_class.hname.text()
            # add no_cut suffix if not exist
            if not no_cut_bool:
                # check if no_cut suffix exist
                if not "_no_cut" in os.path.splitext(current_hdf5_name)[0]:
                    # check if there is extension
                    if len(os.path.splitext(current_hdf5_name)[1]) > 1:
                        extension = os.path.splitext(current_hdf5_name)[1]
                    else:
                        extension = ""
                    # create new name
                    new_hdf5_name = os.path.splitext(current_hdf5_name)[0] + "_no_cut" + extension
                    # set new name
                    current_model_class.hname.setText(new_hdf5_name)
            # remove no_cut suffix if exist
            elif no_cut_bool:
                # check if no_cut suffix exist
                if "_no_cut" in os.path.splitext(current_hdf5_name)[0]:
                    # check if there is extension
                    if len(os.path.splitext(current_hdf5_name)[1]) > 1:
                        extension = os.path.splitext(current_hdf5_name)[1]
                    else:
                        extension = ""
                    # create new name
                    new_hdf5_name = os.path.splitext(current_hdf5_name)[0].replace("_no_cut", "") + extension
                    # set new name
                    current_model_class.hname.setText(new_hdf5_name)


class ModelInfoGroup(QGroupBox):
    """
    This class is a subclass of class QGroupBox.
    """
    send_log = pyqtSignal(str, name='send_log')
    drop_hydro = pyqtSignal()
    drop_merge = pyqtSignal()

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.path_last_file_loaded = self.path_prj
        self.hydraulic_model_information = HydraulicModelInformation()
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_prog)
        self.running_time = 0
        self.p = Process(target=None)  # second process
        self.q = Queue()
        self.progress_value = Value("d", 0)
        # get cmd
        if sys.argv[0][-3:] == ".py":
            self.exe_cmd = '"' + sys.executable + '" "' + sys.argv[0] + '"'
        else:
            self.exe_cmd = '"' + sys.executable + '"'
        self.mystdout = None
        self.init_ui()

    def init_ui(self):
        result_file_title_label = QLabel(self.tr('result file(s)'))
        self.input_file_combobox = QComboBox()
        self.input_file_combobox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # self.input_file_combobox.setToolTip(self.pathfile[0])  # ToolTip to indicated in which folder are the files
        self.select_file_button = QPushButton(self.tr('Choose file(s) (.txt)'))
        self.select_file_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.select_file_button.clicked.connect(self.select_file_and_show_informations_dialog)

        # reach
        reach_name_title_label = QLabel(self.tr('Reach name'))
        self.reach_name_combobox = QComboBox()
        self.reach_name_combobox.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # unit list
        unit_select_title_label = QLabel(self.tr('Unit selected'))
        self.units_QListWidget = QListWidgetClipboard()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.setMinimumHeight(100)

        # unit type
        units_name_title_label = QLabel(self.tr('Unit type'))
        self.units_name_label = QLabel(self.tr('unknown'))

        # unit number
        units_number_title_label = QLabel(self.tr('Unit number'))
        self.unit_number_label = QLabel(self.tr('unknown'))

        # usefull variables
        usefull_variable_label_title = QLabel(self.tr('Data detected'))
        self.usefull_variable_label = QLabel(self.tr('unknown'))

        # epsg
        epsg_title_label = QLabel(self.tr('EPSG code'))
        self.epsg_label = QLineEdit(self.tr('unknown'))

        # hdf5 name
        hdf5_name_title_label = QLabel(self.tr('.hyd file name'))
        self.hdf5_name_lineedit = QLineEdit()
        self.hdf5_name_lineedit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # load button
        self.create_hdf5_button = QPushButton(self.tr('Create .hyd file'))
        self.create_hdf5_button.setStyleSheet("background-color: #47B5E6; color: black")
        self.create_hdf5_button.clicked.connect(self.load_hydraulic_create_hdf5)

        # last_hydraulic_file_label
        self.last_hydraulic_file_label = QLabel(self.tr('Last file created'))
        self.last_hydraulic_file_name_label = QLabel(self.tr('no file'))

        # layout
        layout_ascii = QGridLayout()
        layout_ascii.addWidget(result_file_title_label, 0, 0)
        layout_ascii.addWidget(self.input_file_combobox, 0, 1)
        layout_ascii.addWidget(self.select_file_button, 0, 2)
        layout_ascii.addWidget(reach_name_title_label, 1, 0)
        layout_ascii.addWidget(self.reach_name_combobox, 1, 1)
        layout_ascii.addWidget(unit_select_title_label, 2, 0)
        layout_ascii.addWidget(self.units_QListWidget, 2, 1)
        layout_ascii.addWidget(units_name_title_label, 3, 0)
        layout_ascii.addWidget(self.units_name_label, 3, 1)
        layout_ascii.addWidget(units_number_title_label, 4, 0)
        layout_ascii.addWidget(self.unit_number_label, 4, 1)
        layout_ascii.addWidget(usefull_variable_label_title, 5, 0)
        layout_ascii.addWidget(self.usefull_variable_label, 5, 1, 1, 1)  # from row, from column, nb row, nb column
        layout_ascii.addWidget(epsg_title_label, 6, 0)
        layout_ascii.addWidget(self.epsg_label, 6, 1)
        layout_ascii.addWidget(hdf5_name_title_label, 7, 0)
        layout_ascii.addWidget(self.hdf5_name_lineedit, 7, 1)
        layout_ascii.addWidget(self.create_hdf5_button, 7, 2)
        layout_ascii.addWidget(self.last_hydraulic_file_label, 8, 0)
        layout_ascii.addWidget(self.last_hydraulic_file_name_label, 8, 1)
        [layout_ascii.setRowMinimumHeight(i, 30) for i in range(layout_ascii.rowCount())]

        self.setLayout(layout_ascii)

    def change_model_type_gui(self, i):
        """
        """
        self.hide()
        self.model_index = i - 1
        self.extension = self.hydraulic_model_information.extensions[self.model_index]
        self.model_type = self.hydraulic_model_information.attribute_models_list[self.model_index]
        self.nb_dim = self.hydraulic_model_information.dimensions[self.model_index]

        if i > 0:
            self.clean_gui()
            # extensions
            self.select_file_button.setText(self.tr('Choose file(s) (' + self.extension + ')'))

            self.show()

    def read_attribute_xml(self, att_here):
        """
        A function to read the text of an attribute in the xml project file.

        :param att_here: the attribute name (string).
        """
        data = ''

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            if att_here == "path_last_file_loaded":
                data = load_project_properties(self.path_prj)[att_here]
            else:
                data = load_project_properties(self.path_prj)[att_here]["path"]
        else:
            pass

        return data

    def save_xml(self):
        """
        A function to save the loaded data in the xml file.

        This function adds the name and the path of the newly chosen hydrological data to the xml project file. First,
        it open the xml project file (and send an error if the project is not saved, or if it cannot find the project
        file). Then, it opens the xml file and add the path and name of the file to this xml file. If the model data was
        already loaded, it adds the new name without erasing the old name IF the switch append_name is True. Otherwise,
        it erase the old name and replace it by a new name. The variable “i” has the same role than in select_file_and_show_informations_dialog.

        :param i: a int for the case where there is more than one file to load
        :param append_name: A boolean. If True, the name found will be append to the existing name in the xml file,
                instead of remplacing the old name by the new name.

        """
        filename_path_file = self.pathfile
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')

        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.end_log.emit('Error: The project is not saved. '
                              'Save the project in the General tab before saving hydrological data. \n')
        else:
            # change path_last_file_loaded, model_type (path)
            project_preferences = load_project_properties(self.path_prj)  # load_project_properties
            project_preferences["path_last_file_loaded"] = filename_path_file  # change value
            project_preferences[self.model_type]["path"] = filename_path_file  # change value
            save_project_properties(self.path_prj, project_preferences)  # save_project_properties

    def send_err_log(self, check_ok=False):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout before calling this function. It only sends the hundred first errors
        to avoid freezing the GUI. A similar function exists in estimhab_GUI.py. Correct both if necessary.

        :param check_ok: This is an optional paramter. If True, it checks if the function returns any error
        """
        error = False

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
                self.send_log.emit(QCoreApplication.translate("SubHydroW", 'Warning: too many information for the GUI'))
            if 'Error' in str_found[i] and check_ok:
                error = True
        if check_ok:
            return error

    def name_last_hdf5(self, type):
        """
        This function opens the xml project file to find the name of the last hdf5 merge file and to add it
        to the GUI on the QLabel self.lm2. It also add a QToolTip with the name of substrate and hydraulic files used
        to create this merge file. If there is no file found, this function do nothing.
        """
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        name = QCoreApplication.translate("SubHydroW", 'no file')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.send_log.emit('Error: ' + QCoreApplication.translate("SubHydroW", 'The project is not saved. '
                               'Save the project in the General tab before saving hydraulic data. \n'))
        else:
            project_preferences = load_project_properties(self.path_prj)
            if project_preferences[type]["hdf5"]:
                name = project_preferences[type]["hdf5"][-1]

            self.last_hydraulic_file_name_label.setText(name)

    def set_suffix_no_cut(self, no_cut_bool):
        if self.hydraulic_model_information.name_models_gui_list[self.mod_act]:
            # get class
            current_model_class = getattr(self, self.hydraulic_model_information.attribute_models_list[self.mod_act].lower())
            # get hdf5_name
            current_hdf5_name = current_model_class.hname.text()
            # add no_cut suffix if not exist
            if not no_cut_bool:
                # check if no_cut suffix exist
                if not "_no_cut" in os.path.splitext(current_hdf5_name)[0]:
                    # check if there is extension
                    if len(os.path.splitext(current_hdf5_name)[1]) > 1:
                        extension = os.path.splitext(current_hdf5_name)[1]
                    else:
                        extension = ""
                    # create new name
                    new_hdf5_name = os.path.splitext(current_hdf5_name)[0] + "_no_cut" + extension
                    # set new name
                    current_model_class.hname.setText(new_hdf5_name)
            # remove no_cut suffix if exist
            elif no_cut_bool:
                # check if no_cut suffix exist
                if "_no_cut" in os.path.splitext(current_hdf5_name)[0]:
                    # check if there is extension
                    if len(os.path.splitext(current_hdf5_name)[1]) > 1:
                        extension = os.path.splitext(current_hdf5_name)[1]
                    else:
                        extension = ""
                    # create new name
                    new_hdf5_name = os.path.splitext(current_hdf5_name)[0].replace("_no_cut", "") + extension
                    # set new name
                    current_model_class.hname.setText(new_hdf5_name)

    def clean_gui(self):
        self.input_file_combobox.clear()
        self.reach_name_combobox.clear()
        self.units_name_label.setText("unknown")  # kind of unit
        self.unit_number_label.setText("unknown")  # number units
        self.units_QListWidget.clear()
        self.epsg_label.clear()
        self.hdf5_name_lineedit.setText("")  # hdf5 name
        self.create_hdf5_button.setText(self.tr("Create .hyd file"))

    def select_file_and_show_informations_dialog(self):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """
        # get minimum water height as we might neglect very low water height
        self.project_preferences = load_project_properties(self.path_prj)

        # prepare the filter to show only useful files
        if len(self.extension.split(", ")) <= 4:
            filter2 = "File ("
            for e in self.extension.split(", "):
                filter2 += '*' + e + ' '
            filter2 = filter2[:-1]
            filter2 += ')' + ";; All File (*.*)"
        else:
            filter2 = ''

        # get last path
        if self.read_attribute_xml(self.model_type) != self.path_prj and self.read_attribute_xml(
                self.model_type) != "":
            model_path = self.read_attribute_xml(self.model_type)  # path spe
        elif self.read_attribute_xml("path_last_file_loaded") != self.path_prj and self.read_attribute_xml("path_last_file_loaded") != "":
            model_path = self.read_attribute_xml("path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        # find the filename based on user choice
        filename_list = QFileDialog().getOpenFileNames(self,
                                                     self.tr("Select file(s)"),
                                                     model_path,
                                                     filter2)

        # if file has been selected
        if filename_list[0]:
            # disconnect function for multiple file cases
            try:
                self.input_file_combobox.disconnect()
            except:
                pass

            try:
                self.reach_name_combobox.disconnect()
            except:
                pass

            try:
                self.units_QListWidget.disconnect()
            except:
                pass

            # init
            self.hydrau_case = "unknown"
            self.multi_hdf5 = False
            self.multi_reach = False
            self.index_hydrau_presence = False

            # get_hydrau_description_from_source
            hsra_value = HydraulicSimulationResultsAnalyzer(filename_list[0],
                                                               self.path_prj,
                                                               self.model_type,
                                                               self.nb_dim)

            # warnings
            if hsra_value.warning_list:
                for warn in hsra_value.warning_list:
                    self.send_log.emit(warn)

            # error
            if type(hsra_value.hydrau_description_list) == str:
                self.clean_gui()
                self.send_log.emit(hsra_value.hydrau_description_list)
                return

            # set to attribute
            self.hydrau_description_list = hsra_value.hydrau_description_list

            # display first hydrau_description_list
            self.hydrau_case = self.hydrau_description_list[0]["hydrau_case"]
            # change suffix
            if not self.project_preferences["cut_mesh_partialy_dry"]:
                for telemac_description_num in range(len(self.hydrau_description_list)):
                    namehdf5_old = os.path.splitext(self.hydrau_description_list[telemac_description_num]["hdf5_name"])[0]
                    exthdf5_old = os.path.splitext(self.hydrau_description_list[telemac_description_num]["hdf5_name"])[1]
                    self.hydrau_description_list[telemac_description_num]["hdf5_name"] = namehdf5_old + "_no_cut" + exthdf5_old
            # save last path
            self.pathfile = self.hydrau_description_list[0]["path_filename_source"]  # source file path
            self.namefile = self.hydrau_description_list[0]["filename_source"]  # source file name
            self.name_hdf5 = self.hydrau_description_list[0]["hdf5_name"]
            self.save_xml()
            # multi
            if len(self.hydrau_description_list) > 1:
                self.multi_hdf5 = True
            # multi
            if len(self.hydrau_description_list[0]["reach_list"]) > 1:
                self.multi_reach = True

            # get names
            names = [description["filename_source"] for description in self.hydrau_description_list]
            # to GUI (first decription)

            # clean GUI
            self.clean_gui()

            self.input_file_combobox.addItems(names)

            self.update_reach_from_input_file()
            self.input_file_combobox.currentIndexChanged.connect(self.update_reach_from_input_file)
            self.reach_name_combobox.currentIndexChanged.connect(self.update_unit_from_reach)
            self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)

    def update_reach_from_input_file(self):
        self.reach_name_combobox.blockSignals(True)
        self.reach_name_combobox.clear()
        self.reach_name_combobox.addItems(self.hydrau_description_list[0]["reach_list"])
        mesh_list = ", ".join(self.hydrau_description_list[0]["variable_name_unit_dict"].meshs().names_gui())
        node_list = ", ".join(self.hydrau_description_list[0]["variable_name_unit_dict"].nodes().names_gui())
        self.usefull_variable_label.setText("node : " + node_list + "\nmesh : " + mesh_list)

        self.units_name_label.setText(self.hydrau_description_list[0]["unit_type"])  # kind of unit

        self.update_unit_from_reach()

        self.epsg_label.setText(self.hydrau_description_list[0]["epsg_code"])
        self.hdf5_name_lineedit.setText(self.hydrau_description_list[0]["hdf5_name"])  # hdf5 name
        text_load_button = self.tr("Create ") + str(len(self.hydrau_description_list)) + self.tr(" .hyd file")
        if len(self.hydrau_description_list) > 1:
            text_load_button = text_load_button + "s"
        self.create_hdf5_button.setText(text_load_button)
        self.reach_name_combobox.blockSignals(False)

    def update_unit_from_reach(self):
        self.units_QListWidget.blockSignals(True)
        self.units_QListWidget.clear()
        self.units_QListWidget.addItems(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list_full"][self.reach_name_combobox.currentIndex()])
        if all(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list_tf"][self.reach_name_combobox.currentIndex()]):
            self.units_QListWidget.selectAll()
        else:
            for i in range(len(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list_full"][self.reach_name_combobox.currentIndex()])):
                self.units_QListWidget.item(i).setSelected(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list_tf"][self.reach_name_combobox.currentIndex()][i])
                self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
        self.units_QListWidget.blockSignals(False)
        self.unit_counter()

    def unit_counter(self):
        # count total number items (units)
        total = self.units_QListWidget.count()
        # count total number items selected
        selected = len(self.units_QListWidget.selectedItems())

        # refresh telemac dictonnary
        unit_list = []
        unit_list_full = []
        unit_list_tf = []
        for i in range(total):
            text = self.units_QListWidget.item(i).text()
            if self.units_QListWidget.item(i).isSelected():
                unit_list.append(text)
            unit_list_full.append(text)
            unit_list_tf.append(self.units_QListWidget.item(i).isSelected())
        # save multi
        self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list"][self.reach_name_combobox.currentIndex()] = list(unit_list)
        self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list_full"][self.reach_name_combobox.currentIndex()] = unit_list_full
        self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_list_tf"][self.reach_name_combobox.currentIndex()] = unit_list_tf
        self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_number"] = str(selected)

        if not self.project_preferences["cut_mesh_partialy_dry"]:
            namehdf5_old = \
            os.path.splitext(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["hdf5_name"])[0]
            exthdf5_old = \
            os.path.splitext(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["hdf5_name"])[1]
            if not "no_cut" in namehdf5_old:
                self.hydrau_description_list[self.input_file_combobox.currentIndex()][
                    "hdf5_name"] = namehdf5_old + "_no_cut" + exthdf5_old
        self.hdf5_name_lineedit.setText(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["hdf5_name"])  # hdf5 name

        # set text
        text = str(selected) + "/" + str(total)
        self.unit_number_label.setText(text)  # number units

    def create_script(self):
        # path_prj
        path_prj_script = self.path_prj + "_restarted"
        # script
        script_function_name = "LOAD_" + self.hydraulic_model_information.class_gui_models_list[self.model_index]
        cmd_str = self.exe_cmd + ' ' + script_function_name + \
                  ' inputfile="' + os.path.join(self.pathfile[0], self.namefile[0].replace(', ', ',')) + '"' + \
                  ' unit_list=' + str(self.hydrau_description_list[self.input_file_combobox.currentIndex()]['unit_list']).replace("\'", "'").replace(' ', '') + \
                  ' cut=' + str(self.project_preferences['cut_mesh_partialy_dry']) + \
                  ' outputfilename="' + self.name_hdf5 + '"' + \
                  ' path_prj="' + path_prj_script + '"'
        self.send_log.emit("script" + cmd_str)

    def load_hydraulic_create_hdf5(self):
        """
        The function which call the function which load telemac and
         save the name of files in the project file
        """
        """
        The function which call the function which load hec_ras2d and
         save the name of files in the project file
        """
        # get timestep and epsg selected
        for i in range(len(self.hydrau_description_list)):
            for reach_num in range(int(self.hydrau_description_list[i]["reach_number"])):
                if not any(self.hydrau_description_list[i]["unit_list_tf"][reach_num]):
                    self.send_log.emit("Error: " + self.tr("No units selected for : ") + self.hydrau_description_list[i]["filename_source"] + "\n")
                    return

        # check if extension is set by user (one hdf5 case)
        self.name_hdf5 = self.hdf5_name_lineedit.text()
        self.hydrau_description_list[self.input_file_combobox.currentIndex()]["hdf5_name"] = self.name_hdf5
        if self.name_hdf5 == "":
            self.send_log.emit('Error: ' + self.tr('.hyd output filename is empty. Please specify it.'))
            return

        # for error management and figures
        self.timer.start(100)

        # reset to 0
        self.progress_value.value = 0

        # show progressbar
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setVisible(True)

        # check if extension is set by user (multi hdf5 case)
        hydrau_description_multiple = list(self.hydrau_description_list)  # create copy to not erase inital choices
        for hdf5_num in range(len(hydrau_description_multiple)):
            if not os.path.splitext(hydrau_description_multiple[hdf5_num]["hdf5_name"])[1]:
                hydrau_description_multiple[hdf5_num]["hdf5_name"] = hydrau_description_multiple[hdf5_num]["hdf5_name"] + ".hyd"
            # refresh filename_source
            if self.hydrau_case == '2.a' or self.hydrau_case == '2.b':
                filename_source_list = hydrau_description_multiple[hdf5_num]["filename_source"].split(", ")
                new_filename_source_list = []
                for reach_num in range(len(hydrau_description_multiple[hdf5_num]["unit_list_tf"])):
                    for file_num, file in enumerate(filename_source_list):
                        if hydrau_description_multiple[hdf5_num]["unit_list_tf"][reach_num][file_num]:
                            new_filename_source_list.append(filename_source_list[file_num])
                hydrau_description_multiple[hdf5_num]["filename_source"] = ", ".join(new_filename_source_list)

        # get minimum water height as we might neglect very low water height
        self.project_preferences = load_project_properties(self.path_prj)

        # block button
        self.create_hdf5_button.setDisabled(True)  # hydraulic

        # write the new file name in the project file
        self.save_xml()

        # check cases
        for el in hydrau_description_multiple:
            print(el["unit_list"])

        self.q = Queue()
        self.progress_value = Value("d", 0)
        self.p = Process(target=hydraulic_process_mod.load_hydraulic_cut_to_hdf5,
                         args=(hydrau_description_multiple,
                               self.progress_value,
                               self.q,
                               False,
                               self.project_preferences))

        self.p.name = self.model_type + " data loading"
        self.p.start()

        # log info
        self.send_log.emit(self.tr('# Loading: ' + self.model_type + ' data...'))
        #self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit(
            "py    selafin_habby1.load_hec_ras2d_and_cut_grid('hydro_hec_ras2d_log', file1, path1, name_prj, "
            "path_prj, " + self.model_type + ", 2, path_prj, [], True )\n")
        # script
        self.create_script()
        self.send_log.emit("restart LOAD_" + self.model_type)

    def show_prog(self):
        """
        This function is call regularly by the methods which have a second thread (so moslty the function
        to load the hydrological data). To call this function regularly, the variable self.timer of QTimer type is used.
        The variable self.timer is connected to this function in the initiation of SubHydroW() and so in the initiation
        of all class which inherits from SubHydroW().

        This function just wait while the thread is alive. When it has terminated, it creates the figure and the error
        messages.
        """
        # RUNNING
        if self.p.is_alive():
            self.running_time += 0.100  # this is useful for GUI to update the running, should be logical with self.Timer()
            # get the language
            self.nativeParentWidget().kill_process.setVisible(True)

            # MERGE
            if self.model_type == 'HABITAT':
                self.send_log.emit("Process " +
                                   QCoreApplication.translate("SubHydroW", "'Merge Grid' is alive and run since ") + str(round(self.running_time)) + " sec")
                self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
            # SUBSTRATE
            elif self.model_type == 'SUBSTRATE':
                self.send_log.emit("Process " +
                                   QCoreApplication.translate("SubHydroW", "'Substrate' is alive and run since ") + str(round(self.running_time)) + " sec")
                self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
            # HYDRAULIC
            else:
                # it is necssary to start this string with Process to see it in the Statusbar
                self.send_log.emit("Process " +
                    QCoreApplication.translate("SubHydroW", "'Hydraulic' is alive and run since ") + str(round(self.running_time)) + " sec")
                self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))

        else:
            # FINISH (but can have known errors)
            if not self.q.empty():
                # manage error
                self.timer.stop()
                queue_back = self.q.get()
                if queue_back == "const_sub":  # sub cst case
                    const_sub = True
                else:
                    self.mystdout = queue_back
                    const_sub = False
                error = self.send_err_log(True)

                # known errors
                if error:
                    self.send_log.emit("clear status bar")
                    self.running_time = 0
                    self.nativeParentWidget().kill_process.setVisible(False)
                    # MERGE
                    if self.model_type == 'HABITAT' or self.model_type == 'LAMMI':
                        # unblock button merge
                        self.load_b2.setDisabled(False)  # merge
                    # SUBSTRATE
                    elif self.model_type == 'SUBSTRATE':
                        # unblock button substrate
                        self.load_polygon_substrate.setDisabled(False)  # substrate
                        self.load_point_substrate.setDisabled(False)  # substrate
                        self.load_constant_substrate.setDisabled(False)  # substrate
                    # HYDRAULIC
                    else:
                        # unblock button hydraulic
                        self.create_hdf5_button.setDisabled(False)  # hydraulic

                # finished without error
                elif not error:
                    # MERGE
                    if self.model_type == 'HABITAT' or self.model_type == 'LAMMI':
                        self.send_log.emit(
                            QCoreApplication.translate("SubHydroW", "Merging of substrate and hydraulic grid finished (computation time = ") + str(
                                round(self.running_time)) + " s).")
                        self.drop_merge.emit()
                        # update last name
                        self.name_last_hdf5("HABITAT")
                        # unblock button merge
                        self.load_b2.setDisabled(False)  # merge

                    # SUBSTRATE
                    elif self.model_type == 'SUBSTRATE':
                        self.send_log.emit(QCoreApplication.translate("SubHydroW", "Loading of substrate data finished (computation time = ") + str(
                            round(self.running_time)) + " s).")
                        self.drop_merge.emit()
                        # add the name of the hdf5 to the drop down menu so we can use it to merge with hydrological data
                        self.update_sub_hdf5_name()
                        # update last name
                        self.name_last_hdf5("SUBSTRATE")
                        # unblock button substrate
                        self.load_polygon_substrate.setDisabled(False)  # substrate
                        self.load_point_substrate.setDisabled(False)  # substrate
                        self.load_constant_substrate.setDisabled(False)  # substrate

                    # HYDRAULIC
                    else:
                        self.send_log.emit(QCoreApplication.translate("SubHydroW", "Loading of hydraulic data finished (computation time = ") + str(
                            round(self.running_time)) + " s).")
                        # send a signal to the substrate tab so it can account for the new info
                        self.drop_hydro.emit()
                        # update last name
                        self.name_last_hdf5(self.model_type)
                        if self.model_type == "ASCII":  # can produce .hab
                            self.drop_merge.emit()
                        # unblock button hydraulic
                        self.create_hdf5_button.setDisabled(False)  # hydraulic

                    # send round(c) to attribute .hyd
                    hdf5_hyd = hdf5_mod.Hdf5Management(self.path_prj, self.name_hdf5)
                    hdf5_hyd.set_hdf5_attributes([os.path.splitext(self.name_hdf5)[1][1:] + "_time_creation [s]"],
                                                 [round(self.running_time)])

                    # general
                    self.nativeParentWidget().progress_bar.setValue(100)
                    self.nativeParentWidget().kill_process.setVisible(False)
                    if not const_sub:
                        self.send_log.emit(QCoreApplication.translate("SubHydroW", "Outputs data can be displayed and exported from 'Data explorer' tab."))
                    if const_sub:
                        self.update_sub_hdf5_name()
                    self.send_log.emit("clear status bar")
                    # refresh plot gui list file
                    self.nativeParentWidget().central_widget.data_explorer_tab.refresh_type()
                    self.running_time = 0

            # CLEANING GUI
            if not self.p.is_alive() and self.q.empty():
                self.timer.stop()
                self.send_log.emit("clear status bar")
                self.nativeParentWidget().kill_process.setVisible(False)
                self.running_time = 0
                # MERGE
                if self.model_type == 'HABITAT' or self.model_type == 'LAMMI':
                    # unblock button merge
                    self.load_b2.setDisabled(False)  # merge
                # SUBSTRATE
                elif self.model_type == 'SUBSTRATE':
                    # unblock button substrate
                    self.load_polygon_substrate.setDisabled(False)  # substrate
                    self.load_point_substrate.setDisabled(False)  # substrate
                    self.load_constant_substrate.setDisabled(False)  # substrate
                # HYDRAULIC
                else:
                    # unblock button hydraulic
                    self.create_hdf5_button.setDisabled(False)  # hydraulic
                    if self.model_type == "ASCII":  # can produce .hab
                        self.drop_merge.emit()
                # CRASH
                if self.p.exitcode == 1:
                    self.send_log.emit(QCoreApplication.translate("SubHydroW",
                                                                  "Error : Process crashed !! Restart HABBY. Retry. If same, contact the HABBY team."))
