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
from multiprocessing import Process, Queue, Value, Event
import numpy as np
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QPushButton, \
    QLabel, QGridLayout, \
    QLineEdit, QFileDialog, QSpacerItem, \
    QComboBox, QMessageBox, QGroupBox, \
    QRadioButton, QScrollArea, QFrame, QVBoxLayout, QSizePolicy, \
    QHBoxLayout
from lxml import etree as ET

import src.merge
import src.substrate_mod
import src.tools_mod
from src import hdf5_mod
from src import substrate_mod
from src.project_properties_mod import load_project_properties, load_specific_properties, save_project_properties
from src.tools_mod import QGroupBoxCollapsible
from src_GUI.tools_GUI import change_button_color
np.set_printoptions(threshold=np.inf)


class SubstrateTab(QScrollArea):
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
        super(SubstrateTab, self).__init__()
        self.tab_name = "substrate"
        self.tab_position = 2
        self.path_prj = path_prj
        self.name_prj = name_prj
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

        # empty frame scrolable
        content_widget = QFrame()
        layout = QVBoxLayout(content_widget)
        self.sub_and_merge = SubstrateAndMerge(self.path_prj, self.name_prj, self.send_log)
        layout.addWidget(self.sub_and_merge)

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)


class SubstrateAndMerge(QWidget):
    """
    This is the widget used to load the substrate. It is practical to re-use some of the method from SubHydroW.
    So this class inherit from SubHydroW.
    """
    send_log = pyqtSignal(str, name='send_log')
    drop_hydro = pyqtSignal()
    drop_merge = pyqtSignal()
    """
    A pyqtsignal which signal that merged hydro data is ready. The signal is for the bioinfo_tab and is collected
    by MainWindows1.py.
    """

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.namefile = [""]
        self.pathfile = [""]
        self.stop = Event()
        self.q = Queue()
        self.progress_value = Value("d", 0)
        self.p = Process(target=None)
        # update attribute
        self.sub_description = None
        self.attributexml = ['substrate_path', 'att_name']
        self.model_type = 'SUBSTRATE'
        self.data_type = "SUBSTRATE"
        self.name_att = ''
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_prog)
        self.running_time = 0
        self.max_lengthshow = 90  # the maximum length of a file name to be show in full
        self.nb_dim = 10  # just to ckeck
        self.hname2 = QLineEdit('Sub_CONST')
        self.hname2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # order and name matters here!
        # change with caution!
        # roughness height if ok with George
        self.substrate_classification_codes = ['Cemagref', 'Sandre']
        self.substrate_classification_methods = ['coarser-dominant', 'percentage']
        self.pathfile_polygon = ''
        self.lasf_hdf5 = ''

        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__().
        """

        # choose between loading substrate by polygon, point or constant
        l1 = QLabel(self.tr('Substrate mapping method from'))
        sub_spacer = QSpacerItem(1, 10)
        self.polyg_radiobutton = QRadioButton(self.tr('polygons (.shp, .gpkg)'))
        self.point_radiobutton = QRadioButton(self.tr('points (.txt, .shp, .gpkg)'))
        self.constant_radiobutton = QRadioButton(self.tr('constant values (.txt)'))
        self.polyg_radiobutton.setChecked(True)
        self.polyg_radiobutton.clicked.connect(lambda: self.btnstate(self.polyg_radiobutton, self.point_radiobutton, self.constant_radiobutton))
        self.polyg_radiobutton.clicked.connect(self.add_polygon_widgets)
        self.point_radiobutton.clicked.connect(lambda: self.btnstate(self.point_radiobutton, self.polyg_radiobutton, self.constant_radiobutton))
        self.point_radiobutton.clicked.connect(self.add_point_widgets)
        self.constant_radiobutton.clicked.connect(lambda: self.btnstate(self.constant_radiobutton, self.point_radiobutton, self.polyg_radiobutton))
        self.constant_radiobutton.clicked.connect(self.add_const_widgets)

        # POLYGON (0 line)
        filetitle_polygon_label = QLabel(self.tr('File'))
        self.file_polygon_label = QLabel("", self)
        self.file_polygon_label.setToolTip(self.pathfile_polygon)
        self.sub_choosefile_polygon = QPushButton(self.tr('Choose file (.shp, .gpkg)'), self)
        self.sub_choosefile_polygon.clicked.connect(lambda: self.show_dialog_substrate("polygon"))
        # POLYGON (1 line)
        classification_codetitle_polygon_label = QLabel(self.tr('Classification code'))
        self.sub_classification_code_polygon_label = QLabel(self.tr('unknown'))
        # POLYGON (2 line)
        classification_methodtitle_polygon_label = QLabel(self.tr('Classification method'))
        self.sub_classification_method_polygon_label = QLabel(self.tr('unknown'))
        # POLYGON (3 line)
        default_valuestitle_polygon_label = QLabel(self.tr('Default values'))
        self.sub_default_values_polygon_label = QLabel(self.tr('unknown'))
        # POLYGON (4 line)
        epsgtitle_polygon_label = QLabel(self.tr('EPSG code'))
        self.epsg_polygon_label = QLabel(self.tr('unknown'))
        # POLYGON (5 line)
        hab_filenametitle_polygon_label = QLabel(self.tr('.sub file name'))
        self.polygon_hname = QLineEdit('')  # hdf5 name
        self.load_polygon_substrate_pushbutton = QPushButton(self.tr('Create .sub file'), self)
        change_button_color(self.load_polygon_substrate_pushbutton, "#47B5E6")
        self.load_polygon_substrate_pushbutton.clicked.connect(lambda: self.load_sub_gui('polygon'))
        self.load_polygon_substrate_pushbutton.setEnabled(False)

        # POINT (0 line)
        filetitle_point_label = QLabel(self.tr('File'))
        self.file_point_label = QLabel(self.namefile[0], self)
        self.file_point_label.setToolTip(self.pathfile[0])
        self.sub_choosefile_point = QPushButton(self.tr('Choose file (.txt, .shp, .gpkg)'), self)
        self.sub_choosefile_point.clicked.connect(lambda: self.show_dialog_substrate("point"))
        self.sub_choosefile_point.clicked.connect(lambda: self.file_point_label.setToolTip(self.pathfile[0]))
        self.sub_choosefile_point.clicked.connect(lambda: self.file_point_label.setText(self.namefile[0]))
        # POINT (1 line)
        classification_codetitle_point_label = QLabel(self.tr('Classification code'))
        self.sub_classification_code_point_label = QLabel(self.tr('unknown'))
        # POINT (2 line)
        classification_methodtitle_point_label = QLabel(self.tr('Classification method'))
        self.sub_classification_method_point_label = QLabel(self.tr('unknown'))
        # POINT (3 line)
        default_valuestitle_point_label = QLabel(self.tr('Default values'))
        self.sub_default_values_point_label = QLabel(self.tr('unknown'))
        # POINT (4 line)
        epsgtitle_point_label = QLabel(self.tr('EPSG code'))
        self.epsg_point_label = QLabel(self.tr('unknown'))
        # POINT (5 line)
        hab_filenametitle_point_label = QLabel(self.tr('.sub file name'))
        self.point_hname = QLineEdit('')  # hdf5 name
        self.load_point_substrate_pushbutton = QPushButton(self.tr('Create .sub file'), self)
        change_button_color(self.load_point_substrate_pushbutton, "#47B5E6")
        self.load_point_substrate_pushbutton.clicked.connect(lambda: self.load_sub_gui('point'))
        self.load_point_substrate_pushbutton.setEnabled(False)

        # CONSTANT (0 line)
        filetitle_constant_label = QLabel(self.tr('File'))
        self.file_constant_label = QLabel(self.namefile[0], self)
        self.file_constant_label.setToolTip(self.pathfile[0])
        self.sub_choosefile_constant = QPushButton(self.tr('Choose file (.txt)'), self)
        self.sub_choosefile_constant.clicked.connect(lambda: self.show_dialog_substrate("constant"))
        self.sub_choosefile_constant.clicked.connect(lambda: self.file_constant_label.setToolTip(self.pathfile[0]))
        self.sub_choosefile_constant.clicked.connect(lambda: self.file_constant_label.setText(self.namefile[0]))
        # CONSTANT (1 line)
        classification_codetitle_constant_label = QLabel(self.tr('Classification code'))
        self.sub_classification_code_constant_label = QLabel(self.tr('unknown'))
        # CONSTANT (2 line)
        classification_methodtitle_constant_label = QLabel(self.tr('Classification method'))
        self.sub_classification_method_constant_label = QLabel(self.tr('unknown'))
        # CONSTANT (3 line)
        valuestitle_constant_label = QLabel(self.tr('Constant values'))
        self.valuesdata_constant_label = QLabel(self.tr('unknown'))
        # CONSTANT (4 line)
        hab_filenametitle_constant_label = QLabel(self.tr('.sub file name'))
        self.constant_hname = QLineEdit('')  # hdf5 name
        self.load_constant_substrate_pushbutton = QPushButton(self.tr('Create .sub file'), self)
        change_button_color(self.load_constant_substrate_pushbutton, "#47B5E6")
        self.load_constant_substrate_pushbutton.clicked.connect(lambda: self.load_sub_gui('constant'))
        self.load_constant_substrate_pushbutton.setEnabled(False)

        # COMMON
        last_sub_file_title_label = QLabel(self.tr('Last file created'))
        self.last_sub_file_name_label = QLabel(self.tr('no file'))
        self.name_last_hdf5("SUBSTRATE")

        # MERGE
        l9 = QLabel(self.tr("Hydraulic data (.hyd)"))
        l10 = QLabel(self.tr("Substrate data (.sub)"))
        self.input_hyd_combobox = QComboBox()
        self.input_hyd_combobox.currentIndexChanged.connect(self.create_hdf5_merge_name)
        self.input_sub_combobox = QComboBox()
        self.input_sub_combobox.currentIndexChanged.connect(self.create_hdf5_merge_name)
        self.load_hab_pushbutton = QPushButton(self.tr("Create .hab file"), self)
        change_button_color(self.load_hab_pushbutton, "#47B5E6")
        self.load_hab_pushbutton.clicked.connect(self.compute_merge)
        self.load_hab_pushbutton.setEnabled(False)
        # get possible substrate from the project file
        self.update_sub_hdf5_name()
        # file name output
        hdf5_merge_label = QLabel(self.tr('.hab file name'))
        self.hdf5_merge_lineedit = QLineEdit('')  # default hdf5 merge name
        # get the last file created
        last_hab_created_title_label = QLabel(self.tr('Last file created'))
        self.last_merge_file_name_label = QLabel(self.tr('no file'))
        self.name_last_hdf5("HABITAT")  # find the name of the last merge file and add it to self.lm2

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # POLYGON GROUP
        self.layout_polygon = QGridLayout()  # 4 rows et 3 columns
        self.layout_polygon.addWidget(filetitle_polygon_label, 0, 0)  # 0 line
        self.layout_polygon.addWidget(self.file_polygon_label, 0, 1)  # 0 line
        self.layout_polygon.addWidget(self.sub_choosefile_polygon, 0, 2)  # 0 line
        self.layout_polygon.addWidget(classification_codetitle_polygon_label, 1, 0)  # 1 line
        self.layout_polygon.addWidget(self.sub_classification_code_polygon_label, 1, 1)  # 1 line
        self.layout_polygon.addWidget(classification_methodtitle_polygon_label, 2, 0)  # 2 line
        self.layout_polygon.addWidget(self.sub_classification_method_polygon_label, 2, 1)  # 2 line
        self.layout_polygon.addWidget(default_valuestitle_polygon_label, 3, 0)  # 3 line
        self.layout_polygon.addWidget(self.sub_default_values_polygon_label, 3, 1)  # 3 line
        self.layout_polygon.addWidget(epsgtitle_polygon_label, 4, 0)  # 4 line
        self.layout_polygon.addWidget(self.epsg_polygon_label, 4, 1)  # 4 line
        self.layout_polygon.addWidget(hab_filenametitle_polygon_label, 5, 0)  # 5 line
        self.layout_polygon.addWidget(self.polygon_hname, 5, 1)  # 5 line
        self.layout_polygon.addWidget(self.load_polygon_substrate_pushbutton, 5, 2)  # 5 line
        [self.layout_polygon.setRowMinimumHeight(i, 30) for i in range(self.layout_polygon.rowCount())]
        self.polygon_group = QGroupBox(self.tr('From polygons'))
        self.polygon_group.setLayout(self.layout_polygon)

        # POINT GROUP
        self.layout_point = QGridLayout()  # 4 rows et 3 columns
        self.layout_point.addWidget(filetitle_point_label, 0, 0)  # 0 line
        self.layout_point.addWidget(self.file_point_label, 0, 1)  # 0 line
        self.layout_point.addWidget(self.sub_choosefile_point, 0, 2)  # 0 line
        self.layout_point.addWidget(classification_codetitle_point_label, 1, 0)  # 1 line
        self.layout_point.addWidget(self.sub_classification_code_point_label, 1, 1)  # 1 line
        self.layout_point.addWidget(classification_methodtitle_point_label, 2, 0)  # 2 line
        self.layout_point.addWidget(self.sub_classification_method_point_label, 2, 1)  # 2 line
        self.layout_point.addWidget(default_valuestitle_point_label, 3, 0)  # 3 line
        self.layout_point.addWidget(self.sub_default_values_point_label, 3, 1)  # 3 line
        self.layout_point.addWidget(epsgtitle_point_label, 4, 0)  # 4 line
        self.layout_point.addWidget(self.epsg_point_label, 4, 1)  # 4 line
        self.layout_point.addWidget(hab_filenametitle_point_label, 5, 0)  # 5 line
        self.layout_point.addWidget(self.point_hname, 5, 1)  # 5 line
        self.layout_point.addWidget(self.load_point_substrate_pushbutton, 5, 2)  # 5 line
        [self.layout_point.setRowMinimumHeight(i, 30) for i in range(self.layout_point.rowCount())]
        self.point_group = QGroupBox(self.tr('From points'))
        self.point_group.setLayout(self.layout_point)

        # CONSTANT GROUP
        self.layout_constant = QGridLayout()  # 4 rows et 3 columns
        self.layout_constant.addWidget(filetitle_constant_label, 0, 0)  # 0 line
        self.layout_constant.addWidget(self.file_constant_label, 0, 1)  # 0 line
        self.layout_constant.addWidget(self.sub_choosefile_constant, 0, 2)  # 0 line
        self.layout_constant.addWidget(classification_codetitle_constant_label, 1, 0)  # 1 line
        self.layout_constant.addWidget(self.sub_classification_code_constant_label, 1, 1)  # 1 line
        self.layout_constant.addWidget(classification_methodtitle_constant_label, 2, 0)  # 2 line
        self.layout_constant.addWidget(self.sub_classification_method_constant_label, 2, 1)  # 2 line
        self.layout_constant.addWidget(valuestitle_constant_label, 3, 0)  # 3 line
        self.layout_constant.addWidget(self.valuesdata_constant_label, 3, 1)  # 3 line
        self.layout_constant.addWidget(QLabel(""), 4, 0)  # 4 line
        self.layout_constant.addWidget(QLabel(""), 4, 1)  # 4 line
        self.layout_constant.addWidget(hab_filenametitle_constant_label, 5, 0)  # 5 line
        self.layout_constant.addWidget(self.constant_hname, 5, 1)  # 5 line
        self.layout_constant.addWidget(self.load_constant_substrate_pushbutton, 5, 2)  # 5 line
        [self.layout_constant.setRowMinimumHeight(i, 30) for i in range(self.layout_constant.rowCount())]
        self.constant_group = QGroupBox(self.tr('From constant values'))
        self.constant_group.setLayout(self.layout_constant)

        # SUBSTRATE GROUP
        self.layout_sub = QGridLayout()  # 4 rows et 4 columns
        self.layout_sub.addWidget(l1, 0, 0, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.polyg_radiobutton, 0, 1, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.point_radiobutton, 0, 2, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.constant_radiobutton, 0, 3, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addItem(sub_spacer, 1, 0, 1, 4)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.polygon_group, 2, 0, 1, 4)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.point_group, 3, 0, 1, 4)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.constant_group, 4, 0, 1, 4)  # index row, index column, nb row, nb column
        self.layout_sub.addItem(sub_spacer, 5, 0, 1, 4)  # index row, index column, nb row, nb column
        laste_hdf5_sub_layout = QHBoxLayout()
        laste_hdf5_sub_layout.addWidget(
            last_sub_file_title_label)  # ,     6, 0, 1, 1)  # index row, index column, nb row, nb column
        laste_hdf5_sub_layout.addItem(
            QSpacerItem(45, 1))  # ,     6, 0, 1, 1)  # index row, index column, nb row, nb column
        laste_hdf5_sub_layout.addWidget(
            self.last_sub_file_name_label)  # ,    6, 1, 1, 1, Qt.AlignLeft)  # index row, index column, nb row, nb column
        self.layout_sub.addItem(laste_hdf5_sub_layout, 6, 0, 1, 4, Qt.AlignLeft)
        self.point_group.hide()
        self.constant_group.hide()
        susbtrate_group = QGroupBoxCollapsible()
        susbtrate_group.setTitle(self.tr('Substrate data'))
        susbtrate_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        susbtrate_group.setLayout(self.layout_sub)

        # MERGE GROUP
        self.layout_merge = QGridLayout()  # 5 rows et 3 columns
        self.layout_merge.addWidget(l9, 0, 0)
        self.layout_merge.addWidget(self.input_hyd_combobox, 0, 1)
        self.layout_merge.addWidget(l10, 1, 0)
        self.layout_merge.addWidget(self.input_sub_combobox, 1, 1)
        self.layout_merge.addWidget(hdf5_merge_label, 2, 0)
        self.layout_merge.addWidget(self.hdf5_merge_lineedit, 2, 1)
        self.layout_merge.addWidget(self.load_hab_pushbutton, 2, 2)
        self.layout_merge.addWidget(last_hab_created_title_label, 3, 0)
        self.layout_merge.addWidget(self.last_merge_file_name_label, 3, 1)
        [self.layout_merge.setRowMinimumHeight(i, 30) for i in range(self.layout_merge.rowCount())]
        merge_group = QGroupBoxCollapsible()
        merge_group.setTitle(self.tr('Merging of hydraulic and substrate data'))
        merge_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        merge_group.setLayout(self.layout_merge)
        merge_group.setChecked(True)

        # empty frame scrolable
        content_widget = QFrame()

        # layout general
        self.layout_sub_tab = QVBoxLayout(content_widget)
        self.layout_sub_tab.addWidget(susbtrate_group)
        self.layout_sub_tab.addWidget(merge_group)
        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout_sub_tab.addItem(verticalSpacer)
        self.scrollarea = QScrollArea()
        self.scrollarea.setWidgetResizable(True)
        self.scrollarea.setFrameShape(QFrame.NoFrame)
        self.scrollarea.setWidget(content_widget)
        self.layoutscroll = QVBoxLayout()
        self.layoutscroll.setContentsMargins(0, 0, 0, 0)
        self.layoutscroll.addWidget(self.scrollarea)
        self.setLayout(self.layoutscroll)

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

            if type == "SUBSTRATE":  # substrate
                self.last_sub_file_name_label.setText(name)
            elif type == "HABITAT":  # merge
                self.last_merge_file_name_label.setText(name)

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

    def save_xml(self, i=0, append_name=False):
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
        filename_path_file = self.pathfile[i]
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

    def find_path_hdf5(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_hdf5 is in the project folder in the folder 'hdf5'.
        """
        path_hdf5 = ''

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            path_hdf5 = load_specific_properties(self.path_prj, preference_names=["path_hdf5"])[0]
        else:
            self.send_log.emit("Error: " + QCoreApplication.translate("SubHydroW", "The project is not saved. Save the project in the General tab "
                               "before calling hdf5 files. \n"))

        return path_hdf5

    def find_path_input(self):
        """
        A function to find the path where to save the input file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_input indicates the folder 'input' in the project folder.
        """
        path_input = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            path_input = load_specific_properties(self.path_prj, preference_names=["path_input"])[0]
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(QCoreApplication.translate("SubHydroW", "Save the path to the copied inputs"))
            self.msg2.setText(
                QCoreApplication.translate("SubHydroW", "The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_input

    def btnstate(self, rb_sel, rb_del, rb_del2):
        """
        This function is used to select and deslect radiobutton
        :param rb_sel: the radio button which was just selected
        :param rb_del: the radio button which should be deselected
        :param rb_del2: the radio button which should be deselected
        """
        rb_sel.setChecked(True)
        rb_del.setChecked(False)
        rb_del2.setChecked(False)

    def add_polygon_widgets(self):
        """
         This functions shows the widgets
        """
        self.polygon_group.show()
        self.point_group.hide()
        self.constant_group.hide()

    def add_point_widgets(self):
        """
         This functions shows the widgets
        """
        self.polygon_group.hide()
        self.point_group.show()
        self.constant_group.hide()

    def add_const_widgets(self):
        """
        This function shows the widgets realted to the loading of constatns subtrate
        """
        self.polygon_group.hide()
        self.point_group.hide()
        self.constant_group.show()

    def show_dialog_substrate(self, substrate_mapping_method):
        """
        Selecting shapefile by user and verify integrity of .txt and .prj files.
        Add informations to GUI
        """
        # prepare the filter to show only useful files
        if substrate_mapping_method == "polygon":
            extensions = [".shp", "gpkg"]
        if substrate_mapping_method == "point":
            extensions = [".txt", ".shp", "gpkg"]
        if substrate_mapping_method == "constant":
            extensions = [".txt"]
        filter = "File ("
        for ext in extensions:
            filter += '*' + ext + ' '
        filter += ')' + ";; All File (*.*)"

        self.project_preferences = load_project_properties(self.path_prj)

        # get last path
        if self.read_attribute_xml(self.model_type) != self.path_prj and self.read_attribute_xml(
                self.model_type) != "":
            substrate_path = self.read_attribute_xml(self.model_type)  # path spe
        elif self.read_attribute_xml("path_last_file_loaded") != self.path_prj and self.read_attribute_xml(
                "path_last_file_loaded") != "":
            substrate_path = self.read_attribute_xml("path_last_file_loaded")  # path last
        else:
            substrate_path = self.path_prj  # path proj

        # find the filename based on user choice
        filename_path = QFileDialog.getOpenFileName(self,
                                                    self.tr("Select file"),
                                                    substrate_path,
                                                    filter)[0]

        # exeption: you should be able to clik on "cancel"
        if filename_path:
            # all case
            dirname = os.path.dirname(filename_path)
            filename = os.path.basename(filename_path)
            blob, ext = os.path.splitext(filename)
            self.pathfile[0] = dirname
            self.save_xml(0)  # path in xml
            if any(e in ext for e in extensions):  # extension known
                pass
            else:
                if ext == '':  # no extension
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("File type"))
                    self.msg2.setText(self.tr("The selected file has no extension. If you know this file, change its "
                                              "extension manually to " + " or ".join(extensions)))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
                else:  # no extension known (if not any(e in ext for e in extension_i))
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("File type"))
                    self.msg2.setText(self.tr("Needed type for the file to be loaded: " + ' ,'.join(extensions)))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()

            # get_sub_description_from_source
            sub_description, warning_list = src.substrate_mod.get_sub_description_from_source(filename_path,
                                                                                              substrate_mapping_method,
                                                                                              self.path_prj)
            # save to attribute
            self.sub_description = sub_description
            # error
            if not sub_description:
                for warn in warning_list:
                    self.send_log.emit(warn)
            # ok
            if sub_description:
                # but warnings
                if warning_list:
                    for warn in warning_list:
                        self.send_log.emit(warn)

                # all cases
                self.namefile[0] = filename

                # POLYGON
                if substrate_mapping_method == "polygon":
                    # save to attributes
                    self.pathfile_polygon = dirname
                    self.namefile_polygon = filename
                    self.name_hdf5_polygon = blob + ".sub"

                    # save to GUI
                    self.file_polygon_label.setText(filename)
                    self.file_polygon_label.setToolTip(self.pathfile_polygon)
                    self.sub_classification_code_polygon_label.setText(sub_description["sub_classification_code"])
                    self.sub_classification_method_polygon_label.setText(sub_description["sub_classification_method"])
                    self.sub_default_values_polygon_label.setText(sub_description["sub_default_values"])
                    self.epsg_polygon_label.setText(sub_description["epsg_code"])
                    self.polygon_hname.setText(self.name_hdf5_polygon)
                    self.load_polygon_substrate_pushbutton.setEnabled(True)

                # POINT
                elif substrate_mapping_method == "point":
                    # save to attributes
                    self.pathfile_point = dirname
                    self.namefile_point = filename
                    self.name_hdf5_point = blob + ".sub"

                    # save to GUI
                    self.file_point_label.setText(filename)
                    self.file_point_label.setToolTip(self.pathfile_point)
                    self.sub_classification_code_point_label.setText(sub_description["sub_classification_code"])
                    self.sub_classification_method_point_label.setText(sub_description["sub_classification_method"])
                    self.sub_default_values_point_label.setText(sub_description["sub_default_values"])
                    self.epsg_point_label.setText(sub_description["epsg_code"])
                    self.point_hname.setText(self.name_hdf5_point)
                    self.load_point_substrate_pushbutton.setEnabled(True)

                # CONSTANT
                elif substrate_mapping_method == "constant":
                    # save to attributes
                    self.pathfile_constant = dirname
                    self.namefile_constant = filename
                    self.name_hdf5_constant = blob + ".sub"

                    # save to GUI
                    self.file_constant_label.setText(filename)
                    self.file_constant_label.setToolTip(self.pathfile_constant)
                    self.sub_classification_code_constant_label.setText(sub_description["sub_classification_code"])
                    self.sub_classification_method_constant_label.setText(sub_description["sub_classification_method"])
                    self.valuesdata_constant_label.setText(sub_description["sub_default_values"])
                    self.constant_hname.setText(self.name_hdf5_constant)
                    self.load_constant_substrate_pushbutton.setEnabled(True)

    def load_sub_gui(self, sub_mapping_method):
        """
        This function is used to load the substrate data. The substrate data can be in three forms: a) in the form of a shp
        file form ArGIS (or another GIS-program). b) in the form of a text file (x,y, substrate data line by line),
        c) it can be a constant substrate. Generally this function has some similarities to the functions used to load
        the hydrological data and it re-uses some of the methods developed for them.

        It is possible to have a constant substrate if const_sub= True. In this
        case, an hdf5 is created with only the default value marked. This form of hdf5 file is then managed by the merge
        function.

        :param const_sub: If True, a constant substrate is being loaded. Usually it is set to False.

        """
        self.model_type = 'SUBSTRATE'
        self.data_type = "SUBSTRATE"
        # if hdf5_filename_output empty: msg
        if sub_mapping_method == 'polygon':
            # input_filename
            if self.file_polygon_label.text() == "unknown file":
                self.send_log.emit('Error: ' + self.tr('No input file has been selected.'))
                return
            # output_name_hdf5
            if not self.polygon_hname.text():
                self.send_log.emit('Error: ' + self.tr('.sub output filename is empty. Please specify it.'))
                return
        if sub_mapping_method == 'point':
            # input_filename
            if self.file_point_label.text() == "unknown file":
                self.send_log.emit('Error: ' + self.tr('No input file has been selected.'))
                return
            # output_name_hdf5
            if not self.point_hname.text():
                self.send_log.emit('Error: ' + self.tr('.sub output filename is empty. Please specify it.'))
                return
        if sub_mapping_method == 'constant':
            # input_filename
            if self.file_constant_label.text() == "unknown file":
                self.send_log.emit('Error: ' + self.tr('No input file has been selected.'))
                return
            # output_name_hdf5
            if not self.constant_hname.text():
                self.send_log.emit('Error: ' + self.tr('.sub output filename is empty. Please specify it.'))
                return

        if self.sub_description:
            # info
            self.timer.start(100)

            # show progressbar
            self.nativeParentWidget().progress_bar.setRange(0, 100)
            self.nativeParentWidget().progress_bar.setValue(0)
            self.nativeParentWidget().progress_bar.setVisible(True)

            # polygon case
            if sub_mapping_method == 'polygon':
                # block button substrate
                self.load_polygon_substrate_pushbutton.setEnabled(False)  # substrate
                self.name_hdf5 = self.polygon_hname.text()

            # point case
            if sub_mapping_method == 'point':
                # block button substrate
                self.load_point_substrate_pushbutton.setEnabled(False)  # substrate
                self.name_hdf5 = self.point_hname.text()

            # constante case
            if sub_mapping_method == 'constant':
                # block button substrate
                self.load_constant_substrate_pushbutton.setEnabled(False)  # substrate
                self.name_hdf5 = self.constant_hname.text()

            # save path and name substrate
            self.save_xml(0)  # txt filename in xml

            # change hdf5_name
            self.sub_description["name_hdf5"] = self.name_hdf5

            # load substrate shp (and triangulation)
            self.stop = Event()
            self.q = Queue()
            self.progress_value = Value("d", 0)
            self.p = Process(target=substrate_mod.load_sub,
                             args=(self.sub_description,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences,
                                   self.stop))
            self.p.name = "Substrate data loading from shapefile"
            self.p.start()

            # copy_shapefiles
            path_input = self.find_path_input()

            # log info
            self.send_log.emit(self.tr('# Loading: Substrate data ...'))
            # self.send_err_log()
            self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
            self.send_log.emit("py    path1=r'" + path_input + "'")
            self.send_log.emit("py    type='" + self.sub_description["sub_classification_code"] + "'")
            self.send_log.emit("py    [coord_p, ikle_sub, sub_dm, sub_pg, ok_dom] = substrate.load_sub_sig"
                               "(file1, path1, type)\n")
            self.send_log.emit("restart LOAD_SUB_SHP")
            self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
            self.send_log.emit("restart    sub_classification_code: " + self.sub_description["sub_classification_code"])

    def update_sub_hdf5_name(self):
        """
        This function update the QComBox on substrate data which is on the substrate tab. The similiar function
        for hydrology is in Main_Windows_1.py as it is more practical to have it there to collect all the signals.
        """
        names = hdf5_mod.get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
        self.input_hyd_combobox.clear()
        self.input_hyd_combobox.addItems(names)
        self.input_hyd_combobox.setCurrentIndex(0)

        names = hdf5_mod.get_filename_by_type_physic("substrate", os.path.join(self.path_prj, "hdf5"))
        self.input_sub_combobox.clear()
        self.input_sub_combobox.addItems(names)
        self.input_sub_combobox.setCurrentIndex(0)

    def create_hdf5_merge_name(self):
        hdf5_name_hyd = self.input_hyd_combobox.currentText()
        hdf5_name_sub = self.input_sub_combobox.currentText()
        if hdf5_name_hyd != ' ' and hdf5_name_hyd != '' and hdf5_name_sub != ' ' and hdf5_name_sub != '':
            name_hdf5merge = hdf5_name_hyd[:-4] + "_" + hdf5_name_sub[:-4] + ".hab"
            if hasattr(self, "hdf5_merge_lineedit"):
                self.hdf5_merge_lineedit.setText(name_hdf5merge)
                self.load_hab_pushbutton.setEnabled(True)

    def log_txt(self, code_type):
        """
        This function gives the log for the substrate in text form. this is in a function because it is used twice in
        the function load_sub_gui()
        """
        # log info
        self.send_log.emit(self.tr('# Load: Substrate data - text file'))
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    type='" + code_type + "'")
        self.send_log.emit("py    [coord_pt, ikle_subt, sub_infot, x, y, sub] = substrate.load_sub_txt(file1, path1,"
                           " code_type)\n")
        self.send_log.emit("restart LOAD_SUB_TXT")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))
        self.send_log.emit("restart    code_type: " + code_type)

    def get_att_name(self):
        """
        A function to get the attribute name of the shapefile which contains the substrate data. it is given by the user
        in the GUI.
        """

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            for i in range(0, len(self.attributexml)):
                child = root.find(".//" + self.attributexml[1])
                # if there is data in the project file about the model
                if child is not None:
                    self.name_att = child.text

    def compute_merge(self):
        """
        This function calls the function merge grid in substrate_mod.py. The goal is to have the substrate and hydrological
        data on the same grid. Hence, the hydrological grid will need to be cut to the form of the substrate grid.

        This function can be slow so it call on a second thread.
        """
        self.model_type = 'HABITAT'
        self.data_type = "HABITAT"

        # if not .hyd
        if not self.input_hyd_combobox.currentText():
            self.send_log.emit(self.tr('Error: no input .hyd file selected. Please specify it.'))
            return

        # if not .sub
        if not self.input_sub_combobox.currentText():
            self.send_log.emit(self.tr('Error: no input .sub file selected. Please specify it.'))
            return

        # if not .hab name
        if not self.hdf5_merge_lineedit.text():
            self.send_log.emit(self.tr('Error: .hab filename output is empty. Please specify it.'))
            return

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)  # show progressbar

        self.send_log.emit(self.tr('# Merging: substrate and hydraulic grid...'))

        # get useful data
        path_hdf5 = self.find_path_hdf5()
        if self.input_hyd_combobox.currentText():
            hdf5_name_hyd = self.input_hyd_combobox.currentText()  # path_hdf5 + "/" +
        else:
            self.send_log.emit('Error: ' + self.tr('No hydrological file available \n'))
            return

        if self.input_sub_combobox.currentText():
            hdf5_name_sub = self.input_sub_combobox.currentText()  # path_hdf5 + "/" +
        else:
            self.send_log.emit('Error: ' + self.tr('No substrate file available \n'))
            return

        # hdf5 output file
        self.name_hdf5 = self.hdf5_merge_lineedit.text()
        # if file exist add number
        nb = 0
        while os.path.isfile(path_hdf5 + "/" + self.name_hdf5 + ".hab"):
            nb = nb + 1
            self.name_hdf5 = self.hdf5_merge_lineedit.text() + "_" + str(nb)

        # get the figure options and the type of output to be created
        project_preferences = load_project_properties(self.path_prj)

        # block button merge
        self.load_hab_pushbutton.setEnabled(False)  # merge

        # for error management and figures
        self.timer.start(100)

        # run the function
        self.stop = Event()
        self.q = Queue()
        self.progress_value = Value("d", 0)
        self.p = Process(target=src.merge.merge_grid_and_save,
                         args=(hdf5_name_hyd,
                               hdf5_name_sub,
                               self.name_hdf5,
                               self.path_prj,
                               self.progress_value,
                               self.q,
                               False,
                               project_preferences,
                               self.stop))
        self.p.name = "Hydraulic and substrate data merging"
        self.p.start()

        # log
        self.send_log.emit("py    file_hyd=r'" + self.input_hyd_combobox.currentText() + "'")
        self.send_log.emit("py    name_sub=r'" + self.input_sub_combobox.currentText() + "'")
        self.send_log.emit("py    path_sub=r'" + path_hdf5 + "'")
        self.send_log.emit("py    mesh_grid2.merge_grid_and_save(file_hyd,name_sub, path_sub, defval, name_prj, "
                           "path_prj, 'SUBSTRATE', [], True) \n")
        self.send_log.emit("restart MERGE_GRID_SUB")
        self.send_log.emit("restart    file_hyd: r" + self.input_hyd_combobox.currentText())
        self.send_log.emit("restart    file_sub: r" + os.path.join(path_hdf5,
                                                                   self.input_sub_combobox.currentText()))

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
            self.nativeParentWidget().kill_process_action.setVisible(True)

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
                    self.nativeParentWidget().kill_process_action.setVisible(False)
                    # MERGE
                    if self.model_type == 'HABITAT' or self.model_type == 'LAMMI':
                        # unblock button merge
                        self.load_hab_pushbutton.setEnabled(True)  # merge
                    # SUBSTRATE
                    elif self.model_type == 'SUBSTRATE':
                        # unblock button substrate
                        self.load_polygon_substrate_pushbutton.setEnabled(True)  # substrate
                        self.load_point_substrate_pushbutton.setEnabled(True)  # substrate
                        self.load_constant_substrate_pushbutton.setEnabled(True)  # substrate

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
                        self.load_hab_pushbutton.setEnabled(True)  # merge

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
                        self.load_polygon_substrate_pushbutton.setEnabled(True)
                        self.load_point_substrate_pushbutton.setEnabled(True)
                        self.load_constant_substrate_pushbutton.setEnabled(True)

                    # send round(c) to attribute .hyd
                    hdf5_hyd = hdf5_mod.Hdf5Management(self.path_prj,
                                                       self.name_hdf5,
                                                       new=False)
                    hdf5_hyd.set_hdf5_attributes([os.path.splitext(self.name_hdf5)[1][1:] + "_time_creation [s]"],
                                                 [round(self.running_time)])

                    # general
                    self.nativeParentWidget().progress_bar.setValue(100)
                    self.nativeParentWidget().kill_process_action.setVisible(False)
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
                self.nativeParentWidget().kill_process_action.setVisible(False)
                self.running_time = 0
                # MERGE
                if self.model_type == 'HABITAT' or self.model_type == 'LAMMI':
                    # unblock button merge
                    self.load_hab_pushbutton.setEnabled(True)  # merge
                # SUBSTRATE
                elif self.model_type == 'SUBSTRATE':
                    # unblock button substrate
                    self.load_polygon_substrate_pushbutton.setEnabled(True)  # substrate
                    self.load_point_substrate_pushbutton.setEnabled(True)  # substrate
                    self.load_constant_substrate_pushbutton.setEnabled(True)  # substrate

                # CRASH
                if self.p.exitcode == 1:
                    self.send_log.emit(QCoreApplication.translate("SubHydroW",
                                                                  "Error : Process crashed !! Restart HABBY. Retry. If same, contact the HABBY team."))

