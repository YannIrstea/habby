import os
import Hec_ras06
import hec_ras2D
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

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
        self.name_model = ["", "HEC-RAS 1D", "HEC-RAS 2D", "MAGE", 'MASCARET', "RIVER 2D", "RUBAR", "TELEMAC"]
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
        self.stack.addWidget(self.free)
        self.stack.addWidget(self.hecras1D)
        self.stack.addWidget(self.hecras2D)
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


class HEC_RAS1D(QWidget):
    """
    The sub-windows which help to open the Hec-RAS data. Call the Hec-RAS loader and save the name
     of the files to the project xml file.
    """
    def __init__(self, path_prj, name_prj):

        self.pathgeo_hecras1d = '.'
        self.pathres_hecras1d = '.'
        self.geo_hecras1d = 'unknown file'
        self.res_hecras1d = 'unknown file'
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        super().__init__()
        self.init_iu()

    def init_iu(self):

        # geometry data
        l1 = QLabel(self.tr('<b> Geometry data </b>'))
        self.geo_b = QPushButton('Choose file (.g0x)', self)
        self.geo_b.clicked.connect(self.show_dialog_geo)

        # output data
        l2 = QLabel(self.tr('<b> Output data </b>'))
        self.out_b = QPushButton('Choose file \n (.xml, .sdf, or .res file)', self)
        self.out_b.clicked.connect(self.show_dialog_res)

        # load button
        self.load_b = QPushButton('Load data and create hdf5', self)
        self.load_b.clicked.connect(self.load_hec_ras_gui)
        spacer = QSpacerItem(1, 1)

        # if there is the project file with hecras geo info, update the label and attibutes
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//geodata")
            # if there is data in the project file about HECras
            if child is not None:
                geo_name_path = child.text
                if os.path.isfile(geo_name_path):
                    self.geo_hecras1d = os.path.basename(geo_name_path)
                    self.pathgeo_hecras1d = os.path.dirname(geo_name_path)
                else:
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Geometry file"))
                    self.msg2.setText(self.tr("The geometry file given in the project file does not exist."))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
            # idem for the results
            child2 = root.find(".//resdata")
            if child2 is not None:
                res_name_path = child2.text
                if os.path.isfile(res_name_path):
                    self.res_hecras1d = os.path.basename(res_name_path)
                    self.pathres_hecras1d = os.path.dirname(res_name_path)
                else:
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Geometry file"))
                    self.msg2.setText(self.tr("The result file given in the project file does not exist."))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
            # if there is an hdf5
            # TO BE ADDED
        # label with the file name
        self.out_t2 = QLabel(self.res_hecras1d, self)
        self.geo_t2 = QLabel(self.geo_hecras1d , self)

        # layout
        self.layout_hec = QGridLayout()
        self.layout_hec.addWidget(l1, 0, 0)
        self.layout_hec.addWidget(self.geo_t2,0, 1)
        self.layout_hec.addWidget(self.geo_b, 0, 2)
        self.layout_hec.addWidget(l2, 1, 0)
        self.layout_hec.addWidget(self.out_t2, 1, 1)
        self.layout_hec.addWidget(self.out_b, 1, 2)
        self.layout_hec.addWidget(self.load_b, 2, 2)
        self.layout_hec.addItem(spacer, 3, 1)
        self.setLayout(self.layout_hec)

    def show_dialog_geo(self):
        """
        A function to obtain the name of the geo file from hec-ras
        :param
        :return: the name of the file, the path to this file
        """

        # find the filename based on use choice
        # why [0] : getOpenFilename return a tuple [0,1,2], we need only the filename
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathgeo_hecras1d)[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            pass
        else:
            filename = os.path.basename(filename_path)
            # check extension
            blob, ext_geo = os.path.splitext(filename)
            if ext_geo[:3] != '.g0' and ext_geo[:3] != '.G0':
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Geometry file"))
                self.msg2.setText(self.tr("Needed Type for the geometry file of HEC-RAS: .g0X (g01, g02,...) "))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
            # write the name on the widget
            self.geo_t2.setText(filename)
            # keep the name in an attribute until we save it
            self.pathgeo_hecras1d = os.path.dirname(filename_path)
            self.geo_hecras1d = filename

    def show_dialog_res(self):
        """
        A function to obtain the name of the res file from hec-ras
        :param
        :return: the name of the file, the path to this file
        """

        # find the filename based on use choice
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.pathres_hecras1d)[0]
        # exeption: "cancel"
        if not filename_path:
            pass
        else:
            filename = os.path.basename(filename_path)
            # check extension
            blob, ext_res = os.path.splitext(filename)
            if ext_res != '.xml' and ext_res != '.rep' and ext_res != '.sdf':
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Result file"))
                self.msg2.setText(self.tr("Needed Type for the result file of HEC-RAS: .xml, .rep, .sdf "))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
            # write the name on the widget
            self.out_t2.setText(filename)
            # keep the name in an attribute until we save it
            self.pathres_hecras1d = os.path.dirname(filename_path)
            self.res_hecras1d = filename

    def load_hec_ras_gui(self):
        """
        A function to execture the loading and saving the the HEC-ras file using Hec_ras.py
        :return:
        """
        filename_path_res = os.path.join(self.pathres_hecras1d, self.res_hecras1d)
        filename_path_geo = os.path.join(self.pathgeo_hecras1d, self.geo_hecras1d)
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
            child1 = root.find(".//HECRAS")
            if child1 is None:
                child1 = ET.SubElement(root, "HECRAS")
            child = root.find(".//geodata")
            if child is None:
                child = ET.SubElement(child1, "geodata")
                child.text = filename_path_geo
            else:
                child.text = filename_path_geo
            # res data
            child = root.find(".//resdata")
            if child is None:
                child = ET.SubElement(child1, "resdata")
                child.text = filename_path_res
            else:
                child.text = filename_path_res
            doc.write(filename_path_pro, method="xml")

        # load the hec_ras data
        Hec_ras06.open_hecras(self.geo_hecras1d, self.res_hecras1d, self.pathgeo_hecras1d, self.pathres_hecras1d)


