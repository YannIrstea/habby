import os
import numpy as np
import sys
import shutil
from io import StringIO
from PyQt5.QtCore import QTranslator, pyqtSignal, QTimer, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox, QAbstractItemView
import h5py
np.set_printoptions(threshold=np.inf)
from multiprocessing import Process, Queue
# import time
from src import Hec_ras06
from src import hec_ras2D
from src import selafin_habby1
from src import substrate
from src import rubar
from src import river2d
from src import mascaret
from src import manage_grid_8
from src import load_hdf5
from src_GUI import output_fig_GUI
from src import mesh_grid2
from src import lammi
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class Hydro2W(QWidget):
    """
    The class Hydro2W is the second tab of HABBY. It is the class containing all the classes/Widgets which are used
    to load the hydrological data.

    List of model supported by Hydro2W:
    files separetly. However, sometime the file was not found
    *   Telemac (2D)
    *   Hec-Ras (1.5D et 2D)
    *   Rubar BE et 2(1D et 2D)
    *   Mascaret (1D)
    *   River2D (2D)

    **Technical comments**

    To call the different classes used to load the hydrological data, the user selects the name of the hydrological
    model from a QComboBox call self.mod. The method ‘selection_change” calls the class that the user chooses in
    self.mod. All the classes used to load the
    hydrological data are created when HABBY starts and are kept in a stack called self.stack. The function
    selection_change() just changes the selected item of the stack based on the user choice on self.mod.

    Any new hydrological model should also be added to the stack and to the list of models contained in self.mod
    (name of the list: self.name_model).

    In addition to the stack containing the hydrological information, hydro2W has two buttons. One button open
    a QMessageBox() which give information about the models, using the method “give_info_model”.  It is useful if a
    special type of file is needed to load the data from a model or to give extra information about one hydrological
    model. The text which is shown on the QMessageBox is given in one text file for each model.
    These text file are contained in the folder ‘model_hydro” which is in the HABBY folder. For the moment,
    there are models for which no text files have been prepared. The text file should have the following format:

    *	A short sentence with general info
    *	The keyword:  MORE INFO
    *	All other infomation which are needed.

    The second button allows the user to load an hdf5 file containing hydrological data from another project.
    As long as the hdf5 is in the right format, it does not matter from which hydrological model it was loaded from
    or even if this hydrological model is supported by HABBY.
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.mod = QComboBox()
        # self.mod_loaded = QComboBox()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_model = ["", "HEC-RAS 1D", "HEC-RAS 2D", "LAMMI", "MASCARET", "RIVER2D", "RUBAR BE", "RUBAR 20",
                           "TELEMAC", "HABBY HDF5"]  # "MAGE"
        self.mod_act = 0
        self.stack = QStackedWidget()
        self.msgi = QMessageBox()
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """
        # generic label
        l2 = QLabel(self.tr('<b> LOAD NEW DATA </b>'))
        l3 = QLabel(self.tr('<b>Available hydrological models </b>'))

        # available model
        self.mod.addItems(self.name_model)
        self.mod.currentIndexChanged.connect(self.selectionchange)
        self.button1 = QPushButton(self.tr('?'), self)
        self.button1.clicked.connect(self.give_info_model)
        spacer2 = QSpacerItem(50, 1)

        # add the widgets representing the available models to a stack of widget
        self.free = FreeSpace()
        self.hecras1D = HEC_RAS1D(self.path_prj, self.name_prj)
        self.hecras2D = HEC_RAS2D(self.path_prj, self.name_prj)
        self.telemac = TELEMAC(self.path_prj, self.name_prj)
        self.rubar2d = Rubar2D(self.path_prj, self.name_prj)
        self.rubar1d = Rubar1D(self.path_prj, self.name_prj)
        self.mascar = Mascaret(self.path_prj, self.name_prj)
        self.riverhere2d = River2D(self.path_prj, self.name_prj)
        self.lammi = LAMMI(self.path_prj, self.name_prj)
        self.habbyhdf5 = HabbyHdf5(self.path_prj, self.name_prj)
        self.stack.addWidget(self.free)  # order matters in the next lines!
        self.stack.addWidget(self.hecras1D)
        self.stack.addWidget(self.hecras2D)
        self.stack.addWidget(self.lammi)
        self.stack.addWidget(self.mascar)
        self.stack.addWidget(self.riverhere2d)
        self.stack.addWidget(self.rubar1d)
        self.stack.addWidget(self.rubar2d)
        self.stack.addWidget(self.telemac)
        self.stack.addWidget(self.habbyhdf5)
        self.stack.setCurrentIndex(self.mod_act)

        # list with available hdf5
        l4 = QLabel(self.tr('<b> Available hdf5 files </b>'))
        self.drop_hyd = QComboBox()

        # layout
        self.layout4 = QGridLayout()
        self.layout4.addWidget(l3, 0, 0)
        self.layout4.addWidget(self.mod, 1, 0)
        self.layout4.addItem(spacer2, 1, 1)
        self.layout4.addWidget(self.button1, 1, 2)
        self.layout4.addWidget(self.stack, 2, 0)
        self.layout4.addWidget(l4, 3, 0)
        self.layout4.addWidget(self.drop_hyd, 4, 0)

        self.setLayout(self.layout4)

    def selectionchange(self, i):
        """
        Change the shown widget which represents each hydrological model (all widget are in a stack)

        :param i: the number of the model (0=no model, 1=hecras1d, 2= hecras2D,...)
        """

        self.mod_act = i
        self.stack.setCurrentIndex(self.mod_act)

    def give_info_model(self):
        """
        A function to show extra information about each hydrological model.
        The information should be in a text file with the same name as the model in the model_hydo folder.
        General info goes as the start of the text file. If the text is too long, add the keyword "MORE INFO"
        and add the longer text afterwards. The message box will show the supplementary information only if the user
        asks for detailed information.
        """

        self.msgi.setIcon(QMessageBox.Information)
        text_title = self.tr("Information on ")
        mod_name = self.name_model[self.mod_act]
        self.msgi.setWindowTitle(text_title + mod_name)
        info_filename = os.path.join('./model_hydro', mod_name+'.txt')
        self.msgi.setStandardButtons(QMessageBox.Ok)
        if os.path.isfile(info_filename):
            with open(info_filename, 'rt') as f:
                text = f.read()
            text2 = text.split('MORE INFO')
            self.msgi.setText(text2[0])
            self.msgi.setDetailedText(text2[1])
        else:
            self.msgi.setText(self.tr('No information yet!         '))
            self.msgi.setDetailedText('No detailed info yet.')
        self.msgi.setEscapeButton(QMessageBox.Ok)  # detailed text erase the red x
        self.msgi.show()


class FreeSpace(QWidget):
    """
    Simple class with empty space, just to have only Qwidget in the stack.

    **Technical comment**

    The idea of this class is that the user see a free space when it opens the “Hydro” Tab instead
    of directly seeing one of the hydraulic model. The goal is to avoid the case where a user tries to load data before
    selecting the real model. For example, if a user wants to load mascaret data and that an item is selected by
    default in the stack of classes related to hydrology (such as HEC-RAS1D), it might be logical for the user to try
    to load masacret data using the HEC-RAS class. Because of the FreeSpace class, he actually has to select
    the model he wants to load.
    """

    def __init__(self):

        super().__init__()
        self.spacer = QSpacerItem(1, 1)
        self.layout_s = QGridLayout()
        self.layout_s.addItem(self.spacer, 0, 0)
        self.setLayout(self.layout_s)


