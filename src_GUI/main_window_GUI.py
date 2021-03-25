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
from platform import system as operatingsystem
from subprocess import call
from webbrowser import open as wbopen
import matplotlib as mpl
import numpy as np
import qdarkstyle
from PyQt5.QtCore import QTranslator, pyqtSignal, Qt, pyqtRemoveInputHook
from PyQt5.QtGui import QPixmap, QIcon, QTextCursor, QColor
from PyQt5.QtWidgets import QMainWindow, QComboBox, QDialog, QApplication, QWidget, QPushButton, \
    QLabel, QGridLayout, QAction, QVBoxLayout, QGroupBox, QSizePolicy, QTabWidget, QLineEdit, QTextEdit, \
    QFileDialog, QMessageBox, QFrame, QMenu, QToolBar, QProgressBar
from json import decoder
mpl.use("Qt5Agg")  # backends and toolbar for pyqt5

from src_GUI import welcome_GUI
from src_GUI import estimhab_GUI
from src_GUI import sub_and_merge_GUI
from src_GUI import hydrau_GUI
from src_GUI import stathab_GUI
from src_GUI import project_properties_GUI
from src_GUI import data_explorer_GUI
from src_GUI import tools_GUI
from src_GUI import calc_hab_GUI
from src_GUI import fstress_GUI
from src_GUI import about_GUI
from src_GUI.bio_model_explorer_GUI import BioModelExplorerWindow
from src_GUI.process_manager_GUI import ProcessProgLayout
from src.project_properties_mod import load_project_properties, load_specific_properties, change_specific_properties,\
    create_project_structure, save_project_properties
