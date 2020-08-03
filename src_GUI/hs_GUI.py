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
from multiprocessing import Process, Value, Queue

from PyQt5.QtCore import pyqtSignal, Qt, QAbstractTableModel, QRect, QPoint, QSize, QTimer
from PyQt5.QtGui import QStandardItemModel, QPixmap, QIcon, QPalette, QColor
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, QTableWidget, QWidget, \
    QComboBox, QMessageBox, QFrame, QHeaderView, QLineEdit, QGridLayout, QFileDialog, QStyleOptionTab, \
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QTableView, QTabBar, QStylePainter, QStyle, \
    QCheckBox, QListWidgetItem, QRadioButton, QListView

import src.hydraulic_process_mod
from src import hydrosignature
from src.tools_mod import QGroupBoxCollapsible
from src.hydraulic_process_mod import MyProcessList
from src import hdf5_mod
from src import plot_mod
from src import tools_mod
from src.project_properties_mod import load_project_properties, save_project_properties
from src import hydrosignature
from src_GUI.tools_GUI import change_button_color


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
        self.computing_group.update_gui()

        # visual_group
        self.visual_group.update_gui()

        # compare_group
        self.compare_group.update_gui()


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
        self.timer = QTimer()
        self.timer.timeout.connect(self.show_prog)
        self.running_time = 0
        self.p = Process(target=None)  # second process
        self.q = Queue()
        self.progress_value = Value("i", 0)
        self.project_preferences = load_project_properties(self.path_prj)
        self.setTitle(title)
        self.init_ui()

    def init_ui(self):
        # file_selection
        file_selection_label = QLabel(self.tr("Select a 2D mesh file :"))
        self.file_selection_listwidget = QListWidget()
        self.file_selection_listwidget.setSelectionMode(QAbstractItemView.SingleSelection)
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
        self.input_class_pushbutton = QPushButton(self.tr("Select file"))
        self.input_class_pushbutton.clicked.connect(self.select_input_class_dialog)
        hs_export_txt_label = QLabel(self.tr("Export results (.txt)"))
        self.hs_export_txt_checkbox = QCheckBox()
        hs_export_mesh_label = QLabel(self.tr("Export mesh results (.hyd or .hab)"))
        self.hs_export_mesh_checkbox = QCheckBox()
        self.computation_pushbutton = QPushButton(self.tr("run"))
        change_button_color(self.computation_pushbutton, "#47B5E6")
        self.computation_pushbutton.clicked.connect(self.compute)
        self.computation_pushbutton.setEnabled(False)

        grid_layout = QGridLayout()
        grid_layout.addWidget(input_class_label, 2, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.input_class_filename, 2, 1, Qt.AlignLeft)
        grid_layout.addWidget(self.input_class_pushbutton, 2, 2, Qt.AlignLeft)
        grid_layout.addWidget(hs_export_txt_label, 3, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.hs_export_txt_checkbox, 3, 1, Qt.AlignLeft)
        grid_layout.addWidget(hs_export_mesh_label, 4, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.hs_export_mesh_checkbox, 4, 1, Qt.AlignLeft)
        grid_layout.addWidget(self.computation_pushbutton, 5, 2, Qt.AlignLeft)

        grid_layout.setColumnStretch(0, 2)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 1)
        grid_layout.setAlignment(Qt.AlignRight)

        general_layout = QVBoxLayout()
        general_layout.addLayout(file_selection_layout)
        general_layout.addLayout(grid_layout)

        self.setLayout(general_layout)

    def update_gui(self):
        # computing_group
        hyd_names = hdf5_mod.get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
        hab_names = hdf5_mod.get_filename_by_type_physic("habitat", os.path.join(self.path_prj, "hdf5"))
        names = hyd_names + hab_names
        self.file_selection_listwidget.blockSignals(True)
        self.file_selection_listwidget.clear()
        self.hs_computed_listwidget.blockSignals(True)
        self.hs_computed_listwidget.clear()
        if names:
            self.file_selection_listwidget.addItems(names)
            for name in names:
                item = QListWidgetItem()
                item.setText("")
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                hdf5 = hdf5_mod.Hdf5Management(self.path_prj, name)
                hdf5.open_hdf5_file(False)
                if hdf5.hydrosignature_calculated:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.hs_computed_listwidget.addItem(item)
                item.setTextAlignment(Qt.AlignCenter)

        self.file_selection_listwidget.blockSignals(False)
        self.hs_computed_listwidget.blockSignals(False)
        input_class_file_info = self.read_attribute_xml("HS_input_class")
        self.read_input_class(os.path.join(input_class_file_info["path"], input_class_file_info["file"]))

    def change_scroll_position(self, index):
        self.file_selection_listwidget.verticalScrollBar().setValue(index)
        self.hs_computed_listwidget.verticalScrollBar().setValue(index)

    def read_input_class(self, input_class_file):
        if os.path.exists(input_class_file):
            try:
                self.classhv = hydrosignature.hydraulic_class_from_file(input_class_file)
                self.input_class_filename.setText(os.path.basename(input_class_file))
                if self.file_selection_listwidget.selectedItems():
                    self.computation_pushbutton.setEnabled(True)
            except FileNotFoundError:
                self.send_log.emit('Error: ' + self.tr('Selected hydraulic input class file is not valid.'))
        else:
            self.computation_pushbutton.setEnabled(False)

    def names_hdf5_change(self):
        selection = self.file_selection_listwidget.selectedItems()
        if selection:
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, selection[0].text())
            hdf5.open_hdf5_file(False)
            # enable run button
            if self.input_class_filename.text():
                self.computation_pushbutton.setEnabled(True)
            else:
                self.computation_pushbutton.setEnabled(False)
        else:
            self.computation_pushbutton.setEnabled(False)

    def select_input_class_dialog(self):
        input_class_file_info = self.read_attribute_xml("HS_input_class")
        # get last path
        if input_class_file_info["path"] != self.path_prj and input_class_file_info["path"] != "":
            model_path = input_class_file_info["path"]  # path spe
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
            self.project_preferences = load_project_properties(self.path_prj)  # load_project_properties
            self.project_preferences["path_last_file_loaded"] = self.pathfile  # change value
            self.project_preferences[attr]["file"] = self.namefile  # change value
            self.project_preferences[attr]["path"] = self.pathfile  # change value
            save_project_properties(self.path_prj, self.project_preferences)  # save_project_properties

    def compute(self):

        # for error management and figures
        self.timer.start(100)

        self.nativeParentWidget().progress_bar.setValue(0)
        self.nativeParentWidget().progress_bar.setRange(0, 100)
        self.nativeParentWidget().progress_bar.setVisible(True)

        hydrosignature_description = dict(hs_export_mesh=self.hs_export_mesh_checkbox.isChecked(),
                                          hdf5_name=self.file_selection_listwidget.currentItem().text(),
                                          hs_export_txt=self.hs_export_mesh_checkbox.isChecked(),
                                          classhv=self.classhv)
        self.q = Queue()
        self.progress_value = Value("d", 0)
        self.p = Process(target=src.hydraulic_process_mod.hydrosignature_process,
                         args=(hydrosignature_description,
                               self.progress_value,
                               self.q,
                               False,
                               self.project_preferences))
        self.p.name = "hydrosignature computing"
        self.p.start()

    def show_prog(self):
        """
        This function is call regularly by the methods which have a second thread (so moslty the function
        to load the hydrological data). To call this function regularly, the variable self.timer of QTimer type is used.
        The variable self.timer is connected to this function in the initiation of SubHydroW() and so in the initiation
        of all class which inherits from SubHydroW().

        This function just wait while the thread is alive. When it has terminated, it creates the figure and the error
        messages.
        """
        # RUNNING
        if self.p.is_alive():
            self.running_time += 0.100  # this is useful for GUI to update the running, should be logical with self.Timer()
            # get the language
            self.nativeParentWidget().kill_process.setVisible(True)

            self.send_log.emit(self.tr("Process 'hydrosignature' is alive and run since ") + str(round(self.running_time)) + " sec")
            self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))

        else:
            # FINISH (but can have known errors)
            if not self.q.empty():
                # manage error
                self.timer.stop()
                queue_back = self.q.get()
                self.mystdout = queue_back

            # CLEANING GUI
            if not self.p.is_alive() and self.q.empty():
                self.timer.stop()
                self.nativeParentWidget().kill_process.setVisible(False)
                self.running_time = 0

                # CRASH
                if self.p.exitcode == 1:
                    self.send_log.emit(self.tr("Error : Process crashed !! Restart HABBY. Retry. If same, contact the HABBY team."))



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
        self.reach_QListWidget.itemSelectionChanged.connect(self.reach_hdf5_change)
        reach_layout = QVBoxLayout()
        reach_layout.addWidget(reach_label)
        reach_layout.addWidget(self.reach_QListWidget)

        # units
        units_label = QLabel(self.tr('unit(s)'))
        self.units_QListWidget = QListWidget()
        units_layout = QVBoxLayout()
        units_layout.addWidget(units_label)
        units_layout.addWidget(self.units_QListWidget)

        # axe
        axe_label = QLabel(self.tr("Axe orientation :"))
        self.axe_mod_1_radio = QRadioButton()
        self.axe_mod_1_radio.setChecked(True)  # TODO: save in json default and last choice (to be loaded)
        self.axe_mod_1_radio.setIcon(QIcon(r"translation/axe_mod_1.PNG"))
        self.axe_mod_1_radio.setIconSize(QSize(75, 75))
        self.axe_mod_1_radio.clicked.connect(self.change_axe_mod)

        self.axe_mod_2_radio = QRadioButton()
        self.axe_mod_2_radio.setIcon(QIcon(r"translation/axe_mod_2.PNG"))
        self.axe_mod_2_radio.setIconSize(QSize(75, 75))
        self.axe_mod_2_radio.clicked.connect(self.change_axe_mod)

        self.axe_mod_3_radio = QRadioButton()
        self.axe_mod_3_radio.setIcon(QIcon(r"translation/axe_mod_3.PNG"))
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
        self.input_class_h_lineedit = QLineEdit("")
        self.input_class_v_lineedit = QLineEdit("")
        self.input_class_plot_button = QPushButton(self.tr("Show"))
        self.input_class_plot_button.setStyleSheet("background-color: #47B5E6; color: black")
        input_class_layout = QGridLayout()
        input_class_layout.addWidget(input_class_label, 0, 0)
        input_class_layout.addWidget(self.input_class_h_lineedit, 1, 0)
        input_class_layout.addWidget(self.input_class_v_lineedit, 2, 0)
        input_class_layout.addWidget(self.input_class_plot_button, 1, 1, 2, 1)  # from row, from column, nb row, nb column

        # result
        result_label = QLabel(self.tr("Result :"))
        self.result_tableview = QTableView(self)
        self.result_tableview.setFrameShape(QFrame.NoFrame)
        self.result_tableview.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.result_tableview.verticalHeader().setVisible(False)
        self.result_tableview.horizontalHeader().setVisible(False)
        self.result_plot_button = QPushButton(self.tr("Show"))
        self.result_plot_button.setStyleSheet("background-color: #47B5E6; color: black")
        result_layout = QGridLayout()
        result_layout.addWidget(result_label, 0, 0)
        result_layout.addWidget(self.result_tableview, 1, 0)
        result_layout.addWidget(self.result_plot_button, 1, 1)

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
        hs_names = hdf5_mod.get_filename_hs(os.path.join(self.path_prj, "hdf5"))
        self.file_selection_listwidget.blockSignals(True)
        self.file_selection_listwidget.clear()
        if hs_names:
            self.file_selection_listwidget.addItems(hs_names)
        self.file_selection_listwidget.blockSignals(False)

    def names_hdf5_change(self):
        self.reach_QListWidget.clear()
        self.units_QListWidget.clear()
        selection = self.file_selection_listwidget.selectedItems()
        if selection:
            # read
            hdf5name = selection[0].text()
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)
            # check reach
            self.reach_QListWidget.addItems(hdf5.reach_name)

            self.input_result_group.show()
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
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)

            # add units
            for item_text in hdf5.units_name[self.reach_QListWidget.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget.addItem(item)

    def change_axe_mod(self):
        if self.axe_mod_1_radio.isChecked():
            self.axe_mod_choosen = 1
        elif self.axe_mod_2_radio.isChecked():
            self.axe_mod_choosen = 2
        elif self.axe_mod_3_radio.isChecked():
            self.axe_mod_choosen = 3
        print("axe_mod_choosen", self.axe_mod_choosen)


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
        # file_selection_1
        file_selection_label_1 = QLabel(self.tr("HS files :"))
        self.file_selection_listwidget_1 = QListWidget()
        self.file_selection_listwidget_1.itemSelectionChanged.connect(self.names_hdf5_change_1)
        file_selection_layout_1 = QVBoxLayout()
        file_selection_layout_1.addWidget(file_selection_label_1)
        file_selection_layout_1.addWidget(self.file_selection_listwidget_1)

        # reach_1
        reach_label_1 = QLabel(self.tr('reach(s)'))
        self.reach_QListWidget_1 = QListWidget()
        self.reach_QListWidget_1.itemSelectionChanged.connect(self.reach_hdf5_change_1)
        reach_layout_1 = QVBoxLayout()
        reach_layout_1.addWidget(reach_label_1)
        reach_layout_1.addWidget(self.reach_QListWidget_1)

        # units_1
        units_label_1 = QLabel(self.tr('unit(s)'))
        self.units_QListWidget_1 = QListWidget()
        units_layout_1 = QVBoxLayout()
        units_layout_1.addWidget(units_label_1)
        units_layout_1.addWidget(self.units_QListWidget_1)
        selection_group_1 = QGroupBox(self.tr("First"))
        selection_layout_1 = QHBoxLayout()
        selection_layout_1.addLayout(file_selection_layout_1)
        selection_layout_1.addLayout(reach_layout_1)
        selection_layout_1.addLayout(units_layout_1)
        selection_group_1.setLayout(selection_layout_1)

        # file_selection_2
        file_selection_label_2 = QLabel(self.tr("HS files :"))
        self.file_selection_listwidget_2 = QListWidget()
        self.file_selection_listwidget_2.itemSelectionChanged.connect(self.names_hdf5_change_2)
        file_selection_layout_2 = QVBoxLayout()
        file_selection_layout_2.addWidget(file_selection_label_2)
        file_selection_layout_2.addWidget(self.file_selection_listwidget_2)

        # reach_2
        reach_label_2 = QLabel(self.tr('reach(s)'))
        self.reach_QListWidget_2 = QListWidget()
        self.reach_QListWidget_2.itemSelectionChanged.connect(self.reach_hdf5_change_2)
        reach_layout_2 = QVBoxLayout()
        reach_layout_2.addWidget(reach_label_2)
        reach_layout_2.addWidget(self.reach_QListWidget_2)

        # units_2
        units_label_2 = QLabel(self.tr('unit(s)'))
        self.units_QListWidget_2 = QListWidget()
        units_layout_2 = QVBoxLayout()
        units_layout_2.addWidget(units_label_2)
        units_layout_2.addWidget(self.units_QListWidget_2)
        selection_group_2 = QGroupBox(self.tr("Second"))
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
        self.comp_choice_same_radio = QRadioButton(self.tr("All same"))
        filename_label = QLabel(self.tr("Output filename :"))
        self.filename_lineedit = QLineEdit(self.tr('HS_comp.txt'))
        self.run_comp_pushbutton = QPushButton(self.tr("run"))
        self.run_comp_pushbutton.setStyleSheet("background-color: #47B5E6; color: black")

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

        self.setLayout(general_layout)

    def update_gui(self):
        hs_names = hdf5_mod.get_filename_hs(os.path.join(self.path_prj, "hdf5"))

        # 1
        self.file_selection_listwidget_1.blockSignals(True)
        self.file_selection_listwidget_1.clear()
        if hs_names:
            self.file_selection_listwidget_1.addItems(hs_names)
        self.file_selection_listwidget_1.blockSignals(False)

        # 2
        self.file_selection_listwidget_2.blockSignals(True)
        self.file_selection_listwidget_2.clear()
        if hs_names:
            self.file_selection_listwidget_2.addItems(hs_names)
        self.file_selection_listwidget_2.blockSignals(False)

    def names_hdf5_change_1(self):
        self.reach_QListWidget_1.clear()
        self.units_QListWidget_1.clear()
        selection = self.file_selection_listwidget_1.selectedItems()
        if selection:
            # read
            hdf5name = selection[0].text()
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)
            # check reach
            self.reach_QListWidget_1.addItems(hdf5.reach_name)

            # self.input_result_group.show()
        # else:
            # self.input_result_group.hide()

    def names_hdf5_change_2(self):
        self.reach_QListWidget_2.clear()
        self.units_QListWidget_2.clear()
        selection = self.file_selection_listwidget_2.selectedItems()
        if selection:
            # read
            hdf5name = selection[0].text()
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)
            # check reach
            self.reach_QListWidget_2.addItems(hdf5.reach_name)

        #     self.input_result_group.show()
        # else:
        #     self.input_result_group.hide()

    def reach_hdf5_change_1(self):
        selection_file = self.file_selection_listwidget_1.selectedItems()
        selection_reach = self.reach_QListWidget_1.selectedItems()
        self.units_QListWidget_1.clear()
        # one file selected
        if len(selection_reach) == 1:
            hdf5name = selection_file[0].text()

            # create hdf5 class
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)

            # add units
            for item_text in hdf5.units_name[self.reach_QListWidget_1.currentRow()]:
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

            # create hdf5 class
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file(False)

            # add units
            for item_text in hdf5.units_name[self.reach_QListWidget_2.currentRow()]:
                item = QListWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignRight)
                self.units_QListWidget_2.addItem(item)

