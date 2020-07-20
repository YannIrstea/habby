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
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        # tools frame
        tools_frame = QFrame()
        tools_frame.setFrameShape(QFrame.NoFrame)
        tools_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # file_selection
        self.file_selection_label = QLabel(self.tr("Select a 2D mesh file :"))
        self.file_selection_listwidget = QListWidget()
        file_computed_layout = QHBoxLayout()
        file_computed_label = QLabel(self.tr("HS value computed ?"))
        self.file_computed_checkbox = QCheckBox()
        file_computed_layout.addWidget(file_computed_label)
        file_computed_layout.addWidget(self.file_computed_checkbox)
        file_selection_layout = QVBoxLayout()
        file_selection_layout.addWidget(self.file_selection_label)
        file_selection_layout.addWidget(self.file_selection_listwidget)
        file_selection_layout.addLayout(file_computed_layout)

        # computing
        self.computing_group = ComputingGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Computing"))
        self.computing_group.setChecked(True)

        # visual
        self.visual_group = VisualGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Visualisation"))
        self.visual_group.setChecked(True)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addLayout(file_selection_layout)
        global_layout.addWidget(self.computing_group)
        global_layout.addWidget(self.visual_group)
        global_layout.addStretch()

        # refresh_filenames
        self.refresh_filenames()

    def refresh_filenames(self):
        # get list of file name by type
        hyd_names = hdf5_mod.get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
        hab_names = hdf5_mod.get_filename_by_type_physic("habitat", os.path.join(self.path_prj, "hdf5"))
        names = hyd_names + hab_names
        self.file_selection_listwidget.blockSignals(True)
        self.file_selection_listwidget.clear()
        if names:
            self.file_selection_listwidget.addItems(names)
        self.file_selection_listwidget.blockSignals(False)

    def open_class_file(self):
            filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select hydraulic class file"),
                                                      self.path_prj + "\\input", self.tr("Text files") + " (*.txt)")
            try:
                self.classhv = hydrosignature.hydraulic_class_from_file(filename)
                self.classfilelabel.setText(filename.lstrip(self.path_prj))
            except FileNotFoundError:
                pass


class ComputingGroup(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.path_last_file_loaded = self.path_prj
        self.setTitle(title)
        self.init_ui()

    def init_ui(self):
        input_class_label = QLabel(self.tr("Input class (.txt)"))
        self.input_class_filename = QLabel(self.tr("..."))
        self.input_class_pushbutton = QPushButton(self.tr("Select file"))
        hs_export_txt_label = QLabel(self.tr("Export results (.txt)"))
        self.hs_export_txt_checkbox = QCheckBox()
        hs_export_mesh_label = QLabel(self.tr("Export mesh results (.hyd or .hab)"))
        self.hs_export_mesh_checkbox = QCheckBox()
        self.computation_pushbutton = QPushButton(self.tr("run"))

        grid_layout = QGridLayout()
        grid_layout.addWidget(input_class_label, 0, 0)
        grid_layout.addWidget(self.input_class_filename, 0, 1)
        grid_layout.addWidget(self.input_class_pushbutton, 0, 2)
        grid_layout.addWidget(hs_export_txt_label, 1, 0)
        grid_layout.addWidget(self.hs_export_txt_checkbox, 1, 2, alignment=Qt.AlignCenter)
        grid_layout.addWidget(hs_export_mesh_label, 2, 0)
        grid_layout.addWidget(self.hs_export_mesh_checkbox, 2, 2, alignment=Qt.AlignCenter)
        grid_layout.addWidget(self.computation_pushbutton, 3, 2)

        self.setLayout(grid_layout)


class VisualGroup(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.path_last_file_loaded = self.path_prj
        self.setTitle(title)
        self.init_ui()

    def init_ui(self):
        self.input_pushbutton = QPushButton(self.tr("show input classes"))
        self.output_pushbutton = QPushButton(self.tr("show output results"))

        grid_layout = QGridLayout()
        grid_layout.addWidget(self.input_pushbutton, 0, 0)
        grid_layout.addWidget(self.output_pushbutton, 1, 0)

        self.setLayout(grid_layout)