class SubHydroW(QWidget):
    """
    SubHydroW is class which is the parent of the classes which can be used to open the hydrological models. This class
    is a bit special. It is not called directly by HABBY but by the classes which load the hydrological data and which
    inherits from this class. The advantage of this architecture is that all the children classes can use the methods
    written in SubHydroW(). Indeed, all the children classes load hydrological data and therefore they are similar and
    can use similar functions.

    In other word, there are MainWindows() which provides the windows around the widget and Hydro2W which provide the
    widget for the hydrological Tab and one class by hydrological model to really load the model. The latter classes
    have various methods in common, so they inherit from SubHydroW, this class.
    """

    send_log = pyqtSignal(str, name='send_log')
    """
    A Pyqtsignal to write the log.
    """
    drop_hydro = pyqtSignal()
    """
    A PyQtsignal signal for the substrate tab so it can account for the new hydrological info.
    """
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figure.
    """

    def __init__(self, path_prj, name_prj):

        # do not change the string 'unknown file'
        self.namefile = ['unknown file', 'unknown file']  # for children, careful with list index out of range
        self.interpo = ["Interpolation by block", "Linear interpolation", "Nearest Neighbors"]  # order matters here
        self.interpo_choice = 0 # gives which type of interpolation is chosen (it is the index of self.interpo )
        self.pathfile = ['.', '.']
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
        self.np_point_vel = -99  # -99 -> velocity calculated in the same point than the profile height
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
        self.hname = QLineEdit(' ')
        self.p = None  # second process
        self.q = None
        self.fig_opt = []
        super().__init__()

        # update error or show figure every second
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.send_data)

    def was_model_loaded_before(self, i=0, many_file=False):
        """
        A function to test if the model loaded before. If yes, it updates the attibutes anf the widgets of the
        hydrological model on consideration.

        :param i: an int used in cases where there is more than one file to load (geometry and output for example)
        :param many_file: A bollean. If true this function will load more than one file, separated by ','. If False,
                it will only loads the file of one model (see the comment below).

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
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
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
                            self.msg2.setText(self.tr("One of the file given in the project file does not exist." ))
                            self.msg2.setStandardButtons(QMessageBox.Ok)
                            self.msg2.show()
                else:
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Previously Loaded File"))
                    self.msg2.setText(
                        self.tr("The file given in the project file does not exist. Hydrological model:" + self.model_type))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()

    def gethdf5_name_gui(self):
        """
        This function get the name of the hdf5 file for the hydrological and write down in the QLineEdit on the GUI.
        It is possible to have more than one hdf5 file for a model type. For example, we could have created two hdf5
        based on hec-ras output. The default here is to write the last model loaded. It is the same default behaviour
        than for the function was_model_loaded_before(). To keep the coherence between the filename and hdf5 name,
        a change in this behaviour should be reflected in both function.

        This function calls the function get_hdf5_name in the load_hdf5.py file

        """

        sys.stdout = self.mystdout = StringIO()
        pathname_hdf5 = load_hdf5.get_hdf5_name(self.model_type, self.name_prj, self.path_prj)
        sys.stdout = sys.__stdout__
        self.send_err_log()

        self.name_hdf5 = os.path.basename(pathname_hdf5)

        if self.model_type == 'SUBSTRATE' and 'CONST' in self.name_hdf5:
            if len(self.name_hdf5) > 25:  # careful this number should be changed if the form of the hdf5 name change
                self.name_hdf5 = self.name_hdf5[:-25]
            self.hname2.setText(self.name_hdf5)
        else:
            if len(self.name_hdf5) > 25: # careful this number should be changed if the form of the hdf5 name change
                self.name_hdf5 = self.name_hdf5[:-25]
            self.hname.setText(self.name_hdf5)

    def show_dialog(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class. Based on the
        name of the chosen file, a name is proposed for the hdf5 file.

        :param i: a int for the case where there is more than one file to load
        """

        # find the filename based on user choice
        if len(self.pathfile) == 0: # case where no file was open before
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_prj)[0]
        elif i >= len(self.pathfile):
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathfile[0])[0]
        else:
            # why [0] : getOpenFilename return a tuple [0,1,2], we need only the filename
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathfile[i])[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            return
        else:
            filename = os.path.basename(filename_path)
            # check extension
            extension_i = self.extension[i]
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
                if len(filename) > 9:
                    self.name_hdf5 = 'Substrate_' + filename2[:9] + '_' + ext[1:]
                else:
                    self.name_hdf5 = 'Substrate_' + filename2 + '_' + ext[1:]
            else:
                if len(filename) > 9:
                    self.name_hdf5 = 'Hydro_'+self.model_type+'_'+filename2[:9]
                else:
                    self.name_hdf5 = 'Hydro_'+self.model_type+'_'+filename2

            self.hname.setText(self.name_hdf5)

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

    def save_xml(self, i=0, append_name = False):
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
        filename_path_file = os.path.join(self.pathfile[i], self.namefile[i])
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.end_log.emit('Error: The project is not saved. '
                              'Save the project in the General tab before saving hydrological data. \n')
        else:
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            # geo data
            child1 = root.find(".//"+self.model_type)
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

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Figure")
            if child is None:
                path_im = self.path_prj
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
        path_hdf5 is in the project folder in the folder 'fichier_hdf5'.
        """

        path_hdf5 = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Hdf5")
            if child is None:
                path_hdf5 = self.path_prj
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

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Input")
            if child is None:
                path_input = self.path_prj
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

    def read_attribute_xml(self, att_here):
        """
        A function to read the text of an attribute in the xml project file.

        :param att_here: the attribute name (string).
        """
        data = 'no_data'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
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
            if i == max_send-1:
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
        com= 0
        for l in range(0, len(data)):
            data[l] = data[l].strip()
            if len(data[l])>0:
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

    def send_data(self):
        """
        This function is call regularly by the methods which have a second thread (so moslty the function
        to load the hydrological data). To call this functin regularly, the variable self.timer of QTimer type is used.
        The variable self.timer is connected to this function in the initiation of SubHydroW() and so in the initation
        of all class which inherits from SubHydroW().

        This function just wait while the thread is alive. When it has terminated, it creates the figure and the error
        messages.
        """

        # when the loading is finished
        if not self.q.empty():
            # manage error
            self.timer.stop()
            self.mystdout = self.q.get()
            error = self.send_err_log(True)

            # enable to loading of another model
            self.load_b.setDisabled(False)

            # create the figure and show them
            if not error:
                self.create_image()
            else:
                self.send_log.emit(self.tr("Figures could not be shown because of a prior error \n"))

            if self.model_type == 'SUBSTRATE' or self.model_type == 'LAMMI':
                self.send_log.emit(self.tr("Merging of substrate and hydrological data finished."))
                self.drop_merge.emit()
            else:
                self.send_log.emit(self.tr("Loading of hydrological data finished."))
                # send a signal to the substrate tab so it can account for the new info
                self.drop_hydro.emit()

        if not self.p.is_alive() and self.q.empty():
            self.timer.stop()
            self.load_b.setDisabled(False)
            # if grid creation fails
            # if self.interpo_choice >= 1:
            #     self.send_log.emit(
            #         "Error: Grid creation failed. Try with the interpolation method 'Interpolation by block'")
            #     # add here the call to the interpolatin method 0 to automatize this correction. TO BE DONE.
            #     # if a new thread is created, join it to wait (The GUI would freeze,
            #     # but it will get too complicated otherwise)
            #     return
            # if self.interpo_choice == 0:
            #     self.send_log.emit(
            #         "Error: Grid creation failed. Try with the interpolation method 'Linear Interpolation'")
            #     return

    def recreate_image(self):
        """
        This function is used to recreate the images related to the grid and the hydrology. We do not call create_image
        directly as we might add other command here.
        """

        self.create_image(False)

    def create_image(self, save_fig=True):
        """
        This function is used to create the images related to the grid and the hydrology. it is called by send_data
        and recreate_image. This function exists because the two functions above have similar needs and that we do not
        copy too much codes.

        :param save_fig: a boolean to save the figure or not
        """

        path_im = self.find_path_im()
        path_hdf5 = self.find_path_hdf5()
        sys.stdout = self.mystdout = StringIO()
        # find hsf5 name (files where is hte data)
        if self.model_type == 'SUBSTRATE':
            name_hdf5 = load_hdf5.get_hdf5_name('MERGE', self.name_prj, self.path_prj)
            if self.model_type == 'SUBSTRATE':
                self.lm2.setText(name_hdf5)
        else:
            name_hdf5 = load_hdf5.get_hdf5_name(self.model_type, self.name_prj, self.path_prj)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        if name_hdf5:
            # load data
            [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t] = load_hdf5.load_hdf5_hyd(name_hdf5,
                                                                                                path_hdf5)
            if ikle_all_t == [[-99]]:
                self.send_log.emit('Error: No data found in hdf5 (from send_data)')
                return
            # figure option
            self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
            if not save_fig:
                self.fig_opt['format'] = 123456  # random number  but should be bigger than number of format
            # plot the figure for all time step
            if self.fig_opt['time_step'][0] == -99:  # all time steps
                for t in range(1, len(ikle_all_t)):  # do not plot full profile
                    if t < len(ikle_all_t):
                        if self.model_type == 'SUBSTRATE' or self.model_type == 'LAMMI':
                            manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt,
                                                           inter_vel_all_t[t], inter_h_all_t[t], path_im, True, t)
                        else:
                            manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt,
                                                           inter_vel_all_t[t], inter_h_all_t[t], path_im, False, t)
            # plot the figure for some time steps
            else:
                for t in self.fig_opt['time_step']:  # range(0, len(vel_cell)):
                    # if print last and first time step and one time step only, only print it once
                    if t == -1 and len(ikle_all_t) == 2 and 1 in self.fig_opt['time_step']:
                        pass
                    else:
                        if t < len(ikle_all_t):
                            if self.model_type == 'SUBSTRATE' or self.model_type == 'LAMMI':
                                manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt,
                                                               inter_vel_all_t[t], inter_h_all_t[t], path_im, True, t)
                            else:
                                manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt,
                                                               inter_vel_all_t[t], inter_h_all_t[t], path_im, False, t)
                                # to debug
                                # manage_grid_8.plot_grid(point_all_reach, ikle_all, lim_by_reach,
                                # hole_all, overlap, point_c_all, inter_vel_all, inter_height_all, path_im)

            if self.model_type == 'SUBSTRATE':
                self.butfig2.setDisabled(False)
            else:
                self.butfig.setEnabled(True)
            self.show_fig.emit()
        else:
            self.send_log.emit('Error: The hydrological model is not found. \n')



