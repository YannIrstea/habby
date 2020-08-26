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
from multiprocessing import Value
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication, QVariant, QAbstractTableModel, QTimer
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QWidget, QAbstractItemView, QSpacerItem, \
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, QVBoxLayout, QHBoxLayout, QGridLayout, \
    QSizePolicy, QScrollArea, QTableView, QMenu, QAction, QProgressBar, QListWidgetItem, QRadioButton

from src import hdf5_mod
from src.hydraulic_process_mod import MyProcessList
from src.project_properties_mod import load_project_properties
from src.tools_mod import QHLine, DoubleClicOutputGroup
from src_GUI.tools_GUI import QGroupBoxCollapsible, change_button_color
from src.variable_unit_mod import HydraulicVariableUnitManagement


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
        self.tab_position = 4
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
        index = self.data_explorer_frame.get_type_index()

        if index:
            self.data_explorer_frame.types_hdf5_change()

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
        self.hdf5 = None
        self.file_to_remove_list = []
        self.init_ui()
        self.plot_production_stoped = False

    def init_ui(self):
        """ File selection """
        # hab_filenames_qcombobox
        self.types_hdf5_QLabel = QLabel(self.tr('file types'))
        # radiobutton
        self.hyd_radiobutton = QRadioButton(self.tr("hydraulic"))
        self.hyd_radiobutton.clicked.connect(self.types_hdf5_change)
        self.sub_radiobutton = QRadioButton(self.tr("substrate"))
        self.sub_radiobutton.clicked.connect(self.types_hdf5_change)
        self.hab_radiobutton = QRadioButton(self.tr("habitat"))
        self.hab_radiobutton.clicked.connect(self.types_hdf5_change)

        self.names_hdf5_QLabel = QLabel(self.tr('filenames'))
        self.names_hdf5_QListWidget = QListWidget()
        self.names_hdf5_QListWidget.resizeEvent = self.resize_names_hdf5_qlistwidget
        self.names_hdf5_QListWidget.setObjectName("names_hdf5_QListWidget")
        self.names_hdf5_QListWidget.setFixedHeight(100)
        # self.names_hdf5_QListWidget.setMaximumHeight(100)
        self.names_hdf5_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.names_hdf5_QListWidget.itemSelectionChanged.connect(self.names_hdf5_change)
        self.names_hdf5_QListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.names_hdf5_QListWidget.customContextMenuRequested.connect(self.show_menu_hdf5_remover)

        """ types_hdf5_layout """
        self.types_hdf5_layout = QVBoxLayout()
        self.types_hdf5_layout.setAlignment(Qt.AlignTop)
        self.types_hdf5_layout.addWidget(self.types_hdf5_QLabel)
        self.types_hdf5_layout.addWidget(self.hyd_radiobutton)
        self.types_hdf5_layout.addWidget(self.sub_radiobutton)
        self.types_hdf5_layout.addWidget(self.hab_radiobutton)

        """ names_hdf5_layout """
        self.names_hdf5_layout = QVBoxLayout()
        self.names_hdf5_layout.setAlignment(Qt.AlignTop)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QLabel)
        self.names_hdf5_layout.addWidget(self.names_hdf5_QListWidget)

        """ plot_group """
        self.plot_group = FigureProducerGroup(self.path_prj, self.name_prj, self.send_log,
                                              self.tr("Figure viewer/exporter"))
        self.plot_group.hdf5 = self.hdf5
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

    def resize_names_hdf5_qlistwidget(self, _):
        """
        with qdarkstyle,  names_hdf5_QListWidget height is reduced. GUI improved.
        """
        self.names_hdf5_QListWidget.setFixedHeight(100)

    def get_type_index(self):
        index = 0
        if self.hyd_radiobutton.isChecked():
            index = 1
        elif self.sub_radiobutton.isChecked():
            index = 2
        elif self.hab_radiobutton.isChecked():
            index = 3
        return index

    def types_hdf5_change(self):
        """
        Ajust item list according to hdf5 type selected by user
        """
        index = self.get_type_index()
        self.names_hdf5_QListWidget.clear()

        if index == 0:
            self.set_empty_layout()

        # hydraulic
        elif index == 1:
            names = hdf5_mod.get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                if len(names) == 1:
                    self.names_hdf5_QListWidget.selectAll()

        # substrate
        elif index == 2:
            names = hdf5_mod.get_filename_by_type_physic("substrate", os.path.join(self.path_prj, "hdf5"))
            if names:
                # change list widget
                self.names_hdf5_QListWidget.addItems(names)
                if len(names) == 1:
                    self.names_hdf5_QListWidget.selectAll()

        # habitat
        elif index == 3:
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
        self.plot_group.mesh_variable_QListWidget.clear()
        self.plot_group.node_variable_QListWidget.clear()
        self.plot_group.units_QListWidget.clear()
        self.plot_group.reach_QListWidget.clear()
        self.plot_group.units_QLabel.setText(self.tr("unit(s)"))
        self.habitatvalueremover_group.existing_animal_QListWidget.clear()

        if len(selection) >= 1:
            reach_list = []
            unit_list = []
            variable_node_list = []
            variable_mesh_list = []
            for selection_el in selection:
                # read
                hdf5name = selection_el.text()
                self.hdf5 = hdf5_mod.Hdf5Management(self.path_prj,
                                               hdf5name,
                                               new=False)
                self.hdf5.get_hdf5_attributes(close_file=True)
                self.plot_group.hdf5 = self.hdf5
                # check reach
                reach_list.append(self.hdf5.data_2d.reach_list)
                # check unit
                unit_list.append(self.hdf5.data_2d.unit_list)
                # check variable_node
                variable_node_list.append(self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs().names())
                # check variable_mesh
                variable_mesh_list.append(self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes().names())

            if not reach_list.count(reach_list[0]) == len(reach_list) and \
                    not unit_list.count(unit_list[0]) == len(unit_list) and \
                    not variable_node_list.count(variable_node_list[0]) == len(variable_node_list) and \
                    not variable_mesh_list.count(variable_mesh_list[0]) == len(variable_mesh_list):
                self.set_empty_layout()
            else:
                self.plot_group.units_QListWidget.clear()

                # change unit_type
                if hasattr(self.hdf5.data_2d, "unit_type"):
                    self.hdf5.data_2d.unit_type = self.hdf5.data_2d.unit_type.replace("m3/s", "m<sup>3</sup>/s")
                    self.plot_group.units_QLabel.setText(self.hdf5.data_2d.unit_type)

                # get_type_index
                index_type = self.get_type_index()

                # hydraulic
                if index_type == 1:
                    self.set_hydraulic_layout()
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs().names_gui():
                        for mesh in self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs():
                            mesh_item = QListWidgetItem(mesh.name_gui, self.plot_group.mesh_variable_QListWidget)
                            mesh_item.setData(Qt.UserRole, mesh)
                            if not mesh.hdf5:
                                mesh_item.setText(mesh_item.text() + " *")
                                mesh_item.setToolTip("computable")
                            self.plot_group.mesh_variable_QListWidget.addItem(mesh_item)
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes().names_gui():
                        for node in self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes():
                            node_item = QListWidgetItem(node.name_gui, self.plot_group.node_variable_QListWidget)
                            node_item.setData(Qt.UserRole, node)
                            if not node.hdf5:
                                node_item.setText(node_item.text() + " *")
                                node_item.setToolTip("computable")
                            self.plot_group.node_variable_QListWidget.addItem(node_item)

                    if self.hdf5.data_2d.reach_list:
                        self.plot_group.reach_QListWidget.addItems(self.hdf5.data_2d.reach_list)
                        if len(self.hdf5.data_2d.reach_list) == 1:
                            self.plot_group.reach_QListWidget.selectAll()
                            if self.hdf5.data_2d.unit_list == 1:
                                self.plot_group.units_QListWidget.selectAll()
                            else:
                                self.plot_group.units_QListWidget.setCurrentRow(0)

                # substrat
                if index_type == 2:
                    self.set_substrate_layout()
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs().names_gui():
                        for mesh in self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs():
                            mesh_item = QListWidgetItem(mesh.name_gui, self.plot_group.mesh_variable_QListWidget)
                            mesh_item.setData(Qt.UserRole, mesh)
                            if not mesh.hdf5:
                                mesh_item.setText(mesh_item.text() + " *")
                                mesh_item.setToolTip("computable")
                            self.plot_group.mesh_variable_QListWidget.addItem(mesh_item)
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes().names_gui():
                        for node in self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes():
                            node_item = QListWidgetItem(node.name_gui, self.plot_group.node_variable_QListWidget)
                            node_item.setData(Qt.UserRole, node)
                            if not node.hdf5:
                                node_item.setText(node_item.text() + " *")
                                node_item.setToolTip("computable")
                            self.plot_group.node_variable_QListWidget.addItem(node_item)

                    if self.hdf5.data_2d.sub_mapping_method != "constant":
                        if self.hdf5.data_2d.reach_list:
                            self.plot_group.reach_QListWidget.addItems(self.hdf5.data_2d.reach_list)
                            if len(self.hdf5.data_2d.reach_list) == 1:
                                self.plot_group.reach_QListWidget.selectAll()
                                if self.hdf5.data_2d.unit_list == 1:
                                    self.plot_group.units_QListWidget.selectAll()
                                else:
                                    self.plot_group.units_QListWidget.setCurrentRow(0)

                # habitat
                if index_type == 3:
                    self.set_habitat_layout()
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs().names_gui():
                        for mesh in self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs():
                            mesh_item = QListWidgetItem(mesh.name_gui, self.plot_group.mesh_variable_QListWidget)
                            mesh_item.setData(Qt.UserRole, mesh)
                            if not mesh.hdf5:
                                mesh_item.setText(mesh_item.text() + " *")
                                mesh_item.setToolTip("computable")
                            self.plot_group.mesh_variable_QListWidget.addItem(mesh_item)
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes().names_gui():
                        for node in self.hdf5.data_2d.hvum.hdf5_and_computable_list.nodes():
                            node_item = QListWidgetItem(node.name_gui, self.plot_group.node_variable_QListWidget)
                            node_item.setData(Qt.UserRole, node)
                            if not node.hdf5:
                                node_item.setText(node_item.text() + " *")
                                node_item.setToolTip("computable")
                            self.plot_group.node_variable_QListWidget.addItem(node_item)

                    # habitatvalueremover_group
                    if self.hdf5.data_2d.hvum.hdf5_and_computable_list.meshs().habs().names_gui():
                        for mesh in self.hdf5.data_2d.hvum.hdf5_and_computable_list.habs().meshs():
                            mesh_item = QListWidgetItem(mesh.name_gui, self.habitatvalueremover_group.existing_animal_QListWidget)
                            mesh_item.setData(Qt.UserRole, mesh)
                            if not mesh.hdf5:
                                mesh_item.setText(mesh_item.text() + " *")
                                mesh_item.setToolTip("computable")
                            self.habitatvalueremover_group.existing_animal_QListWidget.addItem(mesh_item)

                    if self.hdf5.data_2d.reach_list:
                        self.plot_group.reach_QListWidget.addItems(self.hdf5.data_2d.reach_list)
                        if len(self.hdf5.data_2d.reach_list) == 1:
                            self.plot_group.reach_QListWidget.selectAll()
                            if self.hdf5.data_2d.unit_list == 1:
                                self.plot_group.units_QListWidget.selectAll()
                            else:
                                self.plot_group.units_QListWidget.setCurrentRow(0)

            # display hdf5 attributes
            tablemodel = MyTableModel(list(zip(self.hdf5.hdf5_attributes_name_text, self.hdf5.hdf5_attributes_info_text)), self)
            self.file_information_group.hdf5_attributes_qtableview.setModel(tablemodel)
            header = self.file_information_group.hdf5_attributes_qtableview.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.file_information_group.hdf5_attributes_qtableview.verticalHeader().setDefaultSectionSize(
                self.file_information_group.hdf5_attributes_qtableview.verticalHeader().minimumSectionSize())

            # resize qtableview
            height = self.file_information_group.hdf5_attributes_qtableview.rowHeight(1) * (len(self.hdf5.hdf5_attributes_name_text) + 1)
            self.file_information_group.hdf5_attributes_qtableview.setFixedHeight(height)
            self.file_information_group.toggle_group(self.file_information_group.isChecked())

        elif len(selection) == 0:
            self.set_empty_layout()

        # count plot
        self.plot_group.count_plot()
        # count exports
        self.dataexporter_group.count_export()

    def set_empty_layout(self):
        self.plot_group.mesh_variable_QListWidget.clear()
        self.plot_group.units_QListWidget.clear()
        self.plot_group.hide()
        self.dataexporter_group.change_export_layout(0)
        self.dataexporter_group.hide()
        self.habitatvalueremover_group.hide()
        self.file_information_group.hide()

    def set_hydraulic_layout(self):
        self.plot_group.mesh_variable_QListWidget.clear()
        self.plot_group.plot_result_QCheckBox.hide()
        self.dataexporter_group.change_export_layout(1)
        self.plot_group.show()
        self.dataexporter_group.show()
        self.habitatvalueremover_group.hide()
        self.file_information_group.show()

    def set_substrate_layout(self):
        self.plot_group.node_variable_QListWidget.clear()
        self.plot_group.mesh_variable_QListWidget.clear()
        self.plot_group.plot_result_QCheckBox.hide()
        self.dataexporter_group.change_export_layout(2)
        self.plot_group.show()
        self.dataexporter_group.hide()
        self.habitatvalueremover_group.hide()
        self.file_information_group.show()

    def set_habitat_layout(self):
        self.plot_group.node_variable_QListWidget.clear()
        self.plot_group.mesh_variable_QListWidget.clear()
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
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_prog)
        # self.process_list.progress_signal.connect(self.show_prog)
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
        """ original and computable data """
        self.mesh_variable_QLabel = QLabel(self.tr('mesh variables'))
        self.mesh_variable_QListWidget = QListWidget()
        self.mesh_variable_QListWidget.setObjectName("mesh_variable_QListWidget")
        # self.mesh_variable_QListWidget.setMinimumWidth(listwidgets_width)
        # self.mesh_variable_QListWidget.setMaximumHeight(listwidgets_height)
        self.mesh_variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.mesh_variable_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.node_variable_QLabel = QLabel(self.tr('node variables'))
        self.node_variable_QListWidget = QListWidget()
        self.node_variable_QListWidget.setObjectName("node_variable_QListWidget")
        # self.node_variable_QListWidget.setMinimumWidth(listwidgets_width)
        # self.node_variable_QListWidget.setMaximumHeight(listwidgets_height)
        self.node_variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.node_variable_QListWidget.itemSelectionChanged.connect(self.count_plot)

        self.variable_hdf5_layout = QGridLayout()
        self.variable_hdf5_layout.addWidget(self.node_variable_QLabel, 0, 0)
        self.variable_hdf5_layout.addWidget(self.node_variable_QListWidget, 1, 0)
        self.variable_hdf5_layout.addWidget(self.mesh_variable_QLabel, 0, 1)
        self.variable_hdf5_layout.addWidget(self.mesh_variable_QListWidget, 1, 1)

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
        self.export_type_QLabel = QLabel(self.tr('View or export :'))
        self.export_type_QComboBox = QComboBox()
        self.export_type_QComboBox.addItems(["interactive", "image export", "both"])
        self.export_type_QComboBox.currentIndexChanged.connect(self.count_plot)
        self.export_type_layout = QVBoxLayout()
        self.export_type_layout.setAlignment(Qt.AlignTop)
        # self.export_type_layout.addWidget(self.export_type_QLabel)
        # self.export_type_layout.addWidget(self.export_type_QComboBox)

        # progress
        self.plot_progressbar = QProgressBar()
        self.plot_progressbar.setValue(0)
        self.plot_progressbar.setTextVisible(False)
        self.plot_progress_label = QLabel()
        self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

        # buttons plot_button
        self.plot_button = QPushButton(self.tr("run"))
        change_button_color(self.plot_button, "#47B5E6")
        self.plot_button.clicked.connect(self.collect_data_from_gui_and_plot)
        self.plot_button.setEnabled(False)

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
        # plot_type_layout.addWidget(self.plot_3d_QCheckBox)
        plot_type_layout.addWidget(self.plot_result_QCheckBox)
        plot_type_layout.addWidget(self.export_type_QLabel)
        plot_type_layout.addWidget(self.export_type_QComboBox)
        plot_type_layout.setAlignment(Qt.AlignLeft)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.plot_progressbar)
        progress_layout.addWidget(self.plot_progress_label)
        progress_layout.addWidget(self.plot_button)
        plot_layout2.addLayout(plot_layout)
        plot_layout2.addLayout(plot_type_layout)
        plot_layout2.addLayout(progress_layout)
        self.setLayout(plot_layout2)

    def count_plot(self):
        """
        count number of graphic to produce and ajust progress bar range
        """
        types_hdf5, names_hdf5, plot_attr = self.collect_data_from_gui()

        reach = plot_attr.reach
        units = plot_attr.units
        export_type = plot_attr.export_type

        plot_type = []
        if self.plot_map_QCheckBox.isChecked():
            plot_type = ["map"]
        if self.plot_result_QCheckBox.isChecked():
            plot_type = ["result"]
        if self.plot_map_QCheckBox.isChecked() and self.plot_result_QCheckBox.isChecked():
            plot_type = ["map", "result"]

        if types_hdf5 and names_hdf5 and self.hvum.user_target_list and reach and units and plot_type:
            # total_variables_number
            total_variables_number = self.hvum.user_target_list.no_habs().__len__()
            # is fish ?
            total_habitat_variable_number = self.hvum.user_target_list.habs().__len__()
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
                    self.nb_plot = len(names_hdf5) * total_variables_number * len(reach) * len(units)
                    if self.gif_export and self.nb_plot > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)
                if plot_type == ["map", "result"]:
                    self.nb_plot = len(names_hdf5) * total_variables_number * len(reach) * len(units)
                    if self.gif_export and self.nb_plot > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)

            # one fish
            if total_habitat_variable_number == 1:
                if plot_type == ["result"]:
                    nb_map = 0
                else:
                    # one map by fish by unit
                    nb_map = len(names_hdf5) * total_habitat_variable_number * len(reach) * len(units)
                    if self.gif_export and nb_map > 1:
                        nb_map = nb_map + total_habitat_variable_number * len(reach) + total_variables_number * len(reach)
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
                self.nb_plot = (len(names_hdf5) * total_variables_number * len(reach) * len(units)) + nb_map + nb_wua_hv

            # multi fish
            if total_habitat_variable_number > 1:
                if plot_type == ["result"]:
                    self.nb_plot = 1
                    self.total_fish_result = total_habitat_variable_number
                if plot_type == ["map"]:
                    # one map by fish by unit
                    nb_map = total_habitat_variable_number * len(reach) * len(units)
                    if self.gif_export and nb_map > 1:
                        nb_map = nb_map + total_habitat_variable_number * len(reach)
                    self.nb_plot = (len(names_hdf5) * total_variables_number * len(reach) * len(units)) + nb_map
                    if self.gif_export and nb_map > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)
                if plot_type == ["map", "result"]:
                    # one map by fish by unit
                    nb_map = total_habitat_variable_number * len(reach) * len(units)
                    if self.gif_export and nb_map > 1:
                        nb_map = nb_map + total_habitat_variable_number * len(reach)
                    self.nb_plot = (len(names_hdf5) * total_variables_number * len(reach) * len(units)) + nb_map + 1
                    if self.gif_export and nb_map > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)
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

    def collect_data_from_gui(self):
        """
        Get selected values by user
        """
        # init
        self.hvum = HydraulicVariableUnitManagement()

        # types
        types_hdf5 = self.parent().get_type_index()

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
        if self.node_variable_QListWidget.selectedIndexes().__len__() > 0:
            for selection in self.node_variable_QListWidget.selectedItems():
                self.hvum.user_target_list.append(selection.data(Qt.UserRole))
        if self.mesh_variable_QListWidget.selectedIndexes().__len__() > 0:
            for selection in self.mesh_variable_QListWidget.selectedItems():
                self.hvum.user_target_list.append(selection.data(Qt.UserRole))

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

        plot_attr = lambda: None
        plot_attr.reach = reach
        plot_attr.units = units
        plot_attr.units_index = units_index
        plot_attr.export_type = export_type
        plot_attr.plot_type = plot_type

        # store values
        return types_hdf5, names_hdf5, plot_attr

    def collect_data_from_gui_and_plot(self):
        """
        Get selected values by user and plot them
        """
        if not self.plot_button.isChecked():
            self.plot_figure(*self.collect_data_from_gui())
        else:
            self.stop_plot()

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

            # # create hdf5 class
            # hdf5 = hdf5_mod.Hdf5Management(self.path_prj,
            #                                hdf5name,
            #                                new=False)
            # hdf5.get_hdf5_attributes()

            # add units
            for item_text in self.hdf5.data_2d.unit_list[self.reach_QListWidget.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget.addItem(item)

        # more than one file selected
        elif len(selection_reach) > 1:
            # # clear attributes hdf5_attributes_qtableview
            # hdf5 = hdf5_mod.Hdf5Management(self.path_prj,
            #                                selection_file[0].text(),
            #                                new=False)
            # hdf5.get_hdf5_attributes()
            # check if units are equal between reachs
            units_equal = True
            for reach_number in range(len(self.hdf5.data_2d.unit_list) - 1):
                if self.hdf5.data_2d.unit_list[reach_number] != self.hdf5.data_2d.unit_list[reach_number + 1]:
                    units_equal = False
            if units_equal:  # homogene units between reach
                # self.units_QListWidget.addItems()
                for item_text in self.hdf5.data_2d.unit_list[0]:
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

    def plot_figure(self, types_hdf5, names_hdf5, plot_attr):
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
        if not self.hvum.user_target_list:
            self.send_log.emit('Error: ' + self.tr('No variable selected.'))
        if not plot_attr.reach:
            self.send_log.emit('Error: ' + self.tr('No reach selected.'))
        if not plot_attr.units:
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
            self.hvum.user_target_list = self.hvum.user_target_list[:32]
        # check if number of display plot are > 30
        if plot_attr.export_type in ("interactive", "both") and self.nb_plot > 30:  # "interactive", "image export", "both
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
        if types_hdf5 and names_hdf5 and self.hvum.user_target_list and plot_attr.reach and plot_attr.units and plot_attr.plot_type:
            # disable
            self.plot_button.setText("stop")

            # active stop button
            self.plot_production_stoped = False
            self.process_list.export_production_stoped = False

            # figure option
            project_preferences = load_project_properties(self.path_prj)
            project_preferences['type_plot'] = plot_attr.export_type  # "interactive", "image export", "both

            plot_attr.hvum = self.hvum
            plot_attr.plot_map_QCheckBoxisChecked = self.plot_map_QCheckBox.isChecked()

            # check plot process done
            if self.process_list.check_all_process_closed():
                self.process_list.new_plots()
                self.process_list.nb_plot_total = self.nb_plot
            else:
                self.process_list.add_plots(self.nb_plot)

            # loop on all desired hdf5 file
            if not self.plot_production_stoped:  # stop loop with button
                self.process_list.set_plot_hdf5_mode(self.path_prj, names_hdf5, plot_attr, project_preferences)
                # start thread
                self.process_list.start()

            # progress bar
            self.plot_progressbar.setRange(0, self.process_list.nb_plot_total)
            self.plot_progressbar.setValue(self.process_list.nb_finished)
            self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.process_list.nb_plot_total))
            QCoreApplication.processEvents()

            # for error management and figures
            self.timer.start(100)

    def stop_plot(self):
        # stop plot production
        self.plot_production_stoped = True
        # activate
        self.plot_button.setText(self.tr("run"))
        # self.plot_button.setChecked(True)
        # disable stop button
        # self.plot_stop_button.setEnabled(False)
        # close_all_export
        self.process_list.stop_plot_production()
        #self.process_list.terminate()
        # self.process_list.quit()
        # self.process_list.wait()
        # log
        self.send_log.emit(self.tr("Figure(s) production stoped by user."))

    def show_prog(self):
        # RUNNING
        if not self.process_list.plot_finished:
            # self.process_list.nb_finished
            self.plot_progressbar.setValue(int(self.process_list.nb_finished))
            self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(self.process_list.nb_finished,
                                                                      self.process_list.nb_plot_total))
        else:
            self.plot_progressbar.setValue(int(self.process_list.nb_finished))
            self.plot_progress_label.setText("{0:.0f}/{1:.0f}".format(self.process_list.nb_finished,
                                                                      self.process_list.nb_plot_total))
            self.timer.stop()
            # activate
            self.plot_button.setText(self.tr("run"))
            self.plot_button.setChecked(True)
            if not self.plot_production_stoped:
                # log
                self.send_log.emit(self.tr("Figure(s) done."))


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
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_prog)
        self.progress_value = Value("i", 0)
        self.export_production_stoped = False
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
        change_button_color(self.data_exporter_run_pushbutton, "#47B5E6")
        self.data_exporter_run_pushbutton.clicked.connect(self.start_stop_export)
        self.data_exporter_run_pushbutton.setEnabled(False)

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
        self.hyd_export_layout.setColumnStretch(0, 3)
        self.hyd_export_layout.setColumnStretch(1, 3)
        self.hyd_export_layout.setColumnStretch(2, 1)
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
        self.hab_export_layout.setColumnStretch(0, 3)
        self.hab_export_layout.setColumnStretch(1, 3)
        self.hab_export_layout.setColumnStretch(2, 1)
        # hab_export_widget
        self.hab_export_widget = QWidget()
        self.hab_export_widget.hide()
        self.hab_export_widget.setLayout(self.hab_export_layout)

        """ progress layout """
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.data_exporter_progressbar)
        progress_layout.addWidget(self.data_exporter_progress_label)
        progress_layout.addWidget(self.data_exporter_run_pushbutton)

        """ data_exporter layout """
        self.data_exporter_layout = QVBoxLayout()
        self.data_exporter_layout.addWidget(self.empty_export_widget)
        self.data_exporter_layout.addWidget(self.hyd_export_widget)
        self.data_exporter_layout.addWidget(self.hab_export_widget)
        self.data_exporter_layout.addLayout(progress_layout)
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
        types_hdf5 = self.parent().get_type_index()

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

    def start_stop_export(self):
        if self.data_exporter_run_pushbutton.text() == self.tr("run"):
            self.start_export()
        elif self.data_exporter_run_pushbutton.text() == self.tr("stop"):
            self.stop_export()

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

            # switch to stop
            self.data_exporter_run_pushbutton.setText(self.tr("stop"))
            self.process_list = MyProcessList("export")

            # loop on all desired hdf5 file
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

                export_dict["nb_export"] = self.nb_export

                self.process_list.set_export_hdf5_mode(self.path_prj, names_hdf5, export_dict, project_preferences)
                # start thread
                self.process_list.start()

                # for error management and figures
                self.timer.start(100)

    def stop_export(self):
        # stop plot production
        self.export_production_stoped = True
        # activate
        self.data_exporter_run_pushbutton.setText(self.tr("run"))
        # close_all_export
        self.process_list.close_all_export()
        self.process_list.terminate()
        self.timer.stop()
        self.count_export()
        # log
        self.send_log.emit(self.tr("Export(s) stoped by user."))

    def show_prog(self):
        # RUNNING
        if not self.process_list.export_finished:
            # self.process_list.nb_finished
            self.data_exporter_progressbar.setValue(int(self.process_list.nb_finished))
            self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(self.process_list.nb_finished,
                                                                               self.process_list.nb_export_total))
        # NOT RUNNING
        else:
            self.timer.stop()
            self.data_exporter_progressbar.setValue(int(self.process_list.nb_finished))
            self.data_exporter_progress_label.setText("{0:.0f}/{1:.0f}".format(self.process_list.nb_finished,
                                                                               self.process_list.nb_export_total))
            self.data_exporter_run_pushbutton.setText(self.tr("run"))
            self.data_exporter_run_pushbutton.setChecked(True)
            # FINISHED
            if not self.export_production_stoped:
                # log
                self.send_log.emit(self.tr("Export(s) done."))


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
        hab_variable_list = []
        for selection in self.existing_animal_QListWidget.selectedItems():
            hab_variable_list.append(selection.data(Qt.UserRole).name)

        # remove
        # hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
        # hdf5.create_or_open_file(False)
        self.hdf5.remove_fish_hab(hab_variable_list)

        # refresh
        self.parent().names_hdf5_change()
        self.parent().send_log.emit(", ".join(hab_variable_list) + " data has been removed in .hab file.")


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
