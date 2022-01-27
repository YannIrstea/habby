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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QLabel, QListWidget, QAbstractItemView, QMessageBox, QFrame, QGridLayout, QVBoxLayout, \
    QSizePolicy, QScrollArea, QListWidgetItem, QPushButton, QFileDialog

from src.process_manager_mod import MyProcessManager
from src.mesh_manager_mod import mesh_manager_from_file
from src.hdf5_mod import get_filename_by_type_physic, Hdf5Management
from src.project_properties_mod import load_project_properties, save_project_properties
from src_GUI.dev_tools_GUI import QGroupBoxCollapsible
from src_GUI.process_manager_GUI import ProcessProgLayout


class MeshManagerTab(QScrollArea):
    """
    Tool tab
    """
    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.tab_name = "mesh_manager"
        self.tab_title = self.tr("Mesh manager")
        self.tooltip_str = self.tr("Manage mesh")
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
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
        self.computing_group.setChecked(True)

        # vertical layout
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addWidget(self.computing_group)
        global_layout.addStretch()
        self.setWidget(tools_frame)

    def refresh_gui(self):
        # computing_group
        self.computing_group.update_gui()

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
        self.project_properties = load_project_properties(self.path_prj)
        self.setTitle(title)
        self.init_ui()
        self.msg2 = QMessageBox()
        self.mesh_manager_file = self.read_attribute_xml("mesh_manager_file")
        self.read_mesh_manager_file(self.mesh_manager_file)
        # process_manager
        self.process_manager = MyProcessManager("mesh_manager")

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

        mesh_manager_file = QLabel(self.tr("Mesh manager file (.txt)"))
        self.mesh_manager_filename_label = QLabel("")
        self.mesh_manager_file_select_pushbutton = QPushButton("...")
        self.mesh_manager_file_select_pushbutton.clicked.connect(self.select_mesh_manager_file_dialog)


        # progress_layout
        self.progress_layout = ProcessProgLayout(self.compute,
                                                 send_log=self.send_log,
                                                 process_type="mesh_manager",
                                                 send_refresh_filenames=self.send_refresh_filenames)

        file_selection_layout = QGridLayout()
        file_selection_layout.addWidget(file_selection_label, 0, 0)
        file_selection_layout.addWidget(self.file_selection_listwidget, 1, 0)
        file_selection_layout.addWidget(self.scrollbar, 1, 1)
        file_selection_layout.setColumnStretch(0, 30)
        file_selection_layout.setColumnStretch(1, 1)

        grid_layout = QGridLayout()
        grid_layout.addWidget(mesh_manager_file, 0, 0, Qt.AlignLeft)
        grid_layout.addWidget(self.mesh_manager_filename_label, 0, 1, Qt.AlignLeft)
        grid_layout.addWidget(self.mesh_manager_file_select_pushbutton, 0, 2, Qt.AlignLeft)
        grid_layout.addLayout(self.progress_layout, 1, 0, 1, 3)

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
        if names:
            for name in names:
                # check
                try:
                    hdf5 = Hdf5Management(self.path_prj, name, new=False, edit=False)
                    hdf5.get_hdf5_attributes(close_file=True)
                    item_name = QListWidgetItem()
                    item_name.setText(name)
                    self.file_selection_listwidget.addItem(item_name)
                    if name in selected_file_names:
                        item_name.setSelected(True)
                    if True:  #TODO : sort files (hdf5 attributes available for HRR) .hyd, one whole profile for all units, ...
                        pass
                    else:
                        pass
                except:
                    self.send_log.emit(self.tr("Error: " + name + " file seems to be corrupted. Delete it with HABBY or manually."))

        self.file_selection_listwidget.blockSignals(False)
        # preselection if one
        if self.file_selection_listwidget.count() == 1:
            self.file_selection_listwidget.selectAll()

    def change_scroll_position(self, index):
        self.file_selection_listwidget.verticalScrollBar().setValue(index)

    def names_hdf5_change(self):
        selection = self.file_selection_listwidget.selectedItems()
        self.progress_layout.progress_bar.setValue(0.0)
        self.progress_layout.progress_label.setText(
            "{0:.0f}/{1:.0f}".format(0.0, len(selection)))
        if selection:
            self.progress_layout.run_stop_button.setEnabled(True)
        else:
            self.progress_layout.run_stop_button.setEnabled(False)

    def read_mesh_manager_file(self, mesh_manager_file):
        if os.path.exists(mesh_manager_file):
            self.mesh_manager_description, warnings_list = mesh_manager_from_file(mesh_manager_file)
            if warnings_list:
                for warning in warnings_list:
                    self.send_log.emit(warning)
            if self.mesh_manager_description["mesh_manager_data"] is None:
                self.send_log.emit(self.tr("Error: Mesh manager file : ") + os.path.basename(mesh_manager_file) + self.tr(" is not valid."))
                self.progress_layout.run_stop_button.setEnabled(False)
            else:
                self.mesh_manager_filename_label.setText(os.path.basename(mesh_manager_file))
                if self.file_selection_listwidget.selectedItems():
                    self.progress_layout.run_stop_button.setEnabled(True)
        else:
            self.progress_layout.run_stop_button.setEnabled(False)

        self.progress_layout.progress_bar.setValue(0.0)
        self.progress_layout.progress_label.setText(
            "{0:.0f}/{1:.0f}".format(0.0, len(self.file_selection_listwidget.selectedItems())))

    def select_mesh_manager_file_dialog(self):
        self.mesh_manager_file = self.read_attribute_xml("mesh_manager_file")
        # get last path
        if self.mesh_manager_file != self.path_prj and self.mesh_manager_file != "":
            model_path = self.mesh_manager_file  # path spe
        elif self.read_attribute_xml("path_last_file_loaded") != self.path_prj and self.read_attribute_xml(
                "path_last_file_loaded") != "":
            model_path = self.read_attribute_xml("path_last_file_loaded")  # path last
        else:
            model_path = self.path_prj  # path proj

        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select a mesh manager file"),
                                                  model_path, self.tr("Text files") + " (*.txt)")
        if filename:
            self.pathfile = filename  # source file path
            self.save_xml("mesh_manager_file")
            self.read_mesh_manager_file(filename)
            self.mesh_manager_file = self.read_attribute_xml("mesh_manager_file")

    def read_attribute_xml(self, att_here):
        """
        A function to read the text of an attribute in the xml project file.

        :param att_here: the attribute name (string).
        """
        data = ''

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            if att_here in {"path_last_file_loaded"}:
                data = load_project_properties(self.path_prj)[att_here]
            else:
                try:
                    data = load_project_properties(self.path_prj)[att_here]
                except KeyError:
                    self.save_xml("mesh_manager_file")
                    data = load_project_properties(self.path_prj)[att_here]
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
            self.project_properties[attr] = self.pathfile  # change value
            save_project_properties(self.path_prj, self.project_properties)  # save_project_properties

    def compute(self):
        if len(self.file_selection_listwidget.selectedItems()) > 0:
            mesh_manager_description = self.mesh_manager_description
            mesh_manager_description["hdf5_name_list"] = [selection_el.text() for selection_el in
                              self.file_selection_listwidget.selectedItems()]

            # for hdf5_file in mesh_manager_description["hdf5_name_list"]:
            #     hdf5_1 = Hdf5Management(self.path_prj, hdf5_file, new=False, edit=False)
            #     hdf5_1.load_hdf5(whole_profil=False)
            #     if hdf5_1.data_2d.hvum.hdf5_and_computable_list.habs():
            #         self.msg2.setIcon(QMessageBox.Warning)
            #         self.msg2.setWindowTitle(self.tr("HSI data in ") + hdf5_1.filename[:-4] + "_MM" + hdf5_1.extension + ".")
            #         self.msg2.setText(self.tr("If computing, existing HSI data will be removed in ") + hdf5_1.filename[:-4] + "_MM" + hdf5_1.extension + ".\n"+
            #                           self.tr("Do you really want to continue computing ?"))
            #         self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            #         res = self.msg2.exec_()
            #
            #         # cancel
            #         if res == QMessageBox.No:
            #             return
            #         if res == QMessageBox.Yes:
            #             break

            self.progress_layout.process_manager.set_mesh_manager(self.path_prj,
                                                                  mesh_manager_description,
                                                                  self.project_properties)

            # start thread
            self.progress_layout.start_process()

    def stop_compute(self):
        # stop_by_user
        self.process_manager.stop_by_user()
