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
from src_GUI.Interpolation_GUI import InterpolationTab
from src_GUI.hydrosignature_GUI import HsTab
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

        self.sub_tabwidget = QTabWidget(self)

        # interpolation group
        self.interpolation_tab = InterpolationTab(self.path_prj, self.name_prj, self.send_log)

        # hydrosignature tab
        self.hs_tab = HsTab(self.path_prj, self.name_prj, self.send_log)

        # other tool
        self.newtool_tab = OtherToolToCreateTab(self.path_prj, self.name_prj, self.send_log)

        self.sub_tabwidget.insertTab(1, self.interpolation_tab, self.tr("Interpolation"))
        self.sub_tabwidget.insertTab(2, self.hs_tab, self.tr("Hydrosignature"))
        self.sub_tabwidget.insertTab(3, self.newtool_tab, self.tr("New tools coming soon"))

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addWidget(self.sub_tabwidget)

        # refresh habi filenames
        self.refresh_gui()

    def refresh_gui(self):
        for tab_num in range(self.sub_tabwidget.count()):
            self.sub_tabwidget.widget(tab_num).refresh_gui()

    def kill_process(self):
        for tab_num in range(self.sub_tabwidget.count()):
            self.sub_tabwidget.widget(tab_num).kill_process()