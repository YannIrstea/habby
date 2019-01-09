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
import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, \
    QComboBox, QMessageBox, QFrame, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QProgressBar
from src import load_hdf5
from src import plot as plot_hab
from src_GUI import output_fig_GUI
from multiprocessing import Process, Value


class PlotTab(QScrollArea):
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
        # GroupPlot
        self.group_plot = GroupPlot()

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
        self.plot_layout.addWidget(self.group_plot)
        self.group_plot.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        # add layout
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content_widget)


class GroupPlot(QGroupBox):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self):
        super().__init__()
        self.nb_plot = 0
        self.init_ui()
        self.plot_production_stoped = False
        self.plot_process_list = MyProcessList(self.progress_bar)

    def init_ui(self):
        # title
        self.setTitle(self.tr('Graphic production'))
        self.setStyleSheet('QGroupBox {font-weight: bold;}')

        # types_hdf5_QComboBox
        self.types_hdf5_QLabel = QLabel(self.tr('hdf5 types :'))
        self.types_hdf5_QComboBox = QComboBox()
        self.types_hdf5_list = ["", "hydraulic", "substrate", "merge", "chronic", "habitat"]
        self.types_hdf5_QComboBox.addItems(self.types_hdf5_list)
        self.types_hdf5_QComboBox.currentIndexChanged.connect(self.types_hdf5_change)
        self.types_hdf5_layout = QVBoxLayout()
        self.types_hdf5_layout.setAlignment(Qt.AlignTop)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QLabel)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QComboBox)

        # names_hdf5_QListWidget
        self.names_hdf5_QLabel = QLabel(self.tr('hdf5 files :'))
        self.names_hdf5_QListWidget = QListWidget()
        self.names_hdf5_QListWidget.setMinimumWidth(250)
        self.names_hdf5_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.names_hdf5_QListWidget.itemSelectionChanged.connect(self.names_hdf5_change)
        self.names_hdf5_layout = QVBoxLayout()
        self.names_hdf5_layout.setAlignment(Qt.AlignTop)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QLabel)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QListWidget)

        # variable_QListWidget
        self.variable_hdf5_QLabel = QLabel(self.tr('variables :'))
        self.variable_QListWidget = QListWidget()
        self.variable_QListWidget.setMinimumWidth(130)
        self.variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.variable_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.variable_hdf5_layout = QVBoxLayout()
        self.variable_hdf5_layout.setAlignment(Qt.AlignTop)
        self.variable_hdf5_layout.addWidget(self.variable_hdf5_QLabel)
        self.variable_hdf5_layout.addWidget(self.variable_QListWidget)

        # units_QListWidget
        self.units_QLabel = QLabel(self.tr('units :'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setMinimumWidth(50)
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.units_layout = QVBoxLayout()
        self.units_layout.setAlignment(Qt.AlignTop)
        self.units_layout.addWidget(self.units_QLabel)
        self.units_layout.addWidget(self.units_QListWidget)

        # types_plot_QComboBox
        self.types_plot_QLabel = QLabel(self.tr('type of graphics :'))
        self.types_plot_QComboBox = QComboBox()
        self.types_plot_QComboBox.addItems(["display", "export", "both"])
        self.types_plot_layout = QVBoxLayout()
        self.types_plot_layout.setAlignment(Qt.AlignTop)
        self.types_plot_layout.addWidget(self.types_plot_QLabel)
        self.types_plot_layout.addWidget(self.types_plot_QComboBox)

        # buttons plot_button
        self.plot_button = QPushButton(self.tr("run"))
        self.plot_button.clicked.connect(self.collect_data_from_gui_and_plot)
        self.plot_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.types_plot_layout.addWidget(self.plot_button)

        # stop plot_button
        self.plot_stop_button = QPushButton(self.tr("stop"))
        self.plot_stop_button.clicked.connect(self.stop_plot)
        self.plot_stop_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.plot_stop_button.setEnabled(False)
        self.types_plot_layout.addWidget(self.plot_stop_button)

        # progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, 0))

        # create layout and add widgets
        self.hbox_layout = QHBoxLayout()
        self.hbox_layout.addLayout(self.types_hdf5_layout)
        self.hbox_layout.addLayout(self.names_hdf5_layout)
        self.hbox_layout.addLayout(self.variable_hdf5_layout)
        self.hbox_layout.addLayout(self.units_layout)
        self.hbox_layout.addLayout(self.types_plot_layout)
        self.vbox_layout = QVBoxLayout()
        self.vbox_layout.addLayout(self.hbox_layout)
        self.vbox_layout.addWidget(self.progress_bar)

        # add layout to group
        self.setLayout(self.vbox_layout)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

    def resize_width_lists(self):
        # names
        if self.names_hdf5_QListWidget.count() != 0:
            self.names_hdf5_QListWidget.setFixedWidth(
                self.names_hdf5_QListWidget.sizeHintForColumn(0) + self.names_hdf5_QListWidget.sizeHintForColumn(
                    0) * 0.1)
        if self.names_hdf5_QListWidget.count() == 0:
            self.names_hdf5_QListWidget.setFixedWidth(150)
        # variables
        if self.variable_QListWidget.count() != 0:
            self.variable_QListWidget.setFixedWidth(
                self.variable_QListWidget.sizeHintForColumn(0) + self.variable_QListWidget.sizeHintForColumn(0) * 0.1)
        else:
            self.variable_QListWidget.setFixedWidth(50)
        # units
        if self.units_QListWidget.count() != 0:
            self.units_QListWidget.setFixedWidth(
                self.units_QListWidget.sizeHintForColumn(0) + self.units_QListWidget.sizeHintForColumn(0) * 0.1)
        else:
            self.units_QListWidget.setFixedWidth(50)

    def count_plot(self):
        """
        count number of graphic to produce and ajust progress bar range
        """
        types_hdf5, names_hdf5, variables, units, units_index, types_plot = self.collect_data_from_gui()
        if types_hdf5 and names_hdf5 and variables and units:
            if types_hdf5 == "habitat":
                variables_to_remove = ["height", "velocity", "mesh", "coarser_dominant"]
                fish_names = [variable for variable in variables if variable not in variables_to_remove]
                variables_other = [variable for variable in variables if variable not in fish_names]
                if len(fish_names) == 0:
                    nb_plot_total = len(names_hdf5) * len(variables) * len(units)
                if len(fish_names) == 1:
                    # one map by fish by unit
                    nb_map = len(fish_names) * len(units)
                    if len(units) == 1:
                        nb_wua_hv = len(fish_names) * len(units)
                    if len(units) > 1:
                        nb_wua_hv = len(fish_names)
                    nb_plot_total = (len(names_hdf5) * len(variables_other) * len(units)) + nb_map + nb_wua_hv
                if len(fish_names) > 1:
                    # one map by fish by unit
                    nb_map = len(fish_names) * len(units)
                    nb_plot_total_hab = nb_map + 1
                    nb_plot_total = (len(names_hdf5) * len(variables_other) * len(units)) + nb_plot_total_hab
            else:
                nb_plot_total = len(names_hdf5) * len(variables) * len(units)
            self.nb_plot = nb_plot_total
            self.progress_bar.setRange(0, self.nb_plot)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, 0))
            self.nb_plot = 0

    def types_hdf5_change(self):
        """
        Ajust item list according to hdf5 type selected by user
        """
        index = self.types_hdf5_QComboBox.currentIndex()
        # "hydraulic", "substrate", "merge", "chronic", "habitat"
        # nothing
        if index == 0:
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            self.units_QListWidget.clear()
        # hydraulic
        if index == 1:
            # get list of file name by type
            names = load_hdf5.get_filename_by_type("hydraulic",
                                                   self.parent().parent().parent().path_prj + "/hdf5_files/")
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                # set list variable
                #self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
        # substrate
        if index == 2:
            # get list of file name by type
            names = load_hdf5.get_filename_by_type("substrate",
                                                   self.parent().parent().parent().path_prj + "/hdf5_files/")
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                # set list variable
                #self.variable_QListWidget.addItems(["coarser_dominant"])
        # merge
        if index == 3:
            # get list of file name by type
            names = load_hdf5.get_filename_by_type("merge", self.parent().parent().parent().path_prj + "/hdf5_files/")
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                # set list variable
                #self.variable_QListWidget.addItems(["height", "velocity", "mesh", "coarser_dominant"])
        # chronic
        if index == 4:
            # get list of file name by type
            names = load_hdf5.get_filename_by_type("chronic", self.parent().parent().parent().path_prj + "/hdf5_files/")
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                # set list variable
                #self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
        # habitat
        if index == 5:
            # get list of file name by type
            names = load_hdf5.get_filename_by_type("habitat", self.parent().parent().parent().path_prj + "/hdf5_files/")
            self.names_hdf5_QListWidget.clear()
            self.variable_QListWidget.clear()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                # set list variable
                #self.variable_QListWidget.addItems(["height", "velocity", "mesh"])

        # update progress bar
        self.count_plot()

    def names_hdf5_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        selection = self.names_hdf5_QListWidget.selectedItems()
        self.units_QListWidget.clear()
        self.variable_QListWidget.clear()
        if len(selection) == 1:  # one file selected
            hdf5name = selection[0].text()
            self.units_QListWidget.clear()
            # hydraulic
            if self.types_hdf5_QComboBox.currentIndex() == 1:
                self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
                self.units_QListWidget.addItems(
                    load_hdf5.load_unit_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
            # substrat
            if self.types_hdf5_QComboBox.currentIndex() == 2:
                self.variable_QListWidget.addItems(["coarser_dominant"])
                self.variable_QListWidget.item(0).setSelected(True)
                self.units_QListWidget.addItems(["one unit"])
                self.units_QListWidget.item(0).setSelected(True)
            # merge
            if self.types_hdf5_QComboBox.currentIndex() == 3:
                self.variable_QListWidget.addItems(["height", "velocity", "mesh", "coarser_dominant"])
                self.units_QListWidget.addItems(
                    load_hdf5.load_unit_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
            # chronic
            if self.types_hdf5_QComboBox.currentIndex() == 4:
                pass
            # habitat
            if self.types_hdf5_QComboBox.currentIndex() == 5:
                self.variable_QListWidget.addItems(["height", "velocity", "mesh", "coarser_dominant"])
                self.variable_QListWidget.addItems(load_hdf5.get_fish_names_habitat(hdf5name,
                                                                                    self.parent().parent().parent().path_prj + "/hdf5_files/"))
                self.units_QListWidget.addItems(
                    load_hdf5.load_unit_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
        if len(selection) > 1:  # more than one file selected
            nb_file = len(selection)
            hdf5name = []
            units = []
            for i in range(nb_file):
                hdf5name.append(selection[i].text())
                units.append(load_hdf5.load_unit_name(selection[i].text(),
                                                         self.parent().parent().parent().path_prj + "/hdf5_files/"))
            if not all(x == units[0] for x in units):  # units are diferrents
                msg2 = QMessageBox(self)
                msg2.setIcon(QMessageBox.Warning)
                msg2.setWindowTitle(self.tr("Warning"))
                msg2.setText(
                    self.tr("The selected files don't have same units !"))
                msg2.setStandardButtons(QMessageBox.Ok)
                msg2.show()
                # clean
                self.names_hdf5_QListWidget.clearSelection()
                self.units_QListWidget.clear()

            # same units
            if all(x == units[0] for x in units):  # OK
                if not self.types_hdf5_QComboBox.currentIndex() == 2:
                    units = [x[0] for x in set([tuple(x) for x in units])]
                self.units_QListWidget.clear()
                self.variable_QListWidget.clear()
                # hydraulic
                if self.types_hdf5_QComboBox.currentIndex() == 1:  # hydraulic
                    self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
                    self.units_QListWidget.addItems(units)
                # substrat
                if self.types_hdf5_QComboBox.currentIndex() == 2:  # substrat
                    self.variable_QListWidget.addItems(["coarser_dominant"])
                    self.variable_QListWidget.item(0).setSelected(True)
                    self.units_QListWidget.addItems(["one unit"])
                    self.units_QListWidget.item(0).setSelected(True)                # merge
                if self.types_hdf5_QComboBox.currentIndex() == 3:  # merge
                    self.variable_QListWidget.addItems(["height", "velocity", "mesh", "coarser_dominant"])
                    self.units_QListWidget.addItems(units)
                # chronic
                if self.types_hdf5_QComboBox.currentIndex() == 4:
                    pass
                # habitat
                if self.types_hdf5_QComboBox.currentIndex() == 5:
                    self.variable_QListWidget.addItems(["height", "velocity", "mesh", "coarser_dominant"])
                    self.variable_QListWidget.addItems(load_hdf5.get_fish_names_habitat(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
                    self.units_QListWidget.addItems(units)        # update progress bar
        self.count_plot()

    def collect_data_from_gui(self):
        """
        Get selected values by user
        """
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
        units_index = []
        for i in range(len(selection)):
            units.append(selection[i].text())
            units_index.append(self.units_QListWidget.indexFromItem(selection[i]).row())
        together = zip(units_index, units)
        sorted_together = sorted(together)
        units_index = [x[0] for x in sorted_together]
        units = [x[1] for x in sorted_together]

        # type of plot
        types_plot = self.types_plot_QComboBox.currentText()

        # store values
        return types_hdf5, names_hdf5, variables, units, units_index, types_plot

    def collect_data_from_gui_and_plot(self):
        """
        Get selected values by user and plot them
        """
        types_hdf5, names_hdf5, variables, units, units_index, types_plot = self.collect_data_from_gui()
        self.plot(types_hdf5, names_hdf5, variables, units, units_index, types_plot)

    def plot(self, types_hdf5, names_hdf5, variables, units, units_index, types_plot):
        """
        Plot
        :param types_hdf5: string representing the type of hdf5 ("hydraulic", "substrat", "habitat")
        :param names_hdf5: list of string representing hdf5 filenames
        :param variables: list of string representing variables to be ploted, depend on type of hdf5 selected ("height", "velocity", "mesh")
        :param units: list of string representing units names (timestep value or discharge)
        :param units_index: list of integer representing the position of units in hdf5 file
        :param types_plot: string representing plot types production ("display", "export", "both")
        """
        # print("types_hdf5 : ", types_hdf5)
        # print("names_hdf5 : ", names_hdf5)
        # print("variables : ", variables)
        # print("units : ", units)
        # print("units_index : ", units_index)
        # print("types_plot : ", types_plot)
        if not types_hdf5:
            self.parent().parent().parent().send_log.emit('Error: No hdf5 type selected.')
        if not names_hdf5:
            self.parent().parent().parent().send_log.emit('Error: No hdf5 file selected.')
        if not variables:
            self.parent().parent().parent().send_log.emit('Error: No variable selected.')
        if not units:
            self.parent().parent().parent().send_log.emit('Error: No units selected.')
        # check if number of display plot are > 30
        if types_plot in ("display", "both") and self.nb_plot > 30:
            qm = QMessageBox
            ret = qm.question(self, self.tr("Warning"),
                              self.tr("Displaying a large number of plots may crash HABBY. "
                                      "It is recommended not to exceed a total number of plots "
                                      f"greater than 30 at a time. \n\nDo you still want to display {self.nb_plot} plots ?"
                                      "\n\nNB : There is no limit for exports."), qm.Yes | qm.No)
            if ret == qm.No:  # pas de plot
                return
        # Go plot
        if types_hdf5 and names_hdf5 and variables and units:
            # disable
            self.plot_button.setEnabled(False)
            # active stop button
            self.plot_stop_button.setEnabled(True)
            self.plot_production_stoped = False

            # figure option
            fig_opt = output_fig_GUI.load_fig_option(self.parent().parent().parent().path_prj,
                                                     self.parent().parent().parent().name_prj)
            fig_opt['type_plot'] = types_plot  # "display", "export", "both"

            # init
            fish_names = []

            # path
            path_hdf5 = self.parent().parent().parent().path_prj + "/hdf5_files/"
            path_im = self.parent().parent().parent().path_prj + "/figures/"

            # check plot process done
            if self.plot_process_list.check_all_plot_closed():
                self.plot_process_list.new_plots(self.nb_plot)
            else:
                self.plot_process_list.add_plots(self.nb_plot)

            # progress bar
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
            QCoreApplication.processEvents()

            # loop on all desired hdf5 file
            for name_hdf5 in names_hdf5:
                if not self.plot_production_stoped:  # stop loop with button

                    # read hdf5 data (get desired units)
                    if types_hdf5 == "hydraulic":  # load hydraulic data
                        [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t] = load_hdf5.load_hdf5_hyd_and_merge(
                            name_hdf5,
                            path_hdf5, units_index=units_index)
                    if types_hdf5 == "substrate":  # load substrate data
                        [ikle_sub, point_all_sub, sub_pg, sub_dom] = load_hdf5.load_hdf5_sub(name_hdf5, path_hdf5)
                    if types_hdf5 == "merge":  # load merge data
                        [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg,
                         substrate_all_dom] = load_hdf5.load_hdf5_hyd_and_merge(name_hdf5, path_hdf5, units_index=units_index, merge=True)
                    if types_hdf5 == "chronic":  # load chronic data
                        [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg,
                         substrate_all_dom] = load_hdf5.load_hdf5_hyd_and_merge(name_hdf5, path_hdf5, units_index=units_index, merge=True)
                    if types_hdf5 == "habitat":  # load habitat data
                        variables_to_remove = ["height", "velocity", "mesh", "coarser_dominant"]
                        fish_names = [variable for variable in variables if variable not in variables_to_remove]
                        if fish_names:  # get all data (hydraulic and substrate and fish habiat)
                            [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg, substrate_all_dom,
                             fish_data, total_wetarea_all_t] = load_hdf5.load_hdf5_hab(name_hdf5, path_hdf5, fish_names, units_index)
                        else:  # get only input data merge (hydraulic and substrate)
                            [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg,
                             substrate_all_dom] = load_hdf5.load_hdf5_hyd_and_merge(name_hdf5, path_hdf5, units_index=units_index, merge=True)

                    # for one or more desired units ==> habitat data (HV and WUA)
                    if fish_names:
                        state = Value("i", 0)
                        plot_hab_fig_spu_process = Process(target=plot_hab.plot_fish_hv_wua,
                                                           args=(state,
                                                       total_wetarea_all_t,
                                                       fish_data["total_WUA"],
                                                       fish_names,
                                                       path_im,
                                                       name_hdf5,
                                                       fig_opt,
                                                       units))
                        self.plot_process_list.append((plot_hab_fig_spu_process, state))

                    # for each desired units ==> maps
                    for index, t in enumerate(units_index):
                        # input data
                        if "height" in variables:  # height
                            state = Value("i", 0)
                            height_process = Process(target=plot_hab.plot_map_height,
                                                     args=(state,
                                                           point_all_t[index + 1],
                                                           ikle_all_t[index + 1],
                                                           fig_opt,
                                                           name_hdf5,
                                                           inter_h_all_t[index + 1],
                                                           path_im, units[index]))
                            self.plot_process_list.append((height_process, state))
                        if "velocity" in variables:  # velocity
                            state = Value("i", 0)
                            velocity_process = Process(target=plot_hab.plot_map_velocity,
                                                       args=(state,
                                                          point_all_t[index + 1],
                                                          ikle_all_t[index + 1],
                                                          fig_opt, name_hdf5,
                                                          inter_vel_all_t[index + 1],
                                                          path_im,
                                                          units[index]))
                            self.plot_process_list.append((velocity_process, state))
                        if "mesh" in variables:  # mesh
                            state = Value("i", 0)
                            mesh_process = Process(target=plot_hab.plot_map_mesh,
                                                   args=(state,
                                                         point_all_t[index + 1],
                                                         ikle_all_t[index + 1],
                                                         fig_opt,
                                                         name_hdf5,
                                                         path_im,
                                                         units[index]))
                            self.plot_process_list.append((mesh_process, state))
                        if "coarser_dominant" in variables:  # coarser_dominant
                            if types_hdf5 == "substrate":  # from substrate
                                state = Value("i", 0)
                                susbtrat_process = Process(target=plot_hab.plot_map_substrate,
                                                           args=(state,
                                                                 point_all_sub,
                                                                 ikle_sub,
                                                                 sub_pg,
                                                                 sub_dom,
                                                                 path_im,
                                                                 name_hdf5,
                                                                 fig_opt))
                                self.plot_process_list.append((susbtrat_process, state))
                            else:  # from merge or habitat
                                state = Value("i", 0)
                                susbtrat_process = Process(target=plot_hab.plot_map_substrate,
                                                           args=(state,
                                                                 point_all_t[index + 1][0],
                                                                 ikle_all_t[index + 1][0],
                                                                 substrate_all_pg[index + 1][0],
                                                                 substrate_all_dom[index + 1][0],
                                                                 path_im,
                                                                 name_hdf5,
                                                                 fig_opt,
                                                                 units[index]))
                                self.plot_process_list.append((susbtrat_process, state))
                        if fish_names:  # habitat data (maps)
                            # map by fish
                            for fish_index, fish_name in enumerate(fish_names):
                                # plot map
                                state = Value("i", 0)
                                habitat_map_process = Process(target=plot_hab.plot_map_fish_habitat,
                                                              args=(state,
                                                                    fish_name,
                                                                    point_all_t[index + 1][0],
                                                                    ikle_all_t[index + 1][0],
                                                                    fish_data["HV_data"][index + 1][fish_index + 1],
                                                                    name_hdf5,
                                                                    fig_opt,
                                                                    path_im,
                                                                    units[index]))
                                self.plot_process_list.append((habitat_map_process, state))

            # end of loop file
            if self.plot_process_list.add_plots_state:  # if plot windows are open ==> add news to existing (don't close them)
                self.plot_process_list[:] = self.plot_process_list[:] + self.plot_process_list.save_process[:]
            # activate
            self.plot_button.setEnabled(True)
            # disable stop button
            self.plot_stop_button.setEnabled(False)

    def stop_plot(self):
        # stop plot production
        self.plot_production_stoped = True
        # activate
        self.plot_button.setEnabled(True)
        # disable stop button
        self.plot_stop_button.setEnabled(False)


class MyProcessList(list):
    """
    This class is a subclass of class list created in order to analyze the status of the processes and the refresh of the progress bar in real time.

    :param nb_plot_total: integer value representing the total number of graphs to be produced.
    :param progress_bar: Qprogressbar of GroupPlot to be refreshed
    """

    def __init__(self, progress_bar):
        super().__init__()
        self.progress_bar = progress_bar
        self.nb_plot_total = 0

    def new_plots(self, nb_plot_total):
        self.add_plots_state = False
        self.nb_plot_total = nb_plot_total
        self.save_process = []
        self[:] = []

    def add_plots(self, nb_plot_total):
        self.add_plots_state = True
        self.nb_plot_total = nb_plot_total
        self.save_process = self[:]
        self[:] = []

    def append(self, *args):
        """
        Overriding of append method in order to analyse state of plot processes and refresh progress bar.
        Each time the list is appended, state is analysed and progress bar refreshed.

        :param args: tuple(process, state of process)
        """
        args[0][0].start()
        self.extend(args)
        self.check_all_plot_produced()

    def check_all_plot_produced(self):
        """
        State is analysed and progress bar refreshed.
        """
        nb_finished = 0
        state_list = []
        for i in range(len(self)):
            state = self[i][1].value
            state_list.append(state)
            if state == 1:
                nb_finished = nb_finished + 1
            if state == 0:
                if i == self.nb_plot_total - 1:  # last of all plot
                    while 0 in state_list:
                        for j in [k for k, l in enumerate(state_list) if l == 0]:
                            state = self[j][1].value
                            state_list[j] = state
                            if state == 1:
                                nb_finished = nb_finished + 1
                                self.progress_bar.setValue(nb_finished)
                                self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(nb_finished, self.nb_plot_total))
                                QCoreApplication.processEvents()

        self.progress_bar.setValue(nb_finished)
        self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(nb_finished, self.nb_plot_total))
        QCoreApplication.processEvents()

    def check_all_plot_closed(self):
        """
        Check if a process is alive (plot window open)
        """
        if any([self[i][0].is_alive() for i in range(len(self))]):  # plot window open or plot not finished
            return False
        else:
            return True

    def close_all_plot_process(self):
        """
        Close all plot process. usefull for button close all figure and for closeevent of Main_windows_1.
        """
        for i in range(len(self)):
            self[i][0].terminate()
