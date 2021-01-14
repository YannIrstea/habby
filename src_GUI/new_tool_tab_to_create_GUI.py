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
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollArea, QPushButton, QVBoxLayout, QSizePolicy, QFrame

from src_GUI.dev_tools_GUI import QGroupBoxCollapsible


class OtherToolToCreateTab(QScrollArea):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.init_ui()

    def init_ui(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

        # global_frame
        global_frame = QFrame()
        global_frame.setFrameShape(QFrame.NoFrame)
        global_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # qpushbutton_test
        self.qpushbutton_test = QPushButton("Don't click! It's going to crash HABBY !")
        self.qpushbutton_test.setStyleSheet("background-color: #47B5E6; color: black")
        self.qpushbutton_test.clicked.connect(self.test_function_dev)

        # group1
        group1 = QGroupBoxCollapsible(self.tr("??"))
        group1.setChecked(False)
        group1_layout = QVBoxLayout()
        group1_layout.addWidget(self.qpushbutton_test)
        group1.setLayout(group1_layout)

        # global_layout
        global_layout = QVBoxLayout()
        global_layout.setAlignment(Qt.AlignTop)
        global_frame.setLayout(global_layout)
        global_layout.addWidget(group1)
        global_layout.addStretch()
        self.setWidget(global_frame)

    def test_function_dev(self):
        #print("test_function_dev")
        1 / 0
        #print("test_function_dev")

    def refresh_gui(self):
        aa = 1
        # print("OtherToolToCreateTab.refresh_gui")
