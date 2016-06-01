import os
import numpy as np
from PyQt5.QtCore import QTranslator, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import Hec_ras06
import hec_ras2D
import selafin_habby1
import substrate
import rubar

class Hydro2W(QWidget):
    """
    A class to load the hydrological data
    List of model supported:
    - TELEMAC
    - HEC-RAS
    -
    -
    """
    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.mod = QComboBox()
        self.mod_loaded = QComboBox()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_model = ["", "HEC-RAS 1D", "HEC-RAS 2D" ,"RUBAR 2D", "TELEMAC"]  # "MAGE", 'MASCARET', "RIVER 2D", "RUBAR",
        self.mod_act = 0
        self.stack = QStackedWidget()
        self.msgi = QMessageBox()
        self.init_iu()

    def init_iu(self):
        # generic label
        self.l1 = QLabel(self.tr('<b> Saved hydrological data </b>'))
        l2 = QLabel(self.tr('<b> LOAD NEW DATA </b>'))
        l3 = QLabel(self.tr('<b>Available hydrological models </b>'))

        # available model
        self.mod_loaded.addItems([""])
        self.mod.addItems(self.name_model)
        self.mod.currentIndexChanged.connect(self.selectionchange)
        self.button1 = QPushButton(self.tr('Model Info'), self)
        self.button1.clicked.connect(self.give_info_model)
        spacer2 = QSpacerItem(50, 1)
        spacer = QSpacerItem(1, 50)

        # add the widgets representing the available models to a stack of widget
        self.free = FreeSpace()
        self.hecras1D = HEC_RAS1D(self.path_prj, self.name_prj)
        self.hecras2D = HEC_RAS2D(self.path_prj, self.name_prj)
        self.telemac = TELEMAC(self.path_prj, self.name_prj)
        self.rubar2d = Rubar2D(self.path_prj, self.name_prj)
        self.stack.addWidget(self.free)
        self.stack.addWidget(self.hecras1D)
        self.stack.addWidget(self.hecras2D)
        self.stack.addWidget(self.rubar2d)
        self.stack.addWidget(self.telemac)
        self.stack.setCurrentIndex(self.mod_act)

        # layout
        self.layout4 = QGridLayout()
        self.layout4.addWidget(l3, 0, 0)
        self.layout4.addWidget(self.mod, 1, 0)
        self.layout4.addItem(spacer2, 1, 1)
        self.layout4.addWidget(self.button1, 1, 2)
        self.layout4.addWidget(self.stack, 2, 0)
        self.layout4.addWidget(self.l1, 3, 0)
        self.layout4.addWidget(self.mod_loaded, 4, 0)
        self.layout4.addItem(spacer, 5, 1)
        self.setLayout(self.layout4)

    def selectionchange(self, i):
        """
        Change the widget reprsenting each hydrological model (all widget are in a stack)
        :param i: the number of the model (0=no model, 1=hecras1d, 2= hecras2D,...)
        :return:
        """

        self.mod_act = i
        self.stack.setCurrentIndex(self.mod_act)

    def give_info_model(self):
        """
        A function to show extra information about each hydrological model.
        The information should be in a text file with the same as the model in the model_hydo folder
        General info goes as the startof the text file. If the text is too long, add the keyword "MORE INFO"
        and the message box will add the supplementary information
        :return: None
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
    Very simple class with empty space, just to have only Qwidget in the stack
    """
    def __init__(self):

        super().__init__()
        spacer = QSpacerItem(1, 1)
        self.layout_s = QGridLayout()
        self.layout_s.addItem(spacer, 0, 0)
        self.setLayout(self.layout_s)