class HEC_RAS1D(SubHydroW):
    """
   The class Hec_ras 1D is there to manage the link between the graphical interface and the functions in
   src/hec_ras06.py which loads the hec-ras data in 1D. The class HEC_RAS1D inherits from SubHydroW() so it have all
   the methods and the variables from the class ubHydroW(). The class hec-ras 1D is added to the self.stack of Hydro2W().
   So the class Hec-Ras 1D is called when the user is on the hydrological tab and click on hec-ras1D as hydrological
   model.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__(path_prj, name_prj)
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
        self.model_type = 'HECRAS1D'
        self.extension = [['.g01', '.g02', '.g03', '.g04','.g05 ', '.g06', '.g07', '.g08',
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
        self.geo_b = QPushButton('Choose file (.g0x)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)

        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.xml, .sdf, or .rep file)', self)
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
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit('')
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_hec_ras_gui)
        self.butfig = QPushButton(self.tr("Create figure again"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)
        self.spacer1 = QSpacerItem(1, 30)
        self.spacer2 = QSpacerItem(1, 80)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
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
        self.layout_hec.addWidget(lh,8,0)
        self.layout_hec.addWidget(self.hname, 8, 1)
        self.layout_hec.addWidget(self.load_b, 8, 3)
        self.layout_hec.addWidget(self.butfig, 9, 3)
        self.layout_hec.addItem(self.spacer2, 10, 1)
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
        self.load_b.setDisabled(True)

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)

        # for error management and figures (when time finsiehed call the self.send_data function)
        self.timer.start(1000)

        # get the image and load option
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.load_b.setDisabled(True)
        self.name_hdf5 = self.hname.text()
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        if self.fig_opt['raw_data'] == 'True':  # from the xml
            show_all_fig = True
        else:
            show_all_fig = False
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
        self.p = Process(target=Hec_ras06.open_hec_hec_ras_and_create_grid, args=(self.name_hdf5, path_hdf5,
                                                                                  self.name_prj,self.path_prj,
                                                                                  self.model_type, self.namefile,
                                                                                  self.pathfile, self.interpo_choice,
                                                                                  path_im, show_all_fig,
                                                                                  self.pro_add, self.q, False,
                                                                                  self.fig_opt))
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
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
        self.send_log.emit("py    interp=" + str(self.interpo_choice) )
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

            for ev in range(0,3):
                if ev == 0: # version 1 from hec-ras
                    for i in range(0, 10):  # max O09.xml is ok
                        new_name = blob[:-len(self.extension[0][0])] + '.O0' + str(i) + self.extension[1][0]
                        pathfilename = os.path.join(self.pathfile[0], new_name)
                        if os.path.isfile(pathfilename):
                            self.out_t2.setText(new_name)
                            # keep the name in an attribute until we save it
                            self.pathfile[1] = self.pathfile[0]
                            self.namefile[1] = new_name
                            break
                else: # version 4 from hec-ras
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
    The class Rubar2D is there to manage the link between the graphical interface and the functions in src/rubar.py
    which loads the RUBAR data in 2D. It inherits from SubHydroW() so it have all the methods and the variables from
    the class SubHydroW(). The form of the function is similar to hec-ras, but it does not have the part about the grid
    creation as we look here as the data created in 2D by RUBAR.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        used by ___init__() in the initialization.
        """

        # update attibute for rubar 2d
        self.attributexml = ['rubar_geodata', 'tpsdata']
        self.model_type = 'RUBAR2D'
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
        self.geo_b = QPushButton('Choose file (.mai, .dat)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)
        self.geo_b.clicked.connect(lambda: self.geo_t2.setToolTip(self.pathfile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.tps)', self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))
        self.out_b.clicked.connect(lambda: self.out_t2.setToolTip(self.pathfile[1]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_rubar)
        self.spacer = QSpacerItem(1, 200)
        self.butfig = QPushButton(self.tr("Create figure again"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
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
        self.layout_hec.addItem(self.spacer, 5, 1)
        self.setLayout(self.layout_hec)

    def load_rubar(self):
        """
        A function to execture the loading and saving the the rubar file using rubar.py. It is similar to the
        load_hec_ras_gui() function. Obviously, it calls rubar and not hec_ras this time. A small difference is that
        the rubar2D outputs are only given in one grid for all time steps and all reaches. Moreover, it is
        necessary to cut the grid for each time step as a function of the wetted area and maybe to separate the
        grid by reaches.  Another problem is that the data of Rubar2D is given on the cells of the grid and not the
        nodes. So we use linear interpolation to correct for this.

        A second thread is used to avoid "freezing" the GUI.

        """
        # for error management and figures
        self.timer.start(1000)

        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        self.load_b.setDisabled(True)
        # the path where to save the image
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # load rubar 2d data, interpolate to node, create grid and save in hdf5 format
        self.q = Queue()
        self.p = Process(target=rubar.load_rubar2d_and_create_grid, args=(self.name_hdf5,self.namefile[0], self.namefile[1],
                                self.pathfile[0], self.pathfile[1], path_im, self.name_prj,
                                self.path_prj, self.model_type, self.nb_dim, path_hdf5, self.q))
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: Rubar 2D data...'))
        #self.send_err_log()
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
    The class Mascaret is there to manage the link between the graphical interface and the functions in src/mascaret.py
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
        super().__init__(path_prj, name_prj)
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
        self.gen_b = QPushButton('Choose file (.xcas, .cas)', self)
        self.gen_b.clicked.connect(lambda: self.show_dialog(0))
        self.gen_b.clicked.connect(lambda: self.gen_t2.setText(self.namefile[0]))
        self.gen_b.clicked.connect(self.propose_next_file)
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.geo)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(1))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[1]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.opt, .rub)', self)
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
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_mascaret_gui)
        spacer = QSpacerItem(1, 30)
        self.butfig = QPushButton(self.tr("Create figure again"))
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
        self.layout.addItem(spacer, 10, 1)
        self.setLayout(self.layout)

    def load_mascaret_gui(self):
        """
        The function is used to load the mascaret data, calling the function contained in the script mascaret.py.
        It also create a 2D grid from the 1D data and distribute the velocity.
        All of theses tasks are done on a second thread to avoid freezing the GUI.
        """

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
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        if self.fig_opt['raw_data'] == 'True':  # from the xml
            show_all_fig = True
        else:
            show_all_fig = False
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
        # for error management and figures (when time finsiehed call the self.send_data function)
        self.timer.start(1000)
        self.p = Process(target=mascaret.load_mascaret_and_create_grid, args=(self.name_hdf5, path_hdf5,self.name_prj,
                                                                              self.path_prj,self.model_type, self.namefile,
                                                                              self.pathfile, self.interpo_choice,
                                                                              self.manning_arr, self.np_point_vel,
                                                                              show_all_fig,self.pro_add, self.q,
                                                                              path_im))
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
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
            self.send_log.emit("py    manning1 = " + str(self.manning_text.text()))  # to be corrected to include text result
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
            blob = np.array2string(self.manning_arr, separator=',',)
            blob = blob.replace('\n','')
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
        super().__init__(path_prj, name_prj)
        self.mystdout = None
        self.init_iu()

    def init_iu(self):
        """
        used by __init__ in the initialization
        """
        # update attibute for rubbar 2d
        self.attributexml = ['river2d_data']
        self.model_type = 'RIVER2D'
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
        self.butfig = QPushButton(self.tr("Create figure again"))
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
        self.load_b = QPushButton(self.tr("Load all files and create hdf5"))
        self.load_b.clicked.connect(self.load_river2d_gui)

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
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
        self.layout.addItem(spacer, 7, 0)
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

        for i in range(len(int_ind)-1, -1, -1):
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

        if len(self.pathfile) == 0: # no file opened before
            filename_path = QFileDialog.getOpenFileNames(self, 'Open File', self.path_prj)[0]
        else:
            filename_path = QFileDialog.getOpenFileNames(self, 'Open File', self.pathfile[0])[0]
        if not filename_path: #cancel case
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
        dirlsit0 = dirlist[0]
        listcdf = [e for e in dirlist if e[-4:] == self.extension[0][0]]
        # add them to name file, path file and extension
        self.namefile = self.namefile + listcdf
        self.pathfile = self.pathfile + [dir_name] * len(listcdf)
        # update list
        self.add_file_to_list()
        # add proposed hdf5 name to the QLineEdit
        filename2, ext = os.path.splitext(self.namefile[0])
        if len(self.namefile[0]) > 9:
            self.name_hdf5 = 'Hydro_' + self.model_type + '_' + filename2[:9]
        else:
            self.name_hdf5 = 'Hydro_' + self.model_type + '_' + filename2

        # self.hname.setAlignment(Qt.AlignRight)
        self.hname.setText(self.name_hdf5)

    def load_river2d_gui(self):
        """
        This function is used to load the river 2d data. It use a second thread to avoid freezing the GUI
        """
        # for error management and figures
        self.timer.start(1000)
        self.load_b.setDisabled(True)

        path_hdf5 = self.find_path_hdf5()

        if len(self.namefile) == 0:
            self.send_log.emit("Warning: No file chosen.")
            return

        for i in range(0, len(self.namefile)):
            # save each name in the project file, empty list on i == 0
            if i == 0:
                self.save_xml(i, False)
            else:
                self.save_xml(i, True)

        self.q = Queue()
        self.p = Process(target=river2d.load_river2d_and_cut_grid, args=(self.name_hdf5,self.namefile, self.pathfile,
                                self.name_prj, self.path_prj, self.model_type, self.nb_dim, path_hdf5, self.q))
        self.p.start()

        # copy input file
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
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
    The class Rubar1D is there to manage the link between the graphical interface and the functions in src/rubar.py
    which loads the Rubar1D data in 1D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to Mascaret class.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__(path_prj, name_prj)
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
        # no useful extension in this case, rbe is assumed
        # the function propose_next_file() uses the fact that .rbe is 4 char
        self.extension = [[''], ['']]
        self.nb_dim = 1

        # if there is the project file with rubar geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # label with the file name
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.rbe)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(self.propose_next_file)
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (profil.X)', self)
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
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_rubar1d)
        self.spacer1 = QSpacerItem(100, 100)
        self.butfig = QPushButton(self.tr("Create figure again"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
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
        self.layout_hec.addItem(self.spacer1, 9, 1)
        self.setLayout(self.layout_hec)

    def load_rubar1d(self):
        """
        A function to execute the loading and saving the the rubar file using rubar.py. After loading the data,
        it distribute the velocity along the profiles by calling self.distribute_velocity() and it created the 2D grid
        by calling the method self.grid_and_interpo.
        """
        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)

        # get the image and load option
        path_im = self.find_path_im()
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.load_b.setDisabled(True)
        self.name_hdf5 = self.hname.text()
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        if self.fig_opt['raw_data'] == 'True':  # xml, string
            show_all_fig = True
        else:
            show_all_fig = False
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
        # for error management and figures (when time finished call the self.send_data function)
        self.timer.start(1000)
        self.p = Process(target=rubar.load_rubar1d_and_create_grid, args=(self.name_hdf5, path_hdf5, self.name_prj,
                                                                        self.path_prj, self.model_type, self.namefile,
                                                                        self.pathfile, self.interpo_choice,
                                                                        self.manning_arr, self.np_point_vel,
                                                                        show_all_fig, self.pro_add, self.q, path_im))
        self.p.start()

        # path input
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
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
            blob = np.array2string(self.manning_arr, separator=',',)
            blob = blob.replace('\n','')
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
    The class hec_RAS2D is there to manage the link between the graphical interface and the functions in src/hec_ras2D.py
    which loads the hec_ras2D data in 2D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class and it has the same problem about node/cell
    which will need to be corrected.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        This method is used to by __init__() during the initialization.
        """

        # update attibutes
        self.attributexml = ['data2D']
        self.model_type = 'HECRAS2D'
        self.extension = [['.hdf']]
        self.nb_dim =2

        # if there is the project file with hecras info, update the label and attibutes
        self.was_model_loaded_before()
        self.h2d_t2 = QLabel(self.namefile[0], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry and output data </b>'))
        self.h2d_b = QPushButton('Choose file (.hdf, .h5)', self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog(0))
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setText(self.namefile[0]))
        l2 = QLabel(self.tr('<b> Options </b>'))
        l3 = QLabel('All time step', self)
        l4 = QLabel('All flow area', self)

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # ToolTip to indicated in which folder are the files
        self.h2d_t2.setToolTip(self.pathfile[0])
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setToolTip(self.pathfile[0]))

        # hdf5 name
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_hec_2d_gui)
        self.spacer = QSpacerItem(1, 200)
        self.butfig = QPushButton(self.tr("Create figure again"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2, 0 , 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(l2, 1, 0)
        self.layout_hec2.addWidget(l3, 1, 1)
        self.layout_hec2.addWidget(l4, 1, 2)
        self.layout_hec2.addWidget(l2D1, 2, 0)
        self.layout_hec2.addWidget(l2D2, 2, 1, 1, 2)
        self.layout_hec2.addWidget(lh, 3, 0)
        self.layout_hec2.addWidget(self.hname, 3, 1)
        self.layout_hec2.addWidget(self.load_b, 4, 2)
        self.layout_hec2.addWidget(self.butfig, 5, 2)
        self.layout_hec2.addItem(self.spacer, 6, 1)
        self.setLayout(self.layout_hec2)

    def load_hec_2d_gui(self):
        """
        This function calls the function which load hecras 2d and save the names of file in the project file.
        It is similar to the function to load_rubar2D. It open a second thread to avoid freezing the GUI.

        When this function starts, it also starts a timer. Every three seconds, the timer run the function send_data()
        which is the class SubHydroW(). This function checks if the thread is finished and, it is finished, manage
        figure and errors.
        """
        # save the name of the file in the xml project file
        self.save_xml(0)
        self.load_b.setDisabled(True)

        # for error management and figures
        self.timer.start(1000)

        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # load the hec_ras data and cut the grid to the needed side
        self.q = Queue()
        self.p = Process(target=hec_ras2D.load_hec_ras_2d_and_cut_grid, args=(self.name_hdf5,self.namefile[0], self.pathfile[0],
                                     self.name_prj, self.path_prj, self.model_type, self.nb_dim, path_hdf5, self.q))
        self.p.start()

        # path input
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=([self.namefile[0]], [self.pathfile[0]], path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: HEC-RAS 2D...'))
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    interpo=" + str(self.interpo_choice) )
        self.send_log.emit("py    pro_add=" + str(self.pro_add) )
        self.send_log.emit("py    hec_ras2D.load_hec_ras_2d_and_cut_grid('HEC_RAS2D_log', file1, path1, name_prj, "
                           "path_prj, 'HECRAS2D',2, path_prj, [], True)\n")
        self.send_log.emit("restart LOAD_HECRAS_2D")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))


class TELEMAC(SubHydroW):
    """
    The class Telemac is there to manage the link between the graphical interface and the functions in src/selafin_habby1.py
    which loads the Telemac data in 2D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class, but data from Telemac is on the node as in HABBY.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        Used by __init__() during the initialization.
        """

        # update the attibutes
        self.attributexml = ['telemac_data']
        self.model_type = 'TELEMAC'
        self.extension = [['.res', '.slf']]
        self.nb_dim = 2

        # if there is the project file with telemac info, update the label and attibutes
        self.was_model_loaded_before()
        self.h2d_t2 = QLabel(self.namefile[0], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry and output data </b>'))
        self.h2d_b = QPushButton('Choose file (.slf, .res)', self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog(0))
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setText(self.namefile[0]))
        l2 = QLabel(self.tr('<b> Options </b>'))
        l3 = QLabel('All time steps', self)

        # ToolTip to indicated in which folder are the files
        self.h2d_t2.setToolTip(self.pathfile[0])
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setToolTip(self.pathfile[0]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # hdf5 name
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_telemac_gui)
        self.spacer = QSpacerItem(1, 180)
        self.butfig = QPushButton(self.tr("Create figure again"))
        self.butfig.clicked.connect(self.recreate_image)
        if self.namefile[0] == 'unknown file':
            self.butfig.setDisabled(True)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2, 0, 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(l2, 1, 0)
        self.layout_hec2.addWidget(l3, 1, 1)
        self.layout_hec2.addWidget(l2D1, 2, 0)
        self.layout_hec2.addWidget(l2D2, 2, 1, 1, 2)
        self.layout_hec2.addWidget(lh, 3, 0)
        self.layout_hec2.addWidget(self.hname, 3, 1)
        self.layout_hec2.addWidget(self.load_b, 4, 2)
        self.layout_hec2.addWidget(self.butfig, 5, 2)
        self.layout_hec2.addItem(self.spacer, 6, 1)
        self.setLayout(self.layout_hec2)

    def load_telemac_gui(self):
        """
        The function which call the function which load telemac and save the name of files in the project file
        """
        # for error management and figures
        self.timer.start(1000)
        # write the new file name in the project file
        self.save_xml(0)
        self.load_b.setDisabled(True)
        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()

        # load the telemac data
        self.q = Queue()
        self.p = Process(target=selafin_habby1.load_telemac_and_cut_grid, args=(self.name_hdf5, self.namefile[0],self.pathfile[0],
                                          self.name_prj,self.path_prj, self.model_type, self.nb_dim, path_hdf5, self.q))
        self.p.start()

        # path input
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
        self.p2.start()

        # log info
        self.send_log.emit(self.tr('# Loading: TELEMAC data...'))
        self.send_err_log()
        self.send_log.emit("py    file1=r'" + self.namefile[0] + "'")
        self.send_log.emit("py    path1=r'" + path_input + "'")
        self.send_log.emit("py    selafin_habby1.load_telemac_and_cut_grid('hydro_telemac_log', file1, path1, name_prj, "
                           "path_prj, 'TELEMAC', 2, path_prj, [], True )\n")
        self.send_log.emit("restart LOAD_TELEMAC")
        self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))


class LAMMI(SubHydroW):
    """
    The class LAMMI is there to manage the link between the graphical interface and the functions in src/lammi.py
    which loads the lammi data. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW().
    """

    drop_merge = pyqtSignal()
    """
    A pyqtsignal which signal that hydro data from lammi is ready. The signal is for the bioinfo_tab and is collected
    by MainWindows1.py. Data from lammi contains substrate data.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)

        self.namefile = ['unknown file', 'unknown file', 'unknown file', 'unknown file']
        # the third path is the directory when the output files are found. Only useful, if the output files were moved
        self.pathfile = ['.', '.', '.', 'Directory from transect.txt']
        self.file_entree = ['Facies.txt', 'Transect.txt']
        self.attributexml = ['lammi_facies', 'lammi_transect', 'lammi_output']
        self.model_type = 'LAMMI'
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
        l2 =  QLabel(self.tr('<b> Output data </b>'))
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
        lh = QLabel(self.tr('<b> hdf5 file name </b>'))
        self.hname = QLineEdit(self.name_hdf5)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_lammi_gui)
        self.spacer = QSpacerItem(1, 150)
        self.butfig = QPushButton(self.tr("Create figure again"))
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
        self.layout_hec2.addItem(self.spacer, 7, 1)
        self.setLayout(self.layout_hec2)

    def show_dialog_lammi(self, i = 0):
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
            filenames = load_hdf5.get_all_filename(dir_name, '.prn')
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

        # for error management and figures
        self.timer.start(1000)

        # write the new file name in the project file
        self.save_xml(0)
        self.save_xml(1)
        self.save_xml(2)
        self.load_b.setDisabled(True)

        # the path where to save the hdf5
        path_hdf5 = self.find_path_hdf5()
        self.name_hdf5 = self.hname.text()
        # get the image and load option
        path_im = self.find_path_im()
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        if self.fig_opt['raw_data'] == 'True':  # saved before in the xml file!
            show_all_fig = True
        else:
            show_all_fig = False

        if not os.path.isdir(self.pathfile[2]):
            self.pathfile[2] = []

        # load the lammi data
        self.q = Queue()
        self.p = Process(target=lammi.open_lammi_and_create_grid,
                         args=(self.pathfile[0], self.pathfile[1], path_im, self.name_hdf5, self.name_prj, self.path_prj
                               , path_hdf5, self.pathfile[2], self.fig_opt, show_all_fig,  self.namefile[1],
                               self.namefile[0], False, self.q, 1, self.model_type))
        self.p.start()

        # path input
        path_input = self.find_path_input()
        self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
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


