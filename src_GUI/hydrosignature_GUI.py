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
from multiprocessing import Process, Value, Queue, Event

from PyQt5.QtCore import pyqtSignal, Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, \
    QMessageBox, QFrame, QLineEdit, QGridLayout, QFileDialog, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QTableView, \
    QCheckBox, QListWidgetItem, QRadioButton, QListView

from src.hydraulic_process_mod import load_hs_and_compare
from src.process_manager_mod import MyProcessManager
from src.hdf5_mod import get_filename_by_type_physic, get_filename_hs, Hdf5Management
from src.project_properties_mod import load_project_properties, save_project_properties, change_specific_properties,\
    load_specific_properties
from src import hydrosignature_mod
from src_GUI.dev_tools_GUI import change_button_color, MyTableModel, \
    QGroupBoxCollapsible
from src_GUI.process_manager_GUI import ProcessProgLayout, ProcessProgShow


class HsTab(QScrollArea):
    """
    Tool tab
    """
    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.tab_name = "hs"
        self.tab_title = "Hydrosignature"
        self.tooltip_str = "Hydrosignature"
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.msg2 = QMessageBox()
        self.init_iu()

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
        self.computing_group.setChecked(False)

        # visual
        self.visual_group = VisualGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Visualisation"))
        self.visual_group.setChecked(False)

        # visual
        self.compare_group = CompareGroup(self.path_prj, self.name_prj, self.send_log, self.tr("Comparison"))
        self.compare_group.setChecked(False)

        # vertical layout
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addWidget(self.computing_group)
        global_layout.addWidget(self.visual_group)
        global_layout.addWidget(self.compare_group)
        global_layout.addStretch()
        self.setWidget(tools_frame)

    def refresh_gui(self):
        # computing_group
        self.computing_group.update_gui()

        # visual_group
        self.visual_group.update_gui()

        # compare_group
        self.compare_group.update_gui()

    def kill_process(self):
        self.computing_group.process_manager.stop_by_user()
        self.visual_group.process_manager.stop_by_user()


