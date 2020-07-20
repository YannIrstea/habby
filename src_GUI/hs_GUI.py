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
from multiprocessing import Process, Value

from PyQt5.QtCore import pyqtSignal, Qt, QAbstractTableModel, QRect, QPoint, QVariant
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, QSpacerItem, \
    QComboBox, QMessageBox, QFrame, QHeaderView, QLineEdit, QGridLayout, QFileDialog, QStyleOptionTab, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QTableView, QTabBar, QStylePainter, QStyle, \
    QCheckBox, QListWidgetItem
from src import hydrosignature

from src.tools_mod import QGroupBoxCollapsible
from src.hydraulic_process_mod import MyProcessList
from src import hdf5_mod
from src import plot_mod
from src import tools_mod
from src.project_properties_mod import load_project_properties


class HsTab(QScrollArea):
    """
    This class contains the tab with Graphic production biological information (the curves of preference).
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "hs"
        self.tab_position = 6
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        self.hsframe = HsFrame(self.path_prj, self.name_prj)
        self.setWidget(self.hsframe)

    # load_hydraulic_cut_to_hdf5


class HsFrame(QFrame):
    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.classhv = None
        self.hyd_tin = None
        self.xy_node = None
        self.hv_node = None
        self.nbreaches = 0  # should be an integer

        self.initUI()

    def initUI(self):
        self.hsframelayout = QGridLayout()

        hsinputlist = HsInputList(self.path_prj, self.name_prj)
        # select file button
        scfbutton = SelectFileButton(self.tr("Select class file"), self, "class")
        shfbutton = SelectFileButton(self.tr("Select hydraulic data file"), self, "xyhv")
        stfbutton = SelectFileButton(self.tr("Select TIN file"), self, "triangles")
        self.classfilelabel = QLabel(self.tr("unknown"))
        self.xyhvfilelabel = QLabel(self.tr("unknown"))
        self.trianglefilelabel = QLabel(self.tr("unknown"))

        # self.hsframelayout.addWidget(QLabel("available .hyd files"))
        # self.hsframelayout.addWidget(hsinputlist)
        self.hsframelayout.addWidget(QLabel(self.tr("Hydraulic classes: ")), 0, 0)
        self.hsframelayout.addWidget(self.classfilelabel, 0, 1)
        self.hsframelayout.addWidget(scfbutton, 0, 3)
        self.hsframelayout.addWidget(QLabel(self.tr("Hydraulic data: ")), 1, 0)
        self.hsframelayout.addWidget(self.xyhvfilelabel, 1, 1)
        self.hsframelayout.addWidget(shfbutton, 1, 3)
        self.hsframelayout.addWidget(QLabel(self.tr("Triangulated Irregular Network: ")), 2, 0)
        self.hsframelayout.addWidget(self.trianglefilelabel, 2, 1)
        self.hsframelayout.addWidget(stfbutton, 2, 3)
        self.setLayout(self.hsframelayout)

    def open_class_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select hydraulic class file"),
                                                  self.path_prj + "\\input", self.tr("Text files") + " (*.txt)")
        try:
            self.classhv = hydrosignature.hydraulic_class_from_file(filename)
            self.classfilelabel.setText(filename.lstrip(self.path_prj))
        except FileNotFoundError:
            pass

    def open_xyhv_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select hydraulic data file"),
                                                  self.path_prj + "\\input",
                                                  self.tr("Text or hdf5 files") + " (*.txt *.hyd *.hab)")
        if filename.endswith(".txt"):
            try:
                self.xy_node, self.hv_node = hydrosignature.hydraulic_data_from_file(filename)
                self.xyhvfilelabel.setText(filename.lstrip(self.path_prj))
                self.nbreaches = 1
            except FileNotFoundError:
                pass
        elif filename.endswith((".hyd", ".hab")):
            try:
                self.xy_node, self.hv_node, self.hyd_tin, self.reach_list = hydrosignature.hs_data_from_hdf5_file(
                    filename)
                # TODO write hs_data_from_hdf5_file function
                self.xyhvfilelabel.setText(filename.lstrip(self.path_prj))
                self.trianglefilelabel.setText(filename.lstrip(self.path_prj))
                self.nbreaches = len(self.reach_list)

                pass
            except FileNotFoundError:
                pass

    def open_tin_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select Triangulated Irregular Network file"),
                                                  self.path_prj + "\\input",
                                                  self.tr("Text or hdf5 files") + " (*.txt *.hyd *.hab)")
        if filename.endswith(".txt"):
            try:
                self.hyd_tin = hydrosignature.tin_from_file(filename)
                # TODO write function to extract data from tin file
                self.trianglefilelabel.setText(filename.lstrip(self.path_prj))
            except FileNotFoundError:
                pass
        elif filename.endswith((".hyd", ".hab")):
            try:
                self.xy_node, self.hv_node, self.hyd_tin = hydrosignature.hs_data_from_hdf5_file(filename)
                self.xyhvfilelabel.setText(filename.lstrip(self.path_prj))
                self.trianglefilelabel.setText(filename.lstrip(self.path_prj))
            except FileNotFoundError:
                pass


class HsInputList(QListWidget):
    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.setSelectionMode(1)
        filenames = os.listdir(path_prj + "\\hdf5")
        self.hydfiles = [s for s in filenames if s.endswith(".hyd")]
        self.addItems(self.hydfiles)
        # for i in range(len(hydfiles)-1,-1,-1):
        #     if not hydfiles[i].endswith("hyd"):
        #         hydfiles.


class SelectFileButton(QPushButton):
    def __init__(self, label, frame, filetype):
        super(SelectFileButton, self).__init__(label, frame)
        if filetype == "class":
            self.clicked.connect(frame.open_class_file)
        elif filetype == "xyhv":
            self.clicked.connect(frame.open_xyhv_file)
        elif filetype == "triangles":
            self.clicked.connect(frame.open_tin_file)

    # def select_file(self):
    #     fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "All Files (*);;Python Files (*.py)")
