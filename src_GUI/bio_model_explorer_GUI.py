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
from io import StringIO
from PyQt5.QtCore import pyqtSignal, Qt, QTimer, QStringListModel
from PyQt5.QtWidgets import QPushButton, QLabel, QGroupBox, QVBoxLayout, QListWidget, QGridLayout, QLineEdit, QMessageBox, QTabWidget,\
    QComboBox, QAbstractItemView, \
    QSizePolicy, QScrollArea, QFrame, QDialog, QCompleter, QTextEdit
from PyQt5.QtGui import QPixmap, QIcon
from multiprocessing import Process, Queue, Value
import os
import sys
import numpy as np

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import bio_info_mod
from src_GUI import estimhab_GUI
from src import calcul_hab_mod
from src import hdf5_mod
from src import plot_mod
from src_GUI import preferences_GUI
from habby import CONFIG_HABBY


class BioModelExplorerWindow(QDialog):
    """
    BioModelExplorerWindow
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj, name_icon):

        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_icon = name_icon
        self.msg2 = QMessageBox()
        self.path_bio = CONFIG_HABBY.path_bio
        # filters index

        # tabs
        self.bio_model_filter_tab = BioModelFilterTab(path_prj, name_prj)
        self.bio_model_infoselection_tab = BioModelInfoSelection(path_prj, name_prj)
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.bio_model_filter_tab, self.tr("Model filter"))
        self.tab_widget.addTab(self.bio_model_infoselection_tab, self.tr("Model selected"))

        self.setGeometry(60, 95, 800, 600)

        general_layout = QVBoxLayout(self)
        general_layout.addWidget(self.tab_widget)
        self.setWindowTitle(self.tr("Biological model explorer"))
        self.setWindowIcon(QIcon(self.name_icon))

    def open_bio_model_explorer(self):
        # fill_filters
        self.bio_model_filter_tab.fill_filters()
        self.show()


class BioModelFilterTab(QScrollArea):
    """
     This class contains the tab with Graphic production biological information (the curves of preference).
     """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "model_filter"
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

        """ WIDGET """
        # filters
        country_label = QLabel(self.tr("Country"))
        self.country_listwidget = QListWidget()
        self.country_listwidget.setObjectName("country")
        aquatic_animal_type_label = QLabel(self.tr("Aquatic animal type"))
        self.aquatic_animal_type_listwidget = QListWidget()
        self.aquatic_animal_type_listwidget.setObjectName("aquatic_animal_type")
        model_type_label = QLabel(self.tr("Model type"))
        self.model_type_listwidget = QListWidget()
        self.model_type_listwidget.setObjectName("model_type")
        stage_and_size_label = QLabel(self.tr("Stage and size"))
        self.stage_and_size_listwidget = QListWidget()
        self.stage_and_size_listwidget.setObjectName("stage_and_size")
        guild_label = QLabel(self.tr("Guild"))
        self.guild_listwidget = QListWidget()
        self.guild_listwidget.setObjectName("guild")
        origine_label = QLabel(self.tr("Origine"))
        self.origine_listwidget = QListWidget()
        self.origine_listwidget.setObjectName("xml_origine")
        made_by_label = QLabel(self.tr("Made by"))
        self.made_by_listwidget = QListWidget()
        self.made_by_listwidget.setObjectName("made_by")

        # filter_list
        self.filter_list = [self.country_listwidget, self.aquatic_animal_type_listwidget, self.model_type_listwidget,
                            self.stage_and_size_listwidget, self.guild_listwidget, self.origine_listwidget,
                            self.made_by_listwidget]
        [filter_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection) for filter_listwidget in self.filter_list]

        # last filters
        fish_label = QLabel("Fish available")
        self.fish_listwidget = QListWidget()
        self.fish_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        invertebrate_label = QLabel("Invertebrate available")
        self.invertebrate_listwidget = QListWidget()
        self.invertebrate_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        """ GROUP ET LAYOUT """
        # filters
        self.filter_group = QGroupBox(self.tr("Filters"))
        self.filter_layout = QGridLayout(self.filter_group)
        self.filter_layout.addWidget(country_label, 0, 0)
        self.filter_layout.addWidget(self.country_listwidget, 1, 0)
        self.filter_layout.addWidget(aquatic_animal_type_label, 0, 1)
        self.filter_layout.addWidget(self.aquatic_animal_type_listwidget, 1, 1)
        self.filter_layout.addWidget(model_type_label, 0, 2)
        self.filter_layout.addWidget(self.model_type_listwidget, 1, 2)
        self.filter_layout.addWidget(stage_and_size_label, 0, 3)
        self.filter_layout.addWidget(self.stage_and_size_listwidget, 1, 3)
        self.filter_layout.addWidget(guild_label, 0, 4)
        self.filter_layout.addWidget(self.guild_listwidget, 1, 4)
        self.filter_layout.addWidget(origine_label, 0, 5)
        self.filter_layout.addWidget(self.origine_listwidget, 1, 5)
        self.filter_layout.addWidget(made_by_label, 0, 6)
        self.filter_layout.addWidget(self.made_by_listwidget, 1, 6)

        # last filters
        self.last_filter_group = QGroupBox(self.tr("Last filters"))
        self.last_filter_layout = QGridLayout(self.last_filter_group)
        self.last_filter_layout.addWidget(fish_label, 0, 0)
        self.last_filter_layout.addWidget(self.fish_listwidget, 1, 0)
        self.last_filter_layout.addWidget(invertebrate_label, 0, 1)
        self.last_filter_layout.addWidget(self.invertebrate_listwidget, 1, 1)

        """ GENERAL """
        # tools frame
        tools_frame = QFrame()
        tools_frame.setFrameShape(QFrame.NoFrame)
        tools_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout(self)
        global_layout.addWidget(self.filter_group)
        global_layout.addWidget(self.last_filter_group)
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)

    def fill_filters(self):
        # filters
        for filter_listwidget in self.filter_list:
            # clear
            filter_listwidget.clear()
            # add items
            filter_listwidget.addItems(CONFIG_HABBY.biological_models_dict_set[filter_listwidget.objectName()])
            # select all
            filter_listwidget.selectAll()

        # last filter
        self.fish_listwidget.clear()
        self.fish_listwidget.addItems(CONFIG_HABBY.biological_models_dict_set["code_alternative"])
        self.fish_listwidget.selectAll()
        self.invertebrate_listwidget.clear()
        #self.invertebrate_listwidget.addItems(CONFIG_HABBY.biological_models_dict_set["code_alternative"])
        self.invertebrate_listwidget.selectAll()


class BioModelInfoSelection(QScrollArea):
    """
     This class contains the tab with Graphic production biological information (the curves of preference).
     """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "model_selected"
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

        """ informations suivtabiolity curve """
        # info on preference curve
        l4 = QLabel(self.tr('<b> Information on the suitability curve</b> (Right click on fish name)'))
        l5 = QLabel(self.tr('Latin Name: '))
        self.com_name = QLabel()
        l7 = QLabel(self.tr('ONEMA fish code: '))
        self.fish_code = QLabel('')
        l8 = QLabel(self.tr('Description:'))
        self.descr = QTextEdit(self)  # where the log is show
        self.descr.setReadOnly(True)
        self.pref_curve = QPushButton(self.tr('Show suitability curve'))
        self.pref_curve.clicked.connect(self.show_pref)

        # # show information about the fish
        # self.list_s.itemClicked.connect(self.show_info_fish_sel)
        # self.list_s.itemActivated.connect(self.show_info_fish_sel)
        # # shwo info if movement of the arrow key
        # self.list_s.itemSelectionChanged.connect(lambda: self.show_info_fish(True))

        # image fish
        self.pic = QLabel()

        # hydrosignature
        self.hs = QPushButton(self.tr('Show Measurement Conditions (Hydrosignature)'))
        self.hs.clicked.connect(self.show_hydrosignature)

        # fill in list of fish
        self.data_fish = CONFIG_HABBY.biological_models_dict

        # erase fish selection
        self.butdel = QPushButton(self.tr("Erase All Selection"))
        # self.butdel.clicked.connect(self.remove_all_fish)
        #
        # # fish selected fish
        # self.add_sel_fish()
        # if self.list_s.count() == 0:
        #     self.runhab.setDisabled(True)
        #     self.runhab.setStyleSheet("background-color: #47B5E6")
        # else:
        #     self.runhab.setStyleSheet("background-color: #47B5E6; color: white; font: bold")

        # # search possibility
        # l3 = QLabel(self.tr('<b> Search biological models </b>'))
        # self.keys = QComboBox()
        # self.keys.addItems(self.attribute_acc[:-1])
        # self.keys.currentIndexChanged.connect(self.get_autocompletion)
        # l02 = QLabel(" = ")
        # l02.setAlignment(Qt.AlignCenter)
        # self.cond1 = QLineEdit()
        # self.cond1.returnPressed.connect(self.next_completion)
        # # self.cond1.returnPressed.connect(self.select_fish)
        # self.bs = QPushButton(self.tr('Select suitability curve'))
        # self.bs.clicked.connect(self.select_fish)
        # # add auto-completion
        # self.completer = QCompleter()
        # self.model = QStringListModel()
        # self.completer.setModel(self.model)
        # self.cond1.setCompleter(self.completer)
        # self.get_autocompletion()
        # tools frame
        tools_frame = QFrame()
        tools_frame.setFrameShape(QFrame.NoFrame)
        tools_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout(self)
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)

    def next_completion(self):
        """
        A small function to use the enter key to select the fish with auto-completion.
        Adapted from https://stackoverflow.com/questions/9044001/qcompleter-and-tab-key
        It would be nice to make it work with tab also but it is quite complcated because the tab key is already used by
        PyQt to go from one windows to the next.
        """
        index = self.completer.currentIndex()
        self.completer.popup().setCurrentIndex(index)
        start = self.completer.currentRow()
        if not self.completer.setCurrentRow(start + 1):
            self.completer.setCurrentRow(0)

        self.select_fish()

    def get_autocompletion(self):
        """
        This function updates the auto-complexton model as a function of the QComboxBox next to it with support for
        upper and lower case.
        """
        ind = self.keys.currentIndex()

        if ind == 0:
            string_all = list(
                set(list(self.data_fish[:, 1]) + list([item.lower() for item in self.data_fish[:, 1]]) +
                    list([item.upper() for item in self.data_fish[:, 1]])))
        elif ind == 1:
            string_all = list(set(list(self.data_fish[:, 3]) + [item.lower() for item in self.data_fish[:, 3]] +
                                  [item.upper() for item in self.data_fish[:, 3]]))
        elif ind == 2:
            string_all = list(set(list(self.data_fish[:, 4]) + [item.lower() for item in self.data_fish[:, 4]] +
                                  [item.upper() for item in self.data_fish[:, 4]]))
        elif ind == 3:
            string_all = list(set(list(self.data_fish[:, 5]) + [item.lower() for item in self.data_fish[:, 5]] +
                                  [item.upper() for item in self.data_fish[:, 5]]))
        elif ind == 4:
            string_all = list(set(list(self.data_fish[:, 6]) + [item.lower() for item in self.data_fish[:, 6]] +
                                  [item.upper() for item in self.data_fish[:, 6]]))
        elif ind == 5:
            string_all = list(set(list(self.data_fish[:, 7]) + [item.lower() for item in self.data_fish[:, 7]] +
                                  [item.upper() for item in self.data_fish[:, 7]]))
        else:
            string_all = ''

        self.model.setStringList(string_all)

    def show_info_fish(self, select=False):
        """
        This function shows the useful information concerning the selected fish on the GUI.

        :param select:If False, the selected items comes from the QListWidgetcontaining the available fish.
                      If True, the items comes the QListWidget with the selected fish
        """

        # get the file
        if not select:
            i1 = self.list_f.currentItem()  # show the info concerning the one selected fish
            if not i1:
                return
            self.ind_current = self.list_f.currentRow()
        else:
            found_it = False
            i1 = self.list_s.currentItem()
            if not i1:
                return
            for m in range(0, self.list_f.count()):
                self.list_f.setCurrentRow(m)
                if i1.text() == self.list_f.currentItem().text():
                    self.ind_current = m
                    found_it = True
                    break
            if not found_it:
                self.ind_current = None

        if i1 is None:
            return

        name_fish = i1.text()
        name_fish = name_fish.split(':')[0]
        i = np.where(self.data_fish[:, 7] == name_fish)[0]
        if len(i) > 0:
            xmlfile = os.path.join(self.path_bio, self.data_fish[i[0], 2])
        else:
            return

        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file does not exist \n")
                return
        except ET.ParseError:
            print("Warning: the xml file is not well-formed.\n")
            return

        # get the data code ONEMA
        # for the moment only one code alternativ possible
        data = root.find('.//CdAlternative')
        if data is not None:
            if data.attrib['OrgCdAlternative']:
                if data.attrib['OrgCdAlternative'] == 'ONEMA':
                    self.fish_code.setText(data.text)

        # get the latin name
        data = root.find('.//LatinName')
        if data is not None:
            self.com_name.setText(data.text)

        # get the description
        data = root.findall('.//Description')
        if len(data) > 0:
            found = False
            for d in data:
                if d.attrib['Language'] == self.lang:
                    self.descr.setText(d.text[2:-1])
                    found = True
            if not found:
                self.descr.setText(data[0].text[2:-1])

        # get the image fish
        data = root.find('.//Image')
        if data is not None:
            self.imfish = os.path.join(os.getcwd(), self.path_im_bio, data.text)
            name_imhere = os.path.join(os.getcwd(), self.path_im_bio, data.text)
            if os.path.isfile(name_imhere):
                # use full ABSOLUTE path to the image, not relative
                self.pic.setPixmap(QPixmap(name_imhere).scaled(200, 90, Qt.KeepAspectRatio))  # 800 500
            else:
                self.pic.clear()
        else:
            self.pic.clear()

    def show_info_fish_sel(self):
        """
        This function shows the useful information concerning the already selected fish on the GUI and
        remove fish from the list of selected fish. This is what happens when the user click on the
        second QListWidget (the one called selected fish and guild).
        """

        self.show_info_fish(True)
        self.remove_fish()
        # Enable the button
        if self.list_s.count() > 0:
            self.runhab.setEnabled(True)
        else:
            self.runhab.setEnabled(False)

    def show_info_fish_avai(self):
        """
        This function shows the useful information concerning the available fish on the GUI and
        add the fish to  the selected fish This is what happens when the user click on the
        first QListWidget (the one called available fish).
        """

        self.show_info_fish(False)
        self.add_fish()
        if self.list_s.count() > 0:
            self.runhab.setEnabled(True)
        else:
            self.runhab.setEnabled(False)

    def show_hydrosignature(self):
        """
        This function make the link with function in bio_info_mod.py which allows to load and plot the data related
        to the hydrosignature.
        """

        # get the file
        i = self.list_f.currentRow()
        xmlfile = os.path.join(self.path_bio, self.data_fish[i, 2])

        # get data
        sys.stdout = self.mystdout = StringIO()  # out to GUI
        data = bio_info_mod.get_hydrosignature(xmlfile)
        sys.stdout = sys.__stdout__  # reset to console
        self.send_err_log()
        if isinstance(data, np.ndarray):
            # do the plot
            if not hasattr(self, 'plot_process_list'):
                self.plot_process_list = MyProcessList()
            state = Value("i", 0)
            hydrosignature_process = Process(target=plot_mod.plot_hydrosignature,
                                             args=(state,
                                                   data,
                                                   self.data_fish[i, 0]))
            self.plot_process_list.append((hydrosignature_process, state))

    def show_pref(self):
        """
        This function shows the image of the preference curve of the selected xml file. For this it calls, the functions
        read_pref and figure_pref of bio_info_mod.py. Hence, this function justs makes the link between the GUI and
        the functions effectively doing the image.
        """

        if self.ind_current is None:
            self.send_log.emit("Warning: No fish selected to create suitability curves.")
            return

        # get the file
        i = self.ind_current  # show the info concerning the one selected fish
        xmlfile = os.path.join(self.path_bio, self.data_fish[i, 2])

        # open the pref
        sys.stdout = self.mystdout = StringIO()
        [h_all, vel_all, sub_all, code_fish, name_fish, stages] = bio_info_mod.read_pref(xmlfile)
        sys.stdout = sys.__stdout__
        self.send_err_log()
        # plot the pref
        fig_dict = preferences_GUI.load_fig_option(self.path_prj, self.name_prj)

        # do the plot
        if not hasattr(self, 'plot_process_list'):
            self.plot_process_list = MyProcessList()
        state = Value("i", 0)
        curve_process = Process(target=plot_mod.plot_suitability_curve,
                                args=(state,
                                      h_all,
                                      vel_all,
                                      sub_all,
                                      code_fish,
                                      name_fish,
                                      stages,
                                      False,
                                      fig_dict))
        self.plot_process_list.append((curve_process, state))
