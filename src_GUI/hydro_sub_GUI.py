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
import numpy as np
import sys
import shutil
from io import StringIO
from PyQt5.QtCore import pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QWidget, QPushButton, \
    QLabel, QGridLayout, \
    QLineEdit, QFileDialog, QSpacerItem, QListWidget, \
    QComboBox, QMessageBox, QGroupBox, \
    QRadioButton, QAbstractItemView, QScrollArea, QFrame, QVBoxLayout, QSizePolicy, \
    QHBoxLayout
from PyQt5.QtGui import QIcon
import h5py
from multiprocessing import Process, Queue, Value
from osgeo import ogr
from osgeo import osr

from src import hec_ras1D_mod
from src import hec_ras2D_mod
from src import telemac_mod
from src import substrate_mod
from src import rubar1d2d_mod
from src import river2d_mod
from src import sw2d_mod
from src import iber2d_mod
from src import mascaret_mod
from src import hdf5_mod
from src_GUI import preferences_GUI
from src import mesh_management_mod
from src import lammi_mod
from src import paraview_mod
from src import hydro_input_file_mod
from src import ascii_mod
from src.user_preferences_mod import user_preferences

np.set_printoptions(threshold=np.inf)
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class Hydro2W(QScrollArea):
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
    (name of the list: self.name_model).

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

        super(Hydro2W, self).__init__()
        self.tab_name = "hydraulic"
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_model = ["", "HEC-RAS 1D", "HEC-RAS 2D", "LAMMI", "MASCARET",
                           "RIVER2D", "RUBAR BE", "RUBAR 20",
                           "SW2D", "IBER2D", "TELEMAC", "TXT", "HABBY HDF5"]  # "MAGE"
        self.name_model.sort()
        self.mod_act = 0
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

        # group hydraulic model
        self.mod = QComboBox()
        self.mod.setMaxVisibleItems(20)
        self.mod.addItems(self.name_model)  # available model
        self.mod.currentIndexChanged.connect(self.selectionchange)
        self.button1 = QPushButton(self.tr('?'), self)
        self.button1.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.button1.clicked.connect(self.give_info_model)
        self.free = QWidget()  # add the widgets representing the available models to a stack of widgets
        self.hecras1D = HEC_RAS1D(self.path_prj, self.name_prj)
        self.hecras2D = HEC_RAS2D(self.path_prj, self.name_prj)
        self.lammi = LAMMI(self.path_prj, self.name_prj)
        self.mascar = Mascaret(self.path_prj, self.name_prj)
        self.riverhere2d = River2D(self.path_prj, self.name_prj)
        self.rubar1d = Rubar1D(self.path_prj, self.name_prj)
        self.rubar2d = Rubar2D(self.path_prj, self.name_prj)
        self.sw2d = SW2D(self.path_prj, self.name_prj)
        self.iber2d = IBER2D(self.path_prj, self.name_prj)
        self.telemac = TELEMAC(self.path_prj, self.name_prj)
        self.ascii = ASCII(self.path_prj, self.name_prj)
        self.habbyhdf5 = HabbyHdf5(self.path_prj, self.name_prj)
        self.layout_modele = QVBoxLayout()
        self.layout_modele.addWidget(self.free)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.hecras1D)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.hecras2D)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.lammi)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.mascar)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.riverhere2d)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.rubar1d)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.rubar2d)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.sw2d)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.iber2d)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.telemac)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.ascii)  # index row, index column, nb row, nb column
        self.layout_modele.addWidget(self.habbyhdf5)  # index row, index column, nb row, nb column
        self.qframe_modele = QFrame()  # 4 rows et 4 columns
        self.qframe_modele.setLayout(self.layout_modele)
        self.hecras1D.hide()
        self.hecras2D.hide()
        self.lammi.hide()
        self.mascar.hide()
        self.riverhere2d.hide()
        self.rubar1d.hide()
        self.rubar2d.hide()
        self.sw2d.hide()
        self.iber2d.hide()
        self.telemac.hide()
        self.ascii.hide()
        self.habbyhdf5.hide()

        # self.stack = QStackedWidget()
        # self.stack.addWidget(self.free)  # order matters in the next lines!
        # self.stack.addWidget(self.hecras1D)
        # self.stack.addWidget(self.hecras2D)
        # self.stack.addWidget(self.lammi)
        # self.stack.addWidget(self.mascar)
        # self.stack.addWidget(self.riverhere2d)
        # self.stack.addWidget(self.rubar1d)
        # self.stack.addWidget(self.rubar2d)
        # self.stack.addWidget(self.sw2d)
        # self.stack.addWidget(self.iber2d)
        # self.stack.addWidget(self.telemac)
        # self.stack.addWidget(self.habbyhdf5)
        # self.stack.setCurrentIndex(self.mod_act)
        # self.stack.setFixedHeight(0)
        # self.stack.setFixedWidth(0)

        # group hydraulic hdf5
        self.slfbut = QPushButton(self.tr('export .slf'))  # export slf
        self.slfbut.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.slfbut.clicked.connect(self.export_slf_gui)
        self.drop_hyd = QComboBox()  # list with available hdf5

        # empty frame scrolable
        content_widget = QFrame()
        self.layout = QVBoxLayout(content_widget)

        # layout hydraulic model
        hydrau_group = QGroupBox(self.tr('Hydraulic data'))
        hydrau_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        hydrau_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.mod)
        button_layout.addWidget(self.button1)
        hydrau_layout = QVBoxLayout()
        hydrau_layout.addLayout(button_layout)
        hydrau_layout.addWidget(self.qframe_modele)
        hydrau_group.setLayout(hydrau_layout)
        self.layout.addWidget(hydrau_group)

        # layout hdf5 model
        hdf5_group = QGroupBox(self.tr('.hyd files created'))
        hdf5_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        hdf5_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        hdf5_layout = QHBoxLayout()
        hdf5_layout.addWidget(self.drop_hyd)
        hdf5_layout.addWidget(self.slfbut)
        hdf5_group.setLayout(hdf5_layout)
        #self.layout.addWidget(hdf5_group)

        # spacer to align top
        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addItem(verticalSpacer)

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

    def selectionchange(self, i):
        """
        Change the shown widget which represents each hydrological model
        (all widget are in a stack)

        :param i: the number of the model
                    (0=no model, 1=hecras1d, 2= hecras2D,...)
        """
        # self.name_model  # list modele
        self.mod_act = i

        if self.mod.currentText() == "":
            self.free.show()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "HEC-RAS 1D":
            self.free.hide()
            self.hecras1D.show()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "HEC-RAS 2D":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.show()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "LAMMI":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.show()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "MASCARET":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.show()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "RIVER2D":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.show()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "RUBAR BE":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.show()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "RUBAR 20":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.show()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "SW2D":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.show()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "IBER2D":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.show()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "TELEMAC":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.show()
            self.ascii.hide()
            self.habbyhdf5.hide()

        if self.mod.currentText() == "TXT":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.show()
            self.habbyhdf5.hide()
            
        if self.mod.currentText() == "HABBY HDF5":
            self.free.hide()
            self.hecras1D.hide()
            self.hecras2D.hide()
            self.lammi.hide()
            self.mascar.hide()
            self.riverhere2d.hide()
            self.rubar1d.hide()
            self.rubar2d.hide()
            self.sw2d.hide()
            self.iber2d.hide()
            self.telemac.hide()
            self.ascii.hide()
            self.habbyhdf5.show()

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
        mod_name = self.name_model[self.mod_act]
        self.msgi.setWindowTitle(text_title)
        info_filename = os.path.join('./model_hydro', mod_name + '.txt')
        if mod_name == "TELEMAC":
            website = "<a href=\"http://www.opentelemac.org\">TELEMAC</a>"
        elif mod_name == "HEC-RAS 1D":
            website = "<a href=\"http://www.hec.usace.army.mil/software/hec-ras\">HEC-RAS 1D</a>"
        elif mod_name == "HEC-RAS 2D":
            website = "<a href=\"http://www.hec.usace.army.mil/software/hec-ras\">HEC-RAS 2D</a>"
        elif mod_name == "SW2D":
            website = "<a href=\"https://sw2d.wordpress.com\">SW2D</a>"
        elif mod_name == "MASCARET":
            website = "<a href=\"http://www.openmascaret.org\">MASCARET</a>"
        elif mod_name == "RIVER2D":
            website = "<a href=\"http://www.river2d.ca\">RIVER2D</a>"
        elif mod_name == "RUBAR 20":
            website = "<a href=\"http://www.irstea.fr/rubar20\">RUBAR20</a>"
        elif mod_name == "RUBAR BE":
            website = "<a href=\"http://www.irstea.fr/rubar3\">RUBARBE</a>"
        elif mod_name == "IBER2D":
            website = "<a href=\"http://www.iberaula.es\">IBER2D</a>"
        else:
            website = ""
        self.msgi.setStandardButtons(QMessageBox.Ok)
        if os.path.isfile(info_filename):
            with open(info_filename, 'rt') as f:
                text = f.read()
            text2 = text.split('MORE INFO')
            self.msgi.setText(website + text2[0])
            self.msgi.setDetailedText(text2[1])
        else:
            self.msgi.setText(self.tr('Choose a type of hydraulic model !         '))
            self.msgi.setDetailedText('No detailed info yet.')
        # detailed text erase the red x
        self.msgi.setEscapeButton(QMessageBox.Ok)
        name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
        self.msgi.setWindowIcon(QIcon(name_icon))
        self.msgi.show()

    def export_slf_gui(self):
        """
        This is the function which is used by the GUI to export slf data.
        NOT FINISHED!!!!!
        """
        self.send_log.emit('export slf is not finished yet')
        name_hdf5 = self.drop_hyd.currentText()
        path_hdf5 = self.rubar1d.find_path_hdf5()
        #path_slf = self.rubar1d.find_path_output('Path_Visualisation')
        path_slf = os.path.join(self.path_prj, "output")

        if not name_hdf5:
            self.send_log.emit(self.tr('Error: No hydraulic file found. \n'))
            return

        paraview_mod.save_slf(name_hdf5, path_hdf5, path_slf, False)


class SubHydroW(QWidget):
    """
    SubHydroW is class which is the parent of the classes which can be used
    to open the hydrological models. This class is a bit special.
    It is not called directly by HABBY but by the classes which load the
    hydrological data and which inherits from this class.
    The advantage of this architecture is that all the children classes can
    use the methods written in SubHydroW(). Indeed, all the children classes
    load hydrological data and therefore they are similar and
    can use similar functions.

    In other word, there are MainWindows() which provides the windows around
    the widget and Hydro2W which provide the
    widget for the hydrological Tab and one class by hydrological model
    to really load the model. The latter classes have various methods in
    common, so they inherit from SubHydroW, this class.
    """

    send_log = pyqtSignal(str, name='send_log')
    """
    A Pyqtsignal to write the log.
    """
    drop_hydro = pyqtSignal()
    """
    A PyQtsignal signal for the substrate tab so it can account
    for the new hydrological info.
    """
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figure.
    """

    def __init__(self, path_prj, name_prj):

        # do not change the string 'unknown file'
        self.namefile = ['unknown file', 'unknown file']

        # for children, careful with list index out of range
        self.interpo = ["Interpolation by block", "Linear interpolation",
                        "Nearest Neighbors"]  # order matters here
        self.interpo_choice = 0
        # gives which type of interpolation is chosen
        # (it is the index of self.interpo )
        self.pathfile = [path_prj, path_prj]
        self.attributexml = [' ', ' ']
        self.model_type = ' '
        self.nb_dim = 2
        self.save_fig = False
        self.coord_pro = []
        self.vh_pro = []
        self.nb_pro_reach = []
        self.on_profile = []
        self.xhzv_data = []
        self.inter_vel_all_t = []
        self.inter_h_all_t = []
        self.ikle_all_t = []
        self.point_all_t = []
        self.point_c_all_t = []
        self.np_point_vel = -99
        # -99 -> velocity calculated in the same point than the profile height
        self.manning1 = 0.025
        self.manning_arr = []
        self.pro_add = 2  # additional profil during the grid creation
        self.extension = [[".txt"]]
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.timer = QTimer()
        self.mystdout = None
        self.name_hdf5 = ''
        self.manning_textname = ''
        self.polygon_hname = QLineEdit(' ')
        self.p = Process(target=None)  # second process
        self.q = Queue()
        self.project_preferences = []
        self.running_time = 0
        super().__init__()

        # update error or show figure every second (1000ms)
        # self.timer.setInterval(1000)  # ms
        self.timer.timeout.connect(self.show_prog)

        # get the last file created
        self.last_hydraulic_file_label = QLabel(self.tr('Last file created'))
        self.last_hydraulic_file_name_label = QLabel(self.tr('no file'))
        self.last_path_input_data = None

    def was_model_loaded_before(self, i=0, many_file=False):
        """
        A function to test if the model loaded before. If yes,
        it updates the attibutes anf the widgets of the
        hydrological model on consideration.

        :param i: an int used in cases where there is more than one file to
         load (geometry and output for example)
        :param many_file: A bollean. If true this function will load more than
         one file, separated by ','. If False,
                it will only loads the file of one model
                (see the comment below).

        **Technical comment**

        This method opens the xml project file and look in the attribute of the xml file to see if data from the
        hydrological model have been loaded before. If yes, the name of the data is written on the GUI of HABBY in the
        Widget related to the hydrological model. Now, there are often more than one data loaded. This method allows
        choosing what should be written. There are two different case to be separated: a) We have loaded two different
        models (like two rivers modeled by HEC-RAS) b) One model type needs two data file (like HEC-RAS would need a
        geometry and output data). For the case a), the default is to write only the last model loaded. If this
        default behaviour is changed, the behaviour of gethdf5_name_GUI should also be changed. If we wish to
        write all data, the switch “many_file” should be True. This switch is also useful for the river2D model, because
        this model create one output file per time step. For the case b), the argument “i”(which is an int) allows us to
        choose which data type should be shown. “i” is in the order of the self.attributexml variable. The definition of
        this order is given in the definition of the class of each hydrological model.

        """
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//" + self.attributexml[i])
            # if there is data in the project file about the model
            if child is not None:
                geo_name_path = child.text
                if os.path.isfile(geo_name_path) and not many_file:
                    self.namefile[i] = os.path.basename(geo_name_path)
                    self.pathfile[i] = os.path.dirname(geo_name_path)
                # load many file at once
                elif many_file:
                    list_all_name = geo_name_path.split(',\n')
                    for j in range(0, len(list_all_name)):
                        if os.path.isfile(list_all_name[j]):
                            self.namefile.append(os.path.basename(list_all_name[j]))
                            self.pathfile.append(os.path.dirname(list_all_name[j]))
                        else:
                            self.msg2.setIcon(QMessageBox.Warning)
                            self.msg2.setWindowTitle(self.tr("Previously Loaded File"))
                            self.msg2.setText(self.tr("One of the file given in the project file does not exist."))
                            self.msg2.setStandardButtons(QMessageBox.Ok)
                            self.msg2.show()
                elif os.path.basename(geo_name_path) != 'unknown file':
                    pass
                    # self.msg2.setIcon(QMessageBox.Warning)
                    # self.msg2.setWindowTitle(self.tr("Previously Loaded File"))
                    # self.msg2.setText(
                    #     self.tr(
                    #         "The file given in the project file does not exist. Hydrological model:" + self.model_type))
                    # self.msg2.setStandardButtons(QMessageBox.Ok)
                    # self.msg2.show()

    def gethdf5_name_gui(self):
        """
        This function get the name of the hdf5 file for the hydrological and write down in the QLineEdit on the GUI.
        It is possible to have more than one hdf5 file for a model type. For example, we could have created two hdf5
        based on hec-ras output. The default here is to write the last model loaded. It is the same default behaviour
        than for the function was_model_loaded_before(). To keep the coherence between the filename and hdf5 name,
        a change in this behaviour should be reflected in both function.

        This function calls the function get_hdf5_name in the hdf5_mod.py file

        """

        sys.stdout = self.mystdout = StringIO()  # out to GUI
        pathname_hdf5 = hdf5_mod.get_hdf5_name(self.model_type, self.name_prj, self.path_prj)
        sys.stdout = sys.__stdout__  # reset to console
        self.send_err_log()

        if pathname_hdf5 is not None:
            self.name_hdf5 = os.path.basename(pathname_hdf5)
        else:
            return

        if self.model_type == 'SUBSTRATE' and 'CONST' in self.name_hdf5:
            if len(self.name_hdf5) > 50:  # careful this number should be changed if the form of the hdf5 name change
                self.name_hdf5 = self.name_hdf5[:-25]
            self.hname2.setText(self.name_hdf5)
        else:
            if len(self.name_hdf5) > 50:  # careful this number should be changed if the form of the hdf5 name change
                self.name_hdf5 = self.name_hdf5[:-25]
            self.polygon_hname.setText(self.name_hdf5)

    def show_dialog(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """

        # prepare the filter to show only useful files
        if len(self.extension[i]) <= 4:
            filter2 = "File ("
            for e in self.extension[i]:
                filter2 += '*' + e + ' '
            filter2 = filter2[:-1]
            filter2 += ')' + ";; All File (*.*)"
        else:
            filter2 = ''

        # get last path substrate_path xml
        model_path = self.read_attribute_xml(self.attributexml[0])
        if model_path == 'no_data':
            model_path = self.path_prj

        # find the filename based on user choice
        filename_path = QFileDialog.getOpenFileNames(self,
                                                    self.tr("Select file"),
                                                    model_path,
                                                    filter2)[0][0]

        # if len(self.pathfile) == 0:  # case where no file was open before
        #     filename_path = QFileDialog.getOpenFileName(self, self.tr("Select file"), self.path_prj, filter2)[0]
        # elif i >= len(self.pathfile):
        #     filename_path = QFileDialog.getOpenFileName(self, self.tr("Select file"), self.pathfile[0], filter2)[0]
        # else:
        #     # why [0] : getOpenFilename return a tuple [0,1,2], we need only the filename
        #     filename_path = QFileDialog.getOpenFileName(self, self.tr("Select file"), self.pathfile[i], filter2)[0]
        # exeption: you should be able to clik on "cancel"
        if filename_path:
            filename = os.path.basename(filename_path)
            # check extension
            extension_i = self.extension[i]
            blob, ext = os.path.splitext(filename)
            if any(e in ext for e in extension_i):  # extension known
                pass
            else:
                if ext == '':  # no extension
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("File type"))
                    self.msg2.setText(self.tr(
                        "The selected file has no extension. If you know this file, change its extension manually to " + " or ".join(
                            extension_i)))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
                else:  # no extension known (if not any(e in ext for e in extension_i))
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("File type"))
                    self.msg2.setText(self.tr("Needed type for the file to be loaded: " + ' ,'.join(extension_i)))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()

            # keep the name in an attribute until we save it
            if i >= len(self.pathfile) or len(self.pathfile) == 0:
                self.pathfile.append(os.path.dirname(filename_path))
                self.namefile.append(filename)
            else:
                self.pathfile[i] = os.path.dirname(filename_path)
                self.namefile[i] = filename

            # add the default name of the hdf5 file to the QLineEdit
            filename2 = filename.split('.')[0]  # os.path.splitext is not a good idea for name.001.xml (hec-ras)
            ext = filename.split('.')[-1]
            if ext == filename2:
                ext = ''
            if self.model_type == 'SUBSTRATE':
                if len(filename) > 6:
                    self.name_hdf5 = 'Sub_' + filename2 + '_' + ext
                else:
                    self.name_hdf5 = 'Sub_' + filename2 + '_' + ext
            else:
                if len(filename) > 9:
                    self.name_hdf5 = filename2 + ".hyd"
                else:
                    self.name_hdf5 = filename2 + ".hyd"

            self.hname.setText(self.name_hdf5)
            # self.nativeParentWidget().central_widget.path_last_file_loaded_c = os.path.dirname(filename_path)
            # print("hydrau : ", self.nativeParentWidget().central_widget.path_last_file_loaded_c)

    def dis_enable_nb_profile(self):
        """
        This function enable and disable the QLineEdit where the user gives the number of additional profile needed to
        create the gird and the related QLabel. If the user choose the interpolation by bloc, the QLineEdit will be
        disabled. If it chooses linear or nearest neighbour interpolation, it will be enabled. Careful, this function
        only works with 1D and 1.5D model.
        """
        if self.nb_dim >= 2:
            return

        if self.inter.currentIndex() == 0:
            # disable
            self.nb_extrapro_text.setDisabled(True)
            self.l5.setDisabled(True)
        else:
            # enable
            self.nb_extrapro_text.setDisabled(False)
            self.l5.setDisabled(False)

    def save_xml(self, i=0, append_name=False):
        """
        A function to save the loaded data in the xml file.

        This function adds the name and the path of the newly chosen hydrological data to the xml project file. First,
        it open the xml project file (and send an error if the project is not saved, or if it cannot find the project
        file). Then, it opens the xml file and add the path and name of the file to this xml file. If the model data was
        already loaded, it adds the new name without erasing the old name IF the switch append_name is True. Otherwise,
        it erase the old name and replace it by a new name. The variable “i” has the same role than in show_dialog.

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
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()

            # save last file path
            if os.path.isdir(filename_path_file):
                last_child = root.find(".//Path_last_file_loaded")
                last_child.text = filename_path_file

            child1 = root.find(".//" + self.model_type)
            if child1 is None:
                child1 = ET.SubElement(root, self.model_type)

            child = root.find(".//" + self.attributexml[i])
            if child is None:
                child = ET.SubElement(child1, self.attributexml[i])
                child.text = filename_path_file
            else:
                if append_name:
                    child.text += ",\n"
                    child.text += filename_path_file
                else:
                    child.text = filename_path_file
            doc.write(filename_path_pro, method="xml")

    def find_path_im(self):
        """
        A function to find the path where to save the figues. Careful a simialar one is in estimhab_GUI.py. By default,
        path_im is in the project folder in the folder 'figure'.

        This is practical to have in a function form as it should be called repeatably (in case the project have been
        changed since the last start of HABBY).
        """

        path_im = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Figure")
            if child is None:
                path_im = os.path.join(self.path_prj, r'/figures')
            else:
                path_im = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save the path to the figures"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        if not os.path.isdir(path_im):
            self.send_log.emit('Warning: The path to the figure was not found.')
            path_im = self.path_prj

        return path_im

    def find_path_hdf5(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_hdf5 is in the project folder in the folder 'hdf5'.
        """

        path_hdf5 = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Hdf5")
            if child is None:
                path_hdf5 = os.path.join(self.path_prj, r'/hdf5')
            else:
                path_hdf5 = os.path.join(self.path_prj, child.text)
        else:
            self.send_log.emit("Error: The project is not saved. Save the project in the General tab "
                               "before calling hdf5 files. \n")

        return path_hdf5

    def find_path_input(self):
        """
        A function to find the path where to save the input file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_input indicates the folder 'input' in the project folder.
        """

        path_input = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
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

    def find_path_output(self, att):
        """
        A function to find the path where to save the shapefile, paraview files and other future format. Here, we gave
        the xml attribute as argument so this functin can be used to find all path needed. However, it is less practical
        to use as the function above as one should remember the xml tribute to call this function. However, it can be
        practical to use to add new folder. Careful a similar function is in estimhab_GUI.py.

        :param att: the xml attribute (from the xml project file) linked to the path needed, without the .//

        """

        path_out = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
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

    def read_attribute_xml(self, att_here):
        """
        A function to read the text of an attribute in the xml project file.

        :param att_here: the attribute name (string).
        """
        data = 'no_data'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.findall('.//' + att_here)
            if child is not None:
                for i in range(0, len(child)):
                    if i == 0:
                        data = child[i].text
                    else:
                        data += ',' + child[i].text
        else:
            pass

        return data

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
                self.send_log.emit(self.tr('Warning: too many information for the GUI'))
            if 'Error' in str_found[i] and check_ok:
                error = True
        if check_ok:
            return error

    def load_manning_text(self):
        """
        This function loads the manning data in case where manning number is not simply a constant. In this case, the manning
        parameter is given in a .txt file.
        The manning parameter used by 1D model such as mascaret or Rubar BE to distribute velocity along the profiles.
        The format of the txt file is "p, dist, n" where  p is the profile number (start at zero), dist is the distance
        along the profile in meter and n is the manning value (in SI unit). One point per line so something like:

        0, 150, 0.035

        0, 200, 0.025

        1, 120, 0.035, etc.

        White space is neglected and a line starting with the character # is also neglected.

        A very similar function to this ones exists in func_for_cmd. It is used to so the same thing but called
        from the cmd. Changes should be copied in both functions if necessary.
        """
        # find the filename based on user choice
        if len(self.pathfile) == 0:
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_prj)[0]
        else:
            # if a model was loaded go directly to the folder were this model was loaded
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathfile[0])[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            return
        else:
            filename = os.path.basename(filename_path)
        # load data
        if not os.path.isfile(filename_path):
            self.send_log.emit('Error: The selected file for manning is not found.')
            return
        self.manning_textname = filename_path
        try:
            with open(filename_path, 'rt') as f:
                data = f.read()
        except IOError:
            self.send_log.emit('Error: The selected file for manning can not be open.')
            return
        # create manning array (to pass to dist_vitess)
        data = data.split('\n')
        manning = np.zeros((len(data), 3))
        com = 0
        for l in range(0, len(data)):
            data[l] = data[l].strip()
            if len(data[l]) > 0:
                if data[l][0] != '#':
                    data_here = data[l].split(',')
                    if len(data_here) == 3:
                        try:
                            manning[l - com, 0] = np.int(data_here[0])
                            manning[l - com, 1] = np.float(data_here[1])
                            manning[l - com, 2] = np.float(data_here[2])
                        except ValueError:
                            self.send_log.emit('Error: The manning data could not be converted to float or int.'
                                               ' Format: p,dist,n line by line.')
                            return
                    else:
                        self.send_log.emit('Error: The manning data was not in the right format.'
                                           ' Format: p,dist,n line by line.')
                        return

                else:
                    manning = np.delete(manning, -1, 0)
                    com += 1

        # save the adress of the text data in the xml file
        self.pathfile[3] = os.path.dirname(filename_path)
        self.namefile[3] = filename
        self.save_xml(3)

        self.manning_arr = manning

    def show_prog(self):
        """
        This function is call regularly by the methods which have a second thread (so moslty the function
        to load the hydrological data). To call this function regularly, the variable self.timer of QTimer type is used.
        The variable self.timer is connected to this function in the initiation of SubHydroW() and so in the initiation
        of all class which inherits from SubHydroW().

        This function just wait while the thread is alive. When it has terminated, it creates the figure and the error
        messages.
        """

        # say in the status bar that the processus is alive
        if self.p.is_alive():
            self.running_time += 0.100  # this is useful for GUI to update the running, should be logical with self.Timer()
            # get the language
            self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
            self.nativeParentWidget().kill_process.setVisible(True)
            # send the message FRENCH
            if self.project_preferences['language'] == str(1):
                # MERGE
                if self.model_type == 'HABITAT':
                    self.send_log.emit(
                        "Processus 'Fusion de Grille' fonctionne depuis " + str(round(self.running_time)) + " sec")
                    self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
                # SUBSTRATE
                elif self.model_type == 'SUBSTRATE':
                    self.send_log.emit(
                        "Processus 'substrat' fonctionne depuis " + str(round(self.running_time)) + " sec")
                    self.nativeParentWidget().progress_bar.setValue(50)
                # HYDRAULIC
                else:
                    # it is necssary to start this string with Process to see it in the Statusbar
                    self.send_log.emit(
                        "Processus 'Hydraulique' fonctionne depuis " + str(round(self.running_time)) + " sec")
                    self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
            # send the message ENGLISH
            else:
                # MERGE
                if self.model_type == 'HABITAT':
                    self.send_log.emit(
                        "Process 'Merge Grid' is alive and run since " + str(round(self.running_time)) + " sec")
                    self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
                # SUBSTRATE
                elif self.model_type == 'SUBSTRATE':
                    self.send_log.emit(
                        "Process 'substrate' is alive and run since " + str(round(self.running_time)) + " sec")
                    self.nativeParentWidget().progress_bar.setValue(50)
                # HYDRAULIC
                else:
                    # it is necssary to start this string with Process to see it in the Statusbar
                    self.send_log.emit(
                        "Process 'Hydraulic' is alive and run since " + str(round(self.running_time)) + " sec")
                    self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))

        # when the loading is finished
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

            # info
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
                    self.load_b.setDisabled(False)  # hydraulic
            if not error:
                # MERGE
                if self.model_type == 'HABITAT' or self.model_type == 'LAMMI':
                    self.send_log.emit(
                        self.tr("Merging of substrate and hydraulic grid finished (computation time = ") + str(
                            round(self.running_time)) + " s).")
                    self.drop_merge.emit()
                    # update last name
                    self.name_last_hdf5("hdf5_mergedata")
                    # unblock button merge
                    self.load_b2.setDisabled(False)  # merge
                # SUBSTRATE
                elif self.model_type == 'SUBSTRATE':
                    self.send_log.emit(self.tr("Loading of substrate data finished (computation time = ") + str(
                        round(self.running_time)) + " s).")
                    self.drop_merge.emit()
                    # add the name of the hdf5 to the drop down menu so we can use it to merge with hydrological data
                    self.update_sub_hdf5_name()
                    # update last name
                    self.name_last_hdf5("hdf5_substrate")
                    # unblock button substrate
                    self.load_polygon_substrate.setDisabled(False)  # substrate
                    self.load_point_substrate.setDisabled(False)  # substrate
                    self.load_constant_substrate.setDisabled(False)  # substrate
                # HYDRAULIC
                else:
                    self.send_log.emit(self.tr("Loading of hydraulic data finished (computation time = ") + str(
                        round(self.running_time)) + " s).")
                    # send a signal to the substrate tab so it can account for the new info
                    self.drop_hydro.emit()
                    # update last name
                    self.name_last_hdf5(self.model_type)
                    if self.model_type == "ASCII":  # can produce .hab
                        self.drop_merge.emit()
                    # unblock button hydraulic
                    self.load_b.setDisabled(False)  # hydraulic

                # general
                self.nativeParentWidget().progress_bar.setValue(100)
                self.nativeParentWidget().kill_process.setVisible(False)
                if not const_sub:
                    self.send_log.emit(self.tr("Figures can be displayed/exported from 'Data explorer' tab.\n"))
                if const_sub:
                    self.update_sub_hdf5_name()
                self.send_log.emit("clear status bar")
                # refresh plot gui list file
                self.nativeParentWidget().central_widget.data_explorer_tab.refresh_type()
                self.running_time = 0

        # finish
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
                self.load_b.setDisabled(False)  # hydraulic
                if self.model_type == "ASCII":  # can produce .hab
                    self.drop_merge.emit()

    def recreate_image(self):
        """
        This function is used to recreate the images related to the grid and the hydrology. We do not call create_image
        directly as we might add other command here.
        """

        self.create_image(False, True)

    def create_image(self, save_fig=True, show_info=False):
        """
        plot hydraulic data

        :param save_fig: a boolean to save the figure or not
        :param show_info: If True, basic information about the data will be displayed into the log window.
        """
        # getting the name
        name_hdf5 = os.path.basename(hdf5_mod.get_hdf5_name(self.model_type, self.name_prj, self.path_prj))

        # getting the data
        units_raw = hdf5_mod.load_unit_name(name_hdf5, self.path_prj + "/hdf5/")

        # plot hydraulic data (h, v, mesh)
        types_hdf5 = "hydraulic"
        names_hdf5 = [name_hdf5]
        variables = ["height", "velocity", "mesh"]
        if len(units_raw) > 1:  # several timestep
            units = [units_raw[0], units_raw[-1]]  # the first and the last timesteo
            units_index = [0, len(units_raw) - 1]
        else:  # one timestep
            units = units_raw
            units_index = [0]
        types_plot = "display"
        self.nativeParentWidget().central_widget.data_explorer_tab.data_explorer_frame.plot(types_hdf5, names_hdf5,
                                                                                            variables, units,
                                                                                            units_index, types_plot)

    def create_image_merge(self, save_fig=True, show_info=False):
        """
        plot merge data

        :param save_fig: a boolean to save the figure or not
        :param show_info: If True, basic information about the data will be displayed into the log window.
        """
        # getting the subtrate name
        name_hdf5 = self.lm2.text()

        # getting the subtrate data
        units_raw = hdf5_mod.load_unit_name(name_hdf5, self.path_prj + "/hdf5/")

        # plot hydraulic data (h, v, mesh)
        types_hdf5 = "hydraulic"
        names_hdf5 = [name_hdf5]
        variables = ["height", "velocity", "mesh"]
        if len(units_raw) > 1:  # several timestep
            units = [units_raw[0], units_raw[-1]]  # the first and the last timesteo
            units_index = [0, len(units_raw)]
        else:  # one timestep
            units = units_raw
            units_index = [0]
        types_plot = "display"
        self.nativeParentWidget().central_widget.data_explorer_tab.data_explorer_frame.plot(types_hdf5, names_hdf5,
                                                                                            variables, units,
                                                                                            units_index, types_plot)

    def name_last_hdf5(self, type):
        """
        This function opens the xml project file to find the name of the last hdf5 merge file and to add it
        to the GUI on the QLabel self.lm2. It also add a QToolTip with the name of substrate and hydraulic files used
        to create this merge file. If there is no file found, this function do nothing.
        """
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.send_log.emit('Error: The project is not saved. '
                               'Save the project in the General tab before saving hydraulic data. \n')
        else:
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            # geo data
            if type == "hdf5_substrate": # substrate hdf5
                child1 = root.findall(f".//SUBSTRATE/{type}")
            elif type == "hdf5_mergedata":  # hab hdf5
                child1 = root.findall(f".//Habitat/")
            else:
                child1 = root.findall(f".//{type}/hdf5_hydrodata")  # hydraulic hdf5

            if child1 is not None:
                if len(child1) > 0:
                    if type not in ("hdf5_substrate", "hdf5_mergedata"):  # hydraulic
                        name = child1[-1].text
                        self.last_hydraulic_file_name_label.setText(name)
                    if type == "hdf5_substrate":  # substrate
                        name = root.findall('.//hdf5_substrate')[0].text
                        self.last_sub_file_name_label.setText(name)
                    if type == "hdf5_mergedata":  # merge
                        name = root.findall('.//hdf5_habitat')[0].text
                        self.last_merge_file_name_label.setText(name)

                    # # QToolTip
                    # [sub_ini, hydro_ini] = load_hdf5.get_initial_files(path_hdf5, mergename)
                    # hydro_ini = os.path.basename(hydro_ini)
                    # textini = 'Hydraulic: ' + hydro_ini + '\nSubstrate :' + sub_ini
                    # self.lm2.setToolTip(textini)


