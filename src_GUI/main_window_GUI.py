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
from functools import partial
from platform import system as operatingsystem
from subprocess import call
import urllib.request
import numpy as np

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from PyQt5.QtCore import QEvent, QObject, QTranslator, pyqtSignal, QSettings, Qt, pyqtRemoveInputHook
from PyQt5.QtWidgets import QMainWindow, QComboBox,QDialog, QApplication, QWidget, QPushButton, \
    QLabel, QGridLayout, QAction, QFormLayout, QVBoxLayout, QGroupBox, QSizePolicy, QTabWidget, QLineEdit, QTextEdit, QFileDialog, QMessageBox, QInputDialog, QMenu, QToolBar, QProgressBar
from PyQt5.QtGui import QPixmap, QIcon, QTextCursor
import qdarkstyle
from webbrowser import open as wbopen
import h5py
import matplotlib as mpl
mpl.use("Qt5Agg")  # backends and toolbar for pyqt5

from src_GUI import welcome_GUI
from src_GUI import estimhab_GUI
from src_GUI import hydro_sub_GUI
from src_GUI import stathab_GUI
from src_GUI import preferences_GUI
from src_GUI import data_explorer_GUI
from src_GUI import tools_GUI
from src_GUI import calc_hab_GUI
from src_GUI import fstress_GUI
from src_GUI.bio_model_explorer_GUI import BioModelExplorerWindow
from src import project_manag_mod
from habby import HABBY_VERSION
from src.user_preferences_mod import user_preferences


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
        self.version = HABBY_VERSION

        # user_preferences
        self.user_preferences = user_preferences

        # operating system
        self.operatingsystemactual = operatingsystem()

        # load user setting
        # self.settings = QSettings('irstea', 'HABBY' + str(self.version))
        # name_prj_set = self.settings.value('name_prj')
        # # print(name_prj_set)
        # name_path_set = self.settings.value('path_prj')
        # # print(name_path_set)
        # language_set = self.settings.value('language_code')
        name_prj_set = self.user_preferences.data["name_prj"]
        name_path_set = self.user_preferences.data["path_prj"]
        language_set = self.user_preferences.data["language"]
        self.actual_theme = self.user_preferences.data["theme"]

        # # to erase setting of older version
        # # add here the number of older version whose setting must be erased because they are not compatible
        # # it should be managed by innosetup, but do not work always
        # self.oldversion = [0.24]
        # for v in self.oldversion:
        #     if v != self.version:
        #         self.oldsettings = QSettings('irstea', 'HABBY' + str(v))
        #     self.oldsettings.clear()

        # # recent project: list of string
        # recent_projects_set = self.settings.value('recent_project_name')
        # recent_projects_path_set = self.settings.value('recent_project_path')
        recent_projects_set = self.user_preferences.data["recent_project_name"]
        recent_projects_path_set = self.user_preferences.data["recent_project_path"]
        if recent_projects_set:
            if len(recent_projects_set) > self.nb_recent:
                self.user_preferences.data["recent_project_name"] = recent_projects_set[-self.nb_recent + 1:]
                self.user_preferences.data["recent_project_path"] = recent_projects_path_set[-self.nb_recent + 1:]

        # set up translation
        self.languageTranslator = QTranslator()
        self.path_trans = os.path.abspath('translation')
        self.file_langue = [r'Zen_EN.qm', r'Zen_FR.qm', r'Zen_ES.qm']
        try:  # english, french, spanish
            if language_set == "english":
                self.lang = 0
            if language_set == "french":
                self.lang = 1
            if language_set == "spanish":
                self.lang = 2
        except:
            self.lang = 0
        self.app = QApplication.instance()
        self.app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[self.lang], self.path_trans)
        self.app.installTranslator(self.languageTranslator)

        # prepare the attributes, careful if change the Qsetting!
        self.msg2 = QMessageBox()
        if name_path_set:
            self.name_prj = name_prj_set
        else:
            self.name_prj = ''
        if name_path_set:
            self.path_prj = name_path_set
        else:
            self.path_prj = '.'
        # if xml project dont exist remove path and name
        if not os.path.isfile(os.path.join(self.path_prj, self.name_prj + ".xml")):
            self.name_prj = ''
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
        self.path_bio_default = os.path.join("biology", "models")

        # create the central widget
        if self.lang == 0:
            lang_bio = 'English'
        elif self.lang == 1:
            lang_bio = 'French'
        else:
            lang_bio = 'English'

        # set selected tabs
        self.physic_tabs, self.stat_tabs, self.research_tabs = self.user_preferences.data["selected_tabs"]

        self.central_widget = CentralW(self.physic_tabs,
                                       self.stat_tabs,
                                       self.research_tabs,
                                       self.path_prj,
                                       self.name_prj,
                                       lang_bio)

        self.msg2 = QMessageBox()

        # call the normal constructor of QWidget
        super().__init__()
        pyqtRemoveInputHook()

        # call an additional function during initialization
        self.init_ui()

    def init_ui(self):
        """ Used by __init__() to create an instance of the class MainWindows """

        # set window icon
        self.name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
        self.setWindowIcon(QIcon(self.name_icon))

        # position theme
        wind_position_x, wind_position_y, wind_position_w, wind_position_h = self.user_preferences.data["wind_position"]
        self.setGeometry(wind_position_x, wind_position_y, wind_position_w, wind_position_h)

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

        # right click
        self.create_menu_right_clic()
        self.central_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.central_widget.customContextMenuRequested.connect(self.show_menu_right_clic)

        self.setCentralWidget(self.central_widget)

        # preferences
        project_manag_mod.set_lang_fig(self.lang, self.path_prj, self.name_prj)
        self.preferences_dialog = preferences_GUI.PreferenceWindow(self.path_prj, self.name_prj, self.name_icon)
        self.preferences_dialog.send_log.connect(self.central_widget.write_log)

        # soft_information_dialog
        self.soft_information_dialog = SoftInformationDialog(self.path_prj, self.name_prj, self.name_icon, self.version)

        # bio_model_explorer_dialog
        self.bio_model_explorer_dialog = BioModelExplorerWindow(self, self.path_prj, self.name_prj, self.name_icon,
                                                                self.central_widget.data_explorer_tab.data_explorer_frame.plot_group.plot_process_list)
        self.bio_model_explorer_dialog.send_log.connect(self.central_widget.write_log)
        self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(self.central_widget.write_log)
        self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)

        # set theme
        if self.actual_theme == "classic":
            self.setthemeclassic()
        else:
            self.setthemedark()

        self.check_concurrency()
        self.show()

    def closeEvent(self, event):
        """
        This is the function which handle the closing of the program. It use the function end_concurrency() to indicate
        to other habby instances that we do not use a particular project anymore.

        We use os_exit instead of sys.exit so it also close the other thread if more than one is open.

        :param event: managed by the operating system.
        """
        isalive = self.process_alive(close=False, isalive=True)
        if isalive:
            qm = QMessageBox
            ret = qm.question(self,
                              self.tr(", ".join(isalive) + " still running"),
                              self.tr("Do you really want to leave HABBY ?\nAll alive processes and figure windows will be closed."),
                              qm.Yes | qm.No)
            if ret == QMessageBox.Yes:
                if event:  # if CTRL+Q : event == False
                    event.accept()
            else:
                if event:  # if CTRL+Q : event == False
                    event.ignore()
                return

        self.end_concurrency()

        # close all process plot
        if hasattr(self, "central_widget"):
            self.central_widget.closefig()

        # close all process data (security)
        self.process_alive(close=True, isalive=False)

        # save model selection calhab
        if hasattr(self.central_widget, "bioinfo_tab"):
            self.central_widget.bioinfo_tab.save_selected_aquatic_animal_list_calc_hab()

        # save settings
        if not self.isMaximized():
            self.user_preferences.data["wind_position"] = (self.geometry().x(),
                                                           self.geometry().y(),
                                                           self.geometry().width(),
                                                           self.geometry().height())
        self.user_preferences.data["theme"] = self.actual_theme
        self.user_preferences.data["selected_tabs"] = (self.physic_tabs, self.stat_tabs, self.research_tabs)
        self.user_preferences.save_user_preferences_json()

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
            filename = os.path.join(os.path.join(self.path_prj, 'hdf5'), 'check_concurrency.txt')
            if not os.path.isfile(filename):
                self.central_widget.write_log('Warning: Could not check if the project was open by '
                                              'another instance of HABBY (1) \n')
                if os.path.isdir(os.path.join(self.path_prj, 'hdf5')):
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
        This function indicates to the project folder than this project is not used anymore. Hence, this project
        can be used freely by an other instance of HABBY.
        """
        if self.name_prj is not None:

            # open the text file
            filename = os.path.join(os.path.join(self.path_prj, 'hdf5'), 'check_concurrency.txt')
            if not os.path.isfile(filename):
                self.central_widget.write_log('Warning: Could not check if the project was open by '
                                              'another instance of HABBY (3) \n')
                return

            try:
                with open(filename, 'wt') as f:
                    f.write('close')
            except IOError:
                return

    def fill_selected_models_listwidets(self):
        # get dict
        item_dict = self.bio_model_explorer_dialog.bio_model_infoselection_tab.item_dict

        if item_dict["source_str"] == "calc_hab":
            self.central_widget.bioinfo_tab.fill_selected_models_listwidets(item_dict)

        if item_dict["source_str"] == "stat_hab":
            self.central_widget.stathab_tab.fill_selected_models_listwidets(item_dict)

    def setlangue(self, nb_lang):
        """
        A function which change the language of the program. It changes the menu and the central widget.
        It uses the self.lang attribute which should be set to the new language before calling this function.

        :param nb_lang: the number representing the language (int)

        *   0 is for English
        *   1 for French
        *   2 for Spanish
        *   n for any additional language

        """

        # set the language
        self.lang = int(nb_lang)
        # get the old tab
        ind_tab = self.central_widget.tab_widget.currentIndex()
        # get hydraulic type open
        ind_hydrau_tab = 0
        if self.central_widget.tab_widget.count() != 1:
            ind_hydrau_tab = self.central_widget.hydro_tab.mod.currentIndex()
        # if plot process are open, close them
        if hasattr(self.central_widget, "data_explorer_tab"):
            if hasattr(self.central_widget.data_explorer_tab.data_explorer_frame, 'plot_process_list'):
                self.central_widget.data_explorer_tab.data_explorer_frame.plot_process_list.close_all_plot_process()
        # get a new translator
        self.app = QApplication.instance()
        self.app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[self.lang], self.path_trans)
        self.app.installTranslator(self.languageTranslator)

        # recreate new widget
        self.recreate_tabs_attributes()
        # if self.central_widget.tab_widget.count() == 1:
        #     self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)
        # else:
        #     self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)
        #     #if self.physic_tabs:
        #     self.central_widget.hydro_tab = hydro_sub_GUI.Hydro2W(self.path_prj, self.name_prj)
        #     if ind_hydrau_tab != 0:
        #         self.central_widget.hydro_tab.mod.setCurrentIndex(ind_hydrau_tab)
        #     self.central_widget.substrate_tab = hydro_sub_GUI.SubstrateW(self.path_prj, self.name_prj)
        #     self.central_widget.bioinfo_tab = calc_hab_GUI.BioInfo(self.path_prj, self.name_prj)
        #     self.central_widget.data_explorer_tab = data_explorer_GUI.DataExplorerTab(self.path_prj, self.name_prj)
        #     self.central_widget.tools_tab = tools_GUI.ToolsTab(self.path_prj, self.name_prj)
        #     #if self.stat_tabs:
        #     self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
        #     self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)
        #     self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)


        # pass the info to the bio info tab
        # to be modified if a new language is added !
        if nb_lang == 0:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'English'
        elif nb_lang == 1:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'French'
        # elif nb_lang == 2:  # to be added if the xml preference files are also in spanish
        #     self.central_widget.bioinfo_tab.lang = 'Spanish'
        else:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'English'

        # write the new language in the figure option to be able to get the title, axis in the right language
        project_manag_mod.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        # set the central widget
        for i in range(self.central_widget.tab_widget.count(), -1, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.name_prj_c = self.name_prj
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.add_all_tab()
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj

        # create the new menu
        self.my_menu_bar()
        # create the new toolbar
        self.my_toolbar()
        # reconnect signal for the welcome tab
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
        # if hasattr(self.central_widget, 'chronicle_tab') == True:
        #     self.central_widget.update_merge_for_chronicle()

        self.central_widget.l1.setText(self.tr('Habby says:'))

        # update user option to remember the language
        if self.lang == 0:
            language = "english"
        if self.lang == 1:
            language = "french"
        if self.lang == 2:
            language = "spanish"
        if self.user_preferences.data["language"] != language:
            self.user_preferences.data["language"] = language
            self.user_preferences.save_user_preferences_json()

        #  right click
        self.create_menu_right_clic()
        self.central_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.central_widget.customContextMenuRequested.connect(self.show_menu_right_clic)

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

        if right_menu:  # right clic
            self.menu_right = QMenu()
            self.menu_right.clear()
        else:
            self.menubar = self.menuBar()
            self.menubar.clear()

        # Menu to open and close file
        exitAction = QAction(self.tr('Exit'), self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip(self.tr('Exit application'))
        exitAction.triggered.connect(self.closeEvent)
        openprj = QAction(self.tr('Open'), self)
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
        newprj = QAction(self.tr('New'), self)
        newprj.setShortcut('Ctrl+N')
        newprj.setStatusTip(self.tr('Create a new project'))
        newprj.triggered.connect(self.new_project)
        closeprj = QAction(self.tr('Close'), self)
        closeprj.setShortcut('Ctrl+W')
        closeprj.setStatusTip(self.tr('Close the current project without opening a new one'))
        closeprj.triggered.connect(self.close_project)

        # Menu to open menu research
        logc = QAction(self.tr("Clear log"), self)
        logc.setStatusTip(
            self.tr('Empty the log windows at the bottom of the main window. Do not erase the .log file.'))
        logc.setShortcut('Ctrl+L')
        logc.triggered.connect(self.clear_log)
        logn = QAction(self.tr("Do not save log"), self)
        logn.setStatusTip(self.tr('The .log file will not be updated further.'))
        logn.triggered.connect(lambda: self.do_log(0))
        logy = QAction(self.tr("Save log"), self)
        logy.setStatusTip(self.tr('Events will be written to the .log file.'))
        logy.triggered.connect(lambda: self.do_log(1))
        savi = QAction(self.tr("Delete all figure files"), self)
        savi.setStatusTip(self.tr('Figures files of current project will be deleted'))
        savi.triggered.connect(self.remove_all_figure_files)
        closeim = QAction(self.tr("Close all figure windows"), self)
        closeim.setStatusTip(self.tr('Close all open figure windows'))
        closeim.triggered.connect(self.central_widget.closefig)
        closeim.setShortcut('Ctrl+B')

        # Menu to choose the language
        self.english_action = QAction(self.tr('&English'), self, checkable=True)
        self.english_action.setStatusTip(self.tr('click here for English'))
        self.english_action.triggered.connect(lambda: self.setlangue(0))  # lambda because of the argument
        self.french_action = QAction(self.tr('&French'), self, checkable=True)
        self.french_action.setStatusTip(self.tr('click here for French'))
        self.french_action.triggered.connect(lambda: self.setlangue(1))
        self.spanish_action = QAction(self.tr('&Spanish'), self, checkable=True)
        self.spanish_action.setStatusTip(self.tr('click here for Spanish'))
        self.spanish_action.triggered.connect(lambda: self.setlangue(2))

        # Menu to obtain help and program version
        helpm = QAction(self.tr('Developper Help'), self)
        helpm.setStatusTip(self.tr('Get help to use the programme'))
        helpm.triggered.connect(self.open_help)

        # Menu to obtain help and program version
        aboutm = QAction(self.tr('About'), self)
        aboutm.setStatusTip(self.tr('Get information software'))
        aboutm.triggered.connect(self.get_information_soft)

        # preferences
        preferences_action = QAction(self.tr('Preferences'), self)
        preferences_action.triggered.connect(self.open_preferences)

        # physical
        self.physicalmodelaction = QAction(self.tr('Physical tabs'), self, checkable=True)
        self.physicalmodelaction.triggered.connect(self.open_close_physic)

        # statistic
        self.statisticmodelaction = QAction(self.tr('Statistical tabs'), self, checkable=True)
        self.statisticmodelaction.triggered.connect(self.open_close_stat)

        # reasearch
        self.researchmodelaction = QAction(self.tr("Research tabs"), self, checkable=True)
        self.researchmodelaction.triggered.connect(self.open_close_rech)

        # classic them
        self.classicthemeaction = QAction(self.tr('classic'), self, checkable=True)
        self.classicthemeaction.triggered.connect(self.setthemeclassic)

        # dark them
        self.darkthemeaction = QAction(self.tr('dark'), self, checkable=True)
        self.darkthemeaction.triggered.connect(self.setthemedark)

        # language
        if self.lang == 0:
            self.english_action.setChecked(True)
            self.french_action.setChecked(False)
            self.spanish_action.setChecked(False)
        if self.lang == 1:
            self.english_action.setChecked(False)
            self.french_action.setChecked(True)
            self.spanish_action.setChecked(False)
        if self.lang == 2:
            self.english_action.setChecked(False)
            self.french_action.setChecked(False)
            self.spanish_action.setChecked(True)

        # theme
        if self.actual_theme == "classic":
            self.classicthemeaction.setChecked(True)
            self.darkthemeaction.setChecked(False)
        if self.actual_theme == "dark":
            self.classicthemeaction.setChecked(False)
            self.darkthemeaction.setChecked(True)

        # tabs
        self.physicalmodelaction.setChecked(self.physic_tabs)
        self.statisticmodelaction.setChecked(self.stat_tabs)
        self.researchmodelaction.setChecked(self.research_tabs)

        # add all first level menu
        if right_menu:
            self.menu_right = QMenu()
            fileMenu_project = self.menu_right.addMenu(self.tr('Project'))
            fileMenu_settings = self.menu_right.addMenu(self.tr('Settings'))
            fileMenu_language = self.menu_right.addMenu(self.tr('Language'))
            fileMenu_view = self.menu_right.addMenu(self.tr('View'))
            self.fileMenu_tabs = self.menu_right.addMenu(self.tr('Tabs'))
            fileMenu_help = self.menu_right.addMenu(self.tr('Help'))
        else:
            self.menubar = self.menuBar()
            fileMenu_project = self.menubar.addMenu(self.tr('Project'))
            fileMenu_settings = self.menubar.addMenu(self.tr('Settings'))
            fileMenu_language = self.menubar.addMenu(self.tr('Language'))
            fileMenu_view = self.menubar.addMenu(self.tr('View'))
            self.fileMenu_tabs = self.menubar.addMenu(self.tr('Tabs'))
            fileMenu_help = self.menubar.addMenu(self.tr('Help'))

        # add all the rest
        fileMenu_project.addAction(newprj)
        fileMenu_project.addAction(openprj)
        recentpMenu = fileMenu_project.addMenu(self.tr('Open recent'))
        for j in range(0, len(recent_proj_menu)):
            recentpMenu.addAction(recent_proj_menu[j])
        fileMenu_project.addAction(closeprj)
        fileMenu_project.addAction(exitAction)
        log_all = fileMenu_settings.addMenu(self.tr('Log'))
        log_all.addAction(logc)
        log_all.addAction(logn)
        log_all.addAction(logy)
        im_all = fileMenu_settings.addMenu(self.tr('Figure options'))
        im_all.addAction(savi)
        im_all.addAction(closeim)
        theme_all = fileMenu_view.addMenu(self.tr("Themes"))
        theme_all.addAction(self.classicthemeaction)
        theme_all.addAction(self.darkthemeaction)
        self.fileMenu_tabs.addAction(self.physicalmodelaction)
        self.fileMenu_tabs.addAction(self.statisticmodelaction)
        self.fileMenu_tabs.addAction(self.researchmodelaction)
        fileMenu_settings.addAction(preferences_action)
        fileMenu_language.addAction(self.english_action)
        fileMenu_language.addAction(self.french_action)
        fileMenu_language.addAction(self.spanish_action)
        fileMenu_help.addAction(helpm)
        fileMenu_help.addAction(aboutm)

        if not right_menu:
            # add the status and progress bar
            self.statusBar()
            self.progress_bar = QProgressBar()
            self.progress_bar.setValue(0)
            self.statusBar().addPermanentWidget(self.progress_bar)
            self.progress_bar.setVisible(False)

            # add the title of the windows
            # let it here as it should be changes if language changes
            if self.name_prj:
                self.setWindowTitle(self.tr('HABBY ') + str(self.version) + ' - ' + self.name_prj)
            else:
                self.setWindowTitle(self.tr('HABBY ') + str(self.version))

            # in case we need a tool bar
            # self.toolbar = self.addToolBar('')

    def setthemeclassic(self):
        self.app.setStyleSheet("")
        #self.app.setStyle("Fusion")
        self.actual_theme = "classic"
        self.my_menu_bar()
        self.my_menu_bar(True)
        if self.user_preferences.data["theme"] != self.actual_theme:
            self.user_preferences.data["theme"] = self.actual_theme
            self.user_preferences.save_user_preferences_json()

    def setthemedark(self):
        #self.app.setStyleSheet(qdarkgraystyle.load_stylesheet())
        self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        #self.app.setStyle("fusion")
        self.actual_theme = "dark"
        # other
        self.central_widget.welcome_tab.pic.setPixmap(
            QPixmap(os.path.join(os.getcwd(), self.central_widget.welcome_tab.imname)).scaled(800, 500))  # 800 500
        self.my_menu_bar()
        self.my_menu_bar(True)
        if self.user_preferences.data["theme"] != self.actual_theme:
            self.user_preferences.data["theme"] = self.actual_theme
            self.user_preferences.save_user_preferences_json()
        #self.setStyleSheet('QGroupBox::title {subcontrol-position: top left}')
        #self.setStyleSheet('QGroupBox::title {subcontrol-position: top left; subcontrol-origin: margin; left: 7px; padding: 0px 0px 0px 0px;}')

    def create_menu_right_clic(self):
        """
        This function create the menu for right click
        """

        self.my_menu_bar(True)

    def show_menu_right_clic(self, point):
        """
        This function is used to show the menu on right click. If we are on the Habitat Tab and that the focus is on
        the QListWidget, it shows the information concerning the fish

        :param point: Not understood, link with the position of the menu.
        """
        # if self.central_widget.bioinfo_tab.selected_aquatic_animal_qtablewidget.underMouse():
        #     self.central_widget.bioinfo_tab.show_info_fish(True)
        if self.central_widget.bioinfo_tab.list_f.underMouse():
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
        name1 = os.path.join(os.getcwd(), "translation", "icon", "openproject.png")
        icon_open.addPixmap(QPixmap(name1), QIcon.Normal)

        icon_see = QIcon()
        name1 = os.path.join(os.getcwd(), "translation", "icon", "see_project.png")
        icon_see.addPixmap(QPixmap(name1), QIcon.Normal)

        icon_new = QIcon()
        name1 = os.path.join(os.getcwd(), "translation", "icon", "newfile.png")
        icon_new.addPixmap(QPixmap(name1), QIcon.Normal)

        icon_kill = QIcon()
        name1 = os.path.join(os.getcwd(), "translation", "icon", "stop.png")
        icon_kill.addPixmap(QPixmap(name1), QIcon.Normal)

        # create the actions of the toolbar
        openAction = QAction(icon_open, self.tr('Open project'), self)
        openAction.setStatusTip(self.tr('Open an existing project'))
        openAction.triggered.connect(self.open_project)

        newAction = QAction(icon_new, self.tr('New project'), self)
        newAction.setStatusTip(self.tr('Create a new project'))
        newAction.triggered.connect(self.new_project)

        self.seeAction = QAction(icon_see, self.tr('See files of the current project'), self)
        self.seeAction.setStatusTip(self.tr('See the existing file of a project and open them.'))
        self.seeAction.triggered.connect(self.see_file)

        closeAction = QAction(icon_closefig, self.tr('Close figure windows'), self)
        closeAction.setStatusTip(self.tr('Close all open figure windows'))
        closeAction.triggered.connect(self.central_widget.closefig)

        self.kill_process = QAction(icon_kill, self.tr('Stop current process'), self)
        self.kill_process.triggered.connect(partial(self.process_alive, close=True, isalive=False))
        self.kill_process.setVisible(False)
        spacer_toolbar = QWidget()
        spacer_toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # position of the toolbar
        self.toolbar.setOrientation(Qt.Vertical)

        # create the toolbar
        self.toolbar.addAction(newAction)
        self.toolbar.addAction(openAction)
        self.toolbar.addAction(self.seeAction)
        self.toolbar.addAction(closeAction)
        self.toolbar.addWidget(spacer_toolbar)
        self.toolbar.addAction(self.kill_process)

    def open_preferences(self):
        # show the pref
        self.preferences_dialog.open_preferences()
        # # witdh_for_checkbox_alignement
        witdh_for_checkbox_alignement = self.preferences_dialog.cut_2d_grid_label.size().width()
        self.preferences_dialog.erase_data_label.setMinimumWidth(witdh_for_checkbox_alignement)

    def recreate_tabs_attributes(self):
        # create new tab (there were some segmentation fault here as it re-write existing QWidget, be careful)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            if hasattr(self.central_widget, "welcome_tab"):
                if not self.central_widget.welcome_tab:
                    self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.welcome_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "hydro_tab"):
                if not self.central_widget.hydro_tab:
                    self.central_widget.hydro_tab = hydro_sub_GUI.Hydro2W(self.path_prj, self.name_prj)
                else:
                    self.central_widget.hydro_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.hydro_tab = hydro_sub_GUI.Hydro2W(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "substrate_tab"):
                if not self.central_widget.substrate_tab:
                    self.central_widget.substrate_tab = hydro_sub_GUI.SubstrateW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.substrate_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.substrate_tab = hydro_sub_GUI.SubstrateW(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "bioinfo_tab"):
                if not self.central_widget.bioinfo_tab:
                    self.central_widget.bioinfo_tab = calc_hab_GUI.BioInfo(self.path_prj, self.name_prj)
                else:
                    self.central_widget.bioinfo_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.bioinfo_tab = calc_hab_GUI.BioInfo(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "data_explorer_tab"):
                if not self.central_widget.data_explorer_tab:
                    self.central_widget.data_explorer_tab = data_explorer_GUI.DataExplorerTab(self.path_prj, self.name_prj)
                else:
                    self.central_widget.data_explorer_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.data_explorer_tab = data_explorer_GUI.DataExplorerTab(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "tools_tab"):
                if not self.central_widget.tools_tab:
                    self.central_widget.tools_tab = tools_GUI.ToolsTab(self.path_prj, self.name_prj)
                else:
                    self.central_widget.tools_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.tools_tab = tools_GUI.ToolsTab(self.path_prj, self.name_prj)

            if hasattr(self, "bio_model_explorer_dialog"):
                if not self.bio_model_explorer_dialog:
                    self.bio_model_explorer_dialog = BioModelExplorerWindow(self, self.path_prj, self.name_prj, self.name_icon,
                                                                    self.central_widget.data_explorer_tab.data_explorer_frame.plot_group.plot_process_list)
                    self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(
                        self.central_widget.write_log)
                    self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)
                else:
                    self.bio_model_explorer_dialog.__init__(self, self.path_prj, self.name_prj, self.name_icon,
                                                            self.central_widget.data_explorer_tab.data_explorer_frame.plot_group.plot_process_list)
                    self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)
            else:
                self.bio_model_explorer_dialog = BioModelExplorerWindow(self, self.path_prj, self.name_prj, self.name_icon,
                                                                    self.central_widget.data_explorer_tab.data_explorer_frame.plot_group.plot_process_list)
                self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(
                    self.central_widget.write_log)
                self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)

            if hasattr(self.central_widget, "statmod_tab"):
                if not self.central_widget.statmod_tab:
                    self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.statmod_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "stathab_tab"):
                if not self.central_widget.stathab_tab:
                    self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.stathab_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "fstress_tab"):
                if not self.central_widget.fstress_tab:
                    self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.fstress_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)

    def save_project(self):
        """
        A function to save the xml file with the information on the project

        **Technical comments**

        This function saves or creates the xml file related to the project. In this xml file, there are the path and
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
        user creates a new project. The user can however change this path if he wants. It also creates other similar
        folders to store different type of outputs. The next step is to communicate
        to all the children widget than the name and path of the project have changed.

        This function also changes the title of the Windows to reflect the project name and it adds the saved
        project to the list of recent project if it is not part of the list already. Because of this the menu must
        updated.

        Finally the log is written (see “log and HABBY in the command line).
        """
        # saved path
        path_prj = os.path.normpath(self.central_widget.welcome_tab.e2.text())
        if not os.path.isdir(path_prj):  # if the directoy do not exist
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
            self.path_prj = path_prj
        # name
        e1here = self.central_widget.welcome_tab.e1
        self.name_prj = e1here.text()

        # username and description
        e4here = self.central_widget.welcome_tab.e4
        self.username_prj = e4here.text()
        e3here = self.central_widget.welcome_tab.e3
        self.descri_prj = e3here.toPlainText()

        fname = os.path.join(self.path_prj, self.name_prj + '.xml')

        # update user option and re-do (the whole) menu
        self.user_preferences.data["name_prj"] = self.name_prj
        self.user_preferences.data["path_prj"] = self.path_prj

        # save name and path of project in the list of recent project
        if self.name_prj not in self.recent_project:
            self.recent_project.append(self.name_prj)
            self.recent_project_path.append(self.path_prj)
        else:
            ind = np.where(self.recent_project == self.name_prj)[0]
            if ind:
                if os.path.normpath(self.path_prj) != os.path.normpath(
                        self.recent_project_path[ind[0]]):  # linux windows path
                    self.recent_project.append(self.name_prj)
                    self.recent_project_path.append(self.path_prj)
        self.user_preferences.data["recent_project_name"] = self.recent_project
        self.user_preferences.data["recent_project_path"] = self.recent_project_path
        self.user_preferences.save_user_preferences_json()

        self.my_menu_bar()

        # if new projet or project move
        if not os.path.isfile(fname):
            path_last_file_loaded_child = project_manag_mod.create_project_structure(self.path_prj,
                                                       self.central_widget.logon,
                                                       self.version,
                                                       self.username_prj,
                                                       self.descri_prj,
                                                       self.path_bio_default)

        # project exist
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            child = root.find(".//Project_Name")
            path_child = root.find(".//Path_Project")
            path_last_file_loaded_child = root.find(".//Path_last_file_loaded")
            user_child = root.find(".//User_Name")
            des_child = root.find(".//Description")
            pathbio_child = root.find(".//Path_Bio")
            pathin_child = root.find(".//Path_Input")
            pathdf5_child = root.find(".//Path_Hdf5")
            pathim_child = root.find(".//Path_Figure")
            pathtxt_child = root.find(".//Path_Text")
            pathshapefile_child = root.find(".//Path_Shape")
            pathpara_child = root.find(".//Path_Visualisation")

            # path input
            if pathin_child is None:
                pathin_text = 'input'
            else:
                pathin_text = pathin_child.text

            # path hdf5
            if pathdf5_child is None:
                pathhdf5_text = 'hdf5'
            else:
                pathhdf5_text = pathdf5_child.text

            # path figures
            if pathim_child is None:
                pathim_text = os.path.join("output", "figures")
            else:
                pathim_text = pathim_child.text

            # path text output
            if pathtxt_child is None:
                pathtxt_text = os.path.join("output", "text")
            else:
                pathtxt_text = pathtxt_child.text

            # path shapefile
            if pathshapefile_child is None:
                pathshapefile_text = os.path.join("output", "GIS")
            else:
                pathshapefile_text = pathin_child.text

            # path visualisation
            if pathpara_child is None:
                pathpara_text = os.path.join("output", "3D")
            else:
                pathpara_text = pathin_child.text

            child.text = self.name_prj
            path_child.text = self.path_prj
            pathbio_child.text = self.path_bio_default
            user_child.text = self.username_prj
            des_child.text = self.descri_prj
            fname = os.path.join(self.path_prj, self.name_prj + '.xml')
            doc.write(fname)

            # create needed folder if not there yet
            pathin_text = os.path.join(self.path_prj, pathin_text)
            path_h5 = os.path.join(self.path_prj, pathhdf5_text)
            path_im = os.path.join(self.path_prj, pathim_text)
            path_text = os.path.join(self.path_prj, pathtxt_text)
            path_shapefile_text = os.path.join(self.path_prj, pathshapefile_text)
            path_para_text = os.path.join(self.path_prj, pathpara_text)
            try:
                if not os.path.exists(pathin_text):
                    os.makedirs(pathin_text)
                if not os.path.exists(path_h5):
                    os.makedirs(path_h5)
                if not os.path.exists(os.path.join(self.path_prj, 'output')):
                    os.makedirs(os.path.join(self.path_prj, 'output'))
                if not os.path.exists(path_im):
                    os.makedirs(path_im)
                if not os.path.exists(path_text):
                    os.makedirs(path_text)
                if not os.path.exists(path_shapefile_text):
                    os.makedirs(path_shapefile_text)
                if not os.path.exists(path_para_text):
                    os.makedirs(path_para_text)
            except PermissionError:
                self.central_widget.write_log('Error: Could not create directory, Permission Error \n')
                return

        # update central widget
        self.central_widget.name_prj_c = self.name_prj
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.path_last_file_loaded_c = path_last_file_loaded_child.text
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj

        # send the new name to all widget and re-connect signal
        t = self.central_widget.tracking_journal_QTextEdit.toPlainText()
        m = self.central_widget.tab_widget.count()

        for i in range(m, 0, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.tab_widget.removeTab(0)

        # recreate new widget
        self.recreate_tabs_attributes()

        self.central_widget.add_all_tab()

        # re-connect signals for the tab
        self.central_widget.connect_signal_fig_and_drop()
        self.central_widget.connect_signal_log()

        # update name
        self.central_widget.update_hydro_hdf5_name()

        # save_preferences
        project_manag_mod.set_lang_fig(self.lang, self.path_prj, self.name_prj)
        self.preferences_dialog.save_preferences()
        self.preferences_dialog = preferences_GUI.PreferenceWindow(self.path_prj, self.name_prj, self.name_icon)
        self.preferences_dialog.send_log.connect(self.central_widget.write_log)
        self.soft_information_dialog = SoftInformationDialog(self.path_prj, self.name_prj, self.name_icon, self.version)

        # write log
        self.central_widget.tracking_journal_QTextEdit.clear()
        self.central_widget.write_log('# Log of HABBY started.')
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

    def open_project(self):
        """
        This function is used to open an existing habby project by selecting an xml project file. Called by
        my_menu_bar()
        """
        #  indicate to HABBY that this project will close
        self.end_concurrency()

        # open an xml file
        path_here = os.path.dirname(self.path_prj)
        if not path_here:
            path_here = os.path.join(os.path.expanduser("~"), "HABBY_projects")
        filename_path = QFileDialog.getOpenFileName(self, self.tr('Open File'), path_here, "XML (*.xml)")[0]
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
        self.path_prj = root2.find(".//Path_Project").text
        self.central_widget.path_last_file_loaded_c = root2.find(".//Path_last_file_loaded").text

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
            root2.find(".//Path_Project").text = self.path_prj
            # if we have change the project path, it is probable that the project folder was copied from somewhere else
            # so the check concurrency file was probably copied and look like open even if the project is closed.
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
        if stathab_info is not None:  # if there is data for STATHAB
            self.central_widget.stathab_tab.load_from_hdf5_gui()
        self.central_widget.statmod_tab.open_estimhab_hdf5()

        # update hydro
        self.central_widget.update_hydro_hdf5_name()
        self.central_widget.substrate_tab.update_sub_hdf5_name()

        # recreate new widget
        self.recreate_tabs_attributes()
        # self.central_widget.hydro_tab = hydro_sub_GUI.Hydro2W(self.path_prj, self.name_prj)
        # self.central_widget.substrate_tab = hydro_sub_GUI.SubstrateW(self.path_prj, self.name_prj)
        # self.central_widget.bioinfo_tab = calc_hab_GUI.BioInfo(self.path_prj, self.name_prj)
        # self.central_widget.statmod_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
        # self.central_widget.stathab_tab = stathab_GUI.StathabW(self.path_prj, self.name_prj)
        # self.central_widget.fstress_tab = fstress_GUI.FstressW(self.path_prj, self.name_prj)
        # self.central_widget.output_tab = preferences_GUI.PreferenceWindow(self.path_prj, self.name_prj)
        # self.central_widget.data_explorer_tab = data_explorer_GUI.DataExplorerTab(self.path_prj, self.name_prj)
        # self.central_widget.tools_tab = tools_GUI.ToolsTab(self.path_prj, self.name_prj)

        # set the central widget
        for i in range(self.central_widget.tab_widget.count(), -1, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.name_prj_c = self.name_prj
        self.central_widget.path_prj_c = self.path_prj
        self.central_widget.add_all_tab()
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj
        # re-connect signals for the tab
        self.central_widget.connect_signal_fig_and_drop()
        self.central_widget.connect_signal_log()

        # update name project
        if self.name_prj != '':
            self.setWindowTitle(self.tr('HABBY ') + str(self.version) + ' - ' + self.name_prj)
        else:
            self.setWindowTitle(self.tr('HABBY ') + str(self.version))

        # reconnect method to button
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.welcome_tab.change_name.connect(self.change_name_project)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        # write the new language in the figure option to be able to get the title, axis in the right language
        project_manag_mod.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        # check if project open somewhere else
        self.check_concurrency()

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
        filename_path = os.path.join(self.recent_project_path[j], self.recent_project[j] + '.xml')

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
        self.path_prj = root.find(".//Path_Project").text
        self.username_prj = root.find(".//User_Name").text
        self.descri_prj = root.find(".//Description").text
        stathab_info = root.find(".//hdf5Stathab")
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText(self.username_prj)
        self.central_widget.welcome_tab.e3.setText(self.descri_prj)
        # self.central_widget.write_log('# Project opened successfully. \n')

        # save the project
        self.save_project()

        # update hydro
        self.central_widget.update_hydro_hdf5_name()
        self.central_widget.substrate_tab.update_sub_hdf5_name()

        # update stathab and estimhab
        if stathab_info is not None:
            self.central_widget.stathab_tab.load_from_hdf5_gui()
        self.central_widget.statmod_tab.open_estimhab_hdf5()

        # write the new langugage in the figure option to be able to get the title, axis in the right language
        project_manag_mod.set_lang_fig(self.lang, self.path_prj, self.name_prj)

        # check if project open somewhere else
        self.check_concurrency()

    def new_project(self):
        """
        This function open an empty project and guide the user to create a new project, using a new Windows
        of the class CreateNewProjectDialog
        """
        pathprj_old = self.path_prj

        self.end_concurrency()

        # open a new Windows to ask for the info for the project
        self.createnew = CreateNewProjectDialog(self.lang, self.physic_tabs, self.stat_tabs, pathprj_old)
        self.createnew.save_project.connect(self.save_project_if_new_project)
        self.createnew.send_log.connect(self.central_widget.write_log)
        self.createnew.show()

    def close_project(self):
        """
        This function close the current project without opening a new project
        """
        # open an empty project (so it close the old one)
        self.empty_project()

        # remove tab 9as we have no project anymore)
        for i in range(self.central_widget.tab_widget.count(), 0, -1):
            self.central_widget.tab_widget.removeTab(i)

        # add the welcome Widget
        self.central_widget.tab_widget.addTab(self.central_widget.welcome_tab, self.tr("Project"))
        self.central_widget.welcome_tab.lowpart.setEnabled(False)

        self.end_concurrency()
        # self.my_menu_bar()

    def save_project_if_new_project(self):
        """
        This function is used to save a project when the project is created from the other Windows CreateNewProjectDialog. It
        can not be in the new_project function as the new_project function call CreateNewProjectDialog().
        """
        name_prj_here = self.createnew.e1.text()
        project_type = self.createnew.project_type_combobox.currentText()
        if project_type == "Physical":
            self.physic_tabs = True
            self.stat_tabs = False
        if project_type == "Statistical":
            self.physic_tabs = False
            self.stat_tabs = True

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

        # check if there is not another project with the same path_name
        fname = os.path.join(self.createnew.e2.text(), name_prj_here, name_prj_here + '.xml')
        if os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("An HABBY project already exists."))
            self.msg2.setText(self.tr("A project with an identical name exists.\n"
                                      "Do you want to overwrite it and all its files ?"))
            self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            res = self.msg2.exec_()

            # delete
            if res == QMessageBox.No:
                self.central_widget.write_log('Warning: Project not created. Choose another project name.')
                self.createnew.close()
            if res == QMessageBox.Yes:
                self.delete_project(path_new_fold)
                try:
                    os.makedirs(path_new_fold)
                except PermissionError:
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Permission Error"))
                    self.msg2.setText(
                        self.tr(
                            "You do not have the permission to write in this folder. Choose another folder. \n"))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
                    return
                # pass the info from the extra Windows to the HABBY MainWindows (check on user input done by save_project)
                self.central_widget.welcome_tab.e1.setText(name_prj_here)
                self.central_widget.welcome_tab.e2.setText(path_new_fold)
                self.central_widget.welcome_tab.e3.setText('')
                self.central_widget.welcome_tab.e4.setText('')
                self.createnew.close()
                self.save_project()
                self.central_widget.write_log('Warning: Old project and its files are deleted. New empty project created.')

        # save project if unique name in the selected folder
        else:
            # pass the info from the extra Windows to the HABBY MainWindows (check on user input done by save_project)
            self.central_widget.welcome_tab.e1.setText(name_prj_here)
            self.central_widget.welcome_tab.e2.setText(path_new_fold)
            self.central_widget.welcome_tab.e3.setText('')
            self.central_widget.welcome_tab.e4.setText('')
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
            child1.text = os.path.join("output", "figures")
        else:
            child1.text = os.path.join("output", "figures")
        doc.write(fname)

        # reconnect method to button
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.welcome_tab.change_name.connect(self.change_name_project)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.xml')):
            self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        # write the new language in the figure option to be able to get the title, axis in the right language
        project_manag_mod.set_lang_fig(self.lang, self.path_prj, self.name_prj)

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
            path_child = root.find(".//Path_Project")
            path_prj_old = path_child.text
            path_child.text = os.path.join(os.path.dirname(path_child.text), name_prj_here)
            new_path_prj = os.path.join(os.path.dirname(path_child.text), name_prj_here)
            # update log name in the new xml
            child_logfile1 = root.find(".//File_Log")
            log1_old = child_logfile1.text
            child_logfile1.text = os.path.join(new_path_prj, name_prj_here + '.log')
            child_logfile2 = root.find(".//File_Restart")
            log2_old = child_logfile2.text
            child_logfile2.text = os.path.join(new_path_prj, 'restart_' + name_prj_here + '.log')

            # copy the xml
            try:
                os.rename(os.path.join(old_path_prj, log1_old), os.path.join(old_path_prj, name_prj_here + '.log'))
                os.rename(os.path.join(old_path_prj, log2_old), os.path.join(old_path_prj,
                                                                             'restart_' + name_prj_here + '.log'))
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
        This function opens a new empty project
        """

        # load the xml file
        filename_empty = os.path.abspath(os.path.join('files_dep', 'empty_proj.xml'))

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
        self.path_prj = root2.find(".//Path_Project").text
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText('')
        self.central_widget.welcome_tab.e3.setText('')

        self.setWindowTitle(self.tr('HABBY ') + str(self.version))
        # save the project
        #self.save_project()

    def see_file(self):
        """
        This function open an explorer with different paths (project folder, habby folder, AppData folder)
        """
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            path_choosen = os.path.normpath(self.user_preferences.user_preferences_habby_path)
        elif modifiers == Qt.ShiftModifier:
            path_choosen = os.path.normpath(os.getcwd())
        else:
            path_choosen = os.path.normpath(self.path_prj)

        if self.operatingsystemactual == 'Windows':
            call(['explorer', path_choosen])
        elif self.operatingsystemactual == 'Linux':
            call(["xdg-open", path_choosen])
        elif self.operatingsystemactual == 'Darwin':
            call(['open', path_choosen])

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

        # a boolean to check to progress of the saving
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
        for i in range(0, self.central_widget.statmod_tab.selected_aquatic_animal_qtablewidget.count()):
            fish_item = self.central_widget.statmod_tab.selected_aquatic_animal_qtablewidget.item(i)
            fish_item_str = fish_item.text()
            fish_list.append(fish_item_str)

        # create an empty hdf5 file using all default prop.
        fname_no_path = self.name_prj + '_ESTIMHAB' + '.hab'
        fnamep = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(fnamep):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save project"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the\
                 start tab before saving ESTIMHAB data"))
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
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the start tab before saving ESTIMHAB data"))
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
                    self.msg2.setText(
                        self.tr("Data is empty or partially empty. Data is saved, but cannot be executed"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()

        return var

    def open_close_physic(self):
        phisical_tabs_list = ["hydraulic", "substrate", "calc hab", "data explorer", "tools"]
        if self.physic_tabs:
            if self.name_prj:
                for i in range(self.central_widget.tab_widget.count() - 1, 0, -1):
                    if self.central_widget.tab_widget.widget(i).tab_name in phisical_tabs_list:
                        self.central_widget.tab_widget.removeTab(i)
            self.physic_tabs = False
        elif not self.physic_tabs:
            if self.name_prj:
                self.central_widget.tab_widget.insertTab(1, self.central_widget.hydro_tab, self.tr("Hydraulic"))  # 1
                self.central_widget.tab_widget.insertTab(2, self.central_widget.substrate_tab, self.tr("Substrate"))  # 2
                self.central_widget.tab_widget.insertTab(3, self.central_widget.bioinfo_tab, self.tr("Habitat Calc."))  # 3
                self.central_widget.tab_widget.insertTab(4, self.central_widget.data_explorer_tab, self.tr("Data explorer"))  # 4
                self.central_widget.tab_widget.insertTab(5, self.central_widget.tools_tab, self.tr("Tools"))  # 5
            self.physic_tabs = True

    def open_close_stat(self):
        stat_tabs_list = ["estimhab", "stathab", "fstress"]
        if self.stat_tabs:
            if self.name_prj:
                for i in range(self.central_widget.tab_widget.count() - 1, 0, -1):
                    if self.central_widget.tab_widget.widget(i).tab_name in stat_tabs_list:
                        self.central_widget.tab_widget.removeTab(i)
            self.stat_tabs = False
        elif not self.stat_tabs:
            if self.physic_tabs:
                start_index = 6
            else:
                start_index = 1
            if self.name_prj:
                self.central_widget.tab_widget.insertTab(start_index, self.central_widget.statmod_tab, self.tr("ESTIMHAB"))  # 6
                self.central_widget.tab_widget.insertTab(start_index + 1, self.central_widget.stathab_tab, self.tr("STATHAB"))  # 7
                self.central_widget.tab_widget.insertTab(start_index + 2, self.central_widget.fstress_tab, self.tr("FStress"))  # 8
            self.stat_tabs = True

    def open_close_rech(self):
        """
        Open the additional research tab, which can be used to create Tab with more experimental contents.

        Indeed, it is possible to show extra tab in HABBY. These supplementary tab correspond to open for researcher.
        The plan is that these options are less tested than other mainstream options. It is not clear yet what
        will be added to these options, but the tabs are already there when it will be needed.
        """
        research_tabs_list = ["research"]
        if self.research_tabs:
            if self.name_prj:
                for i in range(self.central_widget.tab_widget.count() - 1, 0, -1):
                    if self.central_widget.tab_widget.widget(i).tab_name in research_tabs_list:
                        self.central_widget.tab_widget.removeTab(i)
            self.research_tabs = False
        elif not self.research_tabs:
            if self.name_prj:
                self.central_widget.tab_widget.addTab(self.central_widget.other_tab, self.tr("Research 1"))
                self.central_widget.tab_widget.addTab(self.central_widget.other_tab2, self.tr("Research 2"))
            self.research_tabs = True

    def clear_log(self):
        """
        Clear the log in the GUI.
        """
        self.central_widget.tracking_journal_QTextEdit.clear()
        self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
            self.tr('Log erased in this window.<br>'))

    def do_log(self, save_log):
        """
        Save or not save the log

        :param save_log: an int which indicates if the log should be saved or not

        *   0: do not save log
        *   1: save the log in the .log file and restart file
        """
        if save_log == 0:
            t = self.central_widget.tracking_journal_QTextEdit.text()
            self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
                self.tr('This log will not be saved anymore in the .log file. <br>')
                + self.tr('This log will not be saved anymore in the restart file. <br>'))
            self.central_widget.logon = False
        if save_log == 1:
            t = self.central_widget.tracking_journal_QTextEdit.text()
            self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
                self.tr('This log will be saved in the .log file.<br> '
                        'This log will be saved in the restart file. <br>'))
            self.central_widget.logon = True

        # save the option in the xml file
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
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

    def remove_all_figure_files(self):
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
                path_im = os.path.join(self.path_prj, 'output', 'figures')
            else:
                path_im = os.path.join(self.path_prj, *child.text.split("/"))
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()

        # ask for confirmation
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
        t = self.central_widget.tracking_journal_QTextEdit.toPlainText()
        self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('Images deleted. <br>'))

    def delete_project(self, new_project_path):
        try:
            shutil.rmtree(new_project_path)
        except:
            self.central_widget.write_log('Error: Old project and its files are opened by another programme.\n'
                               'Close them and try again.')

    def open_help(self):
        """
        This function open the html which form the help from HABBY. For the moment, it is the full documentation
        with all the coding detail, but we should create a new html or a new pdf file which would be more practical
        for the user.
        """
        filename_help = os.path.join(os.getcwd(), "doc", "_build", "html", "index.html")
        wbopen(filename_help)

    def get_information_soft(self):
        # show the pref
        self.soft_information_dialog.show()

    def process_alive(self, close=True, isalive=False):
        """
        method to close all multiprocess of data (hydro, substrate, merge and calc hab) if they are alive.
        """
        tab_list = [("hydro_tab", "hecras1D"),
                    ("hydro_tab", "hecras2D"),
                    ("hydro_tab", "rubar2d"),
                    ("hydro_tab", "rubar1d"),
                    ("hydro_tab", "sw2d"),
                    ("hydro_tab", "iber2d"),
                    ("hydro_tab", "telemac"),
                    ("hydro_tab", "ascii"),
                    ("hydro_tab", "riverhere2d"),
                    ("hydro_tab", "mascar"),
                    ("hydro_tab", "habbyhdf5"),
                    ("hydro_tab", "lammi"),
                    "substrate_tab",
                    "bioinfo_tab"]

        alive = []
        # loop
        if hasattr(self, "central_widget"):
            central_widget_attrib = getattr(self, "central_widget")
            for tabs in tab_list:
                if type(tabs) == tuple:
                    if hasattr(central_widget_attrib, tabs[0]):
                        process_object = getattr(getattr(central_widget_attrib, tabs[0]), tabs[1]).p
                        if process_object.is_alive():
                            alive.append(process_object.name)
                            if close:
                                process_object.terminate()
                                self.central_widget.write_log("Warning: " + process_object.name +
                                                              " process has been stopped by the user." +
                                                              " The files produced by this process can be damaged.")
                                # hide button
                                self.kill_process.setVisible(False)
                else:
                    if hasattr(central_widget_attrib, tabs):
                        process_object = getattr(central_widget_attrib, tabs).p
                        if process_object.is_alive():
                            alive.append(process_object.name)
                            if close:
                                process_object.terminate()
                                self.central_widget.write_log("Warning: " + process_object.name +
                                                              " process has been stopped by the user." +
                                                              " The files produced by this process can be damaged.")
                                # hide button
                                self.kill_process.setVisible(False)
            # hide button
            self.kill_process.setVisible(False)
        if isalive:
            return alive