from habby import HABBY_VERSION_STR
from src.user_preferences_mod import user_preferences
from src import hdf5_mod
from src.about_mod import get_last_version_number_from_github


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
    children classes. For each project, an xml file is created. This “project” file should be called name_prj.habby
    and should be situated in the path indicated by self.path_prj.

    We call the central_widget which contains the different tabs.

    We create the menu of HABBY calling the function my menu_bar().

    Two signal are connected, one to save the project (i.e to update the xml project file) and another to save an
    ESTIMHAB calculation.

    We show the created widget.
    """

    def __init__(self, name_path=None):
        self.habby_project_file_corrupted = False
        # the maximum number of recent project shown in the menu. if changement here modify self.my_menu_bar
        self.nb_recent = 5
        self.research_tabs = False
        self.physic_tabs = False
        self.stat_tabs = False
        # the version number of habby
        # CAREFUL also change the version in habby.py for the command line version
        self.version = str(HABBY_VERSION_STR)
        self.beta = True  # if set to True : GUI beta version mode is runned (block fonctionality)

        # operating system
        self.myEnv = dict(os.environ)

        if operatingsystem() == "Linux":
            lp_key = 'LD_LIBRARY_PATH'
            lp_orig = self.myEnv.get(lp_key + '_ORIG')
            if lp_orig is not None:
                self.myEnv[lp_key] = lp_orig
            else:
                lp = self.myEnv.get(lp_key)
                if lp is not None:
                    self.myEnv.pop(lp_key)

        language_set = user_preferences.data["language"]
        self.actual_theme = user_preferences.data["theme"]

        recent_projects_set = user_preferences.data["recent_project_name"]
        recent_projects_path_set = user_preferences.data["recent_project_path"]
        if recent_projects_set:
            if len(recent_projects_set) > self.nb_recent:
                user_preferences.data["recent_project_name"] = recent_projects_set[-self.nb_recent + 1:]
                user_preferences.data["recent_project_path"] = recent_projects_path_set[-self.nb_recent + 1:]

        # set up translation
        self.languageTranslator = QTranslator()
        self.path_trans = os.path.abspath('translation')
        self.file_langue = [r'Zen_EN.qm', r'Zen_FR.qm', r'Zen_ES.qm', r'Zen_PO.qm']
        try:  # english, french, spanish
            if language_set == "english":
                self.lang = 0
            if language_set == "french":
                self.lang = 1
            if language_set == "spanish":
                self.lang = 2
            if language_set == "portuguese":
                self.lang = 3
        except:
            self.lang = 0
        self.app = QApplication.instance()
        self.app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[self.lang], self.path_trans)
        self.app.installTranslator(self.languageTranslator)

        # prepare the attributes, careful if change the Qsetting!
        self.msg2 = QMessageBox()

        if recent_projects_set:
            self.recent_project = recent_projects_set[::-1]
        else:
            self.recent_project = []
        if recent_projects_path_set:
            self.recent_project_path = recent_projects_path_set[::-1]
        else:
            self.recent_project_path = []

        self.name_prj = ''
        self.path_prj = ''
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
        elif self.lang == 3:
            lang_bio = 'Portuguese'
        else:
            lang_bio = 'English'

        self.central_widget = CentralW(self.path_prj,
                                       self.name_prj,
                                       lang_bio)

        self.msg2 = QMessageBox()
        # call the normal constructor of QWidget
        super().__init__()
        pyqtRemoveInputHook()

        # call an additional function during initialization
        self.init_ui()

        # open_project
        last_path_prj = user_preferences.data["path_prj"]
        last_name_prj = user_preferences.data["name_prj"]
        filename_path = os.path.join(last_path_prj, last_name_prj + ".habby")

        # direct open (with habby.exe + arg path)
        if name_path:
            filename_path = name_path
        if os.path.exists(filename_path):
            if os.stat(filename_path).st_size != 0:
                try:
                    self.open_project(filename_path)
                except decoder.JSONDecodeError:
                    self.habby_project_file_corrupted = True
                    self.path_prj = ''
            else:
                self.habby_project_file_corrupted = True
                self.path_prj = ''
        else:
            self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('Create or open a project.') + '</br><br>')

        # bio_model_explorer_dialog
        if hasattr(self.central_widget, "data_explorer_tab"):
            self.bio_model_explorer_dialog = BioModelExplorerWindow(self, self.path_prj, self.name_prj, self.name_icon)
            self.bio_model_explorer_dialog.send_log.connect(self.central_widget.write_log)
            self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(self.central_widget.write_log)
            self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)

        # create the menu bar
        self.my_menu_bar()

        # user_attempt_to_add_preference_curve
        if user_preferences.user_attempt_to_add_preference_curve:
            self.central_widget.write_log(user_preferences.user_attempt_to_add_preference_curve)

        # print modification biological database
        if user_preferences.diff_list:
            self.central_widget.write_log("Warning: " + self.tr("Biological models database has been modified : ") + user_preferences.diff_list)

        if self.habby_project_file_corrupted:
            self.central_widget.write_log(self.tr('Error: .habby file is corrupted : ' + filename_path))
            self.central_widget.write_log(self.tr('Create or open another project.'))

        # run_as_beta_version
        self.run_as_beta_version()

        # open window
        self.show()

    def init_ui(self):
        """ Used by __init__() to create an instance of the class MainWindows """

        # set window icon
        self.name_icon = os.path.join(os.getcwd(), "translation", "habby_icon.png")
        self.setWindowIcon(QIcon(self.name_icon))

        # position theme
        wind_position_x, wind_position_y, wind_position_w, wind_position_h = user_preferences.data["wind_position"]
        self.setGeometry(wind_position_x, wind_position_y, wind_position_w, wind_position_h)

        # create a vertical toolbar
        self.toolbar = QToolBar()
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)
        self.my_toolbar()

        # connect the signals of the welcome tab with the different functions (careful if changes this copy 3 times
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_existing_project_dialog)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.open_new_project_dialog)

        self.setCentralWidget(self.central_widget)

        self.preferences_dialog = project_properties_GUI.ProjectPropertiesDialog(self.path_prj, self.name_prj, self.name_icon)

        # check_version_dialog
        self.check_version_dialog = about_GUI.CheckVersionDialog(self.path_prj, self.name_prj, self.name_icon, self.version)
        self.soft_information_dialog = about_GUI.SoftInformationDialog(self.path_prj, self.name_prj, self.name_icon, self.version)

        # inverse before changing theme
        if self.actual_theme == "classic":
            self.actual_theme = "dark"
        else:
            self.actual_theme = "classic"

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        self.change_theme()

        self.check_need_of_update_sofware()

        self.check_concurrency()

    def closeEvent(self, event):
        """
        This is the function which handle the closing of the program. It use the function end_concurrency() to indicate
        to other habby instances that we do not use a particular project anymore.

        We use os_exit instead of sys.exit so it also close the other thread if more than one is open.

        :param event: managed by the operating system.
        """
        process_alive_list = self.central_widget.get_process_alive_list()

        if process_alive_list:
            qm = QMessageBox
            ret = qm.question(self,
                              self.tr(", ".join(process_alive_list) + " still running"),
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

        # close all process
        if hasattr(self, "central_widget"):
            self.central_widget.kill_process_plot_list()
            self.central_widget.kill_process_list()
            self.central_widget.save_info_projet()

        # save wind_position if not fullscreen or not maximazed
        if self.isMaximized() or self.isFullScreen():
            pass
        else:
            user_preferences.data["wind_position"] = (self.geometry().x(),
                                                           self.geometry().y(),
                                                           self.geometry().width(),
                                                           self.geometry().height())
        user_preferences.data["theme"] = self.actual_theme
        user_preferences.save_user_preferences_json()

        os._exit(1)

    # VERSION

    def run_as_beta_version(self):
        """
        Disable desired hydraulic and statistic models if not finished and change windowtitle for Habby beta version.
        If True : run as beta
        If False : run as stable release or dev.
        """
        if self.beta:
            # self.name_models_gui_to_disable_list
            if hasattr(self.central_widget, "hydro_tab"):
                for model_index in range(len(self.central_widget.hydro_tab.hydraulic_model_information.name_models_gui_list)):
                    if not self.central_widget.hydro_tab.hydraulic_model_information.available_models_tf_list[model_index]:
                        self.central_widget.hydro_tab.model_list_combobox.model().item(model_index + 1).setEnabled(False)

            # disable_model_statistic
            # self.statisticmodelaction.setEnabled(False)
            if hasattr(self.central_widget, "estimhab_tab"):
                self.central_widget.estimhab_tab.setEnabled(True)
            # if hasattr(self.central_widget, "estimhab_tab"):
            #     self.central_widget.estimhab_tab.setEnabled(True)
            # if hasattr(self.central_widget, "stathab_tab"):
            #     self.central_widget.stathab_tab.setEnabled(False)
            # if hasattr(self.central_widget, "fstress_tab"):
            #     self.central_widget.fstress_tab.setEnabled(False)

            # # change GUI title
            windows_title = self.version
            if "Beta" not in self.version:
                windows_title = self.version + " Beta"
            if self.name_prj:
                self.setWindowTitle(self.tr('HABBY ') + windows_title + " - " + self.name_prj)
            else:
                self.setWindowTitle(self.tr('HABBY ') + windows_title)

    # PROJECT

    def open_new_project_dialog(self):
        """
        This function open an empty project and guide the user to create a new project, using a new Windows
        of the class CreateNewProjectDialog
        """
        pathprj_old = self.path_prj

        self.end_concurrency()

        # open a new Windows to ask for the info for the project
        self.createnew = CreateNewProjectDialog(self.lang, self.physic_tabs, self.stat_tabs, pathprj_old)
        self.createnew.create_project.connect(self.create_project)
        self.createnew.send_log.connect(self.central_widget.write_log)

        ## disable_model_statistic
        # if self.beta:
        #     self.createnew.project_type_combobox.model().item(1).setEnabled(False)
        #     self.createnew.project_type_combobox.model().item(2).setEnabled(False)
        self.createnew.show()

    def open_existing_project_dialog(self):
        """
        This function is used to open an existing habby project by selecting an xml project file. Called by
        my_menu_bar()
        """
        #  indicate to HABBY that this project will close
        self.end_concurrency()

        # open an xml file
        if self.path_prj:
            path_here = os.path.dirname(self.path_prj)
        else:
            user_path = os.path.expanduser("~")
            user_document_path = os.path.join(user_path, "Documents")
            if os.path.exists(user_document_path):
                path_here = os.path.join(user_document_path, "HABBY_projects")
            else:
                path_here = os.path.join(user_path, "HABBY_projects")

        filename_path = \
        QFileDialog.getOpenFileName(self, self.tr('Open project'), path_here, "HABBY project (*.habby)")[0]
        if not filename_path:  # cancel
            return
        blob, ext_xml = os.path.splitext(filename_path)
        if ext_xml == '.habby':
            pass
        else:
            self.central_widget.write_log("Error: " + self.tr("File should be of type .habby\n"))
            return

        # normpath
        filename_path = os.path.normpath(filename_path)

        self.open_project(filename_path)

    def create_project(self):
        """
        This function is used to save a project when the project is created from the other Windows CreateNewProjectDialog. It
        can not be in the open_new_project_dialog function as the open_new_project_dialog function call CreateNewProjectDialog().
        """
        name_prj = self.createnew.e1.text()
        path_folder_prj = self.createnew.e2.text()
        project_type = self.createnew.project_type_combobox.currentText()
        if project_type == self.tr("physical"):
            self.physic_tabs = True
            self.stat_tabs = False
        elif project_type == self.tr("statistical"):
            self.physic_tabs = False
            self.stat_tabs = True
        elif project_type == self.tr("both"):
            self.physic_tabs = True
            self.stat_tabs = True

        if not os.path.exists(path_folder_prj):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Projects folder error"))
            self.msg2.setText(self.tr("Projects folder specify not exist. Please fix it before creating project. "))
            self.msg2.exec_()
            return

        # path
        path_prj = os.path.join(path_folder_prj, name_prj)

        # if exist : remove and create_project
        if os.path.isdir(path_prj):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Another folder with name " + name_prj + " already exists."))
            self.msg2.setText(self.tr("Do you want to overwrite it and all its files ?"))
            self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            res = self.msg2.exec_()

            # delete
            if res == QMessageBox.No:
                self.central_widget.write_log(
                    'Warning: ' + self.tr('Project not created. Choose another project name.'))
                self.createnew.close()
                return
            if res == QMessageBox.Yes:
                self.delete_project(path_prj)
                try:
                    os.makedirs(path_prj)
                except (PermissionError, FileExistsError):
                    self.msg2.setIcon(QMessageBox.Warning)
                    self.msg2.setWindowTitle(self.tr("Permission Error"))
                    self.msg2.setText(
                        self.tr(
                            "You do not have the permission to write in this folder. Choose another folder. \n"))
                    self.msg2.setStandardButtons(QMessageBox.Ok)
                    self.msg2.show()
                    return

                # pass the info from the extra Windows to the HABBY MainWindows
                # (check on user input done by create_project)
                self.central_widget.welcome_tab.name_prj_label.setText(name_prj)
                self.central_widget.welcome_tab.path_prj_label.setText(path_prj)
                self.central_widget.welcome_tab.description_prj_textedit.setText('')
                self.central_widget.welcome_tab.user_name_lineedit.setText('')
                self.createnew.close()
                self.save_project()
                self.central_widget.write_log('Warning: ' + self.tr('Old project and its files are deleted.'))

        # if not exist : create_project
        else:
            # add a new folder
            try:
                os.makedirs(path_prj)
            except PermissionError:
                self.msg2.setIcon(QMessageBox.Warning)
                self.msg2.setWindowTitle(self.tr("Permission Error"))
                self.msg2.setText(
                    self.tr("You do not have the permission to write in this folder. Choose another folder. \n"))
                self.msg2.setStandardButtons(QMessageBox.Ok)
                self.msg2.show()

            # pass the info from the extra Windows to the HABBY MainWindows (check on user input done by create_project)
            self.central_widget.welcome_tab.name_prj_label.setText(name_prj)
            self.central_widget.welcome_tab.path_prj_label.setText(path_prj)
            self.central_widget.welcome_tab.description_prj_textedit.setText('')
            self.central_widget.welcome_tab.user_name_lineedit.setText('')
            self.createnew.close()
            self.save_project()

        # reconnect method to button
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_existing_project_dialog)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.open_new_project_dialog)

        # write the new language in the figure option to be able to get the title, axis in the right language
        change_specific_properties(self.path_prj,
                                   preference_names=["language"],
                                   preference_values=[self.lang])
        #print("self.central_widget.setFocus()")
        self.central_widget.setFocus()

        self.central_widget.write_log(self.tr('Project created.'))

    def open_project(self, filename_path):
        """
        This function is used to open an existing habby project by selecting an xml project file. Called by
        my_menu_bar()
        """
        # save
        if self.path_prj:
            self.central_widget.save_info_projet()

        # get name and path
        self.path_prj = os.path.dirname(filename_path)
        self.name_prj = os.path.splitext(os.path.basename(filename_path))[0]

        # check if exist
        if not os.path.exists(os.path.join(self.path_prj, self.name_prj + ".habby")):
            self.central_widget.write_log("Error: " + self.tr("The selected project file does not exist.\n"))
            self.close_project()
            return

        # load_project_properties
        project_preferences = load_project_properties(self.path_prj)

        # the text in the Qwidget will be used to save the project
        self.name_prj = project_preferences["name_prj"]
        self.path_prj = project_preferences["path_prj"]
        self.central_widget.path_last_file_loaded = project_preferences["path_last_file_loaded"]

        self.username_prj = project_preferences["user_name"]
        self.descri_prj = project_preferences["description"]
        self.central_widget.welcome_tab.name_prj_label.setText(self.name_prj)
        self.central_widget.welcome_tab.path_prj_label.setText(self.path_prj)
        self.central_widget.welcome_tab.user_name_lineedit.setText(self.username_prj)
        self.central_widget.welcome_tab.description_prj_textedit.setText(self.descri_prj)

        # save the project
        self.central_widget.path_prj = self.path_prj
        self.central_widget.name_prj = self.name_prj

        # recreate new widget
        self.recreate_tabs_attributes()

        # # update estimhab and stathab
        # if project_preferences["STATHAB"]["hdf5"]:  # if there is data for STATHAB
        #     self.central_widget.stathab_tab.load_from_hdf5_gui()

        # update hydro
        self.central_widget.update_combobox_filenames()
        self.central_widget.substrate_tab.sub_and_merge.update_sub_hdf5_name()

        # set the central widget
        for i in range(self.central_widget.tab_widget.count(), -1, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.name_prj = self.name_prj
        self.central_widget.path_prj = self.path_prj
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
        self.central_widget.welcome_tab.open_proj.connect(self.open_existing_project_dialog)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.open_new_project_dialog)

        # write the new language in the figure option to be able to get the title, axis in the right language
        change_specific_properties(self.path_prj,
                                   preference_names=["language"],
                                   preference_values=[self.lang])

        # check if project open somewhere else
        self.check_concurrency()

        user_preferences.data["name_prj"] = self.name_prj
        user_preferences.data["path_prj"] = self.path_prj
        if not self.name_prj in user_preferences.data["recent_project_name"]:
            user_preferences.data["recent_project_name"] = user_preferences.data["recent_project_name"] + [
                self.name_prj]
        if not self.path_prj in user_preferences.data["recent_project_path"]:
            user_preferences.data["recent_project_path"] = user_preferences.data["recent_project_path"] + [
                self.path_prj]
        user_preferences.save_user_preferences_json()

        self.my_menu_bar()

        # check version
        project_version = project_preferences["version_habby"]
        if float(self.version) > float(project_version):
            self.central_widget.write_log(self.tr('Warning: Current project is an old HABBY project. Working with this can lead to software crashes. It is advisable to recreate a new project.'))

        self.central_widget.write_log(self.tr('Project opened.'))

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
        path_prj = os.path.normpath(self.central_widget.welcome_tab.path_prj_label.text())
        if not os.path.isdir(path_prj):  # if the directoy do not exist
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Path to project"))
            self.msg2.setText(
                self.tr("The directory indicated in the project path does not exists. Project not saved."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            self.central_widget.write_log('# ' + self.tr('Project not saved.'))
            return
        else:
            path_prj_before = self.path_prj
            self.path_prj = path_prj
        # name
        e1here = self.central_widget.welcome_tab.name_prj_label
        self.name_prj = e1here.text()

        # username and description
        e4here = self.central_widget.welcome_tab.user_name_lineedit
        self.username_prj = e4here.text()
        e3here = self.central_widget.welcome_tab.description_prj_textedit
        self.descri_prj = e3here.toPlainText()

        fname = os.path.join(self.path_prj, self.name_prj + '.habby')

        # update user option and re-do (the whole) menu
        user_preferences.data["name_prj"] = self.name_prj
        user_preferences.data["path_prj"] = self.path_prj

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
        user_preferences.data["recent_project_name"] = self.recent_project
        user_preferences.data["recent_project_path"] = self.recent_project_path
        user_preferences.save_user_preferences_json()

        # create structure project
        if not os.path.isfile(fname):
            create_project_structure(self.path_prj,
                                                       self.central_widget.logon,
                                                       self.version,
                                                       self.username_prj,
                                                       self.descri_prj,
                                                       "GUI")
            change_specific_properties(self.path_prj,
                                       preference_names=["physic_tabs", "stat_tabs"],
                                       preference_values=[self.physic_tabs, self.stat_tabs])

        self.my_menu_bar()

        # update central widget
        self.central_widget.name_prj = self.name_prj
        self.central_widget.path_prj = self.path_prj
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj

        # send the new name to all widget and re-connect signal
        t = self.central_widget.tracking_journal_QTextEdit.toPlainText()
        m = self.central_widget.tab_widget.count()

        for i in range(m, 0, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.tab_widget.removeTab(0)

        # recreate new widget
        #print("recreate_tabs_attributes2")
        self.recreate_tabs_attributes()

        # add_all_tab
        self.central_widget.add_all_tab()

        # re-connect signals for the tab
        self.central_widget.connect_signal_fig_and_drop()
        self.central_widget.connect_signal_log()

        # update name
        self.central_widget.update_combobox_filenames()

        # change language
        change_specific_properties(self.path_prj,
                                   preference_names=["language"],
                                   preference_values=[self.lang])

        self.preferences_dialog.set_pref_gui_from_dict(default=True)
        self.check_version_dialog = about_GUI.CheckVersionDialog(self.path_prj, self.name_prj, self.name_icon, self.version)
        self.soft_information_dialog = about_GUI.SoftInformationDialog(self.path_prj, self.name_prj, self.name_icon, self.version)

        # write log
        self.central_widget.tracking_journal_QTextEdit.clear()
        # self.central_widget.write_log('# ' + self.tr('Log of HABBY started.'))
        # self.central_widget.write_log('# ' + self.tr('Project saved or opened successfully.'))
        self.central_widget.write_log("py    name_prj= r'" + self.name_prj + "'")
        self.central_widget.write_log("py    path_prj= r'" + self.path_prj + "'")
        self.central_widget.write_log("py    path_bio= r'" + os.path.join(os.getcwd(), self.path_bio_default) + "'")
        self.central_widget.write_log("py    version_habby= " + str(self.version))
        self.central_widget.write_log("restart NAME_PROJECT")
        self.central_widget.write_log("restart    Name of the project: " + self.name_prj)
        self.central_widget.write_log("restart    Path of the project: " + self.path_prj)
        self.central_widget.write_log("restart    version habby: " + str(self.version))


        self.run_as_beta_version()

        # enabled lowest part
        self.central_widget.welcome_tab.current_prj_groupbox.setEnabled(True)

    def open_recent_project(self, j):
        """
        This function open a recent project of the user. The recent project are listed in the menu and can be
        selected by the user. When the user select a recent project to open, this function is called. Then, the name of
        the recent project is selected and the method create_project() is called.

        :param j: This indicates which project should be open, based on the order given in the menu
        """

        # indicate to HABBY that this project will close
        self.end_concurrency()

        # get the project file
        filename_path = os.path.join(self.recent_project_path[j], self.recent_project[j] + '.habby')

        # normpath
        filename_path = os.path.normpath(filename_path)

        if os.path.exists(filename_path):
            self.open_project(filename_path)
        else:
            self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
                "<FONT COLOR='#FF8C00'>Warning: " + filename_path + self.tr(' project not found. It must have been moved or removed.') + ' </br><br>')  # warning in orange

    def close_project(self):
        """
        This function close the current project without opening a new project
        """
        self.end_concurrency()

        # open an empty project (so it close the old one)
        self.empty_project()

        # remove tab 9as we have no project anymore)
        for i in range(self.central_widget.tab_widget.count(), 0, -1):
            self.central_widget.tab_widget.removeTab(i)

        # add the welcome Widget
        self.central_widget.tab_widget.addTab(self.central_widget.welcome_tab, self.tr("Project"))
        self.central_widget.welcome_tab.current_prj_groupbox.setEnabled(False)

        # create the menu bar
        self.my_menu_bar()

        # clear log
        self.clear_log()
        self.central_widget.write_log(self.tr('Create or open a project.'))

    def delete_project(self, new_project_path):
        try:
            shutil.rmtree(new_project_path)
        except:
            self.central_widget.write_log(
                'Error: ' + self.tr('Old project and its files are opened by another programme.\n'
                                    'Close them and try again.'))

    def empty_project(self):
        """
        This function opens a new empty project
        """
        self.path_prj = ""
        self.name_prj = ""
        self.central_widget.welcome_tab.name_prj_label.setText("")
        self.central_widget.welcome_tab.path_prj_label.setText("")
        self.central_widget.welcome_tab.user_name_lineedit.setText('')
        self.central_widget.welcome_tab.description_prj_textedit.setText('')

        self.setWindowTitle(self.tr('HABBY ') + str(self.version))

    def check_concurrency(self):
        """
        This function tests if the project which is opening by HABBY is not used by another instance of HABBY. It is
        dangerous  to open two time the same project as we have problem with the writing of the xml files.

        To check if a project is open, we have a text file in the project folder named "check_concurrency.txt".
        In this text file, there is either the word "open" or "close". When HABBY open a new project, it checks
        this file is set to close and change it to open. Hence, if a project is open twice a warning is written.
        """
        if self.name_prj != "":

            # open the text file
            filename = os.path.join(os.path.join(self.path_prj, 'hdf5'), 'check_concurrency.txt')
            if not os.path.isfile(filename):
                self.central_widget.write_log('Warning: ' + self.tr('Could not check if the project was open by '
                                                                    'another instance of HABBY (1) \n'))
                if os.path.isdir(os.path.join(self.path_prj, 'hdf5')):
                    with open(filename, 'wt') as f:
                        f.write('open')
                return

            # check if open
            try:
                with open(filename, 'rt') as f:
                    data = f.read()
            except IOError:
                self.central_widget.write_log(
                    'Warning: ' + self.tr('Could not check if the project was open by another '
                                          'instance of HABBY (2) \n'))
                return
            if data == 'open':
                self.central_widget.write_log(
                    'Warning: ' + self.tr('The same project is open in another instance of HABBY.'
                                          ' This could results in fatal and unexpected error. '
                                          'It is strongly adivsed to close the other instance of HABBY. This message could also appear if HABBY was not closed properly'
                                          '. In this case, please close and re-open HABBY.\n'))

            else:
                with open(filename, 'wt') as f:
                    f.write('open')

    def check_need_of_update_sofware(self):
        last_float = 0
        actual_float = 0
        last = get_last_version_number_from_github()
        actual = HABBY_VERSION_STR

        if last == "unknown":  # no internet acces
            pass
        else:
            try:
                last_float = float(last)
            except:
                print("Error: Can't convert last version to float number :", last)
            try:
                actual_float = float(actual)
            except:
                print("Error: Can't convert actual version to float number :", actual)

            if actual_float < last_float:
                self.central_widget.write_log(self.tr("Warning: A new version of the HABBY software is available! "
                                                                                               "It is strongly advised to update from " + str(actual_float) + self.tr(" to ") + str(last_float) + " and take into consideration the latest changes."))

    def end_concurrency(self):
        """
        This function indicates to the project folder than this project is not used anymore. Hence, this project
        can be used freely by an other instance of HABBY.
        """
        if self.name_prj != "":

            # open the text file
            filename = os.path.join(os.path.join(self.path_prj, 'hdf5'), 'check_concurrency.txt')
            if not os.path.isfile(filename):
                self.central_widget.write_log('Warning: ' + self.tr('Could not check if the project was open by '
                                                                    'another instance of HABBY (3) \n'))
                return

            try:
                with open(filename, 'wt') as f:
                    f.write('close')
            except IOError:
                return

    # GUI

    def fill_selected_models_listwidets(self):
        # get dict
        item_dict = self.bio_model_explorer_dialog.bio_model_infoselection_tab.item_dict

        if item_dict["source_str"] == "calc_hab":
            self.central_widget.bioinfo_tab.fill_selected_models_listwidets(item_dict)

        elif item_dict["source_str"] == "stat_hab":
            self.central_widget.stathab_tab.fill_selected_models_listwidets(item_dict)

        elif item_dict["source_str"] == "fstress":
            self.central_widget.fstress_tab.fill_selected_models_listwidets(item_dict)

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
        #print("setlangue", self.sender())
        # set the language
        self.lang = int(nb_lang)
        # get the old tab
        ind_tab = self.central_widget.tab_widget.currentIndex()
        # if plot process are open, close them
        if hasattr(self.central_widget, "data_explorer_tab"):
            if hasattr(self.central_widget.data_explorer_tab.data_explorer_frame, 'process_manager'):
                self.central_widget.data_explorer_tab.data_explorer_frame.process_manager.close_all_export()
        # get a new translator
        self.app = QApplication.instance()
        self.app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[self.lang], self.path_trans)
        self.app.installTranslator(self.languageTranslator)

        # recreate new widget
        #print("recreate_tabs_attributes3")
        self.recreate_tabs_attributes()
        if self.central_widget.tab_widget.count() == 1:
            self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)

        # pass the info to the bio info tab
        if nb_lang == 0:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'English'
        elif nb_lang == 1:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'French'
        elif nb_lang == 3:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'Portuguese'
        else:
            if hasattr(self.central_widget, "bioinfo_tab"):
                self.central_widget.bioinfo_tab.lang = 'Spanish'

        # write the new language in the figure option to be able to get the title, axis in the right language
        if os.path.exists(self.path_prj):
            change_specific_properties(self.path_prj,
                                       preference_names=["language"],
                                       preference_values=[self.lang])

        # set the central widget
        for i in range(self.central_widget.tab_widget.count(), -1, -1):
            self.central_widget.tab_widget.removeTab(i)
        self.central_widget.name_prj = self.name_prj
        self.central_widget.path_prj = self.path_prj
        self.central_widget.add_all_tab()
        self.central_widget.welcome_tab.name_prj = self.name_prj
        self.central_widget.welcome_tab.path_prj = self.path_prj

        # create the new menu
        self.my_menu_bar()
        # create the new toolbar
        self.my_toolbar()
        # reconnect signal for the welcome tab
        self.central_widget.welcome_tab.save_signal.connect(self.central_widget.save_info_projet)
        self.central_widget.welcome_tab.open_proj.connect(self.open_existing_project_dialog)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.open_new_project_dialog)
        self.central_widget.welcome_tab.save_info_signal.connect(self.central_widget.save_info_projet)

        # re-connect signals for the other tabs
        self.central_widget.connect_signal_fig_and_drop()
        # re-connect signals for the log
        self.central_widget.connect_signal_log()

        self.central_widget.update_combobox_filenames()
        # if hasattr(self.central_widget, 'chronicle_tab') == True:
        #     self.central_widget.update_merge_for_chronicle()

        # update user option to remember the language
        if self.lang == 0:
            language = "english"
        if self.lang == 1:
            language = "french"
        if self.lang == 2:
            language = "spanish"
        if self.lang == 3:
            language = "portuguese"
        if user_preferences.data["language"] != language:
            user_preferences.data["language"] = language
            user_preferences.save_user_preferences_json()

        self.run_as_beta_version()

        # open at the old tab
        self.central_widget.tab_widget.setCurrentIndex(ind_tab)

    def my_menu_bar(self):
        """
        This function creates the top menu bar of HABBY.
        """
        self.menubar = self.menuBar()
        self.menubar.clear()

        if self.path_prj:
            project_preferences = load_project_properties(self.path_prj)
            self.physic_tabs = project_preferences["physic_tabs"]
            self.stat_tabs = project_preferences["stat_tabs"]

        # add all first level menu
        self.menubar = self.menuBar()
        project_menu = self.menubar.addMenu(self.tr('Project'))
        settings_menu = self.menubar.addMenu(self.tr('Settings'))
        view_menu = self.menubar.addMenu(self.tr('View'))
        help_menu = self.menubar.addMenu(self.tr('Help'))

        # Menu to open and close file
        exitAction = QAction(self.tr('Exit HABBY'), self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip(self.tr('Exit application'))
        exitAction.triggered.connect(self.closeEvent)

        # project actions
        newprj = QAction(self.tr('New'), self)
        newprj.setShortcut('Ctrl+N')
        newprj.setStatusTip(self.tr('Create a new project'))
        newprj.triggered.connect(self.open_new_project_dialog)
        openprj = QAction(self.tr('Open'), self)
        openprj.setShortcut('Ctrl+O')
        openprj.setStatusTip(self.tr('Open an exisiting project'))
        openprj.triggered.connect(self.open_existing_project_dialog)
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
        self.preferences_action = QAction(self.tr('Properties'))
        self.preferences_action.triggered.connect(self.open_project_properties)
        self.preferences_action.setShortcut('Ctrl+P')
        tabs_menu = QMenu(project_menu)
        tabs_menu.setTitle(self.tr('Tabs'))
        self.physicalmodelaction = QAction(self.tr('Physical tabs'), checkable=True)
        self.physicalmodelaction.triggered.connect(self.open_close_physic)
        self.statisticmodelaction = QAction(self.tr('Statistical tabs'), checkable=True)
        self.statisticmodelaction.triggered.connect(self.open_close_stat)
        self.researchmodelaction = QAction(self.tr("Research tabs"), checkable=True)  # hidded
        self.researchmodelaction.triggered.connect(self.open_close_rech)  # hidded
        self.researchmodelaction.setShortcut('Ctrl+R')  # hidded
        log_menu = QMenu(project_menu)
        log_menu.setTitle(self.tr('Log'))
        logc = QAction(self.tr("Clear log"), self)
        logc.setStatusTip(self.tr('Empty the log windows at the bottom of the main window. Do not erase the .log file.'))
        logc.setShortcut('Ctrl+L')
        logc.triggered.connect(self.clear_log)
        logn = QAction(self.tr("Do not save log"), self)
        logn.setStatusTip(self.tr('The .log file will not be updated further.'))
        logn.triggered.connect(lambda: self.do_log(0))
        logy = QAction(self.tr("Save log"), self)
        logy.setStatusTip(self.tr('Events will be written to the .log file.'))
        logy.triggered.connect(lambda: self.do_log(1))
        figure_menu = QMenu(project_menu)
        figure_menu.setTitle(self.tr('Figure management'))
        savi = QAction(self.tr("Delete all figure files"), self)
        savi.setStatusTip(self.tr('Figures files of current project will be deleted'))
        savi.triggered.connect(self.remove_all_figure_files)
        closeim = QAction(self.tr("Close all figure windows"), self)
        closeim.setStatusTip(self.tr('Close all open figure windows'))
        closeim.triggered.connect(self.central_widget.kill_process_list)
        closeim.setShortcut('Ctrl+B')
        closeprj = QAction(self.tr('Close'), self)
        closeprj.setShortcut('Ctrl+W')
        closeprj.setStatusTip(self.tr('Close the current project without opening a new one'))
        closeprj.triggered.connect(self.close_project)

        # settings actions
        self.english_action = QAction(self.tr('&English'), self, checkable=True)
        self.english_action.setStatusTip(self.tr('click here for English'))
        self.english_action.triggered.connect(lambda: self.setlangue(0))  # lambda because of the argument
        self.french_action = QAction(self.tr('&French'), self, checkable=True)
        self.french_action.setStatusTip(self.tr('click here for French'))
        self.french_action.triggered.connect(lambda: self.setlangue(1))
        self.spanish_action = QAction(self.tr('&Spanish'), self, checkable=True)
        self.spanish_action.setStatusTip(self.tr('click here for Spanish'))
        self.spanish_action.triggered.connect(lambda: self.setlangue(2))
        self.portuguese_action = QAction(self.tr('&Portuguese'), self, checkable=True)
        self.portuguese_action.setStatusTip(self.tr('click here for Portuguese'))
        self.portuguese_action.triggered.connect(lambda: self.setlangue(3))
        if self.lang == 0:
            self.english_action.setChecked(True)
            self.french_action.setChecked(False)
            self.spanish_action.setChecked(False)
            self.portuguese_action.setChecked(False)
        if self.lang == 1:
            self.english_action.setChecked(False)
            self.french_action.setChecked(True)
            self.spanish_action.setChecked(False)
            self.portuguese_action.setChecked(False)
        if self.lang == 2:
            self.english_action.setChecked(False)
            self.french_action.setChecked(False)
            self.spanish_action.setChecked(True)
            self.portuguese_action.setChecked(False)
        if self.lang == 3:
            self.english_action.setChecked(False)
            self.french_action.setChecked(False)
            self.spanish_action.setChecked(False)
            self.portuguese_action.setChecked(True)
        self.fullscreen_action = QAction(self.tr('Toggle full screen mode'), self, checkable=True)
        self.fullscreen_action.triggered.connect(self.set_unset_fullscreen)
        self.fullscreen_action.setShortcut('F11')
        self.fullscreen_action.setChecked(False)
        self.change_theme_action = QAction(self.tr('Change theme'), self)
        self.change_theme_action.triggered.connect(self.change_theme)
        self.change_theme_action.setShortcut('F12')

        # user_help_action
        user_help_action = QAction(self.tr('Help contents'), self)
        user_help_action.setStatusTip(self.tr('Get help to use the program'))
        user_help_action.triggered.connect(self.open_user_help)
        user_help_action.setShortcut('F1')

        # dev_help_action
        dev_help_action = QAction(self.tr('API documentation'), self)
        dev_help_action.setStatusTip(self.tr('Get help to develop or use the program'))
        dev_help_action.triggered.connect(self.open_dev_help)

        # issue_action
        issue_action = QAction(self.tr('Report an issue'), self)
        issue_action.setStatusTip(self.tr('Report a repeatable problem'))
        issue_action.triggered.connect(self.open_issue_web_site)

        home_page_action = QAction(self.tr('HABBY official website'), self)
        home_page_action.setStatusTip(self.tr('Open the HABBY official website'))
        home_page_action.triggered.connect(self.open_web_site)
        home_page_action.setShortcut('CTRL+H')

        check_version = QAction(self.tr('Check HABBY version'), self)
        check_version.setStatusTip(self.tr('Check current and last HABBY version'))
        check_version.triggered.connect(self.open_check_version_dialog)

        soft_information = QAction(self.tr('About'), self)
        soft_information.setStatusTip(self.tr('Get software informations'))
        soft_information.triggered.connect(self.open_soft_information_dialog)

        # project menu
        project_menu.addAction(newprj)
        project_menu.addAction(openprj)
        recentpMenu = project_menu.addMenu(self.tr('Open recent'))
        for j in range(0, len(recent_proj_menu)):
            recentpMenu.addAction(recent_proj_menu[j])
        project_menu.addSeparator()
        project_menu.addAction(self.preferences_action)
        project_menu.addMenu(tabs_menu)
        tabs_menu.addAction(self.physicalmodelaction)
        tabs_menu.addAction(self.statisticmodelaction)
        self.addAction(self.researchmodelaction)  # hidded
        self.physicalmodelaction.setChecked(self.physic_tabs)
        self.statisticmodelaction.setChecked(self.stat_tabs)
        self.researchmodelaction.setChecked(self.research_tabs)  # hidded
        project_menu.addMenu(figure_menu)
        figure_menu.addAction(savi)
        figure_menu.addAction(closeim)
        project_menu.addMenu(log_menu)
        log_menu.addAction(logc)
        log_menu.addAction(logn)
        log_menu.addAction(logy)
        project_menu.addAction(closeprj)
        project_menu.addSeparator()
        project_menu.addAction(exitAction)

        # settings menu
        language_menu = settings_menu.addMenu(self.tr('Language'))
        language_menu.addAction(self.english_action)
        language_menu.addAction(self.french_action)
        language_menu.addAction(self.spanish_action)
        language_menu.addAction(self.portuguese_action)

        # view menu
        view_menu.addAction(self.fullscreen_action)
        view_menu.addAction(self.change_theme_action)

        # help menu
        help_menu.addAction(user_help_action)
        help_menu.addAction(dev_help_action)
        help_menu.addSeparator()
        help_menu.addAction(issue_action)
        help_menu.addSeparator()
        help_menu.addAction(home_page_action)
        help_menu.addAction(check_version)
        help_menu.addSeparator()
        help_menu.addAction(soft_information)

        # disable specific actions and menus
        if not self.path_prj:
            #print("disable menu project", self.path_prj)
            self.preferences_action.setEnabled(False)
            tabs_menu.setEnabled(False)
            log_menu.setEnabled(False)
            figure_menu.setEnabled(False)
            closeprj.setEnabled(False)
        else:
            #print("enable menu project", self.path_prj)
            self.preferences_action.setEnabled(True)
            tabs_menu.setEnabled(True)
            log_menu.setEnabled(True)
            figure_menu.setEnabled(True)
            closeprj.setEnabled(True)

        # add the status and progress bar
        self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.progress_bar.setVisible(False)

        # add the title of the windows
        if self.name_prj:
            self.setWindowTitle(self.tr('HABBY ') + str(self.version) + ' - ' + self.name_prj)
        else:
            self.setWindowTitle(self.tr('HABBY ') + str(self.version))

    def change_theme(self):
        #print("change_theme", self.sender(), self.change_theme_action.isChecked())
        if self.actual_theme == "dark":  # 'QScrollArea { background-color : white; }'
            self.app.setStyleSheet('QToolBar { background : white ;}'
                        'QFrame { background-color : white; }')
            #  'QGroupBox QGroupBox {background-color: green;}'
            self.actual_theme = "classic"
        else:
            self.app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            self.actual_theme = "dark"

        if user_preferences.data["theme"] != self.actual_theme:
            user_preferences.data["theme"] = self.actual_theme
            user_preferences.save_user_preferences_json()

    def set_unset_fullscreen(self):
        #print("set_unset_fullscreen", self.sender())
        if self.fullscreen_action.isChecked():
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
        else:
            self.showNormal()
            self.fullscreen_action.setChecked(False)

    def my_toolbar(self):
        #print("my_toolbar", self.sender())

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
        openAction.triggered.connect(self.open_existing_project_dialog)

        newAction = QAction(icon_new, self.tr('New project'), self)
        newAction.setStatusTip(self.tr('Create a new project'))
        newAction.triggered.connect(self.open_new_project_dialog)

        self.seeAction = QAction(icon_see, "clic = See current HABBY project files\n"
                                          "CTRL+clic = See user HABBY AppData files\n"
                                          "SHIFT+clic = See HABBY installation files", self)
        self.seeAction.setStatusTip(self.tr("clic = See current HABBY project files / "
                                          "CTRL+clic == See user HABBY AppData files / "
                                          "SHIFT+clic = See HABBY installation files"))
        self.seeAction.triggered.connect(self.see_file)

        closeAction = QAction(icon_closefig, self.tr('Close figure windows'), self)
        closeAction.setStatusTip(self.tr('Close all open figure windows'))
        closeAction.triggered.connect(self.central_widget.kill_process_plot_list)

        # self.kill_process_action = QAction(icon_kill, self.tr('Stop current process'), self)
        # self.kill_process_action.triggered.connect(partial(self.kill_process, close=True, isalive=False))
        # self.kill_process_action.setVisible(False)
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
        # self.toolbar.addAction(self.kill_process_action)

    def open_project_properties(self):
        #"open_project_properties", self.sender())
        self.preferences_dialog.open_preferences()
        # # witdh_for_checkbox_alignement
        witdh_for_checkbox_alignement = self.preferences_dialog.cut_2d_grid_label.size().width()
        self.preferences_dialog.erase_data_label.setMinimumWidth(witdh_for_checkbox_alignement)

    def recreate_tabs_attributes(self):
        # create new tab (there were some segmentation fault here as it re-write existing QWidget, be careful)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            if hasattr(self.central_widget, "welcome_tab"):
                if not self.central_widget.welcome_tab:
                    self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.welcome_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "hydro_tab"):
                if not self.central_widget.hydro_tab:
                    self.central_widget.hydro_tab = hydrau_GUI.HydrauTab(self.path_prj, self.name_prj)
                else:
                    self.central_widget.hydro_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.hydro_tab = hydrau_GUI.HydrauTab(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "substrate_tab"):
                if not self.central_widget.substrate_tab:
                    self.central_widget.substrate_tab = sub_and_merge_GUI.SubstrateTab(self.path_prj, self.name_prj)
                else:
                    self.central_widget.substrate_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.substrate_tab = sub_and_merge_GUI.SubstrateTab(self.path_prj, self.name_prj)

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
                    self.central_widget.data_explorer_tab.data_explorer_frame.send_remove.connect(
                        self.remove_hdf5_files)
                    self.central_widget.data_explorer_tab.data_explorer_frame.send_rename.connect(
                        self.rename_hdf5_file)

                else:
                    self.central_widget.data_explorer_tab.__init__(self.path_prj, self.name_prj)
                    self.central_widget.data_explorer_tab.data_explorer_frame.send_remove.connect(
                        self.remove_hdf5_files)
                    self.central_widget.data_explorer_tab.data_explorer_frame.send_rename.connect(
                        self.rename_hdf5_file)
            else:
                self.central_widget.data_explorer_tab = data_explorer_GUI.DataExplorerTab(self.path_prj, self.name_prj)
                self.central_widget.data_explorer_tab.data_explorer_frame.send_remove.connect(
                    self.remove_hdf5_files)
                self.central_widget.data_explorer_tab.data_explorer_frame.send_rename.connect(
                    self.rename_hdf5_file)

            if hasattr(self.central_widget, "tools_tab"):
                if not self.central_widget.tools_tab:
                    self.central_widget.tools_tab = tools_GUI.ToolsTab(self.path_prj, self.name_prj)
                else:
                    self.central_widget.tools_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.tools_tab = tools_GUI.ToolsTab(self.path_prj, self.name_prj)

            if hasattr(self.central_widget, "estimhab_tab"):
                if not self.central_widget.estimhab_tab:
                    self.central_widget.estimhab_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)
                else:
                    self.central_widget.estimhab_tab.__init__(self.path_prj, self.name_prj)
            else:
                self.central_widget.estimhab_tab = estimhab_GUI.EstimhabW(self.path_prj, self.name_prj)

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

            if hasattr(self, "bio_model_explorer_dialog"):
                if not self.bio_model_explorer_dialog:
                    self.bio_model_explorer_dialog = BioModelExplorerWindow(self, self.path_prj, self.name_prj, self.name_icon)
                    self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(self.central_widget.write_log)
                    self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)
                else:
                    self.bio_model_explorer_dialog.__init__(self, self.path_prj, self.name_prj, self.name_icon)
                    self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(self.central_widget.write_log)
                    self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)
            else:
                self.bio_model_explorer_dialog = BioModelExplorerWindow(self, self.path_prj, self.name_prj, self.name_icon)
                self.bio_model_explorer_dialog.bio_model_infoselection_tab.send_log.connect(self.central_widget.write_log)
                self.bio_model_explorer_dialog.send_fill.connect(self.fill_selected_models_listwidets)

            if hasattr(self, "preferences_dialog"):
                if not self.preferences_dialog:
                    self.preferences_dialog = project_properties_GUI.ProjectPropertiesDialog(self.path_prj, self.name_prj, self.name_icon)
                    self.preferences_dialog.send_log.connect(self.central_widget.write_log)
                    self.preferences_dialog.cut_mesh_partialy_dry_signal.connect(self.central_widget.hydro_tab.model_group.set_suffix_no_cut)
                else:
                    self.preferences_dialog.__init__(self.path_prj, self.name_prj, self.name_icon)
                    self.preferences_dialog.send_log.connect(self.central_widget.write_log)
                    self.preferences_dialog.cut_mesh_partialy_dry_signal.connect(self.central_widget.hydro_tab.model_group.set_suffix_no_cut)
            else:
                self.preferences_dialog = project_properties_GUI.ProjectPropertiesDialog(self.path_prj, self.name_prj, self.name_icon)
                self.preferences_dialog.send_log.connect(self.central_widget.write_log)
                self.preferences_dialog.cut_mesh_partialy_dry_signal.connect(self.central_widget.hydro_tab.model_group.set_suffix_no_cut)

            # # run_as_beta_version
            # self.run_as_beta_version()
        else:
            self.central_widget.welcome_tab = welcome_GUI.WelcomeW(self.path_prj, self.name_prj)

    def open_close_physic(self):
        #print("open_close_physic", self.sender())
        phisical_tabs_list = ["hydraulic", "substrate", "calc hab", "data explorer", "tools"]
        if self.physic_tabs:
            if self.name_prj:
                if not self.stat_tabs:
                    self.physicalmodelaction.setChecked(True)
                else:
                    for i in range(self.central_widget.tab_widget.count() - 1, 0, -1):
                        if self.central_widget.tab_widget.widget(i).tab_name in phisical_tabs_list:
                            self.central_widget.tab_widget.removeTab(i)
                    self.physic_tabs = False
        elif not self.physic_tabs:
            if self.name_prj:
                self.central_widget.tab_widget.insertTab(self.central_widget.hydro_tab.tab_position,
                                                         self.central_widget.hydro_tab,
                                                         self.tr("Hydraulic"))  # 1
                self.central_widget.tab_widget.insertTab(self.central_widget.substrate_tab.tab_position,
                                                         self.central_widget.substrate_tab,
                                                         self.tr("Substrate"))  # 2
                self.central_widget.tab_widget.insertTab(self.central_widget.bioinfo_tab.tab_position,
                                                         self.central_widget.bioinfo_tab,
                                                         self.tr("Habitat Calc."))  # 3
                self.central_widget.tab_widget.insertTab(self.central_widget.data_explorer_tab.tab_position,
                                                         self.central_widget.data_explorer_tab,
                                                         self.tr("Data explorer"))  # 4
                self.central_widget.tab_widget.insertTab(self.central_widget.tools_tab.tab_position,
                                                         self.central_widget.tools_tab,
                                                         self.tr("Tools"))  # 5

            self.physic_tabs = True
        # save xml
        if self.name_prj:
            change_specific_properties(self.path_prj,
                                       preference_names=["physic_tabs", "stat_tabs"],
                                       preference_values=[self.physic_tabs, self.stat_tabs])

    def open_close_stat(self):
        #print("open_close_stat", self.sender())
        stat_tabs_list = ["estimhab", "stathab", "fstress"]
        if self.stat_tabs:
            if self.name_prj:
                if not self.physic_tabs:
                    self.statisticmodelaction.setChecked(True)
                else:
                    for i in range(self.central_widget.tab_widget.count() - 1, 0, -1):
                        if self.central_widget.tab_widget.widget(i).tab_name in stat_tabs_list:
                            self.central_widget.tab_widget.removeTab(i)
                    self.stat_tabs = False
        elif not self.stat_tabs:
            if self.name_prj:
                self.central_widget.tab_widget.insertTab(self.central_widget.estimhab_tab.tab_position,
                                                         self.central_widget.estimhab_tab,
                                                         self.tr("ESTIMHAB"))  # 6
                self.central_widget.tab_widget.insertTab(self.central_widget.stathab_tab.tab_position,
                                                         self.central_widget.stathab_tab,
                                                         self.tr("STATHAB"))  # 7
                self.central_widget.tab_widget.insertTab(self.central_widget.fstress_tab.tab_position,
                                                         self.central_widget.fstress_tab,
                                                         self.tr("FStress"))  # 8
            self.stat_tabs = True
        # save xml
        if self.name_prj:
            change_specific_properties(self.path_prj,
                                       preference_names=["physic_tabs", "stat_tabs"],
                                       preference_values=[self.physic_tabs, self.stat_tabs])

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

    def open_web_site(self):
        wbopen("https://habby.wiki.inrae.fr")

    def open_issue_web_site(self):
        """
        This function open the html which form the help from HABBY. For the moment, it is the full documentation
        with all the coding detail, but we should create a new html or a new pdf file which would be more practical
        for the user.
        """
        wbopen("https://github.com/YannIrstea/habby/issues")

    def open_check_version_dialog(self):
        # show the pref
        self.check_version_dialog.show()

    def open_soft_information_dialog(self):
        # show the pref
        self.soft_information_dialog.show()

    def open_user_help(self):
        """
        This function open the html which form the help from HABBY. For the moment, it is the full documentation
        with all the coding detail, but we should create a new html or a new pdf file which would be more practical
        for the user.
        """
        filename_help = os.path.join(os.getcwd(), "doc", "_build", "html", "index.html")
        wbopen(filename_help)

    def open_dev_help(self):
        """
        This function open the html which form the help from HABBY. For the moment, it is the full documentation
        with all the coding detail, but we should create a new html or a new pdf file which would be more practical
        for the user.
        """
        filename_help = os.path.join(os.getcwd(), "doc", "_build", "html", "index.html")
        wbopen(filename_help)

    # DATA

    def remove_hdf5_files(self):
        #print("remove_hdf5_files")
        # get list of files
        hdf5_files_list = self.central_widget.data_explorer_tab.data_explorer_frame.file_to_remove_list

        # loop on files
        for file_to_remove in hdf5_files_list:
            # open hdf5 to read type_mode attribute
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, file_to_remove, new=False, edit=False)
            hdf5.close_file()

            # remove files
            try:
                os.remove(os.path.join(self.path_prj, "hdf5", file_to_remove))
            except PermissionError:
                print("Error: " + self.tr("Warning: Could not remove " + file_to_remove + " file. It might be used by another program."))

            # refresh .habby project
            filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
            if os.path.isfile(filename_path_pro):
                # load
                project_preferences = load_project_properties(self.path_prj)

                # remove
                if file_to_remove in project_preferences[hdf5.input_type]["hdf5"]:
                    project_preferences[hdf5.input_type]["hdf5"].remove(file_to_remove)

                    # save
                    save_project_properties(self.path_prj, project_preferences)

        # empty list
        self.central_widget.data_explorer_tab.data_explorer_frame.file_to_remove_list = []

        # update_combobox_filenames
        self.central_widget.update_combobox_filenames()

        # log
        self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('File(s) deleted. <br>'))

    def rename_hdf5_file(self):
        # get names
        file_to_rename = self.central_widget.data_explorer_tab.data_explorer_frame.file_to_rename
        ext = os.path.splitext(file_to_rename)[1]
        file_renamed = self.central_widget.data_explorer_tab.data_explorer_frame.file_renamed

        # rename file
        os.rename(os.path.join(self.path_prj, "hdf5", file_to_rename),
                  os.path.join(self.path_prj, "hdf5", file_renamed))

        # change attribute
        hdf5 = hdf5_mod.Hdf5Management(self.path_prj, file_renamed, new=False, edit=True)
        hdf5.file_object.attrs[ext[1:] + "_filename"] = file_renamed
        hdf5.close_file()

        # refresh .habby project
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            # load
            project_preferences = load_project_properties(self.path_prj)

            # rename
            if file_to_rename in project_preferences[hdf5.input_type]["hdf5"]:
                file_to_rename_index = project_preferences[hdf5.input_type]["hdf5"].index(file_to_rename)
                project_preferences[hdf5.input_type]["hdf5"][file_to_rename_index] = file_renamed

                # save
                save_project_properties(self.path_prj, project_preferences)

        # reconnect
        self.central_widget.data_explorer_tab.data_explorer_frame.names_hdf5_QListWidget.blockSignals(False)

        # update_combobox_filenames
        self.central_widget.update_combobox_filenames()

        # log
        self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('File renamed. <br>'))

    def remove_all_figure_files(self):
        """
        All files contained in the folder indicated by path_im will be deleted.

        From the menu of HABBY, it is possible to ask to erase all files in the folder indicated by path_im
        (usually figure_HABBY). Of course, this is a bit dangerous. So the function asks the user for confirmation.
        However, it is practical because you do not have to go to the folder to erase all the images when there
        are too many of them.
        """
        # get path im
        path_im = ''
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            path_im = load_specific_properties(self.path_prj, ["path_figure"])[0]
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
        self.central_widget.substrate_tab.input_hyd_combobox.clear()
        self.central_widget.substrate_tab.input_sub_combobox.clear()
        # log
        t = self.central_widget.tracking_journal_QTextEdit.toPlainText()
        self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(self.tr('All figures are deleted.'))

    def see_file(self):
        """
        This function open an explorer with different paths (project folder, habby folder, AppData folder)
        """
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            path_choosen = os.path.normpath(user_preferences.user_pref_habby_user_settings_path)
        elif modifiers == Qt.ShiftModifier:
            path_choosen = os.path.normpath(os.getcwd())
        else:
            path_choosen = os.path.normpath(self.path_prj)

        if operatingsystem() == 'Windows':
            call(['explorer', path_choosen])
        elif operatingsystem() == 'Linux':
            call(["xdg-open", path_choosen], env=self.myEnv)
        elif operatingsystem() == 'Darwin':
            call(['open', path_choosen])

    # LOG

    def clear_log(self):
        """
        Clear the log in the GUI.
        """
        self.central_widget.tracking_journal_QTextEdit.clear()
        # self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
        #     self.tr('Log erased in this window.<br>'))

    def do_log(self, save_log):
        """
        Save or not save the log

        :param save_log: an int which indicates if the log should be saved or not

        *   0: do not save log
        *   1: save the log in the .log file and restart file
        """
        if save_log == 0:
            t = self.central_widget.tracking_journal_QTextEdit.toPlainText()
            self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
                self.tr('This log will not be saved anymore in the .log file. <br>')
                + self.tr('This log will not be saved anymore in the restart file. <br>'))
            self.central_widget.logon = False
        if save_log == 1:
            t = self.central_widget.tracking_journal_QTextEdit.toPlainText()
            self.central_widget.tracking_journal_QTextEdit.textCursor().insertHtml(
                self.tr('This log will be saved in the .log file.<br> '
                        'This log will be saved in the restart file. <br>'))
            self.central_widget.logon = True

        # save the option in the .habby file
        try:
            change_specific_properties(self.path_prj,
                                       preference_names=["save_log"],
                                       preference_values=[self.central_widget.logon])
        except AttributeError:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Log Info"))
            self.msg2.setText( \
                self.tr("Information related to the .log file are incomplete. Please check."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()


class CreateNewProjectDialog(QDialog):
    """
    A class which is used to help the user to create a new project
    """
    create_project = pyqtSignal()
    """
    a signal to save the project
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal used to write the log
    """

    def __init__(self, lang, physic_tabs, stat_tabs, oldpath_prj):
        super().__init__()
        user_path = os.path.expanduser("~")
        user_document_path = os.path.join(user_path, "Documents")
        if os.path.exists(user_document_path):
            self.default_fold = os.path.join(user_document_path, "HABBY_projects")

        else:
            self.default_fold = os.path.join(user_path, "HABBY_projects")

        if not os.path.exists(self.default_fold):
            os.makedirs(self.default_fold)

        if oldpath_prj and os.path.isdir(oldpath_prj) and os.path.dirname(oldpath_prj) != "":
            self.default_fold = os.path.dirname(oldpath_prj)

        self.default_name = 'DefaultProj'
        self.physic_tabs = physic_tabs
        self.stat_tabs = stat_tabs

        self.init_iu()

    def init_iu(self):
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)
        l1 = QLabel(self.tr('Project name: '))
        self.e1 = QLineEdit(self.default_name)
        l2 = QLabel(self.tr('Projects folder: '))
        self.e2 = QLineEdit(self.default_fold)
        button2 = QPushButton("...", self)
        button2.setToolTip(self.tr("Change folder"))
        button2.clicked.connect(self.setfolder)
        self.button3 = QPushButton(self.tr('Create project'))
        self.button3.clicked.connect(self.create_project)  # is a PyQtSignal
        self.e1.returnPressed.connect(self.create_project)
        self.button3.setStyleSheet("background-color: #47B5E6; color: black")
        project_type_title_label = QLabel(self.tr("Project type"))
        self.project_type_combobox = QComboBox()
        self.model_type_list = [self.tr("physical"), self.tr("statistical"), self.tr("both")]
        self.project_type_combobox.addItems(self.model_type_list)
        if self.physic_tabs and not self.stat_tabs:
            self.project_type_combobox.setCurrentIndex(0)
        elif self.stat_tabs and not self.physic_tabs:
            self.project_type_combobox.setCurrentIndex(1)
        elif self.physic_tabs and self.stat_tabs:
            self.project_type_combobox.setCurrentIndex(2)

        layoutl = QGridLayout()
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
        self.setMinimumWidth(650)
        self.setMinimumHeight(100)
        self.button3.setFocus()
        self.setModal(True)

    def setfolder(self):
        """
        This function is used by the user to select the folder where the xml project file will be located.
        """
        dir_name = QFileDialog.getExistingDirectory(self, self.tr("Select directory"), self.default_fold,
                                                    )  # check for invalid null parameter on Linux git
        dir_name = os.path.normpath(dir_name)
        # os.getenv('HOME')
        if dir_name not in ['', '.']:  # cancel case
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
    are based on more complicated classes created for example in sub_and_merge_GUI.py.

    Then, we create an area under it for the log. Here HABBY will write various infos for the user. Two things to note
    here: a) we should show the end of the scroll area. b) The size of the area should be controlled and not be
    changing even if a lot of text appears. Hence, the setSizePolicy should be fixed.

    The write_log() and write_log_file() method are explained in the section about the log.
    """

    def __init__(self, path_prj, name_prj, lang_bio):

        super().__init__()
        self.msg2 = QMessageBox()
        self.tab_widget = QTabWidget(self)
        self.name_prj = name_prj
        self.path_prj = path_prj

        self.welcome_tab = welcome_GUI.WelcomeW(path_prj, name_prj)
        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.hydro_tab = hydrau_GUI.HydrauTab(path_prj, name_prj)
            self.substrate_tab = sub_and_merge_GUI.SubstrateTab(path_prj, name_prj)
            self.bioinfo_tab = calc_hab_GUI.BioInfo(path_prj, name_prj, lang_bio)
            self.data_explorer_tab = data_explorer_GUI.DataExplorerTab(path_prj, name_prj)
            self.tools_tab = tools_GUI.ToolsTab(path_prj, name_prj)
            self.estimhab_tab = estimhab_GUI.EstimhabW(path_prj, name_prj)
            self.stathab_tab = stathab_GUI.StathabW(path_prj, name_prj)
            self.fstress_tab = fstress_GUI.FstressW(path_prj, name_prj)

        self.logon = True  # do we save the log in .log file or not
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
        self.update_combobox_filenames()

        # add the widgets to the list of tab if a project exists
        self.add_all_tab()

        # QTextEdit
        self.tracking_journal_QTextEdit = QTextEdit(self)  # where the log is show
        self.tracking_journal_QTextEdit.setReadOnly(True)
        self.tracking_journal_QTextEdit.textChanged.connect(self.scrolldown_log)
        self.tracking_journal_QTextEdit.setFrameShape(QFrame.NoFrame)
        self.tracking_journal_QTextEdit.setTextBackgroundColor(QColor("#A6C313"))

        # Area to show the log
        self.tracking_journal_qgroupbox = QGroupBox(self.tr("HABBY says :"))
        self.tracking_journal_qgroupbox.setFixedHeight(140)
        tracking_journal_layout = QVBoxLayout()
        tracking_journal_layout.setContentsMargins(4, 6, 4, 4)  # int left, int top, int right, int bottom
        tracking_journal_layout.addWidget(self.tracking_journal_QTextEdit)
        self.tracking_journal_qgroupbox.setLayout(tracking_journal_layout)

        # save the description and the figure option if tab changed
        self.welcome_tab.save_info_signal.connect(self.save_info_projet)
        self.tab_widget.currentChanged.connect(self.save_on_change_tab)

        # update plot item in plot tab
        # self.tab_widget.currentChanged.connect(self.update_specific_tab)

        # layout
        self.layoutc = QVBoxLayout()
        self.layoutc.addWidget(self.tab_widget)
        self.layoutc.addWidget(self.tracking_journal_qgroupbox)
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
        This function add the different tab to habby (used by init and by create_project). Careful, if you change the
        position of the Option tab, you should also modify the variable self.opttab in init
        """
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        #print("add_all_tab", self.path_prj)
        # load project pref
        if os.path.isfile(fname) and self.name_prj != '':
            project_preferences = load_project_properties(self.path_prj)
            go_physic = project_preferences["physic_tabs"]
            go_stat = project_preferences["stat_tabs"]
            go_research = False

            # add all tabs
            self.tab_widget.addTab(self.welcome_tab, self.tr("Project"))  # 0
            if go_physic:
                self.tab_widget.addTab(self.hydro_tab, self.tr("Hydraulic"))  # 1
                self.tab_widget.addTab(self.substrate_tab, self.tr("Substrate"))  # 2
                self.tab_widget.addTab(self.bioinfo_tab, self.tr("Habitat Calc."))  # 3
                self.tab_widget.addTab(self.data_explorer_tab, self.tr("Data explorer"))  # 4
                self.tab_widget.addTab(self.tools_tab, self.tr("Tools"))  # 5
            if go_stat:
                self.tab_widget.addTab(self.estimhab_tab, self.tr("ESTIMHAB"))  # 7
                self.tab_widget.addTab(self.stathab_tab, self.tr("STATHAB"))  # 8
                self.tab_widget.addTab(self.fstress_tab, self.tr("FStress"))  # 9
            if go_research:
                self.tab_widget.addTab(self.other_tab, self.tr("Research 1"))  # 10
                self.tab_widget.addTab(self.other_tab2, self.tr("Research 2"))  # 11
            self.welcome_tab.current_prj_groupbox.setEnabled(True)
        # if the project do not exist, do not add new tab
        else:
            self.tab_widget.addTab(self.welcome_tab, self.tr("Project"))
            self.welcome_tab.current_prj_groupbox.setEnabled(False)

        #self.tab_widget.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")

    def get_process_alive_list(self):
        process_alive_list = []
        for process_prog_layout in self.findChildren(ProcessProgLayout):
            if process_prog_layout.process_prog_show.process_manager is not None:
                if process_prog_layout.process_prog_show.process_manager.isRunning():
                    process_alive_list.append(process_prog_layout.process_prog_show.process_manager.process_type_gui)
        return process_alive_list

    def kill_process_plot_list(self):
        """
        method to close the images opened in HABBY and managed by matplotlib
        """
        # for process_prog_layout in self.findChildren(ProcessProgLayout):
        #     if process_prog_layout.process_prog_show.process_manager is not None:
        #         if "plot" in process_prog_layout.process_prog_show.process_manager.process_type:
        #             process_prog_layout.stop_by_user()

        # bio_model_explorer_dialog
        if hasattr(self.parent(), "bio_model_explorer_dialog"):
            if hasattr(self.parent().bio_model_explorer_dialog, "bio_model_infoselection_tab"):
                if hasattr(self.parent().bio_model_explorer_dialog.bio_model_infoselection_tab, "process_manager_sc_plot"):
                    self.parent().bio_model_explorer_dialog.bio_model_infoselection_tab.process_manager_sc_plot.stop_by_user()
                if hasattr(self.parent().bio_model_explorer_dialog.bio_model_infoselection_tab,"process_manager_sc_hs_plot"):
                    self.parent().bio_model_explorer_dialog.bio_model_infoselection_tab.process_manager_sc_hs_plot.stop_by_user()

        # data_explorer_tab
        if hasattr(self, 'data_explorer_tab'):
            if hasattr(self.data_explorer_tab.data_explorer_frame, 'plot_group'):
                if hasattr(self.data_explorer_tab.data_explorer_frame.plot_group, 'progress_layout'):
                    self.data_explorer_tab.data_explorer_frame.plot_group.progress_layout.process_manager.stop_by_user()
        # tools_tab
        if hasattr(self, 'tools_tab'):
            # interpolation_tab
            if hasattr(self.tools_tab, 'interpolation_tab'):
                if hasattr(self.tools_tab.interpolation_tab, 'process_manager'):
                    self.tools_tab.interpolation_tab.process_manager.stop_by_user()
            # hs_tab
            if hasattr(self.tools_tab, 'hs_tab'):
                if hasattr(self.tools_tab.hs_tab, 'computing_group'):
                    if hasattr(self.tools_tab.hs_tab.computing_group, 'process_manager'):
                        self.tools_tab.hs_tab.computing_group.process_manager.stop_by_user()
                if hasattr(self.tools_tab.hs_tab, 'visual_group'):
                    if hasattr(self.tools_tab.hs_tab.visual_group, 'process_manager'):
                        self.tools_tab.hs_tab.visual_group.process_manager.stop_by_user()
        # estimhab
        if hasattr(self, 'estimhab_tab'):
            if hasattr(self.estimhab_tab, 'process_manager'):
                self.estimhab_tab.process_manager.stop_by_user()

    def kill_process_list(self):
        """
        method to kill all process
        """
        # bio_model_explorer_dialog
        if hasattr(self.parent(), "bio_model_explorer_dialog"):
            if hasattr(self.parent().bio_model_explorer_dialog, "bio_model_infoselection_tab"):
                if hasattr(self.parent().bio_model_explorer_dialog.bio_model_infoselection_tab, "process_manager"):
                    self.parent().bio_model_explorer_dialog.bio_model_infoselection_tab.process_manager.close_all_plot()
        # data_explorer_tab
        if hasattr(self, 'data_explorer_tab'):
            if hasattr(self.data_explorer_tab.data_explorer_frame, 'plot_group'):
                if hasattr(self.data_explorer_tab.data_explorer_frame.plot_group, 'progress_layout'):
                    self.data_explorer_tab.data_explorer_frame.plot_group.progress_layout.process_manager.stop_by_user()
            if hasattr(self.data_explorer_tab.data_explorer_frame, 'dataexporter_group'):
                if hasattr(self.data_explorer_tab.data_explorer_frame.dataexporter_group, 'progress_layout'):
                    self.data_explorer_tab.data_explorer_frame.dataexporter_group.progress_layout.process_manager.stop_by_user()
        # tools_tab
        if hasattr(self, 'tools_tab'):
            # interpolation_tab
            if hasattr(self.tools_tab, 'interpolation_tab'):
                if hasattr(self.tools_tab.interpolation_tab, 'process_manager'):
                    self.tools_tab.interpolation_tab.process_manager.stop_by_user()
            # hs_tab
            if hasattr(self.tools_tab, 'hs_tab'):
                if hasattr(self.tools_tab.hs_tab, 'computing_group'):
                    if hasattr(self.tools_tab.hs_tab.computing_group, 'process_manager'):
                        self.tools_tab.hs_tab.computing_group.process_manager.close_all_hs()
                if hasattr(self.tools_tab.hs_tab, 'visual_group'):
                    if hasattr(self.tools_tab.hs_tab.visual_group, 'process_manager'):
                        self.tools_tab.hs_tab.visual_group.process_manager.stop_by_user()
        # estimhab
        if hasattr(self, 'estimhab_tab'):
            if hasattr(self.estimhab_tab, 'process_manager'):
                self.estimhab_tab.process_manager.stop_by_user()

    def connect_signal_log(self):
        """
        connect all the signal linked to the log. This is in a function only to improve readability.
        """

        self.welcome_tab.send_log.connect(self.write_log)

        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            self.hydro_tab.send_log.connect(self.write_log)
            self.substrate_tab.send_log.connect(self.write_log)
            self.estimhab_tab.send_log.connect(self.write_log)
            self.stathab_tab.send_log.connect(self.write_log)
            self.bioinfo_tab.send_log.connect(self.write_log)
            self.fstress_tab.send_log.connect(self.write_log)
            self.data_explorer_tab.send_log.connect(self.write_log)
            self.tools_tab.send_log.connect(self.write_log)

    def connect_signal_fig_and_drop(self):
        """
        This function connect the PyQtsignal to show figure and to connect the log. It is a function to
        improve readability.
        """

        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            # connect signals to update the drop-down menu in the substrate tab when a new hydro hdf5 is created
            self.hydro_tab.model_group.drop_hydro.connect(self.update_combobox_filenames)
            self.tools_tab.hs_tab.computing_group.send_refresh_filenames.connect(self.update_combobox_filenames)
            self.hydro_tab.model_group.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.substrate_tab.sub_and_merge.drop_hydro.connect(self.update_combobox_filenames)
            self.substrate_tab.sub_and_merge.drop_merge.connect(self.bioinfo_tab.update_merge_list)
            self.bioinfo_tab.allmodels_presence.connect(self.update_combobox_filenames)
            self.bioinfo_tab.get_list_merge.connect(self.tools_tab.refresh_gui)

    def write_log(self, text_log):
        """
        A function to write the different log. Please read the section of the doc on the log.

        :param text_log: the text which should be added to the log (a string)

        *   if text_log start with # -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file (comments)
        *   if text_log start with restart -> added it restart_nameproject.txt
        *   if text_log start with WARNING -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file
        *   if text_log start with ERROR -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file
        *   if text_log start with py -> added to the .log file (python command)
        *   if text_log start with cmd -> added to the .log file (script command)
        *   if text_log starts with Process -> Text added to the StatusBar only
        *   if text_log == "clear status bar" -> the status bar is cleared
        *   if text_log start with nothing -> just print to the QTextEdit
        *   if text_log out from stdout -> added it to self.tracking_journal_QTextEdit (QTextEdit) and the .log file (comments)

        if logon = false, do not write in log.txt
        """
        file_script = None
        pathname_restartfile = None
        pathname_logfile = None

        # read xml file to find the path to the log file
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(fname):
            # file_log
            logfile = load_specific_properties(self.path_prj, ["file_log"])[0]
            if logfile:
                pathname_logfile = logfile
            else:
                self.tracking_journal_QTextEdit.textCursor().insertHtml("<FONT COLOR='#FF8C00'> WARNING: The "
                                                                        "log file is not indicated in the .habby file. No log written. </br> <br>")
                return
            # file_script
            file_script = load_specific_properties(self.path_prj, ["file_script"])[0]
            if not file_script:
                self.tracking_journal_QTextEdit.textCursor().insertHtml("<FONT COLOR='#FF8C00'> WARNING: The "
                                                                        "script file is not indicated in the .habby file. No log written. </br> <br>")
                return
            # restart log
            restart = load_specific_properties(self.path_prj, ["file_restart"])[0]
            if restart:
                pathname_restartfile = restart
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
        # add script code to the .log file
        elif text_log[:6] == 'script':
            self.write_script_file(text_log[6:], file_script)
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
            self.parent().progress_bar.setVisible(False)  # hide progress_bar
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
            if pathname_logfile:
                if os.path.isfile(pathname_logfile):
                    with open(pathname_logfile, "a", encoding='utf8') as myfile:
                        myfile.write('\n' + text_log)
                elif self.name_prj == '':
                    return
                else:
                    self.tracking_journal_QTextEdit.textCursor().insertHtml(
                        "<FONT COLOR='#FF8C00'> WARNING: Log file not found. New log created. </br> <br>")
                    shutil.copy(os.path.join('files_dep', 'log0.txt'),
                                os.path.join(self.path_prj, self.name_prj + '.log'))
                    shutil.copy(os.path.join('files_dep', 'restart_log0.txt'),
                                os.path.join(self.path_prj, 'restart_' + self.name_prj + '.log'))
                    with open(pathname_logfile, "a", encoding='utf8') as myfile:
                        myfile.write("    name_project = " + self.name_prj + "\n")
                    with open(pathname_logfile, "a", encoding='utf8') as myfile:
                        myfile.write("    path_project = " + self.path_prj + "\n")
                    with open(pathname_logfile, "a", encoding='utf8') as myfile:
                        myfile.write('\n' + text_log)

        return

    def write_script_file(self, text_log, pathname_scriptfile):
        """
        A function to write to the .log text. Called by write_log.

        :param text_log: the text to be written (string)
        :param pathname_scriptfile: the path+name where the log is
        """
        if self.logon:
            if os.path.isfile(pathname_scriptfile):
                with open(pathname_scriptfile, "a", encoding='utf8') as myfile:
                    myfile.write('\n' + text_log)
            elif self.name_prj == '':
                return
            else:
                self.tracking_journal_QTextEdit.textCursor().insertHtml(
                    "<FONT COLOR='#FF8C00'> WARNING: Script file not found. New script created. </br> <br>")
                with open(pathname_scriptfile, "a", encoding='utf8') as myfile:
                    myfile.write('\n' + text_log)

    def update_combobox_filenames(self):
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

        if os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            # substrate sub combobox
            self.substrate_tab.sub_and_merge.update_sub_hdf5_name()

            # calc hab combobox
            self.bioinfo_tab.update_merge_list()

            self.data_explorer_tab.refresh_type()

            self.tools_tab.refresh_gui()

    def save_info_projet(self):
        """
        This function is used to save the description of the project and the username in the xml project file
        """

        # username and description
        e4here = self.welcome_tab.user_name_lineedit
        self.username_prj = e4here.text()
        e3here = self.welcome_tab.description_prj_textedit
        self.descri_prj = e3here.toPlainText()

        fname = os.path.join(self.path_prj, self.name_prj + '.habby')

        if not os.path.isfile(fname):
            self.write_log('Error: ' + self.tr('The project file is not found. \n'))
        else:
            change_specific_properties(self.path_prj,
                                       preference_names=["user_name", "description"],
                                       preference_values=[self.username_prj, self.descri_prj])

    def save_on_change_tab(self):
        """
        This function is used to save the data when the tab are changed. In most tab this is not needed as data
        is already saved by another functions. However, it is useful for the Welcome Tab and the Option Tab.
        This function can be modified if needed for new tabs.

        Careful, the order of the tab is important here.
        """

        if self.old_ind_tab == 0 and os.path.exists(self.path_prj):
            self.save_info_projet()
        # elif self.old_ind_tab == self.opttab:
        #     self.output_tab.save_preferences()
        self.old_ind_tab = self.tab_widget.currentIndex()

    def update_specific_tab(self):
        # hyd
        if hasattr(self, "hydro_tab"):
            if self.tab_widget.currentIndex() == self.hydro_tab.tab_position:
                self.hydro_tab.model_list_combobox.setFocus()
        # hyd
        if hasattr(self, "substrate_tab"):
            if self.tab_widget.currentIndex() == self.substrate_tab.tab_position:
                self.substrate_tab.sub_and_merge.update_sub_hdf5_name()
        # calc hab
        if hasattr(self, "bioinfo_tab"):
            if self.tab_widget.currentIndex() == self.bioinfo_tab.tab_position:
                self.bioinfo_tab.update_merge_list()
        # data_explorer_tab
        if hasattr(self, "data_explorer_tab"):
            if self.tab_widget.currentIndex() == self.data_explorer_tab.tab_position:
                self.data_explorer_tab.refresh_type()
        # tools_tab
        if hasattr(self, "tools_tab"):
            if self.tab_widget.currentIndex() == self.tools_tab.tab_position:
                self.tools_tab.refresh_gui()


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
        button1 = QPushButton(self.tr('I am a button'), self)
        button1.clicked.connect(self.addtext)

        button2 = QPushButton(self.tr('I am a button'), self)
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


if __name__ == '__main__':
    pass
