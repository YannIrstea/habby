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
from multiprocessing import Process, Queue, Value, Event
import numpy as np
from copy import deepcopy
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, \
    QLabel, QGridLayout, \
    QLineEdit, QFileDialog, \
    QComboBox, QMessageBox, QGroupBox, QRadioButton, \
    QAbstractItemView, QScrollArea, QFrame, QVBoxLayout, QSizePolicy, \
    QHBoxLayout

from src.hydraulic_results_manager_mod import HydraulicSimulationResultsAnalyzer
from src.hydraulic_result_mod import HydraulicModelInformation
from src.project_properties_mod import load_project_properties, save_project_properties, load_specific_properties
from src_GUI.dev_tools_GUI import QListWidgetClipboard
from src_GUI.process_manager_GUI import ProcessProgLayout

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
        self.info_model_pushbutton = QPushButton('?')
        widget_height = self.model_list_combobox.minimumSizeHint().height()
        self.info_model_pushbutton.setFixedHeight(widget_height)
        self.info_model_pushbutton.setFixedWidth(widget_height)
        self.info_model_pushbutton.clicked.connect(self.give_info_model_dialog)

        # info_model_label
        self.info_model_label = QLabel("")

        # model
        model_layout = QHBoxLayout()
        model_layout.addWidget(model_list_title_label)
        model_layout.addWidget(self.model_list_combobox)
        model_layout.addWidget(self.info_model_pushbutton)
        model_layout.addWidget(self.info_model_label)
        model_layout.addStretch()

        # model_group
        self.model_group = ModelInfoGroup(self.path_prj, self.name_prj, self.send_log, self.tr(""))
        self.model_group.hide()
        self.model_list_combobox.currentIndexChanged.connect(self.change_model_type_gui)

        # vertical layout
        self.setWidget(hydrau_frame)
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        hydrau_frame.setLayout(global_layout)
        global_layout.addLayout(model_layout)
        global_layout.addWidget(self.model_group)

        # global_layout.addStretch()

        # # shortcut to change tab (ENTER)
        # self.keyboard_change_tab_filter = EnterPressEvent()
        # self.installEventFilter(self.keyboard_change_tab_filter)
        # self.keyboard_change_tab_filter.enter_signal.connect(self.model_group.load_hydraulic_create_hdf5)

    def change_model_type_gui(self, i):
        """
        """
        self.model_group.hide()
        self.model_group.model_index = i - 1
        self.model_group.extension = self.hydraulic_model_information.extensions[self.model_group.model_index]
        self.model_group.model_type = self.hydraulic_model_information.attribute_models_list[self.model_group.model_index]
        self.model_group.nb_dim = self.hydraulic_model_information.dimensions[self.model_group.model_index]
        self.info_model_label.setText("")
        if i > 0:
            self.give_info_model_label()

            # model_group
            self.model_group.clean_gui()
            # extensions
            # self.select_file_button.setText(self.tr('Choose file(s) (' + self.extension + ')'))
            if self.model_group.model_type == "lammi":
                self.model_group.update_for_lammi(on=True)
            else:
                self.model_group.update_for_lammi(on=False)

            self.model_group.result_file_title_label.setText(self.tr('Result file (') + self.model_group.extension + ')')
            self.model_group.name_last_hdf5(self.model_group.model_type)
            self.model_group.show()

    def give_info_model_dialog(self):
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
        name_icon = os.path.join(os.getcwd(), "file_dep", "habby_icon.png")
        self.msgi.setWindowIcon(QIcon(name_icon))
        self.msgi.show()

    def give_info_model_label(self):
        # 2d informations
        if self.model_group.nb_dim == "2":
            self.info_model_label.setText(
                self.tr("Semi wet cut mesh enable : ") + str(
                    load_specific_properties(self.path_prj, ["cut_mesh_partialy_dry"])[0]) + "\n" +
                self.tr("Water depth value considered to be zero : ") + str(
                    load_specific_properties(self.path_prj, ["min_height_hyd"])[0]) + " m")
        elif self.model_group.nb_dim == "1":
            self.info_model_label.setText(
                self.tr("Semi wet cut mesh enable always disabled for 1D models") + "\n" +
                self.tr("No water depth value considered to be zero for 1D models"))
        else:
            self.info_model_label.setText("\n")

    def set_suffix_no_cut(self, no_cut_bool):
        if self.model_list_combobox.currentIndex() > 0:
            if self.hydraulic_model_information.name_models_gui_list[self.model_group.model_index]:
                if self.hydraulic_model_information.dimensions[self.model_group.model_index] == "2":
                    # give_info_model_label
                    self.give_info_model_label()
                    # get hdf5_name
                    current_hdf5_name = self.model_group.hdf5_name_lineedit.text()
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
                            self.model_group.hdf5_name_lineedit.setText(new_hdf5_name)
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
                            self.model_group.hdf5_name_lineedit.setText(new_hdf5_name)


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
        self.running_time = 0
        self.stop = Event()
        self.q = Queue()
        self.progress_value = Value("d", 0)
        self.p = Process(target=None)
        self.model_index = None
        self.progress_value = Value("d", 0)
        self.mystdout = None
        self.drop_hydro.connect(lambda: self.name_last_hdf5(self.model_type))
        self.init_ui()

    def init_ui(self):
        self.result_file_title_label = QLabel(self.tr('Result file'))
        self.input_file_combobox = QComboBox()
        self.select_file_button = QPushButton("...")
        self.select_file_button.setToolTip(self.tr("Select file(s)"))
        self.select_file_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        widget_height = self.input_file_combobox.minimumSizeHint().height()
        self.select_file_button.setFixedHeight(widget_height)
        self.select_file_button.setFixedWidth(widget_height)
        self.select_file_button.clicked.connect(self.select_file_and_show_informations_dialog)

        # selection_layout
        self.selection_layout = QHBoxLayout()
        self.selection_layout.addWidget(self.input_file_combobox)
        self.selection_layout.addWidget(self.select_file_button)

        # reach
        reach_name_title_label = QLabel(self.tr('Reach name'))
        self.reach_name_combobox = QComboBox()

        # unit list
        unit_title_label = QLabel(self.tr('Unit name'))
        self.units_QListWidget = QListWidgetClipboard()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # unit type
        units_name_title_label = QLabel(self.tr('Type'))
        self.units_name_label = QLabel(self.tr('unknown'))

        # unit number
        units_number_title_label = QLabel(self.tr('Number'))
        self.unit_number_label = QLabel(self.tr('unknown'))

        # unit_layout
        unit_layout = QGridLayout()
        unit_layout.addWidget(self.units_QListWidget, 0, 0, 4, 1)
        unit_layout.addWidget(units_name_title_label, 0, 1, Qt.AlignBottom)
        unit_layout.addWidget(self.units_name_label, 1, 1, Qt.AlignTop)
        unit_layout.addWidget(units_number_title_label, 2, 1, Qt.AlignBottom)
        unit_layout.addWidget(self.unit_number_label, 3, 1, Qt.AlignTop)

        # usefull_mesh_variables
        usefull_mesh_variable_label_title = QLabel(self.tr('Mesh data'))
        # usefull_mesh_variable_label_title.setFixedHeight(widget_height)
        self.usefull_mesh_variable_label = QLabel(self.tr('unknown'))

        # usefull_node_variables
        usefull_node_variable_label_title = QLabel(self.tr('Node data'))
        # usefull_node_variable_label_title.setFixedHeight(widget_height)
        self.usefull_node_variable_label = QLabel(self.tr('unknown'))

        # LAMMI substrate
        classification_code_title_label = QLabel(self.tr('Sub classification code'))
        classification_code_title_label.setToolTip(self.tr("LAMMI data substrate classification code"))
        self.sub_classification_code_edf_radio = QRadioButton("EDF")
        self.sub_classification_code_edf_radio.setToolTip(self.tr("8 EDF classes"))
        self.sub_classification_code_edf_radio.setChecked(True)
        self.sub_classification_code_cemagref_radio = QRadioButton("Cemagef")
        self.sub_classification_code_cemagref_radio.setToolTip(self.tr("8 Cemagref classes"))
        self.sub_classification_code_sandre_radio = QRadioButton("Sandre")
        self.sub_classification_code_sandre_radio.setToolTip(self.tr("12 SANDRE classes"))
        sub_classification_code_frame = QFrame()
        radio_layout_1 = QHBoxLayout(sub_classification_code_frame)
        radio_layout_1.setAlignment(Qt.AlignLeft)
        radio_layout_1.addWidget(self.sub_classification_code_edf_radio)
        radio_layout_1.addWidget(self.sub_classification_code_cemagref_radio)
        radio_layout_1.addWidget(self.sub_classification_code_sandre_radio)

        # LAMMI equation
        equation_title_label = QLabel(self.tr('Equation mode'))
        equation_title_label.setToolTip(self.tr("LAMMI hydraulic data equation mode"))
        self.sub_equation_fe_radio = QRadioButton(self.tr("Finite element"))
        self.sub_equation_fe_radio.setToolTip(self.tr("Vertical 1D hydraulic profile data set to node."))
        self.sub_equation_fe_radio.setChecked(True)
        self.sub_equation_fv_radio = QRadioButton(self.tr("Finite volume"))
        self.sub_equation_fv_radio.setToolTip(self.tr("Vertical 1D hydraulic profile data set to mesh."))
        equation_frame = QFrame()
        radio_layout_2 = QHBoxLayout(equation_frame)
        radio_layout_2.setAlignment(Qt.AlignLeft)
        radio_layout_2.addWidget(self.sub_equation_fe_radio)
        radio_layout_2.addWidget(self.sub_equation_fv_radio)

        # epsg
        epsg_title_label = QLabel(self.tr('EPSG code'))
        self.epsg_label = QLineEdit(self.tr('unknown'))
        # self.epsg_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.epsg_label.returnPressed.connect(self.load_hydraulic_create_hdf5)

        # hdf5 name
        hdf5_name_title_label = QLabel(self.tr('.hyd file name'))
        self.hdf5_name_lineedit = QLineEdit()
        self.hdf5_name_lineedit.returnPressed.connect(self.load_hydraulic_create_hdf5)

        # last_hydraulic_file_label
        self.last_hydraulic_file_label = QLabel(self.tr('Last file created'))
        self.last_hydraulic_file_name_label = QLabel(self.tr('no file'))

        # progress_layout
        self.progress_layout = ProcessProgLayout(self.load_hydraulic_create_hdf5,
                                                 send_log=self.send_log,
                                                 process_type="hyd",
                                                 send_refresh_filenames=self.drop_hydro)

        # layout
        self.hydrau_layout = QGridLayout()
        self.hydrau_layout.addWidget(self.result_file_title_label, 0, 0)
        self.hydrau_layout.addLayout(self.selection_layout, 0, 1)
        self.hydrau_layout.addWidget(reach_name_title_label, 1, 0)
        self.hydrau_layout.addWidget(self.reach_name_combobox, 1, 1)
        self.hydrau_layout.addWidget(unit_title_label, 3, 0)
        self.hydrau_layout.addLayout(unit_layout, 3, 1)
        self.hydrau_layout.addWidget(usefull_mesh_variable_label_title, 5, 0)
        self.hydrau_layout.addWidget(self.usefull_mesh_variable_label, 5, 1)  # from row, from column, nb row, nb column
        self.hydrau_layout.addWidget(usefull_node_variable_label_title, 6, 0)
        self.hydrau_layout.addWidget(self.usefull_node_variable_label, 6, 1)  # from row, from column, nb row, nb column

        self.hydrau_layout.addWidget(classification_code_title_label, 7, 0)
        self.hydrau_layout.addWidget(sub_classification_code_frame, 7, 1)

        self.hydrau_layout.addWidget(equation_title_label, 8, 0)
        self.hydrau_layout.addWidget(equation_frame, 8, 1)

        self.hydrau_layout.addWidget(epsg_title_label, 9, 0)
        self.hydrau_layout.addWidget(self.epsg_label, 9, 1)
        self.hydrau_layout.addWidget(hdf5_name_title_label, 10, 0)
        self.hydrau_layout.addWidget(self.hdf5_name_lineedit, 10, 1)
        self.hydrau_layout.addLayout(self.progress_layout, 11, 0, 1, 2)
        self.hydrau_layout.addWidget(self.last_hydraulic_file_label, 12, 0)
        self.hydrau_layout.addWidget(self.last_hydraulic_file_name_label, 12, 1)
        self.setLayout(self.hydrau_layout)

    def update_for_lammi(self, on=False):
        if on:
            self.hydrau_layout.itemAtPosition(7, 0).widget().show()
            self.hydrau_layout.itemAtPosition(7, 1).widget().show()
            self.hydrau_layout.itemAtPosition(8, 0).widget().show()
            self.hydrau_layout.itemAtPosition(8, 1).widget().show()
        else:
            self.hydrau_layout.itemAtPosition(7, 0).widget().hide()
            self.hydrau_layout.itemAtPosition(7, 1).widget().hide()
            self.hydrau_layout.itemAtPosition(8, 0).widget().hide()
            self.hydrau_layout.itemAtPosition(8, 1).widget().hide()

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
            project_properties = load_project_properties(self.path_prj)  # load_project_properties
            project_properties["path_last_file_loaded"] = filename_path_file  # change value
            project_properties[self.model_type]["path"] = filename_path_file  # change value
            save_project_properties(self.path_prj, project_properties)  # save_project_properties

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
            project_properties = load_project_properties(self.path_prj)
            if project_properties[type]["hdf5"]:
                name = project_properties[type]["hdf5"][-1] 

            self.last_hydraulic_file_name_label.setText(name)

    def clean_gui(self):
        self.input_file_combobox.clear()
        self.reach_name_combobox.clear()
        self.units_name_label.setText("unknown")  # kind of unit
        self.unit_number_label.setText("unknown")  # number units
        self.units_QListWidget.clear()
        self.epsg_label.clear()
        self.hdf5_name_lineedit.setText("")  # hdf5 name
        self.progress_layout.run_stop_button.setText(self.tr("Create .hyd file"))

    def select_file_and_show_informations_dialog(self):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """
        # get minimum water height as we might neglect very low water height
        self.project_properties = load_project_properties(self.path_prj)

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
        if self.extension:
            filename_list = QFileDialog().getOpenFileNames(self,
                                                     self.tr("Select file(s)"),
                                                     model_path,
                                                     filter2)
        else:
            filename_list = QFileDialog().getExistingDirectory(self,
                                                     self.tr("Select directory"),
                                                     model_path)
            filename_list = [filename_list]

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
                                                               self.model_type)

            # warnings
            if hsra_value.warning_list:
                for warn in hsra_value.warning_list:
                    self.send_log.emit(warn)
                    if "Error:" in warn:
                        self.clean_gui()
                        return

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
            if not self.project_properties["cut_mesh_partialy_dry"] and self.hydrau_description_list[0]["model_dimension"] == "2":
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

            # clean GUI
            self.clean_gui()

            self.input_file_combobox.addItems(names)

            self.update_reach_from_input_file()
            self.input_file_combobox.currentIndexChanged.connect(self.update_reach_from_input_file)
            self.reach_name_combobox.currentIndexChanged.connect(self.update_unit_from_reach)
            self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)

            self.hdf5_name_lineedit.setFocus()

    def update_reach_from_input_file(self):
        self.reach_name_combobox.blockSignals(True)
        self.reach_name_combobox.clear()
        self.reach_name_combobox.addItems(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["reach_list"])
        width_char = 120
        mesh_list = ", ".join(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["variable_name_unit_dict"].meshs().names_gui())
        if len(mesh_list) > width_char:
            self.usefull_mesh_variable_label.setText(mesh_list[:width_char] + "...")
            self.usefull_mesh_variable_label.setToolTip(mesh_list)
        else:
            self.usefull_mesh_variable_label.setText(mesh_list)
        node_list = ", ".join(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["variable_name_unit_dict"].nodes().names_gui())
        if len(node_list) > width_char:
            self.usefull_node_variable_label.setText(node_list[:width_char] + "...")
            self.usefull_node_variable_label.setToolTip(node_list)
        else:
            self.usefull_node_variable_label.setText(node_list)
        self.units_name_label.setText(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["unit_type"])  # kind of unit
        self.update_unit_from_reach()
        self.epsg_label.setText(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["epsg_code"])
        self.hdf5_name_lineedit.setText(self.hydrau_description_list[self.input_file_combobox.currentIndex()]["hdf5_name"])  # hdf5 name
        extension = "hyd"
        if self.hydrau_description_list[self.input_file_combobox.currentIndex()]["sub"]:
            extension = "hab"
        text_load_button = self.tr("Create ") + str(len(self.hydrau_description_list)) + self.tr(" file ") + "." + extension
        if len(self.hydrau_description_list) > 1:
            text_load_button = self.tr("Create ") + str(len(self.hydrau_description_list)) + self.tr(" files ") + "." + extension
        self.progress_layout.run_stop_button.setText(text_load_button)
        self.progress_layout.progress_bar.setValue(0.0)
        self.progress_layout.progress_label.setText("{0:.0f}/{1:.0f}".format(0.0, len(self.hydrau_description_list)))
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
        hyd_desc_index = self.input_file_combobox.currentIndex()
        reach_index = self.reach_name_combobox.currentIndex()
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
        self.hydrau_description_list[hyd_desc_index]["unit_list"][reach_index] = list(unit_list)
        self.hydrau_description_list[hyd_desc_index]["unit_list_full"][reach_index] = unit_list_full
        self.hydrau_description_list[hyd_desc_index]["unit_list_tf"][reach_index] = unit_list_tf
        self.hydrau_description_list[hyd_desc_index]["unit_number"] = str(selected)

        if self.hydrau_case == '2.a' or self.hydrau_case == '2.b':
            # preset name hdf5
            filename_source_list = self.hydrau_description_list[hyd_desc_index]["filename_source"].split(", ")
            new_names_list = []
            for file_num, file in enumerate(filename_source_list):
                if self.hydrau_description_list[hyd_desc_index]["unit_list_tf"][reach_index][file_num]:
                    new_names_list.append(os.path.splitext(file)[0])
            self.hydrau_description_list[hyd_desc_index]["hdf5_name"] = "_".join(new_names_list) + ".hyd"
            if len(filename_source_list) == len(new_names_list) and len(self.hydrau_description_list[hyd_desc_index]["hdf5_name"]) > 25:
                self.hydrau_description_list[hyd_desc_index]["hdf5_name"] = new_names_list[0].replace(".", "_") \
                                                                                        + "_to_" + \
                                                                                        new_names_list[-1].replace(".", "_") + ".hyd"

        if not load_specific_properties(self.path_prj, ["cut_mesh_partialy_dry"])[0] and self.hydrau_description_list[hyd_desc_index]["model_dimension"] == "2":
            namehdf5_old = \
            os.path.splitext(self.hydrau_description_list[hyd_desc_index]["hdf5_name"])[0]
            exthdf5_old = \
            os.path.splitext(self.hydrau_description_list[hyd_desc_index]["hdf5_name"])[1]
            if not "no_cut" in namehdf5_old:
                self.hydrau_description_list[hyd_desc_index][
                    "hdf5_name"] = namehdf5_old + "_no_cut" + exthdf5_old

        self.hdf5_name_lineedit.setText(self.hydrau_description_list[hyd_desc_index]["hdf5_name"])  # hdf5 name

        # set text
        text = str(selected) + "/" + str(total)
        self.unit_number_label.setText(text)  # number units

        self.progress_layout.run_stop_button.setEnabled(True)

    def load_hydraulic_create_hdf5(self):
        """
        The function which call the function which load telemac and
         save the name of files in the project file
        """
        """
        The function which call the function which load hec_ras2d and
         save the name of files in the project file
        """
        if self.progress_layout.run_stop_button.isEnabled():
            # get minimum water height as we might neglect very low water height
            self.project_properties = load_project_properties(self.path_prj)

            # get timestep and epsg selected
            for i in range(len(self.hydrau_description_list)):
                for reach_number in range(int(self.hydrau_description_list[i]["reach_number"])):
                    if not any(self.hydrau_description_list[i]["unit_list_tf"][reach_number]):
                        self.send_log.emit("Error: " + self.tr("No units selected for : ") + self.hydrau_description_list[i]["filename_source"] + "\n")
                        return

            # check if extension is set by user (one hdf5 case)
            self.name_hdf5 = self.hdf5_name_lineedit.text()
            self.hydrau_description_list[self.input_file_combobox.currentIndex()]["hdf5_name"] = self.name_hdf5
            if self.name_hdf5 == "":
                self.send_log.emit('Error: ' + self.tr('.hyd output filename is empty. Please specify it.'))
                return

            # check if extension is set by user (multi hdf5 case)
            hydrau_description_multiple = deepcopy(self.hydrau_description_list)  # create copy to not erase inital choices
            for hdf5_num in range(len(hydrau_description_multiple)):
                if not os.path.splitext(hydrau_description_multiple[hdf5_num]["hdf5_name"])[1]:
                    hydrau_description_multiple[hdf5_num]["hdf5_name"] = hydrau_description_multiple[hdf5_num]["hdf5_name"] + ".hyd"
                # refresh filename_source
                if self.hydrau_case == '2.a' or self.hydrau_case == '2.b':
                    filename_source_list = hydrau_description_multiple[hdf5_num]["filename_source"].split(", ")
                    new_filename_source_list = []
                    for reach_number in range(len(hydrau_description_multiple[hdf5_num]["unit_list_tf"])):
                        for file_num, file in enumerate(filename_source_list):
                            if hydrau_description_multiple[hdf5_num]["unit_list_tf"][reach_number][file_num]:
                                new_filename_source_list.append(filename_source_list[file_num])
                    hydrau_description_multiple[hdf5_num]["filename_source"] = ", ".join(new_filename_source_list)

            # process_manager
            self.progress_layout.process_manager.set_hyd_mode(self.path_prj, hydrau_description_multiple, self.project_properties)

            # process_prog_show
            self.progress_layout.start_process()

            # script
            self.create_script(hydrau_description_multiple)

    def create_script(self, hydrau_description_multiple):
        # path_prj
        path_prj_script = self.path_prj + "_restarted"

        # cli
        if sys.argv[0][-3:] == ".py":
            exe_cmd = '"' + sys.executable + '" "' + sys.argv[0] + '"'
        else:
            exe_cmd = '"' + sys.executable + '"'
        script_function_name = "CREATE_HYD"
        cmd_str = exe_cmd + ' ' + script_function_name + \
                  ' model="' + self.model_type + '"' + \
                  ' inputfile="' + os.path.join(self.path_prj, "input", self.name_hdf5.split(".")[0], "indexHYDRAU.txt") + '"' + \
                  ' unit_list=' + str(self.hydrau_description_list[self.input_file_combobox.currentIndex()]['unit_list'][0]).replace("\'", "'").replace(' ', '') + \
                  ' cut=' + str(self.project_properties['cut_mesh_partialy_dry']) + \
                  ' outputfilename="' + self.name_hdf5 + '"' + \
                  ' path_prj="' + path_prj_script + '"'
        self.send_log.emit("script" + cmd_str)

        # py
        cmd_str = F"\t# CREATE_HYD\n" \
                  F"\tfrom src.hydraulic_process_mod import HydraulicSimulationResultsAnalyzer, load_hydraulic_cut_to_hdf5\n\n"
        cmd_str = cmd_str + F'\thsra_value = HydraulicSimulationResultsAnalyzer(filename_path_list=[{repr(os.path.join(self.path_prj, "input", self.name_hdf5.split(".")[0], "indexHYDRAU.txt"))}], ' \
                  F"\tpath_prj={repr(path_prj_script)}, " \
                  F"\tmodel_type={repr(self.model_type)}, " \
                  F"\tnb_dim={repr(str(self.nb_dim))})\n"
        cmd_str = cmd_str + F"\tfor hdf5_file_index in range(0, len(hsra_value.hydrau_description_list)):\n" \
                            F"\t\tprogress_value = Value('d', 0.0)\n" \
                            F"\t\tq = Queue()\n" \
                            F"\t\tload_hydraulic_cut_to_hdf5(hydrau_description=hsra_value.hydrau_description_list[hdf5_file_index], " \
                            F"\tprogress_value=progress_value, " \
                            F"\tq=q, " \
                            F"\tprint_cmd=True, " \
                            F"\tproject_properties=load_project_properties({repr(path_prj_script)}))" + "\n"
        self.send_log.emit("py" + cmd_str)