class HabbyHdf5(SubHydroW):
    """
    This class is used to load hdf5 hydrological file done by HABBY on another project. If the project was lost,
    it is there possible to just add a along hdf5 file to the current project without having to pass to the original
    hydrological files.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.model_type = 'Imported_hydro'
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        l0 = QLabel(self.tr('Select the hdf5 created by HABBY to be loaded:'))
        self.button2 = QPushButton(self.tr('Load data from hdf5'))
        self.button2.clicked.connect(self.get_new_hydro_hdf5)
        spacer1 = QSpacerItem(200, 1)
        spacer2 = QSpacerItem(1, 300)

        self.layout2 = QGridLayout()
        self.layout2.addWidget(l0, 0, 0)
        self.layout2.addWidget(self.button2, 0, 1)
        self.layout2.addItem(spacer1, 0, 2)
        self.layout2.addItem(spacer2, 2, 0)
        self.setLayout(self.layout2)

    def get_new_hydro_hdf5(self):
        """
        This is a function which allows the user to select an hdf5 file containing the hydrological
        data from a previous project and add it to the current project. It modifies the xml project file and test
        that the data is in correct form by loading it. The hdf5 should have the same form than the hydrological data
        created by HABBY in the method save_hdf5 of the class SubHydroW.
        """

        self.send_log.emit('# Loading: HABBY hdf5 file (hydrological data only)...')
        # prep
        ikle_all_t = []
        point_all = []
        inter_vel_all = []
        inter_height_all = []
        # select a file
        fname_h5 = QFileDialog.getOpenFileName()[0]
        if fname_h5 != '':  # cancel
            blob, ext = os.path.splitext(fname_h5)
        else:
            self.send_log.emit('Warning: No file selected.\n')
            return
        # load the data to check integrity
        [ikle_all_t, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(fname_h5)

        # copy the file and update the attribute
        path_hdf5 = self.find_path_hdf5()
        path_input = self.find_path_input()
        if os.path.isdir(path_hdf5):
            new_name = 'COPY_' + os.path.basename(fname_h5)
            pathnewname = os.path.join(path_hdf5, new_name)
            shutil.copyfile(fname_h5, pathnewname)
            # necessary for the restart function
            pathnewname2 = os.path.join(path_input, new_name)
            shutil.copyfile(fname_h5, pathnewname2)
        else:
            self.send_log.emit('Error: the path to the project is not found. Is the project saved in the general tab?')
            return
        try:
            file_hydro2 = h5py.File(pathnewname, 'r+')
        except OSError:
            self.send_log.emit('Error: The hdf5 file could not be loaded. \n')
        file_hydro2.attrs['path_projet'] = self.path_prj
        file_hydro2.attrs['name_projet'] = self.name_prj
        # save the new file name in the xml file of the project
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
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
                hdf5file = ET.SubElement(here_element, "hdf5_hydrodata")
                hdf5file.text = new_name
            else:
                hdf5file = ET.SubElement(child, "hdf5_hydrodata")
                hdf5file.text = new_name

            doc.write(filename_prj)
        self.send_log.emit('# hdf5 file loaded to the current project.')
        self.send_log.emit("py    import shutil")
        self.send_log.emit("py    fname_h5 ='" + fname_h5 + "'")
        self.send_log.emit("py    new_name = os.path.join(path_prj, 'COPY_' + os.path.basename(fname_h5))")
        self.send_log.emit("py    shutil.copyfile(fname_h5, new_name)")
        self.send_log.emit('restart LOAD_HYDRO_HDF5')
        self.send_log.emit('restart    file hdf5: ' + pathnewname2)
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
        super().__init__(path_prj, name_prj)
        # update attribute
        self.attributexml = ['substrate_data', 'att_name']
        self.model_type = 'SUBSTRATE'
        self.extension = [['.txt', '.shp', '.asc']]
        self.name_att = ''
        self.coord_p = []
        self.ikle_sub = []
        self.sub_info = []
        self.hyd_name = []
        self.max_lengthshow = 90  # the maximum length of a file name to be show in full
        self.nb_dim = 10  # just to ckeck
        self.hname2 = QLineEdit('Sub_CONST')
        # order and name matters here!
        # change with caution!
        # roughness height if ok with George
        self.all_code_type = ['Cemagref', 'Sandre']

        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__().
        """

        # to load substrate data from file
        l1 = QLabel(self.tr('<b> Load substrate data </b>'))
        l2 = QLabel(self.tr('File'))
        lh = QLabel(self.tr('hdf5 file name'))
        l11 = QLabel(self.tr('Default substrate value:'))
        l3 = QLabel(self.tr('Code Substrate'))
        self.e2 = QComboBox()
        self.e2.addItems(self.all_code_type)
        self.e3 = QLineEdit('1')  # default substrate value
        self.hname = QLineEdit('')  # hdf5 name
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # choose file button
        self.h2d_b = QPushButton('Choose file (.txt, .shp)', self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog(0))
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setToolTip(self.pathfile[0]))
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setText(self.namefile[0]))

        # if there was substrate info before, update the label and attibutes
        self.was_model_loaded_before()
        self.get_att_name()
        self.h2d_t2 = QLabel(self.namefile[0], self)
        self.h2d_t2.setToolTip(self.pathfile[0])

        # the load button from file
        self.load_b = QPushButton(self.tr('Load data and create hdf5'), self)
        self.load_b.clicked.connect(self.load_sub_gui)
        self.butfig1 = QPushButton(self.tr("Create figure again"))
        self.butfig1.clicked.connect(self.recreate_image_sub)
        if self.namefile[0] == 'unknown file':
            self.butfig1.setDisabled(True)

        # to load constant substrate
        self.l4 = QLabel(self.tr('<b> Load constant substrate </b>'))
        l12 = QLabel(self.tr('Constant substrate value'))
        self.e1 = QLineEdit('1')  # constant substrate value
        l13 = QLabel(self.tr('(Code type: Cemagref)'))
        lh2 = QLabel(self.tr('hdf5 file name'))
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.gethdf5_name_gui()

        # the load button for constant substrate
        self.load_const = QPushButton(self.tr('Load const. data and create hdf5'), self)
        self.load_const.clicked.connect(lambda: self.load_sub_gui(True))

        # label and button for the part to merge the grid
        l8 = QLabel(self.tr("<b> Merge the hydrological and substrate grid </b>"))
        l9 = QLabel(self.tr("Hydrological data (hdf5)"))
        l10 = QLabel(self.tr("Substrate data (hdf5)"))
        self.drop_hyd = QComboBox()
        self.drop_sub = QComboBox()
        self.load_b2 = QPushButton(self.tr("Merge grid and create hdf5"), self)
        self.load_b2.clicked.connect(self.send_merge_grid)
        self.spacer2 = QSpacerItem(1, 10)
        self.butfig2 = QPushButton(self.tr("Create figure again"))
        self.butfig2.clicked.connect(self.recreate_image)
        # get possible substrate from the project file
        self.update_sub_hdf5_name()
        # get the last file created
        lm1 = QLabel(self.tr('Last file created'))
        self.lm2 = QLabel(self.tr('No file'))
        self.name_last_merge()  # find the name of the last merge file and add it to self.lm2
        if self.lm2.text() == self.tr('No file'):
            self.butfig2.setDisabled(True)

        # layout
        self.layout_sub = QGridLayout()
        self.layout_sub.addWidget(l1, 0, 0)
        self.layout_sub.addWidget(l2, 1, 0)
        self.layout_sub.addWidget(self.h2d_t2, 1, 1)
        self.layout_sub.addWidget(self.h2d_b, 1, 2)
        self.layout_sub.addWidget(l3, 2, 0)
        self.layout_sub.addWidget(self.e2, 2, 1)
        self.layout_sub.addWidget(l11, 3, 0)
        self.layout_sub.addWidget(self.e3, 3, 1)
        self.layout_sub.addWidget(lh, 4, 0)
        self.layout_sub.addWidget(self.hname, 4, 1)
        self.layout_sub.addWidget(self.load_b, 5, 2)
        self.layout_sub.addWidget(self.butfig1, 5, 3)

        self.layout_sub.addWidget(self.l4, 6, 0, 1, 2)
        self.layout_sub.addWidget(l12, 7, 0)
        self.layout_sub.addWidget(self.e1, 7, 1)
        self.layout_sub.addWidget(l13, 7, 2)
        self.layout_sub.addWidget(lh2, 8, 0)
        self.layout_sub.addWidget(self.hname2, 8, 1)
        self.layout_sub.addWidget(self.load_const, 9, 2)

        self.layout_sub.addWidget(l8, 10, 0, 1, 2)
        self.layout_sub.addWidget(l9, 11, 0)
        self.layout_sub.addWidget(self.drop_hyd, 11, 1)
        self.layout_sub.addWidget(l10, 12, 0)
        self.layout_sub.addWidget(self.drop_sub, 12, 1)
        self.layout_sub.addWidget(self.load_b2, 14, 2)
        self.layout_sub.addWidget(self.butfig2, 14, 3)
        self.layout_sub.addWidget(lm1, 13, 0)
        self.layout_sub.addWidget(self.lm2, 13, 1)
        self.layout_sub.addItem(self.spacer2, 11, 1)

        self.setLayout(self.layout_sub)

    def name_last_merge(self):
        """
        This function opens the xml project file to find the name of the last hdf5 merge file and to add it
        to the GUI on the QLabel self.lm2. If there is no file found, this functiion do nothing.
        """
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.end_log.emit('Error: The project is not saved. '
                              'Save the project in the General tab before saving hydrological data. \n')
        else:
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            # geo data
            child1 = root.findall(".//SUBSTRATE/hdf5_mergedata")
            if child1 is not None:
                mergename = child1[-1].text
                self.lm2.setText(mergename)

    def load_sub_gui(self, const_sub=False):
        """
        This function is used to load the substrate data. The substrate data can be in two forms: a) in the form of a shp
        file form ArGIS (or another GIS-program). b) in the form of a text file (x,y, substrate data line by line).
        Generally this function has some similarities to the functions used to load the hydrological data and it re-uses
        some of the methods developed for them.

        It is possible to have a constant substrate if const_sub= True. In this
        case, an hdf5 is created with only the default value marked. This form of hdf5 file is then managed by the merge
        function.

        :param const_sub: If True, a constant substrate is being loaded. Usually it is set to False.

        """
        self.send_log.emit(self.tr('# Loading: Substrate data...'))
        self.load_b.setDisabled(True)
        if const_sub:
            if self.namefile[0] != 'unknown file':
                self.send_log.emit('Warning: Constant substrate data. Data from '+self.namefile[0] +
                                   ' not taken into account.')
            try:
                data_sub = int(self.e1.text())
            except ValueError:
                self.send_log.emit('The substrate data should be between 1 and 8')
                return
            if not 0 < data_sub <9:
                self.send_log.emit('The substrate data should be between 1 and 8')
            self.name_hdf5 = self.hname2.text()
            path_hdf5 = self.find_path_hdf5()
            sys.stdout = self.mystdout = StringIO()
            load_hdf5.save_hdf5_sub(path_hdf5, self.path_prj, self.name_prj, data_sub, data_sub, [], [],
                                    self.name_hdf5, True, self.model_type)
            sys.stdout = sys.__stdout__
            self.send_err_log()
            path_im = self.find_path_im()  #needed

            # log info
            self.send_log.emit(self.tr('# Substrate data type: constant value'))
            self.send_log.emit("py    val_c=" + str(data_sub))
            self.send_log.emit(
                "py    load_hdf5.save_hdf5_sub(path_prj, path_prj, name_prj, val_c, val_c, [], [], 're_run_const_sub'"
                ", True, 'SUBSTRATE') \n")
            self.send_log.emit("restart LOAD_SUB_CONST")
            self.send_log.emit("restart    val_c: " + str(data_sub))
        else:
            # save path and name substrate
            self.save_xml(0)
            namebase, ext = os.path.splitext(self.namefile[0])
            path_im = self.find_path_im()
            code_type = self.e2.currentText()
            self.name_hdf5 = self.hname.text()

            self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)

            # if the substrate is in the shp form
            if ext == '.shp':

                # check if we have all files
                name1 = namebase + '.dbf'
                name2 = namebase + '.shx'
                pathname1 = os.path.join(self.pathfile[0], name1)
                pathname2 = os.path.join(self.pathfile[0], name2)
                if not os.path.isfile(pathname1) or not os.path.isfile(pathname2):
                    self.send_log.emit('Error: A shapefile is composed of three files: a .shp file, a .shx file, and'
                                       ' a .dbf file.')
                    self.load_b.setDisabled(False)
                    return

                # load substrate
                sys.stdout = self.mystdout = StringIO()
                [self.coord_p, self.ikle_sub, sub_dom, sub_pg, ok_dom] = substrate.load_sub_shp(self.namefile[0],
                                                                                  self.pathfile[0], code_type)
                # we have a case where two dominant substrate are "equally" dominant
                # so we ask the user to solve this for us
                dom_solve = 0
                if not ok_dom:
                    # in this case ask the user
                    self.msg2 = QMessageBox()
                    self.msg2.setWindowTitle(self.tr('Dominant substrate'))
                    self.msg2.setText(self.tr('Our analysis found that the dominant substrate of certain substrate'
                                              ' cells cannot be determined. Indeed, the maximum percentage of two or '
                                              'more classes are equal. In these cases, should we take the larger or the'
                                              ' smaller substrate class?'))
                    b1 = self.msg2.addButton(self.tr('Larger'), QMessageBox.NoRole)
                    b2 = self.msg2.addButton(self.tr('Smaller'), QMessageBox.YesRole)
                    self.msg2.exec()
                    if self.msg2.clickedButton() == b1:
                       dom_solve = 1
                    elif self.msg2.clickedButton() == b2:
                        dom_solve = -1
                    [self.coord_p, self.ikle_sub, sub_dom, sub_pg, ok_dom] = substrate.load_sub_shp(
                        self.namefile[0],self.pathfile[0], code_type, dom_solve)
                #sys.stdout = sys.__stdout__
                #self.send_err_log()

                if self.ikle_sub == [-99]:
                    self.send_log.emit('Error: Substrate data not loaded')
                    self.load_b.setDisabled(False)
                    return

                # copy shape file (compsed of .shp, .shx and .dbf)
                path_input = self.find_path_input()
                name_3 = [self.namefile[0], name1, name2]
                path_3 = [self.pathfile[0], self.pathfile[0], self.pathfile[0]]
                self.p2 = Process(target=load_hdf5.copy_files, args=(name_3, path_3, path_input))
                self.p2.start()

                # log info
                self.send_log.emit(self.tr('# Substrate data type: Shapefile'))
                self.send_log.emit("py    file1='" + self.namefile[0] + "'")
                self.send_log.emit("py    path1='" + path_input + "'")
                self.send_log.emit("py    type='" + code_type + "'")
                self.send_log.emit("py    [coord_p, ikle_sub, sub_dm, sub_pg, ok_dom] = substrate.load_sub_shp"
                                   "(file1, path1, type)\n")
                self.send_log.emit("restart LOAD_SUB_SHP")
                self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
                self.send_log.emit("restart    code_type: " + code_type)

            # if the substrate data is a text form
            elif ext == '.txt' or ext == ".asc":

                # load
                #sys.stdout = self.mystdout = StringIO()
                [self.coord_p, self.ikle_sub, sub_dom, sub_pg, x, y, sub1, sub2] = \
                    substrate.load_sub_txt(self.namefile[0], self.pathfile[0], code_type)
                #sys.stdout = sys.__stdout__
                self.send_err_log()

                if self.ikle_sub == [-99]:
                    self.send_log.emit('Error: Substrate data not loaded')
                    self.load_b.setDisabled(False)
                    return

                # copy
                path_input = self.find_path_input()
                self.p2 = Process(target=load_hdf5.copy_files, args=(self.namefile, self.pathfile, path_input))
                self.p2.start()

                # log info
                self.send_log.emit(self.tr('# Substrate data type: text file'))
                self.send_log.emit("py    file1='" + self.namefile[0] + "'")
                self.send_log.emit("py    path1=r'" + path_input + "'")
                self.send_log.emit("py    type='" + code_type + "'")
                self.send_log.emit(
                    "py    [coord_pt, ikle_subt, sub_dom2, sub_pg2, x, y, sub_dom, sub_pg] = substrate.load_sub_txt("
                    "file1, path1, type)\n")
                self.send_log.emit("restart LOAD_SUB_TXT")
                self.send_log.emit("restart    file1: " + os.path.join(path_input, self.namefile[0]))
                self.send_log.emit("restart    code_type: " + code_type)

            # case unknown
            else:
                self.send_log.emit("Error: Unknown extension for substrate data. The data was not loaded. Only file "
                                   "with .txt, .asc ,or .shp are accepted.")
                self.load_b.setDisabled(False)
                return

            # save shp and txt in the substrate hdf5
            path_hdf5 = self.find_path_hdf5()
            load_hdf5.save_hdf5_sub(path_hdf5, self.path_prj, self.name_prj, sub_pg, sub_dom, self.ikle_sub,
                                    self.coord_p, self.name_hdf5, False, self.model_type)

            # show image
            self.recreate_image_sub(True)

        # add the name of the hdf5 to the drop down menu so we can use it to merge with hydrological data
        self.update_sub_hdf5_name()

        self.butfig1.setEnabled(True)
        self.load_b.setDisabled(False)

        self.send_log.emit('Loading of substrate data finished \n')

    def recreate_image_sub(self, save_fig = False):
        """
        This function is used to recreate the image linked with the subtrate. So this is not the figure for the "merge"
        part, but only to show the substrat alone.

        :param: save_fig: A boolean to save or not the figure
        """
        path_im = self.find_path_im()

        # getting the subtrate data
        path_hdf5 = self.find_path_hdf5()
        sub_name = self.read_attribute_xml('hdf5_substrate')
        sub_name = sub_name.split(',')
        i = 0
        const = True
        while const and i < len(sub_name):
            s = sub_name[-1-i]
            [ikle_sub, point_all_sub, sub_pg, sub_dom, const] = load_hdf5.load_hdf5_sub(s, path_hdf5, True)
            i +=1

        if not ikle_sub:
            self.send_log.emit('Error: No connectivity table found. \n')
            return

        # plot it
        self.fig_opt = output_fig_GUI.load_fig_option(self.path_prj, self.name_prj)
        if not save_fig:
            self.fig_opt['format'] = 40000  # should be a higher int than the numner of format
        substrate.fig_substrate(point_all_sub, ikle_sub, sub_pg, sub_dom, path_im, self.fig_opt)
        # show figure
        if path_im != 'no_path':
            self.show_fig.emit()

    def update_sub_hdf5_name(self):
        """
        This function update the QComBox on substrate data which is on the substrate tab. The similiar function
        for hydrology is in Main_Windows_1.py as it is more practical to have it there to collect all the signals.
        """
        path_hdf5 = self.find_path_hdf5()
        self.sub_name = self.read_attribute_xml('hdf5_substrate')
        self.sub_name = self.sub_name.split(',')
        sub_name2 = []  # we might have unexisting hdf5 file in the xml project file
        for i in range(0, len(self.sub_name)):
            if os.path.isfile(self.sub_name[i]):
                sub_name2.append(self.sub_name[i])
            if os.path.isfile(os.path.join(path_hdf5, self.sub_name[i])):
                sub_name2.append(self.sub_name[i])
        self.sub_name = sub_name2
        self.drop_sub.clear()
        for i in range(0, len(self.sub_name)):
            if i == 0 and len(self.sub_name) > 1:
                self.drop_sub.addItem(' ')
            if len(self.sub_name[i])> self.max_lengthshow:
                self.drop_sub.addItem(os.path.basename(self.sub_name[i][:self.max_lengthshow]))
            else:
                self.drop_sub.addItem(os.path.basename(self.sub_name[i]))

    def get_attribute_from_shp(self):
        """
        This function opens a shapefile and obtain the attribute. It then update the GUI
        to reflect this and also update the label as needed.
        """

        lob, ext = os.path.splitext(self.namefile[0])
        if ext == '.shp':
            self.e2.clear()
            att_list = substrate.get_all_attribute(self.namefile[0], self.pathfile[0])  # list of attribute with info []
            for i in range(0, len(att_list)):
                self.e2.addItem(str(att_list[i][0]))
            self.e2.setEnabled(True)
        else:
            self.e2.setDisabled(True)
            self.e2.clear()

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

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
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
        This function calls the function merge grid in substrate.py. The goal is to have the substrate and hydrological
        data on the same grid. Hence, the hydrological grid will need to be cut to the form of the substrate grid.

        This function can be slow so it call on a second thread.
        """
        self.send_log.emit('# Merging: substrate and hydrological grid...')

        # get usfule data
        if len(self.drop_hyd) >1:
            hdf5_name_hyd = self.hyd_name[self.drop_hyd.currentIndex()-1]
        else:
            hdf5_name_hyd = self.hyd_name[0]
        if len(self.drop_sub )>1:
            hdf5_name_sub = self.sub_name[self.drop_sub.currentIndex()-1]
        else:
            hdf5_name_sub = self.sub_name[0]
        default_data = self.e3.text()
        path_hdf5 = self.find_path_hdf5()
        path_im = self.find_path_im()

        # for error management and figures
        self.timer.start(1000)

        # run the function
        self.q = Queue()
        self.p = Process(target=mesh_grid2.merge_grid_and_save, args=(hdf5_name_hyd, hdf5_name_sub, path_hdf5,
                                                                     default_data, self.name_prj, self.path_prj,
                                                                     self.model_type, self.q))
        self.p.start()

        # log
        # functions if ind is zero also
        self.send_log.emit("py    file_hyd=r'" + self.hyd_name[self.drop_hyd.currentIndex()-1] + "'")
        self.send_log.emit("py    name_sub=r'" + self.sub_name[self.drop_sub.currentIndex()-1] + "'")
        self.send_log.emit("py    path_sub=r'" + path_hdf5 + "'")
        if len(self.e3.text()) > 0:
            self.send_log.emit("py    defval=" + self.e3.text())
        else:
            self.send_log.emit("py    defval=-99")
        self.send_log.emit("py    mesh_grid2.merge_grid_and_save(file_hyd,name_sub, path_sub, defval, name_prj, "
                           "path_prj, 'SUBSTRATE', [], True) \n")
        self.send_log.emit("restart MERGE_GRID_SUB")
        self.send_log.emit("restart    file_hyd: " + self.hyd_name[self.drop_hyd.currentIndex()-1])
        self.send_log.emit("restart    file_sub: " + os.path.join(self.path_prj,
                                                                  self.sub_name[self.drop_sub.currentIndex()-1]))
        if  len(self.e3.text()) > 0:
            self.send_log.emit("restart    defval: " + self.e3.text())
        else:
            self.send_log.emit("restart    defval: -99")

if __name__ == '__main__':
    pass







