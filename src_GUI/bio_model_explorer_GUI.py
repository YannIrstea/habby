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
from operator import concat
from functools import reduce
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
        self.bio_model_filter_tab.send_selection.connect(self.bio_model_infoselection_tab.get_selection_user)
        self.bio_model_filter_tab.send_fill.connect(self.bio_model_infoselection_tab.fill_available_aquatic_animal)

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
        # fill_country_filter
        self.bio_model_filter_tab.fill_country_filter()
        self.show()


class BioModelFilterTab(QScrollArea):
    """
     This class contains the tab with Graphic production biological information (the curves of preference).
     """
    send_selection = pyqtSignal(object, name='send_selection')
    send_fill = pyqtSignal(object, name='send_fill')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.tab_name = "model_filter"
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.biological_models_dict_gui = CONFIG_HABBY.biological_models_dict.copy()
        self.createDicoSelect()
        self.init_iu()
        self.first_fill_widget()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

        """ WIDGET """
        # country
        country_label = QLabel(self.tr("Country"))
        self.country_listwidget = QListWidget()
        self.country_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][0])
        self.country_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.country_listwidget.objectName()))
        # aquatic_animal_type
        aquatic_animal_type_label = QLabel(self.tr("Aquatic animal type"))
        self.aquatic_animal_type_listwidget = QListWidget()
        self.aquatic_animal_type_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][1])
        self.aquatic_animal_type_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.aquatic_animal_type_listwidget.objectName()))
        # model_type
        model_type_label = QLabel(self.tr("Model type"))
        self.model_type_listwidget = QListWidget()
        self.model_type_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][2])
        self.model_type_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.model_type_listwidget.objectName()))
        # stage_and_size
        stage_and_size_label = QLabel(self.tr("Stage and size"))
        self.stage_and_size_listwidget = QListWidget()
        self.stage_and_size_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][3])
        self.stage_and_size_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.stage_and_size_listwidget.objectName()))
        # guild
        guild_label = QLabel(self.tr("Guild"))
        self.guild_listwidget = QListWidget()
        self.guild_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][4])
        self.guild_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.guild_listwidget.objectName()))
        # origine
        xml_origine_label = QLabel(self.tr("Origine"))
        self.xml_origine_listwidget = QListWidget()
        self.xml_origine_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][5])
        self.xml_origine_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.xml_origine_listwidget.objectName()))
        # made_by
        made_by_label = QLabel(self.tr("Made by"))
        self.made_by_listwidget = QListWidget()
        self.made_by_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][6])
        self.made_by_listwidget.itemSelectionChanged.connect(lambda: self.ResultFromSelected(self.made_by_listwidget.objectName()))
        # code_alternative
        code_alternative_label = QLabel(self.tr("Code alternative"))
        self.code_alternative_listwidget = QListWidget()
        self.code_alternative_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][7])
        #self.code_alternative_listwidget.itemSelectionChanged.connect(self.get_available_aquatic_animal)
        invertebrate_label = QLabel("Invertebrate available")
        # invertebrate
        self.invertebrate_listwidget = QListWidget()

        # filters_list_widget
        self.filters_list_widget = [self.country_listwidget, self.aquatic_animal_type_listwidget, self.model_type_listwidget,
                                    self.stage_and_size_listwidget, self.guild_listwidget, self.xml_origine_listwidget,
                                    self.made_by_listwidget, self.code_alternative_listwidget]
        [filter_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection) for filter_listwidget in self.filters_list_widget]
        # filters names
        self.filters_list_name = [filter_listwidget.objectName() for filter_listwidget in self.filters_list_widget]

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
        self.filter_layout.addWidget(xml_origine_label, 0, 5)
        self.filter_layout.addWidget(self.xml_origine_listwidget, 1, 5)
        self.filter_layout.addWidget(made_by_label, 0, 6)
        self.filter_layout.addWidget(self.made_by_listwidget, 1, 6)

        # last filters
        self.last_filter_group = QGroupBox(self.tr("Last filters"))
        self.last_filter_layout = QGridLayout(self.last_filter_group)
        self.last_filter_layout.addWidget(code_alternative_label, 0, 0)
        self.last_filter_layout.addWidget(self.code_alternative_listwidget, 1, 0)
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

    def createDicoSelect(self):
        self.DicoSelect = dict()
        for i, ky in enumerate(self.biological_models_dict_gui['orderedKeys']):
            #print(ky)
            if self.biological_models_dict_gui['orderedKeysmultilist'][i]:
                s1 = sorted({x for l in self.biological_models_dict_gui[ky] for x in l})
            else:
                s1 = sorted(set(self.biological_models_dict_gui[ky]))
            s2 = [True] * len(s1)
            self.DicoSelect[ky] = [s1, s2, False]
        self.DicoSelect[self.biological_models_dict_gui['orderedKeys'][0]][2] = True

    def first_fill_widget(self):
        for key in self.DicoSelect.keys():
            listwidget = eval("self." + key + "_listwidget")
            if self.DicoSelect[key][2]:
                for ind, bo in enumerate(self.DicoSelect[key][1]):
                    if bo:
                        listwidget.addItem(self.DicoSelect[key][0][ind])

    def ResultFromSelected(self, ky):
        print("ResultFromSelected", ky)
        # get selected
        listwidget = eval("self." + ky + "_listwidget")
        selection = listwidget.selectedItems()
        actual_key_ind = self.biological_models_dict_gui['orderedKeys'].index(ky)
        next_key_ind = actual_key_ind + 1
        if selection:
            # selected_values_list
            lky = [selection_item.text() for selection_item in selection]
            lky = set(lky)
            self.DicoSelect[ky][1] = [x in lky for x in self.DicoSelect[ky][0]]

        self.biological_models_dict_gui['selected'] = np.ones((len(self.biological_models_dict_gui['selected']),), dtype=bool)
        for iky in range(next_key_ind):
            kyi=self.biological_models_dict_gui['orderedKeys'][iky]
            lky={x for x,y in zip(self.DicoSelect[kyi][0],self.DicoSelect[kyi][1]) if y}
            if self.biological_models_dict_gui['orderedKeysmultilist'][iky]: # if multi
                sky = [len(lky & x) != 0 for x in self.biological_models_dict_gui[kyi]]
            else: # if solo
                sky = [x in lky for x in self.biological_models_dict_gui[kyi]]
            self.biological_models_dict_gui['selected'] = np.logical_and(self.biological_models_dict_gui['selected'], np.array(sky))
            self.DicoSelect[kyi][2]=True
        if next_key_ind != len(self.biological_models_dict_gui['orderedKeys']):
            for indice in range(next_key_ind, len(self.biological_models_dict_gui['orderedKeys'])):
                listwidget = eval("self." + self.biological_models_dict_gui['orderedKeys'][indice] + "_listwidget")
                self.DicoSelect[self.biological_models_dict_gui['orderedKeys'][indice]][2] = False    # all subkeys are off
                listwidget.clear()
                print("clear", self.biological_models_dict_gui['orderedKeys'][indice])
            if selection :
                self.ResultToSelected(self.biological_models_dict_gui['orderedKeys'][next_key_ind])

    def ResultToSelected(self, ky):
        sp = [x for x, y in zip(self.biological_models_dict_gui[ky], list(self.biological_models_dict_gui['selected'])) if y]
        if self.biological_models_dict_gui['orderedKeysmultilist'][self.biological_models_dict_gui['orderedKeys'].index(ky)]:
            sp = {x for y in sp for x in y}
        else:
            sp = set(sp)
        # print(sp)
        self.DicoSelect[ky][1] = [x in sp for x in self.DicoSelect[ky][0]]
        self.DicoSelect[ky][2] = False  # the key is off
        # print(self.DicoSelect)
        # display
        listwidget = eval("self." + ky + "_listwidget")
        for ind, bo in enumerate(self.DicoSelect[ky][1]):
            if bo:
                listwidget.addItem(self.DicoSelect[ky][0][ind])



    def fill_country_filter(self):
        # country
        self.country_listwidget.addItems(CONFIG_HABBY.biological_models_dict_set["country"])

    def fill_filters(self, filter_name):
        # get listwidget
        listwidget = eval("self." + filter_name + "_listwidget")

        if filter_name != "code_alternative":
            # get next filter
            next_filter_name = self.filters_list_name[self.filters_list_name.index(filter_name) + 1]
            # get next listwidget
            next_listwidget = eval("self." + next_filter_name + "_listwidget")

        # get selected
        selection = listwidget.selectedItems()
        if selection:
            # selected_values_list
            selected_values_list = [selection_item.text() for selection_item in selection]

            # get indice of selected
            indice = []
            for selected_value in selected_values_list:
                for indice_loop, selected_value_list in enumerate(self.biological_models_dict_gui[filter_name]):
                    if selected_value in selected_value_list:
                        indice.append(indice_loop)

            # get only row dict from indice
            for key in self.biological_models_dict_gui.keys():
                print("before :", len(self.biological_models_dict_gui[key]))
                self.biological_models_dict_gui[key] = [self.biological_models_dict_gui[key][i] for i in indice]
                print("after :", len(self.biological_models_dict_gui[key]))

            # get set
            if filter_name != "code_alternative":
                if type(self.biological_models_dict_gui[next_filter_name][0]) == list:
                    set_list = sorted(list(set(reduce(concat, self.biological_models_dict_gui[next_filter_name]))))
                else:
                    set_list = sorted(list(set(self.biological_models_dict_gui[next_filter_name])))

                # set item
                next_listwidget.clear()
                next_listwidget.addItems(set_list)
        else:
            if filter_name != "code_alternative":
                # clear
                next_listwidget.clear()

            # reset
            if filter_name == "country":
                self.biological_models_dict_gui = CONFIG_HABBY.biological_models_dict.copy()

    def get_available_aquatic_animal(self):
        # last sort
        self.fill_filters(self.code_alternative_listwidget.objectName())

        # new dict
        selection_dict = dict(country=[],  # sortable
             aquatic_animal_type=[],  # sortable
             model_type=[],  # sortable
             stage_and_size=[],  # sortable
             guild=[],  # sortable
             xml_origine=[],  # sortable
             made_by=[],  # sortable
             code_alternative=[])

        # get selection
        for filter_listwidget in self.filters_list_widget:
            selection_dict[filter_listwidget.objectName()] = [selection_item.text() for selection_item in filter_listwidget.selectedItems()]

        self.send_selection.emit(selection_dict)
        self.send_fill.emit(self.biological_models_dict_gui)