class HEC_RAS1D(SubHydroW):
    """
   The class Hec_ras 1D is there to manage the link between the graphical interface and the functions in
   src/hec_ras06.py which loads the hec-ras data in 1D. The class HEC_RAS1D inherits from SubHydroW() so it have all
   the methods and the variables from the class ubHydroW(). The class hec-ras 1D is added to the self.stack of Hydro2W().
   So the class Hec-Ras 1D is called when the user is on the hydrological tab and click on hec-ras1D as hydrological
   model.
    """

    def __init__(self, path_prj, name_prj):
        super(HEC_RAS1D, self).__init__(path_prj, name_prj)
        self.inter = QComboBox()
        self.init_iu()

    def init_iu(self):
        """
        This function is called by __init__() durring the initialization.

        **Technical comment**

        The self.attributexml variable is the name of the attribute in the xml file. To load a hec-ras file, one needs
        to give to HABBY one file containing the geometry data and one file containing the simulation result. The name
        and path to  these two file are saved in the xml project file under the attribute given in
        the self.attributexml variable.

        The variable self.extension is a list of list of the accepted file type. The first list is for the file
        with geometry data. The second list is the extension of the files containing the simulation results.

        Using the function self.was_model_loaded_before, HABBY write the name of the hec-ras files which were loaded
        in HABBY in the same project before.

        Hec-Ras is a 1.5D model and so HABBY create a 2D grid based on the 1.5D input. The user can choose the interpolation
        type and the number of extra profile. If the interpolation type is “interpolation by block”, the number of extra
        profile will always be one. See manage_grid.py for more information on how to create a grid.

        We add a QLineEdit with the proposed name for the created hdf5 file. The user can modified this name if wished so.
        """

        # update attibute for hec-ras 1d
        self.attributexml = ['geodata', 'resdata']
        self.data_type = "HYDRAULIC"
        self.model_type = 'HECRAS1D'
        self.extension = [['.g01', '.g02', '.g03', '.g04', '.g05 ', '.g06', '.g07', '.g08',
                           '.g09', '.g10', '.g11', '.G01', '.G02'], ['.xml', '.rep', '.sdf']]
        self.nb_dim = 1.5

        # if there is the project file with hecras geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)

        # label with the file name
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.geo_t2.setToolTip(self.pathfile[0])
        self.out_t2 = QLabel(self.namefile[1], self)
        self.out_t2.setToolTip(self.pathfile[1])

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton(self.tr('Choose file (.g0x)'), self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)

        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton(self.tr('Choose file \n (.xml, .sdf, or .rep file)'), self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[1]))

        # # grid creation options
        l6 = QLabel(self.tr('<b>Grid creation </b>'))
        l3 = QLabel(self.tr('Velocity distribution'))
        l31 = QLabel(self.tr('Model 1.5D: No dist. needed'))
        l4 = QLabel(self.tr('Interpolation of the data'))
        self.l5 = QLabel(self.tr('Number of additional profiles'))
        self.inter.addItems(self.interpo)
        self.nb_extrapro_text = QLineEdit('1')
        self.dis_enable_nb_profile()
        self.inter.currentIndexChanged.connect(self.dis_enable_nb_profile)

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit('')
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_hec_ras_gui)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)
        self.spacer1 = QSpacerItem(1, 30)
        self.spacer2 = QSpacerItem(1, 80)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2, 0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addItem(self.spacer1, 2, 1)
        self.layout_hec.addWidget(l6, 3, 0)
        self.layout_hec.addWidget(l3, 4, 1)
        self.layout_hec.addWidget(l31, 4, 2, 1, 2)
        self.layout_hec.addWidget(l4, 5, 1)
        self.layout_hec.addWidget(self.inter, 5, 2, 1, 2)
        self.layout_hec.addWidget(self.l5, 6, 1)
        self.layout_hec.addWidget(self.nb_extrapro_text, 6, 2, 1, 2)
        self.layout_hec.addItem(self.spacer1, 7, 1)
        self.layout_hec.addWidget(lh, 8, 0)
        self.layout_hec.addWidget(self.hname, 8, 1)
        self.layout_hec.addWidget(self.load_b, 8, 3)
        self.layout_hec.addWidget(self.butfig, 9, 3)
        # self.layout_hec.addItem(self.spacer2, 10, 1)
        self.setLayout(self.layout_hec)

    def load_hec_ras_gui(self):
        """
        A function to execute the loading and saving of the HEC-ras file using Hec_ras.py

        **Technical comments**

        This function is called when the user press on the button self.load_b. It is the function which really
        calls the load function for hec_ras. First, it updates the xml project file. It adds the name of the new file
        to xml project file under the attribute indicated by self.attributexml. It also gets the path_im by reading the
        path_im in the xml project file. If we want to create the 1D figure, the option show_all_fig
        should be selected in the figure option. It also manages the log as explained in the section about the log.
        It loads the hec-ras data as explained in the section on hec_ras06.py and creates the grid as explained
        in the manage_grid.py based on the interpolation type wished by the user (linear, nearest neighbor or by block).
        The variable self.name_hdf5() is taken from the GUI.
        """
        # test the availability of files
        fileNOK = True
        f0 = os.path.join(self.pathfile[0], self.namefile[0])
        f1 = os.path.join(self.pathfile[1], self.namefile[1])
        if os.path.isfile(f0) & os.path.isfile(f1):
            fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("HEC-RAS 1D"))
            self.msg2.setText(self.tr("Unable to load HEC-RAS data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        self.load_b.setDisabled(True)

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)

        # for error management and figures (when time finsiehed call the self.show_prog function)
        self.timer.start(100)

        # get the image and load option
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.load_b.setDisabled(True)
        self.name_hdf5 = self.hname.text()
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
        show_all_fig = True
        if path_im != 'no_path' and show_all_fig:
            self.save_fig = True
        self.interpo_choice = self.inter.currentIndex()

        # get the number of addition profile
        if self.interpo_choice > 0:
            try:
                self.pro_add = int(self.nb_extrapro_text.text())
            except ValueError:
                self.send_log.emit('Error: Number of profile not recognized.\n')
                return

        # load hec_ras data and create the grid in a second thread
        self.q = Queue()
        self.p = Process(target=hec_ras1D_mod.open_hec_hec_ras_and_create_grid, args=(self.name_hdf5, path_hdf5,
                                                                                      self.name_prj, self.path_prj,
                                                                                      self.model_type, self.namefile,
                                                                                      self.pathfile,
                                                                                      self.interpo_choice,
                                                                                      path_im, show_all_fig,
                                                                                      self.pro_add, self.q, False,
                                                                                      self.project_preferences))
        self.p.name = "HEC-RAS 1D data loading"
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info

        self.send_log.emit(self.tr('# Loading: Hec-Ras 1D data...'))
        self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    file2=r'" + self.namefile[1] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    path2=r'" + path_input + "'")
        self.send_log.emit("py    files = [file1, file2]")
        self.send_log.emit("py    paths = [path1, path2]")
        self.send_log.emit("py    interp=" + str(self.interpo_choice))
        self.send_log.emit("py    pro_add=" + str(self.pro_add))
        self.send_log.emit(
            "py    Hec_ras06.open_hec_hec_ras_and_create_grid('re_run',path_prj"
            ", name_prj, path_prj, 'HECRAS1D', files, paths, interp, '.', False, pro_add, [], True)\n")
        self.send_log.emit("restart LOAD_HECRAS_1D")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(path_input, self.namefile[1]))
        self.send_log.emit("restart    interpolation: " + str(self.interpo_choice))
        self.send_log.emit("restart    number of added profile: " + str(self.pro_add))

    def propose_next_file(self):
        """
        This function proposes the second hec-ras file when the first is selected.  Indeed, to load hec-ras, we need
        one file with the geometry data and one file with the simulation results. If the user selects a file, this
        function looks if a file with the same name but with the extension of the other file type exists in the
        selected folder. Careful, when using hec-ras more than one extension type is possible.
        """

        if self.out_t2.text() == 'unknown file':
            blob = self.namefile[0]

            for ev in range(0, 3):
                if ev == 0:  # version 1 from hec-ras
                    for i in range(0, 10):  # max O09.xml is ok
                        new_name = blob[:-len(self.extension[0][0])] + '.O0' + str(i) + self.extension[1][0]
                        pathfilename = os.path.join(self.pathfile[0], new_name)
                        if os.path.isfile(pathfilename):
                            self.out_t2.setText(new_name)
                            # keep the name in an attribute until we save it
                            self.pathfile[1] = self.pathfile[0]
                            self.namefile[1] = new_name
                            break
                else:  # version 4 from hec-ras
                    if ev == 2:
                        new_name = blob[:-len(self.extension[0][0])] + '.RASexport' + self.extension[1][ev]
                    if ev == 1:
                        new_name = blob[:-len(self.extension[0][0])] + self.extension[1][ev]
                    pathfilename = os.path.join(self.pathfile[0], new_name)
                    if os.path.isfile(pathfilename):
                        self.out_t2.setText(new_name)
                        # keep the name in an attribute until we save it
                        self.pathfile[1] = self.pathfile[0]
                        self.namefile[1] = new_name
                        break


