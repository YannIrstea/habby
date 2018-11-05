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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QListWidget, QAbstractItemView, \
    QComboBox, QMessageBox, QFrame, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSpacerItem, QSizePolicy, QScrollArea
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from src import load_hdf5
from src import manage_grid_8
from src_GUI import output_fig_GUI


class PlotTab(QScrollArea):
    """
    New tab

    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
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
        # GroupPlot
        self.GroupPlot_first = GroupPlot()

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # empty frame scrolable
        content_widget = QFrame()

        # add widgets to layout
        self.plot_layout = QVBoxLayout(content_widget)  # vetical layout
        self.plot_layout.setAlignment(Qt.AlignTop)
        self.plot_layout.addWidget(self.GroupPlot_first)

        # add layout
        #self.setLayout(self.plot_layout)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content_widget)




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
            self.units_QListWidget.addItems(load_hdf5.load_timestep_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
        if len(selection) > 1:  # more than one file selected
            nb_file = len(selection)
            hdf5name = []
            timestep = []
            for i in range(nb_file):
                hdf5name.append(selection[i].text())
                timestep.append(load_hdf5.load_timestep_name(selection[i].text(), self.parent().parent().parent().path_prj + "/hdf5_files/"))
            if all(x == timestep[0] for x in timestep):  # OK
                self.units_QListWidget.clear()
                self.units_QListWidget.addItems(
                    load_hdf5.load_timestep_name(hdf5name[i], self.parent().parent().parent().path_prj + "/hdf5_files/"))
            else:  # timestep are diferrents
                self.msg2 = QMessageBox(self)
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Warning"))
                self.msg2.setText(
                    self.tr("The selected files don't have same units !"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
                # clean
                self.names_hdf5_QListWidget.clearSelection()
                self.units_QListWidget.clear()

    def plot(self):
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
        if "height" in variables:
            height = True
        else:
            height = False
        if "velocity" in variables:
            velocity = True
        else:
            velocity = False
        if "mesh" in variables:
            mesh = True
        else:
            mesh = False

        # units
        selection = self.units_QListWidget.selectedItems()
        units = []
        units_index = []
        for i in range(len(selection)):
            units.append(selection[i].text())
            units_index.append(self.units_QListWidget.indexFromItem(selection[i]).row())
        together = zip(units_index, units)  # TRIS DANS ORDRE TRONCON
        sorted_together = sorted(together, reverse=True)  # TRIS DANS ORDRE TRONCON
        units_index = [x[0] for x in sorted_together]
        units = [x[1] for x in sorted_together]

        # type of plot
        types_plot = self.types_plot_QComboBox.currentText()

        #print(types_hdf5)
        #print(names_hdf5)
        #print(variables)
        #print(units)
        #print(types_plot)

        ################ from hydro_GUI_2.create_image ###################

        if types_plot == "view interactive graphics":
            save_fig = False
        if types_plot == "export files graphics" or types_plot == "both":
            save_fig = True
        path_hdf5 = self.parent().parent().parent().path_prj + "/hdf5_files/"
        show_info = True
        path_im = self.parent().parent().parent().path_prj + "/figures/"
        # for all hdf5 file selected
        for i in range(len(names_hdf5)):
            name_hdf5 = names_hdf5[i]
            print(name_hdf5)
            if name_hdf5:
                # load data
                if types_hdf5 == 'substrat': #  or self.model_type == 'LAMMI'
                    [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg, substrate_all_dom] \
                        = load_hdf5.load_hdf5_hyd(name_hdf5, path_hdf5, True)
                else:
                    substrate_all_pg = []
                    substrate_all_dom = []
                    [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t] = load_hdf5.load_hdf5_hyd(name_hdf5,
                                                                                                        path_hdf5)
                if ikle_all_t == [[-99]]:
                    self.parent().parent().parent().send_log.emit('Error: No data found in hdf5 (from create_image)')
                    return
                # figure option
                self.fig_opt = output_fig_GUI.load_fig_option(self.parent().parent().parent().path_prj, self.parent().parent().parent().name_prj)
                if not save_fig:
                    self.fig_opt['format'] = 123456  # random number  but should be bigger than number of format

                # plot the figure for all time step
                if self.units_QListWidget.count() == len(units): #self.fig_opt['time_step'][0] == -99:  # all time steps
                    for t in range(1, len(ikle_all_t)):  # do not plot full profile
                        if t < len(ikle_all_t):
                            if types_hdf5 == 'substrat':  # or self.model_type == 'LAMMI':
                                self.parent().parent().parent().send_log.emit('Warning: Substrate data created but not plotted. '
                                                   'See the created shapefile for subtrate outputs. \n')
                                manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt, mesh, velocity, height,
                                                               inter_vel_all_t[t], inter_h_all_t[t], path_im, True, units[t - 1],
                                                               substrate_all_pg[t], substrate_all_dom[t]) # , mesh, velocity, height
                            else:
                                manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt, mesh, velocity, height,
                                                               inter_vel_all_t[t], inter_h_all_t[t], path_im, False, units[t - 1])
                # plot the figure for some time steps
                else:
                    print("-------------------------------")
                    print(units, units_index)
                    for index, t in enumerate(units_index):  # self.fig_opt['time_step'] # range(0, len(vel_cell)):
                        t = t + 1
                        # if print last and first time step and one time step only, only print it once
                        if t == -1 and len(ikle_all_t) == 2 and 1 in self.fig_opt['time_step']:
                            pass
                        else:
                            if t < len(ikle_all_t):
                                if types_hdf5 == 'substrat':  # or self.model_type == 'LAMMI':
                                    self.parent().parent().parent().send_log.emit('Warning: Substrate data created but not plotted. '
                                                       'See the created shapefile for subtrate outputs. \n')
                                    manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt, mesh, velocity, height,
                                                                   inter_vel_all_t[t], inter_h_all_t[t], path_im, True, units[index],
                                                                   substrate_all_pg[t], substrate_all_dom[t])
                                else:
                                    manage_grid_8.plot_grid_simple(point_all_t[t], ikle_all_t[t], self.fig_opt, mesh, velocity, height,
                                                                   inter_vel_all_t[t], inter_h_all_t[t], path_im, False, units[index])
                                    # to debug
                                    # manage_grid_8.plot_grid(point_all_reach, ikle_all, lim_by_reach,
                                    # hole_all, overlap, point_c_all, inter_vel_all, inter_height_all, path_im)

                # show basic information
                if show_info and len(ikle_all_t) > 0:
                    self.parent().parent().parent().send_log.emit("# ------------------------------------------------")
                    self.parent().parent().parent().send_log.emit("# Information about the hydrological data from the model " + types_hdf5)
                    self.parent().parent().parent().send_log.emit("# - Number of time step: " + str(len(ikle_all_t) - 1))
                    extx = 0
                    exty = 0
                    nb_node = 0
                    hmean = 0
                    vmean = 0
                    for r in range(0, len(point_all_t[0])):
                        extxr = max(point_all_t[0][r][:, 0]) - min(point_all_t[0][r][:, 0])
                        extyr = max(point_all_t[0][r][:, 1]) - min(point_all_t[0][r][:, 1])
                        nb_node += len(point_all_t[0][r])
                        if extxr > extx:
                            extx = extxr
                        if extyr > exty:
                            exty = extyr
                        hmean += np.sum(inter_h_all_t[-1][r])
                        vmean += np.sum(inter_vel_all_t[-1][r])
                    hmean /= nb_node
                    vmean /= nb_node
                    self.parent().parent().parent().send_log.emit("# - Maximal number of nodes: " + str(nb_node))
                    self.parent().parent().parent().send_log.emit("# - Maximal geographical extend: " + str(round(extx, 3)) + 'm X ' +
                                       str(round(exty, 3)) + "m")
                    self.parent().parent().parent().send_log.emit(
                        "# - Mean water height at the last time step, not weighted by cell area: " +
                        str(round(hmean, 3)) + 'm')
                    self.parent().parent().parent().send_log.emit(
                        "# - Mean velocity at the last time step, not weighted by cell area: " +
                        str(round(vmean, 3)) + 'm/sec')
                    self.parent().parent().parent().send_log.emit("# ------------------------------------------------")

                print(save_fig)
                if not save_fig:
                    matplotlib.interactive(True)
                    plt.show()
                if save_fig:
                    matplotlib.interactive(False)
            else:
                self.parent().parent().parent().send_log.send_log.emit('Error: The hydrological model is not found. \n')


