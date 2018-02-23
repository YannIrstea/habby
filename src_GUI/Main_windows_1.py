"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import sys
import glob
import os
import shutil
import numpy as np
import time
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from PyQt5.QtCore import QTranslator, pyqtSignal, QSettings, Qt, QRect, pyqtRemoveInputHook, QObject, QEvent
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QStatusBar, QMessageBox, QComboBox, QScrollArea, \
    QSizePolicy, QInputDialog, QMenu, QToolBar
from PyQt5.QtGui import QPixmap, QFont, QIcon
from webbrowser import open as wbopen
import h5py
import matplotlib
matplotlib.use("Qt5Agg")
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import matplotlib.pyplot as plt
from src_GUI import estimhab_GUI
from src_GUI import hydro_GUI_2
from src_GUI import stathab_GUI
from src_GUI import output_fig_GUI
from src_GUI import bio_info_GUI
from src_GUI import fstress_GUI
from src_GUI import chronicle_GUI


class MainWindows(QMainWindow):
    """

    The class MainWindows contains the menu and the title of all the HABBY windows.
    It also create all the widgets which can be called during execution

    **Technical comments and walk-through**

    First, we load the user setting using Qsettings: The settings by default of Qsettings are the name of the program (HABBY) and
    the name of the organization which develops the program (irstea).  I have added three user settings (the name of the
    last project loaded into HABBY, the path to this project and the language used). The Qsetting are stored in the
    registry in Windows. Qsettings also function with Apple and Linux even if the information is stored differently

    We set up the translation next. The translation of HABBY in different language is explained in more detail in
    the section “Translation of HABBY”. We give here the path to the data related to the translation. More precisely, we indicate
    here the path to the translation data and the name of the qm file containing the data related to the translation
    in each language. If a new qm is added for a new language, it should be added here to the list.

    Now, two important attributes are defined: self.name_prj and self.path_prj. These attribute will be communicated to
    children classes. For each project, an xml file is created. This “project” file should be called name_prj.xml
    and should be situated in the path indicated by self.path_prj.

    We call the central_widget which contains the different tabs.

    We create the menu of HABBY calling the function my menu_bar().

    Two signal are connected, one to save the project (i.e to update the xml project file) and another to save an
    ESTIMHAB calculation.

    We show the created widget.
    """

    def __init__(self):

        # the maximum number of recent project shown in the menu. if changement here modify self.my_menu_bar
        self.nb_recent = 5

        # the version number of habby
        # CAREFUL also change the version in habby.py for the command line version
        self.version = 0.21

        # load user setting
        self.settings = QSettings('irstea', 'HABBY'+str(self.version))
        name_prj_set = self.settings.value('name_prj')
        print(name_prj_set)
        name_path_set = self.settings.value('path_prj')
        print(name_path_set)
        language_set = self.settings.value('language_code')

        # to erase setting of older version
        # add here the number of older version whose setting must be erased because they are not compatible
        # it should be managed by innosetup, but do not work always
        self.oldversion = [1.1]
        for v in self.oldversion:
            if v != self.version:
                self.oldsettings = QSettings('irstea', 'HABBY' + str(v))
            self.oldsettings.clear()

        # recent project: list of string
        recent_projects_set = self.settings.value('recent_project_name')
        recent_projects_path_set = self.settings.value('recent_project_path')
        if recent_projects_set is not None:
            if len(recent_projects_set) > self.nb_recent:
                self.settings.setValue('recent_project_name', recent_projects_set[ -self.nb_recent+1:])
                self.settings.setValue('recent_project_path', recent_projects_path_set[-self.nb_recent+1:])

        del self.settings

        # set up tranlsation
        self.languageTranslator = QTranslator()
        self.path_trans = os.path.abspath('translation')
        self.file_langue = [r'Zen_EN.qm', r'Zen_FR.qm', r'Zen_ES.qm']
        if language_set:
            try:
                self.lang = int(language_set)  # need integer there
            except ValueError:
                self.lang = 0
        else:
            self.lang = 0
        app = QApplication.instance()
        app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[int(self.lang)], self.path_trans)
        app.installTranslator(self.languageTranslator)

        # prepare the attributes, careful if change the Qsetting!
        self.msg2 = QMessageBox()
        self.rechmain = False
        if name_path_set:
            self.name_prj = name_prj_set
        else:
            self.name_prj = ''
        if name_path_set:
            self.path_prj = name_path_set
        else:
            self.path_prj = '.'
        if recent_projects_set:
            self.recent_project = recent_projects_set[::-1]
        else:
            self.recent_project = []
        if recent_projects_path_set:
            self.recent_project_path = recent_projects_path_set[::-1]
        else:
            self.recent_project_path = []

        self.username_prj = "NoUserName"
        self.descri_prj = ""
        self.does_it_work = True

        # the path to the biological data by default (HABBY force the user to use this path)
        self.path_bio_default = "biology"

        # create the central widget
        if self.lang == 0:
            lang_bio = 'English'
        elif self.lang == 1:
            lang_bio = 'French'
        else:
            lang_bio = 'English'
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj, lang_bio)

        self.msg2 = QMessageBox()

        # call the normal constructor of QWidget
        super().__init__()
        pyqtRemoveInputHook()

        # call an additional function during initialisation
        self.init_ui()

    def init_ui(self):
        """ Used by __init__() to create an instance of the class MainWindows """

        # set window icon
        name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
        self.setWindowIcon(QIcon(name_icon))

        # create the menu bar
        self.my_menu_bar()

        # create a vertical toolbar
        self.toolbar = QToolBar()
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)
        self.my_toolbar()

        # connect the signals of the welcome tab with the different functions (careful if changes this copy 3 times
        # in set_langue and save_project
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.welcome_tab.change_name.connect(self.change_name_project)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        #  right click
        self.create_menu_right()
        self.central_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.central_widget.customContextMenuRequested.connect(self.on_context_menu)

        # set geometry
        self.setGeometry(200, 200, 900, 800)
        self.setCentralWidget(self.central_widget)

        output_fig_GUI.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        self.check_concurrency()
        self.show()

    def closeEvent(self, event):
        """
        This is the function which handle the closing of the program. It use the function end_concurrency() to indicate
        to other habby instances that we do not use a particular project anymore.

        We use os_exit instead of sys.exit so it also close the other thread if more than one is open.

        :param event: managed by the operating system.
        """

        self.end_concurrency()
        os._exit(1)

    def check_concurrency(self):
        """
        This function tests if the project which is opening by HABBY is not used by another instance of HABBY. It is
        dangerous  to open two time the same project as we have problem with the writing of the xml files.

        To check if a project is open, we have a text file in the project folder named "check_concurrency.txt".
        In this text file, there is either the word "open" or "close". When HABBY open a new project, it checks
        this file is set to close and change it to open. Hence, if a project is open twice a warning is written.
        """
        if self.name_prj is not None:

            # open the text file
            filename = os.path.join(os.path.join(self.path_prj,'fichier_hdf5'), 'check_concurrency.txt')
            if not os.path.isfile(filename):
                self.central_widget.write_log('Warning: Could not check if the project was open by '
                                              'another instance of HABBY (1) \n')
                if os.path.isdir(os.path.join(self.path_prj,'fichier_hdf5')):
                    with open(filename, 'wt') as f:
                        f.write('open')
                return

            # check if open
            try:
                with open(filename, 'rt') as f:
                    data = f.read()
            except IOError:
                self.central_widget.write_log('Warning: Could not check if the project was open by another '
                                               'instance of HABBY (2) \n')
                return
            if data == 'open':
                self.central_widget.write_log('Warning: The same project is open in another instance of HABBY.'
                                              ' This could results in fatal and unexpected error. '
                                              'It is strongly adivsed to close the other instance of HABBY.')
                self.central_widget.write_log('Warning: This message could also appear if HABBY was not closed properly'
                                              '. In this case, please close and re-open HABBY.\n')

            else:
                with open(filename, 'wt') as f:
                    f.write('open')

    def end_concurrency(self):
        """
        This functiion indicates to the project folder than this project is not used anymore. Hence, this project
        can be used freely by an other instance of HABBY.
        """
        if self.name_prj is not None:

            # open the text file
            filename = os.path.join(os.path.join(self.path_prj,'fichier_hdf5'), 'check_concurrency.txt')
            if not os.path.isfile(filename):
                self.central_widget.write_log('Warning: Could not check if the project was open by '
                                              'another instance of HABBY (3) \n')
                return

            try:
                with open(filename, 'wt') as f:
                    f.write('close')
            except IOError:
                return

    def setlangue(self, nb_lang):
        """
        A function which change the language of the programme. It change the menu and the central widget.
        It uses the self.lang attribute which should be set to the new language before calling this function.

        :param nb_lang: the number representing the language (int)

        *   0 is for English
        *   1 for French
        *   2 for spanish
        *   n for any additionnal language

        """

        # set the langugae
        self.lang = int(nb_lang)
        # get the old tab
        ind_tab = self.central_widget.tab_widget.currentIndex()
        # get a new tranlator
        app = QApplication.instance()
        app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[int(self.lang)], self.path_trans)
        app.installTranslator(self.languageTranslator)

        # recreate new widget
        if self.central_widget.tab_widget.count() == 1:
            self.central_widget.welcome_tab = WelcomeW(self.path_prj, self.name_prj)
        else:
            self.central_widget.welcome_tab = WelcomeW(self.path_prj, self.name_prj)
            self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
            self.central_widget.hydro_tab = hydro_GUI_2.Hydro2W(self.path_prj, self.name_prj)
            self.central_widget.substrate_tab = hydro_GUI_2.SubstrateW(self.path_prj, self.name_prj)
            self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)
            self.central_widget.output_tab = output_fig_GUI.outputW(self.path_prj, self.name_prj)
            self.central_widget.bioinfo_tab = bio_info_GUI.BioInfo(self.path_prj, self.name_prj)
            self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)
            self.central_widget.chronicle_tab = chronicle_GUI.ChroniqueGui(self.path_prj, self.name_prj)

            # pass the info to the bio info tab
            # to be modified if a new langugage is added !
            if nb_lang == 0:
                self.central_widget.bioinfo_tab.lang = 'English'
            elif nb_lang == 1:
                self.central_widget.bioinfo_tab.lang = 'French'
            # elif nb_lang == 2:  # to be addaed if the xml preference files are also in spanish
            #     self.central_widget.bioinfo_tab.lang = 'Spanish'
            else:
                self.central_widget.bioinfo_tab.lang = 'English'

            # write the new langugage in the figure option to be able to get the title, axis in the right langugage
            output_fig_GUI.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        # set the central widget
        for i in range(self.central_widget.tab_widget.count(), 0, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.name_prj_c = self.name_prj
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.tab_widget.removeTab(0)
        self.central_widget.add_all_tab()
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj

        # create the new menu
        self.my_menu_bar()

        # create the new toolbar
        self.my_toolbar()

        # reconnect saignal for the weclcome tab
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.welcome_tab.change_name.connect(self.change_name_project)
        self.central_widget.welcome_tab.save_info_signal.connect(self.central_widget.save_info_projet)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)
        # re-connect signals for the other tabs
        self.central_widget.connect_signal_fig_and_drop()
        # re-connect signals for the log
        self.central_widget.connect_signal_log()

        self.central_widget.update_hydro_hdf5_name()
        self.central_widget.update_merge_for_chronicle()

        self.central_widget.l1.setText(self.tr('Habby says:'))

        # update user option to remember the language
        self.settings = QSettings('irstea', 'HABBY'+str(self.version))
        self.settings.setValue('language_code', self.lang)
        del self.settings

        #  right click
        self.create_menu_right()
        self.central_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.central_widget.customContextMenuRequested.connect(self.on_context_menu)

        # open at the old tab
        self.central_widget.tab_widget.setCurrentIndex(ind_tab)

    def my_menu_bar(self, right_menu=False):
        """
        This function creates the menu bar of HABBY when call without argument or with the argument right_menu is False.
        if right menu is True, it creates a very similar menu but we use a QMenu() instead of a QMenuBar() as it
        is the menu open when the user right click

        :param right_menu: If call with True, we create a menu for the right click and not for the menu part on the top
               of the screen.
        """

        if right_menu:
            self.menu_right = QMenu()
            self.menu_right.clear()
        else:
            self.menubar = self.menuBar()
            self.menubar.clear()

        # Menu to open and close file
        exitAction = QAction(self.tr('Exit'), self)
        exitAction.setShortcut('Ctrl+C')
        exitAction.setStatusTip(self.tr('Exit application'))
        exitAction.triggered.connect(self.closeEvent)
        openprj = QAction(self.tr('Open Project'), self)
        openprj.setShortcut('Ctrl+O')
        openprj.setStatusTip(self.tr('Open an exisiting project'))
        openprj.triggered.connect(self.open_project)
        recent_proj_menu = []
        for j in range(0, min(self.nb_recent, len(self.recent_project))):
            recent_proj_menu.append(QAction(self.recent_project[j], self))
            # I just do not understand this, but really writing with j just do not work
            # should be changed if self.nb_recent is changed
            if j == 0:
                recent_proj_menu[0].triggered.connect(lambda: self.open_recent_project(0))
            elif j == 1:
                recent_proj_menu[1].triggered.connect(lambda: self.open_recent_project(1))
            elif j == 2:
                recent_proj_menu[2].triggered.connect(lambda: self.open_recent_project(2))
            elif j == 3:
                recent_proj_menu[3].triggered.connect(lambda: self.open_recent_project(3))
            elif j == 4:
                recent_proj_menu[4].triggered.connect(lambda: self.open_recent_project(4))
        newprj = QAction(self.tr('New Project'), self)
        newprj.setShortcut('Ctrl+N')
        newprj.setStatusTip(self.tr('Create a new project'))
        newprj.triggered.connect(self.new_project)
        closeprj = QAction(self.tr('Close Project'), self)
        closeprj.setShortcut('Ctrl+W')
        closeprj.setStatusTip(self.tr('Close the current project without opening a new one'))
        closeprj.triggered.connect(self.close_project)

        # Menu to open menu research
        logc = QAction(self.tr("Clear Log Windows"), self)
        logc.setStatusTip(self.tr('Empty the log windows at the bottom of the main window. Do not erase the .log file.'))
        logc.setShortcut('Ctrl+L')
        logc.triggered.connect(self.clear_log)
        logn = QAction(self.tr("Do Not Save Log"), self)
        logn.setStatusTip(self.tr('The .log file will not be updated further.'))
        logn.triggered.connect(lambda: self.do_log(0))
        logy = QAction(self.tr("Save Log"), self)
        logy.setStatusTip(self.tr('Events will be written to the .log file.'))
        logy.triggered.connect(lambda: self.do_log(1))
        savi = QAction(self.tr("Delete All Images"), self)
        savi.setStatusTip(self.tr('Figures saved by HABBY will be deleted'))
        savi.triggered.connect(self.erase_pict)
        #showim = QAction(self.tr("Show Images"), self)
        #showim.setStatusTip(self.tr('Open the window to view the created figures.'))
        #showim.triggered.connect(self.central_widget.showfig2)
        closeim = QAction(self.tr("Close All Images"), self)
        closeim.setStatusTip(self.tr('Close the figures which are currently created.'))
        closeim.triggered.connect(self.central_widget.closefig)
        closeim.setShortcut('Ctrl+B')
        optim = QAction(self.tr("More Options"), self)
        optim.setStatusTip(self.tr('Various options to modify the figures produced by HABBY.'))
        optim.triggered.connect(self.central_widget.optfig)

        rech = QAction(self.tr("Show Research Options"), self)
        rech.setShortcut('Ctrl+R')
        rech.setStatusTip(self.tr('Add untested research options'))
        rech.triggered.connect(self.open_rech)
        rechc = QAction(self.tr("Hide Research Options"), self)
        rechc.setShortcut('Ctrl+H')
        rechc.setStatusTip(self.tr('Hide untested research options'))
        rechc.triggered.connect(self.close_rech)

        # Menu to choose the language
        lAction1 = QAction(self.tr('&English'), self)
        lAction1.setStatusTip(self.tr('click here for English'))
        lAction1.triggered.connect(lambda: self.setlangue(0))  # lambda because of the argument
        lAction2 = QAction(self.tr('&French'), self)
        lAction2.setStatusTip(self.tr('click here for French'))
        lAction2.triggered.connect(lambda: self.setlangue(1))
        lAction3 = QAction(self.tr('&Spanish'), self)
        lAction3.setStatusTip(self.tr('click here for Spanish'))
        lAction3.triggered.connect(lambda: self.setlangue(2))

        # Menu to obtain help and programme version
        helpm = QAction(self.tr('Developper Help'), self)
        helpm.setStatusTip(self.tr('Get help to use the programme'))
        helpm.triggered.connect(self.open_help)

        # add all first level menu
        if right_menu:
            self.menu_right = QMenu()
            fileMenu = self.menu_right.addMenu(self.tr('&File'))
            fileMenu4 = self.menu_right.addMenu(self.tr('Options'))
            fileMenu2 = self.menu_right.addMenu(self.tr('Language'))
            fileMenu3 = self.menu_right.addMenu(self.tr('Help'))
        else:
            self.menubar = self.menuBar()
            fileMenu = self.menubar.addMenu(self.tr('&File'))
            fileMenu4 = self.menubar.addMenu(self.tr('Options'))
            fileMenu2 = self.menubar.addMenu(self.tr('Language'))
            fileMenu3 = self.menubar.addMenu(self.tr('Help'))

        # add al the rest
        fileMenu.addAction(openprj)
        recentpMenu = fileMenu.addMenu(self.tr('Open Recent Project'))
        for j in range(0, len(recent_proj_menu)):
            recentpMenu.addAction(recent_proj_menu[j])
        fileMenu.addAction(closeprj)
        fileMenu.addAction(newprj)
        fileMenu.addAction(exitAction)
        log_all = fileMenu4.addMenu(self.tr('Log'))
        log_all.addAction(logc)
        log_all.addAction(logn)
        log_all.addAction(logy)
        im_all = fileMenu4.addMenu(self.tr('Image options'))
        #im_all.addAction(showim)
        im_all.addAction(savi)
        im_all.addAction(closeim)
        im_all.addAction(optim)
        re_all = fileMenu4.addMenu(self.tr('Research options'))
        re_all.addAction(rech)
        re_all.addAction(rechc)
        fileMenu2.addAction(lAction1)
        fileMenu2.addAction(lAction2)
        fileMenu2.addAction(lAction3)
        fileMenu3.addAction(helpm)

        if not right_menu:
            # add the status bar
            self.statusBar()

            # add the title of the windows
            # let it here as it should be changes if language changes
            if self.name_prj != '':
                self.setWindowTitle(self.tr('HABBY ')+ str(self.version) + ' - ' + self.name_prj)
            else:
                self.setWindowTitle(self.tr('HABBY ') + str(self.version))

            # in case we need a tool bar
            # self.toolbar = self.addToolBar('')

    def create_menu_right(self):
        """
        This function create the menu for right click
        """

        self.my_menu_bar(True)

    def on_context_menu(self, point):
        """
        This function is used to show the menu on right click. If we are ont he Habitat Tab and that the focus is on
        the QListWidget, it shows the informatin concerning the fish

        :param point: Not understood, linke with the position of the menu.
        """
        if self.central_widget.bioinfo_tab.list_s.underMouse():
            self.central_widget.bioinfo_tab.show_info_fish(True)
        elif self.central_widget.bioinfo_tab.list_f.underMouse():
            self.central_widget.bioinfo_tab.show_info_fish(False)
        else:
            self.menu_right.exec_(self.central_widget.mapToGlobal(point))

    def my_toolbar(self):

        self.toolbar.clear()

        # create the icon
        icon_closefig = QIcon()
        name1 = os.path.join(os.getcwd(), "translation", "icon", "close.png")
        icon_closefig.addPixmap(QPixmap(name1), QIcon.Normal)

        icon_open = QIcon()
        name1 = os.path.join(os.getcwd(), "translation","icon","openproject.png")
        icon_open.addPixmap(QPixmap(name1), QIcon.Normal)

        icon_see = QIcon()
        name1 =os.path.join(os.getcwd(),"translation", "icon","see_project.png")
        icon_see.addPixmap(QPixmap(name1), QIcon.Normal)

        icon_new = QIcon()
        name1 = os.path.join(os.getcwd(), "translation", "icon", "newfile.png")
        icon_new.addPixmap(QPixmap(name1), QIcon.Normal)

        # create the actions of the toolbar
        openAction = QAction(icon_open, self.tr('Open Project'), self)
        openAction.setStatusTip(self.tr('Open an existing project'))
        openAction.triggered.connect(self.open_project)

        newAction = QAction(icon_new, self.tr('New Project'), self)
        newAction.setStatusTip(self.tr('Create a new project'))
        newAction.triggered.connect(self.new_project)

        seeAction = QAction(icon_see, self.tr('See Files of the Current Project'), self)
        seeAction.setStatusTip(self.tr('See the existing file of a project and open them.'))
        seeAction.triggered.connect(self.see_file)

        closeAction = QAction(icon_closefig, self.tr('Close Figures'), self)
        closeAction.setStatusTip(self.tr('Close all figures'))
        closeAction.triggered.connect(self.central_widget.closefig)

        # position of the toolbar
        self.toolbar.setOrientation(Qt.Vertical)

        # create the toolbar
        self.toolbar.addAction(openAction)
        self.toolbar.addAction(newAction)
        self.toolbar.addAction(seeAction)
        self.toolbar.addAction(closeAction)

    def save_project(self):
        """
        A function to save the xml file with the information on the project

        **Technical comments**

        This function saves or creates the xml file related to the projet. In this xml file, there are the path and
        the name to all files related to the project, notably the hdf5 files containing the hydrological data.

        To find or create the xml file, we use the attribute self.path_prj and self.name_proj. If the path to
        the project directory is not found an error appears. The error is here sent though additional windows
        (to be sure that the user notice this problem), using the Qmesssage module. The user should give the general
        info about the project in the general tab of HABBY and they are collected here. User option (using Qsetting)
        is next updated so that the user will find his project open the next time it opens HABBY.

        When HABBY open, there are therefore  two choice: a) This is a new project b) the project exists already.
        If the project is new, the xml file is created and general information is written in this file. In addition,
        the text file which are necessary to log the action of HABBY are created now. This part of the reason why it
        is not possible to run other part of HABBY (such as loading hydrological data) before a project is saved.
        In addition, it would create a lot of problems on where to store the data created. Hence, a project is needed
        before using HABBY. If the project exists already (i.e. the name and the path of the project have not been
        modified), the xml file is just updated to change its attributes as needed.

        Interesting path are a) the biology path (named "biology" by default) which contains the biological information
        such as the preference curve and b) the path_im which is the path where all figures and most outputs of HABBY
        is saved. If path_im is not given, HABBY automatically create a folder called figures when the
        user creates a new project. The user can however change this path if he wants. It also create other similar
        folders to sotre different type of outputs. The next step is to communicate
        to all the children widget than the name and path of the project have changed.

        This function also changes the title of the Windows to reflect the project name and it adds the saved
        project to the list of recent project if it is not part of the list already. Because of this the menu must
        updated.

        Finally the log is written (see “log and HABBY in the command line).
        """

        # saved path
        e2here = self.central_widget.welcome_tab.e2
        if not os.path.isdir(e2here.text()):  # if the directoy do not exist
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Path to project"))
            self.msg2.setText(
                self.tr("The directory indicated in the project path does not exists. Project not saved."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.central_widget.write_log('# Project not saved.')
            return
        else:
            path_prj_before = self.path_prj
            self.path_prj = e2here.text()
        # name
        e1here = self.central_widget.welcome_tab.e1
        self.name_prj = e1here.text()

        # username and description
        e4here = self.central_widget.welcome_tab.e4
        self.username_prj = e4here.text()
        e3here = self.central_widget.welcome_tab.e3
        self.descri_prj = e3here.toPlainText()

        fname = os.path.join(self.path_prj, self.name_prj+'.xml')

        # update user option and re-do (the whole) menu
        self.settings = QSettings('irstea', 'HABBY'+str(self.version))
        self.settings.setValue('name_prj', self.name_prj)
        self.settings.setValue('path_prj', self.path_prj)

        # save name and path of project in the list of recent project
        if self.name_prj not in self.recent_project:
            self.recent_project.append(self.name_prj)
            self.recent_project_path.append(self.path_prj)
        else:
            ind = np.where(self.recent_project == self.name_prj)[0]
            if ind:
                if os.path.normpath(self.path_prj) != os.path.normpath(self.recent_project_path[ind[0]]):  # linux windows path
                    self.recent_project.append(self.name_prj)
                    self.recent_project_path.append(self.path_prj)
        self.settings.setValue('recent_project_name', self.recent_project)
        self.settings.setValue('recent_project_path', self.recent_project_path)
        del self.settings
        self.my_menu_bar()

        # if new projet or project move
        if not os.path.isfile(fname):
            # create the root <root> and general tab
            root_element = ET.Element("root")
            tree = ET.ElementTree(root_element)
            general_element = ET.SubElement(root_element, "General")
            # create all child
            child = ET.SubElement(general_element, "Project_Name")
            child.text = self.name_prj
            path_child = ET.SubElement(general_element, "Path_Projet")
            path_child.text = self.path_prj
            # log
            log_element = ET.SubElement(general_element, "Log_Info")
            pathlog_child = ET.SubElement(log_element, "File_Log")
            pathlog_child.text = os.path.join(self.name_prj + '.log')
            pathlog_child = ET.SubElement(log_element, "File_Restart")
            pathlog_child.text = os.path.join('restart_'+self.name_prj + '.log')
            savelog_child = ET.SubElement(log_element, "Save_Log")
            savelog_child.text = str(self.central_widget.logon)

            # create the log files by copying the existing "basic" log files (log0.txt and restart_log0.txt)
            if self.name_prj != '':
                shutil.copy(os.path.join('src_GUI', 'log0.txt'), os.path.join(self.path_prj, self.name_prj + '.log'))
                shutil.copy(os.path.join('src_GUI', 'restart_log0.txt'), os.path.join(self.path_prj,
                                                                                      'restart_' + self.name_prj +
                                                                                      '.log'))
            # more precise info
            user_child = ET.SubElement(general_element, "User_Name")
            user_child.text = self.username_prj
            des_child = ET.SubElement(general_element, "Description")
            des_child.text = self.descri_prj
            # we save here only the bversin number of when the project was saved the first time.
            # if a project is used in two version, it has the first version number to insure back-comptability.
            # let say on version 1.5, we assure comptability in version 1.4, but that we do assure comptability
            # for version 1.4 in version 1.6. In this case, we should not have the verison number 1.5 in the xml.
            ver_child = ET.SubElement(general_element, 'Version_HABBY')
            ver_child.text = str(self.version)

            # path
            path_element = ET.SubElement(general_element, "Paths")
            pathbio_child = ET.SubElement(path_element, "Path_Bio")
            pathbio_child.text = self.path_bio_default
            path_im = os.path.join(self.path_prj, 'figures')
            pathbio_child = ET.SubElement(path_element, "Path_Figure")
            pathbio_child.text = 'figures'
            path_hdf5 = os.path.join(self.path_prj, 'fichier_hdf5')
            pathhdf5_child = ET.SubElement(path_element, "Path_Hdf5")
            pathhdf5_child.text = 'fichier_hdf5'
            path_input = os.path.join(self.path_prj, 'input')
            pathinput_child = ET.SubElement(path_element, "Path_Input")
            pathinput_child.text = 'input'
            path_text = os.path.join(self.path_prj, 'text_output')
            pathtext_child = ET.SubElement(path_element, "Path_Text")
            pathtext_child.text = 'text_output'
            path_other = os.path.join(self.path_prj, 'shapefiles_output')
            pathother_child = ET.SubElement(path_element, "Path_Shape")
            pathother_child.text = 'shapefiles_output'
            path_para = os.path.join(self.path_prj, 'visualisation_output')
            pathpara_child = ET.SubElement(path_element, "Path_Paraview")
            pathpara_child.text = 'visualisation_output'

            # save new xml file
            if self.name_prj != '':
                fname = os.path.join(self.path_prj, self.name_prj+'.xml')
                tree.write(fname)

            # create a default directory for the figures and the hdf5
            if not os.path.exists(path_im):
                os.makedirs(path_im)
            if not os.path.exists(path_hdf5):
                os.makedirs(path_hdf5)
            if not os.path.exists(path_input):
                os.makedirs(path_input)
            if not os.path.exists(path_text):
                os.makedirs(path_text)
            if not os.path.exists(path_other):
                os.makedirs(path_other)
            if not os.path.exists(path_para):
                os.makedirs(path_para)

            # create the concurency file
            filenamec = os.path.join(os.path.join(self.path_prj, 'fichier_hdf5'), 'check_concurrency.txt')
            if os.path.isdir(os.path.join(self.path_prj, 'fichier_hdf5')):
                with open(filenamec, 'wt') as f:
                    f.write('open')

        # project exist
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            child = root.find(".//Project_Name")
            path_child = root.find(".//Path_Projet")
            user_child = root.find(".//User_Name")
            des_child = root.find(".//Description")
            pathim_child = root.find(".//Path_Figure")
            pathdf5_child = root.find(".//Path_Hdf5")
            pathbio_child = root.find(".//Path_Bio")
            pathtxt_child = root.find(".//Path_Text")
            pathin_child = root.find(".//Path_Input")
            pathout_child = root.find(".//Path_Output")
            if pathim_child is None:
                pathim_text = 'figures'
            else:
                pathim_text = pathim_child.text
            if pathdf5_child is None:
                pathhdf5_text = 'fichier_hdf5'
            else:
                pathhdf5_text = pathdf5_child.text
            if pathtxt_child is None:
                pathtxt_text = 'text_output'
            else:
                pathtxt_text = pathtxt_child.text
            if pathin_child is None:
                pathin_text = 'input'
            else:
                pathin_text = pathin_child.text
            if pathout_child is None:
                pathout_text = 'other_output'
            else:
                pathout_text = pathin_child.text

            child.text = self.name_prj
            path_child.text = self.path_prj
            pathbio_child.text = self.path_bio_default
            user_child.text = self.username_prj
            des_child.text = self.descri_prj
            fname = os.path.join(self.path_prj, self.name_prj+'.xml')
            doc.write(fname)

            # create needed folder if not there yet
            path_im = os.path.join(self.path_prj, pathim_text)
            path_h5 = os.path.join(self.path_prj, pathhdf5_text)
            path_text = os.path.join(self.path_prj, pathtxt_text)
            path_output = os.path.join(self.path_prj, pathout_text)
            pathin_text = os.path.join(self.path_prj, pathin_text)
            try:
                if not os.path.exists(path_im):
                    os.makedirs(path_im)
                if not os.path.exists(path_h5):
                    os.makedirs(path_h5)
                if not os.path.exists(path_text):
                    os.makedirs(path_text)
                if not os.path.exists(pathin_text):
                    os.makedirs(pathin_text)
                if not os.path.exists(path_output):
                    os.makedirs(path_output)
            except PermissionError:
                self.central_widget.write_log('Error: Could not create directory, Permission Error \n')
                return

        # update central widget
        self.central_widget.name_prj_c = self.name_prj
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj

        # send the new name to all widget and re-connect signal
        t = self.central_widget.l2.text()
        m = self.central_widget.tab_widget.count()

        for i in range(m, 0, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.tab_widget.removeTab(0)

        # create new tab (there were some segmentation fault here as it re-write existing QWidget, be careful)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj +'.xml')):
            self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
            self.central_widget.substrate_tab = hydro_GUI_2.SubstrateW(self.path_prj, self.name_prj)
            self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)
            self.central_widget.output_tab = output_fig_GUI.outputW(self.path_prj, self.name_prj)
            self.central_widget.output_tab.save_option_fig()
            self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)
            self.central_widget.bioinfo_tab = bio_info_GUI.BioInfo(self.path_prj, self.name_prj)
            self.central_widget.hydro_tab = hydro_GUI_2.Hydro2W(self.path_prj, self.name_prj)
            self.central_widget.chronicle_tab = chronicle_GUI.ChroniqueGui(self.path_prj, self.name_prj)
        else:
            print('Error: Could not find the project saved just now. \n')
            return

        self.central_widget.add_all_tab()

        # re-connect signals for the tab
        self.central_widget.connect_signal_fig_and_drop()
        self.central_widget.connect_signal_log()

        self.central_widget.update_hydro_hdf5_name()

        # write log
        if len(t) > 26:
            # no need to write #log of habby started two times
            # to breack line habby use <br> there, should not be added again
            self.central_widget.write_log(t[26:-4])
        self.central_widget.write_log('# Project saved or opened successfully.')
        self.central_widget.write_log("py    name_prj= r'" + self.name_prj + "'")
        self.central_widget.write_log("py    path_prj= r'" + self.path_prj + "'")
        self.central_widget.write_log("py    path_bio= r'" + os.path.join(os.getcwd(), self.path_bio_default) + "'")
        self.central_widget.write_log("py    version_habby= " + str(self.version))
        self.central_widget.write_log("restart NAME_PROJECT")
        self.central_widget.write_log("restart    Name of the project: " + self.name_prj)
        self.central_widget.write_log("restart    Path of the project: " + self.path_prj)
        self.central_widget.write_log("restart    version habby: " + str(self.version))

        # enabled lowest part
        self.central_widget.welcome_tab.lowpart.setEnabled(True)

        # update name project
        if self.name_prj != '':
            self.setWindowTitle(self.tr('HABBY ') + str(self.version) + ' - ' + self.name_prj)
        else:
            self.setWindowTitle(self.tr('HABBY ') + str(self.version))

    def open_project(self):
        """
        This function is used to open an existing habby project by selecting an xml project file. Called by
        my_menu_bar()
        """

        #  indicate to HABBY that this project will close
        self.end_concurrency()

        # open an xml file
        path_here = os.path.dirname(self.path_prj)
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', path_here, self.tr("XML (*.xml)"))[0]
        if not filename_path:  # cancel
            return
        blob, ext_xml = os.path.splitext(filename_path)
        if ext_xml == '.xml':
            pass
        else:
            self.central_widget.write_log("Error: File should be of type XML\n")
            return

        # load the xml file
        try:
            try:
                docxml2 = ET.parse(filename_path)
                root2 = docxml2.getroot()
            except IOError:
                self.central_widget.write_log("Error: the selected project file does not exist.\n")
                self.close_project()
                return
        except ET.ParseError:
            self.central_widget.write_log('Error: the XML is not well-formed.\n')
            return

        # get the project name and path. Write it in the QWiddet.
        # the text in the Qwidget will be used to save the project
        self.name_prj = root2.find(".//Project_Name").text
        self.path_prj = root2.find(".//Path_Projet").text

        if self.name_prj is None or self.path_prj is None:
            self.central_widget.write_log('Error: Project xml file is not understood \n')
            return

        # check coherence
        if self.name_prj + '.xml' != os.path.basename(filename_path):
            self.central_widget.write_log('Warning: xml file name is not coherent with project name. '
                                          'New project name: ' + os.path.basename(filename_path))
            self.name_prj = os.path.basename(filename_path)
            root2.find(".//Project_Name").text = self.name_prj
        if not os.path.samefile(self.path_prj, os.path.dirname(filename_path)):
            self.central_widget.write_log('Warning: xml file path is not coherent with project path. '
                                          'New project path: ' + os.path.dirname(filename_path))
            self.path_prj = os.path.dirname(filename_path)
            root2.find(".//Path_Projet").text = self.path_prj
            # if we have change the project path, it is probable tha the project folder was copied from somewhere else
            # so the check concurenncy file was probably copied and look like open even if the project is closed.
            self.central_widget.write_log('Warning: Could not control for concurrency between projects due to path '
                                          'change. If you have any other instance of HABBY open, please close it.')
            self.end_concurrency()
        stathab_info = root2.find(".//hdf5Stathab")
        self.username_prj = root2.find(".//User_Name").text
        self.descri_prj = root2.find(".//Description").text
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText(self.username_prj)
        self.central_widget.welcome_tab.e3.setText(self.descri_prj)
        docxml2.write(filename_path)

        # save the project
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.name_prj_c = self.name_prj
        self.save_project()

        # update estimhab and stathab
        if stathab_info is not None :  # if there is data for STATHAB
            self.central_widget.stathab_tab.load_from_hdf5_gui()
        self.central_widget.statmod_tab.open_estimhab_hdf5()

        # update hydro
        self.central_widget.update_hydro_hdf5_name()
        self.central_widget.substrate_tab.update_sub_hdf5_name()

        # recreate new widget
        self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
        self.central_widget.hydro_tab = hydro_GUI_2.Hydro2W(self.path_prj, self.name_prj)
        self.central_widget.substrate_tab = hydro_GUI_2.SubstrateW(self.path_prj, self.name_prj)
        self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)
        self.central_widget.output_tab = output_fig_GUI.outputW(self.path_prj, self.name_prj)
        self.central_widget.bioinfo_tab = bio_info_GUI.BioInfo(self.path_prj, self.name_prj)
        self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)
        self.central_widget.chronicle_tab = chronicle_GUI.ChroniqueGui(self.path_prj, self.name_prj)

        # set the central widget
        for i in range(self.central_widget.tab_widget.count(), 0, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.name_prj_c = self.name_prj
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.add_all_tab()
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj
        # re-connect signals for the tab
        self.central_widget.connect_signal_fig_and_drop()
        self.central_widget.connect_signal_log()

        # write the new langugage in the figure option to be able to get the title, axis in the right langugage
        output_fig_GUI.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        # check if project open somewhere else
        self.check_concurrency()

        return

    def open_recent_project(self, j):
        """
        This function open a recent project of the user. The recent project are listed in the menu and can be
        selected by the user. When the user select a recent project to open, this function is called. Then, the name of
        the recent project is selected and the method save_project() is called.

        :param j: This indicates which project should be open, based on the order given in the menu
        """

        #  indicate to HABBY that this project will close
        self.end_concurrency()

        # get the project file
        filename_path = os.path.join(self.recent_project_path[j], self.recent_project[j] +'.xml')

        # load the xml file
        try:
            try:
                docxml = ET.parse(filename_path)
                root = docxml.getroot()
            except IOError:
                self.central_widget.write_log("Error: the selected project file does not exist.\n")
                self.close_project()
                return
        except ET.ParseError:
            self.central_widget.write_log('Error: the XML is not well-formed.\n')
            return

        # get the project name and path. Write it in the QWiddet.
        # the text in the Qwidget will be used to save the project
        self.name_prj = root.find(".//Project_Name").text
        self.path_prj = root.find(".//Path_Projet").text
        self.username_prj = root.find(".//User_Name").text
        self.descri_prj = root.find(".//Description").text
        stathab_info = root.find(".//hdf5Stathab")
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText(self.username_prj)
        self.central_widget.welcome_tab.e3.setText(self.descri_prj)
        #self.central_widget.write_log('# Project opened sucessfully. \n')

        # save the project
        self.save_project()

        # update hydro
        self.central_widget.update_hydro_hdf5_name()
        self.central_widget.substrate_tab.update_sub_hdf5_name()

        # update stathab and estimhab
        if stathab_info is not None:
            self.central_widget.stathab_tab.load_from_hdf5_gui()
        self.central_widget.statmod_tab.open_estimhab_hdf5()

        # write the new langugage in the figure option to be able to get the title, axis in the right langugage
        output_fig_GUI.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        # check if project open somewhere else
        self.check_concurrency()

    def new_project(self):
        """
        This function open an empty project and guide the user to create a new project, using a new Windows
        of the class CreateNewProject
        """
        pathprj_old = self.path_prj

        self.end_concurrency()

        # open a new Windows to ask for the info for the project
        self.createnew = CreateNewProject(self.lang, self.path_trans, self.file_langue, pathprj_old)
        self.createnew.save_project.connect(self.save_project_if_new_project)
        self.createnew.send_log.connect(self.central_widget.write_log)
        self.createnew.show()

    def close_project(self):
        """
        This function close the current project wihout opening a new project
        """
        # open an empty project (so it close the old one)
        self.empty_project()

        # remove tab 9as we have no project anymore)
        for i in range(self.central_widget.tab_widget.count(),0,-1):
            self.central_widget.tab_widget.removeTab(i)

        # add the welcome Widget
        self.central_widget.tab_widget.addTab(self.central_widget.welcome_tab, self.tr("Start"))
        self.central_widget.welcome_tab.lowpart.setEnabled(False)

        self.end_concurrency()

    def save_project_if_new_project(self):
        """
        This function is used to save a project when the project is created from the other Windows CreateNewProject. It
        can not be in the new_project function as the new_project function call CreateNewProject().
        """
        name_prj_here = self.createnew.e1.text()

        # add a new folder
        path_new_fold = os.path.join(self.createnew.e2.text(), name_prj_here)
        if not os.path.isdir(path_new_fold):
            try:
                os.makedirs(path_new_fold)
            except PermissionError:
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Permission Error"))
                self.msg2.setText(
                    self.tr("You do not have the permission to write in this folder. Choose another folder. \n"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()
                return

        # pass the info from the extra Windows to the HABBY MainWindows (check on user input done by save_project)
        self.central_widget.welcome_tab.e1.setText(name_prj_here)
        self.central_widget.welcome_tab.e2.setText(path_new_fold)
        self.central_widget.welcome_tab.e3.setText('')
        self.central_widget.welcome_tab.e4.setText('')

        # check if there is not another project with the same path_name
        fname = os.path.join(self.createnew.e2.text(), name_prj_here+'.xml')
        if os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Identical name"))
            self.msg2.setText(self.tr("A project with an identical name exists. Choose another name."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            return

        # save project if unique name in the selected folder
        else:
            self.createnew.close()
            self.save_project()

        # change the path_im
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        self.path_im = os.path.join(self.path_prj, 'figures')
        doc = ET.parse(fname)
        root = doc.getroot()
        # geo data
        child1 = root.find('.//Path_Figure')
        if child1 is None:
            child1 = ET.SubElement(root, 'Path_Figure')
            child1.text = 'figures'
        else:
            child1.text = 'figures'
        doc.write(fname)

        # write the new langugage in the figure option to be able to get the title, axis in the right langugage
        self.central_widget.output_tab.save_option_fig()
        output_fig_GUI.set_lang_fig(self.lang, self.path_prj, self.name_prj)

    def change_name_project(self):
        """
        This function is used to change the name of the current project. To do this, it copies the xml
        project with a new name and copy the file for the log with a new name
        """
        fname_old = os.path.join(self.path_prj, self.name_prj + '.xml')
        old_path_prj = self.path_prj

        # get new name from the user
        text, ok = QInputDialog.getText(self, self.tr('Change Project name'),
                                        self.tr('Enter the new project name:'))
        if ok:
            name_prj_here = str(text)
            # check if file already exist
            fname = os.path.join(self.path_prj, name_prj_here + '.xml')
            new_path_prj = os.path.join(os.path.dirname(self.path_prj), name_prj_here)
            if os.path.isfile(fname) or os.path.isdir(new_path_prj):
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Erase old project?"))
                self.msg2.setText(
                    self.tr("A project with an identical name exists. Choose another name."))
                self.msg2.setDefaultButton(QMessageBox.Ok)
                self.msg2.show()
                return
            # change label name
            self.central_widget.welcome_tab.e1.setText(name_prj_here)
            # copy the xml
            try:
                shutil.copyfile(fname_old, fname)
            except FileNotFoundError:
                self.central_widget.write_log("Error: the old project file does not exist (1)\n.")
                return
            # write the new name in the copied xml
            doc = ET.parse(fname)
            root = doc.getroot()
            name_child = root.find(".//Project_Name")
            # change project path
            path_child = root.find(".//Path_Projet")
            path_prj_old = path_child.text
            path_child.text = os.path.join(os.path.dirname(path_child.text), name_prj_here)
            new_path_prj = os.path.join(os.path.dirname(path_child.text), name_prj_here)
            # update log name in the new xml
            child_logfile1 = root.find(".//File_Log")
            log1_old = child_logfile1.text
            child_logfile1.text = os.path.join(new_path_prj, name_prj_here + '.log')
            child_logfile2 = root.find(".//File_Restart")
            log2_old = child_logfile2.text
            child_logfile2.text = os.path.join(new_path_prj, 'restart_'+ name_prj_here + '.log')

            # copy the xml
            try:
                os.rename(os.path.join(old_path_prj, log1_old), os.path.join(old_path_prj, name_prj_here + '.log'))
                os.rename(os.path.join(old_path_prj, log2_old), os.path.join(old_path_prj,
                                                                             'restart_'+ name_prj_here + '.log'))
            except FileNotFoundError:
                self.central_widget.write_log("Error: the old log files do not exist (2)\n.")
                return
            doc.write(fname)
            # # erase old xml
            os.remove(fname_old)
            # rename directory
            try:
                os.rename(path_prj_old, new_path_prj)
            except FileExistsError:
                self.central_widget.write_log("A project with the same name exist. Conflict arised. \n")
            # change path_prj
            self.path_prj = new_path_prj
            self.central_widget.welcome_tab.e2.setText(new_path_prj)
            # save project, just in case
            self.save_project()

    def empty_project(self):
        """
        This function open a new empty project
        """

        # load the xml file
        filename_empty = os.path.abspath('src_GUI/empty_proj.xml')

        try:
            try:
                docxml2 = ET.parse(filename_empty)
                root2 = docxml2.getroot()
            except IOError:
                self.central_widget.write_log("Error: no empty project. \n")
                return
        except ET.ParseError:
            self.central_widget.write_log('Error: the XML is not well-formed.\n')
            return

        # get the project name and path. Write it in the QWiddet.
        # the text in the Qwidget will be used to save the project
        self.name_prj = root2.find(".//Project_Name").text
        self.path_prj = root2.find(".//Path_Projet").text
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText('')
        self.central_widget.welcome_tab.e3.setText('')

        # save the project
        # self.save_project()

    def see_file(self):
        """
        This function allows the user to see the files in the project folder and to open them.
        """

        file_name = QFileDialog.getOpenFileName(self, self.tr('Open File'), self.path_prj)[0]

        if file_name:
            wbopen(file_name)

    def save_project_estimhab(self):
        """
        A function to save the information linked with Estimhab in an hdf5 file.

        **Technical comments**

        This function save the data and result from the estimhab calculation. It would look more logic if it was in
        the esimhab.py script, but it was easier to call it from here instead of in the child class.

        This function get all estimhab input, create an hdf5 file using h5py and save the data in the hdf5. One
        specialty of hdf5 is that is cannot use Unicode. Hence all string have to be passed to ascii using the encode
        function. The size of each data should also be known.

        Finally, we save the name and path of the estimhab file in the xml project file.
        """

        # a boolenan to check to progress of the saving
        self.does_it_work = True

        # get all the float
        q1 = self.test_entry_float(self.central_widget.statmod_tab.eq1)
        q2 = self.test_entry_float(self.central_widget.statmod_tab.eq2)
        w1 = self.test_entry_float(self.central_widget.statmod_tab.ew1)
        w2 = self.test_entry_float(self.central_widget.statmod_tab.ew2)
        h1 = self.test_entry_float(self.central_widget.statmod_tab.eh1)
        h2 = self.test_entry_float(self.central_widget.statmod_tab.eh2)
        q50 = self.test_entry_float(self.central_widget.statmod_tab.eq50)
        qmin = self.test_entry_float(self.central_widget.statmod_tab.eqmin)
        qmax = self.test_entry_float(self.central_widget.statmod_tab.eqmax)
        sub = self.test_entry_float(self.central_widget.statmod_tab.esub)

        # get chosen fish (xml name of the file)
        fish_list = []
        for i in range(0, self.central_widget.statmod_tab.list_s.count()):
            fish_item = self.central_widget.statmod_tab.list_s.item(i)
            fish_item_str = fish_item.text()
            fish_list.append(fish_item_str)

        # create an empty hdf5 file using all default prop.
        fname_no_path = self.name_prj+'_ESTIMHAB'+'.h5'
        fnamep = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(fnamep):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save project"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the start tab before saving ESTIMHAB data"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        else:
            doc = ET.parse(fnamep)
            root = doc.getroot()
            tree = ET.ElementTree(root)
            child = root.find(".//Path_Hdf5")
            path_hdf5 = child.text

        fname = os.path.join(os.path.join(self.path_prj, path_hdf5), fname_no_path)
        file = h5py.File(fname, 'w')

        # create all datasets and group
        file.attrs['path_bio'] = self.central_widget.statmod_tab.path_bio
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version

        qmesg = file.create_group('qmes')
        qmes = qmesg.create_dataset(fname_no_path, [2, 1], data=[q1, q2])
        wmesg = file.create_group('wmes')
        wmes = wmesg.create_dataset(fname_no_path, [2, 1], data=[w1, w2])
        hmesg = file.create_group('hmes')
        hmes = hmesg.create_dataset(fname_no_path, [2, 1], data=[h1, h2])
        q50_natg = file.create_group('q50')
        q50_nat = q50_natg.create_dataset(fname_no_path, [1, 1], data=[q50])
        qrangeg = file.create_group('qrange')
        qrange = qrangeg.create_dataset(fname_no_path, [2, 1], data=[qmin, qmax])
        subg = file.create_group('substrate')
        sub = subg.create_dataset(fname_no_path, [1, 1], data=[sub])
        ascii_str = [n.encode("ascii", "ignore") for n in fish_list]  # unicode is not ok with hdf5
        # to see if this work dt = h5py.special_dtype(vlen=unicode)
        fish_typeg = file.create_group('fish_type')
        fish_type_all = fish_typeg.create_dataset(fname_no_path, (len(fish_list), 1), data=ascii_str)
        file.close()

        # add the name of this h5 file to the xml file of the project

        if not os.path.isfile(fnamep):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save project"))
            self.msg2.setText(self.tr("The project is not saved. Save the project in the start tab before saving ESTIMHAB data"))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        else:
            doc = ET.parse(fnamep)
            root = doc.getroot()
            tree = ET.ElementTree(root)
            child = root.find(".//ESTIMHAB_data")
            # test if there is already estimhab data in the project
            if child is None:
                child = ET.SubElement(root, "ESTIMHAB_data")
                child.text = fname_no_path
            else:
                child.text = fname_no_path
            tree.write(fnamep)

    def test_entry_float(self, var_in):
        """
        An utility function to test if var_in are float or not
        the boolean self.does_it_work is used to know if the functions run until the end.

        :param var_in: the QlineEdit which contains the data (so var_in.text is a string)

        :return: the tested variable var_in
        """

        var_str = var_in.text()
        var = -99
        if self.does_it_work:
            try:
                var = float(var_str)
            except ValueError:
                self.does_it_work = False
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Data for ESTIMHAB"))
                if var_str:
                    self.msg2.setText(self.tr("Data cannot be converted to float."))
                    add_text = self.tr("First problematic data is ")
                    self.msg2.setDetailedText(add_text + var_str)
                else:
                    self.msg2.setText(self.tr("Data is empty or partially empty. Data is saved, but cannot be executed"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()

        return var

    def open_rech(self):
        """
        Open the additional research tab, which can be used to create Tab with more experimental contents.

        Indeed, it is possible to show extra tab in HABBY. These supplementary tab correspond to open for researcher.
        The plan is that these options are less tested than other mainstream options. It is not clear yet what
        will be added to these options, but the tabs are already there when it will be needed.
        """
        self.rechmain = True
        self.central_widget.tab_widget.addTab(self.central_widget.other_tab, self.tr("Research 1"))
        self.central_widget.tab_widget.addTab(self.central_widget.other_tab2, self.tr("Research 2"))

    def close_rech(self):
        """
            Close the additional research menu (see open_rech for more information). For the moment, ONLY works with
            two research tabs. Modify this function if a different number of tab is needed.
        """
        if self.rechmain:
            for i in range(self.central_widget.tab_widget.count(), self.central_widget.tab_widget.count()-3, -1):
                self.central_widget.tab_widget.removeTab(i)
        self.rechmain = False

    def clear_log(self):
        """
        Clear the log in the GUI.
        """
        self.central_widget.l2.clear()
        self.central_widget.l2.setText(self.tr('Log erased in this window.<br>'))

    def do_log(self, save_log):
        """
        Save or not save the log

        :param save_log: an int which indicates if the log should be saved or not

        *   0: do not save log
        *   1: save the log in the .log file and restart file
        """
        if save_log == 0:
            t = self.central_widget.l2.text()
            self.central_widget.l2.setText(t+self.tr('This log will not be saved anymore in the .log file. <br>')
                                           + self.tr('This log will not be saved anymore in the restart file. <br>'))
            self.central_widget.logon = False
        if save_log == 1:
            t = self.central_widget.l2.text()
            self.central_widget.l2.setText(t + self.tr('This log will be saved in the .log file.<br> '
                                                       'This log will be saved in the restart file. <br>'))
            self.central_widget.logon = True

        # save the option in the xml file
        fname = os.path.join(self.path_prj, self.name_prj +'.xml')
        doc = ET.parse(fname)
        root = doc.getroot()
        savelog_child = root.find(".//Save_Log")
        try:
            savelog_child.text = str(self.central_widget.logon)
            doc.write(fname)
        except AttributeError:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Log Info"))
            self.msg2.setText( \
                self.tr("Information related to the .log file are incomplete. Please check."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

    def erase_pict(self):
        """
        All files contained in the folder indicated by path_im will be deleted.

        From the menu of HABBY, it is possible to ask to erase all files in the folder indicated by path_im
        (usually figure_HABBY). Of course, this is a bit dangerous. So the function asks the user for confirmation.
        However, it is practical because you do not have to go to the folder to erase all the images when there
        are too many of them.
        """
        # get path im
        path_im = '.'
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Figure")
            if child is None:
                path_im = os.path.join(self.path_prj, 'figures')
            else:
                path_im = os.path.join(self.path_prj, child.text)
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        # ask for confimation
        self.msg2.setIcon(QMessageBox.Warning)
        self.msg2.setWindowTitle(self.tr("Delete figure"))
        self.msg2.setText(
            self.tr("Are you sure that you want to delete all file in the folder: \n" + path_im))
        self.msg2.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        res = self.msg2.exec_()

        # delete
        if res == QMessageBox.Ok:
            filelist = [f for f in os.listdir(path_im)]
            for f in filelist:
                os.remove(os.path.join(path_im, f))
        # update substrate and hydro list
        self.central_widget.substrate_tab.drop_hyd.clear()
        self.central_widget.substrate_tab.drop_sub.clear()
        # log
        t = self.central_widget.l2.text()
        self.central_widget.l2.setText(t + self.tr('Images deleted. <br>'))

    def open_help(self):
        """
        This function open the html which form the help from HABBY. For the moment, it is the full documentation
        with all the coding detail, but we should create a new html or a new pdf file which would be more pratical
        for the user.
        """
        filename_help = os.path.join(os.getcwd(), "doc","_build", "html","index.html")
        print(filename_help)
        wbopen(filename_help)


class CreateNewProject(QWidget):
    """
    A class which is used to help the user to create a new project
    """
    save_project = pyqtSignal()
    """
    a signal to save the project
    """
    send_log = pyqtSignal(str, name='send_log')
    """
       A PyQt signal used to write the log
    """

    def __init__(self, lang, path_trans, file_langue, oldpath_prj):

        if oldpath_prj and os.path.isdir(oldpath_prj):
            self.default_fold = os.path.dirname(oldpath_prj)
        else:
            self.default_fold = os.getcwd()
        if self.default_fold == '':
            self.default_fold = os.getcwd()
        self.default_name = 'DefaultProj'
        super().__init__()

        self.init_iu()

    def init_iu(self):
        lg = QLabel(self.tr(" <b> Create a new project </b>"))
        l1 = QLabel(self.tr('Project Name: '))
        self.e1 = QLineEdit(self.default_name)
        l2 = QLabel(self.tr('Main Folder: '))
        self.e2 = QLineEdit(self.default_fold)
        button2 = QPushButton(self.tr('Set Folder'), self)
        button2.clicked.connect(self.setfolder)
        self.button3 = QPushButton(self.tr('Save project'))
        self.button3.clicked.connect(self.save_project)  # is a PyQtSignal
        self.button3.setStyleSheet("background-color: #47B5E6; color: white; font: bold")

        layoutl = QGridLayout()
        layoutl.addWidget(lg, 0, 0)
        layoutl.addWidget(l2, 1, 0)
        layoutl.addWidget(self.e2, 1, 1)
        layoutl.addWidget(button2, 1, 2)
        layoutl.addWidget(l1, 2, 0)
        layoutl.addWidget(self.e1, 2, 1)
        layoutl.addWidget(self.button3, 2, 2)
        
        self.setLayout(layoutl)

        self.setWindowTitle(self.tr('HABBY- New Project'))
        name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
        self.setWindowIcon(QIcon(name_icon))
        self.setGeometry(300, 300, 650, 100)

    def setfolder(self):
        """
        This function is used by the user to select the folder where the xml project file will be located.
        """
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), self.default_fold,
                                                    )  # check for invalid null parameter on Linuxgit
        # os.getenv('HOME')
        if dir_name != '':  # cancel case
            self.e2.setText(dir_name)
            self.send_log.emit('New folder selected for the project. \n')


class CentralW(QWidget):
    """
    This class create the different tabs of the programm, which are then used as the central widget by the class
    MainWindows.

    :param rech: A bollean which is True if the tabs for the "research option" are shown. False otherwise.
    :param path_prj: A string with the path to the project xml file
    :param name_prj: A string with the name of the project
    :param lang_bio: A string with the word 'English', 'French' (or an other language). It is used to find the langugage
           in which the biological info should be shown. So lang_bio should have the same form than the attribute
           "langugage" in xml preference file.

    **Technical comments**

    In the attribute list, there are a series of name which finish by “tab” such as stathab_tab or output_tab. Each of
    these names corresponds to one tab and a new name should be added to the attributes to add a new tab.

    During the creation of the class, each tab is created. Then, the signals to show the figures are connected between this
    class and all the children classes which need it (often this are the classes used to load the hydrological data). When a
    class emits the signal “show_fig”, CentralW collect this signal and show the figure, using the showfig function.

    Show_fig is mostly a “plt.show()”. To avoid problem between matplotlib and PyQt, it is however important that
    matplotlib use the backend “Qt5Agg” in the .py where the “plt.plot” is called. Practically, this means modifying
    the matplotlib import.

    Showfig shows only one figure. To show all existing figures, one can call the function show_fig2 from the menu.
    Show_fig2 call the instance child_win of the class ShowImageW to open a new Windows with all figure. However,
    this would only show the figure without any option for the zoom.

    Then we call a function which connects all the signals from each class which need to write into the log. It is a good
    policy to create a “send_log” signal for each new important class. As there are a lot of signal to connect, these
    connections are written in the function “connect_signal_log”, where the signal for a new class can be added.

    When this is done, the info for the general tab (created before) is filled. If the user has opened a project in HABBY
    before, the name of the project and the other info related to it will be shown on the general tab. If the general
    tab is modified in the class WelcomeW(), this part of the code which fill the general tab will probably needs to
    be modified.

    Finally, each tab is filled. The tabs have been created before, but there were empty. Now we fill each one with the
    adequate widget. This is the link with many of the other classes that we describe below. Indeed, many of the widget
    are based on more complicated classes created for example in hydro_GUI_2.py.

    Then, we create an area under it for the log. Here HABBY will write various infos for the user. Two things to note
    here: a) we should show the end of the scroll area. b) The size of the area should be controlled and not be
    changing even if a lot of text appears. Hence, the setSizePolicy should be fixed.

    The write_log() and write_log_file() method are explained in the section about the log.
    """

    def __init__(self, rech, path_prj, name_prj, lang_bio):

        super().__init__()
        self.msg2 = QMessageBox()
        self.tab_widget = QTabWidget()
        self.name_prj_c = name_prj
        self.path_prj_c = path_prj

        self.welcome_tab = WelcomeW(path_prj, name_prj)
        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            self.statmod_tab = estimhab_GUI.EstimhabW(path_prj, name_prj)
            self.hydro_tab = hydro_GUI_2.Hydro2W(path_prj, name_prj)
            self.substrate_tab = hydro_GUI_2.SubstrateW(path_prj, name_prj)
            self.stathab_tab = stathab_GUI.StathabW(path_prj, name_prj)
            self.output_tab = output_fig_GUI.outputW(path_prj, name_prj)
            self.bioinfo_tab = bio_info_GUI.BioInfo(path_prj, name_prj, lang_bio)
            self.fstress_tab = fstress_GUI.FstressW(path_prj, name_prj)
            self.chronicle_tab = chronicle_GUI.ChroniqueGui(path_prj, name_prj)
            self.update_merge_for_chronicle()

        self.scroll = QScrollArea()
        self.rech = rech
        self.logon = True  # do we save the log in .log file or not
        self.child_win = ShowImageW(self.path_prj_c, self.name_prj_c)  # an extra windows to show figures
        self.vbar = self.scroll.verticalScrollBar()
        self.l2 = QLabel(self.tr('Log of HABBY started. <br>'))  # where the log is show
        self.max_lengthshow = 90
        pyqtRemoveInputHook()
        self.old_ind_tab = 0
        self.opttab = 8 # the position of the option tab

        self.init_iu()

    def init_iu(self):
        """
        A function to initialize an instance of CentralW. Called by __init___().
        """

        # create all the widgets
        self.other_tab = EmptyTab()
        self.other_tab2 = EmptyTab()

        # connect signal figure and drop-down menus
        self.connect_signal_fig_and_drop()

        # connect signal for the log
        self.connect_signal_log()

        # fill the QComboBox on the substrate and hydro tab
        self.update_hydro_hdf5_name()

        # get the log option (should we take log or not)
        fname = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')
        if not os.path.isdir(self.path_prj_c) \
                or not os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Project file not found"))
            self.msg2.setText(self.tr("The xml project file does not exists. \n Create or open a new project."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
            self.msg2.setWindowIcon(QIcon(name_icon))
            self.msg2.show()
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            logon_child = root.find(".//Save_Log")
            if logon_child == 'False' or logon_child == 'false':
                self.logon = False  # is True by default

        # add the widgets to the list of tab if a project exist
        self.add_all_tab()

        # Area to show the log
        # add two Qlabel l1 ad l2 , with one scroll for the log in l2
        self.l1 = QLabel(self.tr('HABBY says:'))
        self.l2.setAlignment(Qt.AlignTop)
        self.l2.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.l2.setTextFormat(Qt.RichText)
        self.l2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # see the end of the log first
        self.vbar.rangeChanged.connect(self.scrolldown)
        self.scroll.setWidget(self.l2)
        # to have the Qlabel at the right size
        self.scroll.setWidgetResizable(True)
        # colors
        self.scroll.setStyleSheet('background-color: white')
        self.vbar.setStyleSheet('background-color: lightGrey')

        self.welcome_tab.save_info_signal.connect(self.save_info_projet)
        # save the desription and the figure option if tab changed
        self.tab_widget.currentChanged.connect(self.save_on_change_tab)

        # layout
        self.layoutc = QGridLayout()
        self.layoutc.addWidget(self.tab_widget, 1, 0)
        self.layoutc.addWidget(self.l1, 2, 0)
        self.layoutc.addWidget(self.scroll, 3, 0)
        self.setLayout(self.layoutc)

    def scrolldown(self):
        """
        Move the scroll bar to the bottow if the ScollArea is getting bigger
        """
        self.vbar.setValue(self.vbar.maximum())

    def add_all_tab(self):
        """
        This function add the different tab to habby (used by init and by save_project). Careful, if you change the
        position of the Option tab, you should also modify the varaible self.opttab in init
        """
        fname = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')
        if os.path.isfile(fname) and self.name_prj_c != '':
            # order matters here
            self.tab_widget.addTab(self.welcome_tab, self.tr("Start"))
            self.tab_widget.addTab(self.hydro_tab, self.tr("Hydraulic"))
            self.tab_widget.addTab(self.chronicle_tab, self.tr("Chronicles"))
            self.tab_widget.addTab(self.substrate_tab, self.tr("Substrate"))
            self.tab_widget.addTab(self.bioinfo_tab, self.tr("Habitat Calc."))
            self.tab_widget.addTab(self.statmod_tab, self.tr("ESTIMHAB"))
            self.tab_widget.addTab(self.stathab_tab, self.tr("STATHAB"))
            self.tab_widget.addTab(self.fstress_tab, self.tr("FStress"))
            self.tab_widget.addTab(self.output_tab, self.tr("Options"))

            if self.rech:
                self.tab_widget.addTab(self.other_tab, self.tr("Research 1"))
                self.tab_widget.addTab(self.other_tab2, self.tr("Research 2"))
            self.welcome_tab.lowpart.setEnabled(True)
        # if the project do not exist, do not add new tab
        else:
            self.tab_widget.addTab(self.welcome_tab, self.tr("Start"))
            self.welcome_tab.lowpart.setEnabled(False)

    def showfig(self):
        """
        A small function to show the last figure
        """

        # check if there is a path where to save the image
        filename_path_pro = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//" + 'Path_Figure')
            if child is not None:
                self.path_im = os.path.join(self.path_prj_c,child.text)

        # if os.name == 'nt':  # windows
        matplotlib.interactive(True)
        plt.show()
        # else:
        #     num_fig = plt.get_fignums()
        #     self.all_fig_widget = []
        #     for id,n in enumerate(num_fig):
        #         canvas = FigureCanvasQTAgg(plt.figure(n))  # plt.gcf()
        #         myfigwig = QWidget()
        #         self.all_fig_widget.append(myfigwig)
        #         canvas.setParent(self.all_fig_widget[id])
        #         menu = NavigationToolbar2QT(canvas, self.all_fig_widget[id])
        #         self.all_fig_widget[id].layout = QGridLayout()
        #         self.all_fig_widget[id].layout.addWidget(menu, 0, 0)
        #         self.all_fig_widget[id].layout.addWidget(canvas, 1, 0)
        #         self.all_fig_widget[id].setLayout(self.all_fig_widget[id].layout)
        #         self.all_fig_widget[id].show()

    def showfig2(self):
        """
        A function to see all saved figures without possibility to zoom
        """
        self.child_win.update_namefig()
        self.child_win.selectionchange(-1)
        self.child_win.show()

    def closefig(self):
        """
        A small function to close the images open in HABBY and managed by matplotlib
        """
        plt.close('all')

    def optfig(self):
        """
        A small function which open the output tab.
        """
        self.tab_widget.setCurrentIndex(self.opttab)

    def connect_signal_log(self):
        """
        connect all the signal linked to the log. This is in a function only to improve lisibility.
        """

        self.welcome_tab.send_log.connect(self.write_log)

        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            self.hydro_tab.send_log.connect(self.write_log)
            self.hydro_tab.hecras1D.send_log.connect(self.write_log)
            self.hydro_tab.hecras2D.send_log.connect(self.write_log)
            self.hydro_tab.rubar2d.send_log.connect(self.write_log)
            self.hydro_tab.rubar1d.send_log.connect(self.write_log)
            self.hydro_tab.sw2d.send_log.connect(self.write_log)
            self.hydro_tab.telemac.send_log.connect(self.write_log)
            self.substrate_tab.send_log.connect(self.write_log)
            self.statmod_tab.send_log.connect(self.write_log)
            self.stathab_tab.send_log.connect(self.write_log)
            self.hydro_tab.riverhere2d.send_log.connect(self.write_log)
            self.hydro_tab.mascar.send_log.connect(self.write_log)
            self.child_win.send_log.connect(self.write_log)
            self.output_tab.send_log.connect(self.write_log)
            self.bioinfo_tab.send_log.connect(self.write_log)
            self.hydro_tab.habbyhdf5.send_log.connect(self.write_log)
            self.hydro_tab.lammi.send_log.connect(self.write_log)
            self.fstress_tab.send_log.connect(self.write_log)
            self.chronicle_tab.send_log.connect(self.write_log)

    def connect_signal_fig_and_drop(self):
        """
        This function connect the PyQtsignal to show figure and to connect the log. It is a function to
        improve lisibility.
        """

        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            # connect signals save figures
            self.hydro_tab.hecras1D.show_fig.connect(self.showfig)
            self.hydro_tab.hecras2D.show_fig.connect(self.showfig)
            self.hydro_tab.telemac.show_fig.connect(self.showfig)
            self.hydro_tab.rubar2d.show_fig.connect(self.showfig)
            self.hydro_tab.rubar1d.show_fig.connect(self.showfig)
            self.hydro_tab.sw2d.show_fig.connect(self.showfig)
            self.hydro_tab.lammi.show_fig.connect(self.showfig)
            self.hydro_tab.habbyhdf5.show_fig.connect(self.showfig)
            self.substrate_tab.show_fig.connect(self.showfig)
            self.statmod_tab.show_fig.connect(self.showfig)
            self.stathab_tab.show_fig.connect(self.showfig)
            self.hydro_tab.riverhere2d.show_fig.connect(self.showfig)
            self.hydro_tab.mascar.show_fig.connect(self.showfig)
            self.fstress_tab.show_fig.connect(self.showfig)
            self.bioinfo_tab.show_fig.connect(self.showfig)

            # connect signals to update the drop-down menu in the substrate tab when a new hydro hdf5 is created
            self.hydro_tab.hecras1D.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.hecras2D.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.telemac.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.rubar2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.rubar1d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.sw2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.riverhere2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.mascar.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.habbyhdf5.drop_hydro.connect(self.update_hydro_hdf5_name)

            # connect signal to update the merge file
            self.bioinfo_tab.get_list_merge.connect(self.update_merge_for_chronicle)
            self.chronicle_tab.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.substrate_tab.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.hydro_tab.lammi.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.hydro_tab.habbyhdf5.drop_merge.connect(self.bioinfo_tab.update_merge_list)

    def write_log(self, text_log):
        """
        A function to write the different log. Please read the section of the doc on the log.

        :param text_log: the text which should be added to the log (a string)

        *   if text_log start with # -> added it to self.l2 (QLabel) and the .log file (comments)
        *   if text_log start with restart -> added it restart_nameproject.txt
        *   if text_log start with WARNING -> added it to self.l2 (QLabel) and the .log file
        *   if text_log start with ERROR -> added it to self.l2 (QLabel) and the .log file
        *   if text_log start with py -> added to the .log file (python command)
        *   if text_log starts with Process -> Text added to the StatusBar only
        *   if text_log == "clear status bar" -> the status bar is cleared
        *   if text_log start with nothing -> just print to the Qlabel
        *   if text_log out from stdout -> added it to self.l2 (QLabel) and the .log file (comments)

        if logon = false, do not write in log.txt
        """

        if self.name_prj_c == '':
            return
        # read xml file to find the path to the log file
        fname = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')
        if os.path.isfile(fname):
            doc = ET.parse(fname)
            root = doc.getroot()
            # python-based log
            child_logfile = root.find(".//File_Log")
            if child_logfile is not None:
                pathname_logfile = os.path.join(self.path_prj_c, child_logfile.text)
            else:
                t = self.l2.text()
                self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: The "
                                    "log file is not indicated in the xml file. No log written. </br> <br>")
                return
            # restart log
            child_logfile = root.find(".//File_Restart")
            if child_logfile is not None:
                pathname_restartfile = os.path.join(self.path_prj_c, child_logfile.text)
            else:
                t = self.l2.text()
                self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: The "
                                    "restart file is not indicated in the xml file. No log written. </br> <br>")
                return
        else:
            # if only one tab, project not open, so it is normal that no log can be written.
            if self.tab_widget.count() > 1:
                t = self.l2.text()
                self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: The project file is not "
                                    "found. no Log written. </br> <br>")
            return

        # add comments to Qlabel and .log file
        if text_log[0] == '#':
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#000000'>" + text_log[1:] + '</br><br>')
            self.write_log_file(text_log, pathname_logfile)
        # add python code to the .log file
        elif text_log[:2] == 'py':
            self.write_log_file(text_log[2:], pathname_logfile)
        # add restart command to the restart file
        elif text_log[:7] == 'restart':
            self.write_log_file(text_log[7:], pathname_restartfile)
        elif text_log[:5] == 'Error' or text_log[:6] == 'Erreur':
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#FF0000'>" + text_log + ' </br><br>')  # error in red
            self.write_log_file('# ' +text_log, pathname_logfile)
        # add warning
        elif text_log[:7] == 'Warning':
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#FF8C00'>" + text_log + ' </br><br>')  # warning in orange
            self.write_log_file('# ' + text_log, pathname_logfile)
        # update to check that processus is alive
        elif text_log[:7] == 'Process':
            self.parent().statusBar().showMessage(text_log)
        elif text_log == 'clear status bar':
            self.parent().statusBar().clearMessage()
        # other case not accounted for
        else:
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#000000'>" + text_log + '</br><br>')\

    def write_log_file(self, text_log, pathname_logfile):
        """
        A function to write to the .log text. Called by write_log.

        :param text_log: the text to be written (string)
        :param pathname_logfile: the path+name where the log is
        """
        if self.logon:
            if os.path.isfile(pathname_logfile):
                with open(pathname_logfile, "a", encoding='utf8') as myfile:
                    myfile.write('\n' + text_log)
            elif self.name_prj_c == '':
                return
            else:
                t = self.l2.text()
                self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: Log file not found. New log created. </br> <br>")
                shutil.copy(os.path.join('src_GUI', 'log0.txt'),
                            os.path.join(self.path_prj_c, self.name_prj_c + '.log'))
                shutil.copy(os.path.join('src_GUI', 'restart_log0.txt'),
                            os.path.join(self.path_prj_c,'restart_' + self.name_prj_c + '.log'))
                with open(pathname_logfile, "a", encoding='utf8') as myfile:
                    myfile.write("    name_projet = " + self.name_prj_c + "'\n")
                with open(pathname_logfile, "a", encoding='utf8') as myfile:
                    myfile.write("    path_projet = " + self.path_prj_c + "'\n")
                with open(pathname_logfile, "a", encoding='utf8') as myfile:
                    myfile.write('\n' + text_log)

        return

    def update_hydro_hdf5_name(self):
        """
        This is a short function used to read all the hydrological data (contained in an hdf5 files) available in
        one project.

        When these files are read, they are added to the drop-down menu on the hydrological tab an on the substrate tab.
        On the substrate Tab, if we have more than one hdf5 file, the first item is blank to insure that the user
        actively choose the hdf5 to reduce the risk of error (Otherwise the user might merge the substrate and
        an hydrological hdf5 without seeing that he needs to select the right hydrological hdf5).

        This tasks should be in a function because an update to this list can be triggered by the loading of a new
        hydrological data. The class Hydro2W() and substrateW() noticed this through the signal drop_hydro
        send by the hydrological class. The signal drop_hydro is connected to this function is in the class
        CentralW in MainWindows.py.

        """

        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            # clear QCombox from Hydro2W() and Substratew()
            self.substrate_tab.drop_hyd.clear()
            self.hydro_tab.drop_hyd.clear()

            # get the hdf5 path
            filename_path_pro = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')
            if os.path.isfile(filename_path_pro):
                doc = ET.parse(filename_path_pro)
                root = doc.getroot()
                child = root.find(".//Path_Hdf5")
                if child is None:
                    path_hdf5 = os.path.join(self.path_prj_c, self.name_prj_c)
                else:
                    path_hdf5 = os.path.join(self.path_prj_c, child.text)
            else:
                self.write_log(self.tr('Error: Project is not saved. \n'))
                return

            # read name
            self.hyd_name = self.substrate_tab.read_attribute_xml('hdf5_hydrodata')
            self.hyd_name = list(reversed(self.hyd_name.split(',')))
            if not os.path.isabs(self.hyd_name[0]):
                for i in range(0, len(self.hyd_name)):
                    self.hyd_name[i] = os.path.join(path_hdf5, self.hyd_name[i])
            hyd_name2 = []  # we might have unexisting hdf5 file in the xml project file
            for i in range(0, len(self.hyd_name)):
                if os.path.isfile(self.hyd_name[i]):
                    hyd_name2.append(self.hyd_name[i])
            self.hyd_name = hyd_name2
            self.substrate_tab.hyd_name = self.hyd_name

            # add new name to the QComboBox()
            for i in range(0, len(self.hyd_name)):
                if i == 0 and len(self.hyd_name) > 1:
                    self.substrate_tab.drop_hyd.addItem(' ')
                if os.path.isfile(self.hyd_name[i]):
                    if len(self.hyd_name[i]) > self.max_lengthshow:
                        self.substrate_tab.drop_hyd.addItem(os.path.basename(self.hyd_name[i][:self.max_lengthshow]))
                        self.hydro_tab.drop_hyd.addItem(os.path.basename(self.hyd_name[i][:self.max_lengthshow]))
                    else:
                        self.substrate_tab.drop_hyd.addItem(os.path.basename(self.hyd_name[i]))
                        self.hydro_tab.drop_hyd.addItem(os.path.basename(self.hyd_name[i]))

    def save_info_projet(self):
        """
        This function is used to save the description of the project and the username in the xml project file
        """

        # username and description
        e4here = self.welcome_tab.e4
        self.username_prj = e4here.text()
        e3here = self.welcome_tab.e3
        self.descri_prj = e3here.toPlainText()

        fname = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')

        if not os.path.isfile(fname):
            self.write_log('Error: The project file is not found. \n')
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            user_child = root.find(".//User_Name")
            des_child = root.find(".//Description")
            if user_child is not None:
                user_child.text = self.username_prj
            else:
                self.write_log("xml file miss one attribute (1) \n")
            if des_child is not None:
                des_child.text = self.descri_prj
            else:
                self.write_log("xml file miss one attribute (2) \n")
            doc.write(fname)

    def save_on_change_tab(self):
        """
        This function is used to save the data when the tab are changed. In most tab this is not needed as data
        is alredy saved by another functions. However, it is useful for the Welcome Tab and the Option Tab.
        This function can be modified if needed for new tabs.

        Careful, the order of the tab is important here.
        """

        if self.old_ind_tab == 0:
            self.save_info_projet()
        elif self.old_ind_tab == self.opttab:
            self.output_tab.save_option_fig()
        self.old_ind_tab = self.tab_widget.currentIndex()

    def update_merge_for_chronicle(self):
        """
        This function looks up the list of merge file in the QComBox in the bio_info tab and copy this
        list to the QCombobox in chronicle_GUI. So the two lists of merge file are the same
        """
        self.chronicle_tab.hdf5_merge = self.bioinfo_tab.hdf5_merge
        self.chronicle_tab.merge_all.clear()
        for i in range(0, self.bioinfo_tab.m_all.count()):
            if self.bioinfo_tab.m_all.itemText(i)[:7] != 'Chronic':
                self.chronicle_tab.merge_all.addItem(self.bioinfo_tab.m_all.itemText(i))
                self.chronicle_tab.merge_all.setItemData(i, self.bioinfo_tab.tooltip[i], Qt.ToolTipRole)


class WelcomeW(QWidget):
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
    " A signal for MainWindows to open an exisiting project"
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
        self.imname = os.path.join('translation','banner.jpg') # image shoulfd in the translation folder
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
        l0 = QLabel(self.tr('<b>Start working with HABBY </b>'))
        l0.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        l0.setFont(font)
        buttono = QPushButton(self.tr('Open Exisiting Project'), self)
        buttono.clicked.connect(self.open_proj.emit)
        buttons = QPushButton(self.tr('New Project'), self)
        buttons.clicked.connect(self.new_proj_signal.emit)
        spacerleft = QSpacerItem(200, 1)
        spacerright = QSpacerItem(120, 1)
        spacer2 = QSpacerItem(1, 70)
        highpart = QWidget()  # used to regroup all QWidgt in the first part of the Windows

        # general into to put in the xml .prj file
        lg = QLabel(self.tr(" <b> Current Project </b>"))
        l1 = QLabel(self.tr('Project Name: '))
        self.e1 = QLabel(self.name_prj)
        l2 = QLabel(self.tr('Main Folder: '))
        self.e2 = QLabel(self.path_prj)
        button2 = QPushButton(self.tr('Set Folder'), self)
        button2.clicked.connect(self.setfolder2)
        button2.setToolTip( self.tr('Move the project to a new location. '
                                    'The data might be long to copy if the project folder is large.'))
        l3 = QLabel(self.tr('Description: '))
        self.e3 = QTextEdit()
        # this is used to save the data if the QLineEdit is going out of Focus
        self.e3.installEventFilter(self.outfocus_filter)
        self.outfocus_filter.outfocus_signal.connect(self.save_info_signal.emit)
        l4 = QLabel(self.tr('User Name: '))
        self.e4 = QLineEdit()
        # this is used to save the data if the QLineEdit is going out of Focus
        self.e4.installEventFilter(self.outfocus_filter)
        self.outfocus_filter.outfocus_signal.connect(self.save_info_signal.emit)
        self.lowpart = QWidget()

        # background image
        pic = QLabel()
        pic.setMaximumSize(1000, 200)
        # use full ABSOLUTE path to the image, not relative
        pic.setPixmap(QPixmap(os.path.join(os.getcwd(), self.imname)).scaled(800, 500))  # 800 500
        # pic.setPixmap(QPixmap(os.path.join(os.getcwd(), self.imname)).scaled(150, 150))  # 800 500

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # if the directoy to the project do not exist, leave the general tab empty
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isdir(self.path_prj) or not os.path.isfile(fname):
            pass
        # otherwise, fill it
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            user_child = root.find(".//User_Name")
            des_child = root.find(".//Description")
            self.e4.setText(user_child.text)
            self.e3.setText(des_child.text)

        # layout (in two parts)
        layout2 = QGridLayout()
        layouth = QGridLayout()
        layoutl = QGridLayout()

        layouth.addItem(spacerleft, 1, 0)
        layouth.addItem(spacerright, 1, 5)
        layouth.addWidget(l0, 0, 1)
        layouth.addWidget(buttono, 2, 1)
        layouth.addWidget(buttons, 3, 1)
        layouth.addItem(spacer2, 5, 2)
        highpart.setLayout(layouth)

        layoutl.addWidget(lg, 0, 0)
        layoutl.addWidget(l1, 1, 0)
        layoutl.addWidget(self.e1, 1, 1)
        layoutl.addWidget(l2, 2, 0)
        layoutl.addWidget(self.e2, 2, 1)
        layoutl.addWidget(button2, 2, 2)
        layoutl.addWidget(l4, 3, 0)
        layoutl.addWidget(self.e4, 3, 1)
        layoutl.addWidget(l3, 4, 0)
        layoutl.addWidget(self.e3, 4, 1)
        self.lowpart.setLayout(layoutl)

        layout2.addWidget(pic, 0, 0)
        layout2.addWidget(highpart, 0, 0)
        layout2.addWidget(self.lowpart, 1, 0)
        self.setLayout(layout2)

    def open_example(self):
        """
        This function will be used to open a project example for HABBY, but the example is not prepared yet. NOT DONE
        AS IT IS COMPLICATED TO INSTALL A EXAMPLE PROJECT. WINDOWS SAVED PROGRAM IN FOLDER WITHOUT WRITE PERMISSIONS.
        """
        self.send_log.emit('Warning: No example prepared yet')

    def setfolder2(self):
        """
        This function is used by the user to select the folder where the xml project file will be located.
        This is used in the case where the project exist already. A similar function is in the class CreateNewProject()
        for the case where the project is new.
        """
        # check for invalid null parameter on Linuxgit
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        if dir_name != '':  # cancel case
            self.e2.setText(dir_name)
            self.send_log.emit('New folder selected for the project. \n')
        else:
            return

        # if the project exist and the project name has not changed
        # ,change the project path in the xml file and copy the xml at the chosen location
        # if a project directory exist copy it as long as no project directory exist at the end location
        path_old = self.path_prj
        fname_old = os.path.join(path_old, self.name_prj + '.xml')
        new_path = os.path.join(dir_name, self.name_prj)
        if os.path.isfile(fname_old) and self.e1.text() == self.name_prj:
            # write new project path
            if not os.path.exists(new_path):
                self.path_prj = new_path
                doc = ET.parse(fname_old)
                root = doc.getroot()
                path_child = root.find(".//Path_Projet")
                path_child.text = self.path_prj  # new name
                fname = os.path.join(self.path_prj, self.name_prj + '.xml')
                try:
                    shutil.copytree(path_old, self.path_prj)
                except shutil.Error:
                    self.send_log.emit('Could not copy the project. Permission Error? \n')
                    return
                self.send_log.emit(' The files in the project folder have been copied to the new location \n')
                try:
                    shutil.copyfile(fname_old, os.path.join(self.path_prj, self.name_prj + '.xml'))
                except shutil.Error:
                    self.send_log.emit('Could not copy the project. Permission Error? \n')
                    return
                doc.write(fname)
                self.e2.setText(self.path_prj)
                self.save_signal.emit()  # if not project folder, will create one
            else:
                self.send_log.emit('Error: A project with the same name exists at the new location. '
                                   'Project not saved \n')
                self.e2.setText(path_old)
                return
        # if the project do not exist or has a different name than before, save a new project
        else:
            self.save_signal.emit()


class EmptyTab(QWidget):
    """
    This class is  used to fill empty tabs with something during the developement.
    It will not be use in the final version.
    """

    def __init__(self):
        super().__init__()
        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization.
        """
        button1 = QPushButton(self.tr('I am a tab'), self)
        button1.clicked.connect(self.addtext)

        button2 = QPushButton(self.tr('I am really'), self)
        button2.clicked.connect(self.addtext)

        layout1 = QGridLayout()
        layout1.addWidget(button1, 0, 0)
        layout1.addWidget(button2, 1, 0)
        self.setLayout(layout1)

    def addtext(self):
        """
        This function print a string on the command line. This is useful if you need to check if a button (or similar).
        is connected.
        """
        print('Text Text and MORE Text')


class ShowImageW(QWidget):
    """
    The widget which shows the saved images. Used only to show all the saved figure together iwhtout zoom or other
    options. Not really used anymore in HABBY but it still there as it can be useful in the future.

    **Technical comments**

    The ShowImageW() class is used to show all the figures created by HABBY. It is a class which can only be
    called from the menu (In Option/Option Image). This is not the usual way of opening a figure which is usually done
    by plt.show from matplotlib. This is the way to look at all figures  together, which can be useful, even if zooming
    is not possible anymore.

    To show all image, HABBY open a separate window and show the saved image in .png format.  Currently, the figures
    shown are in .png, but other formats could be used. For this, one can change the variable self.imtype.

    An important point for the ShowImageW  class  is where the images were saved by the functions which created them.
    In HABBY, all figures are saved in the same folder called “path_im”. One “path_im” is chosen at the start of each
    project. By default, it is the folder “Figure_Habby”, but the user can modify this folder in the window created by
    ShowImageW(). The function for this is called “change_folder”, also in ShowImageW(). The path_im is written in
    the xml project file. The different functions which create image read this path and send the figure created
    to this folder. ShowImageW() reads all  figure of “.png” type in the” path_im” folder and show the most recent
    figure. The user can use the drop-down menu to choose to see another figure. The names of the figure are added to
    the drop-down menu in the function update_namefig. The function "selectionchange" changes the figure shown based
    on the user action.

    """
    send_log = pyqtSignal(str, name='send_log')
    """
        A PyQt signal used to write the log
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.image_list = QComboBox()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.label_im = QLabel()
        self.w = 200  #size of the image (see if we let some options for this)
        self.h = 200
        self.imtype = '*.png'
        self.path_im = os.path.join(self.path_prj, self.name_prj + r'/figures')
        self.msg2 = QMessageBox()
        self.init_iu()
        self.all_file = []

    def init_iu(self):
        """
        Used in the initialization.
        """

        # check if there is a path where to save the image
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//" + 'Path_Figure')
            if child is not None:
                self.path_im = child.text

        # find all figures and add them to the menu ComboBox
        self.image_list.activated.connect(self.selectionchange)

        # create the label which will show the figure
        self.label_im.setGeometry(QRect(0, 0, self.w, self.h))
        self.label_im.setScaledContents(True)
        self.but1 = QPushButton('Change Folder')
        self.but1.clicked.connect(self.change_folder)

        self.setWindowTitle(self.tr('ALL FIGURES'))
        self.setGeometry(200, 200, 500, 300)
        #self.setMaximumSize(100, 100)

        # layout
        self.layout4 = QGridLayout()
        self.sublayout = QGridLayout()
        self.layout4.addLayout(self.sublayout, 0, 0)
        self.sublayout.addWidget(self.but1, 0, 1)
        self.sublayout.addWidget(self.image_list, 0, 0)
        self.layout4.addWidget(self.label_im, 1, 0)
        self.setLayout(self.layout4)

    def selectionchange(self, i):
        """
        A function to change the figure shown by ShowImageW()
        :return:
        """
        if not self.all_file:
            return
        else:
            namefile_im = os.path.join(self.path_im, self.all_file[i])
            pixmap = QPixmap(namefile_im).scaled(800, 500)
            self.label_im.setPixmap(pixmap)
            self.label_im.show()

    def change_folder(self):
        """
        A function to change the folder where are stored the image (i.e., the path_im)
        """

        self.path_im = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        if self.path_im == '':
            return
        self.update_namefig()
        self.send_log.emit('# New folder selected to save figures.\n')
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Change Folder"))
            self.msg2.setText( \
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        else:
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            # geo data
            child1 = root.find('.//Path_Figure')
            if child1 is None:
                child1 = ET.SubElement(root, 'Path_Figure')
                child1.text = self.path_im
            else:
                child1.text = self.path_im
            doc.write(filename_path_pro)
            self.selectionchange(1)

    def update_namefig(self):
        """
        This function add the different figure name to the drop-down list.
        """

        self.image_list.clear()
        if not self.path_im:
            self.path_im = os.path.join(self.path_prj, self.name_prj)
        self.all_file = glob.glob(os.path.join(self.path_im, self.imtype))
        if not self.all_file:
            self.send_log.emit('Warning: No figure was found at the path:' + self.path_im + '\n')
            return
        self.all_file.sort(key=os.path.getmtime)  # the newest figure on the top
        if self.all_file[0] != 'Available figures':
            first_name = self.tr('Available figures')  # variable needed for the translation
            self.all_file = [first_name] + self.all_file
        all_file_nice = self.all_file
        # make the name look nicer
        for i in range(0, len(all_file_nice)):
            all_file_nice[i] = all_file_nice[i].replace(self.path_im, "")
            all_file_nice[i] = all_file_nice[i].replace("\\", "")
            all_file_nice[i] = all_file_nice[i].replace("/", "")
        self.image_list.addItems(all_file_nice)


class MyFilter(QObject):
    """
    This is a filter which is used to know when a QWidget is going out of focus. Practically this is used
    if the user goes away from a QLineEdit. If this events happends, the project is autmatically saved with the new
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


if __name__ == '__main__':
    pass



