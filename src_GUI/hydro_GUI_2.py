import os
import numpy as np
import sys
import shutil
from io import StringIO
from PyQt5.QtCore import QTranslator, pyqtSignal, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox
import h5py
import time
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import Hec_ras06
from src import hec_ras2D
from src import selafin_habby1
from src import substrate
from src import rubar
from src import river2d
from src import mascaret
from src import manage_grid_8
from src import dist_vistess2
from src import load_hdf5
np.set_printoptions(threshold=np.inf)
from multiprocessing import Process, Queue
#import matplotlib.pyplot as plt

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
        #self.mod_loaded = QComboBox()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_model = ["", "HEC-RAS 1D", "HEC-RAS 2D", "MASCARET", "RIVER2D", "RUBAR BE", "RUBAR 20", "TELEMAC"]  # "MAGE"
        self.mod_act = 0
        self.stack = QStackedWidget()
        self.msgi = QMessageBox()
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """
        # generic label
        #self.l1 = QLabel(self.tr('blob'))
        l2 = QLabel(self.tr('<b> LOAD NEW DATA </b>'))
        l3 = QLabel(self.tr('<b>Available hydrological models </b>'))

        # available model
        #self.mod_loaded.addItems([""])
        self.mod.addItems(self.name_model)
        self.mod.currentIndexChanged.connect(self.selectionchange)
        self.button1 = QPushButton(self.tr('Model Info'), self)
        self.button1.clicked.connect(self.give_info_model)
        self.button2 = QPushButton(self.tr('Load data from hdf5'))
        self.button2.clicked.connect(self.get_new_hydro_hdf5)
        spacer2 = QSpacerItem(50, 1)
        spacer = QSpacerItem(1, 50)

        # add the widgets representing the available models to a stack of widget
        self.free = FreeSpace()
        self.hecras1D = HEC_RAS1D(self.path_prj, self.name_prj)
        self.hecras2D = HEC_RAS2D(self.path_prj, self.name_prj)
        self.telemac = TELEMAC(self.path_prj, self.name_prj)
        self.rubar2d = Rubar2D(self.path_prj, self.name_prj)
        self.rubar1d = Rubar1D(self.path_prj, self.name_prj)
        self.mascar = Mascaret(self.path_prj, self.name_prj)
        self.riverhere2d = River2D(self.path_prj, self.name_prj)
        self.stack.addWidget(self.free)  # order matters in the next lines!
        self.stack.addWidget(self.hecras1D)
        self.stack.addWidget(self.hecras2D)
        self.stack.addWidget(self.mascar)
        self.stack.addWidget(self.riverhere2d)
        self.stack.addWidget(self.rubar1d)
        self.stack.addWidget(self.rubar2d)
        self.stack.addWidget(self.telemac)
        self.stack.setCurrentIndex(self.mod_act)

        # layout
        self.layout4 = QGridLayout()
        self.layout4.addWidget(l3, 0, 0)
        self.layout4.addWidget(self.mod, 1, 0)
        self.layout4.addItem(spacer2, 1, 1)
        self.layout4.addWidget(self.button1, 1, 2)
        self.layout4.addWidget(self.button2, 2, 2)
        self.layout4.addWidget(self.stack, 2, 0)
        #self.layout4.addWidget(self.l1, 3, 0)
        #self.layout4.addWidget(self.mod_loaded, 4, 0)
        self.layout4.addItem(spacer, 3, 1)
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

    def get_new_hydro_hdf5(self):
        """
        This is a function which allows the user to select an hdf5 file containing the hydrological
        data from a previous project and add it to the current project. It modifies the xml project file and test
        that the data is in correct form by loading it. The hdf5 should have the same form than the hydrological data
        created by HABBY in the method save_hdf5 of the class SubHydroW.
        """

        self.send_log.emit('# Load hdf5 file of hydrological data')
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
        if os.path.isdir(self.path_prj):
            new_name = os.path.join(self.path_prj,'COPY_' + os.path.basename(fname_h5))
            shutil.copyfile(fname_h5, new_name)
        else:
            self.send_log.emit('Error: the path to the project is not found. Is the project saved in the general tab?')
        try:
            file_hydro2 = h5py.File(new_name, 'r+')
        except OSError:
            self.send_log.emit('Error: The hdf5 file could not be loaded. \n')
        file_hydro2.attrs['path_projet'] = self.path_prj
        file_hydro2.attrs['name_projet'] = self.name_prj
        # save the new file name in the xml file of the project
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            print('Error: No project saved. Please create a project first in the General tab.\n')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            # new xml category in case the hydrological model is not supported by HABBY
            # as long s loded in the right format, it would not be a problem
            child = root.find(".//Imported_hydro")
            if child is None:
                stathab_element = ET.SubElement(root, "Imported_hydro")
                hdf5file = ET.SubElement(stathab_element, "hdf5import")
                hdf5file.text = new_name
            else:
                hdf5file = root.find(".//hdf5import")
                if hdf5file is None:
                    hdf5file = ET.SubElement(child, "hdf5import")
                    hdf5file.text = new_name
                else:
                    hdf5file.text += '\n' + new_name
            doc.write(filename_prj)
        self.send_log.emit('# hdf5 file sucessfully loaded to the current project.')
        return


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
    written in SubHydroW(). Indeed, all the children classes load hydrological data and therefore they are similar and can use
    similar functions.

    In other word, there are MainWindows() which provides the windows around the widget and Hydro2W which provide the widget for the
    hydrological Tab and one class by hydrological model to really load the model. The latter classes have various
    methods in common, so they inherit from SubHydroW, this class.
    """

    send_log = pyqtSignal(str, name='send_log')
    """
    A Pyqtsignal to write the log.
    """
    drop_hydro = pyqtSignal()
    """
    A PyQtsignal signal for the substrate tab so it can account for the new hydrological info.
    """

    def __init__(self, path_prj, name_prj):

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
        self.mystdout = None
        super().__init__()

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
        geometry and output data). For the case a), the default is to write only the first model loaded. If we wish to
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

    def show_dialog(self, i=0):
        """
        A function to obtain the name of the file chosen by the user. This method open a dialog so that the user select
        a file. This file is NOT loaded here. The name and path to this file is saved in an attribute. This attribute
        is then used to loaded the file in other function, which are different for each children class.

        :param i: a int for the case where there is more than one file to load
        """

        # find the filename based on user choice
        if len(self.pathfile) == 0:
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_prj)[0]
        elif i >= len(self.pathfile):
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathfile[0])[0]
        else:
            # why [0] : getOpenFilename return a tuple [0,1,2], we need only the filename
            filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathfile[i])[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            pass
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
            # keep the name in an attribute until we save it
            if i >= len(self.pathfile) or len(self.pathfile) == 0:
                self.pathfile.append(os.path.dirname(filename_path))
                self.namefile.append(filename)
            else:
                self.pathfile[i] = os.path.dirname(filename_path)
                self.namefile[i] = filename

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
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
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

    def save_hdf5(self):
        """
        This function save the hydrological data in the hdf5 format.

        **Techincal comments**

        This function cannot be used outside of the class, so it needs to be re-written if used from the command line.

        This function creates an hdf5 file which contains the hydrological data. First it creates an empty hdf5.
        Then it fill the hdf5 with data. For 1D model, it fill the data in 1D (the original data), then the 1.5D data
        created by dist_vitess2.py and finally the 2D data. For model in 2D it only saved 2D data. Hence, the 2D data
        is the data which is common to all model and which can always be loaded from a hydrological hdf5 created by
        HABBY. The 1D and 1.5D data is only present if the model is 1D or 1.5D. Here is some general info about the
        created hdf5:

        *   Name of the file: name_projet  +  ’_’ +  name model + date/time.h5.  For example, test4_HEC-RAS_25_10_2016_12_23_23.h5.
        *   Position of the file: in the folder  figure_habby currently (probably in a project folder in the final software)
        *   Format of the hdf5 file:

            *   Dats_gen:  number of time step and number of reach
            *   Data_1D:  xhzv_data_all (given profile by profile)
            *   Data_15D :  vh_pro, coord_pro (given profile by profile in a dict) and nb_pro_reach.
            *   Data_2D : For each time step, for each reach: ikle, point, point_c, inter_h, inter_vel

        If a list has elements with a changing number of variables, it is necessary to create a dictionary to save
        this list in hdf5. For example, a dictionary will be needed to save the following list: [[1,2,3,4], [1,2,3]].
        This is used for example, to save data by profile as we can have profile with more or less points. We also note
        in the hdf5 attribute some important info such as the project name, path to the project, hdf5 version.
        This can be useful if an hdf5 is lost and is not linked with any project. We also add the name of the created
        hdf5 to the xml project file. Now we can load the hydrological data using this hdf5 file and the xml project file.

        Hdf5 file do not support unicode. It is necessary to encode string to write them in ascii.
        """
        self.send_log.emit('# Save hdf5 hydrological data')

        # create hdf5 name
        h5name = self.name_prj + '_' + self.model_type + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
        path_hdf5 = self.find_path_im()

        # create a new hdf5
        fname = os.path.join(path_hdf5, h5name)
        file = h5py.File(fname, 'w')

        # create attributes
        file.attrs['path_projet'] = self.path_prj
        file.attrs['name_projet'] = self.name_prj
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version

        # create all datasets and group
        data_all = file.create_group('Data_gen')
        timeg = data_all.create_group('Nb_timestep')
        timeg.create_dataset(h5name, data=len(self.ikle_all_t)-1) # the first time step is for the whole profile
        nreachg = data_all.create_group('Nb_reach')
        nreachg.create_dataset(h5name, data=len(self.ikle_all_t[0]))
        # data by type of model (1D, 1.5D, 2D)
        if self.nb_dim == 1:
            Data_1D = file.create_group('Data_1D')
            xhzv_datag = Data_1D.create_group('xhzv_data')
            xhzv_datag.create_dataset(h5name, data=self.xhzv_data)
        if self.nb_dim < 2:
            Data_15D = file.create_group('Data_15D')
            adict = dict()
            for p in range(0, len(self.coord_pro)):
                ns = 'p' + str(p)
                adict[ns] = self.coord_pro[p]
            coord_prog = Data_15D.create_group('coord_pro')
            for k, v in adict.items():
                coord_prog.create_dataset(k, data=v)
                #coord_prog.create_dataset(h5name, [4, len(self.coord_pro[p][0])], data=self.coord_pro[p])
            for t in range(0, len(self.vh_pro)):
                there = Data_15D.create_group('Timestep_' + str(t))
                adict = dict()
                for p in range(0, len(self.vh_pro[t])):
                    ns = 'p' + str(p)
                    adict[ns] = self.vh_pro[t][p]
                for k, v in adict.items():
                    there.create_dataset(k, data=v)
            nbproreachg = Data_15D.create_group('Number_profile_by_reach')
            nb_pro_reach2 = list(map(float, self.nb_pro_reach))
            nbproreachg.create_dataset(h5name, [len(nb_pro_reach2), 1], data=nb_pro_reach2)
        if self.nb_dim <= 2:
            Data_2D = file.create_group('Data_2D')
            for t in range(0, len(self.ikle_all_t)):
                if t == 0:
                    there = Data_2D.create_group('Whole_Profile')
                else:
                    there = Data_2D.create_group('Timestep_'+str(t-1))
                for r in range(0, len(self.ikle_all_t[t])):
                    rhere = there.create_group('Reach_' + str(r))
                    ikleg = rhere.create_group('ikle')
                    if len(self.ikle_all_t[t][r]) > 0:
                        ikleg.create_dataset(h5name, [len(self.ikle_all_t[t][r]), len(self.ikle_all_t[t][r][0])],
                                             data=self.ikle_all_t[t][r])
                    else:
                        self.send_log.emit('Warning: Reach number ' + str(r) + ' has an empty grid. '
                                                                               'It might be entierely dry.')
                        ikleg.create_dataset(h5name, [len(self.ikle_all_t[t][r])], data=self.ikle_all_t[t][r])
                    point_allg = rhere.create_group('point_all')
                    point_allg.create_dataset(h5name, [len(self.point_all_t[t][r]), 2], data=self.point_all_t[t][r])
                    point_cg = rhere.create_group('point_c_all')
                    point_cg.create_dataset(h5name, [len(self.point_c_all_t[t][r]), 2], data=self.point_c_all_t[t][r])
                    if len(self.inter_vel_all_t[t]) > 0:
                        inter_velg = rhere.create_group('inter_vel_all')
                        inter_velg.create_dataset(h5name, [len(self.inter_vel_all_t[t][r]), 1], data=self.inter_vel_all_t[t][r])
                    else:
                        rhere.create_group('inter_vel_all')
                    if len(self.inter_h_all_t[t]) > 0:
                        inter_hg = rhere.create_group('inter_h_all')
                        inter_hg.create_dataset(h5name, [len(self.inter_h_all_t[t][r]), 1],
                                                data=self.inter_h_all_t[t][r])
                    else:
                        rhere.create_group('inter_h_all')
        file.close()

        # save the file to the xml of the project
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            print('Error: No project saved. Please create a project first in the General tab.\n')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//"+self.model_type)
            if child is None:
                stathab_element = ET.SubElement(root, self.model_type)
                hdf5file = ET.SubElement(stathab_element, "hdf5_hydrodata")
                hdf5file.text = fname
            else:
                hdf5file = root.find(".//"+self.model_type + "/hdf5_hydrodata")
                if hdf5file is None:
                    hdf5file = ET.SubElement(child, "hdf5_hydrodata")
                    hdf5file.text = fname
                else:
                    # hdf5file.text = hdf5file.text + ', ' + fname  # keep the name of the old and new file
                    hdf5file.text = fname   # keep only the new file
            doc.write(filename_prj)

        # send a signal to the substrate tab so it can account for the new info
        self.drop_hydro.emit()
        # log info
        self.send_log.emit('restart SAVE_HYDRO_HDF5')
        self.send_log.emit('py    # save_hdf5 (function needs to be re-written to be used in cmd)')
        return

    def find_path_im(self):
        """
        A function to find the path where to save the figues, careful a simialr one is in estimhab_GUI.py. By default,
        path_im is in a folder calls "Figure_Habby".
        """

        path_im = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Figure")
            if child is None:
                path_im = os.path.join(self.path_prj, 'figures_habby')
            else:
                path_im = child.text
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save the path to the figures"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        return path_im

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
            child = root.findall('.//' +att_here)
            if child is not None:
                for i in range(0, len(child)):
                    if i == 0:
                        data = child[i].text
                    else:
                        data += ',' + child[i].text
        else:
            pass
            # self.msg2.setIcon(QMessageBox.Warning)
            # self.msg2.setWindowTitle(self.tr("Read attributes"))
            # self.msg2.setText(
            #     self.tr("The project is not saved. Save the project in the General tab."))
            # self.msg2.setStandardButtons(QMessageBox.Ok)
            # self.msg2.show()

        return data

    def send_err_log(self):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout.
        """
        str_found = self.mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])

    def grid_and_interpo(self, cb_im):
        """
        This function forms the link between GUI and the various grid and interpolation functions. Is called by
        the "loading' function of hec-ras 1D, Mascaret and Rubar BE.
        :param cb_im: A boolean if true, the figures are created and shown.

        *Technical comment to be added*

        """
        # preparation
        if not isinstance(self.interpo_choice, int):
            self.send_log.emit('Error: Interpolation method is not recognized (Type).\n')
            return
        if cb_im:
            path_im = self.find_path_im()
        if len(self.vh_pro) == 0:
            self.send_log.emit('Warning: Velocity and height data is empty (from grid_and_interpo)')
            return
        if len(self.vh_pro) == 1 and self.vh_pro == [-99]:
            self.send_log.emit('Error: Velocity and height data were not created.')
            return

        # each interpolations type
        if self.interpo_choice == 0:
            self.send_log.emit(self.tr('# Create grid by block.'))
            # first whole profile
            #sys.stdout = self.mystdout = StringIO()
            [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                manage_grid_8.create_grid_only_1_profile(self.coord_pro, self.nb_pro_reach)
            #sys.stdout = sys.__stdout__
            self.send_err_log()
            self.inter_vel_all_t.append([])
            self.inter_h_all_t.append([])
            self.ikle_all_t.append(ikle_all)
            self.point_all_t.append(point_all_reach)
            self.point_c_all_t.append(point_c_all)
            self.send_log.emit("py    [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                    manage_grid_8.create_grid_only_1_profile(coord_pro, nb_pro_reach)\n")
            self.send_log.emit("restart INTERPOLATE_BLOCK")
            # by time step
            for t in range(0, len(self.vh_pro)):
                sys.stdout = self.mystdout = StringIO()
                [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                    manage_grid_8.create_grid_only_1_profile(self.coord_pro, self.nb_pro_reach, self.vh_pro[t])
                if cb_im and path_im != 'no_path':
                    manage_grid_8.plot_grid(point_all_reach, ikle_all, [], [], [], point_c_all,
                                            inter_vel_all, inter_height_all, path_im)
                sys.stdout = sys.__stdout__
                self.send_err_log()
                self.inter_vel_all_t.append(inter_vel_all)
                self.inter_h_all_t.append(inter_height_all)
                self.ikle_all_t.append(ikle_all)
                self.point_all_t.append(point_all_reach)
                self.point_c_all_t.append(point_c_all)
                self.send_log.emit("py    vh_pro_t = vh_pro[" + str(t) + "]\n")
                self.send_log.emit("py    [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                    manage_grid_8.create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro_t)\n")
                self.send_log.emit("restart INTERPOLATE_BLOCK")

        elif self.interpo_choice == 1:
            try:
                self.pro_add = int(self.nb_extrapro_text.text())
            except ValueError:
                self.send_log.emit('Error: Number of profile not recognized.\n')
                return
            self.send_log.emit(self.tr('# Create grid by linear interpolation.'))
            if not isinstance(self.pro_add, int):
                self.send_log.emit('Error: Number of profile not recognized.\n')
                return
            if 1 > self.pro_add > 500:
                self.send_log.emit('Error: Number of add. profiles should be between 1 and 500.\n')
                return
            # grid for the whole profile,
            q = Queue()
            ok = 0
            k = self.pro_add
            while ok == 0:
                # [], [] is used to add the substrate as a condition directly
                p = Process(target=manage_grid_8.create_grid, args=(self.coord_pro, k, [],
                                                                    [], self.nb_pro_reach, [], q))
                # sys.stdout = self.mystdout = StringIO()
                # [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = \
                #     manage_grid_8.create_grid(self.coord_pro, self.pro_add, [], [], self.nb_pro_reach)
                # sys.stdout = sys.__stdout__
                self.send_err_log()
                p.start()
                time.sleep(1)
                if p.exitcode == None:
                    point_all_reach = q.get()
                    ikle_all = q.get()
                    lim_by_reach = q.get()
                    hole_all = q.get()
                    overlap = q.get()
                    coord_pro2 = q.get()
                    point_c_all = q.get()
                    ok = 1
                else:
                    k += 5
                p.terminate()
            self.send_err_log()
            self.inter_vel_all_t.append([])
            self.inter_h_all_t.append([])
            self.ikle_all_t.append(ikle_all)
            self.point_all_t.append(point_all_reach)
            self.point_c_all_t.append(point_c_all)
            # only the wet area, by time step
            for t in range(0, len(self.vh_pro)):
                q = Queue()
                ok = 0
                k = self.pro_add
                while ok == 0:
                    # [], [] is used to add the substrate as a condition directly
                    p = Process(target=manage_grid_8.create_grid, args=(self.coord_pro, k,[],
                                                                        [], self.nb_pro_reach, self.vh_pro[t],q))
                    self.send_err_log()
                    p.start()
                    time.sleep(1)
                    if p.exitcode == None:
                        point_all_reach = q.get()
                        ikle_all = q.get()
                        lim_by_reach = q.get()
                        hole_all = q.get()
                        overlap = q.get()
                        coord_pro2 = q.get()
                        point_c_all = q.get()
                        [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_all_reach, coord_pro2,
                                                                                         self.vh_pro[t])
                        ok = 1
                    else:
                        k += 5
                    p.terminate()
            self.send_err_log()
            self.inter_vel_all_t.append(inter_vel_all)
            self.inter_h_all_t.append(inter_height_all)
            self.ikle_all_t.append(ikle_all)
            self.point_all_t.append(point_all_reach)
            self.point_c_all_t.append(point_c_all)
            if cb_im and path_im != 'no_path':
                manage_grid_8.plot_grid(point_all_reach, ikle_all, lim_by_reach,
                                        hole_all, overlap, point_c_all, inter_vel_all, inter_height_all, path_im)
            self.send_err_log()
            self.send_log.emit("py    vh_pro_t = vh_pro[" + str(t) + "]\n")
            self.send_log.emit("py    [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2,"
                               " point_c_all] = manage_grid_8.create_grid(coord_pro, nb_pro_reach, vh_pro_t)\n")
            self.send_log.emit("py    [inter_vel_all, inter_height_all] = "
                               "manage_grid_8.interpo_linear(point_c_all, coord_pro2, vh_pro_t))\n")
            self.send_log.emit("restart INTERPOLATE_LINEAR")

        elif self.interpo_choice == 2:
            try:
                self.pro_add = int(self.nb_extrapro_text.text())
            except ValueError:
                self.send_log.emit('Error: Number of profile not recognized.\n')
                return
            self.send_log.emit(self.tr('# Create grid by nearest neighbors interpolation.'))
            if 1 > self.pro_add > 500:
                self.send_log.emit('Error: Number of add. profiles should be between 1 and 500.\n')
                return
            # grid for the whole profile,
            q = Queue()
            ok = 0
            k = self.pro_add
            while ok == 0:
                # [], [] is used to add the substrate as a condition directly
                p = Process(target=manage_grid_8.create_grid, args=(self.coord_pro, k, [],
                                                                    [], self.nb_pro_reach, [], q))
                self.send_err_log()
                p.start()
                time.sleep(1)
                if p.exitcode == None:
                    point_all_reach = q.get()
                    ikle_all = q.get()
                    lim_by_reach = q.get()
                    hole_all = q.get()
                    overlap = q.get()
                    coord_pro2 = q.get()
                    point_c_all = q.get()
                    ok = 1
                else:
                    k += 5
                p.terminate()
            self.send_err_log()
            self.inter_vel_all_t.append([])
            self.inter_h_all_t.append([])
            self.ikle_all_t.append(ikle_all)
            self.point_all_t.append(point_all_reach)
            self.point_c_all_t.append(point_c_all)
            # create grid for the wet area by time steps
            for t in range(0, len(self.vh_pro)):
                q = Queue()
                ok = 0
                k = self.pro_add
                while ok == 0:
                    # [], [] is used to add the substrate as a condition directly
                    p = Process(target=manage_grid_8.create_grid, args=(self.coord_pro, k, [],
                                                                        [], self.nb_pro_reach, self.vh_pro[t], q))
                    self.send_err_log()
                    p.start()
                    time.sleep(1)
                    if p.exitcode == None:
                        point_all_reach = q.get()
                        ikle_all = q.get()
                        lim_by_reach = q.get()
                        hole_all = q.get()
                        overlap = q.get()
                        coord_pro2 = q.get()
                        point_c_all = q.get()
                        [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_c_all, coord_pro2,
                                                                                         self.vh_pro[t])
                        ok = 1
                    else:
                        k += 5
                    p.terminate()
                self.send_err_log()
                sys.stdout = self.mystdout = StringIO()
                [inter_vel_all, inter_height_all] = manage_grid_8.interpo_nearest(point_all_reach, coord_pro2, self.vh_pro[t])
                if cb_im and path_im != 'no_path':
                    manage_grid_8.plot_grid(point_all_reach, ikle_all, lim_by_reach,
                                            hole_all, overlap, point_c_all, inter_vel_all, inter_height_all, path_im)
                sys.stdout = sys.__stdout__
                self.send_err_log()
                self.inter_vel_all_t.append(inter_vel_all)
                self.inter_h_all_t.append(inter_height_all)
                self.ikle_all_t.append(ikle_all)
                self.point_all_t.append(point_all_reach)
                self.point_c_all_t.append(point_c_all)
                self.send_log.emit("py    vh_pro_t = vh_pro[" + str(t) + "]\n")
                self.send_log.emit("py    [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2,"
                                   " point_c_all] = manage_grid_8.create_grid(coord_pro, nb_pro_reach, vh_pro_t)\n")
                self.send_log.emit("py    [inter_vel_all, inter_height_all] = "
                                   "manage_grid_8.interpo_nearest(point_c_all, coord_pro2, vh_pro_t))\n")
                self.send_log.emit("restart INTERPOLATE_NEAREST")
        else:
            self.send_log.emit('Error: Interpolation method is not recognized (Num).\n')
        return

    def distribute_velocity(self):
        """
        This function make the link between the GUI and the functions of dist_vitesse2. It is used by 1D model,
        notably rubar and masacret.

        Dist vitess needs a manning parameters. It can be given by the user in two forms: a constant (float) or an array
        created by the function load_manning_text.
        """

        self.send_log.emit("# Velocity distribution")
        sys.stdout = self.mystdout = StringIO()
        if len(self.manning_arr) < 1:
            # distribution of velocity using a float as a manning value (same value for all place)
            manning_array = dist_vistess2.get_manning(self.manning1, self.np_point_vel, len(self.coord_pro), self.coord_pro)
            self.vh_pro = dist_vistess2.dist_velocity_hecras(self.coord_pro, self.xhzv_data, manning_array,
                                                         self.np_point_vel, 1, self.on_profile)
        else:
            # distribution of velocity using txt file as input for manning
            manning_array = dist_vistess2.get_manning_arr(self.manning_arr, self.np_point_vel, self.coord_pro)
            self.vh_pro = dist_vistess2.dist_velocity_hecras(self.coord_pro, self.xhzv_data, manning_array,
                                                             self.np_point_vel, 1, self.on_profile)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        self.send_log.emit("restart GET_MANNING")
        self.send_log.emit("restart DISTRIBUTE VELOCITY")
        self.send_log.emit("py    manning1 = " + str(self.manning1))
        self.send_log.emit("py    np_point_vel = " + str(self.np_point_vel))
        self.send_log.emit("py    manning_array = dist_vistess2.get_manning(manning1, np_point_vel, len(coord_pro))")
        self.send_log.emit("py    vh_pro = dist_vistess2.dist_velocity_hecras(coord_pro, xhzv_data, manning_array, "
                           "np_point_vel, 1, on_profile)")

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


class HEC_RAS1D(SubHydroW):
    """
   The class Hec_ras 1D is there to manage the link between the graphical interface and the functions in
   src/hec_ras06.py which loads the hec-ras data in 1D. The class HEC_RAS1D inherits from SubHydroW() so it have all
   the methods and the variables from the class ubHydroW(). The class hec-ras 1D is added to the self.stack of Hydro2W(). So the class Hec-Ras 1D is called when
   the user is on the hydrological tab and click on hec-ras1D as hydrological model.
    """
    show_fig = pyqtSignal()
    """
    PyQtsignal to show the figure.
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
        self.out_t2 = QLabel(self.namefile[1], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.g0x)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.xml, .sdf, or .res file)', self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))

        # # grid creation options
        l6 = QLabel(self.tr('<b>Grid creation </b>'))
        l3 = QLabel(self.tr('Velocity distribution'))
        l31 = QLabel(self.tr('Model 1.5D: No dist. needed'))
        l4 = QLabel(self.tr('Interpolation of the data'))
        l5 = QLabel(self.tr('Number of additional profiles'))
        self.inter.addItems(self.interpo)
        self.nb_extrapro_text = QLineEdit('1')

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_hec_ras_gui)
        self.spacer1 = QSpacerItem(1, 20)
        self.spacer2 = QSpacerItem(1, 20)
        self.cb = QCheckBox(self.tr('Show figures'), self)

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
        self.layout_hec.addWidget(l5, 6, 1)
        self.layout_hec.addWidget(self.nb_extrapro_text, 6, 2, 1, 2)
        self.layout_hec.addItem(self.spacer2, 7, 1)
        self.layout_hec.addWidget(self.load_b, 8, 3)
        self.layout_hec.addWidget(self.cb, 8, 2)
        #self.layout_hec.addItem(spacer, 4, 1)
        self.setLayout(self.layout_hec)

    def load_hec_ras_gui(self):
        """
        A function to execute the loading and saving of the HEC-ras file using Hec_ras.py

        **Technical comments**

        This function is called when the user press on the button self.load_b. It is the function which really
        calls the load function for hec_ras. First, it updates the xml project file. It adds the name of the new file
        to xml project file under the attribute indicated by self.attributexml. It also gets the path_im by reading the
        path_im in the xml project file. Then it check if the user want to create the figure or not
        (if self.cb.isChecked(), figures should be created). It also manages the log as explained in the section
        about the log. Notably, it redirects the  outstream to the mystdout stream. Hence, the “print” statement is
        now sent to the log windows at the bottom of HABBY window. Next, it loads the hec-ras data as explained in
        the section on hec_ras06.py. It then creates the grid as explained in the manage_grid.py based on the
        interpolation type wished by the user (linear, nearest neighbor or by block). It creates the hdf5
        with the loaded data. Finally, if necessary, it shows the figure by emitting a signal.
        This signal is collected in the MainWindow() class.

        """
        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        path_im = self.find_path_im()

        # load hec_ras data
        if self.cb.isChecked() and path_im != 'no_path':
            self.save_fig = True
        # redirect the out stream to my output
        a = time.time()
        sys.stdout = self.mystdout = StringIO()
        [self.coord_pro, self.vh_pro, self.nb_pro_reach] = Hec_ras06.open_hecras(self.namefile[0], self.namefile[1], self.pathfile[0],
                                               self.pathfile[1], path_im, self.save_fig)
        sys.stdout = sys.__stdout__
        b = time.time()
        print('time to load data: ' + str(b-a))
        # log info
        self.send_log.emit(self.tr('# Load: Hec-Ras 1D data.'))
        self.send_err_log()
        self.send_log.emit("py    file1='"+ self.namefile[0] + "'")
        self.send_log.emit("py    file2='" + self.namefile[1] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    path2='" + self.pathfile[1] + "'")
        self.send_log.emit("py    [coord_pro, vh_pro, nb_pro_reach] = Hec_ras06.open_hecras(file1, file2, path1, path2, '.', False)\n")
        self.send_log.emit("restart LOAD_HECRAS_1D")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0],self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(self.pathfile[1],self.namefile[1]))

        if self.coord_pro == [-99]:
            self.send_log.emit('Error: HEC-RAS data not loaded')
            return

        # grid and interpolation
        self.interpo_choice = self.inter.currentIndex()
        b = time.time()
        self.grid_and_interpo(self.cb.isChecked())
        c = time.time()
        print('time to interpolate velocity ' + str(b-a))
        print('time to create grid ' + str(c-b))

        # save hdf5 data
        self.save_hdf5()
        d = time.time()
        print('time to create grid ' + str(d-c))
        # show figure
        if self.cb.isChecked():
            self.show_fig.emit()


