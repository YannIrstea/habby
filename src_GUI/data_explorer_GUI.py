# -*-coding:Latin-1 -*
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
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QWidget, QAbstractItemView, QSpacerItem, \
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, QVBoxLayout, QHBoxLayout, QGridLayout, \
    QSizePolicy, QScrollArea, QTableView, QMenu, QAction, QProgressBar, QListWidgetItem

from src import hdf5_mod
from src import plot_mod
from src.tools_mod import MyProcessList, create_map_plot_string_dict
from src.project_properties_mod import load_project_properties
from src.tools_mod import QHLine, DoubleClicOutputGroup
from src_GUI.tools_GUI import QGroupBoxCollapsible
from src.hydraulic_bases import HydraulicVariableUnitManagement


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
        # self.setAutoFillBackground(True)
        # p = self.palette()
        # p.setColor(self.backgroundRole(), Qt.white)
        # self.setPalette(p)

        # add layout
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(self.data_explorer_frame)

    def refresh_type(self):
        index = self.data_explorer_frame.types_hdf5_QComboBox.currentIndex()
        if index:
            self.data_explorer_frame.types_hdf5_QComboBox.setCurrentIndex(0)
            self.data_explorer_frame.types_hdf5_QComboBox.setCurrentIndex(index)
            if self.data_explorer_frame.names_hdf5_index:
                self.data_explorer_frame.reselect_hdf5_name_after_rename()
                self.data_explorer_frame.names_hdf5_index = None

    def refresh_filename(self):
        item = self.data_explorer_frame.names_hdf5_QListWidget.selectedItems()
        if item:
            self.data_explorer_frame.names_hdf5_QListWidget.setCurrentItem(None)
            self.data_explorer_frame.names_hdf5_QListWidget.setCurrentItem(item[0])


