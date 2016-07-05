import sys
import glob
import os
import shutil
import numpy as np
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from PyQt5.QtCore import QTranslator, pyqtSignal, QSettings, QRect, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,\
    QListWidgetItem, QAbstractItemView, QMessageBox, QComboBox, QScrollArea, QSizePolicy
from PyQt5.QtGui import QPixmap
import h5py
from src_GUI import estimhab_GUI
from src_GUI import hydro_GUI_2
from src_GUI import stathab_GUI


class MainWindows(QMainWindow):
    """
    The class MainWindows contains the menu and the title of all the HABBY windows.
    It also create all the widgets which can be called during execution
    """

    def __init__(self, user_option):
        # load user setting
        self.settings = QSettings('HABBY', 'irstea')
        name_prj_set = self.settings.value('name_prj')
        print(name_prj_set)
        name_path_set = self.settings.value('path_prj')
        print(name_path_set)
        language_set = self.settings.value('language_code')
        del self.settings
        # set up tranlsation
        self.languageTranslator = QTranslator()
        self.path_trans = r'.\translation'
        self.file_langue = [r'Zen_EN.qm', r'Zen_FR.qm']
        if language_set:
            self.lang = language_set
        else:
            self.lang = 0
        app = QApplication.instance()
        app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[self.lang], self.path_trans)
        app.installTranslator(self.languageTranslator)

        # prepare the attributes
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
        self.username_prj = "NoUserName"
        self.descri_prj = ""
        self.does_it_work = True

        # create the central widget
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)
        self.msg2 = QMessageBox()

        # call the normal constructor of QWidget
        super().__init__()
        # call an additional function during initialisation
        self.init_ui()

    def init_ui(self):

        # create the menu bar
        self.my_menu_bar()

        # connect the signals with the different functions
        self.central_widget.welcome_tab.save_signal.connect(self.save_project)
        self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        # set geometry
        self.setGeometry(300, 400, 700, 400)
        self.setCentralWidget(self.central_widget)
        self.show()

    def setlangue(self, nb_lang):
        """
        A function which change the language of the programme. It change the menu and the central widget.
        it uses the self.lang attribute which should be set to the new language before
        :param nb_lang the number representing the language (int)
        :return: None
        # 0 is for english, 1 for french, x for any additionnal language
        """
        # set the langugae
        self.lang = nb_lang
        # get a new tranlator
        app = QApplication.instance()
        app.removeTranslator(self.languageTranslator)
        self.languageTranslator = QTranslator()
        self.languageTranslator.load(self.file_langue[self.lang], self.path_trans)
        app.installTranslator(self.languageTranslator)

        # create the new menu
        self.my_menu_bar()

        # set the central widget
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)  # False is not research mode
        self.setCentralWidget(self.central_widget)

        # connect the signals with the different functions
        self.central_widget.welcome_tab.save_signal.connect(self.save_project)
        self.central_widget.statmod_tab.save_signal_estimhab.connect(self.save_project_estimhab)

        # update user option to remember the languge
        self.settings = QSettings('HABBY', 'irstea')
        self.settings.setValue('language_code', self.lang)
        del self.settings

    def my_menu_bar(self):
        """
        The function creating the menu bar
        :return: A menu
        """

        self.menubar = self.menuBar()
        self.menubar.clear()

        # Menu to open and close file
        exitAction = QAction(self.tr('&Exit'), self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip(self.tr('Exit application'))
        exitAction.triggered.connect(qApp.quit)
        openprj = QAction(self.tr('Open Project'), self)
        openprj.setShortcut('Ctrl+O')
        openprj.setStatusTip(self.tr('Open an exisiting project'))
        openprj.triggered.connect(open_project)
        newprj = QAction(self.tr('New Project'), self)
        newprj.setShortcut('Ctrl+N')
        newprj.setStatusTip(self.tr('Create a new project'))
        newprj.triggered.connect(new_project)
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
        fileMenu.addAction(newprj)
        fileMenu.addAction(exitAction)
        fileMenu4 = self.menubar.addMenu(self.tr('Options'))
        fileMenu4.addAction(logc)
        fileMenu4.addAction(logn)
        fileMenu4.addAction(logy)
        fileMenu4.addAction(rech)
        fileMenu4.addAction(rechc)
        fileMenu2 = self.menubar.addMenu(self.tr('Language'))
        fileMenu2.addAction(lAction1)
        fileMenu2.addAction(lAction2)
        fileMenu3 = self.menubar.addMenu(self.tr('Help'))
        fileMenu3.addAction(helpm)

        # add the status bar
        self.statusBar()

        # in case we need a tool bar
        # self.toolbar = self.addToolBar('')

        # add the title of the windows
        self.setWindowTitle(self.tr('HABBY- VERSION 1'))

    def save_project(self):
        """
        A function to save the xml file with the information of the project
        :return: None
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

        # update user option
        self.settings = QSettings('HABBY', 'irstea')
        self.settings.setValue('name_prj', self.name_prj)
        self.settings.setValue('path_prj', self.path_prj)
        del self.settings

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
            shutil.copy(os.path.join('src_GUI', 'log0.txt'), os.path.join(self.path_prj, self.name_prj + '.log'))
            shutil.copy(os.path.join('src_GUI', 'restart_log0.txt'), os.path.join(self.path_prj,
                                                                                  'restart_' + self.name_prj + '.log'))
            # more precise info
            user_child = ET.SubElement(general_element, "User_Name")
            user_child.text = self.username_prj
            des_child = ET.SubElement(general_element, "Description")
            des_child.text = self.descri_prj
            pathbio_child = ET.SubElement(root_element, "Path_Bio")
            pathbio_child.text = "./biologie\\"
            # save new xml file
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
            pathbio_child.text = "./biologie"
            user_child.text = self.username_prj
            des_child.text = self.descri_prj
            fname = os.path.join(self.path_prj, self.name_prj+'.xml')
            doc.write(fname)
            # create a default directory for the figures
            path_im = os.path.join(self.path_prj, 'figures_habby')
            if not os.path.exists(path_im):
                os.makedirs(path_im)

        # write log
        self.central_widget.write_log('# Project saved')
        self.central_widget.write_log("py    name_prj= '" + self.name_prj + "'")
        self.central_widget.write_log("py    path_prj= '" + self.path_prj + "'")
        self.central_widget.write_log("restart Name_project")
        self.central_widget.write_log("restart    name_prj= " + self.name_prj)

    def save_project_estimhab(self):
        """
        a function to save in an hdf5 file the information linked with Estimhab.
        :return:
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
        An utility function to test if the entry are float or not
        the boolean self.does_it_work is used to know if it functions without openning new message box
        :param var_in is the QlineEdit which contains the data
        :return: the variable
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
        open the additional research menu
        """
        self.rechmain = True
        self.central_widget = CentralW(self.rechmain, self.path_prj, self.name_prj)  # 0 is not research mode
        self.setCentralWidget(self.central_widget)

    def close_rech(self):
        """
            close the additional research menu
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
        :param save_log 0 -> do not save log, 1 -> save the log in the .log file and restart file
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


class CentralW(QWidget):
    """
    This class create the different tabs of the programm, which are then used as the central widget by MainWindows
    """

    def __init__(self, rech, path_prj, name_prj):

        self.msg2 = QMessageBox()
        self.welcome_tab = WelcomeW()
        self.statmod_tab = estimhab_GUI.EstimhabW(path_prj, name_prj)
        self.hydro_tab = hydro_GUI_2.Hydro2W(path_prj, name_prj)
        self.substrate_tab = hydro_GUI_2.SubstrateW(path_prj, name_prj)
        self.stathab_tab = stathab_GUI.StathabW(path_prj, name_prj)
        self.name_prj_c = name_prj
        self.path_prj_c = path_prj
        self.rech = rech
        self.logon = True  # do we save the log in .log file or not

        super().__init__()
        self.l2 = QLabel(self.tr('Log of HABBY started. <br>'))  # where the log is shown
        self.init_iu()
        self.child_win = None  # in case, we open an extra windows

    def init_iu(self):

        # create a tab and the name of the project6
        self.tab_widget = QTabWidget()

        # create all the widgets
        biorun_tab = HydroW()
        output_tab = HydroW()
        bioinfo_tab = HydroW()
        other_tab = HydroW()
        other_tab2 = HydroW()

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

        # connect signal for the log
        self.connect_signal_log()

        # fill the general tab
        self.welcome_tab.e1.setText(self.name_prj_c)
        self.welcome_tab.e2.setText(self.path_prj_c)
        if not os.path.isdir(self.path_prj_c):  # if the directoy do not exist
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Path to project"))
            self.msg2.setText( \
                self.tr("The directory indicated by the project path does not exists. Correction needed."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        fname = os.path.join(self.path_prj_c, self.name_prj_c+'.xml')
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

        # add the widget to the tab
        self.tab_widget.addTab(self.welcome_tab, self.tr("General"))
        self.tab_widget.addTab(self.hydro_tab, self.tr("Hydraulic"))
        self.tab_widget.addTab(self.substrate_tab, self.tr("Substrate"))
        self.tab_widget.addTab(bioinfo_tab, self.tr("Biology Info"))
        self.tab_widget.addTab(biorun_tab, self.tr("Run the model"))
        self.tab_widget.addTab(output_tab, self.tr("Output"))
        self.tab_widget.addTab(self.statmod_tab, self.tr("ESTIMHAB"))
        self.tab_widget.addTab(self.stathab_tab, self.tr("STATHAB"))
        if self.rech:
            self.tab_widget.addTab(other_tab, self.tr("Reseach 1"))
            self.tab_widget.addTab(other_tab2, self.tr("Reseach 2"))

        # Area to show the log
        # add two Qlabel l1 ad l2 , with one scroll for the log in l2
        l1 = QLabel(self.tr('HABBY says:'))
        self.l2.setAlignment(Qt.AlignTop)
        self.l2.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.l2.setTextFormat(Qt.RichText)
        self.scroll = QScrollArea()
        # see the end of the log first
        self.vbar = self.scroll.verticalScrollBar()
        self.vbar.rangeChanged.connect(self.scrolldown)
        self.scroll.setWidget(self.l2)
        # to have the Qlabel at the right size
        self.scroll.setWidgetResizable(True)
        # colors
        self.scroll.setStyleSheet('background-color: white')
        self.vbar.setStyleSheet('background-color: lightGrey')
        # redirect stdout

        # layout
        layoutc = QGridLayout()
        layoutc.addWidget(self.tab_widget, 1, 0)
        layoutc.addWidget(l1, 2, 0)
        layoutc.addWidget(self.scroll, 3, 0)
        self.setLayout(layoutc)

    def scrolldown(self):
        """
        Move the scroll bar to the bottowm if the ScollArea is getting bigger
        """
        self.vbar.setValue(self.vbar.maximum())

    def showfig(self):
        """
        A small function to show the last figures
        """
        self.child_win = ShowImageW(self.path_prj_c, self.name_prj_c)
        self.child_win.update_namefig()
        self.child_win.selectionchange(-1)
        self.child_win.show()

    def connect_signal_log(self):
        """
        connect all the signal linked to the log
        is in a function only to improve lisibility
        """
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

    def write_log(self, text_log):
        """
        A function to wrtie the different log
        :param text_log: the text which should be added to the log
        if start with # -> added it to self.l2 (QLabel) and the .log file (comments)
        if start with restart -> added it restart_nameproject.txt
        if start with WARNING -> added it to self.l2 (QLabel) and the .log file
        if start with ERROR -> added it to self.l2 (QLabel) and the .log file
        if start with py -> added to the .log file (python command)
        if start with nothing -> just print to the Qlabel
        if out from stdout -> added it to self.l2 (QLabel) and the .log file (comments)
        if logon = false do not write in log.txt
        :return:
        """
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
        A function to write to the .log text
        :param text_log: the text to be written
        :param pathname_logfile: the path+name where the log is
        :return:
        """
        if self.logon:
            if os.path.isfile(pathname_logfile):
                with open(pathname_logfile, "a") as myfile:
                    myfile.write('\n' + text_log)
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

    # define the signal used by the class
    # should be outise of the __init__ function
    save_signal = pyqtSignal()

    def __init__(self):

        super().__init__()
        self.init_iu()

    def init_iu(self):

        # general into to put in the xml .prj file
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

        # save and load button
        buttono = QPushButton(self.tr('Open Project'), self)
        buttono.clicked.connect(open_project)
        buttons = QPushButton(self.tr('Save Project'), self)
        buttons.clicked.connect(self.save_signal.emit)
        spacer = QSpacerItem(50, 50)

        layout2 = QGridLayout()
        layout2.addWidget(l1, 0, 0)
        layout2.addWidget(self.e1, 0, 1)
        layout2.addWidget(l2, 1, 0)
        layout2.addWidget(self.e2, 1, 1)
        layout2.addWidget(button2, 1, 2)
        layout2.addWidget(l4, 2, 0)
        layout2.addWidget(self.e4, 2, 1)
        layout2.addWidget(l3, 3, 0)
        layout2.addWidget(self.e3, 3, 1)
        # layout2.addWidget(buttonn, 4, 2)
        layout2.addWidget(buttono, 4, 2)
        layout2.addWidget(buttons, 4, 1)
        layout2.addItem(spacer, 5, 1)
        self.setLayout(layout2)

    def addtext(self):
        print('Text Text and MORE Text')

    def setfolder(self):
        dir_name = QFileDialog.getExistingDirectory()
        if dir_name != '':  # cancel case
            self.e2.setText(dir_name)


class HydroW(QWidget):

    def __init__(self):
        super().__init__()
        self.init_iu()

    def init_iu(self):
        button1 = QPushButton(self.tr('I am a tab'), self)
        button1.clicked.connect(self.addtext)

        button2 = QPushButton(self.tr('I am really'), self)
        button2.clicked.connect(self.addtext)

        layout1 = QGridLayout()
        layout1.addWidget(button1, 0, 0)
        layout1.addWidget(button2, 1, 0)
        self.setLayout(layout1)

    def addtext(self):
        print('Text Text and MORE Text')


class ShowImageW(QWidget):
    """
    The widget which shows the saved images (so that there is a return when you saved somethings)
    :return:
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.image_list = QComboBox()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.label_im = QLabel()
        #self.w = 200  #size of the image (see if we let some options for this)
        #self.h = 200
        self.imtype = '*.png'
        self.path_im = os.path.join(self.path_prj, 'figures_habby')
        self.msg2 = QMessageBox()
        self.init_iu()

    def init_iu(self):

        # check if there is a path where to save the image
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//" + 'Path_Figure')
            if child is not None:
                self.path_im = child.text

        # find all figures and add them to the menu ComboBox
        self.update_namefig()
        self.image_list.currentIndexChanged.connect(self.selectionchange)

        # create the label which will show the figure
        # self.label_im.setGeometry(QRect(0, 0, self.w, self.h))
        self.label_im.setScaledContents(True)
        self.but1 = QPushButton('Change Folder')
        self.but1.clicked.connect(self.change_folder)

        self.setWindowTitle(self.tr('FIGURES'))

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
        A function to change the figure
        :return:
        """
        if not self.all_file:
            return
        else:
            namefile_im = os.path.join(self.path_im,self.all_file[i])
            pixmap = QPixmap(namefile_im)
            self.label_im.setPixmap(pixmap)

    def change_folder(self):
        """
        a function to change the folder where are the image
        :return:
        """
        self.path_im = QFileDialog.getExistingDirectory()
        self.update_namefig()
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(filename_path_pro):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
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
            doc.write(filename_path_pro, method="xml")

    def update_namefig(self):
        """
        add the different figure name to the drop-down list
        :return:
        """
        self.image_list.clear()
        if not self.path_im:
            self.path_im = os.path.join(self.path_prj, 'figures_habby')
        self.all_file = glob.glob(os.path.join(self.path_im, self.imtype))
        if not self.all_file:
            return
        self.all_file.sort(key=os.path.getmtime)  # the newest figure on the top
        if self.all_file[0] != 'Available figures':
            first_name = self.tr('Available figures')  # variable needed for the translation
            self.all_file = [first_name] + self.all_file
        all_file_nice = self.all_file
        # make them look nicer
        for i in range(0, len(all_file_nice)):
            all_file_nice[i] = all_file_nice[i].replace(self.path_im, "")
            all_file_nice[i] = all_file_nice[i].replace("\\", "")
        self.image_list.addItems(all_file_nice)


def open_project():
    print('I wish to open a project')


def new_project():
    print('I wish to create a new project')


def main():

    # create app
    app = QApplication(sys.argv)
    # create windows
    ex = MainWindows('user_opt.xml')

    # close
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