class Rubar2D(SubHydroW):
    """
    The class Rubar2D is there to manage the link between the graphical interface and the functions in src/rubar.py
    which loads the RUBAR data in 2D. It inherits from SubHydroW() so it have all the methods and the variables from
    the class SubHydroW(). The form of the function is similar to hec-ras, but it does not have the part about the grid
    creation as we look here as the data created in 2D by RUBAR.
    """
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figure.
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

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.mai, .dat)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.tps)', self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_rubar)
        self.spacer = QSpacerItem(1, 80)
        self.cb = QCheckBox(self.tr('Show figures'), self)

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
        self.layout_hec.addWidget(self.load_b, 3, 2)
        self.layout_hec.addWidget(self.cb, 3, 1)
        self.layout_hec.addItem(self.spacer, 4, 1)
        self.setLayout(self.layout_hec)

    def load_rubar(self):
        """
        A function to execture the loading and saving the the rubar file using rubar.py. It is similar to the
        load_hec_ras_gui() function. Obviously, it calls rubar and not hec_ras this time. A small difference is that
        the rubar2D outputs are only given in one grid for all time steps and all reaches. Moreover, it will be
        necessary to cut the grid for each time step as a function of the wetted area and maybe to separate the
        grid by reaches. This have not be done yet.

        Another problem is that the data of Rubar2D is given on the cells of the grid and not the nodes.
        This will need to be corrected as data in HABBY is centered on the node.
        """
        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        path_im = self.find_path_im()
        if self.cb.isChecked() and path_im != 'no_path':
            self.save_fig = True
        # load rubar 2d data
        sys.stdout = self.mystdout = StringIO()
        [self.inter_vel_all_t, self.inter_h_all_t, self.point_all_t, self.point_c_all_t, self.ikle_all_t] \
            = rubar.load_rubar2d(self.namefile[0], self.namefile[1],  self.pathfile[0], self.pathfile[1],
                                 path_im, self.save_fig)
        sys.stdout = sys.__stdout__

        # log info
        self.send_log.emit(self.tr('# Load: Rubar 2D data.'))
        self.send_err_log()
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    file2='" + self.namefile[1] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    path2='" + self.pathfile[1] + "'")
        self.send_log.emit("py    [v, h, coord_p, coord_c, ikle] = rubar.load_rubar2d(file1,"
                           " file2, path1, path2, '.', False)\n")
        self.send_log.emit("restart LOAD_RUBAR_2D")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(self.pathfile[1], self.namefile[1]))

        if self.inter_vel_all_t == [-99]:
            self.send_log.emit('Error: Rubar data not loaded.')
            return

        # TEMPORARY correction because we have only one grid for all time step
        self.point_all_t = [[self.point_all_t]]
        self.point_c_all_t = [[self.point_c_all_t]]
        self.ikle_all_t = [[self.ikle_all_t]]

        self.save_hdf5()

        if self.cb.isChecked():
            self.show_fig.emit()

    def propose_next_file(self):
        """
        This function proposes the second RUBAR file when the first is selected.  Indeed, to load rubar, we need
        one file with the geometry data and one file with the simulation results. If the user selects a file, this
        function looks if a file with the same name but with the extension of the other file type exists in the
        selected folder. This could be done for all hydrological models, but the function is harder
        to write when more than one extension is possible, so it has not been done yet.
        """
        if len(self.extension[1]) == 1:
            if self.out_t2.text() == 'unknown file':
                blob = self.namefile[0]
                self.out_t2.setText(blob[:-len(self.extension[0][0])] + self.extension[1][0])
                # keep the name in an attribute until we save it
                self.pathfile[1] = self.pathfile[0]
                self.namefile[1] = blob[:-len(self.extension[0][0])] + self.extension[1][0]


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
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figure.
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
        self.model_type = 'mascaret'
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
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.geo)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(1))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[1]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.opt, .rub)', self)
        self.out_b.clicked.connect(lambda: self.show_dialog(2))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[2]))

        # grid creation options
        l6 = QLabel(self.tr('<b>Grid creation </b>'))
        l3 = QLabel(self.tr('Velocity distribution'))
        l32 = QLabel(self.tr("Based on Manning's formula"))
        l7 = QLabel(self.tr("Nb. of velocity points by profile"))
        l8 = QLabel(self.tr("Manning coefficient"))
        l4 = QLabel(self.tr('Interpolation of the data'))
        l5 = QLabel(self.tr('Nb. of additional profiles'))
        self.inter.addItems(self.interpo)
        self.nb_extrapro_text = QLineEdit('1')
        self.nb_vel_text = QLineEdit('70')
        self.manning_text = QLineEdit('0.025')
        self.ltest = QLabel(self.tr('or'))
        self.manningb = QPushButton(self.tr('Load .txt'))
        self.manningb.clicked.connect(self.load_manning_text)

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_mascaret_gui)
        #spacer = QSpacerItem(1, 20)
        self.cb = QCheckBox(self.tr('Show figures'), self)

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
        #self.layout.addItem(spacer, 2, 1)
        self.layout.addWidget(l6, 3, 0)
        self.layout.addWidget(l3, 4, 1)
        self.layout.addWidget(l32, 4, 2, 1, 2)
        self.layout.addWidget(l7, 5, 1)
        self.layout.addWidget(self.nb_vel_text, 5, 2)
        self.layout.addWidget(l8, 6, 1)
        self.layout.addWidget(self.manning_text, 6, 2)
        self.layout.addWidget(self.ltest, 6, 3)
        self.layout.addWidget(self.manningb, 6, 4)
        self.layout.addWidget(l4, 7, 1)
        self.layout.addWidget(self.inter, 7, 2, 1, 2)
        self.layout.addWidget(l5, 8, 1)
        self.layout.addWidget(self.nb_extrapro_text, 8, 2)
        #self.layout.addItem(spacer, 7, 1)
        self.layout.addWidget(self.load_b, 9, 2)
        self.layout.addWidget(self.cb, 9, 1)
        self.setLayout(self.layout)

    def load_mascaret_gui(self):
        """
        The function is used to load the mascaret data, calling the function contained in the script mascaret.py
        """
        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        self.save_xml(2)
        path_im = self.find_path_im()
        self.send_log.emit(self.tr('# Load: Mascaret data.'))
        sys.stdout = self.mystdout = StringIO()
        [self.coord_pro, coord_r, self.xhzv_data, name_pro, name_reach, self.on_profile, self.nb_pro_reach]\
            = mascaret.load_mascaret(self.namefile[0], self.namefile[1], self.namefile[2], self.pathfile[0],\
                                     self.pathfile[1], self.pathfile[2])
        sys.stdout = sys.__stdout__
        self.send_err_log()
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    file2='" + self.namefile[1] + "'")
        self.send_log.emit("py    file3='" + self.namefile[2] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    path2='" + self.pathfile[1] + "'")
        self.send_log.emit("py    path3='" + self.pathfile[2] + "'")
        self.send_log.emit("py    [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach] "
                           " =  mascaret.load_mascaret(file1, file2, file3, path1, path2, path3)\n")
        self.send_log.emit("restart LOAD_MASCARET")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(self.pathfile[1], self.namefile[1]))
        self.send_log.emit("restart    file3: " + os.path.join(self.pathfile[2], self.namefile[2]))

        if self.coord_pro == [-99]:
            print('Error: Mascaret data not loaded. \n')
            return

        if self.cb.isChecked() and path_im != 'no_path':
            mascaret.figure_mascaret(self.coord_pro, coord_r, self.xhzv_data, self.on_profile, self.nb_pro_reach,
                                     name_pro, name_reach, path_im, [0, 1], [-1], [0])
        # velocity distibution
        try:
            # we have two cases possible: a manning array or a manning float. here we take the case manning as float
            if not self.manning_arr:
                self.manning1 = float(self.manning_text.text())
        except ValueError:
            self.send_log.emit("Error: The manning value is not understood.")
        try:
            self.np_point_vel = int(self.nb_vel_text.text())
        except ValueError:
            self.send_log.emit("Error: The number of velocity point is not understood.")


        # grid and interpolation
        self.distribute_velocity()
        self.interpo_choice = self.inter.currentIndex()
        self.grid_and_interpo(self.cb.isChecked())

        #self.save_hdf5()

        if self.cb.isChecked():
            self.show_fig.emit()


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

    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figure.
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
        self.add_file_to_list()
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # button
        self.choodirb = QPushButton(self.tr("Add all .cdg files (choose dir)"))
        self.choodirb.clicked.connect(self.add_all_file)
        self.removefileb = QPushButton(self.tr("Remove file"))
        self.removefileb.clicked.connect(self.remove_file)
        self.removeallfileb = QPushButton(self.tr("Remove all files"))
        self.removeallfileb.clicked.connect(self.remove_all_file)
        self.addfileb = QPushButton(self.tr("Add file"))
        self.addfileb.clicked.connect(self.add_file_river2d)
        self.loadb = QPushButton(self.tr("Load all files and create hdf5"))
        self.loadb.clicked.connect(self.load_river2d_gui)

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

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
        self.layout.addWidget(self.loadb, 5, 1)
        self.layout.addWidget(self.cb, 5, 0)
        self.setLayout(self.layout)

    def remove_file(self):
        """
        This is small function to remove a .cdg file from the list of files to be loaded and from the QlistWidget.
        """
        i = self.list_f.currentRow()
        item = self.list_f.takeItem(i)
        item = None
        del self.namefile[i]
        del self.pathfile[i]

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
        It calls show_dialog, prepare some data for it and update the QWidgetList with
        the name of the file containted in the variable self.namefile.
        """
        if len(self.extension) == len(self.namefile):
            self.extension.append(self.extension[0])
            self.attributexml.append(self.attributexml[0])
        self.show_dialog(len(self.namefile))
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

    def add_all_file(self):
        """
        The function finds all .cdg file in one directory to add there names to the list of files to be loaded
        """

        # get the directory
        dir_name = QFileDialog.getExistingDirectory()
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

    def load_river2d_gui(self):
        """
        This function is used to load the river 2d data.
        """

        xyzhv = []
        self.ikle_all_t = []
        self.point_c_all_t = []
        self.point_all_t = []
        self.inter_h_all_t = []
        self.inter_vel_all_t = []
        self.send_log.emit(self.tr('# Load: River2D data.'))

        path_im = self.find_path_im()
        if len(self.namefile) == 0:
            self.send_log.emit("Warning: No file chosen.")
        for i in range(0, len(self.namefile)):
            # save each name in the project file, empty list on i == 0
            if i == 0:
                self.save_xml(i, False)
            else:
                self.save_xml(i, True)
            # load
            sys.stdout = self.mystdout = StringIO()
            [xyzhv_i, ikle_i, coord_c] = river2d.load_river2d_cdg(self.namefile[i], self.pathfile[i])
            sys.stdout = sys.__stdout__
            # if fail
            self.send_err_log()
            if isinstance(xyzhv_i[0], int):
                if xyzhv_i[0] == -99:
                    self.send_log.emit('Error: River2D data could not be loaded')
                    return
            xyzhv.append(xyzhv_i)
            self.point_all_t.append(xyzhv_i[:, :2])
            self.ikle_all_t.append(ikle_i)
            self.point_c_all_t.append(coord_c)
            self.inter_h_all_t.append(xyzhv_i[:, 3])
            self.inter_vel_all_t.append(xyzhv_i[:, 4])
            if self.cb.isChecked() and path_im != 'no_path' and i == 0:
                river2d.figure_river2d(xyzhv_i, ikle_i, path_im, i)

            # log
            self.send_log.emit("py    file1='" + self.namefile[i] + "'")
            self.send_log.emit("py    path1='" + self.pathfile[i] + "'")
            self.send_log.emit("py    [v, h, coord_p, coord_c, ikle] = river2d.load_river2d_cdg(file1, path1) \n")
            self.send_log.emit("restart LOAD_RIVER_2D")
            self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[i], self.namefile[i]))

        # TEMPORARY correction because we have only one grid for all reaches
        self.point_all_t = [self.point_all_t]
        self.point_c_all_t = [self.point_c_all_t]
        self.ikle_all_t = [self.ikle_all_t]
        self.inter_h_all_t = [self.inter_h_all_t]
        self.inter_vel_all_t = [self.inter_vel_all_t]

        self.save_hdf5()

        if self.cb.isChecked():
            self.show_fig.emit()


class Rubar1D(SubHydroW):
    """
    The class Rubar1D is there to manage the link between the graphical interface and the functions in src/rubar.py
    which loads the Rubar1D data in 1D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to Mascaret class.
    """
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figures.
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
        self.extension = [[''], ['']]  # no useful extension in this case
        self.nb_dim = 1

        # if there is the project file with rubar geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)

        # label with the file name
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.rbe)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (profil.X)', self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))

        # grid creation options
        l6 = QLabel(self.tr('<b>Grid creation </b>'))
        l3 = QLabel(self.tr('Velocity distribution'))
        l32 = QLabel(self.tr("Based on Manning's formula"))
        l7 = QLabel(self.tr("Nb. of velocity points by profile"))
        l8 = QLabel(self.tr("Manning coefficient"))
        l4 = QLabel(self.tr('Interpolation of the data'))
        l5 = QLabel(self.tr('Nb. of additional profiles'))
        self.inter.addItems(self.interpo)
        self.nb_extrapro_text = QLineEdit('1')
        self.nb_vel_text = QLineEdit('50')
        self.manning_text = QLineEdit('0.025')
        self.ltest = QLabel(self.tr('or'))
        self.manningb = QPushButton(self.tr('Load .txt'))
        self.manningb.clicked.connect(self.load_manning_text)

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_rubar1d)
        self.spacer1 = QSpacerItem(1, 20)
        self.spacer2 = QSpacerItem(1, 20)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addItem(self.spacer1, 2, 1)
        self.layout_hec.addWidget(l6, 2, 0)
        self.layout_hec.addWidget(l3, 3, 1)
        self.layout_hec.addWidget(l32, 3, 2, 1, 2)
        self.layout_hec.addWidget(l7, 4, 1)
        self.layout_hec.addWidget(self.nb_vel_text, 4, 2)
        self.layout_hec.addWidget(l8, 5, 1)
        self.layout_hec.addWidget(self.manning_text, 5, 2)
        self.layout_hec.addWidget(self.ltest, 5, 3)
        self.layout_hec.addWidget(self.manningb, 5, 4)
        self.layout_hec.addWidget(l4, 6, 1)
        self.layout_hec.addWidget(self.inter, 6, 2)
        self.layout_hec.addWidget(l5, 7, 1)
        self.layout_hec.addWidget(self.nb_extrapro_text, 7, 2)
        #self.layout_hec.addItem(self.spacer2, 7, 1)
        self.layout_hec.addWidget(self.load_b, 8, 2)
        self.layout_hec.addWidget(self.cb, 8, 1)
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
        path_im = self.find_path_im()
        if self.cb.isChecked() and path_im != 'no_path':
            self.save_fig = True
        #load rubar 1D
        sys.stdout = self.mystdout = StringIO()
        [self.xhzv_data, self.coord_pro, lim_riv] = rubar.load_rubar1d(self.namefile[0],
                                         self.namefile[1], self.pathfile[0], self.pathfile[1], path_im, self.save_fig)
        self.nb_pro_reach = [0, len(self.coord_pro)]   # should be corrected?
        sys.stdout = sys.__stdout__
        # log info
        self.send_log.emit(self.tr('# Load: Rubar 1D data.'))
        self.send_err_log()
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    file2='" + self.namefile[1] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    path2='" + self.pathfile[1] + "'")
        self.send_log.emit("py    [data_xhzv, coord_pro, lim_riv] = rubar.load_rubar1d(file1,"
                           " file2, path1, path2, '.', False)\n")
        self.send_log.emit("restart LOAD_RUBAR_1D")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))
        self.send_log.emit("restart    file2: " + os.path.join(self.pathfile[1], self.namefile[1]))

        if self.xhzv_data == [-99]:
            self.send_log.emit("Rubar data could not be loaded.")
            return

        # velocity distibution
        try:
            # we have two cases possible: a manning array or a manning float. here we take the case manning as float
            if not self.manning_arr:
                self.manning1 = float(self.manning_text.text())
        except ValueError:
            self.send_log.emit("Error: The manning value is not understood.")
        try:
            self.np_point_vel = int(self.nb_vel_text.text())
        except ValueError:
            self.send_log.emit("Error: The number of velocity point is not understood.")
        # velcoity distribution
        self.distribute_velocity()
        # grid and interpolation
        self.interpo_choice = self.inter.currentIndex()
        self.grid_and_interpo(self.cb.isChecked())
        self.save_hdf5()

        if self.cb.isChecked() and path_im != 'no_path':
            self.show_fig.emit()


class HEC_RAS2D(SubHydroW):
    """
    The class hec_RAS2D is there to manage the link between the graphical interface and the functions in src/hec_ras2D.py
    which loads the hec_ras2D data in 2D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class and it has the same problem about node/cell
    which will need to be corrected.
    """
    show_fig = pyqtSignal()
    """
    PyQtsignal to show the figures.
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

        # load button
        load_b = QPushButton('Load data and create hdf5', self)
        load_b.clicked.connect(self.load_hec_2d_gui)
        self.spacer = QSpacerItem(1, 80)
        self.cb = QCheckBox(self.tr('Show figures'), self)

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
        self.layout_hec2.addWidget(load_b, 3, 2)
        self.layout_hec2.addWidget(self.cb, 3, 1)
        self.layout_hec2.addItem(self.spacer, 4, 1)
        self.setLayout(self.layout_hec2)

    def load_hec_2d_gui(self):
        """
        This function calls the function which load hecras 2d and save the names of file in the project file.
        It is similar to the function to load_rubar2D.
        """
        self.save_xml(0)
        path_im = self.find_path_im()
        # load the hec_ras data
        sys.stdout = self.mystdout = StringIO()
        [v, h, elev, coord_p, coord_c, ikle] = hec_ras2D.load_hec_ras2d(self.namefile[0], self.pathfile[0])
        sys.stdout = sys.__stdout__

        # TEMPORARY correction because we have only one grid for all time step
        self.point_all_t = [coord_p]
        self.point_c_all_t = [coord_c]
        self.ikle_all_t = [ikle]   # carefil ikle not corrected for non-triangular cells
        self.inter_h_all_t = v
        self.inter_vel_all_t = h

        # log info
        self.send_log.emit(self.tr('# Load: HEC-RAS 2D.'))
        self.send_err_log()
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    [v, h, elev, coord_p, coord_c, ikle] = hec_ras2D.load_hec_ras2d(file1, path1)\n")
        self.send_log.emit("restart LOAD_HECRAS_2D")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))

        if isinstance(v[0], int):
            if v == [-99]:
                self.send_log.emit("Error: HEC-RAS2D data could not be loaded.")
                return

        # save
        self.save_hdf5()

        if self.cb.isChecked() and path_im != 'no_path':
            hec_ras2D.figure_hec_ras2d(v, h, elev, coord_p, coord_c, ikle, path_im, [-1], [0])
            self.show_fig.emit()


