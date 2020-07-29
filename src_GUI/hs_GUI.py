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
from PyQt5.QtGui import QStandardItemModel, QPixmap
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, QSpacerItem, \
    QComboBox, QMessageBox, QFrame, QHeaderView, QLineEdit, QGridLayout, QFileDialog, QStyleOptionTab, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QTableView, QTabBar, QStylePainter, QStyle, \
    QCheckBox, QListWidgetItem, QRadioButton
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

        # computing
        self.computing_group = ComputingGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Computing"))
        self.computing_group.setChecked(True)

        # visual
        self.visual_group = VisualGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Visualisation"))
        self.visual_group.setChecked(True)

        # visual
        self.compare_group = CompareGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Comparison"))
        self.compare_group.setChecked(True)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addWidget(self.computing_group)
        global_layout.addWidget(self.visual_group)
        global_layout.addWidget(self.compare_group)
        global_layout.addStretch()


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

        # refresh_filenames
        self.refresh_filenames()

    def init_ui(self):
        # file_selection
        file_selection_label = QLabel(self.tr("Select a 2D mesh file :"))
        self.file_selection_listwidget = QListWidget()
        self.file_selection_listwidget.setSelectionMode(QAbstractItemView.SingleSelection)
        file_computed_label = QLabel(self.tr("HS value computed ?"))
        self.file_computed_checkbox = QCheckBox()
        input_class_label = QLabel(self.tr("Input class (.txt)"))
        self.input_class_filename = QLabel(self.tr("..."))
        self.input_class_pushbutton = QPushButton(self.tr("Select file"))
        hs_export_txt_label = QLabel(self.tr("Export results (.txt)"))
        self.hs_export_txt_checkbox = QCheckBox()
        hs_export_mesh_label = QLabel(self.tr("Export mesh results (.hyd or .hab)"))
        self.hs_export_mesh_checkbox = QCheckBox()
        self.computation_pushbutton = QPushButton(self.tr("run"))

        grid_layout = QGridLayout()

        grid_layout.addWidget(file_selection_label, 0, 0)
        grid_layout.addWidget(self.file_selection_listwidget, 1, 0)
        grid_layout.addWidget(file_computed_label, 0, 1, alignment=Qt.AlignCenter)
        grid_layout.addWidget(self.file_computed_checkbox, 1, 1, alignment=Qt.AlignCenter)
        grid_layout.addWidget(input_class_label, 2, 0)
        grid_layout.addWidget(self.input_class_filename, 2, 1, alignment=Qt.AlignCenter)
        grid_layout.addWidget(self.input_class_pushbutton, 2, 2)
        grid_layout.addWidget(hs_export_txt_label, 3, 0)
        grid_layout.addWidget(self.hs_export_txt_checkbox, 3, 1, alignment=Qt.AlignCenter)
        grid_layout.addWidget(hs_export_mesh_label, 4, 0)
        grid_layout.addWidget(self.hs_export_mesh_checkbox, 4, 1, alignment=Qt.AlignCenter)
        grid_layout.addWidget(self.computation_pushbutton, 5, 2)

        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)

        self.setLayout(grid_layout)

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

        self.file_selection_listwidget = QListWidget()
        self.reach_QListWidget = QListWidget()
        self.units_QListWidget = QListWidget()


        # axes mod


        self.axe_mod_1_radio = QRadioButton()
        self.axe_mod_1_radio.setChecked(True)  # TODO: save in json default and last choice (to be loaded)
        self.axe_mod_1_radio.toggled.connect(self.change_axe_mod)
        self.axe_mod_1_pixmap = QPixmap(r"translation/axe_mod_1.PNG").scaled(75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # ,
        axe_mod_1_label = QLabel()
        axe_mod_1_label.setPixmap(self.axe_mod_1_pixmap)
        self.axe_mod_2_radio = QRadioButton()
        self.axe_mod_2_radio.toggled.connect(self.change_axe_mod)
        self.axe_mod_2_pixmap = QPixmap(r"translation/axe_mod_2.PNG").scaled(75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # ,
        axe_mod_2_label = QLabel()
        axe_mod_2_label.setPixmap(self.axe_mod_2_pixmap)
        self.axe_mod_3_radio = QRadioButton()
        self.axe_mod_3_radio.toggled.connect(self.change_axe_mod)
        self.axe_mod_3_pixmap = QPixmap(r"translation/axe_mod_3.PNG").scaled(75, 75, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # ,
        axe_mod_3_label = QLabel()
        axe_mod_3_label.setPixmap(self.axe_mod_3_pixmap)

        axe_mod_layout = QHBoxLayout()
        axe_mod_layout.addWidget(self.axe_mod_1_radio)
        axe_mod_layout.addWidget(axe_mod_1_label)
        axe_mod_layout.addWidget(self.axe_mod_2_radio)
        axe_mod_layout.addWidget(axe_mod_2_label)
        axe_mod_layout.addWidget(self.axe_mod_3_radio)
        axe_mod_layout.addWidget(axe_mod_3_label)

        selection_layout = QHBoxLayout()
        selection_layout.addWidget(self.file_selection_listwidget)
        selection_layout.addWidget(self.reach_QListWidget)
        selection_layout.addWidget(self.units_QListWidget)
        selection_layout.addLayout(axe_mod_layout)

        general_layout = QVBoxLayout()
        general_layout.addLayout(selection_layout)


        self.setLayout(general_layout)

    def change_axe_mod(self):
        radio = self.sender()



class CompareGroup(QGroupBoxCollapsible):
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


        grid_layout = QGridLayout()
        # grid_layout.addWidget(self.input_pushbutton, 0, 0)
        # grid_layout.addWidget(self.output_pushbutton, 1, 0)

        self.setLayout(grid_layout)