class BioModelInfoSelection(QScrollArea):
    """
     This class contains the tab with Graphic production biological information (the curves of preference).
     """
    send_log = pyqtSignal(object, name='send_log')
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

        """ WIDGET """
        # available_aquatic_animal
        available_aquatic_animal_label = QLabel(self.tr("Available aquiatic animal"))
        self.available_aquatic_animal_listwidget = QListWidget()
        selected_aquatic_animal_label = QLabel(self.tr("Selected aquatic animal"))
        self.selected_aquatic_animal_listwidget = QListWidget()

        # # show information about the fish
        # self.list_s.itemClicked.connect(self.show_info_fish_sel)
        # self.list_s.itemActivated.connect(self.show_info_fish_sel)
        # # shwo info if movement of the arrow key
        # self.list_s.itemSelectionChanged.connect(lambda: self.show_info_fish(True))

        # latin_name
        latin_name_title_label = QLabel(self.tr('Latin Name: '))
        self.latin_name_label = QLabel("")
        # show_curve
        self.show_curve_pushbutton = QPushButton(self.tr('Show suitability curve'))
        self.show_curve_pushbutton.clicked.connect(self.show_pref)
        # code_alternative
        code_alternative_title_label = QLabel(self.tr('ONEMA fish code: '))
        self.code_alternative_label = QLabel("")
        # hydrosignature
        self.hydrosignature_pushbutton = QPushButton(self.tr('Show Measurement Conditions (Hydrosignature)'))
        self.hydrosignature_pushbutton.clicked.connect(self.show_hydrosignature)
        # description
        description_title_label = QLabel(self.tr('Description:'))
        self.description_textedit = QTextEdit(self)  # where the log is show
        self.description_textedit.setReadOnly(True)
        # image fish
        self.animal_picture_label = QLabel()


        """ GROUP ET LAYOUT """
        # aquatic_animal
        #self.aquatic_animal_group = QGroupBox("")
        self.aquatic_animal_layout = QGridLayout()
        self.aquatic_animal_layout.addWidget(available_aquatic_animal_label, 0, 0)
        self.aquatic_animal_layout.addWidget(self.available_aquatic_animal_listwidget, 1, 0)
        self.aquatic_animal_layout.addWidget(selected_aquatic_animal_label, 0, 1)
        self.aquatic_animal_layout.addWidget(self.selected_aquatic_animal_listwidget, 1, 1)

        # information_curve
        self.information_curve_group = QGroupBox("")
        self.information_curve_layout = QGridLayout(self.information_curve_group)
        self.information_curve_layout.addWidget(latin_name_title_label, 0, 0)
        self.information_curve_layout.addWidget(self.latin_name_label, 0, 1)
        self.information_curve_layout.addWidget(self.show_curve_pushbutton, 0, 2)
        self.information_curve_layout.addWidget(code_alternative_title_label, 1, 0)
        self.information_curve_layout.addWidget(self.code_alternative_label, 1, 1)
        self.information_curve_layout.addWidget(self.hydrosignature_pushbutton, 1, 2)
        self.information_curve_layout.addWidget(description_title_label, 2, 0)
        self.information_curve_layout.addWidget(self.description_textedit, 2, 1)
        self.information_curve_layout.addWidget(self.animal_picture_label, 2, 2)

        """ GENERAL """
        # tools frame
        tools_frame = QFrame()
        tools_frame.setFrameShape(QFrame.NoFrame)
        tools_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout(self)
        global_layout.addLayout(self.aquatic_animal_layout)
        global_layout.addWidget(self.information_curve_group)
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)

    def get_selection_user(self, selection_dict):
        self.selection_dict = selection_dict

    def fill_available_aquatic_animal(self, biological_models_dict_gui):
        # get data
        self.biological_models_dict_gui = biological_models_dict_gui

        # line name
        for code_alternative in self.selection_dict["code_alternative"]:
            for stage in self.selection_dict["stage_and_size"]:
                self.biological_models_dict_gui["latin_name"][0]



        #
        self.available_aquatic_animal_listwidget


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
                    self.code_alternative_label.setText(data.text)

        # get the latin name
        data = root.find('.//LatinName')
        if data is not None:
            self.latin_name_label.setText(data.text)

        # get the description
        data = root.findall('.//Description')
        if len(data) > 0:
            found = False
            for d in data:
                if d.attrib['Language'] == self.lang:
                    self.description_textedit.setText(d.text[2:-1])
                    found = True
            if not found:
                self.description_textedit.setText(data[0].text[2:-1])

        # get the image fish
        data = root.find('.//Image')
        if data is not None:
            self.imfish = os.path.join(os.getcwd(), self.path_im_bio, data.text)
            name_imhere = os.path.join(os.getcwd(), self.path_im_bio, data.text)
            if os.path.isfile(name_imhere):
                # use full ABSOLUTE path to the image, not relative
                self.animal_picture_label.setPixmap(QPixmap(name_imhere).scaled(200, 90, Qt.KeepAspectRatio))  # 800 500
            else:
                self.animal_picture_label.clear()
        else:
            self.animal_picture_label.clear()

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