class HEC_RAS2D(QWidget):
    """
    The Qwidget which open the Hec-RAS data in 2D dimension
    """
    def __init__(self, path_prj, name_prj):

        self.path_hecras2d = '.'
        self.file_hecras2d = 'unknown file'
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        super().__init__()
        self.init_iu(path_prj, name_prj)

    def init_iu(self, path_prj, name_prj):

        # geometry and output data
        l1 = QLabel(self.tr('<b> Geometry and output data </b>'))
        h2d_b = QPushButton('Choose file (.hdf, .h5)', self)
        h2d_b.clicked.connect(self.show_dialog_2d)
        l2 = QLabel(self.tr('<b> Options </b>'))
        l3 = QLabel('All time step', self)
        l4 = QLabel('All flow area', self)

        # if there is the project file with hecras info, update the label and attibutes
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//data_2D")
            # if there is data in the project file about HECras
            if child is not None:
                res_name_path = child.text
                if os.path.isfile(res_name_path):
                    self.file_hecras2d = os.path.basename(res_name_path)
                    self.path_hecras2d = os.path.dirname(res_name_path)
                else:
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Result file"))
                    self.msg2.setText(self.tr("The result file given in the project file does not exist."))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
        self.h2d_t2 = QLabel(self.file_hecras2d, self)

        # load button
        load_b = QPushButton('Load data and create hdf5', self)
        load_b.clicked.connect(self.load_hec_2d_gui)
        spacer = QSpacerItem(1, 20)

        # layout
        self.layout_hec2 = QGridLayout()
        self.layout_hec2.addWidget(l1, 0, 0)
        self.layout_hec2.addWidget(self.h2d_t2,0 , 1)
        self.layout_hec2.addWidget(h2d_b, 0, 2)
        self.layout_hec2.addWidget(l2, 1, 0)
        self.layout_hec2.addWidget(l3, 1, 1)
        self.layout_hec2.addWidget(l4, 1, 2)
        self.layout_hec2.addWidget(load_b, 2, 2)
        self.layout_hec2.addItem(spacer, 3, 1)
        self.setLayout(self.layout_hec2)

    def show_dialog_2d(self):
        """
        A function to obtain the name of the res file from hec-ras
        :param
        :return: the name of the file, the path to this file
        """
        # find the filename based on use choice
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_hecras2d)[0]
        # exeption: you should be able to clik on "cancel"
        if not filename_path:
            pass
        else:
            filename = os.path.basename(filename_path)
            # check extension
            blob, ext_res = os.path.splitext(filename)
            if ext_res != '.hdf' and ext_res != '.h5':
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Output file"))
                self.msg2.setText(self.tr("Needed Type for the result file of HEC-RAS 2D: .hdf or .h5"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
            # write the name on the widget
            self.h2d_t2.setText(filename)
            # keep the name in an attribute until we save it
            self.path_hecras2d = os.path.dirname(filename_path)
            self.file_hecras2d = filename

    def load_hec_2d_gui(self):
        """
        The function which call the function which load hecras 2d and dave name of file in the project file
         :return:
        """
        filename_path_res = os.path.join(self.path_hecras2d, self.file_hecras2d)
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
            # hec ras data
            child1 = root.find(".//HECRAS")
            if child1 is None:
                child1 = ET.SubElement(root, "HECRAS")
            child = root.find(".//data_2D")
            if child is None:
                child = ET.SubElement(child1, "data_2D")
                child.text = filename_path_res
            else:
                child.text = filename_path_res
            doc.write(filename_path_pro, method="xml")

        # load the hec_ras data
        [v, h, elev, coord_p, coord_c, ikle] = hec_ras2D.load_hec_ras2d(self.file_hecras2d, self.path_hecras2d)
        hec_ras2D.figure_hec_ras2d(v, h, elev, coord_p, coord_c, ikle, [-1], [0])
