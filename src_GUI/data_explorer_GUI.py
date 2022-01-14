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
import sys
from multiprocessing import cpu_count
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QWidget, QAbstractItemView, \
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, QVBoxLayout, QHBoxLayout, QGridLayout, \
    QSizePolicy, QScrollArea, QTableView, QMenu, QAction, QListWidgetItem, QRadioButton

from src.hdf5_mod import get_filename_by_type_physic, Hdf5Management
from src.project_properties_mod import load_project_properties, load_specific_properties
from src_GUI.dev_tools_GUI import MyTableModel, QGroupBoxCollapsible, QHLine, DoubleClicOutputGroup
from src_GUI.process_manager_GUI import ProcessProgLayout
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
        else:
            # hydraulic
            if index == 1:
                type_name = "hydraulic"
            # substrate
            elif index == 2:
                type_name = "substrate"
            # habitat
            elif index == 3:
                type_name = "habitat"

            names = get_filename_by_type_physic(type_name, os.path.join(self.path_prj, "hdf5"))
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
                self.hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
                self.hdf5.get_hdf5_attributes(close_file=True)
                self.plot_group.hdf5 = self.hdf5
                self.habitatvalueremover_group.hdf5 = self.hdf5
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
                # substrat
                if index_type == 2:
                    self.set_substrate_layout()
                # habitat
                if index_type == 3:
                    self.set_habitat_layout()

                # reach and units
                show_tf = True
                if self.hdf5.hdf5_type == "substrate":
                    if self.hdf5.data_2d.sub_mapping_method == "constant":
                        show_tf = False

                if show_tf:
                    if self.hdf5.data_2d.reach_list:
                        self.plot_group.reach_QListWidget.addItems(self.hdf5.data_2d.reach_list)
                        if len(self.hdf5.data_2d.reach_list) == 1:
                            self.plot_group.reach_QListWidget.selectAll()
                            if self.hdf5.data_2d.unit_list == 1:
                                self.plot_group.units_QListWidget.selectAll()
                            else:
                                self.plot_group.units_QListWidget.setCurrentRow(0)

                # variables
                for variable in self.hdf5.data_2d.hvum.hdf5_and_computable_list:
                    if variable.position == "mesh":
                        list_widget_position = self.plot_group.mesh_variable_QListWidget
                    elif variable.position == "node":
                        list_widget_position = self.plot_group.node_variable_QListWidget
                    variable_item = QListWidgetItem(variable.name_gui, list_widget_position)
                    variable_item.setData(Qt.UserRole, variable)
                    # tooltip
                    if not variable.hdf5:
                        variable_item.setText(variable_item.text() + " *")
                        variable_item.setToolTip(
                            variable.name_gui + "\n" +
                            "exist in file : no \n" +
                            "position : " + variable.position + "\n" +
                            "unit : " + variable.unit + "\n" +
                            "description : " + variable.descr
                                                 )
                    else:
                        variable_item.setToolTip(
                             variable.name_gui + "\n" +
                             "exist in file : yes" + "\n" +
                             "position : " + variable.position + "\n" +
                             "unit : " + variable.unit + "\n" +
                             "description : " + variable.descr
                        )
                    if variable.position == "mesh":
                        self.plot_group.mesh_variable_QListWidget.addItem(variable_item)
                    elif variable.position == "node":
                        self.plot_group.node_variable_QListWidget.addItem(variable_item)
                    # remover add to existing_animal_QListWidget
                    if variable.habitat:
                        # copy
                        variable_item2 = QListWidgetItem(variable_item)
                        # change associated listwidget
                        variable_item2.listWidget = self.habitatvalueremover_group.existing_animal_QListWidget
                        self.habitatvalueremover_group.existing_animal_QListWidget.addItem(variable_item2)

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
        self.hvum = HydraulicVariableUnitManagement()
        self.gif_export = False
        self.nb_plot = 0
        self.nb_plot_max = cpu_count()
        self.init_ui()

    def init_ui(self):
        qlistwidget_height = 100
        """ original and computable data """
        self.mesh_variable_QLabel = QLabel(self.tr('mesh variables'))
        self.mesh_variable_QListWidget = QListWidget()
        self.mesh_variable_QListWidget.setMaximumHeight(qlistwidget_height)
        self.mesh_variable_QListWidget.setObjectName("mesh_variable_QListWidget")
        self.mesh_variable_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.mesh_variable_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.node_variable_QLabel = QLabel(self.tr('node variables'))
        self.node_variable_QListWidget = QListWidget()
        self.node_variable_QListWidget.setMaximumHeight(qlistwidget_height)
        self.node_variable_QListWidget.setObjectName("node_variable_QListWidget")
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
        self.reach_QListWidget.setMaximumHeight(qlistwidget_height)
        self.reach_QListWidget.setObjectName("reach_QListWidget")
        self.reach_QListWidget.setMinimumWidth(110)
        self.reach_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.reach_QListWidget.itemSelectionChanged.connect(self.reach_hdf5_change)
        self.reach_hdf5_layout = QVBoxLayout()
        self.reach_hdf5_layout.setAlignment(Qt.AlignTop)
        self.reach_hdf5_layout.addWidget(self.reach_hdf5_QLabel)
        self.reach_hdf5_layout.addWidget(self.reach_QListWidget)

        # units_QListWidget
        self.units_QLabel = QLabel(self.tr('unit(s)'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setMaximumHeight(qlistwidget_height)
        self.units_QListWidget.setObjectName("units_QListWidget")
        self.units_QListWidget.setMinimumWidth(50)
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.itemSelectionChanged.connect(self.count_plot)
        self.units_layout = QVBoxLayout()
        self.units_layout.setAlignment(Qt.AlignTop)
        self.units_layout.addWidget(self.units_QLabel)
        self.units_layout.addWidget(self.units_QListWidget)

        # export_type_QComboBox
        self.export_type_QLabel = QLabel(self.tr('mode'))
        self.export_type_QComboBox = QComboBox()
        self.export_type_QComboBox.addItems(["interactive", "image export", "both"])
        self.export_type_QComboBox.currentIndexChanged.connect(self.count_plot)
        self.export_type_layout = QVBoxLayout()
        self.export_type_layout.setAlignment(Qt.AlignTop)

        # progress_layout
        self.progress_layout = ProcessProgLayout(lambda: self.plot_figure(*self.collect_data_from_gui()),
                                                 send_log=self.send_log,
                                                 process_type="plot")

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
        plot_layout.addLayout(self.reach_hdf5_layout, 10)  # stretch factor
        plot_layout.addLayout(self.units_layout, 15)  # stretch factor
        plot_layout.addLayout(self.variable_hdf5_layout, 40)  # stretch factor
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
        plot_layout2.addLayout(plot_layout)
        plot_layout2.addLayout(plot_type_layout)
        plot_layout2.addLayout(self.progress_layout)
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
                    self.nb_plot = len(names_hdf5) * total_variables_number * sum(len(x) for x in units)
                    if self.gif_export and self.nb_plot > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)
                if plot_type == ["map", "result"]:
                    self.nb_plot = len(names_hdf5) * total_variables_number * sum(len(x) for x in units)
                    if self.gif_export and self.nb_plot > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)

            # one fish
            if total_habitat_variable_number == 1:
                if plot_type == ["result"]:
                    nb_map = 0
                else:
                    # one map by fish by unit
                    nb_map = len(names_hdf5) * total_habitat_variable_number * sum(len(x) for x in units)
                    if self.gif_export and nb_map > 1:
                        nb_map = nb_map + total_habitat_variable_number * len(reach) + total_variables_number * len(reach)
                if plot_type == ["map"]:
                    nb_wua_hv = 0
                else:
                    nb_wua_hv = len(names_hdf5) * total_habitat_variable_number
                # total
                self.nb_plot = (len(names_hdf5) * total_variables_number * sum(len(x) for x in units)) + nb_map + nb_wua_hv

            # multi fish
            if total_habitat_variable_number > 1:
                if plot_type == ["result"]:
                    self.nb_plot = 1
                    self.total_fish_result = total_habitat_variable_number
                if plot_type == ["map"]:
                    # one map by fish by unit
                    nb_map = total_habitat_variable_number * sum(len(x) for x in units)
                    if self.gif_export and nb_map > 1:
                        nb_map = nb_map + total_habitat_variable_number * len(reach)
                    self.nb_plot = (len(names_hdf5) * total_variables_number * sum(len(x) for x in units)) + nb_map
                    if self.gif_export and nb_map > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)
                if plot_type == ["map", "result"]:
                    # one map by fish by unit
                    nb_map = total_habitat_variable_number * sum(len(x) for x in units)
                    if self.gif_export and nb_map > 1:
                        nb_map = nb_map + total_habitat_variable_number * len(reach)
                    self.nb_plot = (len(names_hdf5) * total_variables_number * sum(len(x) for x in units)) + nb_map + 1
                    if self.gif_export and nb_map > 1:
                        self.nb_plot = self.nb_plot + total_variables_number * len(reach)
            # set prog
            if self.nb_plot != 0:
                self.progress_layout.run_stop_button.setEnabled(True)
            self.progress_layout.progress_bar.setValue(0.0)
            self.progress_layout.progress_label.setText("{0:.0f}/{1:.0f}".format(0.0, self.nb_plot))
        else:
            self.nb_plot = 0
            self.progress_layout.run_stop_button.setEnabled(False)
            # set prog
            self.progress_layout.progress_bar.setValue(0.0)
            self.progress_layout.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

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

        reach = []
        units = []
        units_index = []

        # reach
        if self.reach_QListWidget.selectedItems():
            for r_i in range(self.reach_QListWidget.count()):
                reach_item = self.reach_QListWidget.item(r_i)
                if reach_item.isSelected():
                    reach.append(reach_item.text())
                    u_selection = self.units_QListWidget.selectedItems()
                    units.append([u_selection[u_i].text() for u_i in range(len(u_selection))])
                    units_index.append([self.units_QListWidget.indexFromItem(u_selection[u_i]).row() for u_i in range(len(u_selection))])
                else:
                    units.append([])
                    units_index.append([])

                # together = zip(units_index, units)
                # sorted_together = sorted(together)
                # units_index = [x[0] for x in sorted_together]
                # units = [x[1] for x in sorted_together]

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
        plot_attr.nb_plot = self.nb_plot

        # store values
        return types_hdf5, names_hdf5, plot_attr

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

            # add units
            for item_text in self.hdf5.data_2d.unit_list[self.reach_QListWidget.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget.addItem(item)

        # more than one file selected
        elif len(selection_reach) > 1:
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
            self.send_log.emit(self.tr('Warning: ') + self.tr(
                'You cannot display more than 32 habitat values per graph. Current selected : ') + str(
                self.total_fish_result) + self.tr(". Only the first 32 will be displayed."))
            # get 32 first element list
            self.hvum.user_target_list = self.hvum.user_target_list[:32]
        # check if number of display plot are > cpu_count()
        if plot_attr.export_type in ("interactive", "both") and self.nb_plot > self.nb_plot_max:  # "interactive", "image export", "both
            qm = QMessageBox
            qm.question(self, self.tr("Warning"),
                              self.tr("Displaying a large number of interactive plots may crash HABBY. "
                                      "It is not possible to exceed a total number of plots "
                                      "greater than " + str(self.nb_plot_max) + " at a time. \n\n"
                                                          "\n\nNB : There is no limit for exports."),
                              qm.Ok)
            return

        # Go plot
        if types_hdf5 and names_hdf5 and self.hvum.user_target_list and plot_attr.reach and plot_attr.units and plot_attr.plot_type:
            # figure option
            project_properties = load_project_properties(self.path_prj)
            project_properties['type_plot'] = plot_attr.export_type  # "interactive", "image export", "both

            plot_attr.hvum = self.hvum
            plot_attr.plot_map_QCheckBoxisChecked = self.plot_map_QCheckBox.isChecked()

            # process_manager
            self.progress_layout.process_manager.set_plot_hdf5_mode(self.path_prj, names_hdf5, plot_attr, project_properties)

            # process_prog_show
            self.progress_layout.start_process()


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
        self.available_export_list = ["mesh_whole_profile",
                                          "point_whole_profile",
                                          "mesh_units",
                                          "point_units",
                                          "elevation_whole_profile",
                                          "variables_units",
                                      "mesh_detailled_text",
                                      "point_detailled_text",
                                          "fish_information"]
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
        self.mesh_detailled_text_hyd = QCheckBox("")
        self.mesh_detailled_text_hyd.setObjectName("mesh_detailled_text_hyd")
        self.mesh_detailled_text_hyd.stateChanged.connect(self.count_export)
        self.point_detailled_text_hyd = QCheckBox("")
        self.point_detailled_text_hyd.setObjectName("point_detailled_text_hyd")
        self.point_detailled_text_hyd.stateChanged.connect(self.count_export)
        self.hyd_checkbox_list = [self.mesh_whole_profile_hyd,
                                  self.point_whole_profile_hyd,
                                  self.mesh_units_hyd,
                                  self.point_units_hyd,
                                  self.elevation_whole_profile_hyd,
                                  self.variables_units_hyd,
                                  self.mesh_detailled_text_hyd,
                                  self.point_detailled_text_hyd]

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
        self.mesh_detailled_text_hab = QCheckBox("")
        self.mesh_detailled_text_hab.setObjectName("mesh_detailled_text_hab")
        self.mesh_detailled_text_hab.stateChanged.connect(self.count_export)
        self.point_detailled_text_hab = QCheckBox("")
        self.point_detailled_text_hab.setObjectName("point_detailled_text_hab")
        self.point_detailled_text_hab.stateChanged.connect(self.count_export)
        self.fish_information_hab = QCheckBox("")
        self.fish_information_hab.setObjectName("fish_information_hab")
        self.fish_information_hab.stateChanged.connect(self.count_export)
        self.hab_checkbox_list = [self.mesh_units_hab,
                                  self.point_units_hab,
                                  self.elevation_whole_profile_hab,
                                  self.variables_units_hab,
                                  self.habitat_text_hab,
                                  self.mesh_detailled_text_hab,
                                  self.point_detailled_text_hab,
                                  self.fish_information_hab]

        # progress_layout
        self.progress_layout = ProcessProgLayout(self.start_export,
                                                 send_log=self.send_log,
                                                process_type="export")

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
        self.hyd_export_layout.addWidget(QLabel(self.tr("Mesh detailled ")), 9, 1)
        self.hyd_export_layout.addWidget(self.mesh_detailled_text_hyd, 9, 2, Qt.AlignCenter)
        # row 10
        self.hyd_export_layout.addWidget(QLabel("Text (.txt)"), 10, 0)
        self.hyd_export_layout.addWidget(QLabel(self.tr("Point detailled")), 10, 1)
        self.hyd_export_layout.addWidget(self.point_detailled_text_hyd, 10, 2, Qt.AlignCenter)
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
        self.hab_export_layout.addWidget(QLabel(self.tr("Mesh detailled ")), 11, 1)
        self.hab_export_layout.addWidget(self.mesh_detailled_text_hab, 11, 2, Qt.AlignCenter)
        # row 12
        self.hab_export_layout.addWidget(QLabel("Text (.txt)"), 12, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Point detailled")), 12, 1)
        self.hab_export_layout.addWidget(self.point_detailled_text_hab, 12, 2, Qt.AlignCenter)
        # row 13
        self.hab_export_layout.addWidget(QHLine(), 13, 0, 1, 4)
        # row 14
        self.hab_export_layout.addWidget(QLabel(self.tr("Report (" + load_specific_properties(self.path_prj, ['format'])[0] + ")")), 14, 0)
        self.hab_export_layout.addWidget(QLabel(self.tr("Fish informations")), 14, 1)
        self.hab_export_layout.addWidget(self.fish_information_hab, 14, 2, Qt.AlignCenter)
        self.hab_export_layout.setColumnStretch(0, 3)
        self.hab_export_layout.setColumnStretch(1, 3)
        self.hab_export_layout.setColumnStretch(2, 1)
        # hab_export_widget
        self.hab_export_widget = QWidget()
        self.hab_export_widget.hide()
        self.hab_export_widget.setLayout(self.hab_export_layout)

        """ data_exporter layout """
        self.data_exporter_layout = QVBoxLayout()
        self.data_exporter_layout.addWidget(self.empty_export_widget)
        self.data_exporter_layout.addWidget(self.hyd_export_widget)
        self.data_exporter_layout.addWidget(self.hab_export_widget)
        self.data_exporter_layout.addLayout(self.progress_layout)
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
                self.progress_layout.run_stop_button.setEnabled(True)
            self.progress_layout.progress_bar.setValue(0.0)
            self.progress_layout.progress_label.setText("{0:.0f}/{1:.0f}".format(0, self.nb_export))
        else:
            self.nb_export = 0
            self.progress_layout.run_stop_button.setEnabled(False)
            # set prog
            self.progress_layout.progress_bar.setValue(0.0)
            self.progress_layout.progress_label.setText("{0:.0f}/{1:.0f}".format(0, 0))

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
            project_properties = load_project_properties(self.path_prj)

            # fake temporary project_properties
            if self.current_type == 1:  # hydraulic
                index_dict = 0
            else:
                index_dict = 1

            # set to False all export before setting specific export to True
            for key in self.available_export_list:
                project_properties[key][index_dict] = False

            # setting specific export to True
            for key in export_dict.keys():
                project_properties[key[:-4]][index_dict] = export_dict[key]

            if True in export_dict.values():

                self.progress_layout.process_manager.set_export_hdf5_mode(self.path_prj,
                                                                          names_hdf5,
                                                                          project_properties)

                # process_prog_show
                self.progress_layout.start_process()

    def create_script(self, hydrau_description_multiple):
        # path_prj
        path_prj_script = self.path_prj + "_restarted"

        # cli
        if sys.argv[0][-3:] == ".py":
            exe_cmd = '"' + sys.executable + '" "' + sys.argv[0] + '"'
        else:
            exe_cmd = '"' + sys.executable + '"'
        script_function_name = "EXPORT"
        cmd_str = exe_cmd + ' ' + script_function_name + \
                  ' model="' + self.model_type + '"' + \
                  ' inputfile="' + os.path.join(self.path_prj, "input", self.name_hdf5.split(".")[0], "indexHYDRAU.txt") + '"' + \
                  ' unit_list=' + str(self.hydrau_description_list[self.input_file_combobox.currentIndex()]['unit_list']).replace("\'", "'").replace(' ', '') + \
                  ' cut=' + str(self.project_properties['cut_mesh_partialy_dry']) + \
                  ' outputfilename="' + self.name_hdf5 + '"' + \
                  ' path_prj="' + path_prj_script + '"'
        self.send_log.emit("script" + cmd_str)

        # py
        cmd_str = F"\t# EXPORT\n" \
                  F"\tfrom src.hydraulic_process_mod import HydraulicSimulationResultsAnalyzer, load_hydraulic_cut_to_hdf5\n\n"
        cmd_str = cmd_str + F'\thsra_value = HydraulicSimulationResultsAnalyzer(filename_path_list=[{repr(os.path.join(self.path_prj, "input", self.name_hdf5.split(".")[0], "indexHYDRAU.txt"))}], ' \
                  F"\tpath_prj={repr(path_prj_script)}, " \
                  F"\tmodel_type={repr(self.model_type)}, " \
                  F"\tnb_dim={repr(str(self.nb_dim))})\n"
        cmd_str = cmd_str + F"\tfor hdf5_file_index in range(0, len(hsra_value.hydrau_description_list)):\n" \
                            F"\t\tprogress_value = Value('d', 0.0)\n" \
                            F"\t\tq = Queue()\n" \
                            F"\t\tload_hydraulic_cut_to_hdf5(hydrau_description=hsra_value.hydrau_description_list[hdf5_file_index], " \
                            F"\tprogress_value=progress_value, " \
                            F"\tq=q, " \
                            F"\tprint_cmd=True, " \
                            F"\tproject_properties=load_project_properties({repr(path_prj_script)}))" + "\n"
        self.send_log.emit("py" + cmd_str)


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
        if not len(file_selection) == 1:
            self.send_log.emit(self.tr('Warning: ') + self.tr('No file selected.'))
            return

        # selected fish
        hab_variable_list = []
        for selection in self.existing_animal_QListWidget.selectedItems():
            hab_variable_list.append(selection.data(Qt.UserRole).name)

        # remove
        self.hdf5.remove_fish_hab(hab_variable_list)

        # refresh
        self.parent().names_hdf5_change()
        self.parent().send_log.emit(", ".join(hab_variable_list) + " data has been removed in .hab file.")

        self.nativeParentWidget().central_widget.update_combobox_filenames()


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