class Rubar2D(SubHydroW):
    """
    The class Rubar2D is there to manage the link between the graphical interface and the functions in src/rubar1d2d_mod.py
    which loads the RUBAR data in 2D. It inherits from SubHydroW() so it have all the methods and the variables from
    the class SubHydroW(). The form of the function is similar to hec-ras, but it does not have the part about the grid
    creation as we look here as the data created in 2D by RUBAR.
    """

    def __init__(self, path_prj, name_prj):

        super(Rubar2D, self).__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        used by ___init__() in the initialization.
        """

        # update attibute for rubar 2d
        self.attributexml = ['rubar_geodata', 'tpsdata']
        self.model_type = 'RUBAR2D'
        self.data_type = "HYDRAULIC"
        self.extension = [['.mai', '.dat'], ['.tps']]  # list of list in case there is more than one possible ext.
        self.nb_dim = 2

        # if there is the project file with rubar geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)

        # label with the file name
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)
        self.geo_t2.setToolTip(self.pathfile[0])
        self.out_t2.setToolTip(self.pathfile[1])

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton(self.tr('Choose file (.mai, .dat)'), self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton(self.tr('Choose file \n (.tps)'), self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[1]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_rubar)
        self.spacer = QSpacerItem(1, 200)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2, 0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(l2D1, 2, 0)
        self.layout_hec.addWidget(l2D2, 2, 1, 1, 2)
        self.layout_hec.addWidget(lh, 3, 0)
        self.layout_hec.addWidget(self.hname, 3, 1)
        self.layout_hec.addWidget(self.load_b, 3, 2)
        self.layout_hec.addWidget(self.butfig, 4, 2)
        # self.layout_hec.addItem(self.spacer, 5, 1)
        self.setLayout(self.layout_hec)

    def load_rubar(self):
        """
        A function to execture the loading and saving the the rubar file using rubar1d2d_mod.py. It is similar to the
        load_hec_ras_gui() function. Obviously, it calls rubar and not hec_ras this time. A small difference is that
        the rubar2D outputs are only given in one grid for all time steps and all reaches. Moreover, it is
        necessary to cut the grid for each time step as a function of the wetted area and maybe to separate the
        grid by reaches.  Another problem is that the data of Rubar2D is given on the cells of the grid and not the
        nodes. So we use linear interpolation to correct for this.

        A second thread is used to avoid "freezing" the GUI.

        """
        # for error management and figures
        self.timer.start(100)

        # test the availability of files
        fileNOK = True
        f0 = os.path.join(self.pathfile[0], self.namefile[0])
        f1 = os.path.join(self.pathfile[1], self.namefile[1])
        if os.path.isfile(f0) & os.path.isfile(f1):
            fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("RUBAR2D"))
            self.msg2.setText(self.tr("Unable to load RUBAR2D data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)

        # disable while loading
        self.load_b.setDisabled(True)

        # the path where to save the image
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # get minimum water height as we might neglect very low water height
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

        # load rubar 2d data, interpolate to node, create grid and save in hdf5 format
        self.q = Queue()
        self.progress_value = Value("i", 0)
        self.p = Process(target=rubar1d2d_mod.load_rubar2d_and_create_grid, args=(self.name_hdf5, self.namefile[0],
                                                                                  self.namefile[1], self.pathfile[0],
                                                                                  self.pathfile[1], path_im,
                                                                                  self.name_prj,
                                                                                  self.path_prj,
                                                                                  self.model_type, self.nb_dim,
                                                                                  self.progress_value,
                                                                                  path_hdf5,
                                                                                  self.q, False, self.project_preferences))
        self.p.name = "Rubar 2D data loading"
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: Rubar 2D data...'))
        # self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    file2=r'" + self.namefile[1] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    path2=r'" + path_input + "'")
        self.send_log.emit("py    rubar.load_rubar2d_and_create_grid('Hydro_rubar2d_log',file1, file2, path1, path2,"
                           " path_prj, name_prj, path_prj, 'RUBAR2D', 2, path_prj, [])\n")
        self.send_log.emit("restart LOAD_RUBAR_2D")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(path_input, self.namefile[1]))

    def propose_next_file(self):
        """
        This function proposes the second RUBAR file when the first is selected.  Indeed, to load rubar, we need
        one file with the geometry data and one file with the simulation results. If the user selects a file, this
        function looks if a file with the same name but with the extension of the other file type exists in the
        selected folder.
        """
        if len(self.extension[1]) == 1:
            if self.out_t2.text() == 'unknown file':
                blob = self.namefile[0]
                new_name = blob[:-len(self.extension[0][0])] + self.extension[1][0]
                pathfilename = os.path.join(self.pathfile[0], new_name)
                if os.path.isfile(pathfilename):
                    self.out_t2.setText(new_name)
                    # keep the name in an attribute until we save it
                    self.pathfile[1] = self.pathfile[0]
                    self.namefile[1] = new_name


class Mascaret(SubHydroW):
    """
    The class Mascaret is there to manage the link between the graphical interface and the functions in src/mascaret_mod.py
    which loads the Masacret data in 1D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is similar to the HEC-Ras1D class (see this class for more information). However, mascaret is 1D model, so the loading
    of mascaret has one additional step compared to the hec-ras load: The velocity must be distributed along the
    profile. For this, the load_masacret_gui call the self.distrbute _velocity function. In addition, it prepares
    the manning value which is necessary to distribute the velocity. The user has two choices to input the manning
    value. The easiest one is just to give a value constant for the whole river. In the second choice, the user loads
    a text file with a serie of lines with the following info: p, dist, n where p is the profile number
    (starting at zero), dist is the distance in meter along the profile and n in the manning value (see the method
    load_manning_text of the class SubHydroW for more information)
    """

    def __init__(self, path_prj, name_prj):
        super(Mascaret, self).__init__(path_prj, name_prj)
        self.inter = QComboBox()
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        # update attibute for mascaret
        self.attributexml = ['gen_data', 'geodata_mas', 'resdata_mas', 'manning_mas']
        self.namefile = ['unknown file', 'unknown file', 'unknown file', 'unknown file']
        self.pathfile = ['.', '.', '.', '.']
        self.model_type = 'MASCARET'
        self.data_type = "HYDRAULIC"
        self.extension = [['.xcas'], ['.geo'], ['.opt', '.rub']]
        self.nb_dim = 1

        # if there is the project file with mascaret info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)
        self.was_model_loaded_before(2)

        # label with the file name
        self.gen_t2 = QLabel(self.namefile[0], self)
        self.geo_t2 = QLabel(self.namefile[1], self)
        self.out_t2 = QLabel(self.namefile[2], self)

        # general, geometry and output data
        l0 = QLabel(self.tr('<b> General data </b>'))
        self.gen_b = QPushButton(self.tr('Choose file (.xcas)'), self)
        self.gen_b.clicked.connect(lambda: self.show_dialog(0))
        self.gen_b.clicked.connect(lambda: self.gen_t2.setText(self.namefile[0]))
        self.gen_b.clicked.connect(self.propose_next_file)
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton(self.tr('Choose file (.geo)'), self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(1))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[1]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton(self.tr('Choose file \n (.opt, .rub)'), self)
        self.out_b.clicked.connect(lambda: self.show_dialog(2))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[2]))

        # tooltip (give the folder of the chosen file)
        self.gen_t2.setToolTip(self.pathfile[0])
        self.geo_t2.setToolTip(self.pathfile[1])
        self.out_t2.setToolTip(self.pathfile[2])
        self.gen_b.clicked.connect(lambda: self.gen_t2.setToolTip(self.pathfile[0]))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[1]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[2]))

        # grid creation options
        l6 = QLabel(self.tr('<b>Grid creation </b>'))
        l3 = QLabel(self.tr('Velocity distribution'))
        l32 = QLabel(self.tr("Based on Manning's formula"))
        l7 = QLabel(self.tr("Nb. of velocity points by profile"))
        l8 = QLabel(self.tr("Manning coefficient"))
        l4 = QLabel(self.tr('Interpolation of the data'))
        self.l5 = QLabel(self.tr('Nb. of additional profiles'))
        self.inter.addItems(self.interpo)
        self.nb_extrapro_text = QLineEdit('1')
        self.nb_vel_text = QLineEdit('70')
        self.manning_text = QLineEdit('0.025')
        self.ltest = QLabel(self.tr('or'))
        self.manningb = QPushButton(self.tr('Load .txt'))
        self.manningb.clicked.connect(self.load_manning_text)
        self.dis_enable_nb_profile()
        self.inter.currentIndexChanged.connect(self.dis_enable_nb_profile)

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hab file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_mascaret_gui)
        spacer = QSpacerItem(1, 30)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(l0, 0, 0)
        self.layout.addWidget(self.gen_t2, 0, 1)
        self.layout.addWidget(self.gen_b, 0, 2)
        self.layout.addWidget(l1, 1, 0)
        self.layout.addWidget(self.geo_t2, 1, 1)
        self.layout.addWidget(self.geo_b, 1, 2)
        self.layout.addWidget(l2, 2, 0)
        self.layout.addWidget(self.out_t2, 2, 1)
        self.layout.addWidget(self.out_b, 2, 2)
        self.layout.addWidget(l6, 3, 0)
        self.layout.addWidget(l3, 3, 1)
        self.layout.addWidget(l32, 3, 2, 1, 2)
        self.layout.addWidget(l7, 4, 1)
        self.layout.addWidget(self.nb_vel_text, 4, 2)
        self.layout.addWidget(l8, 5, 1)
        self.layout.addWidget(self.manning_text, 5, 2)
        self.layout.addWidget(self.ltest, 5, 3)
        self.layout.addWidget(self.manningb, 5, 4)
        self.layout.addWidget(l4, 6, 1)
        self.layout.addWidget(self.inter, 6, 2, 1, 2)
        self.layout.addWidget(self.l5, 7, 1)
        self.layout.addWidget(self.nb_extrapro_text, 7, 2)
        self.layout.addWidget(lh, 8, 0)
        self.layout.addWidget(self.hname, 8, 1)
        self.layout.addWidget(self.load_b, 9, 2)
        self.layout.addWidget(self.butfig, 9, 4)
        # self.layout.addItem(spacer, 10, 1)
        self.setLayout(self.layout)

    def load_mascaret_gui(self):
        """
        The function is used to load the mascaret data, calling the function contained in the script mascaret_mod.py.
        It also create a 2D grid from the 1D data and distribute the velocity.
        All of theses tasks are done on a second thread to avoid freezing the GUI.
        """
        # test the availability of files
        fileNOK = True
        f0 = os.path.join(self.pathfile[0], self.namefile[0])
        f1 = os.path.join(self.pathfile[1], self.namefile[1])
        f2 = os.path.join(self.pathfile[2], self.namefile[2])
        if os.path.isfile(f0) & os.path.isfile(f1) & os.path.isfile(f2):
            fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("MASCARET"))
            self.msg2.setText(self.tr("Unable to load MASCARET data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # disable while loading
        self.load_b.setEnabled(False)

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        self.save_xml(2)

        # get the image and load option
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
        show_all_fig = True
        if path_im != 'no_path' and show_all_fig:
            self.save_fig = True
        self.interpo_choice = self.inter.currentIndex()
        path_im = self.find_path_im()

        # preparation for the velocity distibution
        manning_float = False
        # we have two cases possible: a manning array or a manning float. here we take the case manning as float
        if isinstance(self.manning_arr, float) or isinstance(self.manning_arr, np.float):
            self.manning_arr = []
        if len(self.manning_arr) == 0:
            try:
                manning_float = True
                self.manning_arr = float(self.manning_text.text())
            except ValueError:
                self.send_log.emit("Error: The manning value is not understood.")
                return
        try:
            self.np_point_vel = int(self.nb_vel_text.text())
        except ValueError:
            self.send_log.emit("Error: The number of velocity point is not understood.")
            return

        # load mascaret data, distribute the velocity and create the grid in a second thread
        self.q = Queue()
        # for error management and figures (when time finsiehed call the self.show_prog function)
        self.timer.start(100)
        self.p = Process(target=mascaret_mod.load_mascaret_and_create_grid,
                         args=(self.name_hdf5, path_hdf5, self.name_prj,
                               self.path_prj, self.model_type,
                               self.namefile,
                               self.pathfile, self.interpo_choice,
                               self.manning_arr, self.np_point_vel,
                               show_all_fig, self.pro_add, self.q,
                               path_im))
        self.p.name = "Mascaret data loading"
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: Mascaret data...'))
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    file2=r'" + self.namefile[1] + "'")
        self.send_log.emit("py    file3=r'" + self.namefile[2] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    path2=r'" + path_input + "'")
        self.send_log.emit("py    path3=r'" + path_input + "'")
        self.send_log.emit("py    files = [file1, file2, file3]")
        self.send_log.emit("py    paths = [path1, path2, path3]")
        self.send_log.emit("py    interp=" + str(self.interpo_choice))
        self.send_log.emit("py    pro_add=" + str(self.pro_add))
        if manning_float:
            self.send_log.emit(
                "py    manning1 = " + str(self.manning_text.text()))  # to be corrected to include text result
        else:
            self.manning_arr = np.array(self.manning_arr)
            blob = np.array2string(self.manning_arr, separator=',', )
            blob = blob.replace('\n', '')
            self.send_log.emit("py    manning1 = np.array(" + blob + ')')

        self.send_log.emit("py    np_point_vel = " + str(self.np_point_vel))
        self.send_log.emit("py    mascaret.load_mascaret_and_create_grid('Hydro_mascaret_log', path_prj, name_prj, "
                           "path_prj, 'mascaret', files, paths, interp, manning1, np_point_vel, False, pro_add, "
                           "[], '.')\n")
        self.send_log.emit("restart LOAD_MASCARET")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(path_input, self.namefile[1]))
        self.send_log.emit("restart    file3: " + os.path.join(path_input, self.namefile[2]))
        if manning_float:
            self.send_log.emit("restart    manning: " + str(self.manning1))
        else:
            blob = np.array2string(self.manning_arr, separator=',', )
            blob = blob.replace('\n', '')
            self.send_log.emit("restart    manning1 = " + self.manning_textname)
        self.send_log.emit("restart    interpo: " + str(self.interpo_choice))
        if self.interpo_choice > 0:
            self.send_log.emit("restart    pro_add: " + str(self.pro_add))

    def propose_next_file(self):
        """
        This function proposes the two other mascaret when the first is selected. If the user selects the first file,
        this function looks if a file with the same name but with the extension of the other file types exists in the
        selected folder.
        """

        if self.out_t2.text() == 'unknown file':
            blob = self.namefile[0]

            # second file (geo file)
            new_name = blob[:-len(self.extension[0][0])] + self.extension[1][0]
            pathfilename = os.path.join(self.pathfile[0], new_name)
            if os.path.isfile(pathfilename):
                self.geo_t2.setText(new_name)
                # keep the name in an attribute until we save it
                self.pathfile[1] = self.pathfile[0]
                self.namefile[1] = new_name

            # thris file (output)
            for i in range(0, 2):
                new_name = blob[:-len(self.extension[0][0])] + self.extension[2][i]
                pathfilename = os.path.join(self.pathfile[0], new_name)
                if os.path.isfile(pathfilename):
                    self.out_t2.setText(new_name)
                    # keep the name in an attribute until we save it
                    self.pathfile[2] = self.pathfile[0]
                    self.namefile[2] = new_name


class River2D(SubHydroW):
    """
   The class River2D t is there to manage the link between the graphical interface and the functions in src/river2D.py
   which loads the River2D data in 2D.

   **Technical comments**

    The class River2D inherits from SubHydroW() so it have all the methods and the variables from the class SubHydroW().
    It is similar generally to the hec-ras2D class. However, the hydrological model River2D create one file per time step.
    Hence, it is necessary to have a way to load all the files automatically. Loading one file after one file would be
    annoying. There are four functions to manage the large number of file:

    *   add_all_file: find all files in a folder selected by the user.
    *   add_file_river2D: add just one selected file
    *   Remove_all_file: remove all selected files
    *   Remove_file: remove one selected file

    None of this four functions load the data, it just add the name and path of the files to be loaded to
    self.namefile and self.pathfile. Generally, in HABBY, we load hydrological data in two steps: a) select the files,
    b) load the data. For river2D, the step b) is done by the function load_river2d_gui().
    This function is similar to the one used by Rubar2D. It has the same problem about the grid which
    is identical for all time steps and which contains all reaches together. So a temporary correction was applied.
    Data in River2D is given on the nodes as in HABBY.
     """

    def __init__(self, path_prj, name_prj):
        super(River2D, self).__init__(path_prj, name_prj)
        self.mystdout = None
        self.init_iu()

    def init_iu(self):
        """
        used by __init__ in the initialization
        """
        # update attibute for rubbar 2d
        self.attributexml = ['river2d_data']
        self.model_type = 'RIVER2D'
        self.data_type = "HYDRAULIC"
        self.namefile = []
        self.pathfile = []
        self.extension = [['.cdg'], ['.cdg']]  # list of list in case there is more than one possible ext.
        self.nb_dim = 2

        # if there is the project file with river 2d info, update the label and attibutes
        self.was_model_loaded_before(0, True)

        # geometry and output data
        self.l1 = QLabel(self.tr('<b> Geometry and Output data </.b>'))
        self.list_f = QListWidget()
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.add_file_to_list()
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if not self.namefile:
            self.butfig.setDisabled(True)

        # button
        self.choodirb = QPushButton(self.tr("Add all .cdg files (choose dir)"))
        self.choodirb.clicked.connect(self.add_all_file)
        self.removefileb = QPushButton(self.tr("Remove file"))
        self.removefileb.clicked.connect(self.remove_file)
        self.removeallfileb = QPushButton(self.tr("Remove all files"))
        self.removeallfileb.clicked.connect(self.remove_all_file)
        self.addfileb = QPushButton(self.tr("Add file"))
        self.addfileb.clicked.connect(self.add_file_river2d)
        self.load_b = QPushButton(self.tr("Create .hab file"))
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_river2d_gui)

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()
        spacer = QSpacerItem(1, 100)

        # layout
        self.layout = QGridLayout()
        self.layout.addWidget(self.l1, 0, 0)
        self.layout.addWidget(self.list_f, 1, 0, 2, 2)
        self.layout.addWidget(self.choodirb, 1, 2, 1, 2)
        self.layout.addWidget(self.addfileb, 2, 2)
        self.layout.addWidget(self.removefileb, 2, 3)
        self.layout.addWidget(self.removeallfileb, 3, 3)
        self.layout.addWidget(l2D1, 4, 0)
        self.layout.addWidget(l2D2, 4, 1, 1, 2)
        self.layout.addWidget(lh, 5, 0)
        self.layout.addWidget(self.hname, 5, 1)
        self.layout.addWidget(self.load_b, 5, 2)
        self.layout.addWidget(self.butfig, 6, 2)
        # self.layout.addItem(spacer, 7, 0)
        self.setLayout(self.layout)

    def remove_file(self):
        """
        This is small function to remove one or more .cdg file from the list of files to be loaded and from
        the QlistWidget.

        **Technical Comments**

        The function selectedIndexes does not return an int but an object called QModelIndex. We should start removing
        object from the end of the list to avoid problem. However, it is not possible to sort QModelIndex. Hence,
        It is necessary to use the row() function to get the index as int.
        """
        ind = self.list_f.selectedIndexes()  # QModelIndex Object
        int_ind = []  # int
        for i in ind:
            int_ind.append(i.row())
        int_ind = sorted(int_ind)

        for i in range(len(int_ind) - 1, -1, -1):
            self.list_f.takeItem(int_ind[i])
            del self.namefile[int_ind[i]]
            del self.pathfile[int_ind[i]]

    def remove_all_file(self):
        """
        This function removes all files from the list of files to be loaded and from the QlistWidget.
        """
        # empty list
        self.namefile = []
        self.pathfile = []
        self.list_f.clear()

    def add_file_river2d(self):
        """
        This function is used to add one file to the list of file to be loaded.
        It let the user select one or more than one file, prepare some data for it and update the QWidgetList with
        the name of the file containted in the variable self.namefile.

        We can not call show_dialog() direclty here as the user can select more than one file
        """
        # update attribute xml
        if len(self.extension) == len(self.namefile):
            self.extension.append(self.extension[0])
            self.attributexml.append(self.attributexml[0])
        # the user select file or files

        if len(self.pathfile) == 0:  # no file opened before
            filename_path = QFileDialog.getOpenFileNames(self, 'Open File', self.path_prj)[0]
        else:
            filename_path = QFileDialog.getOpenFileNames(self, 'Open File', self.pathfile[0])[0]
        if not filename_path:  # cancel case
            return
        # manage the found file
        for j in range(0, len(filename_path)):
            filename = os.path.basename(filename_path[j])
            # check extension
            extension_i = self.extension[0]
            blob, ext = os.path.splitext(filename)
            if any(e in ext for e in extension_i):
                pass
            else:
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("File type"))
                self.msg2.setText(self.tr("Needed type for the file to be loaded: " + ' ,'.join(extension_i)))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
                self.msg2.show()
            # add the filename to the variable
            self.pathfile.append(os.path.dirname(filename_path[j]))
            self.namefile.append(filename)
        # add the files to the list on the GUI
        self.add_file_to_list()

    def add_file_to_list(self):
        """
        This function to add all file contained in self.namefile to the QWidgetlist. Called by add_file_river2D and
        add_all_file.
        """
        self.list_f.clear()
        while len(self.extension) <= len(self.namefile):
            self.extension.append(self.extension[0])
            self.attributexml.append(self.attributexml[0])
        for i in range(0, len(self.namefile)):
            self.list_f.addItem(self.namefile[i])

        # add all path from the files as a QToolTip
        # only unique path is added to the Tooltip for the QComboBox
        # not possible to add a ToolTip for item in QComboBox
        pathname_unique = list(set(self.pathfile))
        pathname_unique2 = ''
        for i in range(0, len(pathname_unique)):
            pathname_unique2 += pathname_unique[i] + '\n'
        self.list_f.setToolTip(pathname_unique2[:-1])

    def add_all_file(self):
        """
        The function finds all .cdg file in one directory to add there names to the list of files to be loaded
        """

        # get the directory
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        if dir_name == '':  # cancel case
            self.send_log.emit("Warning: No selected directory for river 2d\n")
            return
        # get all file with .cdg
        dirlist = np.array(os.listdir(dir_name))
        listcdf = [e for e in dirlist if e[-4:] == self.extension[0][0]]
        # add them to name file, path file and extension
        self.namefile = listcdf
        self.pathfile = [dir_name] * len(listcdf)
        # update list
        self.add_file_to_list()
        # add proposed hdf5 name to the QLineEdit
        if len(self.namefile) > 0:
            filename2, ext = os.path.splitext(self.namefile[0])
            if len(self.namefile[0]) > 9:
                self.name_hdf5 = 'Hydro_' + self.model_type + '_' + filename2[:9]
            else:
                self.name_hdf5 = 'Hydro_' + self.model_type + '_' + filename2

            # self.polygon_hname.setAlignment(Qt.AlignRight)
            self.hname.setText(self.name_hdf5)
        else:
            self.send_log.emit('Warning: No .cdg file found in the selected directory \n')

    def load_river2d_gui(self):
        """
        This function is used to load the river 2d data. It use a second thread to avoid freezing the GUI
        """
        # for error management and figures
        self.timer.start(100)

        # test the availability of files
        if len(self.namefile) == 0:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("RIVER 2D"))
            self.msg2.setText(self.tr("Unable to load the RIVER2D data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # disable while loading
        self.load_b.setDisabled(True)

        path_hdf5 = self.find_path_hdf5()

        # get minimum water height as we might neglect very low water height
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

        for i in range(0, len(self.namefile)):
            # save each name in the project file, empty list on i == 0
            if i == 0:
                self.save_xml(i, False)
            else:
                self.save_xml(i, True)

        self.q = Queue()
        self.p = Process(target=river2d_mod.load_river2d_and_cut_grid,
                         args=(self.name_hdf5, self.namefile, self.pathfile,
                               self.name_prj, self.path_prj, self.model_type,
                               self.nb_dim, path_hdf5, self.q, False,
                               self.project_preferences))
        self.p.name = "River 2D data loading"
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log
        self.send_log.emit(self.tr('# Loading : River2D data...'))
        namefile_arr = np.array(self.namefile)
        blob = np.array2string(namefile_arr, separator=',', )
        blob = blob.replace('\n', '')
        self.send_log.emit("py    files= np.array(" + blob + ')')
        # all path inputs
        path_inputs = []
        for i in range(0, len(self.namefile)):
            path_inputs.append(path_input)
        path_inputs = np.array(path_inputs)
        blob = np.array2string(path_inputs, separator=',', )
        blob = blob.replace('\n', '')
        self.send_log.emit("py    paths= np.array(" + blob + ')')
        self.send_log.emit("py    river2d.load_river2d_and_cut_grid('Hydro_river2d_log', files, paths, name_prj, "
                           "path_prj, 'RIVER2D', 2, path_prj, [], True) \n")

        # careful, this will result in all cdg file from a folder to be loaded (to be corrected)
        self.send_log.emit("restart LOAD_RIVER_2D")
        self.send_log.emit("restart    path_to_folder: " + path_input)


class Rubar1D(SubHydroW):
    """
    The class Rubar1D is there to manage the link between the graphical interface and the functions in src/rubar1d2d_mod.py
    which loads the Rubar1D data in 1D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to Mascaret class.
    """

    def __init__(self, path_prj, name_prj):
        super(Rubar1D, self).__init__(path_prj, name_prj)
        self.inter = QComboBox()
        self.init_iu()

    def init_iu(self):
        """
        Used in the initalizatin by __init__()
        """
        # update attibute for hec-ras 1d
        self.attributexml = ['rubar_1dpro', 'data1d_rubar', '', 'manning_rubar']
        self.namefile = ['unknown file', 'unknown file', 'unknown file', 'unknown file']
        self.pathfile = ['.', '.', '.', '.']
        self.model_type = 'RUBAR1D'
        self.data_type = "HYDRAULIC"
        # no useful extension in this case, rbe is assumed
        # the function propose_next_file() uses the fact that .rbe is 4 char
        self.extension = [[''], ['']]
        self.nb_dim = 1

        # if there is the project file with rubar geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # label with the file name
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton(self.tr('Choose file (.rbe)'), self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(self.propose_next_file)
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton(self.tr('Choose file \n (profil.X)'), self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))

        # ToolTip for the path to the files
        self.geo_t2.setToolTip(self.pathfile[0])
        self.out_t2.setToolTip(self.pathfile[1])
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[1]))

        # grid creation options
        l6 = QLabel(self.tr('<b>Grid creation </b>'))
        l3 = QLabel(self.tr('Velocity distribution'))
        l32 = QLabel(self.tr("Based on Manning's formula"))
        l7 = QLabel(self.tr("Nb. of velocity points by profile"))
        l8 = QLabel(self.tr("Manning coefficient"))
        l4 = QLabel(self.tr('Interpolation of the data'))
        self.l5 = QLabel(self.tr('Nb. of additional profiles'))
        self.inter.addItems(self.interpo)
        self.nb_extrapro_text = QLineEdit('1')
        self.nb_vel_text = QLineEdit('50')
        self.manning_text = QLineEdit('0.025')
        self.ltest = QLabel(self.tr('or'))
        self.manningb = QPushButton(self.tr('Load .txt'))
        self.manningb.clicked.connect(self.load_manning_text)
        self.dis_enable_nb_profile()
        self.inter.currentIndexChanged.connect(self.dis_enable_nb_profile)

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hab file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_rubar1d)
        self.spacer1 = QSpacerItem(100, 100)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2, 0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(l6, 2, 0)
        self.layout_hec.addWidget(l3, 2, 1)
        self.layout_hec.addWidget(l32, 2, 2, 1, 2)
        self.layout_hec.addWidget(l7, 3, 1)
        self.layout_hec.addWidget(self.nb_vel_text, 3, 2)
        self.layout_hec.addWidget(l8, 4, 1)
        self.layout_hec.addWidget(self.manning_text, 4, 2)
        self.layout_hec.addWidget(self.ltest, 4, 3)
        self.layout_hec.addWidget(self.manningb, 4, 4)
        self.layout_hec.addWidget(l4, 5, 1)
        self.layout_hec.addWidget(self.inter, 5, 2)
        self.layout_hec.addWidget(self.l5, 6, 1)
        self.layout_hec.addWidget(self.nb_extrapro_text, 6, 2)
        self.layout_hec.addWidget(lh, 7, 0)
        self.layout_hec.addWidget(self.hname, 7, 1)
        self.layout_hec.addWidget(self.load_b, 8, 2)
        self.layout_hec.addWidget(self.butfig, 8, 4)
        # self.layout_hec.addItem(self.spacer1, 9, 1)
        self.setLayout(self.layout_hec)

    def load_rubar1d(self):
        """
        A function to execute the loading and saving the the rubar file using rubar1d2d_mod.py. After loading the data,
        it distribute the velocity along the profiles by calling self.distribute_velocity() and it created the 2D grid
        by calling the method self.grid_and_interpo.
        """
        # test the availability of files
        fileNOK = True
        f0 = os.path.join(self.pathfile[0], self.namefile[0])
        f1 = os.path.join(self.pathfile[1], self.namefile[1])
        if os.path.isfile(f0) & os.path.isfile(f1):
            fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("RUBAR BE"))
            self.msg2.setText(self.tr("Unable to load RUBAR data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)

        # get the image and load option
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.load_b.setDisabled(True)
        self.name_hdf5 = self.hname.text()
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
        show_all_fig = True
        if path_im != 'no_path':
            self.save_fig = True
        self.interpo_choice = self.inter.currentIndex()

        # preparation for the velocity distibution
        manning_float = False
        # we have two cases possible: a manning array or a manning float. here we take the case manning as float
        if isinstance(self.manning_arr, float) or isinstance(self.manning_arr, np.float):
            self.manning_arr = []
        if len(self.manning_arr) == 0:
            try:
                manning_float = True
                self.manning_arr = float(self.manning_text.text())
            except ValueError:
                self.send_log.emit("Error: The manning value is not understood.")
                return
        try:
            self.np_point_vel = int(self.nb_vel_text.text())
        except ValueError:
            self.send_log.emit("Error: The number of velocity point is not understood.")
            return

        # load rubar 1D, distribute velcoity and create the grid
        self.q = Queue()
        # for error management and figures (when time finished call the self.show_prog function)
        self.timer.start(100)
        self.p = Process(target=rubar1d2d_mod.load_rubar1d_and_create_grid,
                         args=(self.name_hdf5, path_hdf5, self.name_prj,
                               self.path_prj, self.model_type, self.namefile,
                               self.pathfile, self.interpo_choice,
                               self.manning_arr, self.np_point_vel,
                               show_all_fig, self.pro_add, self.q, path_im))
        self.p.name = "Rubar 1D data loading"
        self.p.start()

        # path input
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: Rubar 1D data...'))
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    file2=r'" + self.namefile[1] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    path2=r'" + path_input + "'")
        self.send_log.emit("py    files = [file1, file2]")
        self.send_log.emit("py    paths = [path1, path2]")
        self.send_log.emit("py    interp=" + str(self.interpo_choice))
        self.send_log.emit("py    pro_add=" + str(self.pro_add))
        if manning_float:
            self.send_log.emit("py    manning1 = " + str(self.manning_text.text()))
        else:
            self.manning_arr = np.array(self.manning_arr)
            blob = np.array2string(self.manning_arr, separator=',', )
            blob = blob.replace('\n', '')
            self.send_log.emit("py    manning1 = np.array(" + blob + ')')
        self.send_log.emit("py    np_point_vel = " + str(self.np_point_vel))
        self.send_log.emit("py    rubar.load_rubar1d_and_create_grid('Hydro_rubar1d_log', path_prj, name_prj, path_prj,"
                           " 'RUBAR1D',files, paths, interp,manning1, np_point_vel, False, pro_add, [])\n")
        self.send_log.emit("restart LOAD_RUBAR_1D")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(path_input, self.namefile[1]))
        if manning_float:
            self.send_log.emit("restart    manning: " + str(self.manning1))
        else:
            blob = np.array2string(self.manning_arr, separator=',', )
            blob = blob.replace('\n', '')
            self.send_log.emit("restart    manning1 = " + self.manning_textname)
        self.send_log.emit("restart    interpo: " + str(self.interpo_choice))
        if self.interpo_choice > 0:
            self.send_log.emit("restart    pro_add: " + str(self.pro_add))

    def propose_next_file(self):
        """
        This function proposes the other rubar file when the first is selected. If the user selects the first file,
        this function looks if a file of the form profil.name exist
        """

        if self.out_t2.text() == 'unknown file':
            blob = self.namefile[0]

            # second file (geo file)
            new_name = 'profil.' + blob[:-4]
            pathfilename = os.path.join(self.pathfile[0], new_name)
            if os.path.isfile(pathfilename):
                self.out_t2.setText(new_name)
                # keep the name in an attribute until we save it
                self.pathfile[1] = self.pathfile[0]
                self.namefile[1] = new_name


class HEC_RAS2D(SubHydroW):
    """
    The class hec_RAS2D is there to manage the link between the graphical interface and the functions in src/hec_ras2D_mod.py
    which loads the hec_ras2D data in 2D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class and it has the same problem about node/cell
    which will need to be corrected.
    """

    def __init__(self, path_prj, name_prj):

        super(HEC_RAS2D, self).__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        This method is used to by __init__() during the initialization.
        """

        # update attibutes
        self.attributexml = ['data2D']
        self.model_type = 'HECRAS2D'
        self.data_type = "HYDRAULIC"
        self.extension = [['.hdf']]
        self.nb_dim = 2

        # if there is the project file with hecras info, update the label and attibutes
        self.was_model_loaded_before()
        # self.h2d_t2 = QLabel(self.namefile[0], self)

        self.h2d_t2 = QComboBox()
        self.h2d_t2.addItems([self.namefile[0]])
        self.h2d_t2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # geometry and output data
        l1 = QLabel(self.tr('HEC-RAS2D result file(s)'))
        self.h2d_b = QPushButton(self.tr('Choose file(s) (.hdf, .txt)'), self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog_hec_ras2d(0))

        # reach
        reach_name_title_label = QLabel(self.tr('Reach name'))
        self.reach_name_label = QLabel(self.tr('unknown'))

        # unit type
        units_name_title_label = QLabel(self.tr('Unit(s) type'))
        self.units_name_label = QLabel(self.tr('unknown'))

        # unit number
        l2 = QLabel(self.tr('Unit(s) number'))
        self.number_timstep_label = QLabel(self.tr('unknown'))

        # unit list
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.setMinimumHeight(100)
        l_selecttimestep = QLabel(self.tr('Unit(s) selected'))
        # ToolTip to indicated in which folder are the files
        self.h2d_t2.setToolTip(self.pathfile[0])
        self.h2d_b.clicked.connect(
            lambda: self.h2d_t2.setToolTip(self.pathfile[0]))

        # epsg
        epsgtitle_hec_ras2d_label = QLabel(self.tr('EPSG code'))
        self.epsg_hec_ras2d_label = QLineEdit(self.tr('unknown'))
        self.epsg_hec_ras2d_label.editingFinished.connect(self.set_epsg_code)

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
        #     self.gethdf5_name_gui()
        #     if self.h2d_t2.text()[-4:] in self.extension[0]:
        #         self.get_ascii_model_description()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_hec_ras_2d_gui)
        self.spacer = QSpacerItem(1, 180)
        # self.butfig = QPushButton(self.tr("create figure"))
        # self.butfig.clicked.connect(self.recreate_image)
        # if self.namefile[0] == 'unknown file':
        #     self.butfig.setDisabled(True)

        # last hdf5 created
        self.name_last_hdf5(type="TELEMAC")  # find the name of the last merge file and add it to self.lm2

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2, 0, 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(reach_name_title_label, 1, 0)
        self.layout_hec2.addWidget(self.reach_name_label, 1, 1)
        self.layout_hec2.addWidget(units_name_title_label, 2, 0)
        self.layout_hec2.addWidget(self.units_name_label, 2, 1)
        self.layout_hec2.addWidget(l2, 3, 0)
        self.layout_hec2.addWidget(self.number_timstep_label, 3, 1)
        self.layout_hec2.addWidget(l_selecttimestep, 4, 0)
        self.layout_hec2.addWidget(self.units_QListWidget, 4, 1, 1, 1)  # from row, from column, nb row, nb column
        self.layout_hec2.addWidget(epsgtitle_hec_ras2d_label, 5, 0)
        self.layout_hec2.addWidget(self.epsg_hec_ras2d_label, 5, 1)
        self.layout_hec2.addWidget(lh, 6, 0)
        self.layout_hec2.addWidget(self.hname, 6, 1)
        self.layout_hec2.addWidget(self.load_b, 6, 2)
        self.layout_hec2.addWidget(self.last_hydraulic_file_label, 7, 0)
        self.layout_hec2.addWidget(self.last_hydraulic_file_name_label, 7, 1)
        [self.layout_hec2.setRowMinimumHeight(i, 30) for i in range(self.layout_hec2.rowCount())]

        self.setLayout(self.layout_hec2)
        #
        # # geometry and output data
        # min_height = QLabel(self.tr('<b> Geometry and output data </b>'))
        # self.h2d_b = QPushButton(self.tr('Choose file (.hdf, .h5)'), self)
        # self.h2d_b.clicked.connect(lambda: self.show_dialog(0))
        # self.h2d_b.clicked.connect(lambda: self.h2d_t2.setText(self.namefile[0]))
        # l2 = QLabel(self.tr('<b> Options </b>'))
        # l3 = QLabel('All time step', self)
        # l4 = QLabel('All flow area', self)
        #
        # # grid creation
        # l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        # l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))
        #
        # # ToolTip to indicated in which folder are the files
        # self.h2d_t2.setToolTip(self.pathfile[0])
        # self.h2d_b.clicked.connect(lambda: self.h2d_t2.setToolTip(self.pathfile[0]))
        #
        # # hdf5 name
        # lh = QLabel(self.tr('.hyd file name'))
        # self.hname = QLineEdit(self.name_hdf5)
        # self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
        #     self.gethdf5_name_gui()
        #
        # # load button
        # self.load_b = QPushButton(self.tr('Load data and create hab file'), self)
        # self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        # self.load_b.clicked.connect(self.load_hec_2d_gui)
        # self.spacer = QSpacerItem(1, 200)
        # self.butfig = QPushButton(self.tr("create figure"))
        # self.butfig.clicked.connect(self.recreate_image)
        # if self.namefile[0] == 'unknown file':
        #     self.butfig.setDisabled(True)
        #
        # # layout
        # self.layout_ascii = QGridLayout()
        # self.layout_ascii.addWidget(min_height, 0, 0)
        # self.layout_ascii.addWidget(self.h2d_t2, 0, 1)
        # self.layout_ascii.addWidget(self.h2d_b, 0, 2)
        # self.layout_ascii.addWidget(l2, 1, 0)
        # self.layout_ascii.addWidget(l3, 1, 1)
        # self.layout_ascii.addWidget(l4, 1, 2)
        # self.layout_ascii.addWidget(l2D1, 2, 0)
        # self.layout_ascii.addWidget(l2D2, 2, 1, 1, 2)
        # self.layout_ascii.addWidget(lh, 3, 0)
        # self.layout_ascii.addWidget(self.hname, 3, 1)
        # self.layout_ascii.addWidget(self.load_b, 4, 2)
        # self.layout_ascii.addWidget(self.butfig, 5, 2)
        # # self.layout_ascii.addItem(self.spacer, 6, 1)
        # self.setLayout(self.layout_ascii)

    def show_dialog_hec_ras2d(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """
        # disconnect function for multiple file cases
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        # prepare the filter to show only useful files
        if len(self.extension[i]) <= 4:
            filter2 = "File ("
            for e in self.extension[i]:
                filter2 += '*' + e + ' '
            filter2 = filter2[:-1]
            filter2 += ')' + ";; All File (*.*)"
        else:
            filter2 = ''

        # get last path
        if self.read_attribute_xml(self.attributexml[0]) != self.path_prj and self.read_attribute_xml(
                self.attributexml[0]) != "no_data":
            model_path = self.read_attribute_xml(self.attributexml[0])  # path spe
        elif self.read_attribute_xml("Path_last_file_loaded") != self.path_prj:
            model_path = self.read_attribute_xml("Path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        # find the filename based on user choice
        filename_list = QFileDialog.getOpenFileNames(self,
                                                     self.tr("Select file(s)"),
                                                     model_path,
                                                     filter2)

        # init
        self.hydrau_case = "unknown"
        self.multi_hdf5 = False
        self.index_hydrau_presence = False

        # if file has been selected
        if filename_list[0]:
            # clean GUI
            self.clean_gui()

            # get_hydrau_description_from_source
            hydrau_description, warning_list = hydro_input_file_mod.get_hydrau_description_from_source(filename_list[0],
                                                                                                        self.path_prj,
                                                                                                        self.model_type,
                                                                                                        self.nb_dim)
            # warnings
            if warning_list:
                for warn in warning_list:
                    self.send_log.emit(warn)

            # error
            if type(hydrau_description) == str:
                self.clean_gui()
                self.send_log.emit(hydrau_description)

            # one hdf5
            if type(hydrau_description) == dict:
                # multi
                self.multi_hdf5 = False
                # save last path
                self.pathfile[0] = hydrau_description["path_filename_source"]  # source file path
                self.namefile[0] = hydrau_description["filename_source"]  # source file name
                self.name_hdf5 = hydrau_description["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description = hydrau_description
                # to GUI (decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems([self.hydrau_description["filename_source"]])
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"].split(", "))
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"].split(", "))):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_hec_ras2d_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.load_b.setText(self.tr("Create .hyd file"))
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

            # multi hdf5
            if type(hydrau_description) == list:
                # multi
                self.multi_hdf5 = True
                # save last path
                self.pathfile[0] = hydrau_description[0]["path_filename_source"]  # source file path
                self.namefile[0] = hydrau_description[0]["filename_source"]  # source file name
                self.name_hdf5 = hydrau_description[0]["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description_multiple = hydrau_description
                self.hydrau_description = hydrau_description[0]
                # get names
                names = [description["filename_source"] for description in self.hydrau_description_multiple]
                # to GUI (first decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems(names)
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"].split(", "))
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"].split(", "))):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_hec_ras2d_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.h2d_t2.currentIndexChanged.connect(self.change_gui_when_combobox_name_change)
                self.load_b.setText(self.tr("Create ") + str(len(hydrau_description)) + self.tr(" .hyd files"))
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

    def change_gui_when_combobox_name_change(self):
        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        # change hec_ras2d description
        self.hydrau_description = self.hydrau_description_multiple[self.h2d_t2.currentIndex()]

        # change GUI
        self.reach_name_label.setText(self.hydrau_description["reach_list"])
        self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
        self.units_QListWidget.clear()
        self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"].split(", "))
        # change selection items
        for i in range(len(self.hydrau_description["unit_list_full"].split(", "))):
            self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
        self.epsg_hec_ras2d_label.setText(self.hydrau_description["epsg_code"])
        self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
        self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
        self.unit_counter()

    def unit_counter(self):
        # count total number items (units)
        total = self.units_QListWidget.count()
        # count total number items selected
        selected = len(self.units_QListWidget.selectedItems())

        # refresh hec_ras2d dictonnary
        unit_list = []
        unit_list_full = []
        selected_list = []
        for i in range(total):
            unit_list_full.append(self.units_QListWidget.item(i).text())
            selected_list.append(self.units_QListWidget.item(i).isSelected())
            if self.units_QListWidget.item(i).isSelected():
                unit_list.append(self.units_QListWidget.item(i).text())

        # save multi
        if self.hydrau_case == '4.a' or self.hydrau_case == '4.b' or (
                self.hydrau_case == 'unknown' and self.multi_hdf5):
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list"] = ", ".join(unit_list)
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_full"] = ", ".join(unit_list_full)
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_tf"] = selected_list
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_number"] = str(selected)
        # save one
        else:
            self.hydrau_description["unit_list"] = ", ".join(unit_list)
            self.hydrau_description["unit_list_full"] = ", ".join(unit_list_full)
            self.hydrau_description["unit_list_tf"] = selected_list
            self.hydrau_description["unit_number"] = str(selected)

        # set text
        text = str(selected) + "/" + str(total)
        self.number_timstep_label.setText(text)  # number units

    def clean_gui(self):
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        self.h2d_t2.clear()
        self.h2d_t2.addItems(["unknown file"])
        self.reach_name_label.setText("unknown")
        self.units_name_label.setText("unknown")  # kind of unit
        self.number_timstep_label.setText("unknown")  # number units
        self.units_QListWidget.clear()
        self.units_QListWidget.setEnabled(True)
        self.epsg_hec_ras2d_label.setEnabled(True)
        self.hname.setText("")  # hdf5 name
        self.load_b.setText("Create .hyd file")

    def get_time_step(self):
        """
        The function get timestep if selafin files to display them in GUI, in order for the user to be able to choose some of them.
        """
        nbtimes, timestep = hec_ras2d_mod.get_time_step(self.namefile[0], self.pathfile[0])

        # number timestep
        self.number_timstep_label.setText(str(nbtimes))

        self.units_QListWidget.clear()
        self.units_QListWidget.addItems(timestep)
        for i in range(nbtimes):
            self.units_QListWidget.item(i).setSelected(True)
            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignRight)
        # self.units_QListWidget.setFixedWidth(self.units_QListWidget.sizeHintForColumn(0)
        # + (self.units_QListWidget.sizeHintForColumn(0) * 0.6))

    def set_epsg_code(self):
        if hasattr(self, 'hydrau_description'):
            self.hydrau_description["epsg_code"] = self.epsg_hec_ras2d_label.text()

    def load_hec_ras_2d_gui(self):
        """
        The function which call the function which load hec_ras2d and
         save the name of files in the project file
        """
        # get timestep and epsg selected
        if self.multi_hdf5:
            for i in range(len(self.hydrau_description_multiple)):
                if not any(self.hydrau_description_multiple[i]["unit_list_tf"]):
                    self.send_log.emit("Error: No units selected for : " + self.hydrau_description_multiple[i][
                        "filename_source"] + "\n")
                    return
        if not self.multi_hdf5:
            selection = self.units_QListWidget.selectedItems()
            if not selection:
                self.send_log.emit("Error: No units selected. \n")
                return
            self.hydrau_description["epsg_code"] = self.epsg_hec_ras2d_label.text()

        # for error management and figures
        self.timer.start(100)

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)

        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # get minimum water height as we might neglect very low water height
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

        # block button
        self.load_b.setDisabled(True)  # hydraulic

        # write the new file name in the project file
        self.save_xml(0)

        # path input
        path_input = self.find_path_input()

        # load the hec_ras2d data
        self.q = Queue()
        self.progress_value = Value("i", 0)

        # check hec_ras2d cases
        if self.hydrau_case == '4.a' or self.hydrau_case == '4.b' or (
                self.hydrau_case == 'unknown' and self.multi_hdf5):
            # refresh units selection
            self.p = Process(target=hec_ras2D_mod.load_hec_ras_2d_and_cut_grid,
                             args=(self.hydrau_description_multiple,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences))
        else:
            self.hydrau_description["hdf5_name"] = self.name_hdf5
            self.p = Process(target=hec_ras2D_mod.load_hec_ras_2d_and_cut_grid,
                             args=(self.hydrau_description,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences))
        self.p.name = "HEC_RAS2D data loading"
        self.p.start()

        # copy input files
        nb_files = len(self.namefile[0].split(", "))
        files_list = self.namefile[0].split(", ")
        path_file_list = [self.pathfile[0]] * nb_files
        if nb_files > 1:
            self.p2 = Process(target=hdf5_mod.copy_files, args=(files_list, path_file_list, path_input))
            self.p2.start()
        if nb_files == 1:
            self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
            self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: TELEMAC data...'))
        self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit(
            "py    selafin_habby1.load_hec_ras2d_and_cut_grid('hydro_hec_ras2d_log', file1, path1, name_prj, "
            "path_prj, 'TELEMAC', 2, path_prj, [], True )\n")
        self.send_log.emit("restart LOAD_TELEMAC")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))


class TELEMAC(SubHydroW):  # QGroupBox
    """
    The class Telemac is there to manage the link between the graphical
    interface and the functions in src/telemac_mod.py
    which loads the Telemac data in 2D. It inherits from SubHydroW()
    so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class,
    but data from Telemac is on the node as in HABBY.
    """

    def __init__(self, path_prj, name_prj):

        super(TELEMAC, self).__init__(path_prj, name_prj)
        self.hydrau_case = "unknown"
        self.multi_hdf5 = False
        # update the attibutes
        self.attributexml = ['telemac_path']
        self.model_type = 'TELEMAC'
        self.data_type = "HYDRAULIC"
        self.extension = [['.res', '.slf', '.srf', '.txt']]
        self.nb_dim = 2
        self.init_iu()

    def init_iu(self):
        """
        Used by __init__() during the initialization.
        """

        # if there is the project file with telemac info, update
        # the label and attibutes
        self.was_model_loaded_before()
        # self.h2d_t2 = QLabel(self.namefile[0], self)
        self.h2d_t2 = QComboBox()
        self.h2d_t2.addItems([self.namefile[0]])
        self.h2d_t2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # geometry and output data
        l1 = QLabel(self.tr('TELEMAC result file(s)'))
        self.h2d_b = QPushButton(self.tr('Choose file(s) (.slf, .srf, .res, .txt)'), self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog_telemac(0))

        # reach
        reach_name_title_label = QLabel(self.tr('Reach name'))
        self.reach_name_label = QLabel(self.tr('unknown'))

        # unit type
        units_name_title_label = QLabel(self.tr('Unit(s) type'))
        self.units_name_label = QLabel(self.tr('unknown'))

        # unit number
        l2 = QLabel(self.tr('Unit(s) number'))
        self.number_timstep_label = QLabel(self.tr('unknown'))

        # unit list
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.setMinimumHeight(100)
        l_selecttimestep = QLabel(self.tr('Unit(s) selected'))
        # ToolTip to indicated in which folder are the files
        self.h2d_t2.setToolTip(self.pathfile[0])
        self.h2d_b.clicked.connect(
            lambda: self.h2d_t2.setToolTip(self.pathfile[0]))

        # epsg
        epsgtitle_telemac_label = QLabel(self.tr('EPSG code'))
        self.epsg_label = QLineEdit(self.tr('unknown'))
        self.epsg_label.editingFinished.connect(self.set_epsg_code)

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
        #     self.gethdf5_name_gui()
        #     if self.h2d_t2.text()[-4:] in self.extension[0]:
        #         self.get_ascii_model_description()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_telemac_gui)
        self.spacer = QSpacerItem(1, 180)
        # self.butfig = QPushButton(self.tr("create figure"))
        # self.butfig.clicked.connect(self.recreate_image)
        # if self.namefile[0] == 'unknown file':
        #     self.butfig.setDisabled(True)

        # last hdf5 created
        self.name_last_hdf5(type="TELEMAC")  # find the name of the last merge file and add it to self.lm2

        self.last_hydraulic_file_label = QLabel(self.tr('Last file created'))
        self.last_hydraulic_file_name_label = QLabel(self.tr('no file'))

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2, 0, 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(reach_name_title_label, 1, 0)
        self.layout_hec2.addWidget(self.reach_name_label, 1, 1)
        self.layout_hec2.addWidget(units_name_title_label, 2, 0)
        self.layout_hec2.addWidget(self.units_name_label, 2, 1)
        self.layout_hec2.addWidget(l2, 3, 0)
        self.layout_hec2.addWidget(self.number_timstep_label, 3, 1)
        self.layout_hec2.addWidget(l_selecttimestep, 4, 0)
        self.layout_hec2.addWidget(self.units_QListWidget, 4, 1, 1, 1)  # from row, from column, nb row, nb column
        self.layout_hec2.addWidget(epsgtitle_telemac_label, 5, 0)
        self.layout_hec2.addWidget(self.epsg_label, 5, 1)
        self.layout_hec2.addWidget(lh, 6, 0)
        self.layout_hec2.addWidget(self.hname, 6, 1)
        self.layout_hec2.addWidget(self.load_b, 6, 2)
        self.layout_hec2.addWidget(self.last_hydraulic_file_label, 7, 0)
        self.layout_hec2.addWidget(self.last_hydraulic_file_name_label, 7, 1)
        [self.layout_hec2.setRowMinimumHeight(i, 30) for i in range(self.layout_hec2.rowCount())]

        self.setLayout(self.layout_hec2)

    def show_dialog_telemac(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """
        # disconnect function for multiple file cases
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        # prepare the filter to show only useful files
        if len(self.extension[i]) <= 4:
            filter2 = "File ("
            for e in self.extension[i]:
                filter2 += '*' + e + ' '
            filter2 = filter2[:-1]
            filter2 += ')' + ";; All File (*.*)"
        else:
            filter2 = ''

        # get last path
        if self.read_attribute_xml(self.attributexml[0]) != self.path_prj and self.read_attribute_xml(
                self.attributexml[0]) != "no_data":
            model_path = self.read_attribute_xml(self.attributexml[0])  # path spe
        elif self.read_attribute_xml("Path_last_file_loaded") != self.path_prj:
            model_path = self.read_attribute_xml("Path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        # find the filename based on user choice
        filename_list = QFileDialog.getOpenFileNames(self,
                                                     self.tr("Select file(s)"),
                                                     model_path,
                                                     filter2)

        # init
        self.hydrau_case = "unknown"
        self.multi_hdf5 = False
        self.index_hydrau_presence = False

        # if file has been selected
        if filename_list[0]:
            # clean GUI
            self.clean_gui()

            # get_hydrau_description_from_source
            telemac_description, warning_list = hydro_input_file_mod.get_hydrau_description_from_source(filename_list[0],
                                                                                                        self.path_prj,
                                                                                                        self.model_type,
                                                                                                        self.nb_dim)

            # warnings
            if warning_list:
                for warn in warning_list:
                    self.send_log.emit(warn)

            # error
            if type(telemac_description) == str:
                self.clean_gui()
                self.send_log.emit(telemac_description)

            # one hdf5
            if type(telemac_description) == dict:
                self.hydrau_case = telemac_description["hydrau_case"]
                # multi
                self.multi_hdf5 = False
                # save last path
                self.pathfile[0] = telemac_description["path_filename_source"]  # source file path
                self.namefile[0] = telemac_description["filename_source"]  # source file name
                self.name_hdf5 = telemac_description["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description = telemac_description
                # to GUI (decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems([self.hydrau_description["filename_source"]])
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"])
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"])):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.load_b.setText("Create .hyd file")
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

            # multi hdf5
            if type(telemac_description) == list:
                self.hydrau_case = telemac_description[0]["hydrau_case"]
                # multi
                self.multi_hdf5 = True
                # save last path
                self.pathfile[0] = telemac_description[0]["path_filename_source"]  # source file path
                self.namefile[0] = telemac_description[0]["filename_source"]  # source file name
                self.name_hdf5 = telemac_description[0]["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description_multiple = telemac_description
                self.hydrau_description = telemac_description[0]
                # get names
                names = [description["filename_source"] for description in self.hydrau_description_multiple]
                # to GUI (first decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems(names)
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"])
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"])):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.h2d_t2.currentIndexChanged.connect(self.change_gui_when_combobox_name_change)
                self.load_b.setText("Create " + str(len(telemac_description)) + " .hyd files")
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

    def change_gui_when_combobox_name_change(self):
        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        self.hydrau_description["hdf5_name"] = self.hname.text()

        # change telemac description
        self.hydrau_description = self.hydrau_description_multiple[self.h2d_t2.currentIndex()]

        # change GUI
        self.reach_name_label.setText(self.hydrau_description["reach_list"])
        self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
        self.units_QListWidget.clear()
        self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"])
        # change selection items
        for i in range(len(self.hydrau_description["unit_list_full"])):
            self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
        self.epsg_label.setText(self.hydrau_description["epsg_code"])
        if not os.path.splitext(self.hydrau_description["hdf5_name"])[1]:
            self.hydrau_description["hdf5_name"] = self.hydrau_description["hdf5_name"] + ".hyd"
        self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
        self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
        self.unit_counter()

    def unit_counter(self):
        # count total number items (units)
        total = self.units_QListWidget.count()
        # count total number items selected
        selected = len(self.units_QListWidget.selectedItems())
        # refresh telemac dictonnary
        unit_list = []
        unit_list_full = []
        selected_list = []
        for i in range(total):
            unit_list_full.append(self.units_QListWidget.item(i).text())
            selected_list.append(self.units_QListWidget.item(i).isSelected())
            if self.units_QListWidget.item(i).isSelected():
                unit_list.append(self.units_QListWidget.item(i).text())

        # save multi
        if self.hydrau_case == '4.a' or self.hydrau_case == '4.b' or (
                self.hydrau_case == 'unknown' and self.multi_hdf5):
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list"] = unit_list
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_full"] = unit_list_full
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_tf"] = selected_list
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_number"] = str(selected)

            if self.hydrau_case == '2.a' or self.hydrau_case == '2.b':
                # preset name hdf5
                filename_source_list = self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["filename_source"].split(", ")
                new_names_list = []
                for file_num, file in enumerate(filename_source_list):
                    if self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_tf"][file_num]:
                        new_names_list.append(os.path.splitext(file)[0])
                self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["hdf5_name"] = "_".join(new_names_list) + ".hyd"
                self.hname.setText(self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["hdf5_name"])  # hdf5 name

        # save one
        else:
            self.hydrau_description["unit_list"] = unit_list
            self.hydrau_description["unit_list_full"] = unit_list_full
            self.hydrau_description["unit_list_tf"] = selected_list
            self.hydrau_description["unit_number"] = str(selected)

            if self.hydrau_case == '2.a' or self.hydrau_case == '2.b':
                # preset name hdf5
                filename_source_list = self.hydrau_description["filename_source"].split(", ")
                new_names_list = []
                for file_num, file in enumerate(filename_source_list):
                    if self.hydrau_description["unit_list_tf"][file_num]:
                        new_names_list.append(os.path.splitext(file)[0])
                self.hydrau_description["hdf5_name"] = "_".join(new_names_list) + ".hyd"
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name

        # set text
        text = str(selected) + "/" + str(total)
        self.number_timstep_label.setText(text)  # number units

    def clean_gui(self):
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        self.h2d_t2.clear()
        self.h2d_t2.addItems(["unknown file"])
        self.reach_name_label.setText("unknown")
        self.units_name_label.setText("unknown")  # kind of unit
        self.number_timstep_label.setText("unknown")  # number units
        self.units_QListWidget.clear()
        self.units_QListWidget.setEnabled(True)
        self.epsg_label.setEnabled(True)
        self.hname.setText("")  # hdf5 name
        self.load_b.setText("Create .hyd file")

    def get_time_step(self):
        """
        The function get timestep if selafin files to display them in GUI, in order for the user to be able to choose some of them.
        """
        nbtimes, timestep = telemac_mod.get_time_step(self.namefile[0], self.pathfile[0])

        # number timestep
        self.number_timstep_label.setText(str(nbtimes))

        self.units_QListWidget.clear()
        self.units_QListWidget.addItems(timestep)
        for i in range(nbtimes):
            self.units_QListWidget.item(i).setSelected(True)
            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignRight)
        # self.units_QListWidget.setFixedWidth(self.units_QListWidget.sizeHintForColumn(0)
        # + (self.units_QListWidget.sizeHintForColumn(0) * 0.6))

    def set_epsg_code(self):
        if hasattr(self, 'hydrau_description'):
            self.hydrau_description["epsg_code"] = self.epsg_label.text()

    def load_telemac_gui(self):
        """
        The function which call the function which load telemac and
         save the name of files in the project file
        """
        # get timestep and epsg selected
        if self.multi_hdf5:
            for i in range(len(self.hydrau_description_multiple)):
                if not any(self.hydrau_description_multiple[i]["unit_list_tf"]):
                    self.send_log.emit("Error: No units selected for : " + self.hydrau_description_multiple[i][
                        "filename_source"] + "\n")
                    return
        if not self.multi_hdf5:
            selection = self.units_QListWidget.selectedItems()
            if not selection:
                self.send_log.emit("Error: No units selected. \n")
                return
            self.hydrau_description["epsg_code"] = self.epsg_label.text()

        # for error management and figures
        self.timer.start(100)

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)

        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()

        # check if extension is set by user (one hdf5 case)
        self.name_hdf5 = self.hname.text()
        if not self.multi_hdf5:
            if not os.path.splitext(self.name_hdf5)[1]:
                self.name_hdf5 = self.name_hdf5 + ".hyd"

        # check if extension is set by user (multi hdf5 case)
        if self.multi_hdf5:
            for hdf5_num in range(len(self.hydrau_description_multiple)):
                if not os.path.splitext(self.hydrau_description_multiple[hdf5_num]["hdf5_name"])[1]:
                    self.hydrau_description_multiple[hdf5_num]["hdf5_name"] = self.hydrau_description_multiple[hdf5_num]["hdf5_name"] + ".hyd"

        # get minimum water height as we might neglect very low water height
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

        # block button
        self.load_b.setDisabled(True)  # hydraulic

        # write the new file name in the project file
        self.save_xml(0)

        # path input
        path_input = self.find_path_input()

        # load the telemac data
        self.q = Queue()
        self.progress_value = Value("i", 0)

        # check telemac cases
        if self.hydrau_case == '4.a' or self.hydrau_case == '4.b' or (
                self.hydrau_case == 'unknown' and self.multi_hdf5):
            # refresh units selection
            self.p = Process(target=telemac_mod.load_telemac_and_cut_grid,
                             args=(self.hydrau_description_multiple,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences))
        else:
            self.hydrau_description["hdf5_name"] = self.name_hdf5
            self.p = Process(target=telemac_mod.load_telemac_and_cut_grid,
                             args=(self.hydrau_description,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences))
        self.p.name = "TELEMAC data loading"
        self.p.start()

        # copy input files
        nb_files = len(self.namefile[0].split(", "))
        files_list = self.namefile[0].split(", ")
        path_file_list = [self.pathfile[0]] * nb_files
        if nb_files > 1:
            self.p2 = Process(target=hdf5_mod.copy_files, args=(files_list, path_file_list, path_input))
            self.p2.start()
        if nb_files == 1:
            self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
            self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: TELEMAC data...'))
        self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit(
            "py    selafin_habby1.load_telemac_and_cut_grid('hydro_telemac_log', file1, path1, name_prj, "
            "path_prj, 'TELEMAC', 2, path_prj, [], True )\n")
        self.send_log.emit("restart LOAD_TELEMAC")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))


