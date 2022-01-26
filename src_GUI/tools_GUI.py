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
from PyQt5.QtWidgets import QMessageBox, QFrame, QTabWidget,\
    QVBoxLayout, QSizePolicy, QScrollArea

from src import hdf5_mod
from src_GUI.interpolation_GUI import InterpolationTab
from src_GUI.hydrosignature_GUI import HsTab
from src_GUI.hrr_GUI import HrrTab
from src_GUI.mesh_manager_GUI import MeshManagerTab
from src_GUI.new_tool_tab_to_create_GUI import OtherToolToCreateTab


class ToolsTab(QScrollArea):
    """
    This class contains the tab with Graphic production biological information (the curves of preference).
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "tools"
        self.tab_position = 5
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
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

        self.tools_tabwidget = QTabWidget(self)

        # interpolation group
        self.interpolation_tab = InterpolationTab(self.path_prj, self.name_prj, self.send_log)

        # hydrosignature tab
        self.hs_tab = HsTab(self.path_prj, self.name_prj, self.send_log)

        # hrr_tab
        self.mesh_manager_tab = MeshManagerTab(self.path_prj, self.name_prj, self.send_log)

        # hrr_tab
        self.hrr_tab = HrrTab(self.path_prj, self.name_prj, self.send_log)

        # other tool
        self.newtool_tab = OtherToolToCreateTab(self.path_prj, self.name_prj, self.send_log)

        self.tools_tabwidget.insertTab(1, self.interpolation_tab, self.interpolation_tab.tab_title)
        # self.tools_tabwidget.setTabToolTip(1, self.interpolation_tab.tooltip_str)
        self.tools_tabwidget.insertTab(2, self.hs_tab, self.hs_tab.tab_title)
        # self.tools_tabwidget.setTabToolTip(2, self.hs_tab.tooltip_str)
        self.tools_tabwidget.insertTab(3, self.mesh_manager_tab, self.mesh_manager_tab.tab_title)
        # self.tools_tabwidget.setTabToolTip(3, self.mesh_manager_tab.tooltip_str)
        self.tools_tabwidget.insertTab(4, self.hrr_tab, self.hrr_tab.tab_title)
        # self.tools_tabwidget.setTabToolTip(4, self.hrr_tab.tooltip_str)
        self.tools_tabwidget.insertTab(5, self.newtool_tab, self.newtool_tab.tab_title)
        # self.tools_tabwidget.setTabToolTip(5, self.newtool_tab.tooltip_str)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addWidget(self.tools_tabwidget)

        # refresh habi filenames
        self.refresh_gui()

    def refresh_gui(self):
        for tab_num in range(self.tools_tabwidget.count()):
            self.tools_tabwidget.widget(tab_num).refresh_gui()

    def kill_process(self):
        for tab_num in range(self.tools_tabwidget.count()):
            self.tools_tabwidget.widget(tab_num).kill_process()