class SubHydroW(QWidget):
    """
    a class which is the parent of the class which can be used to open the hydrological model.
    So there are MainWindiws which provides the windows around the widget,
    Hydro2W which provide the widget in the windows and one class by hydrological model to really load the model.
    The latter classes have various methods in common, so they inherit from SubHydroW, this class.
    """

    def __init__(self, path_prj, name_prj):
        self.namefile = ['unknown file', 'unknown file']  # for children, careful with list index out of range
        self.pathfile = ['.', '.']
        self.attributexml = [' ', ' ']
        self.model_type = ' '
        self.save_fig = False
        self.extension = [[".txt"]]
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        super().__init__()

    def was_model_loaded_before(self, i=0):
        """
        A function to test if the model loaded before, if yes, update the attibutes anf the widgets
        :param i a number in case there is more than one file to load
        TO BE DONE load hdf5
        :return:
        """
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//" + self.attributexml[i])
            # if there is data in the project file about the model
            if child is not None:
                geo_name_path = child.text
                if os.path.isfile(geo_name_path):
                    self.namefile[i] = os.path.basename(geo_name_path)
                    self.pathfile[i] = os.path.dirname(geo_name_path)
                else:
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Previously Loaded File"))
                    self.msg2.setText(
                        self.tr("The file given in the project file does not exist. Hydrological model:" + self.model_type))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()

    def show_dialog(self, i=0):
        """
        A function to obtain the name of the file chosen by the user
        :param i a number in case there is more than one file to load
        :return: the name of the file, the path to this file
        """

        # find the filename based on user choice
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
            self.pathfile[i] = os.path.dirname(filename_path)
            self.namefile[i] = filename

    def save_xml(self, i=0):
        """
        A function to save the loaded data in the xml file
        :param i a number in case there is more than one file to save
        :return:
        """
        filename_path_file = os.path.join(self.pathfile[i], self.namefile[i])
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText(\
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
                child.text = filename_path_file
            doc.write(filename_path_pro, method="xml")

    def find_path_im(self):
        """
        A function to find the path where to save the figues, careful a simialr one is in estimhab_GUI.py
        :return: path_im
        """
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
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText( \
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            return
        return path_im


class HEC_RAS1D(SubHydroW):
    """
    The sub-windows which help to open the Hec-RAS data. Call the Hec-RAS loader and save the name
     of the files to the project xml file.
    """
    show_fig = pyqtSignal()

    def __init__(self, path_prj, name_prj):
        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):

        # update attibute for hec-ras 1d
        self.attributexml = ['geodata', 'resdata']
        self.model_type = 'HECRAS1D'
        self.extension = [['.g01', '.g02', '.g03', '.g04','.g05 ', '.g06', '.g07', '.g08',
                            '.g09', '.g10', '.g11', '.G01', '.G02'], ['.xml', '.rep', '.sdf']]

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

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_hec_ras_gui)
        spacer = QSpacerItem(1, 1)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(self.load_b, 2, 2)
        self.layout_hec.addWidget(self.cb, 2, 1)
        self.layout_hec.addItem(spacer, 3, 1)
        self.setLayout(self.layout_hec)

    def load_hec_ras_gui(self):
        """
        A function to execture the loading and saving the the HEC-ras file using Hec_ras.py
        :return:
        """
        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        path_im = self.find_path_im()
        #load hec_ras data
        if self.cb.isChecked():
            self.save_fig = True
        [xy_h, zone_v] = Hec_ras06.open_hecras(self.namefile[0], self.namefile[1], self.pathfile[0], self.pathfile[1], path_im, self.save_fig)
        if self.cb.isChecked():
            self.show_fig.emit()


