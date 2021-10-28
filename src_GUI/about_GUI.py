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
from platform import platform as OS_VERSION_STR
from osgeo.gdal import __version__ as GDAL_VERSION_STR
from triangle import __version__ as TRIANGLE_VERSION_STR
from h5py.version import version as H5PY_VERSION_STR
from h5py.version import hdf5_version as HDF5_VERSION_STR
from qdarkstyle import __version__ as QDARKSTYLE_VERSION_STR
from PyQt5.Qt import PYQT_VERSION_STR
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QTableWidget, QDialog, QAbstractItemView, QHeaderView, QPushButton, \
    QLabel, QFormLayout, QVBoxLayout, QGroupBox, QSizePolicy, QTabWidget, QTableWidgetItem, \
    QFrame, QScrollArea, QHBoxLayout

import src_GUI.dev_tools_GUI
from habby import HABBY_VERSION_STR
from src.user_preferences_mod import user_preferences
from src.about_mod import get_last_version_number_from_github


class CheckVersionDialog(QDialog):
    """
    The class which support the creation and management of the output. It is notably used to select the options to
    create the figures.

    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj, name_icon, actual_version):

        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_icon = name_icon
        self.actual_version = actual_version
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        """ WIDGETS """
        actual_version_label_title = QLabel(self.tr('Current software'))
        actual_version_label = QLabel(str(self.actual_version))

        last_version_label_title = QLabel(self.tr('Last on web'))
        self.last_version_label = QLabel("-")

        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.close_button.clicked.connect(self.close_dialog)

        """ LAYOUT """
        # versions layout
        layout_general_options = QFormLayout()
        general_options_group = QGroupBox(self.tr("HABBY version"))
        general_options_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        general_options_group.setLayout(layout_general_options)
        layout_general_options.addRow(actual_version_label_title, actual_version_label)
        layout_general_options.addRow(last_version_label_title, self.last_version_label)

        # general
        layout = QVBoxLayout(self)
        layout.addWidget(general_options_group)
        layout.addWidget(self.close_button)
        layout.setAlignment(self.close_button, Qt.AlignRight)
        self.setWindowTitle(self.tr("Check HABBY version"))
        self.setWindowIcon(QIcon(self.name_icon))
        self.setMinimumWidth(300)
        self.setModal(True)

    def get_last_version_number_from_github(self):
        last_version_str = get_last_version_number_from_github()  # X.Y.Z version level
        last_version_str = last_version_str
        self.last_version_label.setText(last_version_str)

    def showEvent(self, event):
        # do stuff here
        self.get_last_version_number_from_github()
        event.accept()

    def close_dialog(self):
        self.close()


class SoftInformationDialog(QDialog):
    """
    The class which support the creation and management of the output. It is notably used to select the options to
    create the figures.

    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj, name_icon, actual_version):

        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_icon = name_icon
        self.actual_version = actual_version
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        """ about_tab """
        about_tab = QScrollArea()
        about_tab.setAutoFillBackground(True)  # insist on white background color (for linux, mac)
        about_tab.setPalette(p)
        about_tab.setWidgetResizable(True)
        about_tab.setFrameShape(QFrame.NoFrame)
        about_frame = QFrame()
        about_frame.setFrameShape(QFrame.NoFrame)
        about_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        about_tab.setWidget(about_frame)
        about_layout = QFormLayout()
        home_page_label = QLabel("<a href='https://habby.wiki.inrae.fr'>https://habby.wiki.inrae.fr</a>")
        home_page_label.setOpenExternalLinks(True)
        github_page_label = QLabel("<a href='https://github.com/YannIrstea/habby'>https://github.com/YannIrstea/habby</a>")
        github_page_label.setOpenExternalLinks(True)
        about_layout.addRow(QLabel(self.tr("HABBY version")), QLabel(HABBY_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("Qt version")), QLabel(PYQT_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("GDAL/OGR version")), QLabel(GDAL_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("triangle version")), QLabel(TRIANGLE_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("h5py version")), QLabel(H5PY_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("hdf5 version")), QLabel(HDF5_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("qdarkstyle version")), QLabel(QDARKSTYLE_VERSION_STR))
        about_layout.addRow(QLabel(self.tr("OS version")), QLabel(OS_VERSION_STR()))
        about_layout.addRow(QLabel(self.tr("HABBY official web site")), home_page_label)
        about_layout.addRow(QLabel(self.tr("HABBY github web site")), github_page_label)
        about_layout.setAlignment(Qt.AlignTop)
        about_frame.setLayout(about_layout)

        """ developer_tab """
        developer_tab = QScrollArea()
        developer_tab.setAutoFillBackground(True)  # insist on white background color (for linux, mac)
        developer_tab.setPalette(p)
        developer_tab.setWidgetResizable(True)
        developer_tab.setFrameShape(QFrame.NoFrame)
        developer_frame = QFrame() 
        developer_frame.setFrameShape(QFrame.NoFrame)
        developer_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        developer_tab.setWidget(developer_frame)
        developer_layout = QVBoxLayout()
        self.developer_tablewidget = QTableWidget()
        self.developer_tablewidget.setFrameShape(QFrame.NoFrame)
        self.developer_tablewidget.setShowGrid(False)
        self.developer_tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        self.developer_tablewidget.verticalHeader().setVisible(False)
        self.developer_tablewidget.horizontalHeader().setVisible(False)
        #self.developer_tablewidget.horizontalHeader().setStretchLastSection(True)
        my_developer_list = []
        with open(os.path.join("doc", "table_developpers.txt"), 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                my_developer_list.append(line.strip().split("\t"))
        self.developer_tablewidget.setRowCount(len(my_developer_list))
        self.developer_tablewidget.setColumnCount(len(my_developer_list[0]))
        for line_num in range(len(my_developer_list)):
            for header_num in range(len(my_developer_list[line_num])):
                twi = QTableWidgetItem(my_developer_list[line_num][header_num])
                current_font = twi.font()
                current_font.setPointSize(7)
                twi.setFont(current_font)
                self.developer_tablewidget.setItem(line_num, header_num, twi)
        self.developer_tablewidget.verticalHeader().setDefaultSectionSize(self.developer_tablewidget.verticalHeader().minimumSectionSize())
        self.developer_tablewidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        developer_layout.addWidget(self.developer_tablewidget)
        developer_layout.setAlignment(Qt.AlignTop)
        developer_frame.setLayout(developer_layout)

        """ contributor_tab """
        contributor_tab = QScrollArea()
        contributor_tab.setAutoFillBackground(True)  # insist on white background color (for linux, mac)
        contributor_tab.setPalette(p)
        contributor_tab.setWidgetResizable(True)
        contributor_tab.setFrameShape(QFrame.NoFrame)
        contributor_frame = QFrame() 
        contributor_frame.setFrameShape(QFrame.NoFrame)
        contributor_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        contributor_tab.setWidget(contributor_frame)
        contributor_layout = QVBoxLayout()
        self.contributor_tablewidget = QTableWidget()
        self.contributor_tablewidget.setFrameShape(QFrame.NoFrame)
        self.contributor_tablewidget.setShowGrid(False)
        self.contributor_tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        self.contributor_tablewidget.verticalHeader().setVisible(False)
        self.contributor_tablewidget.horizontalHeader().setVisible(False)
        #self.contributor_tablewidget.horizontalHeader().setStretchLastSection(True)
        my_contributor_list = []
        with open(os.path.join("doc", "table_contributors.txt"), 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                my_contributor_list.append(line.strip().split("\t"))
        self.contributor_tablewidget.setRowCount(len(my_contributor_list))
        self.contributor_tablewidget.setColumnCount(len(my_contributor_list[0]))
        for line_num in range(len(my_contributor_list)):
            for header_num in range(len(my_contributor_list[line_num])):
                twi = QTableWidgetItem(my_contributor_list[line_num][header_num])
                current_font = twi.font()
                current_font.setPointSize(7)
                twi.setFont(current_font)
                self.contributor_tablewidget.setItem(line_num, header_num, twi)
        self.contributor_tablewidget.verticalHeader().setDefaultSectionSize(self.contributor_tablewidget.verticalHeader().minimumSectionSize())
        self.contributor_tablewidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        contributor_layout.addWidget(self.contributor_tablewidget)
        contributor_layout.setAlignment(Qt.AlignTop)
        contributor_frame.setLayout(contributor_layout)

        """ thanks_tab """
        thanks_tab = QScrollArea()
        thanks_tab.setAutoFillBackground(True)  # insist on white background color (for linux, mac)
        thanks_tab.setPalette(p)
        thanks_tab.setWidgetResizable(True)
        thanks_tab.setFrameShape(QFrame.NoFrame)
        thanks_frame = QFrame()
        thanks_frame.setFrameShape(QFrame.NoFrame)
        thanks_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        thanks_tab.setWidget(thanks_frame)
        thanks_layout = QVBoxLayout()
        self.thanks_tablewidget = QTableWidget()
        self.thanks_tablewidget.setFrameShape(QFrame.NoFrame)
        self.thanks_tablewidget.setShowGrid(False)
        self.thanks_tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.thanks_tablewidget.verticalHeader().setVisible(False)
        self.thanks_tablewidget.horizontalHeader().setVisible(False)
        #self.thanks_tablewidget.horizontalHeader().setStretchLastSection(True)
        my_thanks_list = []
        with open(os.path.join("doc", "table_acknowledgements.txt"), 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                my_thanks_list.append(line.strip().split("\t"))
        self.thanks_tablewidget.setRowCount(len(my_thanks_list))
        self.thanks_tablewidget.setColumnCount(len(my_thanks_list[0]))
        for line_num in range(len(my_thanks_list)):
            for header_num in range(len(my_thanks_list[line_num])):
                twi = QTableWidgetItem(my_thanks_list[line_num][header_num])
                current_font = twi.font()
                current_font.setPointSize(7)
                twi.setFont(current_font)
                self.thanks_tablewidget.setItem(line_num, header_num, twi)
        self.thanks_tablewidget.verticalHeader().setDefaultSectionSize(self.thanks_tablewidget.verticalHeader().minimumSectionSize())
        self.thanks_tablewidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        thanks_layout.addWidget(self.thanks_tablewidget)
        thanks_layout.setAlignment(Qt.AlignTop)
        thanks_frame.setLayout(thanks_layout)

        """ translator_tab """
        translator_tab = QScrollArea()
        translator_tab.setAutoFillBackground(True)  # insist on white background color (for linux, mac)
        translator_tab.setPalette(p)
        translator_tab.setWidgetResizable(True)
        translator_tab.setFrameShape(QFrame.NoFrame)
        translator_frame = QFrame()
        translator_frame.setFrameShape(QFrame.NoFrame)
        translator_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        translator_tab.setWidget(translator_frame)
        translator_layout = QVBoxLayout()
        self.translator_tablewidget = QTableWidget()
        self.translator_tablewidget.setFrameShape(QFrame.NoFrame)
        self.translator_tablewidget.setShowGrid(False)
        self.translator_tablewidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.translator_tablewidget.verticalHeader().setVisible(False)
        self.translator_tablewidget.horizontalHeader().setVisible(False)
        #self.translator_tablewidget.horizontalHeader().setStretchLastSection(True)
        my_translator_list = []
        with open(os.path.join("doc", "table_translators.txt"), 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                my_translator_list.append(line.strip().split("\t"))
        self.translator_tablewidget.setRowCount(len(my_translator_list))
        self.translator_tablewidget.setColumnCount(len(my_translator_list[0]))
        for line_num in range(len(my_translator_list)):
            for header_num in range(len(my_translator_list[line_num])):
                twi = QTableWidgetItem(my_translator_list[line_num][header_num])
                current_font = twi.font()
                current_font.setPointSize(7)
                twi.setFont(current_font)
                self.translator_tablewidget.setItem(line_num, header_num, twi)
        self.translator_tablewidget.verticalHeader().setDefaultSectionSize(self.translator_tablewidget.verticalHeader().minimumSectionSize())
        self.translator_tablewidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        translator_layout.addWidget(self.translator_tablewidget)
        translator_layout.setAlignment(Qt.AlignTop)
        translator_frame.setLayout(translator_layout)

        """ licence_tab """
        licence_tab = QScrollArea()
        licence_tab.setAutoFillBackground(True)  # insist on white background color (for linux, mac)
        licence_tab.setPalette(p)
        licence_tab.setWidgetResizable(True)
        licence_tab.setFrameShape(QFrame.NoFrame)
        licence_frame = QFrame()
        licence_frame.setFrameShape(QFrame.NoFrame)
        licence_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        licence_tab.setWidget(licence_frame)
        licence_layout = QVBoxLayout()
        self.licence_label = QLabel()
        licence_layout.addWidget(self.licence_label)
        licence_layout.setAlignment(Qt.AlignTop)
        licence_frame.setLayout(licence_layout)

        """ last line """
        inrae_label = QLabel()
        inrae_label.setPixmap(QPixmap("file_dep/INRAE.png").scaled(inrae_label.size() * 0.2, Qt.KeepAspectRatio))
        ofb_label = QLabel()
        ofb_label.setPixmap(QPixmap("file_dep/OFB.png").scaled(ofb_label.size() * 0.2, Qt.KeepAspectRatio))
        edf_label = QLabel()
        edf_label.setPixmap(QPixmap("file_dep/EDF.png").scaled(edf_label.size() * 0.2, Qt.KeepAspectRatio))
        self.close_button = QPushButton(self.tr("Close"))
        self.close_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.close_button.clicked.connect(self.close_dialog)

        """ general """
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabBar(src_GUI.dev_tools_GUI.LeftHorizontalTabBar(self))  # horizontal tab title text
        self.tab_widget.setTabPosition(QTabWidget.West)  # tab position to le left
        self.tab_widget.addTab(about_tab, self.tr("About"))
        self.tab_widget.addTab(developer_tab, self.tr("Developers"))
        self.tab_widget.addTab(contributor_tab, self.tr("Contributors"))
        self.tab_widget.addTab(thanks_tab, self.tr("Acknowledgements"))
        self.tab_widget.addTab(translator_tab, self.tr("Translators"))
        self.tab_widget.addTab(licence_tab, self.tr("Licence"))

        """ LAYOUT """
        # last_line_layout
        last_line_layout = QHBoxLayout()
        last_line_layout.addWidget(inrae_label)
        last_line_layout.addWidget(ofb_label)
        last_line_layout.addWidget(edf_label)
        last_line_layout.addStretch()
        last_line_layout.addWidget(self.close_button)
        last_line_layout.setAlignment(inrae_label, Qt.AlignLeft)
        last_line_layout.setAlignment(ofb_label, Qt.AlignLeft)
        last_line_layout.setAlignment(edf_label, Qt.AlignLeft)
        last_line_layout.setAlignment(self.close_button, Qt.AlignRight)

        # general
        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.addLayout(last_line_layout)
        self.setWindowTitle(self.tr("About HABBY"))
        self.setWindowIcon(QIcon(self.name_icon))
        self.resize(650, 500)
        self.setModal(True)

    def set_licence_string(self):
        # change language
        if user_preferences.data["language"] == 'english':
            self.licence_file_path = r"file_dep/Licence_CeCILL_V2.1-en.txt"
        elif user_preferences.data["language"] == "french":
            self.licence_file_path = r"file_dep/Licence_CeCILL_V2.1-fr.txt"
        else:
            self.licence_file_path = r"file_dep/Licence_CeCILL_V2.1-en.txt"

        # read
        with open(self.licence_file_path, "r") as fh:
            licence_string = fh.read()

        # set text
        self.licence_label.setText(licence_string)

    def showEvent(self, event):
        event.accept()
        self.set_licence_string()

    def close_dialog(self):
        self.close()