class CreateNewProjectDialog(QWidget):
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

    def __init__(self, lang, physic_tabs, stat_tabs, oldpath_prj):

        if oldpath_prj and os.path.isdir(oldpath_prj):
            self.default_fold = os.path.dirname(oldpath_prj)
        else:
            self.default_fold = os.path.join(os.path.expanduser("~"), "HABBY_projects")
        if self.default_fold == '':
            self.default_fold = os.path.join(os.path.expanduser("~"), "HABBY_projects")
        self.default_name = 'DefaultProj'
        self.physic_tabs = physic_tabs
        self.stat_tabs = stat_tabs
        super().__init__()

        self.init_iu()

    def init_iu(self):
        lg = QLabel(self.tr(" <b> Create a new project </b>"))
        l1 = QLabel(self.tr('Project name: '))
        self.e1 = QLineEdit(self.default_name)
        l2 = QLabel(self.tr('Projects folder: '))
        self.e2 = QLineEdit(self.default_fold)
        button2 = QPushButton(self.tr('Change folder'), self)
        button2.clicked.connect(self.setfolder)
        self.button3 = QPushButton(self.tr('Create project'))
        self.button3.clicked.connect(self.save_project)  # is a PyQtSignal
        self.e1.returnPressed.connect(self.save_project)
        self.button3.setStyleSheet("background-color: #47B5E6; color: black")
        project_type_title_label = QLabel(self.tr("Project type"))
        self.project_type_combobox = QComboBox()
        self.model_type_list = [self.tr("Physical"), self.tr("Statistical")]
        self.project_type_combobox.addItems(self.model_type_list)
        if self.physic_tabs and not self.stat_tabs:
            self.project_type_combobox.setCurrentIndex(0)
        elif self.stat_tabs and not self.physic_tabs:
            self.project_type_combobox.setCurrentIndex(1)

        layoutl = QGridLayout()
        layoutl.addWidget(lg, 0, 0)
        layoutl.addWidget(l2, 1, 0)
        layoutl.addWidget(self.e2, 1, 1)
        layoutl.addWidget(button2, 1, 2)
        layoutl.addWidget(l1, 2, 0)
        layoutl.addWidget(self.e1, 2, 1)
        layoutl.addWidget(project_type_title_label, 3, 0)
        layoutl.addWidget(self.project_type_combobox, 3, 1)
        layoutl.addWidget(self.button3, 3, 2)

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
                                                    )  # check for invalid null parameter on Linux git
        dir_name = os.path.normpath(dir_name)
        # os.getenv('HOME')
        if dir_name != '.':  # cancel case
            self.e2.setText(dir_name)
            self.send_log.emit('New folder selected for the project.')