class Rubar2D(SubHydroW):
    """
    The sub-windows which help to open the rubar data. Call the rubar loader and save the name
     of the files to the project xml file.
    """
    show_fig = pyqtSignal()

    def __init__(self, path_prj, name_prj):
        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):

        # update attibute for hec-ras 1d
        self.attributexml = ['rubar_geodata', 'tpsdata']
        self.model_type = 'RUBAR2D'
        self.extension = [['.mai'], ['.tps']]  # list of list in case there is more than one possible ext.

        # if there is the project file with rubar geo info, update the label and attibutes
        self.was_model_loaded_before(0)
        self.was_model_loaded_before(1)

        # label with the file name
        self.geo_t2 = QLabel(self.namefile[0], self)
        self.out_t2 = QLabel(self.namefile[1], self)

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.mai)', self)
        self.geo_b.clicked.connect(lambda: self.show_dialog(0))
        self.geo_b.clicked.connect(lambda: self.geo_t2.setText(self.namefile[0]))
        self.geo_b.clicked.connect(self.propose_next_file)

        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.tps)', self)
        self.out_b.clicked.connect(lambda: self.show_dialog(1))
        self.out_b.clicked.connect(lambda: self.out_t2.setText(self.namefile[1]))

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_rubar)
        spacer = QSpacerItem(1, 1)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(self.load_b, 2, 2)
        self.layout_hec.addWidget(self.cb, 2, 1)
        self.layout_hec.addItem(spacer, 3, 1)
        self.setLayout(self.layout_hec)

    def propose_next_file(self):
        """
        A function which avoid to the user to search for both file,
        it tries to find the second one when the first one is selected
        :return:
        """
        if len(self.extension[1]) == 1:  # would not work with more than one possible extension
            if self.out_t2.text() == 'unknown file':
                blob = self.namefile[0]
                self.out_t2.setText(blob[:-len(self.extension[0][0])] + self.extension[1][0])
                # keep the name in an attribute until we save it
                self.pathfile[1] = self.pathfile[0]
                self.namefile[1] = blob[:-len(self.extension[0][0])] + self.extension[1][0]

    def load_rubar(self):
        """
        A function to execture the loading and saving the the rubar file using rubar.py
        :return:
        """
        # update the xml file of the project
        self.save_xml(0)
        self.save_xml(1)
        path_im = self.find_path_im()
        if self.cb.isChecked():
            self.save_fig = True
        #load hec_ras data
        [v, h, coord_p, coord_c, ikle] = rubar.load_rubar2d(self.namefile[0], self.namefile[1],  self.pathfile[0], self.pathfile[1], path_im, self.save_fig)
        if self.cb.isChecked():
            self.show_fig.emit()


class HEC_RAS2D(SubHydroW):
    """
    The Qwidget which open the Hec-RAS data in 2D dimension
    """
    show_fig = pyqtSignal()

    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):

        # update attibutes
        self.attributexml = ['data2D']
        self.model_type = 'HECRAS2D'
        self.extension = [['.hdf']]

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

        # load button
        load_b = QPushButton('Load data and create hdf5', self)
        load_b.clicked.connect(self.load_hec_2d_gui)
        spacer = QSpacerItem(1, 20)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2, 0 , 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(l2, 1, 0)
        self.layout_hec2.addWidget(l3, 1, 1)
        self.layout_hec2.addWidget(l4, 1, 2)
        self.layout_hec2.addWidget(load_b, 2, 2)
        self.layout_hec2.addItem(spacer, 3, 1)
        self.layout_hec2.addWidget(self.cb, 2, 1)
        self.setLayout(self.layout_hec2)

    def load_hec_2d_gui(self):
        """
        The function which call the function which load hecras 2d and save name of file in the project file
         :return:
        """
        self.save_xml(0)
        path_im = self.find_path_im()
        # load the hec_ras data
        [v, h, elev, coord_p, coord_c, ikle] = hec_ras2D.load_hec_ras2d(self.namefile[0], self.pathfile[0])
        if self.cb.isChecked():
            hec_ras2D.figure_hec_ras2d(v, h, elev, coord_p, coord_c, ikle, path_im, [-1], [0])
            self.show_fig.emit()


