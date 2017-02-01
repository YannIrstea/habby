import sys
import glob
import os
import shutil
import numpy as np
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from PyQt5.QtCore import QTranslator, pyqtSignal, QSettings, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,\
    QListWidgetItem, QAbstractItemView, QMessageBox, QComboBox, QScrollArea, QSizePolicy, QInputDialog
from PyQt5.QtGui import QPixmap, QFont
import h5py
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
#from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from src_GUI import estimhab_GUI
from src_GUI import hydro_GUI_2
from src_GUI import stathab_GUI
from src_GUI import output_fig_GUI
from src_GUI import bio_info_GUI


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
        # load user setting
        self.settings = QSettings('HABBY', 'irstea')
        name_prj_set = self.settings.value('name_prj')
        print(name_prj_set)
        name_path_set = self.settings.value('path_prj')
        print(name_path_set)
        language_set = self.settings.value('language_code')
        # recent project: list of string
        recent_projects_set = self.settings.value('recent_project_name')
        recent_projects_path_set = self.settings.value('recent_project_path')
        del self.settings

        # set up tranlsation
        self.languageTranslator = QTranslator()
        self.path_trans = r'.\translation'
        self.file_langue = [r'Zen_EN.qm', r'Zen_FR.qm']
        if language_set:
            self.lang = int(language_set)  # need to be sure to have an integer there
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
            self.recent_project = recent_projects_set
        else:
            self.recent_project = []
        if recent_projects_path_set:
            self.recent_project_path = recent_projects_path_set
        else:
            self.recent_project_path = []
        self.username_prj = "NoUserName"
        self.descri_prj = ""
        self.does_it_work = True
        # the maximum number of recent project shown in the menu. if changement here modify self.my_menu_bar
        self.nb_recent = 5

        # create the central widget
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)
        self.msg2 = QMessageBox()

        # call the normal constructor of QWidget
        super().__init__()
        # call an additional function during initialisation
        self.init_ui()

    def init_ui(self):
        """ Used by __init__() to create an instance of the class MainWindows """

        # create the menu bar
        self.my_menu_bar()

        # connect the signals of the welcome tab with the different functions (careful if changes this copy 3 times
        # in set_langue and save_proje
        self.central_widget.welcome_tab.save_signal.connect(self.save_project)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        # set geometry
        self.setGeometry(200, 200, 800, 600)
        self.setCentralWidget(self.central_widget)
        self.show()

    def closeEvent(self, event):
        """
        Close the program better than before (where it used to crash about 1 times in ten). It is not really clear why.

        :param event: managed by the operating system.
        """
        sys.exit()

    def setlangue(self, nb_lang):
        """
        A function which change the language of the programme. It change the menu and the central widget.
        It uses the self.lang attribute which should be set to the new language before calling this function.

        :param nb_lang: the number representing the language (int)

        *   0 is for English
        *   1 for French
        *   n for any additionnal language

        """

        # set the langugae
        self.lang = int(nb_lang)
        # get a new tranlator
        app = QApplication.instance()
        app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[int(self.lang)], self.path_trans)
        app.installTranslator(self.languageTranslator)

        # set the central widget
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)  # False is not research mode
        self.setCentralWidget(self.central_widget)

        # connect the signals with the different functions
        self.central_widget.welcome_tab.save_signal.connect(self.save_project)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        # create the new menu
        self.my_menu_bar()

        # update user option to remember the languge
        self.settings = QSettings('HABBY', 'irstea')
        self.settings.setValue('language_code', self.lang)
        del self.settings

    def my_menu_bar(self):
        """
        This function creates the menu bar of HABBY.
        """

        self.menubar = self.menuBar()
        self.menubar.clear()

        # Menu to open and close file
        exitAction = QAction(self.tr('Exit'), self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip(self.tr('Exit application'))
        exitAction.triggered.connect(qApp.quit)
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
        saveprj = QAction(self.tr('Save Project'), self)
        saveprj.setShortcut('Ctrl+S')
        saveprj.setStatusTip(self.tr('Save the project'))
        saveprj.triggered.connect(self.save_project)

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
        savi = QAction(self.tr("Clear Images and h5 Files"), self)
        savi.setStatusTip(self.tr('Figures saved by HABBY will be deleted'))
        savi.triggered.connect(self.erase_pict)
        showim = QAction(self.tr("Show Images"), self)
        showim.setStatusTip(self.tr('Open the window to view the created figures.'))
        showim.triggered.connect(self.central_widget.showfig2)
        optim = QAction(self.tr("More Options"), self)
        optim.setStatusTip(self.tr('Various options to modify the figures produced by HABBY.'))
        # optim.triggered.connect(self.central_widget.optfig)

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

        # Menu to obtain help and programme version
        helpm = QAction(self.tr('Help'), self)
        helpm.setStatusTip(self.tr('Get help to use the programme'))

        # add all menu together
        self.menubar = self.menuBar()
        fileMenu = self.menubar.addMenu(self.tr('&File'))
        fileMenu.addAction(saveprj)
        fileMenu.addAction(openprj)
        recentpMenu = fileMenu.addMenu(self.tr('Recent Project'))
        for j in range(0, len(recent_proj_menu)):
            recentpMenu.addAction(recent_proj_menu[j])
        fileMenu.addAction(newprj)
        fileMenu.addAction(exitAction)
        fileMenu4 = self.menubar.addMenu(self.tr('Options'))
        log_all = fileMenu4.addMenu(self.tr('Log'))
        log_all.addAction(logc)
        log_all.addAction(logn)
        log_all.addAction(logy)
        im_all = fileMenu4.addMenu(self.tr('Image options'))
        im_all.addAction(showim)
        im_all.addAction(savi)
        im_all.addAction(optim)
        re_all = fileMenu4.addMenu(self.tr('Research options'))
        re_all.addAction(rech)
        re_all.addAction(rechc)
        fileMenu2 = self.menubar.addMenu(self.tr('Language'))
        fileMenu2.addAction(lAction1)
        fileMenu2.addAction(lAction2)
        fileMenu3 = self.menubar.addMenu(self.tr('Help'))
        fileMenu3.addAction(helpm)

        # add the status bar
        self.statusBar()

        # add the title of the windows
        # let it here as it should be changes if language changes
        self.setWindowTitle(self.tr('HABBY: ') + self.name_prj)

        # in case we need a tool bar
        # self.toolbar = self.addToolBar('')

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
        is saved. If path_im is not given, HABBY automatically create a folder called figure_habby when the
        user creates a new project. The user can however change this path if he wants. The next step is to communicate
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
        self.settings = QSettings('HABBY', 'irstea')
        self.settings.setValue('name_prj', self.name_prj)
        self.settings.setValue('path_prj', self.path_prj)

        # save name and path of project
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

        # if new projet
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
            pathlog_child.text = os.path.join(self.path_prj, self.name_prj + '.log')
            pathlog_child = ET.SubElement(log_element, "File_Restart")
            pathlog_child.text = os.path.join(self.path_prj, 'restart_'+self.name_prj + '.log')
            savelog_child = ET.SubElement(log_element, "Save_Log")
            savelog_child.text = str(self.central_widget.logon)

            # create the log files by copying the existing "basic" log files (log0.txt and restart_log0.txt)
            if self.name_prj != '':
                shutil.copy(os.path.join('src_GUI', 'log0.txt'), os.path.join(self.path_prj, self.name_prj + '.log'))
                shutil.copy(os.path.join('src_GUI', 'restart_log0.txt'), os.path.join(self.path_prj,
                                                                                  'restart_' + self.name_prj + '.log'))
            # more precise info
            user_child = ET.SubElement(general_element, "User_Name")
            user_child.text = self.username_prj
            des_child = ET.SubElement(general_element, "Description")
            des_child.text = self.descri_prj
            pathbio_child = ET.SubElement(root_element, "Path_Bio")
            pathbio_child.text = "./biology\\"

            # save new xml file
            if self.name_prj != '':
                fname = os.path.join(self.path_prj, self.name_prj+'.xml')
                tree.write(fname)
            # create a default directory for the figures
            path_im = os.path.join(self.path_prj, 'figures_habby')
            if not os.path.exists(path_im):
                os.makedirs(path_im)
        # project exist
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            child = root.find(".//Project_Name")
            path_child = root.find(".//Path_Projet")
            user_child = root.find(".//User_Name")
            des_child = root.find(".//Description")
            pathim_child = root.find(".//Path_Figure")
            pathbio_child = root.find(".//Path_Bio")
            #  if pathim is the default one, change it. Otherwise keep the user chosen directory
            if pathim_child is not None:
                if os.path.samefile(pathim_child.text, os.path.join(path_prj_before, 'figures_habby')):
                    pathim_child.text = os.path.join(self.path_prj, 'figures_habby')
            child.text = self.name_prj
            path_child.text = self.path_prj
            pathbio_child.text = "./biology"
            user_child.text = self.username_prj
            des_child.text = self.descri_prj
            fname = os.path.join(self.path_prj, self.name_prj+'.xml')
            doc.write(fname)
            # create a default directory for the figures
            path_im = os.path.join(self.path_prj, 'figures_habby')
            if not os.path.exists(path_im):
                os.makedirs(path_im)

        # send the new name to all widget and re-connect signal
        t = self.central_widget.l2.text()
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)  # False is not research mode
        self.setCentralWidget(self.central_widget)
        self.central_widget.welcome_tab.save_signal.connect(self.save_project)
        self.central_widget.welcome_tab.open_proj.connect(self.open_project)
        self.central_widget.welcome_tab.new_proj_signal.connect(self.new_project)
        self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)
        # write log
        if len(t) > 26:
            # no need to write #log of habby started two times
            # to breack line habby use <br> there, should not be added again
            self.central_widget.write_log(t[26:-4])
        self.central_widget.write_log('# Project saved sucessfully.')
        self.central_widget.write_log("py    name_prj= '" + self.name_prj + "'")
        self.central_widget.write_log("py    path_prj= '" + self.path_prj + "'")
        self.central_widget.write_log("restart Name_project")
        self.central_widget.write_log("restart    name_prj= " + self.name_prj)

        # enabled lowest part
        self.central_widget.welcome_tab.lowpart.setEnabled(True)

        # update name project
        self.setWindowTitle(self.tr('HABBY: ') + self.name_prj)


        return

    def open_project(self):
        """
        This function is used to open an existing habby project by selecting an xml project file. Called by
        my_menu_bar()
        """

        # open an xml file
        filename_path = QFileDialog.getOpenFileName(self, 'Open File', self.path_prj)[0]
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
                docxml = ET.parse(filename_path)
                root = docxml.getroot()
            except IOError:
                self.central_widget.write_log("Error: the selected xml file does not exist\n")
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
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText(self.username_prj)
        self.central_widget.welcome_tab.e3.setText(self.descri_prj)
        self.central_widget.write_log('# Project opened sucessfully. \n')

        # save the project
        self.save_project()

    def open_recent_project(self, j):
        """
        This function open a recent project of the user. The recent project are listed in the menu and can be
        selected by the user. When the user select a recent project to open, this function is called. Then, the name of
        the recent project is selected and the method save_project() is called.

        :param j: This indicates which project should be open, based on the order given in the menu
        """

        # get the project file
        filename_path = os.path.join(self.recent_project_path[j], self.recent_project[j] +'.xml')

        # load the xml file
        try:
            try:
                docxml = ET.parse(filename_path)
                root = docxml.getroot()
            except IOError:
                self.central_widget.write_log("Error: the selected xml file does not exist\n")
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
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText(self.username_prj)
        self.central_widget.welcome_tab.e3.setText(self.descri_prj)
        self.central_widget.write_log('# Project opened sucessfully. \n')

        # save the project
        self.save_project()


    def new_project(self):
        """
        This function open an empty project and guide the user to create a new project, using a new Windows
        of the class CreateNewProject
        """
        # create an empty project
        self.empty_project()

        # open a new Windows to ask for the info for the project
        self.createnew = CreateNewProject(self.lang, self.path_trans, self.file_langue)
        self.createnew.show()
        self.createnew.save_project.connect(self.save_project_if_new_project)
        self.createnew.send_log.connect(self.central_widget.write_log)

    def save_project_if_new_project(self):
        """
        This function is used to save a project when the project is created from the other Windows CreateNewProject
        """

        # pass the info from the extra Windows to the HABBY MainWindows (check on user input done by save_project)
        name_prj_here = self.createnew.e1.text()
        self.central_widget.welcome_tab.e1.setText(name_prj_here)
        self.central_widget.welcome_tab.e2.setText(self.createnew.e2.text())

        # check if there is not another project with the same path_name
        fname = os.path.join(self.createnew.e2.text(), name_prj_here+'.xml')
        if os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Erase old project?"))
            self.msg2.setText(
                self.tr("A project with an identical name exists. Should this project be erased definitively? "))
            self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.msg2.setDefaultButton(QMessageBox.No)
            ret = self.msg2.exec_()
            if ret == QMessageBox.Yes:
                os.remove(fname)
                os.remove(os.path.join(self.createnew.e2.text(), name_prj_here+'.log'))
                os.remove(os.path.join(self.createnew.e2.text(), 'restart_'+name_prj_here+'.log'))
                self.save_project()
                self.createnew.close()
            else:
                return
        # save project if unique name in the selected folder
        else:
            self.save_project()
            self.createnew.close()

    def empty_project(self):
        """
        This function open a new empty project
        """

        # load the xml file
        filename_empty = r'src_GUI/empty_proj.xml'
        with open(filename_empty, 'rt') as f:
            data_geo = f.read()

        try:
            try:
                docxml = ET.parse(filename_empty)
                root = docxml.getroot()
            except IOError:
                self.central_widget.write_log("Error: no empty project. \n")
                return
        except ET.ParseError:
            self.central_widget.write_log('Error: the XML is not well-formed.\n')
            return

        # get the project name and path. Write it in the QWiddet.
        # the text in the Qwidget will be used to save the project
        self.name_prj = root.find(".//Project_Name").text
        self.path_prj = root.find(".//Path_Projet").text
        self.central_widget.welcome_tab.e1.setText(self.name_prj)
        self.central_widget.welcome_tab.e2.setText(self.path_prj)
        self.central_widget.welcome_tab.e4.setText('')
        self.central_widget.welcome_tab.e3.setText('')
        self.central_widget.write_log('# Empty project was opened. \n')

        # save the project
        self.save_project()

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
        fname = os.path.join(self.path_prj, fname_no_path)
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
        fish_typeg = file.create_group('fish_type')
        fish_type_all = fish_typeg.create_dataset(fname_no_path, (len(fish_list), 1), data=ascii_str)
        file.close()

        # add the name of this h5 file to the xml file of the project
        fnamep = os.path.join(self.path_prj, self.name_prj+'.xml')
        if not os.path.isfile(fnamep):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save project"))
            self.msg2.setText(self.tr("The project is not saved. Save the project in the General tab before saving ESTIMHAB data"))
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
        will be added to these options, but the basic architecture is there when it will be needed.
        """
        self.rechmain = True
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)  # 0 is not research mode
        self.setCentralWidget(self.central_widget)

    def close_rech(self):
        """
            Close the additional research menu (see open_rech for more information)
        """
        self.rechmain = False
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)  # 0 is not research mode
        self.setCentralWidget(self.central_widget)

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
                                                       'This log will be saved anymore in the restart file. <br>'))
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
                path_im = os.path.join(self.path_prj, 'figures_habby')
            else:
                path_im = child.text
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

    def __init__(self, lang, path_trans, file_langue):

        self.default_fold = r'C:\Users\diane.von-gunten\HABBY'
        self.default_name = 'DefaultProj'
        super().__init__()
        #translation
        self.languageTranslator = QTranslator()
        app = QApplication.instance()
        app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(file_langue[int(lang)], path_trans)
        app.installTranslator(self.languageTranslator)

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
        self.button3.clicked.connect(self.save_project)

        layoutl = QGridLayout()
        layoutl.addWidget(lg, 0, 0)
        layoutl.addWidget(l1, 1, 0)
        layoutl.addWidget(self.e1, 1, 1)
        layoutl.addWidget(l2, 2, 0)
        layoutl.addWidget(self.e2, 2, 1)
        layoutl.addWidget(button2, 2, 2)
        layoutl.addWidget(self.button3, 3, 1)
        self.setLayout(layoutl)

        self.setWindowTitle(self.tr('HABBY- NEW PROJECT'))

    def setfolder(self):
        """
        This function is used by the user to select the folder where the xml project file will be located.
        """
        dir_name = QFileDialog.getExistingDirectory(None)  # check for invalid null parameter on Linuxgit
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

    def __init__(self, rech, path_prj, name_prj):

        super().__init__()
        self.msg2 = QMessageBox()
        self.tab_widget = QTabWidget()
        self.welcome_tab = WelcomeW()
        self.statmod_tab = estimhab_GUI.EstimhabW(path_prj, name_prj)
        self.hydro_tab = hydro_GUI_2.Hydro2W(path_prj, name_prj)
        self.substrate_tab = hydro_GUI_2.SubstrateW(path_prj, name_prj)
        self.stathab_tab = stathab_GUI.StathabW(path_prj, name_prj)
        self.output_tab = output_fig_GUI.outputW(path_prj, name_prj)
        self.bioinfo_tab = bio_info_GUI.BioInfo(path_prj, name_prj)
        self.name_prj_c = name_prj
        self.path_prj_c = path_prj
        self.scroll = QScrollArea()
        self.rech = rech
        self.logon = True  # do we save the log in .log file or not
        self.child_win = ShowImageW(self.path_prj_c, self.name_prj_c)  # an extra windows to show figures
        self.vbar = self.scroll.verticalScrollBar()
        self.l2 = QLabel(self.tr('Log of HABBY started. <br>'))  # where the log is show
        self.init_iu()

    def init_iu(self):
        """
        A function to initilize an instance of CentralW. Called by __init___().
        """

        # create all the widgets
        biorun_tab = EmptyTab()
        bioinfo_tab = EmptyTab()
        other_tab = EmptyTab()
        other_tab2 = EmptyTab()

        # connect signals save figures
        self.hydro_tab.hecras1D.show_fig.connect(self.showfig)
        self.hydro_tab.hecras2D.show_fig.connect(self.showfig)
        self.hydro_tab.telemac.show_fig.connect(self.showfig)
        self.hydro_tab.rubar2d.show_fig.connect(self.showfig)
        self.hydro_tab.rubar1d.show_fig.connect(self.showfig)
        self.substrate_tab.show_fig.connect(self.showfig)
        self.statmod_tab.show_fig.connect(self.showfig)
        self.stathab_tab.show_fig.connect(self.showfig)
        self.hydro_tab.riverhere2d.show_fig.connect(self.showfig)
        self.hydro_tab.mascar.show_fig.connect(self.showfig)

        # connect signals to update the drop-down menu in the substrate tab when a new hydro hdf5 is created
        self.hydro_tab.hecras1D.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)
        self.hydro_tab.hecras2D.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)
        self.hydro_tab.telemac.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)
        self.hydro_tab.rubar2d.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)
        self.hydro_tab.rubar1d.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)
        self.hydro_tab.riverhere2d.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)
        self.hydro_tab.mascar.drop_hydro.connect(self.substrate_tab.update_hydro_hdf5_name)

        # connect signal for the log
        self.connect_signal_log()

        # fill the general tab
        self.welcome_tab.e1.setText(self.name_prj_c)
        self.welcome_tab.e2.setText(self.path_prj_c)
        # if the directoy to the project do not exist, leave the general tab empty
        if not os.path.isdir(self.path_prj_c):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Path to project"))
            self.msg2.setText( \
                self.tr("The directory indicated by the project path does not exists. Correction needed."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        fname = os.path.join(self.path_prj_c, self.name_prj_c+'.xml')
        # otherwise, fill it
        if os.path.isfile(fname):
            doc = ET.parse(fname)
            root = doc.getroot()
            user_child = root.find(".//User_Name")
            des_child = root.find(".//Description")
            self.welcome_tab.e4.setText(user_child.text)
            self.welcome_tab.e3.setText(des_child.text)
            logon_child = root.find(".//Save_Log")
            if logon_child == 'False' or logon_child == 'false':
                self.logon = False  # is True by default

        # add the widgets to the list of tab if a project exist
        if os.path.isfile(fname) and self.name_prj_c != '':
            self.tab_widget.addTab(self.welcome_tab, self.tr("Start"))
            self.tab_widget.addTab(self.hydro_tab, self.tr("Hydraulic"))
            self.tab_widget.addTab(self.substrate_tab, self.tr("Substrate"))
            self.tab_widget.addTab(self.bioinfo_tab, self.tr("Biology Info"))
            self.tab_widget.addTab(self.output_tab, self.tr("Output"))
            self.tab_widget.addTab(self.statmod_tab, self.tr("ESTIMHAB"))
            self.tab_widget.addTab(self.stathab_tab, self.tr("STATHAB"))
            if self.rech:
                self.tab_widget.addTab(other_tab, self.tr("Research 1"))
                self.tab_widget.addTab(other_tab2, self.tr("Research 2"))
            self.welcome_tab.lowpart.setEnabled(True)
        # if the project do not exist, do nmot add new tab
        else:
            self.tab_widget.addTab(self.welcome_tab, self.tr("Start"))
            self.welcome_tab.lowpart.setEnabled(False)

        # Area to show the log
        # add two Qlabel l1 ad l2 , with one scroll for the log in l2
        l1 = QLabel(self.tr('HABBY says:'))
        self.l2.setAlignment(Qt.AlignTop)
        self.l2.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.l2.setTextFormat(Qt.RichText)
        # see the end of the log first
        self.vbar.rangeChanged.connect(self.scrolldown)
        self.scroll.setWidget(self.l2)
        # to have the Qlabel at the right size
        self.scroll.setWidgetResizable(True)
        # colors
        self.scroll.setStyleSheet('background-color: white')
        self.vbar.setStyleSheet('background-color: lightGrey')

        # layout
        layoutc = QGridLayout()
        layoutc.addWidget(self.tab_widget, 1, 0)
        layoutc.addWidget(l1, 2, 0)
        layoutc.addWidget(self.scroll, 3, 0)
        self.setLayout(layoutc)

    def scrolldown(self):
        """
        Move the scroll bar to the bottow if the ScollArea is getting bigger
        """
        self.vbar.setValue(self.vbar.maximum())

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
                self.path_im = child.text

        plt.show()

    def showfig2(self):
        """
        A function to see all saved figures without possibility to zoom
        """
        self.child_win.update_namefig()
        self.child_win.selectionchange(-1)
        self.child_win.show()

    def optfig(self):
        """
        A small function which open the output tab. It contains the different options for the figures.
        Output should be the 6th tab, otherwise it will not work.
        """
        self.tab_widget.setCurrentIndex(5)

    def connect_signal_log(self):
        """
        connect all the signal linked to the log. This is in a function only to improve lisibility.
        """

        self.hydro_tab.send_log.connect(self.write_log)
        self.hydro_tab.hecras1D.send_log.connect(self.write_log)
        self.hydro_tab.hecras2D.send_log.connect(self.write_log)
        self.hydro_tab.rubar2d.send_log.connect(self.write_log)
        self.hydro_tab.rubar1d.send_log.connect(self.write_log)
        self.hydro_tab.telemac.send_log.connect(self.write_log)
        self.substrate_tab.send_log.connect(self.write_log)
        self.statmod_tab.send_log.connect(self.write_log)
        self.stathab_tab.send_log.connect(self.write_log)
        self.hydro_tab.riverhere2d.send_log.connect(self.write_log)
        self.hydro_tab.mascar.send_log.connect(self.write_log)
        self.child_win.send_log.connect(self.write_log)
        self.welcome_tab.send_log.connect(self.write_log)
        self.output_tab.send_log.connect(self.write_log)
        self.bioinfo_tab.send_log.connect(self.write_log)

    def write_log(self, text_log):
        """
        A function to write the different log. Please read the section of the doc on the log.

        :param text_log: the text which should be added to the log (a string)

        *   if text_log start with # -> added it to self.l2 (QLabel) and the .log file (comments)
        *   if text_log start with restart -> added it restart_nameproject.txt
        *   if text_log start with WARNING -> added it to self.l2 (QLabel) and the .log file
        *   if text_log start with ERROR -> added it to self.l2 (QLabel) and the .log file
        *   if text_log start with py -> added to the .log file (python command)
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
                pathname_logfile = child_logfile.text
            else:
                t = self.l2.text()
                self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: The "
                                    "log file is not indicated in the xml file. No log written. </br> <br>")
                return
            # restart log
            child_logfile = root.find(".//File_Restart")
            if child_logfile is not None:
                pathname_restartfile = child_logfile.text
            else:
                t = self.l2.text()
                self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: The "
                                    "restart file is not indicated in the xml file. No log written. </br> <br>")
                return
        else:
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#FF8C00'> WARNING: The project file is not "
                                "found. no Log written. </br> <br>")
            return

        # add comments to Qlabel and .log file
        if text_log[0] == '#':
            t = self.l2.text()
            self.l2.setText(t + text_log[1:] + '<br>')
            self.write_log_file(text_log, pathname_logfile)
        # add python code to the .log file
        elif text_log[:2] == 'py':
            self.write_log_file(text_log[2:], pathname_logfile)
        # add restart command to the restart file
        elif text_log[:7] == 'restart':
            self.write_log_file(text_log[7:], pathname_restartfile)
        elif text_log[:5] == 'Error':
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#FF0000'>" + text_log + ' </br><br>')  # error in red
            self.write_log_file('# ' +text_log, pathname_logfile)
        # add warning
        elif text_log[:7] == 'Warning':
            t = self.l2.text()
            self.l2.setText(t + "<FONT COLOR='#FF8C00'>" + text_log + ' </br><br>')  # warning in orange
            self.write_log_file('# ' + text_log, pathname_logfile)
        # other case not accounted for
        else:
            t = self.l2.text()
            self.l2.setText(t + text_log + '<br>')

    def write_log_file(self, text_log, pathname_logfile):
        """
        A function to write to the .log text. Called by write_log.

        :param text_log: the text to be written (string)
        :param pathname_logfile: the path+name where the log is
        """
        if self.logon:
            if os.path.isfile(pathname_logfile):
                with open(pathname_logfile, "a") as myfile:
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
                with open(pathname_logfile, "a") as myfile:
                    myfile.write("    name_projet = " + self.name_prj_c + "'\n")
                with open(pathname_logfile, "a") as myfile:
                    myfile.write("    path_projet = " + self.path_prj_c + "'\n")
                with open(pathname_logfile, "a") as myfile:
                    myfile.write('\n' + text_log)

        return


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

    def __init__(self):

        super().__init__()
        self.imname = r'\translation\test3.jpg'  # image shoulfd in the translation folder
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
        buttone = QPushButton(self.tr('Open Example'), self)
        buttone.clicked.connect(self.open_example)
        spacerleft = QSpacerItem(200, 1)
        spacerright = QSpacerItem(120, 1)
        spacer2 = QSpacerItem(1, 50)
        # color
        highpart = QWidget()  # used to regroup all QWidgt in the first part of the Windows

        # general into to put in the xml .prj file
        lg = QLabel(self.tr(" <b> Current Project </b>"))
        l1 = QLabel(self.tr('Project Name: '))
        self.e1 = QLineEdit()
        l2 = QLabel(self.tr('Main Folder: '))
        self.e2 = QLineEdit()
        button2 = QPushButton(self.tr('Set Folder'), self)
        button2.clicked.connect(self.setfolder)
        l3 = QLabel(self.tr('Description: '))
        self.e3 = QTextEdit()
        l4 = QLabel(self.tr('User Name: '))
        self.e4 = QLineEdit()
        self.buttonm = QPushButton(self.tr('Save Project Info'))
        self.buttonm.clicked.connect(self.save_signal.emit)
        self.lowpart = QWidget()

        # background image
        pic = QLabel()
        pic.setMaximumSize(1000, 200)
        # use full ABSOLUTE path to the image, not relative
        pic.setPixmap(QPixmap(os.getcwd() + self.imname).scaled(800, 500))  # 800 500

        # layout (in two parts)
        layout2 = QGridLayout()
        layouth = QGridLayout()
        layoutl = QGridLayout()

        layouth.addItem(spacerleft, 1, 0)
        layouth.addItem(spacerright, 1, 5)
        layouth.addWidget(l0, 0, 1)
        layouth.addWidget(buttono, 2, 1)
        layouth.addWidget(buttons, 3, 1)
        layouth.addWidget(buttone, 4, 1)
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
        layoutl.addWidget(self.buttonm, 4, 2)
        self.lowpart.setLayout(layoutl)

        layout2.addWidget(pic, 0, 0)
        layout2.addWidget(highpart, 0, 0)
        layout2.addWidget(self.lowpart, 1, 0)
        self.setLayout(layout2)

    def open_example(self):
        """
        This function will be used to open a project example for HABBY, but the example is not prepared yet
        """
        self.send_log.emit('Warning: No example prepared yet')

    def setfolder(self):
        """
        This function is used by the user to select the folder where the xml project file will be located.
        """
        dir_name = QFileDialog.getExistingDirectory(None)  # check for invalid null parameter on Linuxgit
        if dir_name != '':  # cancel case
            self.e2.setText(dir_name)
            self.send_log.emit('New folder selected for the project. \n')


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
    options.

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
        # self.w = 200  #size of the image (see if we let some options for this)
        # self.h = 200
        self.imtype = '*.png'
        self.path_im = os.path.join(self.path_prj, 'figures_habby')
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
        # self.label_im.setGeometry(QRect(0, 0, self.w, self.h))
        self.label_im.setScaledContents(True)
        self.but1 = QPushButton('Change Folder')
        self.but1.clicked.connect(self.change_folder)

        self.setWindowTitle(self.tr('ALL FIGURES'))

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
            pixmap = QPixmap(namefile_im)
            self.label_im.setPixmap(pixmap)
            self.label_im.show()

    def change_folder(self):
        """
        A function to change the folder where are stored the image (i.e., the path_im)
        """

        self.path_im = QFileDialog.getExistingDirectory(None)
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
            self.path_im = os.path.join(self.path_prj, 'figures_habby')
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


# class MyMplCanvas(FigureCanvas):
#     #Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
#     def __init__(self, parent=None, width=5, height=4, dpi=100):
#         fig = Figure(figsize=(width, height), dpi=dpi)
#         self.fig = fig
#         self.axes = fig.add_subplot(111)
#         # We want the axes cleared every time plot() is called
#         self.axes.hold(False)
#
#         self.compute_initial_figure()
#         FigureCanvas.__init__(self, fig)
#         self.setParent(parent)
#
#         FigureCanvas.setSizePolicy(self,
#                                    QSizePolicy.Expanding,
#                                    QSizePolicy.Expanding)
#         FigureCanvas.updateGeometry(self)
#
#     def compute_initial_figure(self):
#         pass
#
#
# class MyStaticMplCanvas(MyMplCanvas):
#     #Simple canvas with a sine plot.
#     def compute_initial_figure(self):
#         plt.show()
#         #figure()
#         #t = np.arange(0.0, 3.0, 0.01)
#         #s = np.sin(2*np.pi*t)
#         print(plt.gcf())
#
#         #self.axes = plt.gca()
#         self.fig = plt.gcf()



