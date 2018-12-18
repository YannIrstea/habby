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
from src import manage_grid_8
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
        self.GroupPlot = GroupPlot()

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
        self.plot_layout.addWidget(self.GroupPlot)
        self.GroupPlot.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

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
        types_hdf5, names_hdf5, variables, units, units_index, types_plot = self.collect_data_plot_from_gui()
        if types_hdf5 and names_hdf5 and variables and units:
            if types_hdf5 == "habitat":
                variables_to_remove = ["height", "velocity", "mesh", "coarser_dominant"]
                fish_names = [variable for variable in variables if variable not in variables_to_remove]
                if fish_names:
                    nb_variable_type_fish = len(fish_names)
                    nb_plot_total = (len(names_hdf5) * len(variables) * len(units)) + nb_variable_type_fish * len(units)
                else:
                    nb_plot_total = len(names_hdf5) * len(variables) * len(units)
            else:
                nb_plot_total = len(names_hdf5) * len(variables) * len(units)
            self.nb_plot = nb_plot_total
            self.progress_bar.setRange(0, self.nb_plot)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
        if not types_hdf5 or not names_hdf5 or not variables or not units:
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
                self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
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
                self.variable_QListWidget.addItems(["coarser_dominant"])
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
                self.variable_QListWidget.addItems(["height", "velocity", "mesh", "coarser_dominant"])
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
                self.variable_QListWidget.addItems(["height", "velocity", "mesh"])
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
                self.variable_QListWidget.addItems(["height", "velocity", "mesh"])

        # update progress bar
        self.count_plot()

    def names_hdf5_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        selection = self.names_hdf5_QListWidget.selectedItems()
        if not selection:  # no file selected
            self.units_QListWidget.clear()
        if len(selection) == 1:  # one file selected
            hdf5name = selection[0].text()
            self.units_QListWidget.clear()
            # hydraulic
            if self.types_hdf5_QComboBox.currentIndex() == 1:
                self.units_QListWidget.addItems(
                    load_hdf5.load_unit_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
            # substrat
            if self.types_hdf5_QComboBox.currentIndex() == 2:
                self.units_QListWidget.addItems(["one unit"])
                self.units_QListWidget.item(0).setSelected(True)
            # merge
            if self.types_hdf5_QComboBox.currentIndex() == 3:
                self.units_QListWidget.addItems(
                    load_hdf5.load_unit_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
            # chronic
            if self.types_hdf5_QComboBox.currentIndex() == 4:
                pass
            # habitat
            if self.types_hdf5_QComboBox.currentIndex() == 5:
                self.variable_QListWidget.addItems(load_hdf5.get_fish_names_habitat(hdf5name,
                                                                                    self.parent().parent().parent().path_prj + "/hdf5_files/"))
                self.units_QListWidget.addItems(
                    load_hdf5.load_unit_name(hdf5name, self.parent().parent().parent().path_prj + "/hdf5_files/"))
        if len(selection) > 1:  # more than one file selected
            nb_file = len(selection)
            hdf5name = []
            timestep = []
            for i in range(nb_file):
                hdf5name.append(selection[i].text())
                timestep.append(load_hdf5.load_unit_name(selection[i].text(),
                                                         self.parent().parent().parent().path_prj + "/hdf5_files/"))
            if not all(x == timestep[0] for x in timestep):  # timestep are diferrents
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
            if all(x == timestep[0] for x in timestep):  # OK
                self.units_QListWidget.clear()
                if self.types_hdf5_QComboBox.currentIndex() == 2:  # substrat
                    self.units_QListWidget.addItems(["one unit"])
                if self.types_hdf5_QComboBox.currentIndex() == 1 or self.types_hdf5_QComboBox.currentIndex() == 3:  # hydraulic or merge
                    self.units_QListWidget.addItems(load_hdf5.load_unit_name(hdf5name[i],
                                                                             self.parent().parent().parent().path_prj + "/hdf5_files/"))
                self.units_QListWidget.setFixedWidth(
                    self.units_QListWidget.sizeHintForColumn(0) + (self.units_QListWidget.sizeHintForColumn(0) * 0.6))

        # update progress bar
        self.count_plot()

    def collect_data_plot_from_gui(self):
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
        together = zip(units_index, units)  # TRIS DANS ORDRE TRONCON
        sorted_together = sorted(together, reverse=True)  # TRIS DANS ORDRE TRONCON
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
        types_hdf5, names_hdf5, variables, units, units_index, types_plot = self.collect_data_plot_from_gui()
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
        print("types_hdf5 : ", types_hdf5)
        print("names_hdf5 : ", names_hdf5)
        print("variables : ", variables)
        print("units : ", units)
        print("units_index : ", units_index)
        print("types_plot : ", types_plot)
        if not types_hdf5:
            self.parent().parent().parent().send_log.emit('Error: No hdf5 type selected. \n')
        if not names_hdf5:
            self.parent().parent().parent().send_log.emit('Error: No hdf5 file selected. \n')
        if not variables:
            self.parent().parent().parent().send_log.emit('Error: No variable selected. \n')
        if not units:
            self.parent().parent().parent().send_log.emit('Error: No units selected. \n')
        if types_hdf5 and names_hdf5 and variables and units:
            # figure option
            fig_opt = output_fig_GUI.load_fig_option(self.parent().parent().parent().path_prj,
                                                     self.parent().parent().parent().name_prj)
            fig_opt['type_plot'] = types_plot  # "display", "export", "both"

            # init
            fish_names = []

            # path
            path_hdf5 = self.parent().parent().parent().path_prj + "/hdf5_files/"
            show_info = False
            path_im = self.parent().parent().parent().path_prj + "/figures/"

            # check plot process done
            if self.plot_process_list.check_all_plot_closed():
                print("new_plots")
                self.plot_process_list.new_plots(self.nb_plot)
            else:
                print("add_plots")
                self.plot_process_list.add_plots(self.nb_plot)

            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
            QCoreApplication.processEvents()

            # for all hdf5 file
            for name_hdf5 in names_hdf5:
                # load hydraulic data
                if types_hdf5 == "hydraulic":
                    [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t] = load_hdf5.load_hdf5_hyd_and_merge(
                        name_hdf5,
                        path_hdf5)
                # load substrate data
                if types_hdf5 == "substrate":
                    [ikle_sub, point_all_sub, sub_pg, sub_dom] = load_hdf5.load_hdf5_sub(name_hdf5, path_hdf5)
                # load merge data
                if types_hdf5 == "merge":
                    [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg,
                     substrate_all_dom] = load_hdf5.load_hdf5_hyd_and_merge(name_hdf5, path_hdf5, merge=True)
                # load chronic data
                if types_hdf5 == "chronic":
                    [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg,
                     substrate_all_dom] = load_hdf5.load_hdf5_hyd_and_merge(name_hdf5, path_hdf5, merge=True)
                # load habitat data
                if types_hdf5 == "habitat":
                    variables_to_remove = ["height", "velocity", "mesh", "coarser_dominant"]
                    fish_names = [variable for variable in variables if variable not in variables_to_remove]
                    if fish_names:  # get all data (hydraulic and substrate and fish habiat)
                        [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg, substrate_all_dom,
                         fish_data, total_wetarea_all_t] = load_hdf5.load_hdf5_hab(name_hdf5, path_hdf5, fish_names)
                    else:  # get only input data data (hydraulic and substrate)
                        [ikle_all_t, point_all_t, inter_vel_all_t, inter_h_all_t, substrate_all_pg,
                         substrate_all_dom] = load_hdf5.load_hdf5_hyd_and_merge(name_hdf5, path_hdf5, merge=True)

                # check validity susbtrate
                if types_hdf5 == "substrate":
                    if len(sub_dom) == 0 or len(sub_pg) == 0:
                        self.parent().parent().parent().send_log.emit('Error: No data found to plot.')
                        return
                    if not ikle_sub:
                        self.parent().parent().parent().send_log.emit('Error: No connectivity table found. \n')
                        return
                    if len(point_all_sub) < 3:
                        self.parent().parent().parent().send_log.emit('Error: Not enough point found to form a grid \n')
                        return

                # for each units (timestep or discharge)
                for index, t in enumerate(units_index):  # self.fig_opt['time_step'] # range(0, len(vel_cell)):
                    t = t + 1
                    # height
                    if "height" in variables:
                        state = Value("i", 0)  # process not finished
                        height_process = Process(target=manage_grid_8.plot_grid_height, args=(state,
                                                                                              point_all_t[t],
                                                                                              ikle_all_t[t], fig_opt,
                                                                                              name_hdf5,
                                                                                              inter_h_all_t[t],
                                                                                              path_im, units[index]))
                        height_process.start()
                        self.plot_process_list.append((height_process, state))
                    # velocity
                    if "velocity" in variables:
                        state = Value("i", 0)  # process not finished
                        velocity_process = Process(target=manage_grid_8.plot_grid_velocity, args=(state,
                                                                                                  point_all_t[t],
                                                                                                  ikle_all_t[t],
                                                                                                  fig_opt, name_hdf5,
                                                                                                  inter_vel_all_t[t],
                                                                                                  path_im,
                                                                                                  units[index]))
                        velocity_process.start()
                        self.plot_process_list.append((velocity_process, state))
                    # mesh
                    if "mesh" in variables:
                        state = Value("i", 0)  # process not finished
                        mesh_process = Process(target=manage_grid_8.plot_grid_mesh, args=(state,
                                                                                          point_all_t[t], ikle_all_t[t],
                                                                                          fig_opt, name_hdf5, path_im,
                                                                                          units[index]))
                        mesh_process.start()
                        self.plot_process_list.append((mesh_process, state))
                    # coarser_dominant
                    if "coarser_dominant" in variables:
                        state = Value("i", 0)  # process not finished
                        if types_hdf5 == "substrate":
                            susbtrat_process = Process(target=manage_grid_8.plot_substrate,
                                                       args=(state, point_all_sub, ikle_sub, sub_pg, sub_dom, path_im,
                                                             name_hdf5, fig_opt))
                        else:
                            susbtrat_process = Process(target=manage_grid_8.plot_substrate,
                                                       args=(state, point_all_t[t][0], ikle_all_t[t][0],
                                                             substrate_all_pg[t][0],
                                                             substrate_all_dom[t][0], path_im, name_hdf5, fig_opt,
                                                             units[index]))
                        susbtrat_process.start()
                        self.plot_process_list.append((susbtrat_process, state))
                    # fish habitat
                    if fish_names:
                        # loop on fish
                        for fish_index, fish_name in enumerate(fish_names):
                            # plot map
                            state = Value("i", 0)  # process not finished
                            habitat_map_process = Process(target=manage_grid_8.plot_fish_habitat_map,
                                                          args=(state, fish_name,
                                                                point_all_t[t][0], ikle_all_t[t][0],
                                                                fish_data["HV_data"][t][fish_index], name_hdf5,
                                                                fig_opt, path_im, units[index]))
                            habitat_map_process.start()
                            self.plot_process_list.append((habitat_map_process, state))

                            # plot mean hist
                            state = Value("i", 0)  # process not finished
                            wua_hv_mean_process = Process(target=manage_grid_8.plot_wua_hv_mean,
                                                          args=(state, fish_data["total_WUA"][t][fish_index],
                                                                total_wetarea_all_t[t], fish_name, name_hdf5,
                                                                fig_opt, path_im, units[index]))
                            wua_hv_mean_process.start()
                            self.plot_process_list.append((wua_hv_mean_process, state))

                # show basic information
                if show_info and len(ikle_all_t) > 0:
                    self.parent().parent().parent().send_log.emit("# ------------------------------------------------")
                    self.parent().parent().parent().send_log.emit(
                        "# Information about the hydrological data from the model " + types_hdf5)
                    self.parent().parent().parent().send_log.emit(
                        "# - Number of time step: " + str(len(ikle_all_t) - 1))
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
                    self.parent().parent().parent().send_log.emit(
                        "# - Maximal geographical extend: " + str(round(extx, 3)) + 'm X ' +
                        str(round(exty, 3)) + "m")
                    self.parent().parent().parent().send_log.emit(
                        "# - Mean water height at the last time step, not weighted by cell area: " +
                        str(round(hmean, 3)) + 'm')
                    self.parent().parent().parent().send_log.emit(
                        "# - Mean velocity at the last time step, not weighted by cell area: " +
                        str(round(vmean, 3)) + 'm/sec')
                    self.parent().parent().parent().send_log.emit("# ------------------------------------------------")

            if self.plot_process_list.add_plots_state:
                self.plot_process_list[:] = self.plot_process_list[:] + self.plot_process_list.save_process[:]


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