class TELEMAC(SubHydroW):
    """
    The Qwidget which open the TELEMAC data
    """
    show_fig = pyqtSignal()
    def __init__(self, path_prj, name_prj):

        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):

        # update the attibutes
        self.attributexml = ['telemac_data']
        self.model_type = 'TELEMAC'
        self.extension = [['.res', '.slf']]

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

        # load button
        load_b = QPushButton('Load data and create hdf5', self)
        load_b.clicked.connect(self.load_telemac_gui)
        spacer = QSpacerItem(1, 20)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2,0 , 1)
        self.layout_hec2.addWidget(self.h2d_b, 0, 2)
        self.layout_hec2.addWidget(l2, 1, 0)
        self.layout_hec2.addWidget(l3, 1, 1)
        self.layout_hec2.addWidget(load_b, 2, 2)
        self.layout_hec2.addItem(spacer, 3, 1)
        self.layout_hec2.addWidget(self.cb, 2, 1)
        self.setLayout(self.layout_hec2)

    def load_telemac_gui(self):
        """
        The function which call the function which load htelemac and save tje name of file in the project file
         :return:
        """
        self.save_xml(0)
        # load the telemac data
        path_im = self.find_path_im()
        [v, h, coord_p, ikle] = selafin_habby1.load_telemac(self.namefile[0], self.pathfile[0])
        if self.cb.isChecked():
            selafin_habby1.plot_vel_h(coord_p, h, v, path_im)
            self.show_fig.emit()


class SubstrateW(SubHydroW):
    """
    This is the widget used to load the substrate. It is practical to re-use some of the method from SubHydroW.
    So this class inherit from SubHydroW.
    """
    show_fig = pyqtSignal()
    def __init__(self, path_prj, name_prj):
        super().__init__(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):

        # update attribute
        self.attributexml = ['substrate_data', 'att_name']
        self.model_type = 'SUBSTRATE'
        self.extension = [['.txt', '.shp', '.asc']]
        self.name_att = ''

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
        spacer = QSpacerItem(1, 140)
        spacer2 = QSpacerItem(150, 1)
        self.cb = QCheckBox(self.tr('Show figures'), self)

        #layout
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
        self.layout_sub.addItem(spacer, 5, 0)
        self.layout_sub.addItem(spacer2, 5, 3)
        self.layout_sub.addWidget(self.cb, 3, 3)
        self.setLayout(self.layout_sub)

    def load_sub_gui(self):
        # save path and name substrate
        self.save_xml(0)
        # only save attribute name if shapefile
        self.name_att = self.e2.text()
        blob, ext = os.path.splitext(self.namefile[0])
        path_im = self.find_path_im()
        if ext == '.shp':
            if not self.name_att:
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Save Substrate Data"))
                self.msg2.setText(self.tr("No attribute name was given to load the shapefile"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
                return
            self.pathfile[1] = ''
            self.namefile[1] = self.name_att  # avoid to code things again
            self.save_xml(1)
        # load substrate
            [coord_p, ikle_sub, sub_info] = substrate.load_sub_shp(self.namefile[0], self.pathfile[0], self.name_att)
            if self.cb.isChecked():
                substrate.fig_substrate(coord_p, ikle_sub, sub_info, path_im)
        elif ext == '.txt' or ext == ".asc":
            [coord_pt, ikle_subt, sub_infot, x, y, sub] = substrate.load_sub_txt(self.namefile[0], self.pathfile[0])
            if self.cb.isChecked():
                substrate.fig_substrate(coord_pt, ikle_subt, sub_infot, path_im, x, y, sub)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("File type"))
            self.msg2.setText(self.tr("Unknown extension for substrate data, the model will try to load as .txt"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            [coord_pt, ikle_subt, sub_infot, x, y, sub] = substrate.load_sub_txt(self.namefile[0], self.pathfile[0])
            if self.cb.isChecked():
                substrate.fig_substrate(coord_pt, ikle_subt, sub_infot, path_im, x, y, sub)
        if self.cb.isChecked():
            self.show_fig.emit()

    def get_att_name(self):
        """
        A function to get the attribute name of the shape file which is possibly int e project xml file.
        :return:
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





