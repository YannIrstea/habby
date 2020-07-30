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
from src.project_properties_mod import load_project_properties, save_project_properties
from src import hydrosignature


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

        # refresh_filenames
        self.refresh_filenames()

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

    def refresh_filenames(self):
        # computing_group
        hyd_names = hdf5_mod.get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
        hab_names = hdf5_mod.get_filename_by_type_physic("habitat", os.path.join(self.path_prj, "hdf5"))
        names = hyd_names + hab_names
        self.computing_group.file_selection_listwidget.blockSignals(True)
        self.computing_group.file_selection_listwidget.clear()
        if names:
            self.computing_group.file_selection_listwidget.addItems(names)
        self.computing_group.file_selection_listwidget.blockSignals(False)

        # visual_group
        self.visual_group.file_selection_listwidget.blockSignals(True)
        self.visual_group.file_selection_listwidget.clear()
        if names:
            self.visual_group.file_selection_listwidget.addItems(names)
        self.visual_group.file_selection_listwidget.blockSignals(False)

        # compare_group


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
        self.classhv = None
        self.setTitle(title)
        self.init_ui()

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
        self.input_class_pushbutton.clicked.connect(self.select_input_class_dialog)
        hs_export_txt_label = QLabel(self.tr("Export results (.txt)"))
        self.hs_export_txt_checkbox = QCheckBox()
        hs_export_mesh_label = QLabel(self.tr("Export mesh results (.hyd or .hab)"))
        self.hs_export_mesh_checkbox = QCheckBox()
        self.computation_pushbutton = QPushButton(self.tr("run"))
        self.computation_pushbutton.clicked.connect(self.compute)

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

    def select_input_class_dialog(self):
        # get last path
        if self.read_attribute_xml("HS_input_class") != self.path_prj and self.read_attribute_xml(
                "HS_input_class") != "":
            model_path = self.read_attribute_xml("HS_input_class")  # path spe
        elif self.read_attribute_xml("path_last_file_loaded") != self.path_prj and self.read_attribute_xml("path_last_file_loaded") != "":
            model_path = self.read_attribute_xml("path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select hydraulic class file"),
                                                  model_path + "\\input", self.tr("Text files") + " (*.txt)")
        if filename:
            self.pathfile = os.path.dirname(filename)  # source file path
            self.namefile = os.path.basename(filename)  # source file name
            self.save_xml("HS_input_class")

            try:
                self.classhv = hydrosignature.hydraulic_class_from_file(filename)
                self.input_class_filename.setText(os.path.basename(filename))
            except FileNotFoundError:
                self.send_log.emit('Error: ' + self.tr('Selected hydraulic input class file is not valid.'))

    def read_attribute_xml(self, att_here):
        """
        A function to read the text of an attribute in the xml project file.

        :param att_here: the attribute name (string).
        """
        data = ''

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            if att_here == "path_last_file_loaded":
                data = load_project_properties(self.path_prj)[att_here]
            else:
                data = load_project_properties(self.path_prj)[att_here]["path"]
        else:
            pass

        return data

    def save_xml(self, attr):
        """
        A function to save the loaded data in the xml file.

        This function adds the name and the path of the newly chosen hydrological data to the xml project file. First,
        it open the xml project file (and send an error if the project is not saved, or if it cannot find the project
        file). Then, it opens the xml file and add the path and name of the file to this xml file. If the model data was
        already loaded, it adds the new name without erasing the old name IF the switch append_name is True. Otherwise,
        it erase the old name and replace it by a new name. The variable “i” has the same role than in select_file_and_show_informations_dialog.

        :param i: a int for the case where there is more than one file to load
        :param append_name: A boolean. If True, the name found will be append to the existing name in the xml file,
                instead of remplacing the old name by the new name.

        """
        filename_path_file = self.pathfile
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')

        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.end_log.emit('Error: The project is not saved. '
                              'Save the project in the General tab before saving hydrological data. \n')
        else:
            # change path_last_file_loaded, model_type (path)
            project_preferences = load_project_properties(self.path_prj)  # load_project_properties
            project_preferences["path_last_file_loaded"] = filename_path_file  # change value
            project_preferences[attr]["path"] = filename_path_file  # change value
            save_project_properties(self.path_prj, project_preferences)  # save_project_properties

    def compute(self):
        aa = 1


        # compute
        hdf5 = hdf5_mod.Hdf5Management(self.path_prj, self.file_selection_listwidget.currentItem().text())
        hdf5.hydrosignature_new_file(self.classhv)


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
        self.file_selection_listwidget.itemSelectionChanged.connect(self.names_hdf5_change)

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

    def names_hdf5_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        selection = self.file_selection_listwidget.selectedItems()
        self.plot_group.mesh_variable_QListWidget.clear()
        self.plot_group.node_variable_QListWidget.clear()
        self.plot_group.units_QListWidget.clear()
        self.plot_group.reach_QListWidget.clear()
        self.plot_group.units_QLabel.setText(self.tr("unit(s)"))
        self.habitatvalueremover_group.existing_animal_QListWidget.clear()

        if len(selection) == 1:
            reach_list = []
            unit_list = []
            variable_node_list = []
            variable_mesh_list = []
            for selection_el in selection:
                # read
                hdf5name = selection_el.text()
                hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
                hdf5.open_hdf5_file(False)
                # check reach
                reach_list.append(hdf5.reach_name)
                # check unit
                unit_list.append(hdf5.units_name)

            # one file selected
            self.plot_group.units_QListWidget.clear()
            hdf5name = selection[0].text()

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
                if hdf5.hvum.hdf5_and_computable_list.meshs().names_gui():
                    for mesh in hdf5.hvum.hdf5_and_computable_list.meshs():
                        mesh_item = QListWidgetItem(mesh.name_gui, self.plot_group.mesh_variable_QListWidget)
                        mesh_item.setData(Qt.UserRole, mesh)
                        if not mesh.hdf5:
                            mesh_item.setText(mesh_item.text() + " *")
                            mesh_item.setToolTip("computable")
                        self.plot_group.mesh_variable_QListWidget.addItem(mesh_item)
                if hdf5.hvum.hdf5_and_computable_list.nodes().names_gui():
                    for node in hdf5.hvum.hdf5_and_computable_list.nodes():
                        node_item = QListWidgetItem(node.name_gui, self.plot_group.node_variable_QListWidget)
                        node_item.setData(Qt.UserRole, node)
                        if not node.hdf5:
                            node_item.setText(node_item.text() + " *")
                            node_item.setToolTip("computable")
                        self.plot_group.node_variable_QListWidget.addItem(node_item)

                if hdf5.reach_name:
                    self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                    if len(hdf5.reach_name) == 1:
                        self.plot_group.reach_QListWidget.selectAll()
                        if hdf5.nb_unit == 1:
                            self.plot_group.units_QListWidget.selectAll()
                        else:
                            self.plot_group.units_QListWidget.setCurrentRow(0)

            # substrat
            if self.types_hdf5_QComboBox.currentIndex() == 2:
                self.set_substrate_layout()
                if hdf5.hvum.hdf5_and_computable_list.meshs().names_gui():
                    for mesh in hdf5.hvum.hdf5_and_computable_list.meshs():
                        mesh_item = QListWidgetItem(mesh.name_gui, self.plot_group.mesh_variable_QListWidget)
                        mesh_item.setData(Qt.UserRole, mesh)
                        if not mesh.hdf5:
                            mesh_item.setText(mesh_item.text() + " *")
                            mesh_item.setToolTip("computable")
                        self.plot_group.mesh_variable_QListWidget.addItem(mesh_item)
                if hdf5.hvum.hdf5_and_computable_list.nodes().names_gui():
                    for node in hdf5.hvum.hdf5_and_computable_list.nodes():
                        node_item = QListWidgetItem(node.name_gui, self.plot_group.node_variable_QListWidget)
                        node_item.setData(Qt.UserRole, node)
                        if not node.hdf5:
                            node_item.setText(node_item.text() + " *")
                            node_item.setToolTip("computable")
                        self.plot_group.node_variable_QListWidget.addItem(node_item)

                if hdf5.sub_mapping_method != "constant":
                    if hdf5.reach_name:
                        self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                        if len(hdf5.reach_name) == 1:
                            self.plot_group.reach_QListWidget.selectAll()
                            if hdf5.nb_unit == 1:
                                self.plot_group.units_QListWidget.selectAll()
                            else:
                                self.plot_group.units_QListWidget.setCurrentRow(0)

            # habitat
            if self.types_hdf5_QComboBox.currentIndex() == 3:
                self.set_habitat_layout()
                if hdf5.hvum.hdf5_and_computable_list.meshs().names_gui():
                    for mesh in hdf5.hvum.hdf5_and_computable_list.meshs():
                        mesh_item = QListWidgetItem(mesh.name_gui, self.plot_group.mesh_variable_QListWidget)
                        mesh_item.setData(Qt.UserRole, mesh)
                        if not mesh.hdf5:
                            mesh_item.setText(mesh_item.text() + " *")
                            mesh_item.setToolTip("computable")
                        self.plot_group.mesh_variable_QListWidget.addItem(mesh_item)
                if hdf5.hvum.hdf5_and_computable_list.nodes().names_gui():
                    for node in hdf5.hvum.hdf5_and_computable_list.nodes():
                        node_item = QListWidgetItem(node.name_gui, self.plot_group.node_variable_QListWidget)
                        node_item.setData(Qt.UserRole, node)
                        if not node.hdf5:
                            node_item.setText(node_item.text() + " *")
                            node_item.setToolTip("computable")
                        self.plot_group.node_variable_QListWidget.addItem(node_item)

                # habitatvalueremover_group
                if hdf5.hvum.hdf5_and_computable_list.meshs().habs().names_gui():
                    for mesh in hdf5.hvum.hdf5_and_computable_list.habs().meshs():
                        mesh_item = QListWidgetItem(mesh.name_gui, self.habitatvalueremover_group.existing_animal_QListWidget)
                        mesh_item.setData(Qt.UserRole, mesh)
                        if not mesh.hdf5:
                            mesh_item.setText(mesh_item.text() + " *")
                            mesh_item.setToolTip("computable")
                        self.habitatvalueremover_group.existing_animal_QListWidget.addItem(mesh_item)

                if hdf5.reach_name:
                    self.plot_group.reach_QListWidget.addItems(hdf5.reach_name)
                    if len(hdf5.reach_name) == 1:
                        self.plot_group.reach_QListWidget.selectAll()
                        if hdf5.nb_unit == 1:
                            self.plot_group.units_QListWidget.selectAll()
                        else:
                            self.plot_group.units_QListWidget.setCurrentRow(0)





        # count plot
        self.plot_group.count_plot()
        # count exports
        self.dataexporter_group.count_export()

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