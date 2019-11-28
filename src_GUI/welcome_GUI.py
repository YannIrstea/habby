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
import shutil

from lxml import etree as ET
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QEvent
from PyQt5.QtWidgets import QWidget, QPushButton, QGroupBox,\
    QLabel, QGridLayout, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, \
    QMessageBox, QScrollArea, \
    QFrame
from PyQt5.QtGui import QPixmap, QFont
import matplotlib as mpl
mpl.use("Qt5Agg")  # backends and toolbar for pyqt5


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
        self.imname = os.path.join('translation', 'banner.jpg')  # image should be in the translation folder
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
        l0 = QLabel('<b>HABitat suitaBilitY</b>')
        l0.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        l0.setFont(font)
        buttono = QPushButton(self.tr('Open existing project'), self)
        buttono.clicked.connect(self.open_proj.emit)
        buttons = QPushButton(self.tr('New project'), self)
        buttons.clicked.connect(self.new_proj_signal.emit)
        spacerleft = QSpacerItem(200, 1)
        spacerright = QSpacerItem(120, 1)
        spacer2 = QSpacerItem(1, 70)
        highpart = QWidget()  # used to regroup all QWidgt in the first part of the Windows

        # general into to put in the xml .prj file
        l1 = QLabel(self.tr('Project name: '))
        self.e1 = QLabel(self.name_prj)
        l2 = QLabel(self.tr('Main folder: '))
        self.e2 = QLabel(self.path_prj)
        # button2 = QPushButton(self.tr('Set folder'), self)
        # button2.clicked.connect(self.setfolder2)
        # button2.setToolTip(self.tr('Move the project to a new location. '
        #                            'The data might be long to copy if the project folder is large.'))
        l3 = QLabel(self.tr('Description: '))
        self.e3 = QTextEdit()
        # this is used to save the data if the QLineEdit is going out of Focus
        self.e3.installEventFilter(self.outfocus_filter)
        self.outfocus_filter.outfocus_signal.connect(self.save_info_signal.emit)
        l4 = QLabel(self.tr('User name: '))
        self.e4 = QLineEdit()
        # this is used to save the data if the QLineEdit is going out of Focus
        self.e4.installEventFilter(self.outfocus_filter)
        self.outfocus_filter.outfocus_signal.connect(self.save_info_signal.emit)

        # background image
        self.pic = QLabel()
        self.pic.setMaximumSize(1000, 200)
        # use full ABSOLUTE path to the image, not relative
        self.pic.setPixmap(QPixmap(os.path.join(os.getcwd(), self.imname)).scaled(500, 500))  # 800 500
        # animal_picture_label.setPixmap(QPixmap(os.path.join(os.getcwd(), self.imname)).scaled(150, 150))  # 800 500

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # if the directory of the project does not exist, let the general tab empty
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isdir(self.path_prj) or not os.path.isfile(fname):
            pass
        # otherwise, fill it
        else:
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(fname, parser)
            root = doc.getroot()
            user_child = root.find(".//user_name")
            des_child = root.find(".//description")
            self.e4.setText(user_child.text)
            self.e3.setText(des_child.text)

        # empty frame scrolable
        content_widget = QFrame()

        # layout (in two parts)
        layout2 = QGridLayout(content_widget)
        layouth = QGridLayout()

        layouth.addItem(spacerleft, 1, 0)
        layouth.addItem(spacerright, 1, 5)
        layouth.addWidget(l0, 0, 1)
        layouth.addWidget(buttons, 2, 1)
        layouth.addWidget(buttono, 3, 1)
        layouth.addItem(spacer2, 5, 2)
        highpart.setLayout(layouth)

        self.lowpart = QGroupBox(self.tr("Current project"))
        layoutl = QGridLayout(self.lowpart)
        layoutl.addWidget(l1, 1, 0)
        layoutl.addWidget(self.e1, 1, 1)
        layoutl.addWidget(l2, 2, 0)
        layoutl.addWidget(self.e2, 2, 1)
        layoutl.addWidget(l4, 3, 0)
        layoutl.addWidget(self.e4, 3, 1)
        layoutl.addWidget(l3, 4, 0)
        layoutl.addWidget(self.e3, 4, 1)

        layout2.addWidget(self.pic, 0, 0)
        layout2.addWidget(highpart, 0, 0)
        layout2.addWidget(self.lowpart, 1, 0)

        # self.setLayout(layout2)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

    def open_example(self):
        """
        This function will be used to open a project example for HABBY, but the example is not prepared yet. NOT DONE
        AS IT IS COMPLICATED TO INSTALL A EXAMPLE PROJECT. WINDOWS SAVED PROGRAM IN FOLDER WITHOUT WRITE PERMISSIONS.
        """
        self.send_log.emit('Warning: ' + self.tr('No example prepared yet.'))

    def setfolder2(self):
        """
        This function is used by the user to select the folder where the xml project file will be located.
        This is used in the case where the project exist already. A similar function is in the class CreateNewProjectDialog()
        for the case where the project is new.
        """
        # check for invalid null parameter on Linuxgit
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        if dir_name != '':  # cancel case
            self.e2.setText(dir_name)
            self.send_log.emit(self.tr('New folder selected for the project.'))
        else:
            return

        # if the project exist and the project name has not changed
        # ,change the project path in the xml file and copy the xml at the chosen location
        # if a project directory exist copy it as long as no project directory exist at the end location
        path_old = self.path_prj
        fname_old = os.path.join(path_old, self.name_prj + '.habby')
        new_path = os.path.join(dir_name, self.name_prj)
        if os.path.isfile(fname_old) and self.e1.text() == self.name_prj:
            # write new project path
            if not os.path.exists(new_path):
                self.path_prj = new_path
                parser = ET.XMLParser(remove_blank_text=True)
                doc = ET.parse(fname_old, parser)
                root = doc.getroot()
                path_child = root.find(".//Path_Project")
                path_child.text = self.path_prj  # new name
                fname = os.path.join(self.path_prj, self.name_prj + '.habby')
                try:
                    shutil.copytree(path_old, self.path_prj)
                except shutil.Error:
                    self.send_log.emit(self.tr('Could not copy the project. Permission Error?'))
                    return
                self.send_log.emit(self.tr('The files in the project folder have been copied to the new location.'))
                try:
                    shutil.copyfile(fname_old, os.path.join(self.path_prj, self.name_prj + '.habby'))
                except shutil.Error:
                    self.send_log.emit(self.tr('Could not copy the project. Permission Error?'))
                    return
                doc.write(fname, pretty_print=True)
                self.e2.setText(self.path_prj)
                self.save_signal.emit()  # if not project folder, will create one
            else:
                self.send_log.emit('Error: ' + self.tr('A project with the same name exists at the new location. '
                                   'Project not saved.'))
                self.e2.setText(path_old)
                return
        # if the project do not exist or has a different name than before, save a new project
        else:
            self.save_signal.emit()


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

