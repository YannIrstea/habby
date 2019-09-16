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

from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication, QVariant, QAbstractTableModel
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QWidget, QAbstractItemView, \
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, \
    QSizePolicy, QScrollArea, QProgressBar, QTableView

from src import hdf5_mod
from src import plot_mod
from src_GUI.preferences_GUI import load_project_preferences, QHLine, DoubleClicOutputGroup
from src_GUI.tools_GUI import QGroupBoxCollapsible


class DataExplorerTab(QScrollArea):
    """
    This class contains the tab with Graphic production biological information (the curves of preference).
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "data explorer"
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.init_iu()

    def init_iu(self):
        # DataExplorerFrame
        self.data_explorer_frame = DataExplorerFrame(self.path_prj, self.name_prj, self.send_log)

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # # empty frame scrolable
        # content_widget = QFrame()

        # # add widgets to layout
        # self.plot_layout = QVBoxLayout(content_widget)  # vetical layout
        # self.plot_layout.setAlignment(Qt.AlignTop)
        # self.plot_layout.addWidget(self.data_explorer_frame)
        # self.data_explorer_frame.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        # add layout
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(self.data_explorer_frame)

    def refresh_type(self):
        index = self.data_explorer_frame.types_hdf5_QComboBox.currentIndex()
        if index:
            self.data_explorer_frame.types_hdf5_QComboBox.setCurrentIndex(0)
            self.data_explorer_frame.types_hdf5_QComboBox.setCurrentIndex(index)

    def refresh_filename(self):
        item = self.data_explorer_frame.names_hdf5_QListWidget.selectedItems()
        if item:
            self.data_explorer_frame.names_hdf5_QListWidget.setCurrentItem(None)
            self.data_explorer_frame.names_hdf5_QListWidget.setCurrentItem(item[0])


class DataExplorerFrame(QFrame):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.nb_plot = 0
        self.init_ui()
        self.plot_production_stoped = False

    def init_ui(self):
        # title
        #self.setTitle(self.tr('HABBY data explorer'))
        #self.setStyleSheet('QGroupBox {font-weight: bold;}')

        """ File selection """
        # hab_filenames_qcombobox
        self.types_hdf5_QLabel = QLabel(self.tr('file types'))
        self.types_hdf5_QComboBox = QComboBox()
        self.types_hdf5_list = ["", "hydraulic", "substrate", "habitat"]
        self.types_hdf5_QComboBox.addItems(self.types_hdf5_list)
        self.types_hdf5_QComboBox.currentIndexChanged.connect(self.types_hdf5_change)
        self.types_hdf5_layout = QVBoxLayout()
        self.types_hdf5_layout.setAlignment(Qt.AlignTop)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QLabel)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QComboBox)

        # available_units_qlistwidget
        self.names_hdf5_QLabel = QLabel(self.tr('filenames'))
        self.names_hdf5_QListWidget = QListWidget()
        self.names_hdf5_QListWidget.setMinimumWidth(250)
        self.names_hdf5_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.names_hdf5_QListWidget.itemSelectionChanged.connect(self.names_hdf5_change)
        self.names_hdf5_layout = QVBoxLayout()
        self.names_hdf5_layout.setAlignment(Qt.AlignTop)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QLabel)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QListWidget)

        """ Figure producer """
        self.plot_group = FigureProducerGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Figure viewer/exporter"))
        self.plot_group.setChecked(False)
        self.plot_group.hide()

        """ export """
        # interpolation group
        self.dataexporter_group = DataExporterGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Data exporter"))
        self.dataexporter_group.setChecked(False)
        self.dataexporter_group.hide()

        """ remove_fish """
        self.habitatvalueremover_group = HabitatValueRemover(self.path_prj, self.name_prj, self.send_log, self.tr("Habitat value remover"))
        self.habitatvalueremover_group.setChecked(False)
        self.habitatvalueremover_group.hide()

        """ File information """
        # attributes hdf5
        self.hdf5_attributes_qtableview = QTableView(self)
        self.hdf5_attributes_qtableview.setFrameShape(QFrame.NoFrame)
        self.hdf5_attributes_qtableview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.hdf5_attributes_qtableview.verticalHeader().setVisible(False)
        self.hdf5_attributes_qtableview.horizontalHeader().setVisible(False)

        """ File selection """
        # SELECTION FILE
        selectionfile_layout = QHBoxLayout()
        selectionfile_layout.addLayout(self.types_hdf5_layout)
        selectionfile_layout.addLayout(self.names_hdf5_layout)
        selectionfile_group = QGroupBox(self.tr("File selection"))
        selectionfile_group.setLayout(selectionfile_layout)

        """ File information """
        # ATTRIBUTE GROUP
        attributes_layout = QVBoxLayout()
        attributes_layout.addWidget(self.hdf5_attributes_qtableview)
        attributes_group = QGroupBox(self.tr("File informations"))
        attributes_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        attributes_group.setLayout(attributes_layout)

        # first line layout (selection + (graphic+export))
        hbox_layout = QHBoxLayout()
        hbox_layout.addWidget(selectionfile_group, stretch=1)

        vbox_plot_export_layout = QVBoxLayout()
        vbox_plot_export_layout.addWidget(self.plot_group)
        vbox_plot_export_layout.addWidget(self.dataexporter_group)
        vbox_plot_export_layout.addWidget(self.habitatvalueremover_group)
        vbox_plot_export_layout.setAlignment(Qt.AlignTop)
        hbox_layout.addLayout(vbox_plot_export_layout, stretch=1)

        # second line layout (attribute)
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(attributes_group)

        # global layout
        global_layout = QVBoxLayout(self)
        global_layout.addLayout(hbox_layout)
        global_layout.addLayout(vbox_layout)

        # add layout to group
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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

    def types_hdf5_change(self):
        """
        Ajust item list according to hdf5 type selected by user
        """
        index = self.types_hdf5_QComboBox.currentIndex()
        # nothing
        if index == 0:
            self.names_hdf5_QListWidget.clear()
            self.plot_group.variable_QListWidget.clear()
            self.plot_group.units_QListWidget.clear()
            self.plot_group.hide()
            self.dataexporter_group.change_layout(0)
            self.dataexporter_group.hide()
            self.habitatvalueremover_group.hide()
        # hydraulic
        if index == 1:
            names = hdf5_mod.get_filename_by_type("hydraulic", os.path.join(self.path_prj, "hdf5"))
            self.names_hdf5_QListWidget.clear()
            self.plot_group.variable_QListWidget.clear()
            self.plot_group.plot_result_QCheckBox.hide()
            self.dataexporter_group.change_layout(0)
            self.plot_group.show()
            self.dataexporter_group.show()
            self.habitatvalueremover_group.hide()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                self.dataexporter_group.change_layout(1)
        # substrate
        if index == 2:
            names = hdf5_mod.get_filename_by_type("substrate", os.path.join(self.path_prj, "hdf5"))
            self.names_hdf5_QListWidget.clear()
            self.plot_group.variable_QListWidget.clear()
            self.plot_group.plot_result_QCheckBox.hide()
            self.dataexporter_group.change_layout(0)
            self.plot_group.show()
            self.dataexporter_group.show()
            self.habitatvalueremover_group.hide()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                self.dataexporter_group.change_layout(2)
        # merge hab
        if index == 3:
            names = hdf5_mod.get_filename_by_type("habitat", os.path.join(self.path_prj, "hdf5"))
            self.names_hdf5_QListWidget.clear()
            self.plot_group.variable_QListWidget.clear()
            self.plot_group.plot_result_QCheckBox.show()
            self.dataexporter_group.change_layout(0)
            self.plot_group.show()
            self.dataexporter_group.show()
            self.habitatvalueremover_group.show()
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                self.dataexporter_group.change_layout(3)

        # update progress bar
        self.plot_group.count_plot()

    def names_hdf5_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        selection = self.names_hdf5_QListWidget.selectedItems()
        self.plot_group.variable_QListWidget.clear()
        self.plot_group.units_QListWidget.clear()
        self.plot_group.reach_QListWidget.clear()
        self.habitatvalueremover_group.existing_animal_QListWidget.clear()

        # one file selected
        if len(selection) == 1:
            hdf5name = selection[0].text()
            self.plot_group.units_QListWidget.clear()

            # create hdf5 class
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)

            # hydraulic
            if self.types_hdf5_QComboBox.currentIndex() == 1:
                self.plot_group.variable_QListWidget.addItems(hdf5.variables)
                if hdf5.reach_name:
                    self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)

            # substrat
            if self.types_hdf5_QComboBox.currentIndex() == 2:
                if hdf5.variables:  # if not False (from constant substrate) add items else nothing
                    self.plot_group.variable_QListWidget.addItems(hdf5.variables)
                    if hdf5.reach_name:
                        self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)

            # hab
            if self.types_hdf5_QComboBox.currentIndex() == 3:
                self.plot_group.variable_QListWidget.addItems(hdf5.variables)
                if hdf5.reach_name:
                    self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                    self.habitatvalueremover_group.existing_animal_QListWidget.addItems(hdf5.fish_list)

            # display hdf5 attributes
            tablemodel = MyTableModel(list(zip(hdf5.hdf5_attributes_name_text, hdf5.hdf5_attributes_info_text)), self)
            self.hdf5_attributes_qtableview.setModel(tablemodel)
            header = self.hdf5_attributes_qtableview.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.hdf5_attributes_qtableview.verticalHeader().setDefaultSectionSize(self.hdf5_attributes_qtableview.verticalHeader().minimumSectionSize())

        else:
            self.hdf5_attributes_qtableview.setModel(None)

        # count plot
        self.plot_group.count_plot()
        # count exports
        self.dataexporter_group.count_export()


class FigureProducerGroup(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.setTitle(title)
        self.plot_process_list = MyProcessList("plot")
        self.variables_to_remove = ["mesh", "mesh and points", "points elevation", "height", "velocity",
                                    "coarser_dominant", "max_slope_bottom", "max_slope_energy", "shear_stress"]
        self.init_ui()

    def init_ui(self):
        # existing_animal_QListWidget
        self.variable_hdf5_QLabel = QLabel(self.tr('variables'))
        self.variable_QListWidget = QListWidget()
        self.variable_QListWidget.setMinimumWidth(130)
        self.variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.variable_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.variable_hdf5_layout = QVBoxLayout()
        self.variable_hdf5_layout.setAlignment(Qt.AlignTop)
        self.variable_hdf5_layout.addWidget(self.variable_hdf5_QLabel)
        self.variable_hdf5_layout.addWidget(self.variable_QListWidget)

        # reach_QListWidget
        self.reach_hdf5_QLabel = QLabel(self.tr('reachs'))
        self.reach_QListWidget = QListWidget()
        self.reach_QListWidget.setMinimumWidth(110)
        self.reach_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.reach_QListWidget.itemSelectionChanged.connect(self.reach_hdf5_change)
        self.reach_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.reach_hdf5_layout = QVBoxLayout()
        self.reach_hdf5_layout.setAlignment(Qt.AlignTop)
        self.reach_hdf5_layout.addWidget(self.reach_hdf5_QLabel)
        self.reach_hdf5_layout.addWidget(self.reach_QListWidget)

        # units_QListWidget
        self.units_QLabel = QLabel(self.tr('units'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setMinimumWidth(50)
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.units_layout = QVBoxLayout()
        self.units_layout.setAlignment(Qt.AlignTop)
        self.units_layout.addWidget(self.units_QLabel)
        self.units_layout.addWidget(self.units_QListWidget)

        # export_type_QComboBox
        self.export_type_QLabel = QLabel(self.tr('View or export ?'))
        self.export_type_QComboBox = QComboBox()
        self.export_type_QComboBox.addItems(["interactive", "image export", "both"])
        self.export_type_layout = QVBoxLayout()
        self.export_type_layout.setAlignment(Qt.AlignTop)
        self.export_type_layout.addWidget(self.export_type_QLabel)
        self.export_type_layout.addWidget(self.export_type_QComboBox)

        # buttons plot_button
        self.plot_button = QPushButton(self.tr("run"))
        self.plot_button.clicked.connect(self.collect_data_from_gui_and_plot)
        self.plot_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.export_type_layout.addWidget(self.plot_button)

        # stop plot_button
        self.plot_stop_button = QPushButton(self.tr("stop"))
        self.plot_stop_button.clicked.connect(self.stop_plot)
        self.plot_stop_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.plot_stop_button.setEnabled(False)
        self.export_type_layout.addWidget(self.plot_stop_button)

        # type plot
        plot_type_qlabel = QLabel(self.tr("figure type :"))
        self.plot_map_QCheckBox = QCheckBox(self.tr("map"))
        self.plot_map_QCheckBox.setChecked(True)
        self.plot_map_QCheckBox.stateChanged.connect(self.count_plot)
        self.plot_result_QCheckBox = QCheckBox(self.tr("habitat values"))
        self.plot_result_QCheckBox.setChecked(False)
        self.plot_result_QCheckBox.stateChanged.connect(self.count_plot)

        # PLOT GROUP
        plot_layout = QHBoxLayout()
        plot_layout.addLayout(self.variable_hdf5_layout, 4)  # stretch factor
        plot_layout.addLayout(self.reach_hdf5_layout, 1)  # stretch factor
        plot_layout.addLayout(self.units_layout, 1)  # stretch factor
        plot_layout.addLayout(self.export_type_layout)
        plot_layout2 = QVBoxLayout()
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(plot_type_qlabel)
        plot_type_layout.addWidget(self.plot_map_QCheckBox)
        plot_type_layout.addWidget(self.plot_result_QCheckBox)
        plot_type_layout.setAlignment(Qt.AlignLeft)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.plot_process_list.progress_bar)
        progress_layout.addWidget(self.plot_process_list.progress_label)
        plot_layout2.addLayout(plot_layout)
        plot_layout2.addLayout(plot_type_layout)
        # plot_layout2.addWidget(self.progress_bar)
        plot_layout2.addLayout(progress_layout)
        #plot_group = QGroupBoxCollapsible(self.tr("Figure exporter/viewer"))
        self.setLayout(plot_layout2)

    def count_plot(self):
        """
        count number of graphic to produce and ajust progress bar range
        """
        types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type = self.collect_data_from_gui()
        plot_type = []
        if self.plot_map_QCheckBox.isChecked():
            plot_type = ["map"]
        if self.plot_result_QCheckBox.isChecked():
            plot_type = ["result"]
        if self.plot_map_QCheckBox.isChecked() and self.plot_result_QCheckBox.isChecked():
            plot_type = ["map", "result"]

        if types_hdf5 and names_hdf5 and variables and reach and units and plot_type:
            # is fish ?
            fish_names = [variable for variable in variables if variable not in self.variables_to_remove]
            variables_other = [variable for variable in variables if variable not in fish_names]

            # no fish
            if len(fish_names) == 0:
                if plot_type == ["result"]:
                    self.nb_plot = 0
                if plot_type == ["map"]:
                    self.nb_plot = len(names_hdf5) * len(variables) * len(reach) * len(units)
                if plot_type == ["map", "result"]:
                    self.nb_plot = len(names_hdf5) * len(variables) * len(reach) * len(units)

            # one fish
            if len(fish_names) == 1:
                if plot_type == ["result"]:
                    nb_map = 0
                else:
                    # one map by fish by unit
                    nb_map = len(names_hdf5) * len(fish_names) * len(reach) * len(units)
                if len(units) == 1:
                    if plot_type == ["map"]:
                        nb_wua_hv = 0
                    else:
                        nb_wua_hv = len(names_hdf5) * len(fish_names) * len(reach) * len(units)
                if len(units) > 1:
                    if plot_type == ["map"]:
                        nb_wua_hv = 0
                    else:
                        nb_wua_hv = len(names_hdf5) * len(fish_names)
                # total
                self.nb_plot = (len(names_hdf5) * len(variables_other) * len(reach) * len(units)) + nb_map + nb_wua_hv

            # multi fish
            if len(fish_names) > 1:
                if plot_type == ["result"]:
                    self.nb_plot = 1  #(len(names_hdf5) * len(variables_other) * len(units)) + 1
                if plot_type == ["map"]:
                    # one map by fish by unit
                    nb_map = len(fish_names) * len(reach) * len(units)
                    self.nb_plot = (len(names_hdf5) * len(variables_other) * len(reach) * len(units)) + nb_map
                if plot_type == ["map", "result"]:
                    # one map by fish by unit
                    nb_map = len(fish_names) * len(reach) * len(units)
                    self.nb_plot = (len(names_hdf5) * len(variables_other) * len(reach) * len(units)) + nb_map + 1

            # set prog
            if self.nb_plot != 0:
                self.plot_process_list.progress_bar.setRange(0, self.nb_plot)
            self.plot_process_list.progress_bar.setValue(0)
            self.plot_process_list.progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
        else:
            self.nb_plot = 0
            # set prog
            self.plot_process_list.progress_bar.setValue(0)
            self.plot_process_list.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

    def collect_data_from_gui(self):
        """
        Get selected values by user
        """
        # types
        types_hdf5 = self.parent().types_hdf5_QComboBox.currentText()

        # names
        selection = self.parent().names_hdf5_QListWidget.selectedItems()
        names_hdf5 = []
        for i in range(len(selection)):
            names_hdf5.append(selection[i].text())

        # variables
        selection = self.variable_QListWidget.selectedItems()
        variables = []
        for i in range(len(selection)):
            variables.append(selection[i].text())

        # variables
        selection = self.reach_QListWidget.selectedItems()
        reach = []
        for i in range(len(selection)):
            reach.append(selection[i].text())

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

        # type of view (interactif, export, both)
        export_type = self.export_type_QComboBox.currentText()

        # plot type (map, result)
        plot_type = []
        if self.plot_map_QCheckBox.isChecked():
            plot_type = ["map"]
        if self.plot_result_QCheckBox.isChecked():
            plot_type = ["result"]
        if self.plot_map_QCheckBox.isChecked() and self.plot_result_QCheckBox.isChecked():
            plot_type = ["map", "result"]

        # store values
        return types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type

    def collect_data_from_gui_and_plot(self):
        """
        Get selected values by user and plot them
        """
        types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type = self.collect_data_from_gui()
        self.plot(types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type)

    def reach_hdf5_change(self):
        """
         Ajust item list according to hdf5 filename selected by user
         """
        selection_file = self.parent().names_hdf5_QListWidget.selectedItems()
        selection_reach = self.reach_QListWidget.selectedItems()
        self.units_QListWidget.clear()

        # one file selected
        if len(selection_reach) == 1:
            hdf5name = selection_file[0].text()
            self.units_QListWidget.clear()

            # create hdf5 class
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)

            # add
            self.units_QListWidget.addItems(hdf5.units_name[self.reach_QListWidget.currentRow()])

        # more than one file selected
        elif len(selection_reach) > 1:
            # clear attributes hdf5_attributes_qtableview
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, selection_file[0].text())
            hdf5.open_hdf5_file(False)
            # check if units are equal between reachs
            units_equal = True
            for reach_num in range(len(hdf5.units_name) - 1):
                if hdf5.units_name[reach_num] != hdf5.units_name[reach_num + 1]:
                    units_equal = False
            if units_equal:  # homogene units between reach
                self.units_QListWidget.addItems(hdf5.units_name[0])
            if not units_equal:  # heterogne units between reach
                # clean
                self.units_QListWidget.clear()
                # message to user
                msg2 = QMessageBox(self)
                msg2.setIcon(QMessageBox.Warning)
                msg2.setWindowTitle(self.tr("Warning"))
                msg2.setText(
                    self.tr("The selected files don't have same units !"))
                msg2.setStandardButtons(QMessageBox.Ok)
                msg2.show()

        # count plot
        self.count_plot()

    def plot(self, types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type):
        """
        Plot
        :param types_hdf5: string representing the type of hdf5 ("hydraulic", "substrat", "habitat")
        :param names_hdf5: list of string representing hdf5 filenames
        :param variables: list of string representing variables to be ploted, depend on type of hdf5 selected ("height", "velocity", "mesh")
        :param units: list of string representing units names (timestep value or discharge)
        :param units_index: list of integer representing the position of units in hdf5 file
        :param export_type: string representing plot types production ("display", "export", "both")
        """
        if not types_hdf5:
            self.send_log.emit('Error: No hdf5 type selected.')
        if not names_hdf5:
            self.send_log.emit('Error: No hdf5 file selected.')
        if not variables:
            self.send_log.emit('Error: No variable selected.')
        if not reach:
            self.send_log.emit('Error: No reach selected.')
        if not units:
            self.send_log.emit('Error: No unit selected.')
        if self.nb_plot == 0:
            self.send_log.emit('Error: Selected variables and units not corresponding with figure type choices.')
        # check if number of display plot are > 30
        if export_type in ("display", "both") and self.nb_plot > 30:
            qm = QMessageBox
            ret = qm.question(self, self.tr("Warning"),
                              self.tr("Displaying a large number of plots may crash HABBY. "
                                      "It is recommended not to exceed a total number of plots "
                                      "greater than 30 at a time. \n\nDo you still want to display") + str(self.nb_plot) + self.tr("plots ?"
                                      "\n\nNB : There is no limit for exports."), qm.Yes | qm.No)
            if ret == qm.No:  # pas de plot
                return
        # Go plot
        if types_hdf5 and names_hdf5 and variables and reach and units and plot_type:
            # disable
            self.plot_button.setEnabled(False)
            # active stop button
            self.plot_stop_button.setEnabled(True)
            self.plot_production_stoped = False

            # figure option
            project_preferences = load_project_preferences(self.path_prj,
                                                               self.name_prj)
            project_preferences['type_plot'] = export_type  # "display", "export", "both"

            # init
            fish_names = [variable for variable in variables if variable not in self.variables_to_remove]

            # path
            path_hdf5 = os.path.join(self.path_prj, "hdf5")
            path_im = os.path.join(self.path_prj, "output", "figures")

            self.plot_process_list.export_production_stoped = False

            # check plot process done
            if self.plot_process_list.check_all_process_closed():
                self.plot_process_list.new_plots(self.nb_plot)
            else:
                self.plot_process_list.add_plots(self.nb_plot)

            # progress bar
            self.plot_process_list.progress_bar.setValue(0)
            self.plot_process_list.progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
            QCoreApplication.processEvents()

            # loop on all desired hdf5 file
            for name_hdf5 in names_hdf5:
                if not self.plot_production_stoped:  # stop loop with button
                    # create hdf5 class by file
                    hdf5 = hdf5_mod.Hdf5Management(self.path_prj, name_hdf5)

                    # read hdf5 data (get desired units)
                    if types_hdf5 == "hydraulic":  # load hydraulic data
                        hdf5.load_hdf5_hyd(units_index=units_index)
                        data_description = dict(reach_list=hdf5.data_description["hyd_reach_list"].split(", "),
                                                reach_number=hdf5.data_description["hyd_reach_number"],
                                                unit_number=hdf5.data_description["hyd_unit_number"],
                                                unit_type=hdf5.data_description["hyd_unit_type"],
                                                name_hdf5=hdf5.data_description["hyd_filename"])
                    if types_hdf5 == "substrate":  # load substrate data
                        hdf5.load_hdf5_sub(convert_to_coarser_dom=True)
                        data_description = dict(reach_list=hdf5.data_description["sub_reach_list"].split(", "),
                                                reach_number=hdf5.data_description["sub_reach_number"],
                                                unit_number=hdf5.data_description["sub_unit_number"],
                                                unit_type=hdf5.data_description["sub_unit_type"],
                                                name_hdf5=hdf5.data_description["sub_filename"],
                                                sub_classification_code=hdf5.data_description["sub_classification_code"])
                    if types_hdf5 == "habitat":  # load habitat data
                        hdf5.load_hdf5_hab(units_index=units_index,
                                           fish_names=fish_names,
                                           whole_profil=False,
                                           convert_to_coarser_dom=True)
                        data_description = dict(hdf5.data_description)
                        # change name attributes
                        data_description["reach_list"] = hdf5.data_description["hyd_reach_list"].split(", ")
                        data_description["reach_number"] = hdf5.data_description["hyd_reach_number"]
                        data_description["unit_number"] = hdf5.data_description["hyd_unit_number"]
                        data_description["unit_type"] = hdf5.data_description["hyd_unit_type"]
                        data_description["units_index"] = units_index
                        data_description["name_hdf5"] = hdf5.data_description["hab_filename"]

                    # for each reach
                    for reach_name in reach:
                        reach_num = data_description["reach_list"].index(reach_name)
                        # for one or more desired units ==> habitat data (HV and WUA)
                        if fish_names and plot_type != ["map"] and not self.plot_production_stoped:
                            state = Value("i", 0)
                            plot_hab_fig_spu_process = Process(target=plot_mod.plot_fish_hv_wua,
                                                               args=(state,
                                                                     data_description,
                                                                     reach_num,
                                                                     fish_names,
                                                                     path_im,
                                                                     name_hdf5,
                                                                     project_preferences),
                                                               name="plot_fish_hv_wua")
                            self.plot_process_list.append((plot_hab_fig_spu_process, state))

                        # for each desired units ==> maps
                        if plot_type != ["result"]:
                            for unit_num, t in enumerate(units_index):
                                # input data
                                if "mesh" in variables and not self.plot_production_stoped:  # mesh
                                    state = Value("i", 0)
                                    mesh_process = Process(target=plot_mod.plot_map_mesh,
                                                           args=(state,
                                                                 hdf5.data_2d["xy"][reach_num][unit_num],
                                                                 hdf5.data_2d["tin"][reach_num][unit_num],
                                                                 project_preferences,
                                                                 data_description,
                                                                 path_im,
                                                                 reach_name,
                                                                 units[unit_num],
                                                                 False),
                                                               name="plot_map_mesh")
                                    self.plot_process_list.append((mesh_process, state))
                                if "mesh and points" in variables and not self.plot_production_stoped:  # mesh
                                    state = Value("i", 0)
                                    mesh_process = Process(target=plot_mod.plot_map_mesh,
                                                           args=(state,
                                                                 hdf5.data_2d["xy"][reach_num][unit_num],
                                                                 hdf5.data_2d["tin"][reach_num][unit_num],
                                                                 project_preferences,
                                                                 data_description,
                                                                 path_im,
                                                                 reach_name,
                                                                 units[unit_num],
                                                                 True),
                                                               name="plot_map_mesh_and_point")
                                    self.plot_process_list.append((mesh_process, state))
                                if "points elevation" in variables and not self.plot_production_stoped:  # mesh
                                    state = Value("i", 0)
                                    mesh_process = Process(target=plot_mod.plot_map_elevation,
                                                           args=(state,
                                                                 hdf5.data_2d["xy"][reach_num][unit_num],
                                                                 hdf5.data_2d["tin"][reach_num][unit_num],
                                                                 hdf5.data_2d["z"][reach_num][unit_num],
                                                                 project_preferences,
                                                                 data_description,
                                                                 path_im,
                                                                 reach_name,
                                                                 units[unit_num]),
                                                               name="plot_map_elevation")
                                    self.plot_process_list.append((mesh_process, state))
                                if "height" in variables and not self.plot_production_stoped:  # height
                                    state = Value("i", 0)
                                    height_process = Process(target=plot_mod.plot_map_height,
                                                             args=(state,
                                                                   hdf5.data_2d["xy"][reach_num][unit_num],
                                                                   hdf5.data_2d["tin"][reach_num][unit_num],
                                                                   project_preferences,
                                                                   data_description,
                                                                   hdf5.data_2d["h"][reach_num][unit_num],
                                                                   path_im,
                                                                   reach_name,
                                                                   units[unit_num]),
                                                               name="plot_map_height")
                                    self.plot_process_list.append((height_process, state))
                                if "velocity" in variables and not self.plot_production_stoped:  # velocity
                                    state = Value("i", 0)
                                    velocity_process = Process(target=plot_mod.plot_map_velocity,
                                                               args=(state,
                                                                     hdf5.data_2d["xy"][reach_num][unit_num],
                                                                     hdf5.data_2d["tin"][reach_num][unit_num],
                                                                     project_preferences,
                                                                     data_description,
                                                                     hdf5.data_2d["v"][reach_num][unit_num],
                                                                     path_im,
                                                                     reach_name,
                                                                     units[unit_num]),
                                                               name="plot_map_velocity")
                                    self.plot_process_list.append((velocity_process, state))
                                if "coarser_dominant" in variables and not self.plot_production_stoped:  # coarser_dominant
                                    state = Value("i", 0)
                                    susbtrat_process = Process(target=plot_mod.plot_map_substrate,
                                                               args=(state,
                                                                     hdf5.data_2d["xy"][reach_num][unit_num],
                                                                     hdf5.data_2d["tin"][reach_num][unit_num],
                                                                     hdf5.data_2d["sub"][reach_num][unit_num],
                                                                     data_description,
                                                                     path_im,
                                                                     project_preferences,
                                                                     reach_name,
                                                                     units[unit_num]),
                                                               name="plot_map_substrate")
                                    self.plot_process_list.append((susbtrat_process, state))
                                if "max_slope_bottom" in variables and not self.plot_production_stoped:  # height
                                    state = Value("i", 0)
                                    slope_bottom_process = Process(target=plot_mod.plot_map_slope_bottom,
                                                                   args=(state,
                                                                         hdf5.data_2d["xy"][reach_num][unit_num],
                                                                         hdf5.data_2d["tin"][reach_num][unit_num],
                                                                         hdf5.data_2d["max_slope_bottom"][reach_num][unit_num],
                                                                         data_description,
                                                                         project_preferences,
                                                                         path_im,
                                                                         reach_name,
                                                                         units[unit_num]),
                                                               name="plot_map_slope_bottom")
                                    self.plot_process_list.append((slope_bottom_process, state))
                                if "max_slope_energy" in variables and not self.plot_production_stoped:  # height
                                    state = Value("i", 0)
                                    slope_bottom_process = Process(target=plot_mod.plot_map_slope_energy,
                                                                   args=(state,
                                                                         hdf5.data_2d["xy"][reach_num][unit_num],
                                                                         hdf5.data_2d["tin"][reach_num][unit_num],
                                                                         hdf5.data_2d["max_slope_energy"][reach_num][unit_num],
                                                                         data_description,
                                                                         project_preferences,
                                                                         path_im,
                                                                         reach_name,
                                                                         units[unit_num]),
                                                               name="plot_map_slope_energy")
                                    self.plot_process_list.append((slope_bottom_process, state))
                                if "shear_stress" in variables and not self.plot_production_stoped:  # height
                                    state = Value("i", 0)
                                    slope_bottom_process = Process(target=plot_mod.plot_map_shear_stress,
                                                                   args=(state,
                                                                         hdf5.data_2d["xy"][reach_num][unit_num],
                                                                         hdf5.data_2d["tin"][reach_num][unit_num],
                                                                         hdf5.data_2d["shear_stress"][reach_num][unit_num],
                                                                         data_description,
                                                                         project_preferences,
                                                                         path_im,
                                                                         reach_name,
                                                                         units[unit_num]),
                                                               name="plot_map_shear_stress")
                                    self.plot_process_list.append((slope_bottom_process, state))
                                if fish_names and not self.plot_production_stoped:  # habitat data (maps)
                                    # map by fish
                                    for fish_index, fish_name in enumerate(fish_names):
                                        # plot map
                                        state = Value("i", 0)
                                        habitat_map_process = Process(target=plot_mod.plot_map_fish_habitat,
                                                                      args=(state,
                                                                            fish_name,
                                                                            hdf5.data_2d["xy"][reach_num][unit_num],
                                                                            hdf5.data_2d["tin"][reach_num][unit_num],
                                                                            hdf5.data_2d["hv_data"][fish_name][reach_num][unit_num],
                                                                            data_description["percent_area_unknown"][fish_name][reach_num][unit_num],
                                                                            data_description,
                                                                            project_preferences,
                                                                            path_im,
                                                                            reach_name,
                                                                            units[unit_num]),
                                                               name="plot_map_fish_habitat")
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
        # stop loop
        self.plot_process_list.export_production_stoped = True


class DataExporterGroup(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.setTitle(title)
        self.export_process_list = MyProcessList("export")
        self.current_type = 0
        self.checkbox_list = []
        self.nb_export = 0
        self.all_export_keys_available = ["mesh_whole_profile",
                                          "point_whole_profile",
                                          "mesh_units",
                                          "point_units",
                                          "elevation_whole_profile",
                                          "variables_units",
                                          "detailled_text",
                                          "fish_information"]
        self.init_ui()

    def init_ui(self):
        # connect double click to group
        self.doubleclick_check_uncheck_filter = DoubleClicOutputGroup()
        self.installEventFilter(self.doubleclick_check_uncheck_filter)
        self.doubleclick_check_uncheck_filter.double_clic_signal.connect(self.check_uncheck_all_checkboxs_at_once)

        """ hyd_export widgets """
        self.mesh_whole_profile_hyd = QCheckBox("")
        self.mesh_whole_profile_hyd.setObjectName("mesh_whole_profile_hyd")
        self.mesh_whole_profile_hyd.stateChanged.connect(self.count_export)
        self.point_whole_profile_hyd = QCheckBox("")
        self.point_whole_profile_hyd.setObjectName("point_whole_profile_hyd")
        self.point_whole_profile_hyd.stateChanged.connect(self.count_export)
        self.mesh_units_hyd = QCheckBox("")
        self.mesh_units_hyd.setObjectName("mesh_units_hyd")
        self.mesh_units_hyd.stateChanged.connect(self.count_export)
        self.point_units_hyd = QCheckBox("")
        self.point_units_hyd.setObjectName("point_units_hyd")
        self.point_units_hyd.stateChanged.connect(self.count_export)
        self.elevation_whole_profile_hyd = QCheckBox("")
        self.elevation_whole_profile_hyd.setObjectName("elevation_whole_profile_hyd")
        self.elevation_whole_profile_hyd.stateChanged.connect(self.count_export)
        self.variables_units_hyd = QCheckBox("")
        self.variables_units_hyd.setObjectName("variables_units_hyd")
        self.variables_units_hyd.stateChanged.connect(self.count_export)
        self.detailled_text_hyd = QCheckBox("")
        self.detailled_text_hyd.setObjectName("detailled_text_hyd")
        self.detailled_text_hyd.stateChanged.connect(self.count_export)
        self.hyd_checkbox_list = [self.mesh_whole_profile_hyd,
                                  self.point_whole_profile_hyd,
                                  self.mesh_units_hyd,
                                  self.point_units_hyd,
                                  self.elevation_whole_profile_hyd,
                                  self.variables_units_hyd,
                                  self.detailled_text_hyd]

        """ hab_export widgets """
        self.mesh_units_hab = QCheckBox("")
        self.mesh_units_hab.setObjectName("mesh_units_hab")
        self.mesh_units_hab.stateChanged.connect(self.count_export)
        self.point_units_hab = QCheckBox("")
        self.point_units_hab.setObjectName("point_units_hab")
        self.point_units_hab.stateChanged.connect(self.count_export)
        self.elevation_whole_profile_hab = QCheckBox("")
        self.elevation_whole_profile_hab.setObjectName("elevation_whole_profile_hab")
        self.elevation_whole_profile_hab.stateChanged.connect(self.count_export)
        self.variables_units_hab = QCheckBox("")
        self.variables_units_hab.setObjectName("variables_units_hab")
        self.variables_units_hab.stateChanged.connect(self.count_export)
        self.habitat_text_hab = QCheckBox("")
        self.habitat_text_hab.setObjectName("habitat_text_hab")
        self.habitat_text_hab.stateChanged.connect(self.count_export)
        self.detailled_text_hab = QCheckBox("")
        self.detailled_text_hab.setObjectName("detailled_text_hab")
        self.detailled_text_hab.stateChanged.connect(self.count_export)
        self.fish_information_hab = QCheckBox("")
        self.fish_information_hab.setObjectName("fish_information_hab")
        self.fish_information_hab.stateChanged.connect(self.count_export)
        self.hab_checkbox_list = [self.mesh_units_hab,
                                  self.point_units_hab,
                                  self.elevation_whole_profile_hab,
                                  self.variables_units_hab,
                                  self.habitat_text_hab,
                                  self.detailled_text_hab,
                                  self.fish_information_hab]

        """ data_exporter widgets """
        self.data_exporter_run_pushbutton = QPushButton(self.tr("run"))
        self.data_exporter_run_pushbutton.clicked.connect(self.start_export)
        self.data_exporter_run_pushbutton.setFixedWidth(110)
        self.data_exporter_run_pushbutton.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_exporter_run_pushbutton.setEnabled(True)
        self.data_exporter_stop_pushbutton = QPushButton(self.tr("stop"))
        self.data_exporter_stop_pushbutton.clicked.connect(self.stop_export)
        self.data_exporter_stop_pushbutton.setEnabled(False)
        self.data_exporter_stop_pushbutton.setFixedWidth(110)
        self.data_exporter_stop_pushbutton.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        """ empty layout """
        self.empty_export_layout = QGridLayout()
        self.empty_export_widget = QWidget()
        self.empty_export_widget.setLayout(self.empty_export_layout)

        """ hyd_export layout """
        self.hyd_export_layout = QGridLayout()
        # row 1
        self.hyd_export_layout.addWidget(QLabel("Geopackage (.gpkg)"), 1, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Mesh whole profile")), 1, 1)
        self.hyd_export_layout.addWidget(self.mesh_whole_profile_hyd, 1, 2, Qt.AlignCenter)
        # row 2
        self.hyd_export_layout.addWidget(QLabel("Geopackage (.gpkg)"), 2, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Point whole profile")), 2, 1)
        self.hyd_export_layout.addWidget(self.point_whole_profile_hyd, 2, 2, Qt.AlignCenter)
        # row 3
        self.hyd_export_layout.addWidget(QLabel("Geopackage (.gpkg)"), 3, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Mesh units")), 3, 1)
        self.hyd_export_layout.addWidget(self.mesh_units_hyd, 3, 2, Qt.AlignCenter)
        # row 4
        self.hyd_export_layout.addWidget(QLabel("Geopackage (.gpkg)"), 4, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Point units")), 4, 1)
        self.hyd_export_layout.addWidget(self.point_units_hyd, 4, 2, Qt.AlignCenter)
        # row 5
        self.hyd_export_layout.addWidget(QHLine(), 5, 0, 1, 3)
        # row 6
        self.hyd_export_layout.addWidget(QLabel("3D (.stl)"), 6, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Mesh whole profile")), 6, 1)
        self.hyd_export_layout.addWidget(self.elevation_whole_profile_hyd, 6, 2, Qt.AlignCenter)
        # row 7
        self.hyd_export_layout.addWidget(QLabel("3D (.pvd, .vtu)"), 7, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Mesh units")), 7, 1)
        self.hyd_export_layout.addWidget(self.variables_units_hyd, 7, 2, Qt.AlignCenter)
        # row 8
        self.hyd_export_layout.addWidget(QHLine(), 8, 0, 1, 3)
        # row 9
        self.hyd_export_layout.addWidget(QLabel("Text (.txt)"), 9, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Detailled mesh and points")), 9, 1)
        self.hyd_export_layout.addWidget(self.detailled_text_hyd, 9, 2, Qt.AlignCenter)
        # hyd_export_widget
        self.hyd_export_widget = QWidget()
        self.hyd_export_widget.hide()
        self.hyd_export_widget.setLayout(self.hyd_export_layout)

        """ hab_export_layout """
        self.hab_export_layout = QGridLayout()
        # row 3
        self.hab_export_layout.addWidget(QLabel("Geopackage (.gpkg)"), 3, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Mesh units")), 3, 1)
        self.hab_export_layout.addWidget(self.mesh_units_hab, 3, 2, Qt.AlignCenter)
        # row 4
        self.hab_export_layout.addWidget(QLabel("Geopackage (.gpkg)"), 4, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Point units")), 4, 1)
        self.hab_export_layout.addWidget(self.point_units_hab, 4, 2, Qt.AlignCenter)
        # row 5
        self.hab_export_layout.addWidget(QHLine(), 5, 0, 1, 4)
        # row 6
        self.hab_export_layout.addWidget(QLabel("3D (.stl)"), 6, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Mesh whole profile")), 6, 1)
        self.hab_export_layout.addWidget(self.elevation_whole_profile_hab, 6, 2, Qt.AlignCenter)
        # row 7
        self.hab_export_layout.addWidget(QLabel("3D (.pvd, .vtu)"), 7, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Mesh units")), 7, 1)
        self.hab_export_layout.addWidget(self.variables_units_hab, 7, 2, Qt.AlignCenter)
        # row 9
        self.hab_export_layout.addWidget(QHLine(), 9, 0, 1, 4)
        # row 10
        self.hab_export_layout.addWidget(QLabel("Text (.txt)"), 10, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Global habitat values")), 10, 1)
        self.hab_export_layout.addWidget(self.habitat_text_hab, 10, 2, Qt.AlignCenter)
        # row 11
        self.hab_export_layout.addWidget(QLabel("Text (.txt)"), 11, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Detailled habitat values")), 11, 1)
        self.hab_export_layout.addWidget(self.detailled_text_hab, 11, 2, Qt.AlignCenter)
        # row 12
        self.hab_export_layout.addWidget(QHLine(), 12, 0, 1, 4)
        # row 13
        self.hab_export_layout.addWidget(QLabel(self.tr("Report (figure extension)")), 13, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Fish informations")), 13, 1)
        self.hab_export_layout.addWidget(self.fish_information_hab, 13, 2, Qt.AlignCenter)

        # hab_export_widget
        self.hab_export_widget = QWidget()
        self.hab_export_widget.hide()
        self.hab_export_widget.setLayout(self.hab_export_layout)

        """ progress layout """
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.export_process_list.progress_bar)
        progress_layout.addWidget(self.export_process_list.progress_label)

        """ run_stop_layout """
        run_stop_layout = QVBoxLayout()
        run_stop_layout.addWidget(self.data_exporter_run_pushbutton)
        run_stop_layout.addWidget(self.data_exporter_stop_pushbutton)

        """ data_exporter layout """
        self.data_exporter_layout = QGridLayout()
        self.data_exporter_layout.addWidget(self.empty_export_widget, 0, 0)
        self.data_exporter_layout.addWidget(self.hyd_export_widget, 0, 0)
        self.data_exporter_layout.addWidget(self.hab_export_widget, 0, 0)
        self.data_exporter_layout.addLayout(run_stop_layout, 0, 1)
        self.data_exporter_layout.addLayout(progress_layout, 1, 0, 1, 2)
        self.setLayout(self.data_exporter_layout)

    def change_layout(self, type):
        if type == 0:
            self.empty_export_widget.show()
            self.hyd_export_widget.hide()
            self.hab_export_widget.hide()
            self.checkbox_list = []
            self.current_type = 0
        if type == 1:
            self.empty_export_widget.hide()
            self.hyd_export_widget.show()
            self.hab_export_widget.hide()
            self.checkbox_list = self.hyd_checkbox_list
            self.current_type = 1
        if type == 2:
            self.empty_export_widget.show()
            self.hyd_export_widget.hide()
            self.hab_export_widget.hide()
            self.checkbox_list = []
            self.current_type = 2
        if type == 3:
            self.empty_export_widget.hide()
            self.hyd_export_widget.hide()
            self.hab_export_widget.show()
            self.checkbox_list = self.hab_checkbox_list
            self.current_type = 3
        # refresh group gui
        if self.isChecked():  # if open
            self.setChecked(False)  # close group
            self.setChecked(True)  # open group

    def check_uncheck_all_checkboxs_at_once(self):
        checked = False

        if self.current_type == 0:
            self.checkbox_list = []

        if self.current_type == 1:
            checked = self.mesh_whole_profile_hyd.isChecked()

        if self.current_type == 2:
            self.checkbox_list = []
            checked = False

        if self.current_type == 3:
            checked = self.mesh_units_hab.isChecked()

        # uncheck all
        if checked:
            [checkbox.setChecked(False) for checkbox in self.checkbox_list]
        else:
            [checkbox.setChecked(True) for checkbox in self.checkbox_list]

    def collect_data_from_gui(self):
        """
        Get selected values by user
        """
        # types
        types_hdf5 = self.parent().types_hdf5_QComboBox.currentText()

        # names
        selection = self.parent().names_hdf5_QListWidget.selectedItems()
        names_hdf5 = []
        for i in range(len(selection)):
            names_hdf5.append(selection[i].text())

        # exports
        export_names = [checkbox.objectName() for checkbox in self.checkbox_list]
        export_activated = [checkbox.isChecked() for checkbox in self.checkbox_list]
        export_dict = dict(zip(export_names, export_activated))

        # store values
        return types_hdf5, names_hdf5, export_dict

    def count_export(self):
        """
        count number of export to produce and ajust progress bar range
        """
        types_hdf5, names_hdf5, export_dict = self.collect_data_from_gui()

        if types_hdf5 and names_hdf5 and any(export_dict.values()):
            self.nb_export = len(names_hdf5) * sum(export_dict.values())

            # set prog
            if self.nb_export != 0:
                self.export_process_list.progress_bar.setRange(0, self.nb_export)
            self.export_process_list.progress_bar.setValue(0)
            self.export_process_list.progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_export))
        else:
            self.nb_export = 0
            # set prog
            self.export_process_list.progress_bar.setValue(0)
            self.export_process_list.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

    def start_export(self):
        types_hdf5, names_hdf5, export_dict = self.collect_data_from_gui()
        if not types_hdf5:
            self.send_log.emit('Error:' + self.tr(' No hdf5 type selected.'))
        elif not names_hdf5:
            self.send_log.emit('Error:' + self.tr(' No hdf5 file selected.'))
        elif self.nb_export == 0:
            self.send_log.emit('Error:' + self.tr(' No export choosen.'))

        # Go export
        if types_hdf5 and names_hdf5:
            # disable
            self.data_exporter_run_pushbutton.setEnabled(False)
            # active stop button
            self.data_exporter_stop_pushbutton.setEnabled(True)
            self.export_production_stoped = False

            # figure option
            project_preferences = load_project_preferences(self.path_prj,
                                                           self.name_prj)

            # export_production_stoped
            self.export_process_list.export_production_stoped = False

            # check plot process done
            if self.export_process_list.check_all_process_closed():
                self.export_process_list.new_plots(self.nb_export)
            else:
                self.export_process_list.add_plots(self.nb_export)

            # progress bar
            self.export_process_list.progress_bar.setValue(0)
            self.export_process_list.progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_export))
            QCoreApplication.processEvents()

            # loop on all desired hdf5 file
            for name_hdf5 in names_hdf5:
                if not self.export_production_stoped:  # stop loop with button
                    # fake temporary project_preferences
                    if self.current_type == 1:  # hydraulic
                        index_dict = 0
                    else:
                        index_dict = 1

                    # set to False all export before setting specific export to True
                    for key in self.all_export_keys_available:
                        project_preferences[key][index_dict] = False

                    # setting specific export to True
                    for key in export_dict.keys():
                        project_preferences[key[:-4]][index_dict] = export_dict[key]

                    # create hdf5 class by file
                    hdf5 = hdf5_mod.Hdf5Management(self.path_prj, name_hdf5)
                    hdf5.project_preferences = project_preferences

                    # hydraulic
                    if types_hdf5 == "hydraulic":  # load hydraulic data
                        hdf5.load_hdf5_hyd(whole_profil=True)
                        total_gpkg_export = sum([export_dict["mesh_whole_profile_hyd"], export_dict["point_whole_profile_hyd"], export_dict["mesh_units_hyd"], export_dict["point_units_hyd"]])
                        if export_dict["mesh_whole_profile_hyd"] or export_dict["point_whole_profile_hyd"] or export_dict["mesh_units_hyd"] or export_dict["point_units_hyd"]:
                            # append fake first
                            for fake_num in range(1, total_gpkg_export):
                                self.export_process_list.append((Process(name="fake" + str(fake_num)), Value("i", 1)))
                            state = Value("i", 0)
                            export_gpkg_process = Process(target=hdf5.export_gpkg,
                                                          args=(state, ),
                                                          name="export_gpkg")
                            self.export_process_list.append((export_gpkg_process, state))

                        if export_dict["elevation_whole_profile_hyd"]:
                            state = Value("i", 0)
                            export_stl_process = Process(target=hdf5.export_stl,
                                                          args=(state, ),
                                                          name="export_stl")
                            self.export_process_list.append((export_stl_process, state))
                        if export_dict["variables_units_hyd"]:
                            state = Value("i", 0)
                            export_paraview_process = Process(target=hdf5.export_paraview,
                                                          args=(state, ),
                                                          name="export_paraview")
                            self.export_process_list.append((export_paraview_process, state))
                        if export_dict["detailled_text_hyd"]:
                            state = Value("i", 0)
                            export_detailled_mesh_txt_process = Process(target=hdf5.export_detailled_txt,
                                                                        args=(state,),
                                                                        name="export_detailled_txt")
                            self.export_process_list.append((export_detailled_mesh_txt_process, state))

                    # substrate
                    if types_hdf5 == "substrate":  # load substrate data
                        hdf5.load_hdf5_sub()

                    # habitat
                    if types_hdf5 == "habitat":  # load habitat data
                        hdf5.load_hdf5_hab(whole_profil=True)
                        total_gpkg_export = sum([export_dict["mesh_units_hab"], export_dict["point_units_hab"]])
                        if export_dict["mesh_units_hab"] or export_dict["point_units_hab"]:
                            # append fake first
                            for fake_num in range(1, total_gpkg_export):
                                self.export_process_list.append((Process(name="fake" + str(fake_num)), Value("i", 1)))
                            state = Value("i", 0)
                            export_gpkg_process = Process(target=hdf5.export_gpkg,
                                                          args=(state, ),
                                                          name="export_gpkg")
                            self.export_process_list.append((export_gpkg_process, state))
                        if export_dict["elevation_whole_profile_hab"]:
                            state = Value("i", 0)
                            export_stl_process = Process(target=hdf5.export_stl,
                                                          args=(state, ),
                                                          name="export_stl")
                            self.export_process_list.append((export_stl_process, state))
                        if export_dict["variables_units_hab"]:
                            state = Value("i", 0)
                            export_paraview_process = Process(target=hdf5.export_paraview,
                                                          args=(state, ),
                                                          name="export_paraview")
                            self.export_process_list.append((export_paraview_process, state))
                        if export_dict["habitat_text_hab"]:
                            state = Value("i", 0)
                            export_spu_txt_process = Process(target=hdf5.export_spu_txt,
                                                          args=(state, ),
                                                          name="export_spu_txt")
                            self.export_process_list.append((export_spu_txt_process, state))
                        if export_dict["detailled_text_hab"]:
                            state = Value("i", 0)
                            export_detailled_mesh_txt_process = Process(target=hdf5.export_detailled_txt,
                                                          args=(state, ),
                                                          name="export_detailled_txt")
                            self.export_process_list.append((export_detailled_mesh_txt_process, state))
                        if export_dict["fish_information_hab"]:
                            if hdf5.fish_list:
                                state = Value("i", 0)
                                export_pdf_process = Process(target=hdf5.export_pdf,
                                                              args=(state,),
                                                          name="export_pdf")
                                self.export_process_list.append((export_pdf_process, state))
                            else:
                                self.send_log.emit('Error: ' + self.tr('No computed models in this .hab file.'))

            # activate
            self.data_exporter_run_pushbutton.setEnabled(True)
            # disable stop button
            self.data_exporter_stop_pushbutton.setEnabled(False)

    def stop_export(self):
        # stop plot production
        self.export_production_stoped = True
        # activate
        self.data_exporter_run_pushbutton.setEnabled(True)
        # disable stop button
        self.data_exporter_stop_pushbutton.setEnabled(False)
        # stop loop
        self.export_process_list.export_production_stoped = True
        # kill_all_process
        self.export_process_list.kill_all_process()


class HabitatValueRemover(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.setTitle(title)
        self.init_ui()

    def init_ui(self):
        """ widgets """
        existing_animal_title_QLabel = QLabel(self.tr('Existing aquatic animal habitat values :'))
        self.existing_animal_QListWidget = QListWidget()
        self.existing_animal_QListWidget.setMinimumWidth(130)
        self.existing_animal_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.remove_animal_button = QPushButton(self.tr("remove selected animals"))
        self.remove_animal_button.clicked.connect(self.remove_animal_selected)

        """ layout """
        existing_animal_layout = QVBoxLayout()
        existing_animal_layout.addWidget(existing_animal_title_QLabel)
        existing_animal_layout.addWidget(self.existing_animal_QListWidget)
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.remove_animal_button)
        button_layout.setAlignment(Qt.AlignBottom)

        plot_layout = QHBoxLayout()
        plot_layout.addLayout(existing_animal_layout, 4)  # stretch factor
        plot_layout.addLayout(button_layout, 1)  # stretch factor
        self.setLayout(plot_layout)

    def remove_animal_selected(self):
        file_selection = self.parent().names_hdf5_QListWidget.selectedItems()
        if len(file_selection) == 1:
            hdf5name = file_selection[0].text()
        else:
            print("Warning: No file selected.")
            return

        # selected fish
        selection = self.existing_animal_QListWidget.selectedItems()
        fish_names = []
        for i in range(len(selection)):
            fish_names.append(selection[i].text())

        # remove
        hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
        hdf5.open_hdf5_file(False)
        hdf5.remove_fish_hab(fish_names)

        # refresh
        self.parent().names_hdf5_change()


class MyProcessList(list):
    """
    This class is a subclass of class list created in order to analyze the status of the processes and the refresh of the progress bar in real time.

    :param nb_plot_total: integer value representing the total number of graphs to be produced.
    :param progress_bar: Qprogressbar of DataExplorerFrame to be refreshed
    """

    def __init__(self, type):
        super().__init__()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_label = QLabel()
        self.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))
        self.nb_plot_total = 0
        self.export_production_stoped = False
        self.process_type = type  # cal or plot or export

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

        self.check_all_process_produced()

    def check_all_process_produced(self):
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
                        if self.export_production_stoped:
                            break
                        for j in [k for k, l in enumerate(state_list) if l == 0]:
                            state = self[j][1].value
                            state_list[j] = state
                            if state == 1:
                                nb_finished = nb_finished + 1
                                self.progress_bar.setValue(nb_finished)
                                self.progress_label.setText("{0:.0f}/{1:.0f}".format(nb_finished, self.nb_plot_total))
                                QCoreApplication.processEvents()

        self.progress_bar.setValue(nb_finished)
        self.progress_label.setText("{0:.0f}/{1:.0f}".format(nb_finished, self.nb_plot_total))
        QCoreApplication.processEvents()

    def check_all_process_closed(self):
        """
        Check if a process is alive (plot window open)
        """
        if any([self[i][0].is_alive() for i in range(len(self))]):  # plot window open or plot not finished
            return False
        else:
            return True

    def kill_all_process(self):
        """
        Close all plot process. usefull for button close all figure and for closeevent of Main_windows_1.
        """
        for i in range(len(self)):
            self[i][0].terminate()
            #print(self[i][0].name, "terminate(), state : ", self[i][1].value)


class MyTableModel(QAbstractTableModel):
    def __init__(self, datain, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = datain

    def rowCount(self, parent):
        return len(self.arraydata)

    def columnCount(self, parent):
        return len(self.arraydata[0])

    def data(self, index, role):
        if not index.isValid():
            return QVariant()
        elif role != Qt.DisplayRole:
            return QVariant()
        return QVariant(self.arraydata[index.row()][index.column()])