class TELEMAC(SubHydroW):
    """
    The class Telemac is there to manage the link between the graphical interface and the functions in src/selafin_habby1.py
    which loads the Telemac data in 2D. It inherits from SubHydroW() so it have all the methods and the variables
    from the class SubHydroW(). It is very similar to RUBAR2D class, but data from Telemac is on the node as in HABBY.
    """
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figure.
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

        # grid creation
        l2D1 = QLabel(self.tr('<b>Grid creation </b>'))
        l2D2 = QLabel(self.tr('2D MODEL - No new grid needed.'))

        # load button
        load_b = QPushButton('Load data and create hdf5', self)
        load_b.clicked.connect(self.load_telemac_gui)
        self.spacer = QSpacerItem(1, 80)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2,0 , 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(l2, 1, 0)
        self.layout_hec2.addWidget(l3, 1, 1)
        self.layout_hec2.addWidget(l2D1, 2, 0)
        self.layout_hec2.addWidget(l2D2, 2, 1, 1, 2)
        self.layout_hec2.addWidget(load_b, 3, 2)
        self.layout_hec2.addItem(self.spacer, 4, 1)
        self.layout_hec2.addWidget(self.cb, 3, 1)
        self.setLayout(self.layout_hec2)

    def load_telemac_gui(self):
        """
        The function which call the function which load telemac and save the name of files in the project file
        """
        self.save_xml(0)
        # load the telemac data
        path_im = self.find_path_im()
        sys.stdout = self.mystdout = StringIO()
        [v, h, coord_p, ikle, coord_c] = selafin_habby1.load_telemac(self.namefile[0], self.pathfile[0])
        sys.stdout = sys.__stdout__

        # TEMPORARY correction because we have only one grid for all time step and all reach
        self.point_all_t = [[coord_p]]
        self.point_c_all_t = [[coord_c]]
        self.ikle_all_t = [[ikle] ]  # carefil ikle not corrected for non-triangular cells
        self.inter_h_all_t = [v]
        self.inter_vel_all_t = [h]

        # log info
        self.send_log.emit(self.tr('# Load: TELEMAC data.'))
        self.send_err_log()
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    [[v, h, coord_p, ikle] = selafin_habby1.load_telemac(file1, path1)\n")
        self.send_log.emit("restart LOAD_TELEMAC")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))

        if len(v) == 1 and v[0] == [-99]:
            self.send_log.emit('Error: Telemac data not loaded.')

        # save
        self.save_hdf5()

        if self.cb.isChecked() and path_im != 'no_path':
            selafin_habby1.plot_vel_h(coord_p, h, v, path_im)
            self.show_fig.emit()