class ASCII(SubHydroW):  # QGroupBox
    """
    The class Telemac is there to manage the link between the graphical
    interface and the functions in src/ascii_mod.py
    which loads the Telemac data in 2D. It inherits from SubHydroW()
    so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class,
    but data from Telemac is on the node as in HABBY.
    """
    drop_merge = pyqtSignal()

    def __init__(self, path_prj, name_prj):

        super(ASCII, self).__init__(path_prj, name_prj)
        self.hydrau_case = "unknown"
        self.multi_hdf5 = False
        self.multi_reach = False
        self.attributexml = ['ascii_path']
        self.model_type = 'ASCII'
        self.data_type = "HYDRAULIC"
        self.extension = [['.txt']]
        self.nb_dim = 2
        self.init_iu()

    def init_iu(self):
        """
        Used by __init__() during the initialization.
        """
        # if there is the project file with ascii info, update
        # the label and attibutes
        self.was_model_loaded_before()
        # self.h2d_t2 = QLabel(self.namefile[0], self)
        self.h2d_t2 = QComboBox()
        self.h2d_t2.addItems([self.namefile[0]])
        self.h2d_t2.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # geometry and output data
        l1 = QLabel(self.tr('ASCII hydraulic model file(s)'))
        self.h2d_b = QPushButton(self.tr('Choose file(s) (.txt)'), self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog_ascii(0))

        # reach
        reach_name_title_label = QLabel(self.tr('Reach name'))
        self.reach_name_label = QLabel(self.tr('unknown'))

        # unit type
        units_name_title_label = QLabel(self.tr('Unit(s) type'))
        self.units_name_label = QLabel(self.tr('unknown'))

        # unit number
        l2 = QLabel(self.tr('Unit(s) number'))
        self.number_unit_label = QLabel(self.tr('unknown'))

        # unit list
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.setMinimumHeight(100)
        l_selecttimestep = QLabel(self.tr('Unit(s) selected'))
        # ToolTip to indicated in which folder are the files
        self.h2d_t2.setToolTip(self.pathfile[0])
        self.h2d_b.clicked.connect(
            lambda: self.h2d_t2.setToolTip(self.pathfile[0]))

        # epsg
        epsgtitle_ascii_label = QLabel(self.tr('EPSG code'))
        self.epsg_label = QLineEdit(self.tr('unknown'))

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        # if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
        #     self.gethdf5_name_gui()
        #     if self.h2d_t2.text()[-4:] in self.extension[0]:
        #         self.get_ascii_model_description()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_ascii_gui)
        self.spacer = QSpacerItem(1, 180)
        # self.butfig = QPushButton(self.tr("create figure"))
        # self.butfig.clicked.connect(self.recreate_image)
        # if self.namefile[0] == 'unknown file':
        #     self.butfig.setDisabled(True)

        # last hdf5 created
        self.name_last_hdf5(type="TELEMAC")  # find the name of the last merge file and add it to self.lm2

        # layout
        self.layout_ascii = QGridLayout()
        self.layout_ascii.addWidget(l1, 0, 0)
        self.layout_ascii.addWidget(self.h2d_t2, 0, 1)
        self.layout_ascii.addWidget(self.h2d_b, 0, 2)
        self.layout_ascii.addWidget(reach_name_title_label, 1, 0)
        self.layout_ascii.addWidget(self.reach_name_label, 1, 1)
        self.layout_ascii.addWidget(units_name_title_label, 2, 0)
        self.layout_ascii.addWidget(self.units_name_label, 2, 1)
        self.layout_ascii.addWidget(l2, 3, 0)
        self.layout_ascii.addWidget(self.number_unit_label, 3, 1)
        self.layout_ascii.addWidget(l_selecttimestep, 4, 0)
        self.layout_ascii.addWidget(self.units_QListWidget, 4, 1, 1, 1)  # from row, from column, nb row, nb column
        self.layout_ascii.addWidget(epsgtitle_ascii_label, 5, 0)
        self.layout_ascii.addWidget(self.epsg_label, 5, 1)
        self.layout_ascii.addWidget(lh, 6, 0)
        self.layout_ascii.addWidget(self.hname, 6, 1)
        self.layout_ascii.addWidget(self.load_b, 6, 2)
        self.layout_ascii.addWidget(self.last_hydraulic_file_label, 7, 0)
        self.layout_ascii.addWidget(self.last_hydraulic_file_name_label, 7, 1)
        [self.layout_ascii.setRowMinimumHeight(i, 30) for i in range(self.layout_ascii.rowCount())]

        self.setLayout(self.layout_ascii)

    def show_dialog_ascii(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """
        # disconnect function for multiple file cases
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        # prepare the filter to show only useful files
        if len(self.extension[i]) <= 4:
            filter2 = "File ("
            for e in self.extension[i]:
                filter2 += '*' + e + ' '
            filter2 = filter2[:-1]
            filter2 += ')' + ";; All File (*.*)"
        else:
            filter2 = ''

        # get last path
        if self.read_attribute_xml(self.attributexml[0]) != self.path_prj and self.read_attribute_xml(
                self.attributexml[0]) != "no_data":
            model_path = self.read_attribute_xml(self.attributexml[0])  # path spe
        elif self.read_attribute_xml("Path_last_file_loaded") != self.path_prj:
            model_path = self.read_attribute_xml("Path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        # find the filename based on user choice
        filename_list = QFileDialog.getOpenFileNames(self,
                                                     self.tr("Select file(s)"),
                                                     model_path,
                                                     filter2)

        # init
        self.hydrau_case = "unknown"
        self.multi_hdf5 = False
        self.index_hydrau_presence = False

        # if file has been selected
        if filename_list[0]:
            # clean GUI
            self.clean_gui()

            # get_hydrau_description_from_source
            ascii_description, warning_list = hydro_input_file_mod.get_hydrau_description_from_source(
                filename_list[0],
                self.path_prj,
                self.model_type,
                self.nb_dim)
            # warnings
            if warning_list:
                for warn in warning_list:
                    self.send_log.emit(warn)

            # error
            if type(ascii_description) == str:
                self.clean_gui()
                self.send_log.emit(ascii_description)

            # one hdf5
            if type(ascii_description) == dict:
                # multi
                self.multi_hdf5 = False
                # save last path
                self.pathfile[0] = ascii_description["path_filename_source"]  # source file path
                self.namefile[0] = ascii_description["filename_source"]  # source file name
                self.name_hdf5 = ascii_description["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description = ascii_description
                # to GUI (decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems([self.hydrau_description["filename_source"]])
                # one reach
                if len(ascii_description["unit_list"]) == 1:
                    self.multi_reach = False
                    self.swith_qlabel_qcombobox_reach_name("qlabel")
                    self.reach_name_label.setText(self.hydrau_description["reach_list"][0])
                    self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                    self.units_QListWidget.clear()
                    self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"][0])
                    if not self.hydrau_description["unit_list_tf"]:
                        self.units_QListWidget.selectAll()
                    else:
                        for i in range(len(self.hydrau_description["unit_list_full"][0])):
                            self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][0][i])
                            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                    self.units_QListWidget.setEnabled(True)
                    self.epsg_label.setText(self.hydrau_description["epsg_code"])
                    self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                    if not ascii_description["sub"]:
                        self.load_b.setText("Create .hyd file")
                    if ascii_description["sub"]:
                        self.load_b.setText("Create .hab file")
                        new_hdf5_name = os.path.splitext(self.hydrau_description["hdf5_name"])[0] + ".hab"
                        self.hname.setText(new_hdf5_name)  # hdf5 name

                # multi reach  ==> change reach_name label by combobox
                if len(ascii_description["unit_list"]) > 1:
                    self.multi_reach = True
                    self.swith_qlabel_qcombobox_reach_name("qcombobox")
                    self.reach_name_label.addItems(self.hydrau_description["reach_list"])
                    self.reach_name_label.currentIndexChanged.connect(self.change_gui_when_combobox_reach_change)
                    self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                    self.units_QListWidget.clear()
                    self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"][0])
                    if not self.hydrau_description["unit_list_tf"]:
                        self.units_QListWidget.selectAll()
                    else:
                        for i in range(len(self.hydrau_description["unit_list_full"][0])):
                            self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][0][i])
                            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                    self.units_QListWidget.setEnabled(True)
                    self.epsg_label.setText(self.hydrau_description["epsg_code"])
                    self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                    if not ascii_description["sub"]:
                        self.load_b.setText("Create .hyd file")
                    if ascii_description["sub"]:
                        self.load_b.setText("Create .hab file")
                        new_hdf5_name = os.path.splitext(self.hydrau_description["hdf5_name"])[0] + ".hab"
                        self.hname.setText(new_hdf5_name)  # hdf5 name

                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

            # multi hdf5
            if type(ascii_description) == list:
                # multi
                self.multi_hdf5 = True
                # save last path
                self.pathfile[0] = ascii_description[0]["path_filename_source"]  # source file path
                self.namefile[0] = ascii_description[0]["filename_source"]  # source file name
                self.name_hdf5 = ascii_description[0]["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description_multiple = ascii_description
                self.hydrau_description = ascii_description[0]
                # get names
                names = [description["filename_source"] for description in self.hydrau_description_multiple]
                # to GUI (first decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems(names)
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"])
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"])):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_telemac_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.h2d_t2.currentIndexChanged.connect(self.change_gui_when_combobox_name_change)
                if not ascii_description["sub"]:
                    self.load_b.setText("Create " + str(len(ascii_description)) + " .hyd files")
                if ascii_description["sub"]:
                    self.load_b.setText("Create " + str(len(ascii_description)) + " .hab files")
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

    def swith_qlabel_qcombobox_reach_name(self, wish_widget):
        self.layout_ascii.removeWidget(self.reach_name_label)
        self.reach_name_label.setParent(None)
        if wish_widget == "qcombobox":
            self.reach_name_label = QComboBox()
        if wish_widget == "qlabel":
            self.reach_name_label = QLabel(self.tr('unknown'))
        self.layout_ascii.addWidget(self.reach_name_label, 1, 1)

    def change_gui_when_combobox_reach_change(self):
        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        # change GUI
        self.units_QListWidget.clear()
        self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"][self.reach_name_label.currentIndex()])
        # change selection items
        for i in range(len(self.hydrau_description["unit_list_full"][self.reach_name_label.currentIndex()])):
            self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][self.reach_name_label.currentIndex()][i])
            self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
        self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
        self.unit_counter()

    def clean_gui(self):
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        self.h2d_t2.clear()
        self.h2d_t2.addItems(["unknown file"])
        self.swith_qlabel_qcombobox_reach_name("qlabel")
        self.reach_name_label.setText("unknown")
        self.units_name_label.setText("unknown")  # kind of unit
        self.number_unit_label.setText("unknown")  # number units
        self.units_QListWidget.clear()
        self.units_QListWidget.setEnabled(True)
        self.epsg_label.setEnabled(True)
        self.hname.setText("")  # hdf5 name
        self.load_b.setText("Create .hyd file")

    def unit_counter(self):
        # count total number items (units)
        total = self.units_QListWidget.count()
        # count total number items selected
        selected = len(self.units_QListWidget.selectedItems())

        # refresh telemac dictonnary
        unit_list = []
        unit_list_full = []
        selected_list = []
        for i in range(total):
            unit_list_full.append(self.units_QListWidget.item(i).text())
            selected_list.append(self.units_QListWidget.item(i).isSelected())
            if self.units_QListWidget.item(i).isSelected():
                unit_list.append(self.units_QListWidget.item(i).text())

        # save multi
        if self.hydrau_case == '4.a' or self.hydrau_case == '4.b' or (
                self.hydrau_case == 'unknown' and self.multi_hdf5):
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list"] = unit_list
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_full"] = unit_list_full
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_list_tf"] = selected_list
            self.hydrau_description_multiple[self.h2d_t2.currentIndex()]["unit_number"] = str(selected)
        # save one
        else:
            if self.multi_reach:
                for reach_num in range(int(self.hydrau_description["reach_number"])):
                    for unit_num in range(int(self.hydrau_description["unit_number"])):
                        self.hydrau_description["unit_list_tf"][reach_num][unit_num] = selected_list[unit_num]
            else:
                self.hydrau_description["unit_list"] = [unit_list]
                self.hydrau_description["unit_list_full"] = [unit_list_full]
                self.hydrau_description["unit_list_tf"] = [selected_list]
                self.hydrau_description["unit_number"] = str(selected)

        # set text
        text = str(selected) + "/" + str(total)
        self.number_unit_label.setText(text)  # number units

    def load_ascii_gui(self):
        """
        The function which call the function which load ascii and
         save the name of files in the project file
        """
        # get timestep and epsg selected
        if self.multi_hdf5:
            for i in range(len(self.hydrau_description_multiple)):
                if not any(self.hydrau_description_multiple[i]["unit_list_tf"]):
                    self.send_log.emit("Error: No units selected for : " + self.hydrau_description_multiple[i][
                        "filename_source"] + "\n")
                    return
        if not self.multi_hdf5:
            selection = self.units_QListWidget.selectedItems()
            if not selection:
                self.send_log.emit("Error: No units selected. \n")
                return
            self.hydrau_description["epsg_code"] = self.epsg_label.text()

        # for error management and figures
        self.timer.start(100)

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)

        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()

        # check if extension is set by user (one hdf5 case)
        self.name_hdf5 = self.hname.text()
        if not self.multi_hdf5:
            if not os.path.splitext(self.name_hdf5)[1]:
                if self.hydrau_description["sub"]:
                    self.name_hdf5 = self.name_hdf5 + ".hab"
                else:
                    self.name_hdf5 = self.name_hdf5 + ".hyd"

        # check if extension is set by user (multi hdf5 case)
        if self.multi_hdf5:
            for hdf5_num in range(len(self.hydrau_description_multiple)):
                if not os.path.splitext(self.hydrau_description_multiple[hdf5_num]["hdf5_name"])[1]:
                    if self.hydrau_description_multiple[hdf5_num]["sub"]:
                        self.hydrau_description_multiple[hdf5_num]["hdf5_name"] = self.hydrau_description_multiple[hdf5_num]["hdf5_name"] + ".sub"
                    else:
                        self.hydrau_description_multiple[hdf5_num]["hdf5_name"] = self.hydrau_description_multiple[hdf5_num]["hdf5_name"] + ".hyd"

        # get minimum water height as we might neglect very low water height
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

        # block button
        self.load_b.setDisabled(True)  # hydraulic

        # write the new file name in the project file
        self.save_xml(0)

        # path input
        path_input = self.find_path_input()

        # load the ascii data
        self.q = Queue()
        self.progress_value = Value("i", 0)
        # check ascii cases
        if self.hydrau_case == '4.a' or self.hydrau_case == '4.b' or (
                self.hydrau_case == 'unknown' and self.multi_hdf5):
            # refresh units selection
            self.p = Process(target=ascii_mod.load_ascii_and_cut_grid,
                             args=(self.hydrau_description_multiple,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences,
                                   user_preferences.user_preferences_temp_path))
        else:
            self.hydrau_description["hdf5_name"] = self.name_hdf5
            self.p = Process(target=ascii_mod.load_ascii_and_cut_grid,
                             args=(self.hydrau_description,
                                   self.progress_value,
                                   self.q,
                                   False,
                                   self.project_preferences,
                                   user_preferences.user_preferences_temp_path))
        self.p.name = "ASCII data loading"
        self.p.start()

        # copy input files
        nb_files = len(self.namefile[0].split(", "))
        files_list = self.namefile[0].split(", ")
        path_file_list = [self.pathfile[0]] * nb_files
        if nb_files > 1:
            self.p2 = Process(target=hdf5_mod.copy_files, args=(files_list, path_file_list, path_input))
            self.p2.start()
        if nb_files == 1:
            self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
            self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: ASCII data...'))
        self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit(
            "py    selafin_habby1.load_telemac_and_cut_grid('hydro_telemac_log', file1, path1, name_prj, "
            "path_prj, 'ASCII', 2, path_prj, [], True )\n")
        self.send_log.emit("restart ASCII")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))


class LAMMI(SubHydroW):
    """
    The class LAMMI is there to manage the link between the graphical interface and the functions in src/lammi_mod.py
    which loads the lammi data. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW().
    """

    drop_merge = pyqtSignal()
    """
    A pyqtsignal which signal that hydro data from lammi is ready. The signal is for the bioinfo_tab and is collected
    by MainWindows1.py. Data from lammi contains substrate data.
    """

    def __init__(self, path_prj, name_prj):

        super(LAMMI, self).__init__(path_prj, name_prj)

        self.namefile = ['unknown file', 'unknown file', 'unknown file', 'unknown file']
        # the third path is the directory when the output files are found. Only useful, if the output files were moved
        self.pathfile = ['.', '.', '.', 'Directory from transect.txt']
        self.file_entree = ['Facies.txt', 'Transect.txt']
        self.attributexml = ['lammi_facies', 'lammi_transect', 'lammi_output']
        self.model_type = 'LAMMI'
        self.data_type = "HYDRAULIC"
        self.extension = [['.txt'], ['.txt']]
        self.nb_dim = 1.5
        self.init_iu()

    def init_iu(self):
        """
        Used by __init__() during the initialization.
        """

        # if there is the project file with lammi info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)
        self.was_model_loaded_before(2)

        # geometry and output data
        l1 = QLabel(self.tr('<b> General data </b>'))
        self.h2d_t2 = QLabel(self.namefile[0] + ', ' + self.namefile[1], self)
        self.h2d_b = QPushButton(self.tr("Select the 'Entree' directory"), self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog_lammi(0))
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setText(self.namefile[0] + ', ' + self.namefile[1]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.dirlab = QLabel(self.pathfile[2])
        self.dirbut = QPushButton(self.tr("Select the 'SimHydro' directory"))
        self.dirbut.clicked.connect(lambda: self.show_dialog_lammi(1))
        self.dirbut.clicked.connect(lambda: self.dirlab.setText(self.pathfile[2]))

        # show the directory as tooltip
        self.h2d_t2.setToolTip(self.pathfile[0])
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setToolTip(self.pathfile[0]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr("Only 'Interpolation by Block' possible for LAMMI data. Substrate data is included."))

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hab file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_lammi_gui)
        self.spacer = QSpacerItem(1, 150)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 1, 0)
        self.layout_hec2.addWidget(self.h2d_t2, 1, 1)
        self.layout_hec2.addWidget(self.h2d_b, 1, 2)
        self.layout_hec2.addWidget(l2, 2, 0)
        self.layout_hec2.addWidget(self.dirlab, 2, 1)
        self.layout_hec2.addWidget(self.dirbut, 2, 2)
        self.layout_hec2.addWidget(l2D1, 3, 0)
        self.layout_hec2.addWidget(l2D2, 3, 1, 1, 2)
        self.layout_hec2.addWidget(lh, 4, 0)
        self.layout_hec2.addWidget(self.hname, 4, 1)
        self.layout_hec2.addWidget(self.load_b, 5, 2)
        self.layout_hec2.addWidget(self.butfig, 6, 2)
        # self.layout_ascii.addItem(self.spacer, 7, 1)
        self.setLayout(self.layout_hec2)

    def show_dialog_lammi(self, i=0):
        """
        When using lammi data, the user selects a directory and not a file. Hence, we need to modify the ususal
        show_dialog function. Hence, function the show_dilaog_lammi() obtain the directory chosen by the user.
        This method open a dialog so that the user select a directory. The files are NOT loaded here. The name and path
        to the files are saved in an attribute.

        :param i: If i ==0, we obtain the Entree dirctory, if i == 1, the Resu directory.
        """

        # get the directory
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        if dir_name == '':  # cancel case
            self.send_log.emit("Warning: No selected directory for lammi\n")
            return

        # get the files if entree
        if i == 0:
            for f in range(0, 2):
                filename = self.file_entree[f]
                # check files
                if os.path.isfile(os.path.join(dir_name, filename)):
                    pass
                else:
                    self.send_log.emit("Error: Transect.txt or Facies.txt was not found in the selected directory.\n")
                    return
                # keep the name in an attribute until we save it
                self.pathfile[f] = dir_name
                self.namefile[f] = filename

            # add the default name of the hdf5 file to the QLineEdit
            self.name_hdf5 = 'Merge_' + self.model_type
            self.hname.setText(self.name_hdf5)

        if i == 1:
            # test if there is at least one output file in the proposed output directory
            filenames = hdf5_mod.get_all_filename(dir_name, '.prn')
            if len(filenames) > 0:
                self.pathfile[2] = dir_name
                self.namefile[2] = os.path.basename(filenames[0])
            else:
                self.send_log.emit("Error: No output (.prn) file found in the selected directory.\n")
                return


        else:
            return

    def load_lammi_gui(self):
        """
        This function loads the lammi data, save the text file to the xml project file and create the grid
        """
        # test the availability of files
        fileNOK = True
        f0 = os.path.join(self.pathfile[0], self.namefile[0])
        f1 = os.path.join(self.pathfile[1], self.namefile[1])
        f2 = os.path.join(self.pathfile[2], self.namefile[2])
        if os.path.isfile(f0) & os.path.isfile(f1) & os.path.isfile(f2):
            fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("LAMMI"))
            self.msg2.setText(self.tr("Unable to load LAMMI data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # for error management and figures
        self.timer.start(100)

        # write the new file name in the project file
        self.save_xml(0)
        self.save_xml(1)
        self.save_xml(2)

        # disable while loading
        self.load_b.setDisabled(True)

        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()
        # get the image and load option
        path_im = self.find_path_im()
        self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
        show_all_fig = True
        if not os.path.isdir(self.pathfile[2]):
            self.pathfile[2] = []

        # load the lammi data
        self.q = Queue()
        self.p = Process(target=lammi_mod.open_lammi_and_create_grid,
                         args=(self.pathfile[0], self.pathfile[1], path_im, self.name_hdf5, self.name_prj, self.path_prj
                               , path_hdf5, self.pathfile[2], self.project_preferences, show_all_fig, self.namefile[1],
                               self.namefile[0], False, self.q, 1, self.model_type))
        self.p.start()

        # path input
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: LAMMI data...'))
        self.send_err_log()
        self.send_log.emit("py    dir1=r'" + self.pathfile[0] + "'")
        self.send_log.emit("py    dir2=r'" + self.pathfile[1] + "'")
        self.send_log.emit("py    dir3=r'" + self.pathfile[2] + "'")
        self.send_log.emit("py    lammi.open_lammi_and_create_grid(dir1, dir2, path_prj, 'lammi_hdf5', "
                           "name_prj, path_prj, path_prj, dir3, [], False, 'Transect.txt', 'Facies.txt', True)\n")
        self.send_log.emit("restart LOAD_LAMMI")
        self.send_log.emit("restart    dir1: " + self.pathfile[0])
        self.send_log.emit("restart    dir3: " + self.pathfile[2])


class SW2D(SubHydroW):
    """
    The class SW2D is there to manage the link between the graphical interface and the functions in src/read_sw2f.py
    which loads the SW2D data . It inherits from SubHydroW() so it have all the methods and the variables from
    the class SubHydroW().
    """

    def __init__(self, path_prj, name_prj):

        super(SW2D, self).__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        used by ___init__() in the initialization.
        """

        # update attibute for rubar 2d
        self.attributexml = ['sw2d_geodata', 'sw2d_result']
        self.model_type = 'SW2D'
        self.extension = [['.geo'], ['.res']]  # list of list in case there is more than one possible ext.
        self.data_type = "HYDRAULIC"
        self.nb_dim = 2

        # if there is the project file with sw2d geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)

        # create and update label with the result and geo filename
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)
        self.geo_t2.setToolTip(self.pathfile[0])
        self.out_t2.setToolTip(self.pathfile[1])

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton(self.tr('Choose file (.geo)'), self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton(self.tr('Choose file \n (.res)'), self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[1]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_sw2d)
        self.spacer = QSpacerItem(1, 200)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2, 0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(l2D1, 2, 0)
        self.layout_hec.addWidget(l2D2, 2, 1, 1, 2)
        self.layout_hec.addWidget(lh, 3, 0)
        self.layout_hec.addWidget(self.hname, 3, 1)
        self.layout_hec.addWidget(self.load_b, 3, 2)
        self.layout_hec.addWidget(self.butfig, 4, 2)
        # self.layout_hec.addItem(self.spacer, 5, 1)
        self.setLayout(self.layout_hec)

    def show_dialog_sw2d(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: an int for the case where there is more than one file to load
        """
        # disconnect function for multiple file cases
        try:
            self.h2d_t2.disconnect()
        except:
            pass

        try:
            self.units_QListWidget.disconnect()
        except:
            pass

        # prepare the filter to show only useful files
        if len(self.extension[i]) <= 4:
            filter2 = "File ("
            for e in self.extension[i]:
                filter2 += '*' + e + ' '
            filter2 = filter2[:-1]
            filter2 += ')' + ";; All File (*.*)"
        else:
            filter2 = ''

        # get last path
        if self.read_attribute_xml(self.attributexml[0]) != self.path_prj and self.read_attribute_xml(
                self.attributexml[0]) != "no_data":
            model_path = self.read_attribute_xml(self.attributexml[0])  # path spe
        elif self.read_attribute_xml("Path_last_file_loaded") != self.path_prj:
            model_path = self.read_attribute_xml("Path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        # find the filename based on user choice
        filename_list = QFileDialog.getOpenFileNames(self,
                                                     self.tr("Select file(s)"),
                                                     model_path,
                                                     filter2)

        # init
        self.hydrau_case = "unknown"
        self.multi_hdf5 = False
        self.index_hydrau_presence = False

        # if file has been selected
        if filename_list[0]:
            # clean GUI
            self.clean_gui()

            # get_hydrau_description_from_source
            telemac_description, warning_list = hydro_input_file_mod.get_hydrau_description_from_source(filename_list[0],
                                                                                                        self.path_prj,
                                                                                                        self.model_type,
                                                                                                        self.nb_dim)

            # warnings
            if warning_list:
                for warn in warning_list:
                    self.send_log.emit(warn)

            # error
            if type(telemac_description) == str:
                self.clean_gui()
                self.send_log.emit(telemac_description)

            # one hdf5
            if type(telemac_description) == dict:
                self.hydrau_case = telemac_description["hydrau_case"]
                # multi
                self.multi_hdf5 = False
                # save last path
                self.pathfile[0] = telemac_description["path_filename_source"]  # source file path
                self.namefile[0] = telemac_description["filename_source"]  # source file name
                self.name_hdf5 = telemac_description["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description = telemac_description
                # to GUI (decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems([self.hydrau_description["filename_source"]])
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"])
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"])):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.load_b.setText("Create .hyd file")
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

            # multi hdf5
            if type(telemac_description) == list:
                self.hydrau_case = telemac_description[0]["hydrau_case"]
                # multi
                self.multi_hdf5 = True
                # save last path
                self.pathfile[0] = telemac_description[0]["path_filename_source"]  # source file path
                self.namefile[0] = telemac_description[0]["filename_source"]  # source file name
                self.name_hdf5 = telemac_description[0]["hdf5_name"]
                self.save_xml(0)  # path in xml
                # set to attribute
                self.hydrau_description_multiple = telemac_description
                self.hydrau_description = telemac_description[0]
                # get names
                names = [description["filename_source"] for description in self.hydrau_description_multiple]
                # to GUI (first decription)
                self.h2d_t2.clear()
                self.h2d_t2.addItems(names)
                self.reach_name_label.setText(self.hydrau_description["reach_list"])
                self.units_name_label.setText(self.hydrau_description["unit_type"])  # kind of unit
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(self.hydrau_description["unit_list_full"])
                if not self.hydrau_description["unit_list_tf"]:
                    self.units_QListWidget.selectAll()
                else:
                    for i in range(len(self.hydrau_description["unit_list_full"])):
                        self.units_QListWidget.item(i).setSelected(self.hydrau_description["unit_list_tf"][i])
                        self.units_QListWidget.item(i).setTextAlignment(Qt.AlignLeft)
                self.units_QListWidget.setEnabled(True)
                self.epsg_label.setText(self.hydrau_description["epsg_code"])
                self.hname.setText(self.hydrau_description["hdf5_name"])  # hdf5 name
                self.h2d_t2.currentIndexChanged.connect(self.change_gui_when_combobox_name_change)
                self.load_b.setText("Create " + str(len(telemac_description)) + " .hyd files")
                self.units_QListWidget.itemSelectionChanged.connect(self.unit_counter)
                self.unit_counter()

    def load_sw2d(self):
        """
        A function to execture the loading and saving the sw2d files using read_sw2d.py.

        A second thread is used to avoid "freezing" the GUI.
        """
        # for error management and figures
        self.timer.start(100)

        # test the availability of files
        fileNOK = True
        f0 = os.path.join(self.pathfile[0], self.namefile[0])
        f1 = os.path.join(self.pathfile[1], self.namefile[1])
        if os.path.isfile(f0) & os.path.isfile(f1):
            fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("SW2D"))
            self.msg2.setText(self.tr("Unable to load SW2D data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)

        # disable while loading
        self.load_b.setDisabled(True)

        # the path where to save the image
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # load sw2d, interpolate to node, create grid and save in hdf5 format
        self.q = Queue()
        # to be changed
        self.progress_value = Value("i", 0)
        self.p = Process(target=sw2d_mod.load_sw2d_and_modify_grid, args=(self.name_hdf5, self.namefile[0],
                                                                          self.namefile[1], self.pathfile[0],
                                                                          self.pathfile[1], path_im, self.name_prj,
                                                                          self.path_prj,
                                                                          self.model_type, self.nb_dim, path_hdf5,
                                                                          self.q,
                                                                          False, self.project_preferences,
                                                                          self.progress_value))
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: SW2D data...'))
        # self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    file2=r'" + self.namefile[1] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    path2=r'" + path_input + "'")
        # to be changed
        self.send_log.emit(
            "py    read_sw2d.myfunc('Hydro_sw2d_log',file1, file2, path1, path2,"
            " path_prj, name_prj, path_prj, 'SW2D', 2, path_prj, [])\n")
        self.send_log.emit("restart LOAD_SW2D")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(path_input, self.namefile[1]))

    def propose_next_file(self):
        """
        This function proposes the second SW2D file when the first is selected.  Indeed, to load SW2D, we need
        one file with the geometry data and one file with the simulation results. If the user selects a file, this
        function looks if a file with the same name but with the extension of the other file type exists in the
        selected folder.
        """
        if len(self.extension[1]) == 1:
            if self.out_t2.text() == 'unknown file':
                blob = self.namefile[0]
                new_name = blob[:-len(self.extension[0][0])] + self.extension[1][0]
                pathfilename = os.path.join(self.pathfile[0], new_name)
                if os.path.isfile(pathfilename):
                    self.out_t2.setText(new_name)
                    # keep the name in an attribute until we save it
                    self.pathfile[1] = self.pathfile[0]
                    self.namefile[1] = new_name


class IBER2D(SubHydroW):
    """
    The class IBER2D is there to manage the link between the graphical
    interface and the functions in src/read_iber2d.py
    which loads the IBER2D data . It inherits from SubHydroW() so it have all
    the methods and the variables from the class SubHydroW().
    """

    def __init__(self, path_prj, name_prj):

        super(IBER2D, self).__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        used by ___init__() in the initialization.
        """

        # update attibute for iber2d
        self.attributexml = ['iber2d_geodata', 'iber2d_result1',
                             'iber2d_result2', 'iber2d_result3',
                             'iber2d_result4']
        self.model_type = 'IBER2D'
        self.data_type = "HYDRAULIC"
        # list of list in case there is more than one possible ext.
        self.extension = ['.dat', '.rep', '.rep', '.rep', '.rep']
        self.nb_dim = 2

        # if there is the project file with iber2d geo info,
        # update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)

        # create and update label with the result and geo filename
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)
        self.out_t2bis = QLabel(self.namefile[1], self)
        self.out_t2ter = QLabel(self.namefile[1], self)
        self.out_t2qua = QLabel(self.namefile[1], self)
        self.geo_t2.setToolTip(self.pathfile[0])
        self.out_t2.setToolTip(self.pathfile[1])
        self.out_t2bis.setToolTip(self.pathfile[1])
        self.out_t2ter.setToolTip(self.pathfile[1])
        self.out_t2qua.setToolTip(self.pathfile[1])

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton(self.tr('Choose file (.dat)'), self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton(self.tr('Choose file for h\n (.rep)'), self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[1]))
        l3 = QLabel(self.tr('<b> Output data </b>'))
        self.outbis_b = QPushButton(self.tr('Choose file for u\n (.rep)'), self)
        self.outbis_b.clicked.connect(lambda: self.show_dialog(2))
        self.outbis_b.clicked.connect(lambda: self.out_t2bis.setText(self.namefile[2]))
        self.outbis_b.clicked.connect(lambda: self.out_t2bis.setToolTip(self.pathfile[1]))
        l4 = QLabel(self.tr('<b> Output data </b>'))
        self.outter_b = QPushButton(self.tr('Choose file for v\n (.rep)'), self)
        self.outter_b.clicked.connect(lambda: self.show_dialog(3))
        self.outter_b.clicked.connect(lambda: self.out_t2ter.setText(self.namefile[3]))
        self.outter_b.clicked.connect(lambda: self.out_t2ter.setToolTip(self.pathfile[1]))
        l5 = QLabel(self.tr('<b> Output data </b>'))
        self.outqua_b = QPushButton(self.tr('Choose file for xyz\n (.rep)'), self)
        self.outqua_b.clicked.connect(lambda: self.show_dialog(4))
        self.outqua_b.clicked.connect(lambda: self.out_t2qua.setText(self.namefile[4]))
        self.outqua_b.clicked.connect(lambda: self.out_t2qua.setToolTip(self.pathfile[1]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('.hyd file name'))
        self.hname = QLineEdit(self.name_hdf5)
        self.hname.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton(self.tr('Create .hyd file'), self)
        self.load_b.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b.clicked.connect(self.load_iber2d)
        self.spacer = QSpacerItem(1, 200)
        self.butfig = QPushButton(self.tr("create figure"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2, 0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(l3, 2, 0)
        self.layout_hec.addWidget(self.out_t2bis, 2, 1)
        self.layout_hec.addWidget(self.outbis_b, 2, 2)
        self.layout_hec.addWidget(l4, 3, 0)
        self.layout_hec.addWidget(self.out_t2ter, 3, 1)
        self.layout_hec.addWidget(self.outter_b, 3, 2)
        self.layout_hec.addWidget(l5, 4, 0)
        self.layout_hec.addWidget(self.out_t2qua, 4, 1)
        self.layout_hec.addWidget(self.outqua_b, 4, 2)
        self.layout_hec.addWidget(l2D1, 5, 0)
        self.layout_hec.addWidget(l2D2, 5, 1, 1, 2)
        self.layout_hec.addWidget(lh, 6, 0)
        self.layout_hec.addWidget(self.hname, 6, 1)
        self.layout_hec.addWidget(self.load_b, 6, 2)
        self.layout_hec.addWidget(self.butfig, 7, 2)
        # self.layout_hec.addItem(self.spacer, 8, 1)
        self.setLayout(self.layout_hec)

    def load_iber2d(self):
        """
        A function to execute the loading and saving the iber2d files
        using read_iber2d.py.

        A second thread is used to avoid "freezing" the GUI.
        """
        # for error management and figures
        self.timer.start(100)

        # test the availability of files
        fileNOK = True
        if len(self.namefile) == 5:
            f0 = os.path.join(self.pathfile[0], self.namefile[0])
            f1 = os.path.join(self.pathfile[1], self.namefile[1])
            f2 = os.path.join(self.pathfile[1], self.namefile[2])
            f3 = os.path.join(self.pathfile[1], self.namefile[3])
            f4 = os.path.join(self.pathfile[1], self.namefile[4])
            if os.path.isfile(f0) & os.path.isfile(f1) & os.path.isfile(f2) \
                    & os.path.isfile(f3) & os.path.isfile(f4):
                fileNOK = False
        if fileNOK:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("IBER2D"))
            self.msg2.setText(self.tr("Unable to load IBER2D data files!"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.p = Process(target=None)
            self.p.start()
            self.q = Queue()
            return

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        self.save_xml(2)
        self.save_xml(3)
        self.save_xml(4)

        # disable while loading
        self.load_b.setDisabled(True)

        # the path where to save the image
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # load iber2d, interpolate to node, create grid and save in hdf5 format
        self.q = Queue()
        # to be changed

        self.p = Process(target=iber2d_mod.load_iber2d_and_modify_grid,
                         args=(self.name_hdf5, self.namefile[0],
                               self.namefile[1], self.namefile[2],
                               self.namefile[3], self.namefile[4],
                               self.pathfile[0], self.pathfile[1],
                               path_im, self.name_prj,
                               self.path_prj, self.model_type, self.nb_dim,
                               path_hdf5, self.q, False, self.project_preferences))
        self.p.name = "Iber 2D data loading"
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=hdf5_mod.copy_files,
                          args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: IBER2D data...'))
        # self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    file2=r'" + self.namefile[1] + "'")
        self.send_log.emit("py    file3=r'" + self.namefile[2] + "'")
        self.send_log.emit("py    file4=r'" + self.namefile[3] + "'")
        self.send_log.emit("py    file5=r'" + self.namefile[4] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    path2=r'" + path_input + "'")
        # to be changed
        self.send_log.emit(
            "py    read_iber2d.myfunc('Hydro_iber2d_log', file1, file2, \
                                      file3, file4, file5, path1,\
                                      path2,"
            " path_prj, name_prj, path_prj, 'IBER2D', 2, path_prj, [])\n")
        self.send_log.emit("restart LOAD_IBER2D")
        self.send_log.emit("restart    file1: "
                           + os.path.join(path_input, self.namefile[0]))
        self.send_log.emit("restart    file2: "
                           + os.path.join(path_input, self.namefile[1]))
        self.send_log.emit("restart    file3: "
                           + os.path.join(path_input, self.namefile[2]))
        self.send_log.emit("restart    file4: "
                           + os.path.join(path_input, self.namefile[3]))
        self.send_log.emit("restart    file5: "
                           + os.path.join(path_input, self.namefile[4]))

    def propose_next_file(self):
        """
        This function proposes the second IBER2D file when the first is
        selected. Indeed, to load IBER2D, we need
        one file with the geometry data and one file with
        the simulation results. If the user selects a file, this
        function looks if a file with the same name but with the extension
        of the other file type exists in the selected folder.
        """
        if len(self.extension[1]) == 1:
            if self.out_t2.text() == 'unknown file':
                blob = self.namefile[0]
                new_name = \
                    blob[:-len(self.extension[0][0])] + self.extension[1][0]
                pathfilename = os.path.join(self.pathfile[0], new_name)
                if os.path.isfile(pathfilename):
                    self.out_t2.setText(new_name)
                    # keep the name in an attribute until we save it
                    self.pathfile[1] = self.pathfile[0]
                    self.namefile[1] = new_name


class HabbyHdf5(SubHydroW):
    """
    This class is used to load hdf5 hydrological file done by HABBY on another project. If the project was lost,
    it is there possible to just add a along hdf5 file to the current project without having to pass to the original
    hydrological files.
    """

    drop_merge = pyqtSignal()
    """
    A pyqtsignal which signal that new merge data is ready as it also possible to import merge data here.
    """

    def __init__(self, path_prj, name_prj):

        super(HabbyHdf5, self).__init__(path_prj, name_prj)
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.model_type = 'Imported_hydro'
        self.data_type = "HYDRAULIC"
        self.new_name = 'no name'  # the name of the new hdf5 file
        self.ismerge = False
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        l0 = QLabel(self.tr('Select the hdf5 created by HABBY to be loaded:'))
        self.button2 = QPushButton(self.tr('Load hydraulic data from hdf5'))
        self.button2.clicked.connect(self.get_new_hydro_hdf5)
        self.button3 = QPushButton(self.tr('Load merge data from hdf5'))
        self.button3.clicked.connect(self.get_new_merge_hdf5)
        self.button4 = QPushButton(self.tr('Merge two hdf5 hydraulic files together'))
        self.button4.clicked.connect(lambda: self.add_two_hdf5(False))
        self.button5 = QPushButton(self.tr('Merge two hdf5 merge files together'))
        self.button5.clicked.connect(lambda: self.add_two_hdf5(True))
        self.butfig = QPushButton(self.tr("Create figure"))
        self.butfig.clicked.connect(self.recreate_image)

        spacer1 = QSpacerItem(250, 1)
        spacer2 = QSpacerItem(1, 70)

        self.layout2 = QGridLayout()
        self.layout2.addWidget(l0, 0, 0)
        self.layout2.addWidget(self.button2, 0, 1)
        self.layout2.addWidget(self.button3, 1, 1)
        self.layout2.addWidget(self.button4, 3, 1)
        self.layout2.addWidget(self.button5, 4, 1)
        self.layout2.addWidget(self.butfig, 6, 1)
        self.layout2.addItem(spacer1, 0, 2)
        self.layout2.addItem(spacer2, 2, 0)
        self.layout2.addItem(spacer2, 5, 0)
        self.layout2.addItem(spacer2, 7, 0)
        self.setLayout(self.layout2)

    def get_new_hydro_hdf5(self):
        """
        This is a function which allows the user to select an hdf5 file containing the hydrological
        data from a previous project and add it to the current project. It modifies the xml project file and test
        that the data is in correct form by loading it. The hdf5 should have the same form than the hydrological data
        created by HABBY in the method save_hdf5 of the class SubHydroW.
        """

        self.send_log.emit(self.tr('# Loading: HABBY hdf5 file (hydraulic data only)...'))

        # prep
        ikle_all_t = []
        point_all = []
        inter_vel_all = []
        inter_height_all = []
        self.ismerge = False

        # select a file
        path_hdf5 = self.find_path_hdf5()
        fname_h5 = QFileDialog.getOpenFileName(self, 'QFileDialog.getOpenFileName()', path_hdf5, '*.hyd', '*.hyd')[0]
        if fname_h5 != '':  # cancel
            blob, ext = os.path.splitext(fname_h5)
        else:
            self.send_log.emit('Warning: No file selected.\n')
            return
        # load the data to check integrity
        [ikle_all_t, point_all, inter_vel_all, inter_height_all] = hdf5_mod.load_hdf5_hyd_and_merge(fname_h5, path_hdf5)

        # copy the file and update the attribute
        path_input = self.find_path_input()
        if os.path.isdir(path_hdf5):
            self.new_name = 'COPY_' + os.path.basename(fname_h5)
            pathnewname = os.path.join(path_hdf5, self.new_name)
            shutil.copyfile(fname_h5, pathnewname)
            # necessary for the restart function
            pathnewname2 = os.path.join(path_input, self.new_name)
            shutil.copyfile(fname_h5, pathnewname2)
        else:
            self.send_log.emit('Error: the path to the project is not found. Is the project saved in the general tab?')
            return
        try:
            file_hydro2 = h5py.File(pathnewname, 'r+')
        except OSError:
            self.send_log.emit('Error: The hdf5 file could not be loaded. \n')
            return
        file_hydro2.attrs['path_project'] = self.path_prj
        file_hydro2.attrs['name_project'] = self.name_prj

        self.add_new_hdf5_to_xml()

        self.send_log.emit('# hdf5 file loaded to the current project.')
        self.send_log.emit("py    import shutil")
        self.send_log.emit("py    fname_h5 ='" + fname_h5 + "'")
        self.send_log.emit("py    new_name = os.path.join(path_prj, 'COPY_' + os.path.basename(fname_h5))")
        self.send_log.emit("py    shutil.copyfile(fname_h5, new_name)")
        self.send_log.emit('restart LOAD_HYDRO_HDF5')
        self.send_log.emit('restart    file hdf5: ' + pathnewname2)
        self.drop_hydro.emit()

    def get_new_merge_hdf5(self):
        """
        This is a function which allows the user to select an hdf5 file containing the hydrological and the substrate
        data from a previous project and add it to the current project. It modifies the xml project file and test
        that the data is in correct form by loading it. The hdf5 should have the same form than the merge data
        created by HABBY in the method save_hdf5 of the class SubHydroW.
        """

        self.send_log.emit(self.tr('# Loading: HABBY hdf5 file (hydraulic and substrate data)...'))

        # prep
        self.ismerge = True

        # select a file
        path_hdf5 = self.find_path_hdf5()
        fname_h5 = QFileDialog.getOpenFileName(self, 'QFileDialog.getOpenFileName()', path_hdf5, '*.hab', '*.hab')[0]
        if fname_h5 != '':  # cancel
            blob, ext = os.path.splitext(fname_h5)
        else:
            self.send_log.emit('Warning: No file selected.\n')
            return
        # load the data to check integrity
        [ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom] \
            = hdf5_mod.load_hdf5_hyd_and_merge(fname_h5, path_hdf5, merge=True)

        # copy the file and update the attribute
        path_hdf5 = self.find_path_hdf5()
        path_input = self.find_path_input()
        if os.path.isdir(path_hdf5):
            self.new_name = 'COPY_' + os.path.basename(fname_h5)
            pathnewname = os.path.join(path_hdf5, self.new_name)
            shutil.copyfile(fname_h5, pathnewname)
            # necessary for the restart function
            pathnewname2 = os.path.join(path_input, self.new_name)
            shutil.copyfile(fname_h5, pathnewname2)
        else:
            self.send_log.emit('Error: the path to the project is not found. Is the project saved in the general tab?')
            return
        try:
            file_hydro2 = h5py.File(pathnewname, 'r+')
        except OSError:
            self.send_log.emit('Error: The hdf5 file could not be loaded. \n')
            return
        file_hydro2.attrs['path_project'] = self.path_prj
        file_hydro2.attrs['name_project'] = self.name_prj

        self.add_new_hdf5_to_xml()

        self.send_log.emit('# hdf5 file loaded to the current project.')
        self.send_log.emit("py    import shutil")
        self.send_log.emit("py    fname_h5 ='" + fname_h5 + "'")
        self.send_log.emit("py    new_name = os.path.join(path_prj, 'COPY_' + os.path.basename(fname_h5))")
        self.send_log.emit("py    shutil.copyfile(fname_h5, new_name)")
        self.send_log.emit('restart LOAD_HYDRO_HDF5')
        self.send_log.emit('restart    file hdf5: ' + pathnewname2)
        self.drop_merge.emit()

    def add_new_hdf5_to_xml(self):
        """
        This function is used to add the new hdf5 to the xml project file
        """
        if self.new_name == 'no name':
            return

        # save the new file name in the xml file of the project
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isfile(filename_prj):
            self.send_log.emit('Error: No project saved. Please create a project first in the General tab.\n')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            # new xml category in case the hydrological model is not supported by HABBY
            # as long s loded in the right format, it would not be a problem
            child = root.find(".//Imported_hydro")
            if child is None:
                here_element = ET.SubElement(root, "Imported_hydro")
                if self.ismerge:
                    hdf5file = ET.SubElement(here_element, "hdf5_mergedata")
                else:
                    hdf5file = ET.SubElement(here_element, "hdf5_hydrodata")
                hdf5file.text = self.new_name
            else:
                if self.ismerge:
                    hdf5file = ET.SubElement(child, "hdf5_mergedata")
                else:
                    hdf5file = ET.SubElement(child, "hdf5_hydrodata")
                hdf5file.text = self.new_name

            doc.write(filename_prj)

    def add_two_hdf5(self, merge):
        """
        This functions is used to merge together two hydro/merge hdf5. For this, it call the function 'addition_hdf5'
        from hdf5_mod.py

        :param merge: A boolean which say if we load an hydrological or a merge file
        """

        self.send_log.emit(self.tr('# Loading: Join two HABBY hdf5 file together ...'))
        self.ismerge = merge
        path_hdf5 = self.find_path_hdf5()

        if merge:
            # select the first file
            fname_h5 = QFileDialog.getOpenFileName(self,
                                                   'QFileDialog.getOpenFileName()',
                                                   path_hdf5,
                                                   '*.hab',
                                                   '*.hab')[0]
        if not merge:
            # select the first file
            fname_h5 = QFileDialog.getOpenFileName(self,
                                                   'QFileDialog.getOpenFileName()',
                                                   path_hdf5,
                                                   '*.hyd',
                                                   '*.hyd')[0]
        if fname_h5 != '':  # cancel
            hdf51 = os.path.basename(fname_h5)
            path1 = os.path.dirname(fname_h5)
        else:
            self.send_log.emit('Warning: No file selected.\n')
            return

        self.msg2.setIcon(QMessageBox.Information)
        self.msg2.setWindowTitle(self.tr("Select second file"))
        self.msg2.setText(self.tr("The first file was selected. Now select the second file."))
        self.msg2.setStandardButtons(QMessageBox.Ok)
        self.msg2.show()

        if self.msg2.exec() == QMessageBox.Ok:
            # select the second file
            if merge:
                fname_h5 = \
                    QFileDialog.getOpenFileName(self,
                                                'QFileDialog.getOpenFileName()',
                                                path_hdf5,
                                                '*.hab',
                                                '*.hab')[0]
            if not merge:
                fname_h5 = QFileDialog.getOpenFileName(self,
                                                       'QFileDialog.getOpenFileName()',
                                                       path_hdf5,
                                                       '*.hyd',
                                                       '*.hyd')[0]
            if fname_h5 != '':  # cancel
                hdf52 = os.path.basename(fname_h5)
                path2 = os.path.dirname(fname_h5)
            else:
                self.send_log.emit('Warning: No second file selected.\n')
                return

            # join the two files
            self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
            if self.project_preferences['erase_id']:
                erase_id = True
            else:
                erase_id = False

            hdf5_mod.addition_hdf5(path1, hdf51, path2, hdf52, self.name_prj, self.path_prj, self.model_type,
                                   path_hdf5, merge=self.ismerge, erase_id=erase_id)
            self.add_new_hdf5_to_xml()

            self.send_log.emit('Two hdf5 file added together')

            if self.ismerge:
                self.drop_merge.emit()
            else:
                self.drop_hydro.emit()


class SubstrateW(SubHydroW):
    """
    This is the widget used to load the substrate. It is practical to re-use some of the method from SubHydroW.
    So this class inherit from SubHydroW.
    """
    drop_merge = pyqtSignal()
    """
    A pyqtsignal which signal that merged hydro data is ready. The signal is for the bioinfo_tab and is collected
    by MainWindows1.py.
    """

    def __init__(self, path_prj, name_prj):
        super(SubstrateW, self).__init__(path_prj, name_prj)
        # update attribute
        self.tab_name = "substrate"
        self.attributexml = ['substrate_path', 'att_name']
        self.model_type = 'SUBSTRATE'
        self.data_type = "SUBSTRATE"
        self.name_att = ''
        self.coord_p = []
        self.ikle_sub = []
        self.sub_info = []
        self.hyd_name = []
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
        self.rb0 = QRadioButton(self.tr('polygons (.shp)'))
        self.rb1 = QRadioButton(self.tr('points (.txt)'))
        self.rb2 = QRadioButton(self.tr('constant values (.txt)'))
        self.rb0.setChecked(True)
        self.rb0.clicked.connect(lambda: self.btnstate(self.rb0, self.rb1, self.rb2))
        self.rb0.clicked.connect(self.add_polygon_widgets)
        self.rb1.clicked.connect(lambda: self.btnstate(self.rb1, self.rb0, self.rb2))
        self.rb1.clicked.connect(self.add_point_widgets)
        self.rb2.clicked.connect(lambda: self.btnstate(self.rb2, self.rb1, self.rb0))
        self.rb2.clicked.connect(self.add_const_widgets)

        # POLYGON (0 line)
        filetitle_polygon_label = QLabel(self.tr('File'))
        self.file_polygon_label = QLabel(self.namefile[0], self)
        self.file_polygon_label.setToolTip(self.pathfile_polygon)
        self.sub_choosefile_polygon = QPushButton(self.tr('Choose file (.shp)'), self)
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
        self.load_polygon_substrate = QPushButton(self.tr('Create .sub file'), self)
        self.load_polygon_substrate.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_polygon_substrate.clicked.connect(lambda: self.load_sub_gui('polygon'))

        # POINT (0 line)
        filetitle_point_label = QLabel(self.tr('File'))
        self.file_point_label = QLabel(self.namefile[0], self)
        self.file_point_label.setToolTip(self.pathfile[0])
        self.sub_choosefile_point = QPushButton(self.tr('Choose file (.txt)'), self)
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
        self.load_point_substrate = QPushButton(self.tr('Create .sub file'), self)
        self.load_point_substrate.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_point_substrate.clicked.connect(lambda: self.load_sub_gui('point'))

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
        self.load_constant_substrate = QPushButton(self.tr('Create .sub file'), self)
        self.load_constant_substrate.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_constant_substrate.clicked.connect(lambda: self.load_sub_gui('constant'))

        # COMMON
        last_sub_file_title_label = QLabel(self.tr('Last file created'))
        self.last_sub_file_name_label = QLabel(self.tr('no file'))
        self.name_last_hdf5(type="hdf5_substrate")  # find the name of the last merge file and add it to self.lm2

        # MERGE
        l9 = QLabel(self.tr("Hydraulic data (.hyd)"))
        l10 = QLabel(self.tr("Substrate data (.sub)"))
        self.drop_hyd = QComboBox()
        self.drop_hyd.currentIndexChanged.connect(self.create_hdf5_merge_name)
        self.drop_sub = QComboBox()
        self.drop_sub.currentIndexChanged.connect(self.create_hdf5_merge_name)
        self.load_b2 = QPushButton(self.tr("Create .hab file"), self)
        self.load_b2.setStyleSheet("background-color: #47B5E6; color: black")
        self.load_b2.clicked.connect(self.send_merge_grid)
        self.spacer2 = QSpacerItem(1, 10)
        # get possible substrate from the project file
        self.update_sub_hdf5_name()
        # file name output
        hdf5_merge_label = QLabel(self.tr('.hab file name'))
        self.hdf5_merge_lineedit = QLineEdit('')  # default hdf5 merge name
        # get the last file created
        lm1 = QLabel(self.tr('Last file created'))
        self.last_merge_file_name_label = QLabel(self.tr('no file'))
        self.name_last_hdf5(type="hdf5_mergedata")  # find the name of the last merge file and add it to self.lm2

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
        self.layout_polygon.addWidget(self.load_polygon_substrate, 5, 2)  # 5 line
        [self.layout_polygon.setRowMinimumHeight(i, 30) for i in range(self.layout_polygon.rowCount())]
        self.polygon_group = QGroupBox(self.tr('Polygons'))
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
        self.layout_point.addWidget(self.load_point_substrate, 5, 2)  # 5 line
        [self.layout_point.setRowMinimumHeight(i, 30) for i in range(self.layout_point.rowCount())]
        self.point_group = QGroupBox(self.tr('Points'))
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
        self.layout_constant.addWidget(self.load_constant_substrate, 5, 2)  # 5 line
        [self.layout_constant.setRowMinimumHeight(i, 30) for i in range(self.layout_constant.rowCount())]
        self.constant_group = QGroupBox(self.tr('Constant values'))
        self.constant_group.setLayout(self.layout_constant)

        # SUBSTRATE GROUP
        self.layout_sub = QGridLayout()  # 4 rows et 4 columns
        self.layout_sub.addWidget(l1, 0, 0, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.rb0, 0, 1, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.rb1, 0, 2, 1, 1)  # index row, index column, nb row, nb column
        self.layout_sub.addWidget(self.rb2, 0, 3, 1, 1)  # index row, index column, nb row, nb column
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
        susbtrate_group = QGroupBox(self.tr('Substrate data'))
        susbtrate_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        susbtrate_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        susbtrate_group.setLayout(self.layout_sub)

        # MERGE GROUP
        self.layout_merge = QGridLayout()  # 5 rows et 3 columns
        self.layout_merge.addWidget(l9, 0, 0)
        self.layout_merge.addWidget(self.drop_hyd, 0, 1)
        self.layout_merge.addWidget(l10, 1, 0)
        self.layout_merge.addWidget(self.drop_sub, 1, 1)
        self.layout_merge.addWidget(hdf5_merge_label, 2, 0)
        self.layout_merge.addWidget(self.hdf5_merge_lineedit, 2, 1)
        self.layout_merge.addWidget(self.load_b2, 2, 2)
        self.layout_merge.addWidget(lm1, 3, 0)
        self.layout_merge.addWidget(self.last_merge_file_name_label, 3, 1)
        [self.layout_merge.setRowMinimumHeight(i, 30) for i in range(self.layout_merge.rowCount())]
        merge_group = QGroupBox(self.tr('Merging of hydraulic and substrate data'))
        merge_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        merge_group.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        merge_group.setLayout(self.layout_merge)

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
            extensions = [".shp"]
        if substrate_mapping_method == "point":
            extensions = [".txt"]
        if substrate_mapping_method == "constant":
            extensions = [".txt"]
        filter = "File ("
        for ext in extensions:
            filter += '*' + ext + ' '
        filter += ')' + ";; All File (*.*)"

        # get last path
        if self.read_attribute_xml("substrate_path") != self.path_prj and self.read_attribute_xml(
                "substrate_path") != "no_data":
            substrate_path = self.read_attribute_xml("substrate_path")  # path spe
        elif self.read_attribute_xml("Path_last_file_loaded") != self.path_prj:
            substrate_path = self.read_attribute_xml("Path_last_file_loaded")  # path last
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

            # POLYGON
            if substrate_mapping_method == "polygon":
                # check classification code in .txt (polygon or point shp)
                if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                    self.send_log.emit("Error: The selected shapefile is not accompanied by its habby .txt file.")
                    return
                if os.path.isfile(os.path.join(dirname, blob + ".txt")):
                    with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                        dataraw = f.read()
                    substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                        "\n")
                    if "substrate_classification_code=" in substrate_classification_code_raw:
                        substrate_classification_code = \
                        substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                        if substrate_classification_code not in self.substrate_classification_codes:
                            self.send_log.emit("Error: The classification code in .txt file is not recognized : "
                                               + substrate_classification_code)
                            return
                    else:
                        self.send_log.emit("Error: The name 'substrate_classification_code=' is not found in"
                                           " .txt file.")
                        return
                    if "substrate_classification_method=" in substrate_classification_method_raw:
                        substrate_classification_method = \
                        substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                        if substrate_classification_method not in self.substrate_classification_methods:
                            self.send_log.emit("Error: The classification method in .txt file is not recognized : "
                                               + substrate_classification_method)
                            return
                    else:
                        self.send_log.emit("Error: The name 'substrate_classification_method=' is not found in"
                                           " .txt file.")
                        return
                    if "default_values=" in substrate_default_values_raw:
                        substrate_default_values = substrate_default_values_raw.split("default_values=")[1].strip()
                        constant_values_list = substrate_default_values.split(",")
                        for value in constant_values_list:
                            try:
                                int(value.strip())
                            except:
                                self.send_log.emit("Error: Default values can't be converted to integer : "
                                                   + substrate_default_values)
                                return
                    else:
                        self.send_log.emit("Error: The name 'default_values=' is not found in"
                                           " .txt file.")
                        return

                # check EPSG code in .prj
                if not os.path.isfile(os.path.join(dirname, blob + ".prj")):
                    self.send_log.emit(
                        "Warning: The selected shapefile is not accompanied by its .prj file. EPSG code is unknwon.")
                    epsg_code = "unknown"
                if os.path.isfile(os.path.join(dirname, blob + ".prj")):
                    # ident = Sridentify()
                    # ident.from_file(os.path.join(dirname, blob + ".prj"))
                    # epsg_code = ident.get_epsg()
                    driver = ogr.GetDriverByName('ESRI Shapefile')
                    file_shp = driver.Open(os.path.join(dirname, blob + ".shp"))
                    layer = file_shp.GetLayer()
                    inSpatialRef  = layer.GetSpatialRef()
                    sr = osr.SpatialReference(str(inSpatialRef))
                    res = sr.AutoIdentifyEPSG()
                    epsg_code_str = sr.GetAuthorityCode(None)
                    if epsg_code_str:
                        epsg_code = int(epsg_code_str)
                    else:
                        epsg_code = "unknown"

                # save to attributes
                self.namefile[0] = filename
                self.pathfile_polygon = dirname
                self.namefile_polygon = filename
                self.name_hdf5_polygon = blob + ".sub"

                # save to GUI
                self.file_polygon_label.setText(filename)
                self.file_polygon_label.setToolTip(self.pathfile_polygon)
                self.sub_classification_code_polygon_label.setText(substrate_classification_code)
                self.sub_classification_method_polygon_label.setText(substrate_classification_method)
                self.sub_default_values_polygon_label.setText(substrate_default_values)
                self.epsg_polygon_label.setText(str(epsg_code))
                self.polygon_hname.setText(self.name_hdf5_polygon)

            # POINT
            if substrate_mapping_method == "point":
                # txt case
                if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                    self.send_log.emit("Error: The selected file don't exist.")
                    return
                if os.path.isfile(os.path.join(dirname, blob + ".txt")):
                    with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                        dataraw = f.read()
                    if len(dataraw.split("\n")[:4]) < 4:
                        self.send_log.emit("Error: This text file is not a valid point substrate.")
                        return
                    epsg_raw, substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                        "\n")[:4]
                    # check EPSG in .txt (polygon or point shp)
                    if "EPSG=" in epsg_raw:
                        epsg_code = epsg_raw.split("EPSG=")[1].strip()
                    else:
                        self.send_log.emit("Error: The name 'EPSG=' is not found in .txt file.")
                        return
                    # check classification code in .txt ()
                    if "substrate_classification_code=" in substrate_classification_code_raw:
                        substrate_classification_code = \
                        substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                        if substrate_classification_code not in self.substrate_classification_codes:
                            self.send_log.emit("Error: The classification code in .txt file is not recognized : "
                                               + substrate_classification_code)
                            return
                    else:
                        self.send_log.emit("Error: The name 'substrate_classification_code=' is not found in"
                                           " .txt file.")
                        return
                    if "substrate_classification_method=" in substrate_classification_method_raw:
                        substrate_classification_method = \
                        substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                        if substrate_classification_method not in self.substrate_classification_methods:
                            self.send_log.emit("Error: The classification method in .txt file is not recognized : "
                                               + substrate_classification_method)
                            return
                    else:
                        self.send_log.emit("Error: The name 'substrate_classification_method=' is not found in"
                                           " .txt file.")
                        return
                    if "default_values=" in substrate_default_values_raw:
                        substrate_default_values = substrate_default_values_raw.split("default_values=")[1].strip()
                        constant_values_list = substrate_default_values.split(",")
                        for value in constant_values_list:
                            try:
                                int(value.strip())
                            except:
                                self.send_log.emit("Error: Default values can't be converted to integer : "
                                                   + substrate_default_values)
                                return
                    else:
                        self.send_log.emit("Error: The name 'default_values=' is not found in"
                                           " .txt file.")
                        return

                    # save to attributes
                    self.namefile[0] = filename
                    self.pathfile_point = dirname
                    self.namefile_point = filename
                    self.name_hdf5_point = blob + ".sub"

                    # save to GUI
                    self.file_point_label.setText(filename)
                    self.file_point_label.setToolTip(self.pathfile_point)
                    self.sub_classification_code_point_label.setText(substrate_classification_code)
                    self.sub_classification_method_point_label.setText(substrate_classification_method)
                    self.sub_default_values_point_label.setText(substrate_default_values)
                    self.epsg_point_label.setText(str(epsg_code))
                    self.point_hname.setText(self.name_hdf5_point)

            # CONSTANT
            if substrate_mapping_method == "constant":
                # txt
                if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                    self.send_log.emit("Error: The selected text file don't exist.")
                    return
                if os.path.isfile(os.path.join(dirname, blob + ".txt")):
                    with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                        dataraw = f.read()
                    substrate_classification_code_raw, substrate_classification_method_raw, constant_values_raw = dataraw.split(
                        "\n")
                    # classification code
                    if "substrate_classification_code=" in substrate_classification_code_raw:
                        substrate_classification_code = \
                        substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                        if substrate_classification_code not in self.substrate_classification_codes:
                            self.send_log.emit("Error: The classification code in .txt file is not recognized : "
                                               + substrate_classification_code)
                            return
                    else:
                        self.send_log.emit("Error: The name 'substrate_classification_code=' is not found in"
                                           " .txt file.")
                        return
                    if "substrate_classification_method=" in substrate_classification_method_raw:
                        substrate_classification_method = \
                        substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                        if substrate_classification_method not in self.substrate_classification_methods:
                            self.send_log.emit("Error: The classification method in .txt file is not recognized : "
                                               + substrate_classification_method)
                            return
                    else:
                        self.send_log.emit("Error: The name 'substrate_classification_method=' is not found in"
                                           " .txt file.")
                        return
                    # constant values
                    if "constant_values=" in constant_values_raw:
                        constant_values = constant_values_raw.split("constant_values=")[1].strip()
                        constant_values_list = constant_values.split(",")
                        for value in constant_values_list:
                            try:
                                int(value.strip())
                            except:
                                self.send_log.emit("Error: Constant values can't be converted to integer : "
                                                   + constant_values)
                                return
                    else:
                        self.send_log.emit("Error: The name 'constant_values=' is not found in .txt file.")
                        return
                    # save to attributes
                    self.namefile[0] = filename
                    self.pathfile_constant = dirname
                    self.namefile_constant = filename
                    self.name_hdf5_constant = blob + ".sub"

                    # save to GUI
                    self.file_constant_label.setText(filename)
                    self.file_constant_label.setToolTip(self.pathfile_constant)
                    self.sub_classification_code_constant_label.setText(substrate_classification_code)
                    self.sub_classification_method_constant_label.setText(substrate_classification_method)
                    self.valuesdata_constant_label.setText(constant_values)
                    self.constant_hname.setText(self.name_hdf5_constant)

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
            if not self.polygon_hname.text():
                self.send_log.emit(self.tr('Warning: filename output is empty. Please specify it.'))
                return
        if sub_mapping_method == 'point':
            if not self.point_hname.text():
                self.send_log.emit(self.tr('Warning: filename output is empty. Please specify it.'))
                return
        if sub_mapping_method == 'constant':
            if not self.constant_hname.text():
                self.send_log.emit(self.tr('Warning: filename output is empty. Please specify it.'))
                return

        # info
        self.timer.start(100)

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)

        # polygon case
        if sub_mapping_method == 'polygon':
            # block button substrate
            self.load_polygon_substrate.setDisabled(True)  # substrate
            # save path and name substrate
            self.save_xml(0)  # shp filename in xml
            filename = self.file_polygon_label.text()
            namebase, ext = os.path.splitext(filename)
            path_im = self.find_path_im()
            sub_classification_code = self.sub_classification_code_polygon_label.text()
            sub_epsg_code = self.epsg_polygon_label.text()
            default_values = self.sub_default_values_polygon_label.text()
            self.name_hdf5 = self.polygon_hname.text()
            self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

            # check if we have all files
            name1 = namebase + '.dbf'
            name2 = namebase + '.shx'
            name3 = namebase + '.prj'  # it is ok if it does not exists
            pathname1 = os.path.join(self.pathfile_polygon, name1)
            pathname2 = os.path.join(self.pathfile_polygon, name2)
            pathname3 = os.path.join(self.pathfile_polygon, name3)
            if not os.path.isfile(pathname1) or not os.path.isfile(pathname2):
                self.send_log.emit(
                    'Error: A shapefile is composed of three file at leasts: a .shp file, a .shx file, and'
                    ' a .dbf file.')
                self.load_polygon_substrate.setDisabled(False)
                return

            sys.stdout = self.mystdout = StringIO()  # out to GUI

            # load substrate shp (and triangulation)
            self.q = Queue()
            self.p = Process(target=substrate_mod.load_sub_shp,
                             args=(filename,
                                   self.pathfile_polygon,
                                   self.path_prj,
                                   self.path_prj + "/hdf5",
                                   self.name_prj,
                                   self.name_hdf5,
                                   sub_mapping_method,
                                   sub_classification_code,
                                   sub_epsg_code,
                                   default_values,
                                   self.q))
            self.p.name = "Substrate data loading from shapefile"
            self.p.start()

            sys.stdout = sys.__stdout__  # reset to console
            self.send_err_log()

            # copy shape file (compsed of .shp, .shx and .dbf)
            path_input = self.find_path_input()
            name_all = [filename, name1, name2]
            path_all = [self.pathfile_polygon, self.pathfile_polygon, self.pathfile_polygon]
            # we might have an addition projection file to copy
            if os.path.isfile(pathname3):
                name_all = [filename, name1, name2, name3]
                path_all = [self.pathfile_polygon, self.pathfile_polygon, self.pathfile_polygon, self.pathfile_polygon]
            self.p2 = Process(target=hdf5_mod.copy_files, args=(name_all, path_all, path_input))
            self.p2.start()

            # log info
            self.send_log.emit(self.tr('# Loading: Substrate data ...'))
            self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
            self.send_log.emit("py    path1=r'" + path_input + "'")
            self.send_log.emit("py    type='" + sub_classification_code + "'")
            self.send_log.emit("py    [coord_p, ikle_sub, sub_dm, sub_pg, ok_dom] = substrate.load_sub_shp"
                               "(file1, path1, type)\n")
            self.send_log.emit("restart LOAD_SUB_SHP")
            self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
            self.send_log.emit("restart    sub_classification_code: " + sub_classification_code)

        # point case
        if sub_mapping_method == 'point':
            # block button substrate
            self.load_point_substrate.setDisabled(True)  # substrate
            # save path and name substrate
            self.save_xml(0)  # txt filename in xml
            filename = self.file_point_label.text()
            namebase, ext = os.path.splitext(filename)
            path_im = self.find_path_im()
            path_shp = self.find_path_input()
            sub_classification_code = self.sub_classification_code_point_label.text()
            sub_classification_method = self.sub_classification_method_point_label.text()
            sub_epsg_code = self.epsg_point_label.text()
            default_values = self.sub_default_values_point_label.text()
            self.name_hdf5 = self.point_hname.text()
            self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

            sys.stdout = self.mystdout = StringIO()  # out to GUI

            sub_filename_voronoi_shp = substrate_mod.load_sub_txt(self.namefile[0], self.pathfile[0],
                                                                  sub_mapping_method,
                                                                  sub_classification_code,
                                                                  sub_classification_method,
                                                                  sub_epsg_code,
                                                                  path_shp)

            # if shp ok
            if sub_filename_voronoi_shp:
                # load substrate shp (and triangulation)
                self.q = Queue()
                self.p = Process(target=substrate_mod.load_sub_shp,
                                 args=(sub_filename_voronoi_shp,
                                       path_shp,
                                       self.path_prj,
                                       self.path_prj + "/hdf5",
                                       self.name_prj,
                                       self.name_hdf5,
                                       sub_mapping_method,
                                       sub_classification_code,
                                       sub_epsg_code,
                                       default_values,
                                       self.q))
                self.p.name = "Substrate data loading from points"
                self.p.start()

                sys.stdout = sys.__stdout__  # reset to console
                self.send_err_log()

                # copy
                path_input = self.find_path_input()
                self.p2 = Process(target=hdf5_mod.copy_files, args=(self.namefile, self.pathfile, path_input))
                self.p2.start()

                # log info
                self.send_log.emit(self.tr('# Loading: Substrate data shapefile ...'))
                self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
                self.send_log.emit("py    path1=r'" + path_input + "'")
                self.send_log.emit("py    type='" + sub_classification_code + "'")
                self.send_log.emit("py    [coord_p, ikle_sub, sub_dm, sub_pg, ok_dom] = substrate.load_sub_shp"
                                   "(file1, path1, type)\n")
                self.send_log.emit("restart LOAD_SUB_SHP")
                self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
                self.send_log.emit("restart    sub_classification_code: " + sub_classification_code)

        # constante case
        if sub_mapping_method == 'constant':
            # block button substrate
            self.load_constant_substrate.setDisabled(True)  # substrate
            # save path and name substrate
            self.save_xml(0)  # txt filename in xml
            filename = self.file_constant_label.text()
            namebase, ext = os.path.splitext(filename)
            path_im = self.find_path_im()
            path_shp = self.find_path_input()
            path_hdf5 = self.find_path_hdf5()
            sub_classification_code = self.sub_classification_code_constant_label.text()
            sub_classification_method = self.sub_classification_method_constant_label.text()
            sub_constant_values = self.valuesdata_constant_label.text()
            self.name_hdf5 = self.constant_hname.text()
            self.project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

            constant_values_list = sub_constant_values.split(",")
            sub_array = [[] for i in range(len(constant_values_list))]
            for i, value in enumerate(constant_values_list):
                sub_array[i] = int(value.strip())

            sub_description_system = dict(sub_mapping_method=sub_mapping_method,
                                          sub_classification_code=sub_classification_code,
                                          sub_classification_method=sub_classification_method,
                                          sub_filename_source=filename,
                                          sub_constant_values=sub_constant_values,
                                          sub_default_values=sub_constant_values,
                                          sub_class_number=str(len(sub_array)),
                                          sub_reach_number="1",
                                          sub_unit_number="1",
                                          sub_unit_list="0.0",
                                          sub_unit_type="unknown")

            data = dict(sub=[sub_array],
                        nb_unit=1,
                        nb_reach=1)

            sys.stdout = self.mystdout = StringIO()  # out to GUI
            self.q = Queue()
            self.q.put("const_sub")

            # save hdf5
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, self.name_hdf5)
            self.p = Process(target=hdf5.create_hdf5_sub,
                             args=(sub_description_system, data))
            self.p.name = "Substrate data loading from constant values"
            self.p.start()

            self.send_err_log()

            # log info
            self.send_log.emit(self.tr('# Loading: Substrate data constant values ...'))
            self.send_log.emit("py    val_c=" + sub_constant_values)
            self.send_log.emit(
                "py    load_hdf5.save_hdf5_sub(path_prj, path_prj, name_prj, val_c, val_c, [], [], [], [], 're_run_const_sub'"
                ", True, 'SUBSTRATE') \n")
            self.send_log.emit("restart LOAD_SUB_CONST")
            self.send_log.emit("restart    val_c: " + sub_constant_values)
            # self.send_log.emit("restart    hdf5_namefile: " + os.path.join(path_hdf5, self.name_hdf5 +'.sub'))
            # unblock button substrate
            self.load_constant_substrate.setDisabled(False)  # substrate
            self.p.join()

    def recreate_image_sub(self, save_fig=False):
        """
        This function is used to recreate the image linked with the subtrate. So this is not the figure for the "merge"
        part, but only to show the substrat alone.

        :param: save_fig: A boolean to save or not the figure
        """
        path_im = self.find_path_im()
        if not self.last_hdf5:
            self.send_log.emit('Warning: No figure created \n')
            return

        # getting the subtrate data
        path_hdf5 = self.find_path_hdf5()

        # plot susbstrate
        types_hdf5 = "substrate"
        names_hdf5 = [self.last_hdf5]
        variables = ["coarser_dominant"]
        units = ["no unit"]
        units_index = [0]
        types_plot = "display"
        self.nativeParentWidget().central_widget.data_explorer_tab.data_explorer_frame.plot(types_hdf5, names_hdf5,
                                                                                            variables, units,
                                                                                            units_index, types_plot)

    def update_sub_hdf5_name(self):
        """
        This function update the QComBox on substrate data which is on the substrate tab. The similiar function
        for hydrology is in Main_Windows_1.py as it is more practical to have it there to collect all the signals.
        """
        path_hdf5 = self.find_path_hdf5()
        self.sub_name = self.read_attribute_xml('hdf5_substrate')
        self.sub_name = list(reversed(self.sub_name.split(',')))
        sub_name2 = []  # we might have unexisting hdf5 file in the xml project file
        for i in range(0, len(self.sub_name)):
            if os.path.isfile(self.sub_name[i]):
                sub_name2.append(self.sub_name[i])
            if os.path.isfile(os.path.join(path_hdf5, self.sub_name[i])):
                sub_name2.append(self.sub_name[i])
        self.sub_name = sub_name2
        self.drop_sub.clear()
        for i in range(0, len(self.sub_name)):
            # if i == 0 and len(self.sub_name) > 1:
            #     self.drop_sub.addItem(' ')
            if len(self.sub_name[i]) > self.max_lengthshow:
                self.drop_sub.addItem(os.path.basename(self.sub_name[i][:self.max_lengthshow]))
            else:
                self.drop_sub.addItem(os.path.basename(self.sub_name[i]))
        self.drop_sub.setCurrentIndex(0)

    def create_hdf5_merge_name(self):
        hdf5_name_hyd = self.drop_hyd.currentText()
        hdf5_name_sub = self.drop_sub.currentText()
        if hdf5_name_hyd != ' ' and hdf5_name_hyd != '' and hdf5_name_sub != ' ' and hdf5_name_sub != '':
            name_hdf5merge = hdf5_name_hyd[:-4] + "_" + hdf5_name_sub[:-4] + ".hab"
            self.hdf5_merge_lineedit.setText(name_hdf5merge)

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
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            for i in range(0, len(self.attributexml)):
                child = root.find(".//" + self.attributexml[1])
                # if there is data in the project file about the model
                if child is not None:
                    self.name_att = child.text

    def send_merge_grid(self):
        """
        This function calls the function merge grid in substrate_mod.py. The goal is to have the substrate and hydrological
        data on the same grid. Hence, the hydrological grid will need to be cut to the form of the substrate grid.

        This function can be slow so it call on a second thread.
        """
        self.model_type = 'HABITAT'
        self.data_type = "HABITAT"
        # if hdf5_filename_output empty: msg
        if not self.hdf5_merge_lineedit.text():
            self.send_log.emit(self.tr('Warning: .hab filename output is empty. Please specify it.'))
            return

        # show progressbar
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setVisible(True)  # show progressbar

        self.send_log.emit(self.tr('# Merging: substrate and hydraulic grid...'))

        # get useful data
        path_hdf5 = self.find_path_hdf5()
        path_shp = self.find_path_output("Path_Shape")
        if len(self.drop_hyd) > 1:
            hdf5_name_hyd = self.drop_hyd.currentText()  # path_hdf5 + "/" +
        elif len(self.drop_hyd) == 0:
            self.send_log.emit('Error: No hydrological file available \n')
            return
        else:
            hdf5_name_hyd = self.hyd_name[0]
        if len(self.sub_name) == 0:
            self.send_log.emit('Error: No substrate file available \n')
            return
        hdf5_name_sub = self.drop_sub.currentText()

        # hdf5 output file
        name_hdf5merge = self.hdf5_merge_lineedit.text()
        # if file exist add number
        nb = 0
        while os.path.isfile(path_hdf5 + "/" + name_hdf5merge + ".hab"):
            nb = nb + 1
            name_hdf5merge = self.hdf5_merge_lineedit.text() + "_" + str(nb)

        # get if we erase old data or not
        # get the figure options and the type of output to be created
        project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)

        # block button merge
        self.load_b2.setDisabled(True)  # merge

        # for error management and figures
        self.timer.start(100)

        # run the function
        self.q = Queue()
        self.progress_value = Value("i", 0)
        self.p = Process(target=mesh_management_mod.merge_grid_and_save,
                         args=(name_hdf5merge,
                               hdf5_name_hyd,
                               hdf5_name_sub,
                               path_hdf5,
                               self.name_prj,
                               self.path_prj,
                               self.model_type,
                               self.progress_value,
                               self.q,
                               False,
                               project_preferences))
        self.p.name = "Hydraulic and substrate data merging"
        self.p.start()

        # log
        # functions if ind is zero also
        self.send_log.emit("py    file_hyd=r'" + self.hyd_name[self.drop_hyd.currentIndex() - 1] + "'")
        self.send_log.emit("py    name_sub=r'" + self.sub_name[self.drop_sub.currentIndex()] + "'")
        self.send_log.emit("py    path_sub=r'" + path_hdf5 + "'")
        self.send_log.emit("py    mesh_grid2.merge_grid_and_save(file_hyd,name_sub, path_sub, defval, name_prj, "
                           "path_prj, 'SUBSTRATE', [], True) \n")
        self.send_log.emit("restart MERGE_GRID_SUB")
        self.send_log.emit("restart    file_hyd: r" + self.hyd_name[self.drop_hyd.currentIndex() - 1])
        self.send_log.emit("restart    file_sub: r" + os.path.join(path_hdf5,
                                                                   self.sub_name[self.drop_sub.currentIndex()]))


if __name__ == '__main__':
    pass
