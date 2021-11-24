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
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox,\
    QLabel, QGridLayout, QLineEdit, QTextEdit, QSpacerItem, \
    QMessageBox, QScrollArea, QSizePolicy, QFrame
from PyQt5.QtGui import QPixmap, QFont
import matplotlib as mpl
mpl.use("Qt5Agg")  # backends and toolbar for pyqt5

from src.project_properties_mod import load_project_properties


class WelcomeW(QScrollArea):
    """
    The class WeLcomeW()  creates the first tab of HABBY (the tab called “General”). This tab is there to create
    a new project or to change the name, path, etc. of a project.
    """
    # define the signal used by the class
    # should be outise of the __init__ function

    save_signal = pyqtSignal()
    """
        A PyQt signal used to save the project
    """
    open_proj = pyqtSignal()
    " A signal for MainWindows to open an existing project"
    new_proj_signal = pyqtSignal()
    """
        A PyQt signal used to open a new project
    """
    send_log = pyqtSignal(str, name='send_log')
    """
       A PyQt signal used to write the log
    """
    change_name = pyqtSignal()
    """
    A signal to change the name of the project for MainWindows
    """
    save_info_signal = pyqtSignal()
    """
    A signal to change the user name and the description of the project
    """

    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.tab_name = "welcome"
        self.imname = os.path.join('file_dep', 'banner.png')  # image should be in the translation folder
        self.image_background_path = os.path.join(os.getcwd(), self.imname)
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.outfocus_filter = MyFilter()
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization of a new instance of the class WelcomeW()
        """
        # Welcome windows
        self.habby_title_label = QLabel('<b>HABitat suitaBilitY</b>')
        self.habby_title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        self.habby_title_label.setFont(font)
        self.habby_title_label.setStyleSheet("QLabel {background-color:None; color : rgb(71, 181, 230); }")

        # background image
        self.background_image_label = QLabel()
        self.background_image_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Qt.AlignCenter
        self.background_image_label.setContentsMargins(0, 0, 0, 0)
        self.background_image_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.background_image_label.setMaximumHeight(150)
        self.background_image_pixmap = QPixmap(self.image_background_path).scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # ,
        self.background_image_label.setPixmap(self.background_image_pixmap)
        self.background_image_label.setScaledContents(True)

        # general into to put in the xml .prj file
        name_prj_title_label = QLabel(self.tr('Name:'))
        self.name_prj_label = QLabel(self.name_prj)
        path_prj_title_label = QLabel(self.tr('Path:'))
        self.path_prj_label = QLabel(self.path_prj)
        user_name_title_label = QLabel(self.tr('User name:'))
        self.user_name_lineedit = QLineEdit()
        # this is used to save the data if the QLineEdit is going out of Focus
        self.user_name_lineedit.installEventFilter(self.outfocus_filter)
        self.outfocus_filter.outfocus_signal.connect(self.save_info_signal.emit)
        description_prj_title_label = QLabel(self.tr('Description:'))
        self.description_prj_textedit = QTextEdit()
        # this is used to save the data if the QLineEdit is going out of Focus
        self.description_prj_textedit.installEventFilter(self.outfocus_filter)
        self.outfocus_filter.outfocus_signal.connect(self.save_info_signal.emit)

        # insist on white background color (for linux, mac)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # if the directory of the project does not exist, let the general tab empty
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isdir(self.path_prj) or not os.path.isfile(fname):
            pass
        # otherwise, fill it
        else:
            project_properties = load_project_properties(self.path_prj)
            self.user_name_lineedit.setText(project_properties["user_name"])
            self.description_prj_textedit.setText(project_properties["description"])

        # current_prj_groupbox
        self.current_prj_groupbox = QGroupBox(self.tr("Current project"))
        current_prj_layout = QGridLayout(self.current_prj_groupbox)
        current_prj_layout.addWidget(name_prj_title_label, 1, 0)
        current_prj_layout.addWidget(self.name_prj_label, 1, 1)
        current_prj_layout.addWidget(path_prj_title_label, 2, 0)
        current_prj_layout.addWidget(self.path_prj_label, 2, 1)
        current_prj_layout.addWidget(user_name_title_label, 3, 0)
        current_prj_layout.addWidget(self.user_name_lineedit, 3, 1)
        current_prj_layout.addWidget(description_prj_title_label, 4, 0)
        current_prj_layout.addWidget(self.description_prj_textedit, 4, 1)

        # empty frame scrolable
        general_frame = QFrame()
        self.general_layout = QGridLayout(general_frame)
        self.general_layout.addWidget(self.current_prj_groupbox, 1, 0)
        self.general_layout.addWidget(self.background_image_label, 0, 0)
        self.general_layout.addWidget(self.habby_title_label, 0, 0)

        # self.setLayout(self.general_layout)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(general_frame)

    def open_example(self):
        """
        This function will be used to open a project example for HABBY, but the example is not prepared yet. NOT DONE
        AS IT IS COMPLICATED TO INSTALL A EXAMPLE PROJECT. WINDOWS SAVED PROGRAM IN FOLDER WITHOUT WRITE PERMISSIONS.
        """
        self.send_log.emit('Warning: ' + self.tr('No example prepared yet.'))


class MyFilter(QObject):
    """
    This is a filter which is used to know when a QWidget is going out of focus. Practically this is used
    if the user goes away from a QLineEdit. If this events happens, the project is automatically saved with the new
    info of the user.
    """
    outfocus_signal = pyqtSignal()
    """
    A signal to change the user name and the description of the project
    """

    def eventFilter(self, widget, event):
        # FocusOut event
        if event.type() == QEvent.FocusOut:
            self.outfocus_signal.emit()
            # return False so that the widget will also handle the event
            # otherwise it won't focus out
            return False
        else:
            # we don't care about other events
            return False