class DataExplorerFrame(QFrame):
    """
    This class is a subclass of class QGroupBox.
    """
    send_remove = pyqtSignal(str, name='send_remove')
    send_rename = pyqtSignal(str, name='send_rename')

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.nb_plot = 0
        self.names_hdf5_index = None
        self.file_to_remove_list = []
        self.init_ui()
        self.plot_production_stoped = False

    def init_ui(self):
        # title
        # self.setTitle(self.tr('HABBY data explorer'))
        # self.setStyleSheet('QGroupBox {font-weight: bold;}')

        verticalSpacer = QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Expanding)
        """ File selection """
        # hab_filenames_qcombobox
        self.types_hdf5_QLabel = QLabel(self.tr('file types'))
        self.types_hdf5_QComboBox = QComboBox()
        self.types_hdf5_list = ["", "hydraulic", "substrate", "habitat"]
        self.types_hdf5_QComboBox.addItems(self.types_hdf5_list)
        self.types_hdf5_QComboBox.currentIndexChanged.connect(self.types_hdf5_change)
        self.names_hdf5_QLabel = QLabel(self.tr('filenames'))
        self.names_hdf5_QListWidget = QListWidget()
        self.names_hdf5_QListWidget.setObjectName("names_hdf5_QListWidget")
        self.names_hdf5_QListWidget.setMaximumHeight(100)
        self.names_hdf5_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.names_hdf5_QListWidget.itemSelectionChanged.connect(self.names_hdf5_change)
        self.names_hdf5_QListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.names_hdf5_QListWidget.customContextMenuRequested.connect(self.show_menu_hdf5_remover)

        """ types_hdf5_layout """
        self.types_hdf5_layout = QVBoxLayout()
        self.types_hdf5_layout.setAlignment(Qt.AlignTop)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QLabel)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QComboBox)

        """ names_hdf5_layout """
        self.names_hdf5_layout = QVBoxLayout()
        self.names_hdf5_layout.setAlignment(Qt.AlignTop)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QLabel)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QListWidget)

        """ plot_group """
        self.plot_group = FigureProducerGroup(self.path_prj, self.name_prj, self.send_log,
                                              self.tr("Figure viewer/exporter"))
        self.plot_group.setChecked(False)
        self.plot_group.hide()

        """ dataexporter_group """
        self.dataexporter_group = DataExporterGroup(self.path_prj, self.name_prj, self.send_log,
                                                    self.tr("Data exporter"))
        self.dataexporter_group.setChecked(False)
        self.dataexporter_group.hide()

        """ habitatvalueremover_group """
        self.habitatvalueremover_group = HabitatValueRemover(self.path_prj, self.name_prj, self.send_log,
                                                             self.tr("Habitat value remover"))
        self.habitatvalueremover_group.setChecked(False)
        self.habitatvalueremover_group.hide()

        """ file_information_group """
        self.file_information_group = FileInformation(self.path_prj, self.name_prj, self.send_log,
                                                      self.tr("File informations"))
        self.file_information_group.setChecked(False)
        self.file_information_group.hide()

        """ selectionfile_layout """
        selectionfile_layout = QHBoxLayout()
        selectionfile_layout.addLayout(self.types_hdf5_layout)
        selectionfile_layout.addLayout(self.names_hdf5_layout)
        selectionfile_layout.setAlignment(Qt.AlignTop)

        # global layout
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        global_layout.addLayout(selectionfile_layout)
        global_layout.addWidget(self.plot_group)
        global_layout.addWidget(self.dataexporter_group)
        global_layout.addWidget(self.habitatvalueremover_group)
        global_layout.addWidget(self.file_information_group)
        global_layout.addStretch()

        # add layout to group
        self.setLayout(global_layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setFrameShape(QFrame.NoFrame)

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
        self.names_hdf5_QListWidget.clear()

        # hydraulic
        if index == 1:
            names = hdf5_mod.get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                if len(names) == 1:
                    self.names_hdf5_QListWidget.selectAll()

        # substrate
        if index == 2:
            names = hdf5_mod.get_filename_by_type_physic("substrate", os.path.join(self.path_prj, "hdf5"))
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                if len(names) == 1:
                    self.names_hdf5_QListWidget.selectAll()

        # habitat
        if index == 3:
            names = hdf5_mod.get_filename_by_type_physic("habitat", os.path.join(self.path_prj, "hdf5"))
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                if len(names) == 1:
                    self.names_hdf5_QListWidget.selectAll()

    def names_hdf5_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        selection = self.names_hdf5_QListWidget.selectedItems()
        self.plot_group.mesh_variable_original_QListWidget.clear()
        self.plot_group.node_variable_original_QListWidget.clear()
        self.plot_group.mesh_variable_computable_QListWidget.clear()
        self.plot_group.node_variable_computable_QListWidget.clear()
        self.plot_group.units_QListWidget.clear()
        self.plot_group.reach_QListWidget.clear()
        self.plot_group.units_QLabel.setText(self.tr("unit(s)"))
        self.habitatvalueremover_group.existing_animal_QListWidget.clear()

        # one file selected
        if len(selection) == 1:
            hdf5name = selection[0].text()
            self.plot_group.units_QListWidget.clear()

            # create hdf5 class
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)

            # change unit_type
            if hasattr(hdf5, "unit_type"):
                hdf5.unit_type = hdf5.unit_type.replace("m3/s", "m<sup>3</sup>/s")
                self.plot_group.units_QLabel.setText(hdf5.unit_type)

            # hydraulic
            if self.types_hdf5_QComboBox.currentIndex() == 1:
                self.set_hydraulic_layout()
                if hdf5.hyd_mesh_variable_original_list:
                    self.plot_group.mesh_variable_original_QListWidget.addItems(hdf5.hyd_mesh_variable_original_list.names_gui)
                if hdf5.hyd_node_variable_original_list:
                    self.plot_group.node_variable_original_QListWidget.addItems(hdf5.hyd_node_variable_original_list.names_gui)
                if hdf5.hyd_mesh_variable_computable_list:
                    self.plot_group.mesh_variable_computable_QListWidget.addItems(hdf5.hyd_mesh_variable_computable_list.names_gui)
                if hdf5.hyd_node_variable_computable_list:
                    self.plot_group.node_variable_computable_QListWidget.addItems(hdf5.hyd_node_variable_computable_list.names_gui)

                if hdf5.reach_name:
                    self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                    if len(hdf5.reach_name) == 1:
                        self.plot_group.reach_QListWidget.selectAll()
                        if hdf5.nb_unit == 1:
                            self.plot_group.units_QListWidget.selectAll()

            # substrat
            if self.types_hdf5_QComboBox.currentIndex() == 2:
                self.set_substrate_layout()
                if hdf5.variables:  # if not False (from constant substrate) add items else nothing
                    self.plot_group.mesh_variable_original_QListWidget.addItems(hdf5.variables)
                    if hdf5.reach_name:
                        self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                        if len(hdf5.reach_name) == 1:
                            self.plot_group.reach_QListWidget.selectAll()
                            if hdf5.nb_unit == 1:
                                self.plot_group.units_QListWidget.selectAll()

            # habitat
            if self.types_hdf5_QComboBox.currentIndex() == 3:
                self.set_habitat_layout()
                self.plot_group.mesh_variable_original_QListWidget.addItems(hdf5.variables)
                if hdf5.reach_name:
                    self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                    self.habitatvalueremover_group.existing_animal_QListWidget.addItems(hdf5.fish_list)
                    if len(hdf5.reach_name) == 1:
                        self.plot_group.reach_QListWidget.selectAll()
                        if hdf5.nb_unit == 1:
                            self.plot_group.units_QListWidget.selectAll()

            # # change unit_type string
            # for element_index, _ in enumerate(hdf5.hdf5_attributes_info_text):
            #     if "m3/s" in hdf5.hdf5_attributes_info_text[element_index]:
            #         hdf5.hdf5_attributes_info_text[element_index] = hdf5.hdf5_attributes_info_text[element_index].replace("m3/s", u"m<sup>3</sup>/s")
            # display hdf5 attributes
            tablemodel = MyTableModel(list(zip(hdf5.hdf5_attributes_name_text, hdf5.hdf5_attributes_info_text)), self)
            self.file_information_group.hdf5_attributes_qtableview.setModel(tablemodel)
            header = self.file_information_group.hdf5_attributes_qtableview.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.file_information_group.hdf5_attributes_qtableview.verticalHeader().setDefaultSectionSize(
                self.file_information_group.hdf5_attributes_qtableview.verticalHeader().minimumSectionSize())

            # resize qtableview
            height = self.file_information_group.hdf5_attributes_qtableview.rowHeight(1) * (len(hdf5.hdf5_attributes_name_text) + 1)
            self.file_information_group.hdf5_attributes_qtableview.setFixedHeight(height)
            self.file_information_group.toggle_group(self.file_information_group.isChecked())
        else:
            self.set_empty_layout()

        # count plot
        self.plot_group.count_plot()
        # count exports
        self.dataexporter_group.count_export()

    def set_empty_layout(self):
        self.plot_group.mesh_variable_original_QListWidget.clear()
        self.plot_group.units_QListWidget.clear()
        self.plot_group.hide()
        self.dataexporter_group.change_export_layout(0)
        self.dataexporter_group.hide()
        self.habitatvalueremover_group.hide()
        self.file_information_group.hide()

    def set_hydraulic_layout(self):
        self.plot_group.mesh_variable_original_QListWidget.clear()
        self.plot_group.plot_result_QCheckBox.hide()
        self.dataexporter_group.change_export_layout(1)
        self.plot_group.show()
        self.dataexporter_group.show()
        self.habitatvalueremover_group.hide()
        self.file_information_group.show()

    def set_substrate_layout(self):
        self.plot_group.mesh_variable_original_QListWidget.clear()
        self.plot_group.plot_result_QCheckBox.hide()
        self.dataexporter_group.change_export_layout(2)
        self.plot_group.show()
        self.dataexporter_group.hide()
        self.habitatvalueremover_group.hide()
        self.file_information_group.show()

    def set_habitat_layout(self):
        self.plot_group.mesh_variable_original_QListWidget.clear()
        self.plot_group.plot_result_QCheckBox.show()
        self.dataexporter_group.change_export_layout(3)
        self.plot_group.show()
        self.dataexporter_group.show()
        self.habitatvalueremover_group.show()
        self.file_information_group.show()

    def show_menu_hdf5_remover(self, point):
        selection = self.names_hdf5_QListWidget.selectedItems()
        if selection:
            # create get_hdf5_list_to_remove_and_emit
            self.hdf5_remover_menu = QMenu()
            if len(selection) == 1:
                remove_action = QAction(self.tr("Remove selected file"))
                remove_action.setStatusTip(self.tr('Remove selected file and refresh solftware informations'))
            if len(selection) > 1:
                remove_action = QAction(self.tr("Remove selected files"))
                remove_action.setStatusTip(self.tr('Remove selected files and refresh solftware informations'))
            remove_action.triggered.connect(self.get_hdf5_list_to_remove_and_emit)
            self.hdf5_remover_menu.addAction(remove_action)
            # rename
            if len(selection) == 1:
                rename_action = QAction(self.tr("Rename selected file"))
                rename_action.setStatusTip(self.tr('Rename selected file and refresh solftware informations'))
                rename_action.triggered.connect(self.rename_item_selected)
                self.hdf5_remover_menu.addAction(rename_action)
            # all cases
            self.hdf5_remover_menu.exec_(self.names_hdf5_QListWidget.mapToGlobal(point))

    def get_hdf5_list_to_remove_and_emit(self):
        selection = self.names_hdf5_QListWidget.selectedItems()
        self.file_to_remove_list = []
        for item_selected in selection:
            self.file_to_remove_list.append(item_selected.text())

        # emit signal
        self.send_remove.emit("")

    def rename_item_selected(self):
        """
        Set the item editable and connect function to analyse user filename edition.
        """
        selection = self.names_hdf5_QListWidget.selectedItems()[0]  # get the selection
        self.file_to_rename = selection.text()  # get name before modification
        selection.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled)  # set item editable
        self.names_hdf5_QListWidget.editItem(selection)  # edit this item
        self.names_hdf5_QListWidget.itemChanged.connect(self.get_hdf5_name_to_rename_and_emit)  # connect function

    def get_hdf5_name_to_rename_and_emit(self, selection):
        self.file_renamed = selection.text()  # get name after modification
        self.names_hdf5_index = self.names_hdf5_QListWidget.currentIndex()
        # check if ext is not removed by user
        ext_before = os.path.splitext(self.file_to_rename)[1]
        ext_after = os.path.splitext(self.file_renamed)[1]
        if ext_after != ext_before:
            self.file_renamed = os.path.splitext(self.file_renamed)[0] + ext_before

        # disconnect, set item non editable and reconnect (in mainwindow)
        self.names_hdf5_QListWidget.blockSignals(True)
        selection.setFlags(~Qt.ItemIsEditable | Qt.ItemIsEnabled)  # set item not editable

        # emit signal
        self.send_rename.emit("")

    def reselect_hdf5_name_after_rename(self):
        self.names_hdf5_QListWidget.setCurrentIndex(self.names_hdf5_index)
        QCoreApplication.processEvents()


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
        self.total_fish_result = 0
        self.process_list = MyProcessList("plot")
        self.process_list.progress_signal.connect(self.show_prog)
        self.variables_to_remove = ["mesh", "elevation", "water_height", "water_velocity",
                                    "substrate_coarser", "substrate_dominant", "max_slope_bottom", "max_slope_energy",
                                    "shear_stress",
                                    "conveyance", "froude_number", "hydraulic_head", "water_level"]
        self.hvum = HydraulicVariableUnitManagement()
        self.gif_export = False
        self.nb_plot = 0
        self.init_ui()

    def init_ui(self):
        listwidgets_width = 130
        listwidgets_height = 100
        """ original data """
        self.mesh_variable_original_QLabel = QLabel(self.tr('original mesh variables'))
        self.mesh_variable_original_QListWidget = QListWidget()
        self.mesh_variable_original_QListWidget.setObjectName("mesh_variable_original_QListWidget")
        self.mesh_variable_original_QListWidget.setMinimumWidth(listwidgets_width)
        self.mesh_variable_original_QListWidget.setMaximumHeight(listwidgets_height)
        self.mesh_variable_original_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.mesh_variable_original_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.node_variable_original_QLabel = QLabel(self.tr('original node variables'))
        self.node_variable_original_QListWidget = QListWidget()
        self.node_variable_original_QListWidget.setObjectName("node_variable_original_QListWidget")
        self.node_variable_original_QListWidget.setMinimumWidth(listwidgets_width)
        self.node_variable_original_QListWidget.setMaximumHeight(listwidgets_height)
        self.node_variable_original_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.node_variable_original_QListWidget.itemSelectionChanged.connect(self.count_plot)
        
        """ computable data """
        self.mesh_variable_computable_QLabel = QLabel(self.tr('computable mesh variables'))
        self.mesh_variable_computable_QListWidget = QListWidget()
        self.mesh_variable_computable_QListWidget.setObjectName("mesh_variable_computable_QListWidget")
        self.mesh_variable_computable_QListWidget.setMinimumWidth(listwidgets_width)
        self.mesh_variable_computable_QListWidget.setMaximumHeight(listwidgets_height)
        self.mesh_variable_computable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.mesh_variable_computable_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.node_variable_computable_QLabel = QLabel(self.tr('computable node variables'))
        self.node_variable_computable_QListWidget = QListWidget()
        self.node_variable_computable_QListWidget.setObjectName("node_variable_computable_QListWidget")
        self.node_variable_computable_QListWidget.setMinimumWidth(listwidgets_width)
        self.node_variable_computable_QListWidget.setMaximumHeight(listwidgets_height)
        self.node_variable_computable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.node_variable_computable_QListWidget.itemSelectionChanged.connect(self.count_plot)
        
        self.variable_hdf5_layout = QGridLayout()

        """ original data """
        self.variable_hdf5_layout.addWidget(self.node_variable_original_QLabel, 0, 0)
        self.variable_hdf5_layout.addWidget(self.node_variable_original_QListWidget, 1, 0)
        self.variable_hdf5_layout.addWidget(self.mesh_variable_original_QLabel, 2, 0)
        self.variable_hdf5_layout.addWidget(self.mesh_variable_original_QListWidget, 3, 0)
        """ computable data """
        self.variable_hdf5_layout.addWidget(self.node_variable_computable_QLabel, 0, 1)
        self.variable_hdf5_layout.addWidget(self.node_variable_computable_QListWidget, 1, 1)
        self.variable_hdf5_layout.addWidget(self.mesh_variable_computable_QLabel, 2, 1)
        self.variable_hdf5_layout.addWidget(self.mesh_variable_computable_QListWidget, 3, 1)

        # reach_QListWidget
        self.reach_hdf5_QLabel = QLabel(self.tr('reach(s)'))
        self.reach_QListWidget = QListWidget()
        self.reach_QListWidget.setObjectName("reach_QListWidget")
        self.reach_QListWidget.setMinimumWidth(110)
        self.reach_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.reach_QListWidget.itemSelectionChanged.connect(self.reach_hdf5_change)
        #self.reach_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.reach_hdf5_layout = QVBoxLayout()
        self.reach_hdf5_layout.setAlignment(Qt.AlignTop)
        self.reach_hdf5_layout.addWidget(self.reach_hdf5_QLabel)
        self.reach_hdf5_layout.addWidget(self.reach_QListWidget)

        # units_QListWidget
        self.units_QLabel = QLabel(self.tr('unit(s)'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setObjectName("units_QListWidget")
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
        self.export_type_QComboBox.currentIndexChanged.connect(self.count_plot)
        self.export_type_layout = QVBoxLayout()
        self.export_type_layout.setAlignment(Qt.AlignTop)
        self.export_type_layout.addWidget(self.export_type_QLabel)
        self.export_type_layout.addWidget(self.export_type_QComboBox)

        # progress
        self.plot_progressbar = QProgressBar()
        self.plot_progressbar.setValue(0)
        self.plot_progressbar.setTextVisible(False)
        self.plot_progress_label = QLabel()
        self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

        # buttons plot_button
        self.plot_button = QPushButton(self.tr("run"))
        self.plot_button.clicked.connect(self.collect_data_from_gui_and_plot)
        self.plot_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.export_type_layout.addWidget(self.plot_button)
        self.plot_button.setEnabled(False)

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
        self.plot_result_QCheckBox = QCheckBox(self.tr("Global habitat values"))
        self.plot_result_QCheckBox.setChecked(False)
        self.plot_result_QCheckBox.stateChanged.connect(self.count_plot)

        # PLOT GROUP
        plot_layout = QHBoxLayout()
        plot_layout.addLayout(self.reach_hdf5_layout, 1)  # stretch factor
        plot_layout.addLayout(self.units_layout, 1)  # stretch factor
        plot_layout.addLayout(self.variable_hdf5_layout, 4)  # stretch factor
        plot_layout.addLayout(self.export_type_layout)
        plot_layout2 = QVBoxLayout()
        plot_type_layout = QHBoxLayout()
        plot_type_layout.addWidget(plot_type_qlabel)
        plot_type_layout.addWidget(self.plot_map_QCheckBox)
        plot_type_layout.addWidget(self.plot_result_QCheckBox)
        plot_type_layout.setAlignment(Qt.AlignLeft)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.plot_progressbar)
        progress_layout.addWidget(self.plot_progress_label)
        plot_layout2.addLayout(plot_layout)
        plot_layout2.addLayout(plot_type_layout)
        # plot_layout2.addWidget(self.progress_bar)
        plot_layout2.addLayout(progress_layout)
        # plot_group = QGroupBoxCollapsible(self.tr("Figure exporter/viewer"))
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
            self.hvum.get_original_computable_mesh_and_node_from_dict_gui(variables)
            # is fish ?
            total_habitat_variable_number = self.hvum.total_habitat_variable_number
            total_original_computable_number = self.hvum.total_original_computable_number
            # for GIF
            map_condition = plot_type == ["map"] or plot_type == ["map", "result"]  # map_condition
            export_type_condition = export_type == "image export"  # export_type_condition
            all_unit_condition = self.units_QListWidget.count() == len(units) and len(units) > 1  # all_unit_condition
            if map_condition and export_type_condition and all_unit_condition:
                self.gif_export = True
            else:
                self.gif_export = False

            # no fish
            if total_habitat_variable_number == 0:
                if plot_type == ["result"]:
                    self.nb_plot = 0
                if plot_type == ["map"]:
                    self.nb_plot = len(names_hdf5) * total_original_computable_number * len(reach) * len(units)
                    if self.gif_export:
                        self.nb_plot = self.nb_plot + total_original_computable_number * len(reach)
                if plot_type == ["map", "result"]:
                    self.nb_plot = len(names_hdf5) * total_original_computable_number * len(reach) * len(units)
                    if self.gif_export:
                        self.nb_plot = self.nb_plot + total_original_computable_number * len(reach)

            # one fish
            if total_habitat_variable_number == 1:
                if plot_type == ["result"]:
                    nb_map = 0
                else:
                    # one map by fish by unit
                    nb_map = len(names_hdf5) * total_habitat_variable_number * len(reach) * len(units)
                    if self.gif_export:
                        nb_map = nb_map + total_habitat_variable_number * len(reach) + total_original_computable_number * len(reach)
                if len(units) == 1:
                    if plot_type == ["map"]:
                        nb_wua_hv = 0
                    else:
                        nb_wua_hv = len(names_hdf5) * total_habitat_variable_number * len(reach) * len(units)
                if len(units) > 1:
                    if plot_type == ["map"]:
                        nb_wua_hv = 0
                    else:
                        nb_wua_hv = len(names_hdf5) * total_habitat_variable_number
                # total
                self.nb_plot = (len(names_hdf5) * total_original_computable_number * len(reach) * len(units)) + nb_map + nb_wua_hv

            # multi fish
            if total_habitat_variable_number > 1:
                if plot_type == ["result"]:
                    self.nb_plot = 1  # (len(names_hdf5) * total_original_computable_number * len(units)) + 1
                    self.total_fish_result = total_habitat_variable_number
                if plot_type == ["map"]:
                    # one map by fish by unit
                    nb_map = total_habitat_variable_number * len(reach) * len(units)
                    if self.gif_export:
                        nb_map = nb_map + total_habitat_variable_number * len(reach)
                    self.nb_plot = (len(names_hdf5) * total_original_computable_number * len(reach) * len(units)) + nb_map
                    if self.gif_export:
                        self.nb_plot = self.nb_plot + total_original_computable_number * len(reach)
                if plot_type == ["map", "result"]:
                    # one map by fish by unit
                    nb_map = total_habitat_variable_number * len(reach) * len(units)
                    if self.gif_export:
                        nb_map = nb_map + total_habitat_variable_number * len(reach)
                    self.nb_plot = (len(names_hdf5) * total_original_computable_number * len(reach) * len(units)) + nb_map + 1
                    if self.gif_export:
                        self.nb_plot = self.nb_plot + total_original_computable_number * len(reach)
            # set prog
            if self.nb_plot != 0:
                self.plot_progressbar.setRange(0, self.nb_plot)
                self.plot_button.setEnabled(True)
            self.plot_progressbar.setValue(0)
            self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
        else:
            self.nb_plot = 0
            self.plot_button.setEnabled(False)
            # set prog
            self.plot_progressbar.setValue(0)
            self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

    def show_prog(self, value):
        self.plot_progressbar.setValue(value)
        self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(value, self.nb_plot))
        QCoreApplication.processEvents()

        if value == self.nb_plot and self.nb_plot != 0:  # != 0 if closefig of mainwindow
            # activate
            self.plot_button.setEnabled(True)
            # disable stop button
            self.plot_stop_button.setEnabled(False)
            # log
            self.send_log.emit(self.tr("Figure(s) done."))

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

        # reach
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

        # variables
        variables = dict()
        variables["node_variable_original_list"] = [selection.text() for selection in self.node_variable_original_QListWidget.selectedItems()]
        variables["mesh_variable_original_list"] = [selection.text() for selection in self.mesh_variable_original_QListWidget.selectedItems()]
        variables["node_variable_computable_list"] = [selection.text() for selection in self.node_variable_computable_QListWidget.selectedItems()]
        variables["mesh_variable_computable_list"] = [selection.text() for selection in self.mesh_variable_computable_QListWidget.selectedItems()]

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
        self.plot_figure(types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type)

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

            # add units
            for item_text in hdf5.units_name[self.reach_QListWidget.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget.addItem(item)

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
                # self.units_QListWidget.addItems()
                for item_text in hdf5.units_name[0]:
                    item = QListWidgetItem(item_text)
                    item.setTextAlignment(Qt.AlignRight)
                    self.units_QListWidget.addItem(item)

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

    def plot_figure(self, types_hdf5, names_hdf5, variables, reach, units, units_index, export_type, plot_type):
        """
        Plot
        :param types_hdf5: string representing the type of hdf5 ("hydraulic", "substrat", "habitat")
        :param names_hdf5: list of string representing hdf5 filenames
        :param variables: list of string representing variables to be ploted, depend on type of hdf5 selected ("water_height", "water_velocity", "mesh")
        :param units: list of string representing units names (timestep value or discharge)
        :param units_index: list of integer representing the position of units in hdf5 file
        :param export_type: string representing export types ("display", "export", "both")
        :param plot_type: string representing plot types ["map", "result"]
        """
        if not types_hdf5:
            self.send_log.emit('Error: ' + self.tr('No hdf5 type selected.'))
        if not names_hdf5:
            self.send_log.emit('Error: ' + self.tr('No hdf5 file selected.'))
        if not variables:
            self.send_log.emit('Error: ' + self.tr('No variable selected.'))
        if not reach:
            self.send_log.emit('Error: ' + self.tr('No reach selected.'))
        if not units:
            self.send_log.emit('Error: ' + self.tr('No unit selected.'))
        if self.nb_plot == 0:
            self.send_log.emit(
                'Error: ' + self.tr('Selected variables and units not corresponding with figure type choices.'))
            return
        if self.nb_plot == 1 and self.total_fish_result > 32:
            self.send_log.emit('Warning: ' + self.tr(
                'You cannot display more than 32 habitat values per graph. Current selected : ') + str(
                self.total_fish_result) + self.tr(". Only the first 32 will be displayed."))
            # get 32 first element list
            # TODO : variables dict..
            variables = variables[:32]
        # check if number of display plot are > 30
        if export_type in ("interactive", "both") and self.nb_plot > 30:  # "interactive", "image export", "both
            qm = QMessageBox
            ret = qm.question(self, self.tr("Warning"),
                              self.tr("Displaying a large number of plots may crash HABBY. "
                                      "It is recommended not to exceed a total number of plots "
                                      "greater than 30 at a time. \n\nDo you still want to display ") + str(
                                  self.nb_plot) + self.tr(" figures ?"
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
            self.process_list.export_production_stoped = False

            # figure option
            project_preferences = load_project_properties(self.path_prj)
            project_preferences['type_plot'] = export_type  # "interactive", "image export", "both

            # init
            fish_names = [variable for variable in variables if variable not in self.variables_to_remove]

            # check plot process done
            if self.process_list.check_all_process_closed():
                self.process_list.new_plots()
            else:
                self.process_list.add_plots()

            # progress bar
            self.plot_progressbar.setValue(0)
            self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_plot))
            QCoreApplication.processEvents()

            # loop on all desired hdf5 file
            for name_hdf5 in names_hdf5:
                if not self.plot_production_stoped:  # stop loop with button
                    # create hdf5 class by file
                    hdf5 = hdf5_mod.Hdf5Management(self.path_prj, name_hdf5)
                    # variables_mesh = variables.copy()
                    # variables_node = variables.copy()
                    # # remove useless variables names for mesh
                    # variables_useless = ['mesh', 'substrate_coarser', 'substrate_dominant', 'elevation', "water_height",
                    #                      "water_velocity", "water_level", "froude_number",
                    #                      "hydraulic_head", "conveyance"]
                    # for variables_useless in variables_useless:
                    #     if variables_useless in variables_mesh:
                    #         variables_mesh.remove(variables_useless)
                    # # remove useless variables names for node
                    # variables_useless = ['mesh', 'substrate_coarser', 'substrate_dominant', 'elevation', "water_height",
                    #                      "water_velocity", 'max_slope_bottom', 'max_slope_energy', 'shear_stress']
                    # for variables_useless in variables_useless:
                    #     if variables_useless in variables_node:
                    #         variables_node.remove(variables_useless)
                    # load hydraulic data
                    if types_hdf5 == "hydraulic":
                        hdf5.load_hdf5_hyd(units_index=units_index)  #
                        # compute variables
                        self.hvum.get_original_computable_mesh_and_node_from_dict_gui(variables)
                        hdf5.compute_variables(mesh_variable_list=self.hvum.mesh_variable_computable_list,
                                               node_variable_list=self.hvum.node_variable_computable_list)
                        # data_description
                        data_description = dict(hdf5.data_description)
                        data_description["reach_list"] = hdf5.data_description["hyd_reach_list"].split(", ")
                        data_description["reach_number"] = hdf5.data_description["hyd_reach_number"]
                        data_description["unit_number"] = hdf5.data_description["hyd_unit_number"]
                        data_description["unit_type"] = hdf5.data_description["hyd_unit_type"]
                        data_description["units_index"] = units_index
                        data_description["name_hdf5"] = hdf5.data_description["hyd_filename"]
                    # load substrate data
                    if types_hdf5 == "substrate":
                        hdf5.load_hdf5_sub(convert_to_coarser_dom=True)
                        # data_description
                        data_description = dict(hdf5.data_description)
                        data_description["reach_list"] = hdf5.data_description["sub_reach_list"].split(", ")
                        data_description["reach_number"] = hdf5.data_description["sub_reach_number"]
                        data_description["unit_number"] = hdf5.data_description["sub_unit_number"]
                        data_description["unit_type"] = hdf5.data_description["sub_unit_type"]
                        data_description["name_hdf5"] = hdf5.data_description["sub_filename"]
                        data_description["sub_classification_code"] = hdf5.data_description["sub_classification_code"]
                    # load habitat data
                    if types_hdf5 == "habitat":
                        hdf5.load_hdf5_hab(units_index=units_index,
                                           fish_names=fish_names,
                                           whole_profil=False,
                                           convert_to_coarser_dom=True)
                        # remove list fish
                        for variables_fish in fish_names:
                            if variables_fish in variables_mesh:
                                variables_mesh.remove(variables_fish)
                            if variables_fish in variables_node:
                                variables_node.remove(variables_fish)
                        # compute variables
                        hdf5.compute_variables(mesh_variable_list=variables_mesh,
                                               node_variable_list=variables_node)
                        # data_description
                        data_description = dict(hdf5.data_description)
                        data_description["reach_list"] = hdf5.data_description["hyd_reach_list"].split(", ")
                        data_description["reach_number"] = hdf5.data_description["hyd_reach_number"]
                        data_description["unit_number"] = hdf5.data_description["hyd_unit_number"]
                        data_description["unit_type"] = hdf5.data_description["hyd_unit_type"]
                        data_description["units_index"] = units_index
                        data_description["name_hdf5"] = hdf5.data_description["hab_filename"]

                    # all cases
                    unit_type = data_description["unit_type"][
                                data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(
                                    ']')]

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
                                                                     project_preferences),
                                                               name="plot_fish_hv_wua")
                            self.process_list.append([plot_hab_fig_spu_process, state])

                        # for each desired units ==> maps
                        if plot_type != ["result"]:
                            for unit_num, t in enumerate(units_index):
                                # string_tr
                                string_tr = [self.tr("reach"), self.tr("unit")]



                                # # elevation
                                # if "elevation" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("elevation"),
                                #                                                "m",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     # plot_map_elevation
                                #     elevation_process = Process(target=plot_mod.plot_map_elevation,
                                #                            args=(
                                #                                state,
                                #                                hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                hdf5.data_2d["node"]["z"][reach_num][unit_num],
                                #                                plot_string_dict,
                                #                                data_description,
                                #                                project_preferences
                                #                            ),
                                #                            name="plot_map_elevation")
                                #     self.process_list.append([elevation_process, state])
                                #
                                # # water_height
                                # if "water_height" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("water_height"),
                                #                                                "m",
                                #                                                    string_tr)
                                #
                                #     state = Value("i", 0)
                                #     height_process = Process(target=plot_mod.plot_map_height,
                                #                              args=(
                                #                                  state,
                                #                                  hdf5.data_2d[reach_num][unit_num]["node"]["xy"],
                                #                                  hdf5.data_2d[reach_num][unit_num]["mesh"]["tin"],
                                #                                  hdf5.data_2d[reach_num][unit_num]["node"]["data"]["h"],
                                #                                  plot_string_dict,
                                #                                  data_description,
                                #                                  project_preferences
                                #                              ),
                                #                              name="plot_map_height")
                                #     self.process_list.append([height_process, state])
                                #
                                # # water_velocity
                                # if "water_velocity" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("water_velocity"),
                                #                                                "m/s",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     velocity_process = Process(target=plot_mod.plot_map_velocity,
                                #                                args=(
                                #                                    state,
                                #                                    hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                    hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                    hdf5.data_2d["node"]["data"]["v"][reach_num][unit_num],
                                #                                    plot_string_dict,
                                #                                    data_description,
                                #                                    project_preferences
                                #                                ),
                                #                                name="plot_map_velocity")
                                #     self.process_list.append([velocity_process, state])
                                #
                                # # conveyance
                                # if "conveyance" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("conveyance"),
                                #                                                "m²/s",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     conveyance_process = Process(target=plot_mod.plot_map_conveyance,
                                #                                  args=(
                                #                                      state,
                                #                                      hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                      hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                      hdf5.data_2d["node"]["data"]["conveyance"][
                                #                                          reach_num][unit_num],
                                #                                      plot_string_dict,
                                #                                      data_description,
                                #                                      project_preferences
                                #                                  ),
                                #                                  name="plot_map_conveyance")
                                #     self.process_list.append([conveyance_process, state])
                                #
                                # # froude_number
                                # if "froude_number" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("froude_number"),
                                #                                                "",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     froude_process = Process(target=plot_mod.plot_map_froude_number,
                                #                              args=(
                                #                                  state,
                                #                                  hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                  hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                  hdf5.data_2d["node"]["data"]["froude_number"][reach_num][
                                #                                      unit_num],
                                #                                  plot_string_dict,
                                #                                  data_description,
                                #                                  project_preferences
                                #                              ),
                                #                              name="plot_map_froude")
                                #     self.process_list.append([froude_process, state])
                                #
                                # # hydraulic_head
                                # if "hydraulic_head" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("hydraulic_head"),
                                #                                                "m",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     hydraulic_head_process = Process(target=plot_mod.plot_map_hydraulic_head,
                                #                                      args=(
                                #                                          state,
                                #                                          hdf5.data_2d["node"]["xy"][reach_num][
                                #                                              unit_num],
                                #                                          hdf5.data_2d["mesh"]["tin"][reach_num][
                                #                                              unit_num],
                                #                                          hdf5.data_2d["node"]["data"]["hydraulic_head"][
                                #                                              reach_num][unit_num],
                                #                                          plot_string_dict,
                                #                                          data_description,
                                #                                          project_preferences
                                #                                      ),
                                #                                      name="plot_map_hydraulic_head")
                                #     self.process_list.append([hydraulic_head_process, state])
                                #
                                # # water_level
                                # if "water_level" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("water_level"),
                                #                                                "m",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     water_level_process = Process(target=plot_mod.plot_map_water_level,
                                #                                   args=(
                                #                                       state,
                                #                                       hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                       hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                       hdf5.data_2d["node"]["data"]["water_level"][
                                #                                           reach_num][unit_num],
                                #                                       plot_string_dict,
                                #                                       data_description,
                                #                                       project_preferences
                                #                                   ),
                                #                                   name="plot_map_water_level")
                                #     self.process_list.append([water_level_process, state])
                                #
                                # # mesh
                                # if "mesh" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("mesh"),
                                #                                                "",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     mesh_process = Process(target=plot_mod.plot_map_mesh,
                                #                            args=(
                                #                                state,
                                #                                hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                plot_string_dict,
                                #                                data_description,
                                #                                project_preferences
                                #                            ),
                                #                            name="plot_map_mesh_and_point")
                                #     self.process_list.append([mesh_process, state])
                                #
                                # # max_slope_bottom
                                # if "max_slope_bottom" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("max_slope_bottom"),
                                #                                                "m/m",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     slope_bottom_process = Process(target=plot_mod.plot_map_slope_bottom,
                                #                                    args=(
                                #                                        state,
                                #                                        hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                        hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                        hdf5.data_2d["mesh"]["data"]["max_slope_bottom"][
                                #                                            reach_num][unit_num],
                                #                                        plot_string_dict,
                                #                                        data_description,
                                #                                        project_preferences
                                #                                    ),
                                #                                    name="plot_map_slope_bottom")
                                #     self.process_list.append([slope_bottom_process, state])
                                #
                                # # max_slope_energy
                                # if "max_slope_energy" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("max_slope_energy"),
                                #                                                "m/m",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     slope_bottom_process = Process(target=plot_mod.plot_map_slope_energy,
                                #                                    args=(
                                #                                        state,
                                #                                        hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                        hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                        hdf5.data_2d["mesh"]["data"]["max_slope_energy"][
                                #                                            reach_num][unit_num],
                                #                                        plot_string_dict,
                                #                                        data_description,
                                #                                        project_preferences
                                #
                                #                                    ),
                                #                                    name="plot_map_slope_energy")
                                #     self.process_list.append([slope_bottom_process, state])
                                #
                                # # shear_stress
                                # if "shear_stress" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("shear_stress"),
                                #                                                "",
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     slope_bottom_process = Process(target=plot_mod.plot_map_shear_stress,
                                #                                    args=(
                                #                                        state,
                                #                                        hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                        hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                        hdf5.data_2d["mesh"]["data"]["shear_stress"][
                                #                                            reach_num][unit_num],
                                #                                        plot_string_dict,
                                #                                        data_description,
                                #                                        project_preferences
                                #
                                #                                    ),
                                #                                    name="plot_map_shear_stress")
                                #     self.process_list.append([slope_bottom_process, state])
                                #
                                # # substrate_coarser
                                # if "substrate_coarser" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("substrate_coarser"),
                                #                                                    data_description["sub_classification_code"],
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     susbtrat_process = Process(target=plot_mod.plot_map_substrate_coarser,
                                #                                args=(
                                #                                    state,
                                #                                    hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                    hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                    hdf5.data_2d["mesh"]["data"]["sub"][reach_num][
                                #                                        unit_num],
                                #                                    plot_string_dict,
                                #                                    data_description,
                                #                                    project_preferences
                                #                                ),
                                #                                name="plot_substrate_coarser")
                                #     self.process_list.append([susbtrat_process, state])
                                #
                                # # substrate_dominant
                                # if "substrate_dominant" in variables and not self.plot_production_stoped:
                                #     plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                    reach_name,
                                #                                                    units[unit_num],
                                #                                                    unit_type,
                                #                                                    self.tr("substrate_dominant"),
                                #                                                    data_description["sub_classification_code"],
                                #                                                    string_tr)
                                #     state = Value("i", 0)
                                #     susbtrat_process = Process(target=plot_mod.plot_map_substrate_dominant,
                                #                                args=(
                                #                                    state,
                                #                                    hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                    hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                    hdf5.data_2d["mesh"]["data"]["sub"][reach_num][
                                #                                        unit_num],
                                #                                    plot_string_dict,
                                #                                    data_description,
                                #                                    project_preferences
                                #                                ),
                                #                                name="plot_substrate_dominant")
                                #     self.process_list.append([susbtrat_process, state])
                                #
                                # # fish map
                                # if fish_names and not self.plot_production_stoped:  # habitat data (maps)
                                #     # map by fish
                                #     for fish_index, fish_name in enumerate(fish_names):
                                #         plot_string_dict = create_map_plot_string_dict(data_description["name_hdf5"],
                                #                                                        reach_name,
                                #                                                        units[unit_num],
                                #                                                        unit_type,
                                #                                                        fish_name,
                                #                                                    "",
                                #                                                        string_tr,
                                #                                                        self.tr('HSI = ') + '{0:3.2f}'.format(data_description["total_HV_area"][fish_name][reach_num][unit_num]) + " / " + self.tr('unknown area') + " = " + '{0:3.2f}'.format(data_description["percent_area_unknown"][fish_name][reach_num][unit_num]) + " %")
                                #         state = Value("i", 0)
                                #         habitat_map_process = Process(target=plot_mod.plot_map_fish_habitat,
                                #                                       args=(
                                #                                           state,
                                #                                           hdf5.data_2d["node"]["xy"][reach_num][unit_num],
                                #                                           hdf5.data_2d["mesh"]["tin"][reach_num][unit_num],
                                #                                           hdf5.data_2d["mesh"]["hv_data"][fish_name][reach_num][unit_num],
                                #                                           plot_string_dict,
                                #                                           data_description,
                                #                                           project_preferences
                                #                                       ),
                                #                                       name="plot_map_fish_habitat")
                                #         self.process_list.append([habitat_map_process, state])

                            # GIF
                            if self.gif_export:
                                for variable in variables:
                                    # plot map
                                    state = Value("i", 0)
                                    gif_map_process = Process(target=plot_mod.create_gif_from_files,
                                                              args=(state,
                                                                    self.tr(variable),
                                                                    reach_name,
                                                                    units,
                                                                    data_description,
                                                                    project_preferences),
                                                              name="plot_gif")
                                    self.process_list.append([gif_map_process, state])

            # ajust total plot if add_plots
            self.nb_plot = len(self.process_list.process_list)
            # start thread
            self.process_list.start()
            # activate
            self.plot_button.setEnabled(False)
            # disable stop button
            self.plot_stop_button.setEnabled(True)

    def stop_plot(self):
        # stop plot production
        self.plot_production_stoped = True
        # activate
        self.plot_button.setEnabled(True)
        # disable stop button
        self.plot_stop_button.setEnabled(False)
        # close_all_export
        self.process_list.stop_plot_production()
        #self.process_list.terminate()
        # self.process_list.quit()
        # self.process_list.wait()
        # log
        self.send_log.emit(self.tr("Figure(s) production stoped by user."))


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
        self.process_list = MyProcessList("export")
        self.process_list.progress_signal.connect(self.show_prog)
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
        self.data_exporter_run_pushbutton.setEnabled(False)
        self.data_exporter_stop_pushbutton = QPushButton(self.tr("stop"))
        self.data_exporter_stop_pushbutton.clicked.connect(self.stop_export)
        self.data_exporter_stop_pushbutton.setEnabled(False)
        self.data_exporter_stop_pushbutton.setFixedWidth(110)
        self.data_exporter_stop_pushbutton.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_exporter_progressbar = QProgressBar()
        self.data_exporter_progressbar.setValue(0)
        self.data_exporter_progressbar.setTextVisible(False)
        self.data_exporter_progress_label = QLabel()
        self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))
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
        progress_layout.addWidget(self.data_exporter_progressbar)
        progress_layout.addWidget(self.data_exporter_progress_label)

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

    def change_export_layout(self, type):
        # nothing
        if type == 0:
            self.empty_export_widget.show()
            self.hyd_export_widget.hide()
            self.hab_export_widget.hide()
            self.checkbox_list = []
            self.current_type = 0
        # hyd
        if type == 1:
            self.empty_export_widget.hide()
            self.hyd_export_widget.show()
            self.hab_export_widget.hide()
            self.checkbox_list = self.hyd_checkbox_list
            self.current_type = 1
        # sub
        if type == 2:
            self.empty_export_widget.show()
            self.hyd_export_widget.hide()
            self.hab_export_widget.hide()
            self.checkbox_list = []
            self.current_type = 2
        # hab
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
                self.data_exporter_progressbar.setRange(0, self.nb_export)
                self.data_exporter_run_pushbutton.setEnabled(True)
            self.data_exporter_progressbar.setValue(0)
            self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_export))
        else:
            self.nb_export = 0
            self.data_exporter_run_pushbutton.setEnabled(False)
            # set prog
            self.data_exporter_progressbar.setValue(0)
            self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

    def show_prog(self, value):
        self.data_exporter_progressbar.setValue(value)
        self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(value, self.nb_export))

        if value == self.nb_export and self.nb_export != 0:  # != 0 if closefig of mainwindow
            # activate
            self.data_exporter_run_pushbutton.setEnabled(True)
            # disable stop button
            self.data_exporter_stop_pushbutton.setEnabled(False)
            # log
            self.send_log.emit(self.tr("Export(s) done."))

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
            self.export_production_stoped = False

            # figure option
            project_preferences = load_project_properties(self.path_prj)

            # export_production_stoped
            self.process_list.process_list = []
            self.process_list.export_production_stoped = False

            # disable
            self.data_exporter_run_pushbutton.setEnabled(False)

            # progress bar
            self.data_exporter_progressbar.setValue(0)
            self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_export))
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

                    # hydraulic
                    if types_hdf5 == "hydraulic":  # load hydraulic data
                        hdf5.load_hdf5_hyd(whole_profil=True)
                        hdf5.project_preferences = project_preferences
                        hdf5.get_variables_from_dict_and_compute()
                        total_gpkg_export = sum(
                            [export_dict["mesh_whole_profile_hyd"], export_dict["point_whole_profile_hyd"],
                             export_dict["mesh_units_hyd"], export_dict["point_units_hyd"]])
                        if export_dict["mesh_whole_profile_hyd"] or export_dict["point_whole_profile_hyd"] or \
                                export_dict["mesh_units_hyd"] or export_dict["point_units_hyd"]:
                            # append fake first
                            for fake_num in range(1, total_gpkg_export):
                                self.process_list.append([Process(name="fake" + str(fake_num)), Value("i", 1)])
                            state = Value("i", 0)
                            export_gpkg_process = Process(target=hdf5.export_gpkg,
                                                          args=(state,),
                                                          name="export_gpkg")
                            self.process_list.append([export_gpkg_process, state])

                        if export_dict["elevation_whole_profile_hyd"]:
                            state = Value("i", 0)
                            export_stl_process = Process(target=hdf5.export_stl,
                                                         args=(state,),
                                                         name="export_stl")
                            self.process_list.append([export_stl_process, state])
                        if export_dict["variables_units_hyd"]:
                            state = Value("i", 0)
                            export_paraview_process = Process(target=hdf5.export_paraview,
                                                              args=(state,),
                                                              name="export_paraview")
                            self.process_list.append([export_paraview_process, state])
                        if export_dict["detailled_text_hyd"]:
                            state = Value("i", 0)
                            export_detailled_mesh_txt_process = Process(target=hdf5.export_detailled_txt,
                                                                        args=(state,),
                                                                        name="export_detailled_txt")
                            self.process_list.append([export_detailled_mesh_txt_process, state])

                    # substrate
                    if types_hdf5 == "substrate":  # load substrate data
                        hdf5.load_hdf5_sub()

                    # habitat
                    if types_hdf5 == "habitat":  # load habitat data
                        hdf5.load_hdf5_hab(whole_profil=True)
                        hdf5.project_preferences = project_preferences
                        hdf5.get_variables_from_dict_and_compute()
                        total_gpkg_export = sum([export_dict["mesh_units_hab"], export_dict["point_units_hab"]])
                        if export_dict["mesh_units_hab"] or export_dict["point_units_hab"]:
                            # append fake first
                            for fake_num in range(1, total_gpkg_export):
                                self.process_list.append([Process(name="fake_gpkg" + str(fake_num)), Value("i", 1)])
                            state = Value("i", 0)
                            export_gpkg_process = Process(target=hdf5.export_gpkg,
                                                          args=(state,),
                                                          name="export_gpkg")
                            self.process_list.append([export_gpkg_process, state])
                        if export_dict["elevation_whole_profile_hab"]:
                            state = Value("i", 0)
                            export_stl_process = Process(target=hdf5.export_stl,
                                                         args=(state,),
                                                         name="export_stl")
                            self.process_list.append([export_stl_process, state])
                        if export_dict["variables_units_hab"]:
                            state = Value("i", 0)
                            export_paraview_process = Process(target=hdf5.export_paraview,
                                                              args=(state,),
                                                              name="export_paraview")
                            self.process_list.append([export_paraview_process, state])
                        if export_dict["habitat_text_hab"]:
                            state = Value("i", 0)
                            export_spu_txt_process = Process(target=hdf5.export_spu_txt,
                                                             args=(state,),
                                                             name="export_spu_txt")
                            self.process_list.append([export_spu_txt_process, state])
                        if export_dict["detailled_text_hab"]:
                            state = Value("i", 0)
                            export_detailled_mesh_txt_process = Process(target=hdf5.export_detailled_txt,
                                                                        args=(state,),
                                                                        name="export_detailled_txt")
                            self.process_list.append([export_detailled_mesh_txt_process, state])
                        if export_dict["fish_information_hab"]:
                            if hdf5.fish_list:
                                state = Value("i", 0)
                                export_pdf_process = Process(target=hdf5.export_export,
                                                             args=(state,),
                                                             name="export_export")
                                self.process_list.append([export_pdf_process, state])
                            else:
                                # append fake first
                                self.process_list.append([Process(name="fake_fish_information_hab"), Value("i", 1)])
                                self.send_log.emit('Warning: ' + self.tr(
                                    'No habitat data in this .hab file to export Fish informations report.'))

            # start thread
            self.process_list.start()
            # disable run_pushbutton
            self.data_exporter_run_pushbutton.setEnabled(False)
            # enable stop_pushbutton
            self.data_exporter_stop_pushbutton.setEnabled(True)

    def stop_export(self):
        # stop plot production
        self.export_production_stoped = True
        # activate
        self.data_exporter_run_pushbutton.setEnabled(True)
        # disable stop button
        self.data_exporter_stop_pushbutton.setEnabled(False)
        # close_all_export
        self.process_list.close_all_export()
        self.process_list.terminate()
        # self.process_list.quit()
        # self.process_list.wait()
        # log
        self.send_log.emit(self.tr("Export(s) stoped by user."))


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
        self.existing_animal_QListWidget.setObjectName("existing_animal_QListWidget")
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
            self.send_log.emit('Warning: ' + self.tr('No file selected.'))
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


class FileInformation(QGroupBoxCollapsible):
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
        # attributes hdf5
        self.hdf5_attributes_qtableview = QTableView(self)
        self.hdf5_attributes_qtableview.setFrameShape(QFrame.NoFrame)
        self.hdf5_attributes_qtableview.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.hdf5_attributes_qtableview.verticalHeader().setVisible(False)
        self.hdf5_attributes_qtableview.horizontalHeader().setVisible(False)

        # ATTRIBUTE GROUP
        attributes_layout = QVBoxLayout()
        attributes_layout.addWidget(self.hdf5_attributes_qtableview)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setLayout(attributes_layout)


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
