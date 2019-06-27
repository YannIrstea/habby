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
from multiprocessing import Process, Value

import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtWidgets import QPushButton, QLabel, QGroupBox, QVBoxLayout, QListWidget, QHBoxLayout, QGridLayout, \
    QMessageBox, QTabWidget, \
    QAbstractItemView, \
    QSizePolicy, QScrollArea, QFrame, QDialog, QTextEdit
from subprocess import call
from platform import system as operatingsystem

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from src import bio_info_mod
from src import plot_mod
from src_GUI import preferences_GUI
from src.config_data_habby_mod import CONFIG_HABBY
from src_GUI.data_explorer_GUI import MyProcessList
from src.bio_info_mod import get_name_stage_codebio_fromstr


class BioModelExplorerWindow(QDialog):
    """
    This class contain the window Biological model selector (QDialog) which contain two tabs.
    """
    send_log = pyqtSignal(str, name='send_log')
    send_fill = pyqtSignal(str, name='send_fill')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, parent, path_prj, name_prj, name_icon, plot_process_list):
        super().__init__(parent)
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_icon = name_icon
        self.msg2 = QMessageBox()
        self.path_bio = CONFIG_HABBY.path_bio
        self.plot_process_list = plot_process_list
        # filters index

        # tabs
        self.bio_model_filter_tab = BioModelFilterTab(path_prj, name_prj)
        self.bio_model_infoselection_tab = BioModelInfoSelection(path_prj, name_prj, plot_process_list)
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.bio_model_filter_tab, self.tr("Model filter"))
        self.tab_widget.addTab(self.bio_model_infoselection_tab, self.tr("Model selection"))

        self.tab_widget.currentChanged.connect(self.load_model_selected_to_available)

        self.setGeometry(60, 95, 800, 600)

        general_layout = QVBoxLayout(self)
        general_layout.addWidget(self.tab_widget)
        self.setWindowTitle(self.tr("Biological model selector"))
        self.setWindowIcon(QIcon(self.name_icon))

    def open_bio_model_explorer(self, source_str):
        # source
        self.source_str = source_str

        # load dicoselect in xml project
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        doc = ET.parse(fname)
        root = doc.getroot()
        # geo data
        child1 = root.find('.//Bio_model_explorer_selection')
        if CONFIG_HABBY.modified:
            self.send_log.emit("Warning: Biological models database has been modified. \n" + CONFIG_HABBY.diff_list)
        if child1 is None or CONFIG_HABBY.modified:
            self.bio_model_filter_tab.create_dico_select()
            self.bio_model_infoselection_tab.dicoselect = self.bio_model_filter_tab.dicoselect
        else:
            self.bio_model_filter_tab.dicoselect = eval(child1.text)
            self.bio_model_filter_tab.dicoselect["selected"] = np.array(self.bio_model_filter_tab.dicoselect["selected"])
            self.bio_model_infoselection_tab.dicoselect = self.bio_model_filter_tab.dicoselect

        # mainwindow
        mainwindow_center = self.nativeParentWidget().geometry().center()

        self.setGeometry(60, 95, 800, 600)
        rect_geom = self.frameGeometry()
        rect_geom.moveCenter(mainwindow_center)
        self.move(rect_geom.topLeft())
        # fill_first_time
        self.bio_model_filter_tab.fill_first_time()
        self.show()

    def load_model_selected_to_available(self):
        if self.tab_widget.currentIndex() == 1:  # model selected tab
            dicoselect = self.bio_model_filter_tab.dicoselect
            biological_models_dict_gui = self.bio_model_filter_tab.biological_models_dict_gui
            self.bio_model_infoselection_tab.dicoselect = dicoselect
            self.bio_model_infoselection_tab.biological_models_dict_gui = biological_models_dict_gui
            self.bio_model_infoselection_tab.fill_available_aquatic_animal()

    def closeEvent(self, *args, **kwargs):
        self.bio_model_infoselection_tab.quit_biological_model_explorer()

    def showEvent(self, QShowEvent):
        self.load_model_selected_to_available()


