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
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication, QVariant, QAbstractTableModel
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, \
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QProgressBar, QTextEdit, QTableView
from src_GUI import preferences_GUI
from src import hdf5_mod
from src import plot_mod
from multiprocessing import Process, Queue, Value


class ToolsTab(QScrollArea):
    """
    This class contains the tab with Graphic production biological information (the curves of preference).
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.plot_list_combobox = QComboBox()
        self.plot_previous_button = QPushButton("<<")
        self.plot_next_button = QPushButton(">>")
        self.plot_wigdet_layout = QHBoxLayout()
        self.init_iu()

    def init_iu(self):
        # DataExplorerFrame
        self.tools_frame = ToolsFrame()

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # add layout
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(self.tools_frame)


class ToolsFrame(QFrame):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """ File selection """
        # types_hdf5_QComboBox
        self.types_hdf5_QLabel = QLabel(self.tr('file types'))
        self.types_hdf5_QComboBox = QComboBox()
        self.types_hdf5_layout = QVBoxLayout()
        self.types_hdf5_layout.setAlignment(Qt.AlignTop)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QLabel)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QComboBox)

        # names_hdf5_QListWidget
        self.names_hdf5_QLabel = QLabel(self.tr('filenames'))
        self.names_hdf5_QListWidget = QListWidget()
        self.names_hdf5_QListWidget.setMinimumWidth(250)
        self.names_hdf5_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.names_hdf5_layout = QVBoxLayout()
        self.names_hdf5_layout.setAlignment(Qt.AlignTop)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QLabel)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QListWidget)

        """ Graphic producer """
        # variable_QListWidget
        self.variable_hdf5_QLabel = QLabel(self.tr('variables'))
        self.variable_QListWidget = QListWidget()
        self.variable_QListWidget.setMinimumWidth(130)
        self.variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.variable_hdf5_layout = QVBoxLayout()
        self.variable_hdf5_layout.setAlignment(Qt.AlignTop)
        self.variable_hdf5_layout.addWidget(self.variable_hdf5_QLabel)
        self.variable_hdf5_layout.addWidget(self.variable_QListWidget)

        # units_QListWidget
        self.units_QLabel = QLabel(self.tr('units'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setMinimumWidth(50)
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_layout = QVBoxLayout()
        self.units_layout.setAlignment(Qt.AlignTop)
        self.units_layout.addWidget(self.units_QLabel)
        self.units_layout.addWidget(self.units_QListWidget)

        # export_type_QComboBox
        self.export_type_QLabel = QLabel(self.tr('View or export ?'))
        self.export_type_QComboBox = QComboBox()
        self.export_type_layout = QVBoxLayout()
        self.export_type_layout.setAlignment(Qt.AlignTop)
        self.export_type_layout.addWidget(self.export_type_QLabel)
        self.export_type_layout.addWidget(self.export_type_QComboBox)

        # buttons plot_button
        self.plot_button = QPushButton(self.tr("run"))
        self.plot_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.export_type_layout.addWidget(self.plot_button)

        # stop plot_button
        self.plot_stop_button = QPushButton(self.tr("stop"))
        self.plot_stop_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.plot_stop_button.setEnabled(False)
        self.export_type_layout.addWidget(self.plot_stop_button)

        # type plot
        plot_type_qlabel = QLabel(self.tr("figure type :"))
        self.plot_map_QCheckBox = QCheckBox(self.tr("map"))
        self.plot_map_QCheckBox.setChecked(False)
        self.plot_result_QCheckBox = QCheckBox(self.tr("result"))
        self.plot_result_QCheckBox.setChecked(False)

        # progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, 0))

        # attributes hdf5
        self.hdf5_attributes_QTextEdit = QTableView(self)
        self.hdf5_attributes_QTextEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.hdf5_attributes_QTextEdit.verticalHeader().setVisible(False)
        self.hdf5_attributes_QTextEdit.horizontalHeader().setVisible(False)

        """ File selection """
        # SELECTION FILE
        selectionfile_layout = QHBoxLayout()
        selectionfile_layout.addLayout(self.types_hdf5_layout)
        selectionfile_layout.addLayout(self.names_hdf5_layout)
        selectionfile_group = QGroupBox(self.tr("File selection"))
        selectionfile_group.setLayout(selectionfile_layout)

        """ Graphic producer """
        # PLOT GROUP
        plot_layout = QHBoxLayout()
        plot_layout.addLayout(self.variable_hdf5_layout, 4)
        plot_layout.addLayout(self.units_layout, 1)
        plot_layout.addLayout(self.export_type_layout)
        plot_layout2 = QVBoxLayout()
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(plot_type_qlabel)
        plot_type_layout.addWidget(self.plot_map_QCheckBox)
        plot_type_layout.addWidget(self.plot_result_QCheckBox)
        plot_type_layout.setAlignment(Qt.AlignLeft)
        plot_layout2.addLayout(plot_layout)
        plot_layout2.addLayout(plot_type_layout)
        plot_layout2.addWidget(self.progress_bar)
        plot_group = QGroupBox(self.tr("Figure producer"))
        plot_group.setLayout(plot_layout2)

        """ File information """
        # ATTRIBUTE GROUP
        attributes_layout = QVBoxLayout()
        attributes_layout.addWidget(self.hdf5_attributes_QTextEdit)
        attributes_group = QGroupBox(self.tr("file informations"))
        attributes_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        attributes_group.setLayout(attributes_layout)

        # first line layout (selection + graphic)
        hbox_layout = QHBoxLayout()
        hbox_layout.addWidget(selectionfile_group)
        hbox_layout.addWidget(plot_group)

        # second line layout (attribute)
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(attributes_group)

        # global layout
        global_layout = QVBoxLayout(self)
        global_layout.addLayout(hbox_layout)
        global_layout.addLayout(vbox_layout)

        # add layout to group
        #self.setLayout(global_layout)
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