class SubstrateW(SubHydroW):
    """
    This is the widget used to load the substrate. It is practical to re-use some of the method from SubHydroW.
    So this class inherit from SubHydroW.
    """
    show_fig = pyqtSignal()
    """
    A PyQtsignal to show the figures.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__().
        """
        # update attribute
        self.attributexml = ['substrate_data', 'att_name']
        self.model_type = 'SUBSTRATE'
        self.extension = [['.txt', '.shp', '.asc']]
        self.name_att = ''
        self.coord_p = []
        self.ikle_sub = []
        self.sub_info = []

        # if there was substrate info before, update the label and attibutes
        self.e2 = QLineEdit()
        self.was_model_loaded_before()
        self.get_att_name()
        self.h2d_t2 = QLabel(self.namefile[0], self)
        self.e2.setText(self.name_att)

        # label and button
        l1 = QLabel(self.tr('<b> Load substrate data </b>'))
        l2 = QLabel(self.tr('File'))
        l3 = QLabel(self.tr('If text file used as input:'))
        l7 = QLabel(self.tr('Attribute name:'))
        l6 = QLabel(self.tr('(only for shapefile)'))
        l5 = QLabel(self.tr('A Delaunay triangulation will be applied.'))
        self.h2d_b = QPushButton('Choose file (.txt, .shp)', self)
        self.h2d_b.clicked.connect(lambda: self.show_dialog(0))
        self.h2d_b.clicked.connect(lambda: self.h2d_t2.setText(self.namefile[0]))
        l4 = QLabel(self.tr('Default substrate:'))
        self.e1 = QLineEdit()
        # e1.setValidator(QIntValidator())
        load_b = QPushButton('Load data and save', self)
        load_b.clicked.connect(self.load_sub_gui)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # label and button for the part to merge the grid
        l8 = QLabel(self.tr("<b> Merge the hydrological and substrate grid </b>"))
        l9 = QLabel(self.tr("Hydrological data (hdf5)"))
        l10 = QLabel(self.tr("Substrate data (hdf5)"))
        self.drop_hyd = QComboBox()
        self.drop_sub = QComboBox()
        self.load_b2 = QPushButton(self.tr("Merge grid and create hdf5"), self)
        self.load_b2.clicked.connect(self.send_merge_grid)
        self.spacer2 = QSpacerItem(1, 120)
        self.cb2 = QCheckBox(self.tr('Show figures'), self)

        # get possible substrate and hydro hdf5 from the project file
        self.sub_name = self.read_attribute_xml('hdf5_substrate')
        self.sub_name = self.sub_name.split(',')
        sub_name2 = []  # we might have unexisting hdf5 file in the xml project file
        for i in range(0, len(self.sub_name)):
            if os.path.isfile(self.sub_name[i]):
                sub_name2.append(self.sub_name[i])
        self.sub_name = sub_name2
        for i in range(0, len(self.sub_name)):
            if os.path.isfile(self.sub_name[i]):
                self.drop_sub.addItem(os.path.basename(self.sub_name[i]))
        self.update_hydro_hdf5_name()

        # layout
        self.layout_sub = QGridLayout()
        self.layout_sub.addWidget(l1, 0, 0)
        self.layout_sub.addWidget(l2, 1, 0)
        self.layout_sub.addWidget(self.h2d_t2, 1, 1)
        self.layout_sub.addWidget(self.h2d_b, 1, 2)
        self.layout_sub.addWidget(l7, 2, 0)
        self.layout_sub.addWidget(self.e2, 2, 1)
        self.layout_sub.addWidget(l6, 2, 2)
        self.layout_sub.addWidget(l3, 4, 0)
        self.layout_sub.addWidget(l5, 4, 1)
        self.layout_sub.addWidget(l4, 3, 0)
        self.layout_sub.addWidget(self.e1, 3, 1)
        self.layout_sub.addWidget(load_b, 3, 2)
        #self.layout_sub.addItem(spacer, 5, 0)
        #self.layout_sub.addItem(spacer2, 5, 3)
        self.layout_sub.addWidget(self.cb, 3, 3)
        self.layout_sub.addWidget(l8, 5, 0)
        self.layout_sub.addWidget(l9, 6, 0)
        self.layout_sub.addWidget(self.drop_hyd, 6, 1)
        self.layout_sub.addWidget(l10, 7, 0)
        self.layout_sub.addWidget(self.drop_sub, 7, 1)
        self.layout_sub.addWidget(self.load_b2, 8, 2)
        self.layout_sub.addWidget(self.cb2, 8, 1)
        self.layout_sub.addItem(self.spacer2, 9, 1)

        self.setLayout(self.layout_sub)

    def update_hydro_hdf5_name(self):
        """
        This is a short function used to read all the hydrological data contained in an hdf5 files and available in
        one project. When these files are read, they are added to the drop-down menu;
        This should be a function because an update to this list can be triggered by the loading of a new hydrological
        data. The class SubstrateW() noticed this through the signal drop_hydro send by the hydrological class.
        The signal drop_hydro is connected to this function in the class CentralW in MainWindows.py. Indeed, it is not
        possible to do it in SubstrateW().
        """
        self.hyd_name = self.read_attribute_xml('hdf5_hydrodata')
        self.hyd_name = self.hyd_name.split(',')
        hyd_name2 = []  # we might have unexisting hdf5 file in the xml project file
        for i in range(0, len(self.hyd_name)):
            if os.path.isfile(self.hyd_name[i]):
                hyd_name2.append(self.hyd_name[i])
        self.hyd_name = hyd_name2
        for i in range(0, len(self.hyd_name)):
            if os.path.isfile(self.hyd_name[i]):
                self.drop_hyd.addItem(os.path.basename(self.hyd_name[i]))

    def load_sub_gui(self):
        """
        This function is used to load the substrate data. The substrate data can be in two forms: a) in the form of a shp
        file form ArGIS (or another GIS-program). b) in the form of a text file (x,y, substrate data line by line).
        Generally this function has some similarities to the functions used to load the hydrological data and it re-uses
        some of the methods developed for them.
        """

        # save path and name substrate
        self.save_xml(0)
        # only save attribute name if shapefile
        self.name_att = self.e2.text()
        blob, ext = os.path.splitext(self.namefile[0])
        path_im = self.find_path_im()
        # if the substrate is in the shp form
        if ext == '.shp':
            if not self.name_att:
                self.send_log.emit("Error: No attribute name was given to load the shapefile.")
                return
            self.pathfile[1] = ''
            self.namefile[1] = self.name_att  # avoid to code things again
            self.save_xml(1)
        # load substrate
            sys.stdout = self.mystdout = StringIO()
            [self.coord_p, self.ikle_sub, self.sub_info] = substrate.load_sub_shp(self.namefile[0], self.pathfile[0], self.name_att)
            # log info
            self.send_log.emit(self.tr('# Load: Substrate data - Shapefile'))
            self.send_err_log()
            self.send_log.emit("py    file1='" + self.namefile[0] + "'")
            self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
            self.send_log.emit("py    attr='" + self.name_att + "'")
            self.send_log.emit("py    [coord_p, ikle_sub, sub_info] = substrate.load_sub_shp(file1, path1, attr)\n")
            self.send_log.emit("restart LOAD_SUB_SHP")
            self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))
            self.send_log.emit("restart    file2: " + os.path.join(self.pathfile[0], self.namefile[0]))
            self.send_log.emit("restart    attr: " + self.name_att)

            if self.cb.isChecked():
                substrate.fig_substrate(self.coord_p, self.ikle_sub, self.sub_info, path_im)
        # if the substrate data is a text form
        elif ext == '.txt' or ext == ".asc":
            sys.stdout = self.mystdout = StringIO()
            [self.coord_p, self.ikle_sub, self.sub_info, x, y, sub] = substrate.load_sub_txt(self.namefile[0], self.pathfile[0])
            self.log_txt()
            if self.cb.isChecked():
                substrate.fig_substrate(self.coord_p, self.ikle_sub, self.sub_info, path_im, x, y, sub)
        # case unknown
        else:
            self.send_log.emit("Warning: Unknown extension for substrate data, the model will try to load as .txt")
            sys.stdout = self.mystdout = StringIO()
            [self.coord_p, self.ikle_sub, self.sub_info, x, y, sub] = substrate.load_sub_txt(self.namefile[0], self.pathfile[0])
            if self.cb.isChecked():
                substrate.fig_substrate(self.coord_p, self.ikle_sub, self.sub_info, path_im, x, y, sub)
            self.log_txt()
        self.save_hdf5_sub()

        # add the name of the hdf5 to the drop down menu so we can use it to merge with hydrological data
        self.sub_name = self.read_attribute_xml('hdf5_substrate')
        self.sub_name = self.sub_name.split(',')
        sub_name2 = []  # we might have unexisting hdf5 file in the xml project file
        for i in range(0, len(self.sub_name)):
            if os.path.isfile(self.sub_name[i]):
                sub_name2.append(self.sub_name[i])
        self.sub_name = sub_name2
        self.drop_sub.clear()
        for i in range(0, len(self.sub_name)):
            self.drop_sub.addItem(os.path.basename(self.sub_name[i]))

        # show figure
        if self.cb.isChecked() and path_im != 'no_path':
            self.show_fig.emit()

    def log_txt(self):
        """
        This function gives the log for the substrate in text form. this is in a function because it is used twice in
        the function load_sub_gui()
        """
        # log info
        self.send_log.emit(self.tr('# Load: Substrate data - text file'))
        str_found = self.mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
        self.send_log.emit("py    file1='" + self.namefile[0] + "'")
        self.send_log.emit("py    path1='" + self.pathfile[0] + "'")
        self.send_log.emit("py    [coord_pt, ikle_subt, sub_infot, x, y, sub] = substrate.load_sub_txt(file1, path1)\n")
        self.send_log.emit("restart LOAD_SUB_TXT")
        self.send_log.emit("restart    file1: " + os.path.join(self.pathfile[0], self.namefile[0]))

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

    def save_hdf5_sub(self):
        """
        This function save the substrate data in its own hdf5 file and write the name of this hdf5 file in the
        xml project file. The format of the hdf5 file is not finalzed yet so it is not documented.
        """

        self.send_log.emit('# Save data for the substrate in an hdf5 file.')

        # create hdf5 name
        h5name = self.name_prj + '_' + 'substrate' + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
        path_hdf5 = self.find_path_im()

        # create a new hdf5
        fname = os.path.join(path_hdf5, h5name)
        file = h5py.File(fname, 'w')

        # create attributes
        file.attrs['path_projet'] = self.path_prj
        file.attrs['name_projet'] = self.name_prj
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version

        # save ikle, coordonate and data
        ikleg = file.create_group('ikle_sub')
        coordpg = file.create_group('coord_p_sub')
        if len(self.ikle_sub) > 0:
            ikleg.create_dataset(h5name, [len(self.ikle_sub), len(self.ikle_sub[0])], data=self.ikle_sub)
        coordpg.create_dataset(h5name, [len(self.coord_p), 2], data=self.coord_p)
        # CAREFUL: Data sub is not save yet in the substrate hdf5
        # because we do not know yet the form of the substrate data
        datasubg = file.create_group('data_sub')
        file.close()

        # save the file to the xml of the project
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            pass
            self.send_log.emit('Error: No project saved. Please create a project first in the General tab.\n')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//" + self.model_type)
            if child is None:
                stathab_element = ET.SubElement(root, self.model_type)
                hdf5file = ET.SubElement(stathab_element, "hdf5_substrate")
                hdf5file.text = fname
            else:
                hdf5file = root.find(".//" + 'substrate_data' + "/hdf5_substrate")
                if hdf5file is None:
                    hdf5file = ET.SubElement(child, "hdf5_substrate")
                    hdf5file.text = fname
                else:
                    # hdf5file.text = hdf5file.text + ', ' + fname  # keep the name of the old and new file
                    hdf5file.text = fname  # keep only the new file
            doc.write(filename_prj)

        self.send_log.emit('restart SAVE_HYDRO_HDF5')
        self.send_log.emit('py    # save_hdf5_sub (function needs to be re-written to be used in cmd)')

    def send_merge_grid(self):
        """
        This function calls the function merge grid in substrate.py. The goal is to have the substrate and hydrological
        data on the same grid. Hence, the hydrological grid will need to be cut to the form of the substrate grid.
        """
        self.send_log.emit('# Merge substrate and hydrological grid')

        hdf5_name_hyd = self.hyd_name[self.drop_hyd.currentIndex()]
        hdf5_name_sub = self.sub_name[self.drop_sub.currentIndex()]
        default_data = self.e1.text()

        # check inputs in the function
        sys.stdout = self.mystdout = StringIO()
        [ikle_both, point_all_both, sub_data, vel, height] = substrate.merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub,
                                                                                default_data)
        sys.stdout = sys.__stdout__
        # figure
        path_im = self.find_path_im()
        if self.cb2.isChecked() and path_im != 'no_path':
            # plot the last time step, can be changed if necessary
            substrate.fig_merge_grid(point_all_both[-1], ikle_both[-1], path_im)

        # log
        self.send_err_log()
        self.send_log.emit("py    file_hyd='" + self.hyd_name[self.drop_hyd.currentIndex()] + "'")
        self.send_log.emit("py    file_sub='" + self.sub_name[self.drop_sub.currentIndex()] + "'")
        self.send_log.emit("py    defval='" + self.e1.text() + "'")
        self.send_log.emit("py    [ikle, coord_p, sub_data, vel, height] = substrate.merge_grid_hydro_sub(file_hyd,"
                           " file_sub, defval)\n")
        self.send_log.emit("restart MERGE_GRID_SUB")
        self.send_log.emit("restart    file_hyd='" + self.hyd_name[self.drop_hyd.currentIndex()] + "'")
        self.send_log.emit("restart    file_sub='" + self.sub_name[self.drop_sub.currentIndex()] + "'")
        self.send_log.emit("restart    defval='" + self.e1.text() + "'")
        if self.cb2.isChecked() and path_im != 'no_path':
            self.show_fig.emit()

        # save the data in a new hdf5
