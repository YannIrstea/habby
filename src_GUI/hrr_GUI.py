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
    QSizePolicy, QScrollArea, QListWidgetItem

from src.process_manager_mod import MyProcessManager
from src.hdf5_mod import get_filename_by_type_physic, Hdf5Management
from src.project_properties_mod import load_project_properties, save_project_properties
from src_GUI.dev_tools_GUI import QGroupBoxCollapsible
from src_GUI.process_manager_GUI import ProcessProgLayout


class HrrTab(QScrollArea):
    """
    Tool tab
    """
    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.tab_name = "hrr"
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
        self.classhv = None
        self.project_properties = load_project_properties(self.path_prj)
        self.setTitle(title)
        self.init_ui()
        # process_manager
        self.process_manager = MyProcessManager("hrr")

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

        file_selection_layout = QGridLayout()
        file_selection_layout.addWidget(file_selection_label, 0, 0)
        file_selection_layout.addWidget(self.file_selection_listwidget, 1, 0)
        file_selection_layout.addWidget(self.scrollbar, 1, 2)
        file_selection_layout.setColumnStretch(0, 30)
        file_selection_layout.setColumnStretch(1, 1)


        """ progress layout """
        # progress_layout
        self.progress_layout = ProcessProgLayout(self.compute,
                                                 send_log=self.send_log,
                                                 process_type="hrr",
                                                 send_refresh_filenames=self.send_refresh_filenames)

        grid_layout = QGridLayout()
        grid_layout.addLayout(self.progress_layout, 5, 0, 1, 3)
        grid_layout.setAlignment(Qt.AlignRight)

        general_layout = QVBoxLayout()
        general_layout.addLayout(file_selection_layout)
        general_layout.addLayout(grid_layout)

        self.setLayout(general_layout)

    def update_gui(self):
        selected_file_names = [selection_el.text() for selection_el in self.file_selection_listwidget.selectedItems()]
        # computing_group
        hyd_names = get_filename_by_type_physic("hydraulic", os.path.join(self.path_prj, "hdf5"))
        names = hyd_names
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

    def compute(self):
        if len(self.file_selection_listwidget.selectedItems()) > 0:
            hrr_description = dict(deltatlist=[],
                              hdf5_name_list=[selection_el.text() for selection_el in
                                              self.file_selection_listwidget.selectedItems()])

            self.progress_layout.process_manager.set_hrr_hdf5_mode(self.path_prj,
                                                                  hrr_description,
                                                                  self.project_properties)

            # start thread
            self.progress_layout.start_process()

    def stop_compute(self):
        # stop_by_user
        self.process_manager.stop_by_user()