class ComputingGroup(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """
    send_refresh_filenames = pyqtSignal(name='send_refresh_filenames')

    def __init__(self, path_prj, name_prj, send_log, title):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.path_last_file_loaded = self.path_prj
        self.classhv = None
        self.project_properties = load_project_properties(self.path_prj)
        self.setTitle(title)
        self.init_ui()
        self.input_class_file_info = self.read_attribute_xml("HS_input_class")
        self.read_input_class(os.path.join(self.input_class_file_info["path"], self.input_class_file_info["file"]))
        # process_manager
        self.process_manager = MyProcessManager("hs")

    def init_ui(self):
        # file_selection
        file_selection_label = QLabel(self.tr("Select a 2D mesh file :"))
        self.file_selection_listwidget = QListWidget()
        self.file_selection_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_selection_listwidget.itemSelectionChanged.connect(self.names_hdf5_change)
        self.file_selection_listwidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_selection_listwidget.verticalScrollBar().setEnabled(True)
        self.file_selection_listwidget.verticalScrollBar().valueChanged.connect(self.change_scroll_position)
        self.scrollbar = self.file_selection_listwidget.verticalScrollBar()
        file_computed_label = QLabel(self.tr("Computed ?"))
        self.hs_computed_listwidget = QListWidget()
        self.hs_computed_listwidget.setEnabled(False)
        self.hs_computed_listwidget.setFlow(QListView.TopToBottom)
        self.hs_computed_listwidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hs_computed_listwidget.verticalScrollBar().setEnabled(True)
        self.hs_computed_listwidget.verticalScrollBar().valueChanged.connect(self.change_scroll_position)

        file_selection_layout = QGridLayout()
        file_selection_layout.addWidget(file_selection_label, 0, 0)
        file_selection_layout.addWidget(self.file_selection_listwidget, 1, 0)
        file_selection_layout.addWidget(file_computed_label, 0, 1)
        file_selection_layout.addWidget(self.hs_computed_listwidget, 1, 1)
        file_selection_layout.addWidget(self.scrollbar, 1, 2)
        file_selection_layout.setColumnStretch(0, 30)
        file_selection_layout.setColumnStretch(1, 1)

        input_class_label = QLabel(self.tr("Input class (.txt)"))
        self.input_class_filename = QLabel("")
        self.input_class_pushbutton = QPushButton("...")
        self.input_class_pushbutton.clicked.connect(self.select_input_class_dialog)
        hs_export_txt_label = QLabel(self.tr("Export results (.txt)"))
        self.hs_export_txt_checkbox = QCheckBox()
        self.hs_export_txt_checkbox.setChecked(True)
        hs_export_mesh_label = QLabel(self.tr("Export mesh results (.hyd or .hab)"))
        self.hs_export_mesh_checkbox = QCheckBox()

        """ progress layout """
        # progress_layout
        self.progress_layout = ProcessProgLayout(self.compute,
                                                 send_log=self.send_log,
                                                 process_type="hs",
                                                 send_refresh_filenames=self.send_refresh_filenames)

        grid_layout = QGridLayout()
        grid_layout.addWidget(input_class_label, 2, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.input_class_filename, 2, 1, Qt.AlignLeft)
        grid_layout.addWidget(self.input_class_pushbutton, 2, 2, Qt.AlignLeft)
        grid_layout.addWidget(hs_export_txt_label, 3, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.hs_export_txt_checkbox, 3, 1, Qt.AlignLeft)
        grid_layout.addWidget(hs_export_mesh_label, 4, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.hs_export_mesh_checkbox, 4, 1, Qt.AlignLeft)
        grid_layout.addLayout(self.progress_layout, 5, 0, 1, 3)

        grid_layout.setColumnStretch(0, 2)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setAlignment(Qt.AlignRight)

        general_layout = QVBoxLayout()
        general_layout.addLayout(file_selection_layout)
        general_layout.addLayout(grid_layout)

        self.setLayout(general_layout)

    def update_gui(self):
        selected_file_names = [selection_el.text() for selection_el in self.file_selection_listwidget.selectedItems()]
        # computing_group
        hyd_names = get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
        hab_names = get_filename_by_type_physic("habitat", os.path.join(self.path_prj, "hdf5"))
        names = hyd_names + hab_names
        self.file_selection_listwidget.blockSignals(True)
        self.file_selection_listwidget.clear()
        self.hs_computed_listwidget.blockSignals(True)
        self.hs_computed_listwidget.clear()
        if names:
            for name in names:
                # filename
                item_name = QListWidgetItem()
                item_name.setText(name)
                self.file_selection_listwidget.addItem(item_name)
                if name in selected_file_names:
                    item_name.setSelected(True)
                # check
                item = QListWidgetItem()
                item.setText("")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                try:
                    hdf5 = Hdf5Management(self.path_prj, name, new=False, edit=False)
                    hdf5.get_hdf5_attributes(close_file=True)
                    if hdf5.hs_calculated:
                        item.setCheckState(Qt.Checked)
                    else:
                        item.setCheckState(Qt.Unchecked)
                except:
                    self.send_log.emit(self.tr("Error: " + name + " file seems to be corrupted. Delete it with HABBY or manually."))
                self.hs_computed_listwidget.addItem(item)

                item.setTextAlignment(Qt.AlignCenter)

        self.file_selection_listwidget.blockSignals(False)
        self.hs_computed_listwidget.blockSignals(False)
        # preselection if one
        if self.file_selection_listwidget.count() == 1:
            self.file_selection_listwidget.selectAll()

    def change_scroll_position(self, index):
        self.file_selection_listwidget.verticalScrollBar().setValue(index)
        self.hs_computed_listwidget.verticalScrollBar().setValue(index)

    def read_input_class(self, input_class_file):
        if os.path.exists(input_class_file):
            self.classhv, warnings_list = hydrosignature_mod.hydraulic_class_from_file(input_class_file)
            if warnings_list:
                for warning in warnings_list:
                    self.send_log.emit(warning)
            if self.classhv is None:
                self.send_log.emit(self.tr("Error: Input class file : ") + os.path.basename(input_class_file) + self.tr(" is not valid."))
                self.progress_layout.run_stop_button.setEnabled(False)
            else:
                self.input_class_filename.setText(os.path.basename(input_class_file))
                if self.file_selection_listwidget.selectedItems():
                    self.progress_layout.run_stop_button.setEnabled(True)
        else:
            self.progress_layout.run_stop_button.setEnabled(False)

        self.progress_layout.progress_bar.setValue(0.0)
        self.progress_layout.progress_label.setText(
            "{0:.0f}/{1:.0f}".format(0.0, len(self.file_selection_listwidget.selectedItems())))

    def names_hdf5_change(self):
        selection = self.file_selection_listwidget.selectedItems()
        self.progress_layout.progress_bar.setValue(0.0)
        self.progress_layout.progress_label.setText(
            "{0:.0f}/{1:.0f}".format(0.0, len(selection)))
        if selection:
            # enable run button
            if self.input_class_filename.text():
                self.progress_layout.run_stop_button.setEnabled(True)
            else:
                self.progress_layout.run_stop_button.setEnabled(False)
        else:
            self.progress_layout.run_stop_button.setEnabled(False)

    def select_input_class_dialog(self):
        self.input_class_file_info = self.read_attribute_xml("HS_input_class")
        # get last path
        if self.input_class_file_info["path"] != self.path_prj and self.input_class_file_info["path"] != "":
            model_path = self.input_class_file_info["path"]  # path spe
        elif self.read_attribute_xml("path_last_file_loaded") != self.path_prj and self.read_attribute_xml("path_last_file_loaded") != "":
            model_path = self.read_attribute_xml("path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select hydraulic class file"),
                                                  model_path, self.tr("Text files") + " (*.txt)")
        if filename:
            self.pathfile = os.path.dirname(filename)  # source file path
            self.namefile = os.path.basename(filename)  # source file name
            self.save_xml("HS_input_class")
            self.read_input_class(filename)
            self.input_class_file_info = self.read_attribute_xml("HS_input_class")

    def read_attribute_xml(self, att_here):
        """
        A function to read the text of an attribute in the xml project file.

        :param att_here: the attribute name (string).
        """
        data = ''

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            if att_here in {"path_last_file_loaded", "HS_input_class"}:
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
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')

        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.end_log.emit('Error: The project is not saved. '
                              'Save the project in the General tab before saving hydrological data. \n')
        else:
            # change path_last_file_loaded, model_type (path)
            self.project_properties = load_project_properties(self.path_prj)  # load_project_properties
            self.project_properties["path_last_file_loaded"] = self.pathfile  # change value
            self.project_properties[attr]["file"] = self.namefile  # change value
            self.project_properties[attr]["path"] = self.pathfile  # change value
            save_project_properties(self.path_prj, self.project_properties)  # save_project_properties

    def compute(self):
        if len(self.file_selection_listwidget.selectedItems()) > 0:
            hydrosignature_description = dict(hs_export_mesh=self.hs_export_mesh_checkbox.isChecked(),
                                              hdf5_name_list=[selection_el.text() for selection_el in
                                                              self.file_selection_listwidget.selectedItems()],
                                              hs_export_txt=self.hs_export_txt_checkbox.isChecked(),
                                              classhv_input_class_file_info=self.input_class_file_info,
                                              classhv=self.classhv)

            self.progress_layout.process_manager.set_hs_hdf5_mode(self.path_prj,
                                                                  hydrosignature_description,
                                                                  self.project_properties)

            # start thread
            self.progress_layout.start_process()

    def stop_compute(self):
        # stop_by_user
        self.process_manager.stop_by_user()


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
        self.process_manager = MyProcessManager("hs_plot")
        self.axe_mod_choosen = 1
        self.setTitle(title)
        self.init_ui()
        self.process_prog_show_input = ProcessProgShow(send_log=self.send_log,
                                                 run_function=self.plot_hs_class,
                                                 computation_pushbutton=self.input_class_plot_button)
        self.process_prog_show_area = ProcessProgShow(send_log=self.send_log,
                                                 run_function=self.plot_hs_area,
                                                 computation_pushbutton=self.result_plot_button_area)
        self.process_prog_show_volume = ProcessProgShow(send_log=self.send_log,
                                                 run_function=self.plot_hs_volume,
                                                 computation_pushbutton=self.result_plot_button_volume)

    def init_ui(self):
        # file_selection
        file_selection_label = QLabel(self.tr("HS files :"))
        self.file_selection_listwidget = QListWidget()
        self.file_selection_listwidget.itemSelectionChanged.connect(self.names_hdf5_change)
        file_selection_layout = QVBoxLayout()
        file_selection_layout.addWidget(file_selection_label)
        file_selection_layout.addWidget(self.file_selection_listwidget)

        # reach
        reach_label = QLabel(self.tr('reach(s)'))
        self.reach_QListWidget = QListWidget()
        self.reach_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.reach_QListWidget.itemSelectionChanged.connect(self.reach_hdf5_change)
        reach_layout = QVBoxLayout()
        reach_layout.addWidget(reach_label)
        reach_layout.addWidget(self.reach_QListWidget)

        # units
        units_label = QLabel(self.tr('unit(s)'))
        self.units_QListWidget = QListWidget()
        self.units_QListWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.units_QListWidget.itemSelectionChanged.connect(self.unit_hdf5_change)
        units_layout = QVBoxLayout()
        units_layout.addWidget(units_label)
        units_layout.addWidget(self.units_QListWidget)

        # axe
        self.axe_mod_choosen = load_specific_properties(self.path_prj, ["hs_axe_mod"])[0]

        axe_label = QLabel(self.tr("Axe orientation :"))
        self.axe_mod_1_radio = QRadioButton()
        if self.axe_mod_choosen == 1:
            self.axe_mod_1_radio.setChecked(True)
        self.axe_mod_1_radio.setIcon(QIcon(r"file_dep/axe_mod_1.png"))
        self.axe_mod_1_radio.setIconSize(QSize(75, 75))
        self.axe_mod_1_radio.clicked.connect(self.change_axe_mod)

        self.axe_mod_2_radio = QRadioButton()
        if self.axe_mod_choosen == 2:
            self.axe_mod_2_radio.setChecked(True)
        self.axe_mod_2_radio.setIcon(QIcon(r"file_dep/axe_mod_2.png"))
        self.axe_mod_2_radio.setIconSize(QSize(75, 75))
        self.axe_mod_2_radio.clicked.connect(self.change_axe_mod)

        self.axe_mod_3_radio = QRadioButton()
        if self.axe_mod_choosen == 3:
            self.axe_mod_3_radio.setChecked(True)
        self.axe_mod_3_radio.setIcon(QIcon(r"file_dep/axe_mod_3.png"))
        self.axe_mod_3_radio.setIconSize(QSize(75, 75))
        self.axe_mod_3_radio.clicked.connect(self.change_axe_mod)

        axe_mod_layout = QHBoxLayout()
        axe_mod_layout.addWidget(self.axe_mod_1_radio)
        axe_mod_layout.addWidget(self.axe_mod_2_radio)
        axe_mod_layout.addWidget(self.axe_mod_3_radio)
        axe_layout = QVBoxLayout()
        axe_layout.addWidget(axe_label)
        axe_layout.addLayout(axe_mod_layout)
        axe_layout.addStretch()
        selection_layout = QHBoxLayout()
        selection_layout.addLayout(file_selection_layout)
        selection_layout.addLayout(reach_layout)
        selection_layout.addLayout(units_layout)
        selection_layout.addLayout(axe_layout)

        # input_class
        input_class_label = QLabel(self.tr("Input class :"))
        input_class_h_label = QLabel(self.tr("h (m)"))
        self.input_class_h_lineedit = QLineEdit("")
        input_class_v_label = QLabel(self.tr("v (m)"))
        self.input_class_v_lineedit = QLineEdit("")
        self.input_class_plot_button = QPushButton(self.tr("Show input"))
        self.input_class_plot_button.clicked.connect(self.plot_hs_class)
        change_button_color(self.input_class_plot_button, "#47B5E6")
        self.input_class_plot_button.setEnabled(False)
        input_class_layout = QGridLayout()
        input_class_layout.addWidget(input_class_label, 0, 0, 1, 2)
        input_class_layout.addWidget(input_class_h_label, 1, 0)
        input_class_layout.addWidget(input_class_v_label, 2, 0)
        input_class_layout.addWidget(self.input_class_h_lineedit, 1, 1)
        input_class_layout.addWidget(self.input_class_v_lineedit, 2, 1)
        input_class_layout.addWidget(self.input_class_plot_button, 1, 2, 2, 1)  # from row, from column, nb row, nb column

        # result
        result_label = QLabel(self.tr("Result :"))
        self.result_tableview = QTableView()
        self.result_tableview.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.result_tableview.verticalHeader().setVisible(False)
        self.result_tableview.horizontalHeader().setVisible(False)
        self.result_plot_button_area = QPushButton(self.tr("Show area"))
        self.result_plot_button_area.clicked.connect(self.plot_hs_area)
        self.result_plot_button_area.setEnabled(False)
        change_button_color(self.result_plot_button_area, "#47B5E6")
        self.result_plot_button_volume = QPushButton(self.tr("Show volume"))
        self.result_plot_button_volume.clicked.connect(self.plot_hs_volume)
        self.result_plot_button_volume.setEnabled(False)
        change_button_color(self.result_plot_button_volume, "#47B5E6")
        pushbutton_layout = QVBoxLayout()
        pushbutton_layout.addWidget(self.result_plot_button_area)
        pushbutton_layout.addWidget(self.result_plot_button_volume)
        result_layout = QGridLayout()
        result_layout.addWidget(result_label, 0, 0)
        result_layout.addWidget(self.result_tableview, 1, 0, 2, 1)
        result_layout.addLayout(pushbutton_layout, 1, 1)
        self.input_result_group = QGroupBox()
        input_result_layout = QVBoxLayout()
        input_result_layout.addLayout(input_class_layout)
        input_result_layout.addLayout(result_layout)
        self.input_result_group.setLayout(input_result_layout)
        self.input_result_group.hide()

        general_layout = QVBoxLayout()
        general_layout.addLayout(selection_layout)
        general_layout.addWidget(self.input_result_group)

        self.setLayout(general_layout)

    def update_gui(self):
        hs_names = get_filename_hs(os.path.join(self.path_prj, "hdf5"))
        self.file_selection_listwidget.blockSignals(True)
        self.file_selection_listwidget.clear()
        if hs_names:
            self.file_selection_listwidget.addItems(hs_names)
        self.file_selection_listwidget.blockSignals(False)

    def change_axe_mod(self):
        if self.axe_mod_1_radio.isChecked():
            self.axe_mod_choosen = 1
        elif self.axe_mod_2_radio.isChecked():
            self.axe_mod_choosen = 2
        elif self.axe_mod_3_radio.isChecked():
            self.axe_mod_choosen = 3
        change_specific_properties(self.path_prj, ["hs_axe_mod"], [self.axe_mod_choosen])

    def names_hdf5_change(self):
        self.reach_QListWidget.clear()
        self.units_QListWidget.clear()
        selection = self.file_selection_listwidget.selectedItems()
        if selection:
            # read
            hdf5name = selection[0].text()
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.get_hdf5_attributes(close_file=True)
            # check reach
            self.reach_QListWidget.addItems(hdf5.data_2d.reach_list)

            self.input_class_h_lineedit.setText(", ".join(list(map(str, hdf5.hs_input_class[0]))))
            self.input_class_v_lineedit.setText(", ".join(list(map(str, hdf5.hs_input_class[1]))))

            self.input_class_plot_button.setEnabled(True)

            self.toggle_group(False)
            self.input_result_group.show()
            self.toggle_group(True)

        else:
            self.input_result_group.hide()

    def reach_hdf5_change(self):
        selection_file = self.file_selection_listwidget.selectedItems()
        selection_reach = self.reach_QListWidget.selectedItems()
        self.units_QListWidget.clear()
        # one file selected
        if len(selection_reach) == 1:
            hdf5name = selection_file[0].text()

            # create hdf5 class
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.get_hdf5_attributes(close_file=True)

            # add units
            for item_text in hdf5.data_2d.unit_list[self.reach_QListWidget.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget.addItem(item)

        if len(selection_reach) > 1:
            # add units
            item = QListWidgetItem("all units")
            item.setTextAlignment(Qt.AlignRight)
            self.units_QListWidget.addItem(item)
            self.units_QListWidget.selectAll()

    def unit_hdf5_change(self):
        selection_unit = self.units_QListWidget.selectedItems()
        # one file selected
        if len(selection_unit) > 0:
            hdf5name = self.file_selection_listwidget.selectedItems()[0].text()

            # create hdf5 class
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.load_hydrosignature()
            hdf5.close_file()

            if len(selection_unit) == 1 and selection_unit[0].text() == "all units":
                # get hs data
                hdf5.data_2d.get_hs_summary_data([element.row() for element in self.reach_QListWidget.selectedIndexes()],
                                                 list(range(hdf5.nb_unit)))
            else:
                # get hs data
                hdf5.data_2d.get_hs_summary_data([element.row() for element in self.reach_QListWidget.selectedIndexes()],
                                                 [element.row() for element in self.units_QListWidget.selectedIndexes()])

            # table
            mytablemodel = MyTableModel(hdf5.data_2d.hs_summary_data)
            self.result_tableview.setModel(mytablemodel)  # set model
            self.result_plot_button_area.setEnabled(True)
            self.result_plot_button_volume.setEnabled(True)
        else:
            mytablemodel = MyTableModel(["", ""])
            self.result_tableview.setModel(mytablemodel)  # set model
            self.result_plot_button_area.setEnabled(False)
            self.result_plot_button_volume.setEnabled(False)

    def plot_hs_class(self):
        plot_attr = lambda: None

        plot_attr.nb_plot = 1
        plot_attr.axe_mod_choosen = self.axe_mod_choosen
        plot_attr.hs_plot_type = "input_class"

        # process_manager
        self.process_manager.set_plot_hdf5_mode(self.path_prj,
                                                [self.file_selection_listwidget.selectedItems()[0].text()],
                                                plot_attr,
                                                load_project_properties(self.path_prj))

        # process_prog_show
        self.process_prog_show_input.start_show_prog(self.process_manager)

    def plot_hs_area(self):
        plot_attr = lambda: None

        plot_attr.axe_mod_choosen = self.axe_mod_choosen
        plot_attr.hs_plot_type = "area"
        plot_attr.reach = [element.row() for element in self.reach_QListWidget.selectedIndexes()]
        plot_attr.units = [element.row() for element in self.units_QListWidget.selectedIndexes()]
        plot_attr.nb_plot = len(plot_attr.units)

        # process_manager
        self.process_manager.set_plot_hdf5_mode(self.path_prj,
                                                [self.file_selection_listwidget.selectedItems()[0].text()],
                                                plot_attr,
                                                load_project_properties(self.path_prj))

        # process_prog_show
        self.process_prog_show_area.start_show_prog(self.process_manager)

    def plot_hs_volume(self):
        plot_attr = lambda: None

        plot_attr.axe_mod_choosen = self.axe_mod_choosen
        plot_attr.hs_plot_type = "volume"
        plot_attr.reach = [element.row() for element in self.reach_QListWidget.selectedIndexes()]
        plot_attr.units = [element.row() for element in self.units_QListWidget.selectedIndexes()]
        plot_attr.nb_plot = len(plot_attr.units)

        # process_manager
        self.process_manager.set_plot_hdf5_mode(self.path_prj,
                                                [self.file_selection_listwidget.selectedItems()[0].text()],
                                                plot_attr,
                                                load_project_properties(self.path_prj))

        # process_prog_show
        self.process_prog_show_volume.start_show_prog(self.process_manager)


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
        self.comp_filename = 'HS_comp.txt'
        self.q = Queue()
        self.stop = Event()
        self.progress_value = Value("d", 0)
        self.p = Process(target=None)
        self.setTitle(title)
        self.init_ui()

    def init_ui(self):
        # file_selection_1
        file_selection_label_1 = QLabel(self.tr("HS files :"))
        self.file_selection_listwidget_1 = QListWidget()
        # self.file_selection_listwidget_1.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_selection_listwidget_1.itemSelectionChanged.connect(self.names_hdf5_change_1)
        file_selection_layout_1 = QVBoxLayout()
        file_selection_layout_1.addWidget(file_selection_label_1)
        file_selection_layout_1.addWidget(self.file_selection_listwidget_1)

        # reach_1
        reach_label_1 = QLabel(self.tr('reach(s)'))
        self.reach_QListWidget_1 = QListWidget()
        # self.reach_QListWidget_1.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.reach_QListWidget_1.itemSelectionChanged.connect(self.reach_hdf5_change_1)
        reach_layout_1 = QVBoxLayout()
        reach_layout_1.addWidget(reach_label_1)
        reach_layout_1.addWidget(self.reach_QListWidget_1)

        # units_1
        units_label_1 = QLabel(self.tr('unit(s)'))
        self.units_QListWidget_1 = QListWidget()
        self.units_QListWidget_1.itemSelectionChanged.connect(self.enable_disable_pushbutton)
        self.units_QListWidget_1.setSelectionMode(QAbstractItemView.ExtendedSelection)
        units_layout_1 = QVBoxLayout()
        units_layout_1.addWidget(units_label_1)
        units_layout_1.addWidget(self.units_QListWidget_1)
        selection_group_1 = QGroupBox(self.tr("First"))
        selection_group_1.setStyleSheet("QGroupBox { font-weight: normal; } ")
        selection_layout_1 = QHBoxLayout()
        selection_layout_1.addLayout(file_selection_layout_1)
        selection_layout_1.addLayout(reach_layout_1)
        selection_layout_1.addLayout(units_layout_1)
        selection_group_1.setLayout(selection_layout_1)

        # file_selection_2
        file_selection_label_2 = QLabel(self.tr("HS files :"))
        self.file_selection_listwidget_2 = QListWidget()
        # self.file_selection_listwidget_2.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_selection_listwidget_2.itemSelectionChanged.connect(self.names_hdf5_change_2)
        file_selection_layout_2 = QVBoxLayout()
        file_selection_layout_2.addWidget(file_selection_label_2)
        file_selection_layout_2.addWidget(self.file_selection_listwidget_2)

        # reach_2
        reach_label_2 = QLabel(self.tr('reach(s)'))
        self.reach_QListWidget_2 = QListWidget()
        # self.reach_QListWidget_2.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.reach_QListWidget_2.itemSelectionChanged.connect(self.reach_hdf5_change_2)
        reach_layout_2 = QVBoxLayout()
        reach_layout_2.addWidget(reach_label_2)
        reach_layout_2.addWidget(self.reach_QListWidget_2)

        # units_2
        units_label_2 = QLabel(self.tr('unit(s)'))
        self.units_QListWidget_2 = QListWidget()
        self.units_QListWidget_2.itemSelectionChanged.connect(self.enable_disable_pushbutton)
        self.units_QListWidget_2.setSelectionMode(QAbstractItemView.ExtendedSelection)
        units_layout_2 = QVBoxLayout()
        units_layout_2.addWidget(units_label_2)
        units_layout_2.addWidget(self.units_QListWidget_2)
        selection_group_2 = QGroupBox(self.tr("Second"))
        selection_group_2.setStyleSheet("QGroupBox { font-weight: normal; } ")
        selection_layout_2 = QHBoxLayout()
        selection_layout_2.addLayout(file_selection_layout_2)
        selection_layout_2.addLayout(reach_layout_2)
        selection_layout_2.addLayout(units_layout_2)
        selection_group_2.setLayout(selection_layout_2)

        # comp
        comp_layout = QHBoxLayout()
        comp_layout.addWidget(selection_group_1)
        comp_layout.addWidget(selection_group_2)

        # comp_run
        self.comp_choice_all_radio = QRadioButton(self.tr("All possibilities"))
        self.comp_choice_all_radio.setChecked(True)
        self.comp_choice_all_radio.toggled.connect(self.mod_change)
        self.comp_choice_same_radio = QRadioButton(self.tr("All same"))
        filename_label = QLabel(self.tr("Output filename :"))
        self.filename_lineedit = QLineEdit()
        self.filename_lineedit.textChanged.connect(self.enable_disable_pushbutton)
        self.run_comp_pushbutton = QPushButton(self.tr("run"))
        change_button_color(self.run_comp_pushbutton, "#47B5E6")
        self.run_comp_pushbutton.clicked.connect(self.compare)
        self.run_comp_pushbutton.setEnabled(False)
        # self.run_comp_pushbutton.setStyleSheet("background-color: #47B5E6; color: black")

        comp_run_layout = QGridLayout()
        comp_run_layout.addWidget(self.comp_choice_all_radio, 0, 0, Qt.AlignLeft)
        comp_run_layout.addWidget(self.comp_choice_same_radio, 1, 0, Qt.AlignLeft)
        comp_run_layout.addWidget(filename_label, 0, 1, Qt.AlignLeft)
        comp_run_layout.addWidget(self.filename_lineedit, 1, 1, Qt.AlignLeft)
        comp_run_layout.addWidget(self.run_comp_pushbutton, 2, 1, Qt.AlignLeft)
        comp_run_layout.setAlignment(Qt.AlignRight)

        # general
        general_layout = QVBoxLayout()
        general_layout.addLayout(comp_layout)
        general_layout.addLayout(comp_run_layout)

        self.mod_change(None)

        self.setLayout(general_layout)

    def update_gui(self):
        hs_names = get_filename_hs(os.path.join(self.path_prj, "hdf5"))

        # 1
        # self.file_selection_listwidget_1.blockSignals(True)
        self.file_selection_listwidget_1.clear()
        if hs_names:
            self.file_selection_listwidget_1.addItems(hs_names)
        # self.file_selection_listwidget_1.blockSignals(False)

        # 2
        # self.file_selection_listwidget_2.blockSignals(True)
        self.file_selection_listwidget_2.clear()
        if hs_names:
            self.file_selection_listwidget_2.addItems(hs_names)
        # self.file_selection_listwidget_2.blockSignals(False)

    def names_hdf5_change_1(self):
        self.reach_QListWidget_1.clear()
        self.units_QListWidget_1.clear()
        selection_file = self.file_selection_listwidget_1.selectedItems()
        if selection_file:
            hdf5name = selection_file[0].text()
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.get_hdf5_attributes(close_file=True)
            # check reach
            self.reach_QListWidget_1.addItems(hdf5.data_2d.reach_list)

    def names_hdf5_change_2(self):
        self.reach_QListWidget_2.clear()
        self.units_QListWidget_2.clear()
        selection_file = self.file_selection_listwidget_2.selectedItems()
        if selection_file:
            hdf5name = selection_file[0].text()
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.get_hdf5_attributes(close_file=True)
            # check reach
            self.reach_QListWidget_2.addItems(hdf5.data_2d.reach_list)

    def reach_hdf5_change_1(self):
        selection_file = self.file_selection_listwidget_1.selectedItems()
        selection_reach = self.reach_QListWidget_1.selectedItems()
        self.units_QListWidget_1.clear()
        # one file selected
        if len(selection_reach) == 1:
            hdf5name = selection_file[0].text()
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.get_hdf5_attributes(close_file=True)
            # add units
            for item_text in hdf5.data_2d.unit_list[self.reach_QListWidget_1.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget_1.addItem(item)

    def reach_hdf5_change_2(self):
        selection_file = self.file_selection_listwidget_2.selectedItems()
        selection_reach = self.reach_QListWidget_2.selectedItems()
        self.units_QListWidget_2.clear()
        # one file selected
        if len(selection_reach) == 1:
            hdf5name = selection_file[0].text()
            hdf5 = Hdf5Management(self.path_prj, hdf5name, new=False, edit=False)
            hdf5.get_hdf5_attributes(close_file=True)
            # add units
            for item_text in hdf5.data_2d.unit_list[self.reach_QListWidget_2.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget_2.addItem(item)

    def enable_disable_pushbutton(self):
        selection_1 = self.units_QListWidget_1.selectedItems()
        selection_2 = self.units_QListWidget_2.selectedItems()
        filename_output = self.filename_lineedit.text()
        if (selection_1 or selection_2) and filename_output:
            self.run_comp_pushbutton.setEnabled(True)
        else:
            self.run_comp_pushbutton.setEnabled(False)

    def mod_change(self, _):
        if self.comp_choice_all_radio.isChecked():
            self.filename_lineedit.setText(os.path.splitext(self.comp_filename)[0] + "_poss.txt")
        else:
            self.filename_lineedit.setText(os.path.splitext(self.comp_filename)[0] + "_same.txt")

    def compare(self):
        # hdf5
        hdf5name_1 = self.file_selection_listwidget_1.selectedItems()[0].text()
        hdf5name_2 = self.file_selection_listwidget_2.selectedItems()[0].text()

        # reach
        reach_index_list_1 = [element.row() for element in self.reach_QListWidget_1.selectedIndexes()]
        reach_index_list_2 = [element.row() for element in self.reach_QListWidget_2.selectedIndexes()]

        # units
        unit_index_list_1 = [element.row() for element in self.units_QListWidget_1.selectedIndexes()]
        unit_index_list_2 = [element.row() for element in self.units_QListWidget_2.selectedIndexes()]

        # load_hs_and_compare
        self.p = Process(target=load_hs_and_compare,
                         args=(hdf5name_1, reach_index_list_1, unit_index_list_1,
                               hdf5name_2, reach_index_list_2, unit_index_list_2,
                               self.comp_choice_all_radio.isChecked(),
                               self.filename_lineedit.text(),
                               self.path_prj))
        self.p.name = "hydrosignature comparison"
        self.p.start()
        self.p.join()
        self.send_log.emit(self.tr("Hydrosignature comparison finished."))



