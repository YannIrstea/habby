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
import h5py
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QListWidget, QAbstractItemView, \
    QComboBox, QMessageBox,\
    QVBoxLayout, QHBoxLayout, QGroupBox, QSpacerItem, QSizePolicy
from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg as FigureCanvas)
from matplotlib.figure import (Figure)
from src import load_hdf5


class PlotTab(QWidget):
    """
    The class which support the creation and management of the output. It is notably used to select the options to
    create the figures.

    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.plot_list_combobox = QComboBox()
        self.plot_previous_button = QPushButton("<<")
        self.plot_next_button = QPushButton(">>")
        self.plot_wigdet_layout = QHBoxLayout()
        self.init_iu()

    def init_iu(self):
        # GroupPlot
        self.GroupPlot_first = GroupPlot()

        # add widgets to layout
        self.plot_layout = QVBoxLayout()  # vetical layout
        self.plot_layout.setAlignment(Qt.AlignTop)
        self.plot_layout.addWidget(self.GroupPlot_first)

        # add layout
        self.setLayout(self.plot_layout)


class GroupPlot(QGroupBox):
    """
    zzzz
    """
    def __init__(self):
        super().__init__()
        # title
        self.setTitle(self.tr('Graphic selection'))

        # types_hdf5_QComboBox
        self.types_hdf5_QLabel = QLabel(self.tr('hdf5 types :'))
        self.types_hdf5_QComboBox = QComboBox()
        self.types_hdf5_list = ["", "hydraulic", "substrat", "habitat"]
        self.types_hdf5_QComboBox.addItems(self.types_hdf5_list)
        self.types_hdf5_QComboBox.currentIndexChanged.connect(self.types_hdf5_change)
        self.types_hdf5_layout = QVBoxLayout()
        self.types_hdf5_layout.setAlignment(Qt.AlignTop)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QLabel)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QComboBox)

        # names_hdf5_QListWidget
        self.names_hdf5_QLabel = QLabel(self.tr('hdf5 files :'))
        self.names_hdf5_QListWidget = QListWidget()
        self.names_hdf5_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.names_hdf5_QListWidget.itemSelectionChanged.connect(self.names_hdf5_change)
        self.names_hdf5_layout = QVBoxLayout()
        self.names_hdf5_layout.setAlignment(Qt.AlignTop)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QLabel)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QListWidget)

        # variable_QListWidget
        self.variable_hdf5_QLabel = QLabel(self.tr('variables :'))
        self.variable_QListWidget = QListWidget()
        self.variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.variable_hdf5_layout = QVBoxLayout()
        self.variable_hdf5_layout.setAlignment(Qt.AlignTop)
        self.variable_hdf5_layout.addWidget(self.variable_hdf5_QLabel)
        self.variable_hdf5_layout.addWidget(self.variable_QListWidget)

        # units_QListWidget
        self.units_QLabel = QLabel(self.tr('units :'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_layout = QVBoxLayout()
        self.units_layout.setAlignment(Qt.AlignTop)
        self.units_layout.addWidget(self.units_QLabel)
        self.units_layout.addWidget(self.units_QListWidget)

        # types_plot_QComboBox
        self.types_plot_QLabel = QLabel(self.tr('type of plot :'))
        self.types_plot_QComboBox = QComboBox()
        self.types_plot_QComboBox.addItems(["view interactive graphics", "export files graphics", "both"])
        self.types_plot_layout = QVBoxLayout()
        self.types_plot_layout.setAlignment(Qt.AlignTop)
        self.types_plot_layout.addWidget(self.types_plot_QLabel)
        self.types_plot_layout.addWidget(self.types_plot_QComboBox)

        # buttons plot_button
        self.plot_button = QPushButton("plot")
        self.plot_button.clicked.connect(self.plot)
        self.plot_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        # create layout and add widgets
        self.hbox_layout = QHBoxLayout()
        self.hbox_layout.addLayout(self.types_hdf5_layout)
        self.hbox_layout.addLayout(self.names_hdf5_layout)
        self.hbox_layout.addLayout(self.variable_hdf5_layout)
        self.hbox_layout.addLayout(self.units_layout)
        self.hbox_layout.addLayout(self.types_plot_layout)
        self.hbox_layout.addWidget(self.plot_button)

        # add layout to group
        self.setLayout(self.hbox_layout)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

    def types_hdf5_change(self):
        index = self.types_hdf5_QComboBox.currentIndex()
        if index == 0:  # nothing
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            self.units_QListWidget.clear()
        if index == 1:  # hydraulic
            # get list of file name
            absname = self.parent().parent().parent().parent().parent().parent().hyd_name
            names = []
            for i in range(len(absname)):
                names.append(os.path.basename(absname[i]))
            # change list widget
            self.names_hdf5_QListWidget.clear()
            self.names_hdf5_QListWidget.addItems(names)
            # set list variable
            self.variable_QListWidget.clear()
            self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
        if index == 2:  # substrat
            # get list of file name
            absname = self.parent().parent().parent().parent().parent().parent().substrate_tab.sub_name
            names = []
            for i in range(len(absname)):
                names.append(os.path.basename(absname[i]))
            # change list widget
            self.names_hdf5_QListWidget.clear()
            self.names_hdf5_QListWidget.addItems(names)
            # set list variable
            self.variable_QListWidget.clear()
            self.variable_QListWidget.addItems(["coarser", "dominant"])
        if index == 3:  # chronics / merge ==> habitat
            # get list of file name
            absname = self.parent().parent().parent().parent().parent().parent().bioinfo_tab.hdf5_merge
            names = []
            for i in range(len(absname)):
                names.append(os.path.basename(absname[i]))
            # change list widget
            self.names_hdf5_QListWidget.clear()
            self.names_hdf5_QListWidget.addItems(names)
            # set list variable
            self.variable_QListWidget.clear()
            self.variable_QListWidget.addItems(["habitat value map", "global habitat value and SPU"])

    def names_hdf5_change(self):
        selection = self.names_hdf5_QListWidget.selectedItems()
        if not selection:  # no file selected
            self.units_QListWidget.clear()
        if len(selection) == 1:  # one file selected
            hdf5name = selection[0].text()
            self.units_QListWidget.clear()
            self.units_QListWidget.addItems(load_hdf5.load_timestep_name(hdf5name, self.parent().path_prj + "/hdf5_files/"))
        if len(selection) > 1:  # more than one file selected
            nb_file = len(selection)
            hdf5name = []
            timestep = []
            for i in range(nb_file):
                hdf5name.append(selection[i].text())
                timestep.append(load_hdf5.load_timestep_name(selection[i].text(), self.parent().path_prj + "/hdf5_files/"))
            if all(x == timestep[0] for x in timestep):  # OK
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(
                    load_hdf5.load_timestep_name(hdf5name[i], self.parent().path_prj + "/hdf5_files/"))
            else:  # timestep are diferrents
                self.msg2 = QMessageBox(self)
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Warning"))
                self.msg2.setText(
                    self.tr("The selected files don't have same timestep !"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
                # clean
                self.names_hdf5_QListWidget.clearSelection()
                self.units_QListWidget.clear()

    def plot(self):
        aa = 1
        # types
        types_hdf5 = self.types_hdf5_QComboBox.currentText()

        # names
        selection = self.names_hdf5_QListWidget.selectedItems()
        names_hdf5 = []
        for i in range(len(selection)):
            names_hdf5.append(selection[i].text())

        # variables
        selection = self.variable_QListWidget.selectedItems()
        variables = []
        for i in range(len(selection)):
            variables.append(selection[i].text())

        # units
        selection = self.units_QListWidget.selectedItems()
        units = []
        for i in range(len(selection)):
            units.append(selection[i].text())

        # type of plot
        types_plot = self.types_plot_QComboBox.currentText()

        print(types_hdf5)
        print(names_hdf5)
        print(variables)
        print(units)
        print(types_plot)