class BioModelFilterTab(QScrollArea):
    """
    This class contain first tab (Model filter).
    """
    send_log = pyqtSignal(str, name='send_log')
    send_selection = pyqtSignal(object, name='send_selection')
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
        #self.create_dico_select()
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
        # country
        country_label = QLabel(self.tr("Country"))
        self.country_listwidget = QListWidget()
        self.country_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][0])
        self.country_listwidget.itemSelectionChanged.connect(self.result_from_selected)
        # aquatic_animal_type
        aquatic_animal_type_label = QLabel(self.tr("Aquatic animal type"))
        self.aquatic_animal_type_listwidget = QListWidget()
        self.aquatic_animal_type_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][1])
        self.aquatic_animal_type_listwidget.itemSelectionChanged.connect(self.result_from_selected)
        # model_type
        model_type_label = QLabel(self.tr("Model type"))
        self.model_type_listwidget = QListWidget()
        self.model_type_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][2])
        self.model_type_listwidget.itemSelectionChanged.connect(self.result_from_selected)
        # stage_and_size
        stage_and_size_label = QLabel(self.tr("Stage and size"))
        self.stage_and_size_listwidget = QListWidget()
        self.stage_and_size_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][3])
        self.stage_and_size_listwidget.itemSelectionChanged.connect(self.result_from_selected)
        # guild
        guild_label = QLabel(self.tr("Guild"))
        self.guild_listwidget = QListWidget()
        self.guild_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][4])
        self.guild_listwidget.itemSelectionChanged.connect(self.result_from_selected)
        # origine
        xml_origine_label = QLabel(self.tr("Origine"))
        self.xml_origine_listwidget = QListWidget()
        self.xml_origine_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][5])
        self.xml_origine_listwidget.itemSelectionChanged.connect(self.result_from_selected)
        # made_by
        made_by_label = QLabel(self.tr("Made by"))
        self.made_by_listwidget = QListWidget()
        self.made_by_listwidget.setObjectName(self.biological_models_dict_gui["orderedKeys"][6])
        self.made_by_listwidget.itemSelectionChanged.connect(self.result_from_selected)

        # fish_code_alternative
        fish_code_alternative_label = QLabel(self.tr("Fish"))
        self.fish_code_alternative_listwidget = QListWidget()
        self.fish_code_alternative_listwidget.setObjectName("fish_code_alternative")
        self.fish_code_alternative_listwidget.itemSelectionChanged.connect(self.result_from_selected_dispatch)

        # invertebrate
        inv_code_alternative_label = QLabel("Invertebrate")
        self.inv_code_alternative_listwidget = QListWidget()
        self.inv_code_alternative_listwidget.setObjectName("inv_code_alternative")
        self.inv_code_alternative_listwidget.itemSelectionChanged.connect(self.result_from_selected_dispatch)

        # filters_list_widget
        self.filters_list_widget = [self.country_listwidget, self.aquatic_animal_type_listwidget,
                                    self.model_type_listwidget,
                                    self.stage_and_size_listwidget, self.guild_listwidget, self.xml_origine_listwidget,
                                    self.made_by_listwidget, self.fish_code_alternative_listwidget,
                                    self.inv_code_alternative_listwidget]
        [filter_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection) for filter_listwidget in
         self.filters_list_widget]

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
        self.last_filter_group = QGroupBox(self.tr("Code alternative filter"))
        self.last_filter_layout = QGridLayout(self.last_filter_group)
        self.last_filter_layout.addWidget(fish_code_alternative_label, 0, 0)
        self.last_filter_layout.addWidget(self.fish_code_alternative_listwidget, 1, 0)
        self.last_filter_layout.addWidget(inv_code_alternative_label, 0, 1)
        self.last_filter_layout.addWidget(self.inv_code_alternative_listwidget, 1, 1)

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

    def create_dico_select(self):
        print("create_dico_select")
        self.dicoselect = dict()
        for i, ky in enumerate(self.biological_models_dict_gui['orderedKeys']):
            # print(ky)
            if self.biological_models_dict_gui['orderedKeysmultilist'][i]:
                s1 = sorted({x for l in self.biological_models_dict_gui[ky] for x in l})
            else:
                s1 = sorted(set(self.biological_models_dict_gui[ky]))
            s2 = [True] * len(s1)
            self.dicoselect[ky] = [s1, s2, True]
        self.dicoselect[self.biological_models_dict_gui['orderedKeys'][0]][2] = True
        # dispatching 'code_alternative' into 'fish_code_alternative' and 'inv_code_alternative'
        lkyf, lkyi = [], []
        for i, item in enumerate(self.biological_models_dict_gui['code_alternative']):
            if self.biological_models_dict_gui['aquatic_animal_type'][i] == 'fish':
                lkyf.append(item)
            else:
                lkyi.append(item)
        skyf = sorted({x for l in lkyf for x in l})
        skyi = sorted({x for l in lkyi for x in l})
        self.dicoselect['fish_code_alternative'] = [skyf, [True] * len(skyf), True]
        self.dicoselect['inv_code_alternative'] = [skyi, [True] * len(skyi), True]
        self.dicoselect['selected'] = np.ones((len(self.biological_models_dict_gui['country']),), dtype=bool)

    def fill_first_time(self):
        """
        this function build or rebuild the view of the biological models selected from the dicoselect  and
        biological_models_dict_gui dictionnaries
        """
        # clean
        self.clear_filter(True)
        self.clear_filter_dispatch(True)

        # fill
        bio_models_selected = np.ones((len(self.dicoselect['selected']),), dtype=bool)
        for i, ky in enumerate(self.biological_models_dict_gui['orderedKeys']):
            if not self.dicoselect[ky][2]:
                return
            listwidget = eval("self." + ky + "_listwidget")
            listwidget.blockSignals(True)
            if ky == 'country':
                for itemx in self.dicoselect[ky][0]:
                    listwidget.addItem(itemx)
            lky = set()
            for index in range(listwidget.count()):
                ii = self.dicoselect[ky][0].index(listwidget.item(index).text())
                if self.dicoselect[ky][1][ii]:
                    listwidget.item(index).setSelected(True)
                    lky.add(self.dicoselect[ky][0][ii])
            listwidget.blockSignals(False)
            if self.biological_models_dict_gui['orderedKeysmultilist'][i]:  # if multi
                sky = [len(lky & set(x)) != 0 for x in self.biological_models_dict_gui[ky]]
            else:  # if solo
                sky = [x in lky for x in self.biological_models_dict_gui[ky]]
            bio_models_selected = np.logical_and(bio_models_selected, np.array(sky))
            if i < len(self.biological_models_dict_gui['orderedKeys']) - 1:  # the before last key
                kynext = self.biological_models_dict_gui['orderedKeys'][i + 1]
                sp = [x for x, y in zip(self.biological_models_dict_gui[kynext], list(bio_models_selected)) if y]
                if self.biological_models_dict_gui['orderedKeysmultilist'][i + 1]:
                    sp = {x for y in sp for x in y}
                else:
                    sp = set(sp)
                listwidget = eval("self." + kynext + "_listwidget")
                listwidget.blockSignals(True)
                for item in self.dicoselect[kynext][0]:
                    if item in sp:
                        listwidget.addItem(item)
                listwidget.blockSignals(False)
        sp = [x for x, y in zip(self.biological_models_dict_gui['code_alternative'],
                                list(bio_models_selected)) if y]
        sp = {x for y in sp for x in y}

        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            if self.dicoselect[kyi][2]:
                listwidget = eval("self." + kyi + "_listwidget")
                listwidget.blockSignals(True)
                inditem = -1
                for ind, item in enumerate(self.dicoselect[kyi][0]):
                    if item in sp:
                        listwidget.addItem(item)
                        inditem += 1
                        if self.dicoselect[kyi][1][ind]:
                            listwidget.item(inditem).setSelected(True)
                listwidget.blockSignals(False)
        return

    def clear_filter(self, first_time=False):
        """
        clearing 'fish_code_alternative' and 'inv_code_alternative' associated listwidgets
        """
        for kyi in self.biological_models_dict_gui['orderedKeys']:
            listwidget = eval("self." + kyi + "_listwidget")
            if not first_time:
                self.dicoselect[kyi][2] = False  # all subkeys are off
            if listwidget.count() != 0:
                listwidget.blockSignals(True)
                listwidget.clear()
                listwidget.blockSignals(False)

    def result_from_selected(self):
        """
        building the view selection of biological models
        after selection in a 'regular' ' key/filter/listwidgets
        determining  the biological_models_dict_gui['selected']
        """
        ky = self.sender().objectName()
        # get selected
        listwidget = self.sender()
        selection = listwidget.selectedItems()

        actual_key_ind = self.biological_models_dict_gui['orderedKeys'].index(ky)
        next_key_ind = actual_key_ind + 1
        if selection:
            # selected_values_list
            lky = {selection_item.text() for selection_item in selection}
            self.dicoselect[ky][1] = [x in lky for x in self.dicoselect[ky][0]]
        else:
            self.dicoselect[ky][1] = [False]*len(self.dicoselect[ky][1])
        self.dicoselect['selected'] = np.ones((len(self.dicoselect['selected']),),
                                                              dtype=bool)
        for iky in range(next_key_ind):
            kyi = self.biological_models_dict_gui['orderedKeys'][iky]
            lky = {x for x, y in zip(self.dicoselect[kyi][0], self.dicoselect[kyi][1]) if y}
            if self.biological_models_dict_gui['orderedKeysmultilist'][iky]:  # if multi
                sky = [len(lky & set(x)) != 0 for x in self.biological_models_dict_gui[kyi]]
            else:  # if solo
                sky = [x in lky for x in self.biological_models_dict_gui[kyi]]
            self.dicoselect['selected'] = np.logical_and(self.dicoselect['selected'],
                                                                         np.array(sky))
            self.dicoselect[kyi][2] = True
        if next_key_ind != len(self.biological_models_dict_gui['orderedKeys']):
            for indice in range(next_key_ind, len(self.biological_models_dict_gui['orderedKeys'])):
                # print("loop key", self.biological_models_dict_gui['orderedKeys'][indice])
                listwidget = eval("self." + self.biological_models_dict_gui['orderedKeys'][indice] + "_listwidget")
                self.dicoselect[self.biological_models_dict_gui['orderedKeys'][indice]][
                    2] = False  # all subkeys are off
                if listwidget.count() != 0:
                    listwidget.blockSignals(True)
                    listwidget.clear()
                    listwidget.blockSignals(False)
                    # print("clear", self.biological_models_dict_gui['orderedKeys'][indice], listwidget.objectName())
            self.clear_filter_dispatch()
            if selection:
                self.result_to_selected(self.biological_models_dict_gui['orderedKeys'][next_key_ind])
        else:
            if selection:
                self.clear_filter_dispatch()
                self.result_to_selected_dispatch()
            else:
                self.clear_filter_dispatch()
        if ky == "country" and not selection:
            self.dicoselect['selected'] = np.zeros((len(self.dicoselect['selected']),),
                                                                   dtype=bool)

    def result_to_selected(self, ky):
        """
        building the view selection of biological models
        after selection adding items in the following key
        :param ky: a dictionnary key belonging both to biological_models_dict_gui and dicoselect dictionnaries and used to name listwidget associated
        """
        # print("result_to_selected", ky)
        sp = [x for x, y in zip(self.biological_models_dict_gui[ky], list(self.dicoselect['selected']))
              if y]
        if self.biological_models_dict_gui['orderedKeysmultilist'][
            self.biological_models_dict_gui['orderedKeys'].index(ky)]:
            sp = {x for y in sp for x in y}
        else:
            sp = set(sp)
        # print(sp)
        self.dicoselect[ky][1] = [x in sp for x in self.dicoselect[ky][0]]
        self.dicoselect[ky][2] = False  # the key is off
        # print(self.DicoSelect)
        # display
        listwidget = eval("self." + ky + "_listwidget")
        for ind, bo in enumerate(self.dicoselect[ky][1]):
            if bo:
                listwidget.addItem(self.dicoselect[ky][0][ind])
        listwidget.selectAll()

    def clear_filter_dispatch(self, first_time=False):
        """
        clearing 'fish_code_alternative' and 'inv_code_alternative' associated listwidgets
        """
        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            listwidget = eval("self." + kyi + "_listwidget")
            if not first_time:
                self.dicoselect[kyi][2] = False  # all subkeys are off
            if listwidget.count() != 0:
                listwidget.blockSignals(True)
                listwidget.clear()
                listwidget.blockSignals(False)

    def result_from_selected_dispatch(self):
        """
        building the view selection of biological models
        after selection in the ' key/filter 'fish_code_alternative' or 'inv_code_alternative' key/listwidgets
        determining  the biological_models_dict_gui['selected']
        """
        ky = self.sender().objectName()  # 'fish_code_alternative' or 'inv_code_alternative']:
        listwidget = self.sender()
        selection = listwidget.selectedItems()
        self.dicoselect['selected'] = np.ones((len(self.dicoselect['selected']),),
                                                              dtype=bool)
        for iky in range(len(self.biological_models_dict_gui['orderedKeys'])):
            kyi = self.biological_models_dict_gui['orderedKeys'][iky]
            lky = {x for x, y in zip(self.dicoselect[kyi][0], self.dicoselect[kyi][1]) if y}
            if self.biological_models_dict_gui['orderedKeysmultilist'][iky]:  # if multi
                sky = [len(lky & set(x)) != 0 for x in self.biological_models_dict_gui[kyi]]
            else:  # if solo
                sky = [x in lky for x in self.biological_models_dict_gui[kyi]]
            self.dicoselect['selected'] = np.logical_and(self.dicoselect['selected'],
                                                                         np.array(sky))
            self.dicoselect[kyi][2] = True
        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            if kyi != ky:
                lkyi = {x for x, y in zip(self.dicoselect[kyi][0], self.dicoselect[kyi][1]) if y}
                skyi = [len(lkyi & set(x)) != 0 for x in self.biological_models_dict_gui['code_alternative']]
        lkyj = {selection_item.text() for selection_item in selection}
        self.dicoselect[ky][1] = [x in lkyj for x in self.dicoselect[ky][0]]
        skyj = [len(lkyj & set(x)) != 0 for x in self.biological_models_dict_gui['code_alternative']]
        askyj = np.logical_or(np.array(skyi), np.array(skyj))
        self.dicoselect['selected'] = np.logical_and(self.dicoselect['selected'], askyj)
        self.dicoselect[ky][2] = True

    def result_to_selected_dispatch(self):
        """
        building the view selection of biological models
        after selection in the last 'regular' key/filter adding items in 'fish_code_alternative','inv_code_alternative' key/listwidgets
        :return:
        """
        sp = [x for x, y in zip(self.biological_models_dict_gui['code_alternative'],
                                list(self.dicoselect['selected']))
              if y]
        sp = {x for y in sp for x in y}
        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            self.dicoselect[kyi][1] = [x in sp for x in self.dicoselect[kyi][0]]
            self.dicoselect[kyi][2] = False  # the key is off
            listwidget = eval("self." + kyi + "_listwidget")
            for ind, bo in enumerate(self.dicoselect[kyi][1]):
                if bo:
                    listwidget.addItem(self.dicoselect[kyi][0][ind])
            listwidget.selectAll()