class CentralW(QWidget):
    """
    This class create the different tabs of the program, which are then used as the central widget by the class
    MainWindows.

    :param rech: A bollean which is True if the tabs for the "research option" are shown. False otherwise.
    :param path_prj: A string with the path to the project xml file
    :param name_prj: A string with the name of the project
    :param lang_bio: A string with the word 'English', 'French' (or an other language). It is used to find the language
           in which the biological info should be shown. So lang_bio should have the same form than the attribute
           "language" in xml preference file.

    **Technical comments**

    In the attribute list, there are a series of name which finish by “tab” such as stathab_tab or output_tab. Each of
    these names corresponds to one tab and a new name should be added to the attributes to add a new tab.

    Then we call a function which connects all the signals from each class which need to write into the log. It is a good
    policy to create a “send_log” signal for each new important class. As there are a lot of signal to connect, these
    connections are written in the function “connect_signal_log”, where the signal for a new class can be added.

    When this is done, the info for the general tab (created before) is filled. If the user has opened a project in HABBY
    before, the name of the project and the other info related to it will be shown on the general tab. If the general
    tab is modified in the class welcome_GUI.WelcomeW(), this part of the code which fill the general tab will probably needs to
    be modified.

    Finally, each tab is filled. The tabs have been created before, but there were empty. Now we fill each one with the
    adequate widget. This is the link with many of the other classes that we describe below. Indeed, many of the widget
    are based on more complicated classes created for example in hydro_sub_GUI.py.

    Then, we create an area under it for the log. Here HABBY will write various infos for the user. Two things to note
    here: a) we should show the end of the scroll area. b) The size of the area should be controlled and not be
    changing even if a lot of text appears. Hence, the setSizePolicy should be fixed.

    The write_log() and write_log_file() method are explained in the section about the log.
    """

    def __init__(self, physic, stat, rech, path_prj, name_prj, lang_bio):

        super().__init__()
        self.msg2 = QMessageBox()
        self.tab_widget = QTabWidget(self)
        self.name_prj_c = name_prj
        self.path_prj_c = path_prj

        self.welcome_tab = welcome_GUI.WelcomeW(path_prj, name_prj)
        self.data_explorer_tab = data_explorer_GUI.DataExplorerTab(path_prj, name_prj)
        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            self.statmod_tab = estimhab_GUI.EstimhabW(path_prj, name_prj)
            self.hydro_tab = hydro_sub_GUI.Hydro2W(path_prj, name_prj)
            self.substrate_tab = hydro_sub_GUI.SubstrateW(path_prj, name_prj)
            self.stathab_tab = stathab_GUI.StathabW(path_prj, name_prj)
            self.tools_tab = tools_GUI.ToolsTab(path_prj, name_prj)
            self.bioinfo_tab = calc_hab_GUI.BioInfo(path_prj, name_prj, lang_bio)
            self.fstress_tab = fstress_GUI.FstressW(path_prj, name_prj)

        self.physic = physic
        self.stat = stat
        self.rech = rech
        self.logon = True  # do we save the log in .log file or not
        self.tracking_journal_QTextEdit = QTextEdit(self)  # where the log is show
        self.tracking_journal_QTextEdit.setReadOnly(True)
        self.tracking_journal_QTextEdit.textChanged.connect(self.scrolldown_log)
        self.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('Log of HABBY started. <br>'))
        self.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('Create or open a project. <br>'))
        self.max_lengthshow = 180
        pyqtRemoveInputHook()
        self.old_ind_tab = 0
        self.opttab = 8  # the position of the option tab

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
            self.msg2.setWindowTitle(self.tr("First time with HABBY ?"))
            self.msg2.setText(self.tr("Create or open an HABBY project."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.setMinimumWidth(1000)
            name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
            self.msg2.setWindowIcon(QIcon(name_icon))
            self.msg2.show()

        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            logon_child = root.find(".//Save_Log")
            if logon_child == 'False' or logon_child == 'false':
                self.logon = False  # is True by default
            self.path_last_file_loaded_c = root.find(".//Path_last_file_loaded").text

        # add the widgets to the list of tab if a project exists
        self.add_all_tab()

        # Area to show the log
        self.l1 = QLabel(self.tr('HABBY says:'))
        self.tracking_journal_QTextEdit.setFixedHeight(100)

        self.welcome_tab.save_info_signal.connect(self.save_info_projet)
        # save the description and the figure option if tab changed
        self.tab_widget.currentChanged.connect(self.save_on_change_tab)

        # update plot item in plot tab
        self.tab_widget.currentChanged.connect(self.update_specific_tab)

        self.keyboard_change_tab_filter = AltTabPressEater()
        self.tab_widget.installEventFilter(self.keyboard_change_tab_filter)
        self.keyboard_change_tab_filter.next_signal.connect(self.next_tab)
        self.keyboard_change_tab_filter.previous_signal.connect(self.previous_tab)
        self.tab_widget.setFocus()

        # layout
        self.layoutc = QGridLayout()
        self.layoutc.addWidget(self.tab_widget, 1, 0)
        self.layoutc.addWidget(self.l1, 2, 0)
        self.layoutc.addWidget(self.tracking_journal_QTextEdit, 3, 0)
        self.setLayout(self.layoutc)

    def previous_tab(self):
        max_tab = self.tab_widget.count() - 1
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index == 0:
            self.tab_widget.setCurrentIndex(max_tab)
        else:
            self.tab_widget.setCurrentIndex(current_tab_index - 1)

    def next_tab(self):
        max_tab = self.tab_widget.count() - 1
        current_tab_index = self.tab_widget.currentIndex()
        if current_tab_index < max_tab:
            self.tab_widget.setCurrentIndex(current_tab_index + 1)
        else:
            self.tab_widget.setCurrentIndex(0)

    def scrolldown_log(self):
        """
        Move the scroll bar to the bottom if the ScollArea is getting bigger
        """
        # self.vbar.setValue(self.vbar.maximum())
        self.tracking_journal_QTextEdit.moveCursor(QTextCursor.End)

    def add_all_tab(self):
        """
        This function add the different tab to habby (used by init and by save_project). Careful, if you change the
        position of the Option tab, you should also modify the variable self.opttab in init
        """
        fname = os.path.join(self.path_prj_c, self.name_prj_c + '.xml')
        if os.path.isfile(fname) and self.name_prj_c != '':
            # allways uptodate
            if self.parent():
                go_physic = self.parent().physic_tabs
                go_stat = self.parent().stat_tabs
                go_research = self.parent().research_tabs
            # first time from init
            else:
                go_physic = self.physic
                go_stat = self.stat
                go_research = self.rech

            # add all tabs
            self.tab_widget.addTab(self.welcome_tab, self.tr("Start"))  # 0
            if go_physic:
                self.tab_widget.addTab(self.hydro_tab, self.tr("Hydraulic"))  # 1
                self.tab_widget.addTab(self.substrate_tab, self.tr("Substrate"))  # 2
                self.tab_widget.addTab(self.bioinfo_tab, self.tr("Habitat Calc."))  # 3
                self.tab_widget.addTab(self.data_explorer_tab, self.tr("Data explorer"))  # 4
                self.tab_widget.addTab(self.tools_tab, self.tr("Tools"))  # 5
            if go_stat:
                self.tab_widget.addTab(self.statmod_tab, self.tr("ESTIMHAB"))  # 6
                self.tab_widget.addTab(self.stathab_tab, self.tr("STATHAB"))  # 7
                self.tab_widget.addTab(self.fstress_tab, self.tr("FStress"))  # 8
            if go_research:
                self.tab_widget.addTab(self.other_tab, self.tr("Research 1"))  # 9
                self.tab_widget.addTab(self.other_tab2, self.tr("Research 2"))  # 10
            self.welcome_tab.lowpart.setEnabled(True)
        # if the project do not exist, do not add new tab
        else:
            self.tab_widget.addTab(self.welcome_tab, self.tr("Project"))
            self.welcome_tab.lowpart.setEnabled(False)

        #self.tab_widget.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")

    def closefig(self):
        """
        method to close the images opened in HABBY and managed by matplotlib
        """
        if hasattr(self, 'data_explorer_tab'):
            if hasattr(self.data_explorer_tab.data_explorer_frame, 'plot_process_list'):
                self.data_explorer_tab.data_explorer_frame.plot_process_list.close_all_plot_process()
        if hasattr(self, 'bioinfo_tab'):
            if hasattr(self.bioinfo_tab, 'plot_process_list'):
                self.bioinfo_tab.plot_process_list.close_all_plot_process()

    def connect_signal_log(self):
        """
        connect all the signal linked to the log. This is in a function only to improve readability.
        """

        self.welcome_tab.send_log.connect(self.write_log)

        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            self.hydro_tab.send_log.connect(self.write_log)
            self.hydro_tab.hecras1D.send_log.connect(self.write_log)
            self.hydro_tab.hecras2D.send_log.connect(self.write_log)
            self.hydro_tab.rubar2d.send_log.connect(self.write_log)
            self.hydro_tab.rubar1d.send_log.connect(self.write_log)
            self.hydro_tab.sw2d.send_log.connect(self.write_log)
            self.hydro_tab.iber2d.send_log.connect(self.write_log)
            self.hydro_tab.telemac.send_log.connect(self.write_log)
            self.hydro_tab.ascii.send_log.connect(self.write_log)
            self.substrate_tab.send_log.connect(self.write_log)
            self.statmod_tab.send_log.connect(self.write_log)
            self.stathab_tab.send_log.connect(self.write_log)
            self.hydro_tab.riverhere2d.send_log.connect(self.write_log)
            self.hydro_tab.mascar.send_log.connect(self.write_log)
            self.bioinfo_tab.send_log.connect(self.write_log)
            self.hydro_tab.habbyhdf5.send_log.connect(self.write_log)
            self.hydro_tab.lammi.send_log.connect(self.write_log)
            self.fstress_tab.send_log.connect(self.write_log)
            self.data_explorer_tab.send_log.connect(self.write_log)
            self.tools_tab.send_log.connect(self.write_log)

    def connect_signal_fig_and_drop(self):
        """
        This function connect the PyQtsignal to show figure and to connect the log. It is a function to
        improve readability.
        """

        if os.path.isfile(os.path.join(self.path_prj_c, self.name_prj_c + '.xml')):
            # connect signals to update the drop-down menu in the substrate tab when a new hydro hdf5 is created
            self.hydro_tab.hecras1D.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.hecras2D.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.telemac.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.ascii.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.rubar2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.rubar1d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.sw2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.iber2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.riverhere2d.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.mascar.drop_hydro.connect(self.update_hydro_hdf5_name)
            self.hydro_tab.habbyhdf5.drop_hydro.connect(self.update_hydro_hdf5_name)

            # connect signal to update the merge file
            # refresh interpolation tools

            self.bioinfo_tab.get_list_merge.connect(self.tools_tab.refresh_hab_filenames)
#            self.chronicle_tab.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.substrate_tab.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.hydro_tab.lammi.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.hydro_tab.ascii.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.hydro_tab.habbyhdf5.drop_merge.connect(self.bioinfo_tab.update_merge_list)

    def write_log(self, text_log):
        """
        A function to write the different log. Please read the section of the doc on the log.

        :param text_log: the text which should be added to the log (a string)

        *   if text_log start with # -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file (comments)
        *   if text_log start with restart -> added it restart_nameproject.txt
        *   if text_log start with WARNING -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file
        *   if text_log start with ERROR -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file
        *   if text_log start with py -> added to the .log file (python command)
        *   if text_log starts with Process -> Text added to the StatusBar only
        *   if text_log == "clear status bar" -> the status bar is cleared
        *   if text_log start with nothing -> just print to the QTextEdit
        *   if text_log out from stdout -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file (comments)

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
                self.tracking_journal_QTextEdit.textCursor().insertHtml("<FONT COLOR='#FF8C00'> WARNING: The "
                                                                        "log file is not indicated in the xml file. No log written. </br> <br>")
                return
            # restart log
            child_logfile = root.find(".//File_Restart")
            if child_logfile is not None:
                pathname_restartfile = os.path.join(self.path_prj_c, child_logfile.text)
            else:
                self.tracking_journal_QTextEdit.textCursor().insertHtml("<FONT COLOR='#FF8C00'> WARNING: The "
                                                                        "restart file is not indicated in the xml file. No log written. </br> <br>")
                return
        else:
            # if only one tab, project not open, so it is normal that no log can be written.
            if self.tab_widget.count() > 1:
                self.tracking_journal_QTextEdit.textCursor().insertHtml(
                    "<FONT COLOR='#FF8C00'> WARNING: The project file is not "
                    "found. no Log written. </br> <br>")
            return

        # add comments to QTextEdit and .log file
        if text_log[0] == '#':
            # set text cursor to the end (in order to append text at the end)
            self.scrolldown_log()
            self.tracking_journal_QTextEdit.textCursor().insertHtml(
                text_log[1:] + '</br><br>')  # "<FONT COLOR='#000000'>" +
            self.write_log_file(text_log, pathname_logfile)
        # add python code to the .log file
        elif text_log[:2] == 'py':
            self.write_log_file(text_log[2:], pathname_logfile)
        # add restart command to the restart file
        elif text_log[:7] == 'restart':
            self.write_log_file(text_log[7:], pathname_restartfile)
        elif text_log[:5] == 'Error' or text_log[:6] == 'Erreur':
            self.scrolldown_log()
            self.tracking_journal_QTextEdit.textCursor().insertHtml(
                "<FONT COLOR='#FF0000'>" + text_log + ' </br><br>')  # error in red
            self.write_log_file('# ' + text_log, pathname_logfile)
        # add warning
        elif text_log[:7] == 'Warning':
            self.scrolldown_log()
            self.tracking_journal_QTextEdit.textCursor().insertHtml(
                "<FONT COLOR='#FF8C00'>" + text_log + ' </br><br>')  # warning in orange
            self.write_log_file('# ' + text_log, pathname_logfile)
        # update to check that processus is alive
        elif text_log[:7] == 'Process':
            self.parent().statusBar().showMessage(text_log)
        elif text_log == 'clear status bar':
            self.parent().statusBar().clearMessage()
            self.parent().progress_bar.setVisible(False)  # hide progressbar
        # other case not accounted for
        else:
            self.scrolldown_log()
            self.tracking_journal_QTextEdit.textCursor().insertHtml(
                text_log + '</br><br>')  # "<FONT COLOR='#000000'>" +

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
                self.tracking_journal_QTextEdit.textCursor().insertHtml(
                    "<FONT COLOR='#FF8C00'> WARNING: Log file not found. New log created. </br> <br>")
                shutil.copy(os.path.join('files_dep', 'log0.txt'),
                            os.path.join(self.path_prj_c, self.name_prj_c + '.log'))
                shutil.copy(os.path.join('files_dep', 'restart_log0.txt'),
                            os.path.join(self.path_prj_c, 'restart_' + self.name_prj_c + '.log'))
                with open(pathname_logfile, "a", encoding='utf8') as myfile:
                    myfile.write("    name_project = " + self.name_prj_c + "'\n")
                with open(pathname_logfile, "a", encoding='utf8') as myfile:
                    myfile.write("    path_project = " + self.path_prj_c + "'\n")
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
            hyd_name2 = []  # we might have no hdf5 file in the xml project file
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
        is already saved by another functions. However, it is useful for the Welcome Tab and the Option Tab.
        This function can be modified if needed for new tabs.

        Careful, the order of the tab is important here.
        """

        if self.old_ind_tab == 0:
            self.save_info_projet()
        # elif self.old_ind_tab == self.opttab:
        #     self.output_tab.save_preferences()
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

    def update_specific_tab(self):
        # calc hab
        if self.tab_widget.currentIndex() == 3:
            self.bioinfo_tab.update_merge_list()
        # data_explorer_tab
        elif self.tab_widget.currentIndex() == 4:
            self.data_explorer_tab.refresh_type()
        # tools_tab
        elif self.tab_widget.currentIndex() == 5:
            self.tools_tab.refresh_hab_filenames()


class EmptyTab(QWidget):
    """
    This class is  used to fill empty tabs with something during the developement.
    It will not be use in the final version.
    """

    def __init__(self):
        super().__init__()
        self.tab_name = "research"
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


class AltTabPressEater(QObject):
    next_signal = pyqtSignal()
    previous_signal = pyqtSignal()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == 16777217:
            self.next_signal.emit()
            return True # eat alt+tab or alt+shift+tab key
        elif event.type() == QEvent.KeyPress and event.key() == 16777218:
            self.previous_signal.emit()
            return True  # eat alt+tab or alt+shift+tab key
        else:
            # standard event processing
            return QObject.eventFilter(self, obj, event)


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

        """ WIDGETS """
        actual_version_label_title = QLabel(self.tr('Actual'))
        actual_version_label = QLabel(str(self.actual_version))

        last_version_label_title = QLabel(self.tr('Last'))
        self.last_version_label = QLabel("-")

        self.close_button = QPushButton(self.tr("Ok"))
        self.close_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.close_button.clicked.connect(self.close_dialog)

        """ LAYOUT """
        # versions layout
        layout_general_options = QFormLayout()
        general_options_group = QGroupBox(self.tr("HABBY version"))
        general_options_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        general_options_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        general_options_group.setLayout(layout_general_options)
        layout_general_options.addRow(actual_version_label_title, actual_version_label)
        layout_general_options.addRow(last_version_label_title, self.last_version_label)

        # general
        layout = QVBoxLayout(self)
        layout.addWidget(general_options_group)
        layout.addWidget(self.close_button)
        #layout.setAlignment(Qt.AlignRight)
        self.setWindowTitle(self.tr("About"))
        self.setWindowIcon(QIcon(self.name_icon))

    def get_last_version_number_from_github(self):
        last_version_str = "unknown"
        try:
            url_github = 'https://api.github.com/repos/YannIrstea/habby/tags'
            with urllib.request.urlopen(url_github) as response:
                html = response.read()
                last_version_str = eval(html)[0]["name"][1:]
                self.last_version_label.setText(last_version_str)
        except:
            print("no internet access")
            self.last_version_label.setText(last_version_str)

    def showEvent(self, event):
        # do stuff here
        self.get_last_version_number_from_github()
        event.accept()

    def close_dialog(self):
        self.close()


if __name__ == '__main__':
    pass