class BioModelInfoSelection(QScrollArea):
    """
    This class contain second tab (Model selection).
    """
    send_log = pyqtSignal(object, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj, plot_process_list):
        super().__init__()
        self.tab_name = "model_selected"
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.plot_process_list = plot_process_list
        self.selected_fish_cd_biological_model = None
        self.selected_aquatic_animal_list = []
        self.msg2 = QMessageBox()
        self.init_iu()
        self.lang = 0

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
        self.available_aquatic_animal_label = QLabel(self.tr("Available models") + " (0)")
        self.available_aquatic_animal_listwidget = QListWidget()
        self.available_aquatic_animal_listwidget.setObjectName("available_aquatic_animal")
        self.available_aquatic_animal_listwidget.itemSelectionChanged.connect(lambda: self.show_info_fish("available"))
        #self.available_aquatic_animal_listwidget.itemDoubleClicked.connect(self.add_fish)
        self.available_aquatic_animal_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.available_aquatic_animal_listwidget.setDragDropMode(QAbstractItemView.DragDrop)
        self.available_aquatic_animal_listwidget.setDefaultDropAction(Qt.MoveAction)
        self.available_aquatic_animal_listwidget.setAcceptDrops(True)
        self.available_aquatic_animal_listwidget.setSortingEnabled(True)
        self.available_aquatic_animal_listwidget.model().rowsInserted.connect(self.count_models_listwidgets)
        self.available_aquatic_animal_listwidget.model().rowsRemoved.connect(self.count_models_listwidgets)


        self.selected_aquatic_animal_label = QLabel(self.tr("Selected models") + " (0)")
        self.selected_aquatic_animal_listwidget = QListWidget()
        self.selected_aquatic_animal_listwidget.setObjectName("selected_aquatic_animal")
        self.selected_aquatic_animal_listwidget.itemSelectionChanged.connect(lambda: self.show_info_fish("selected"))
        #self.selected_aquatic_animal_listwidget.itemDoubleClicked.connect(self.remove_fish)
        self.selected_aquatic_animal_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_aquatic_animal_listwidget.setDragDropMode(QAbstractItemView.DragDrop)
        self.selected_aquatic_animal_listwidget.setDefaultDropAction(Qt.MoveAction)
        self.selected_aquatic_animal_listwidget.setAcceptDrops(True)
        self.selected_aquatic_animal_listwidget.setSortingEnabled(True)
        self.selected_aquatic_animal_listwidget.model().rowsInserted.connect(self.count_models_listwidgets)
        self.selected_aquatic_animal_listwidget.model().rowsRemoved.connect(self.count_models_listwidgets)
        # self.selected_aquatic_animal_qtablewidget.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # latin_name
        latin_name_title_label = QLabel(self.tr('Latin Name: '))
        self.latin_name_label = QLabel("")
        # show_curve
        self.show_curve_pushbutton = QPushButton(self.tr('Show suitability curve'))
        self.show_curve_pushbutton.clicked.connect(self.show_pref)
        # code_alternative
        code_alternative_title_label = QLabel(self.tr('Code alternative:'))
        self.code_alternative_label = QLabel("")
        # hydrosignature
        self.hydrosignature_pushbutton = QPushButton(self.tr('Show Measurement Conditions (Hydrosignature)'))
        self.hydrosignature_pushbutton.clicked.connect(self.show_hydrosignature)
        # description
        description_title_label = QLabel(self.tr('Description:'))
        description_title_label.setAlignment(Qt.AlignTop)
        self.description_textedit = QTextEdit(self)  # where the log is show
        self.description_textedit.setFrameShape(QFrame.NoFrame)
        self.description_textedit.setReadOnly(True)
        # image fish
        self.animal_picture_label = ClickLabel()
        self.animal_picture_label.setStyleSheet("QLabel { background-color : white; color : black; }");
        # self.animal_picture_label.setFrameShape(QFrame.Panel)
        self.animal_picture_label.setAlignment(Qt.AlignCenter)
        self.animal_picture_label.clicked.connect(self.open_explorer_on_picture_path)

        # add
        self.add_selected_to_main_pushbutton = QPushButton(self.tr("Validate selected models"))
        self.add_selected_to_main_pushbutton.clicked.connect(self.add_selected_to_main)

        # quit
        self.quit_biological_model_explorer_pushbutton = QPushButton(self.tr("Close"))
        self.quit_biological_model_explorer_pushbutton.clicked.connect(self.quit_biological_model_explorer)

        """ GROUP ET LAYOUT """
        # aquatic_animal
        self.aquatic_animal_layout = QGridLayout()
        self.aquatic_animal_layout.addWidget(self.available_aquatic_animal_label, 0, 0)
        self.aquatic_animal_layout.addWidget(self.available_aquatic_animal_listwidget, 1, 0)
        self.aquatic_animal_layout.addWidget(self.selected_aquatic_animal_label, 0, 1)
        self.aquatic_animal_layout.addWidget(self.selected_aquatic_animal_listwidget, 1, 1)

        # information_curve
        self.information_curve_group = QGroupBox("Suitability curve information")
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

        # valid_close_layout
        valid_close_layout = QHBoxLayout()
        valid_close_layout.setAlignment(Qt.AlignRight)
        valid_close_layout.addWidget(self.add_selected_to_main_pushbutton)
        valid_close_layout.addWidget(self.quit_biological_model_explorer_pushbutton)

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
        global_layout.addLayout(valid_close_layout)
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)

    def fill_available_aquatic_animal(self):
        self.available_aquatic_animal_listwidget.clear()
        self.selected_aquatic_animal_listwidget.clear()
        # line name
        item_list = []
        for selected_xml_ind, selected_xml_tf in enumerate(self.dicoselect["selected"]):
            if selected_xml_tf:
                for selected_stage_ind, selected_stage_tf in enumerate(self.dicoselect["stage_and_size"][1]):
                    if selected_stage_tf:
                        stage_wish = self.dicoselect["stage_and_size"][0][selected_stage_ind]
                        if stage_wish in self.biological_models_dict_gui["stage_and_size"][selected_xml_ind]:
                            item_list.append(self.biological_models_dict_gui["latin_name"][selected_xml_ind] + ": " +
                                             self.dicoselect["stage_and_size"][0][selected_stage_ind] + " - " +
                                             self.biological_models_dict_gui["cd_biological_model"][selected_xml_ind])

        self.available_aquatic_animal_listwidget.model().blockSignals(True)
        self.available_aquatic_animal_listwidget.addItems(item_list)
        self.available_aquatic_animal_listwidget.model().blockSignals(False)
        # change qlabel
        self.available_aquatic_animal_label.setText(self.tr("Available models") + " (" + str(len(item_list)) + ")")
        self.selected_aquatic_animal_label.setText(self.tr("Selected models") + " (0)")

    def count_models_listwidgets(self):
        """
        method to count total number of models in twice listwidgets. Sort is automatic but not apply when dra/drop in same listwidget.
        """
        self.available_aquatic_animal_label.setText(self.tr("Available models") + " (" + str(self.available_aquatic_animal_listwidget.count()) + ")")
        self.selected_aquatic_animal_label.setText(self.tr("Selected models") + " (" + str(self.selected_aquatic_animal_listwidget.count()) + ")")

    def remove_fish(self):
        """
        The function is used to remove fish species (or inverterbates species)
        """
        # remove it from available
        item = self.selected_aquatic_animal_listwidget.takeItem(self.selected_aquatic_animal_listwidget.currentRow())
        # remove it from list
        self.selected_aquatic_animal_list.pop(self.selected_aquatic_animal_list.index(item.text()))

        # clear selection
        self.selected_aquatic_animal_listwidget.clearSelection()

        # create normal font
        font = QFont()
        font.setBold(False)

        # identify which one and remove bold
        for item_index in range(self.available_aquatic_animal_listwidget.count()):
            item_loop = self.available_aquatic_animal_listwidget.item(item_index)
            if item_loop.text() == item.text():
                item_loop.setFont(font)
        # change qlabel
        self.selected_aquatic_animal_label.setText(self.tr("Selected models") + " (" + str(len(self.selected_aquatic_animal_list)) + ")")

    def show_info_fish(self, listwidget_source):
        """
        This function shows the useful information concerning the selected fish on the GUI.

        :param select:If False, the selected items comes from the QListWidgetcontaining the available fish.
                      If True, the items comes the QListWidget with the selected fish
        """

        listwidget = eval("self." + listwidget_source + "_aquatic_animal_listwidget")

        # get the file
        i1 = listwidget.currentItem()  # show the info concerning the one selected fish
        if not i1:
            return

        self.selected_fish_cd_biological_model = i1.text()
        self.selected_fish_cd_biological_model = self.selected_fish_cd_biological_model.split(' - ')[-1]
        i = self.biological_models_dict_gui["cd_biological_model"].index(self.selected_fish_cd_biological_model)

        xmlfile = self.biological_models_dict_gui["path_xml"][i]
        img_file = self.biological_models_dict_gui["path_img"][i]

        # from dict
        self.code_alternative_label.setText(self.biological_models_dict_gui["code_alternative"][i][0])
        self.latin_name_label.setText(self.biological_models_dict_gui["latin_name"][i])

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

        # get the description from xml
        data = root.findall('.//Description')
        if len(data) > 0:
            found = False
            for d in data:
                if d.attrib['Language'] == self.lang:
                    self.description_textedit.setText(d.text[2:-1])
                    found = True
            if not found:
                self.description_textedit.setText(data[0].text[2:-1])

        if img_file:
            if os.path.isfile(img_file):
                self.animal_picture_label.clear()
                self.animal_picture_label.setPixmap(QPixmap(img_file).scaled(self.animal_picture_label.size() * 0.95,
                                                                            Qt.KeepAspectRatio))  # 800 500  # .scaled(self.animal_picture_label.size(), Qt.KeepAspectRatio)
                self.animal_picture_path = img_file
            else:
                self.animal_picture_label.clear()
                self.animal_picture_label.setText(self.tr("no image file"))
                self.animal_picture_path = None
        else:
            self.animal_picture_label.clear()
            self.animal_picture_label.setText(self.tr("no image file"))
            self.animal_picture_path = None

    def open_explorer_on_picture_path(self):
        if self.animal_picture_path:
            path_choosen = os.path.normpath(self.animal_picture_path)

            if operatingsystem() == 'Windows':
                call(['explorer', path_choosen])
            elif operatingsystem() == 'Linux':
                call(["xdg-open", path_choosen])
            elif operatingsystem() == 'Darwin':
                call(['open', path_choosen])

    def show_pref(self):
        """
        This function shows the image of the preference curve of the selected xml file. For this it calls, the functions
        read_pref and figure_pref of bio_info_mod.py. Hence, this function justs makes the link between the GUI and
        the functions effectively doing the image.
        """

        if not self.selected_fish_cd_biological_model:
            self.send_log.emit("Warning: No fish selected to create suitability curves.")
            return

        # get the file
        i = self.biological_models_dict_gui["cd_biological_model"].index(self.selected_fish_cd_biological_model)
        xmlfile = self.biological_models_dict_gui["path_xml"][i]

        # open the pref
        [h_all, vel_all, sub_all, code_fish, name_fish, stages] = bio_info_mod.read_pref(xmlfile)
        # plot the pref
        project_preferences = preferences_GUI.load_project_preferences(self.path_prj, self.name_prj)
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
                                      project_preferences))
        self.plot_process_list.append((curve_process, state))

    def show_hydrosignature(self):
        """
        This function make the link with function in bio_info_mod.py which allows to load and plot the data related
        to the hydrosignature.
        """

        if not self.selected_fish_cd_biological_model:
            self.send_log.emit("Warning: No fish selected to hydrosignature.")
            return

        # get the file
        i = self.biological_models_dict_gui["cd_biological_model"].index(self.selected_fish_cd_biological_model)
        fishname = self.biological_models_dict_gui["latin_name"][i]
        xmlfile = self.biological_models_dict_gui["path_xml"][i]

        # get data
        data = bio_info_mod.get_hydrosignature(xmlfile)
        if isinstance(data, np.ndarray):
            # do the plot
            if not hasattr(self, 'plot_process_list'):
                self.plot_process_list = MyProcessList()
            state = Value("i", 0)
            hydrosignature_process = Process(target=plot_mod.plot_hydrosignature,
                                             args=(state,
                                                   data,
                                                   fishname))
            self.plot_process_list.append((hydrosignature_process, state))

    def add_selected_to_main(self):
        # source
        source_str = self.nativeParentWidget().source_str

        # get selected models
        selected_aquatic_animal_list = []
        hydraulic_mode_list = []
        substrate_mode_list = []
        for item_index in range(self.selected_aquatic_animal_listwidget.count()):
            new_item_to_merge = self.selected_aquatic_animal_listwidget.item(item_index).text()
            selected_aquatic_animal_list.append(new_item_to_merge)
            # get info
            name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(new_item_to_merge)
            index_fish = CONFIG_HABBY.biological_models_dict["cd_biological_model"].index(code_bio_model)
            # get stage index
            index_stage = CONFIG_HABBY.biological_models_dict["stage_and_size"][index_fish].index(stage)

            # get default_hydraulic_type
            default_hydraulic_type = CONFIG_HABBY.biological_models_dict["hydraulic_type"][index_fish][index_stage]
            hydraulic_type_available = CONFIG_HABBY.biological_models_dict["hydraulic_type_available"][index_fish][index_stage]
            hydraulic_mode_list.append(hydraulic_type_available.index(default_hydraulic_type))

            # get default_substrate_type
            default_substrate_type = CONFIG_HABBY.biological_models_dict["substrate_type"][index_fish][index_stage]
            substrate_type_available = CONFIG_HABBY.biological_models_dict["substrate_type_available"][index_fish][index_stage]
            substrate_mode_list.append(substrate_type_available.index(default_substrate_type))

        # create dict
        self.item_dict = dict(source_str=source_str,
                              selected_aquatic_animal_list=selected_aquatic_animal_list,
                              hydraulic_mode_list=hydraulic_mode_list,
                              substrate_mode_list=substrate_mode_list)

        # emit signal
        self.nativeParentWidget().send_fill.emit("")

        # close window
        self.quit_biological_model_explorer()

    def quit_biological_model_explorer(self):
        # convert one key
        dicoselect = self.dicoselect.copy()
        dicoselect["selected"] = self.dicoselect["selected"].tolist()

        # save dicoselect in xml project
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        doc = ET.parse(fname)
        root = doc.getroot()
        # geo data
        child1 = root.find('.//Bio_model_explorer_selection')
        if child1 is None:
            child1 = ET.SubElement(root, 'Bio_model_explorer_selection')
            child1.text = str(dicoselect)
        else:
            child1.text = str(dicoselect)
        doc.write(fname)
        self.parent().parent().parent().close()


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        QLabel.mousePressEvent(self, event)
