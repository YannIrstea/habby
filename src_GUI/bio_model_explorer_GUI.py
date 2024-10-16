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
import re
import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt, QEvent, QSize
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtWidgets import QPushButton, QLabel, QGroupBox, QVBoxLayout, QListWidget, QHBoxLayout, QGridLayout, \
    QMessageBox, QTabWidget, QApplication, QStatusBar,\
    QAbstractItemView, \
    QSizePolicy, QScrollArea, QFrame, QDialog, QTextEdit
from subprocess import call
from platform import system as operatingsystem

from lxml import etree as ET

from src import bio_info_mod
from src.project_properties_mod import load_project_properties, load_specific_properties, change_specific_properties
from src.user_preferences_mod import user_preferences
from src.process_manager_mod import MyProcessManager
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

    def __init__(self, parent, path_prj, name_prj, name_icon):
        super().__init__(parent)
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_icon = name_icon
        self.status_bar = QStatusBar()
        self.msg2 = QMessageBox()
        self.path_bio = user_preferences.path_bio
        # filters index

        # tabs
        self.bio_model_filter_tab = BioModelFilterTab(path_prj, name_prj, self.send_log)
        self.bio_model_filter_tab.refresh_user_bio_database_push.clicked.connect(self.refresh_user_bio_database)
        self.bio_model_infoselection_tab = BioModelInfoSelection(path_prj, name_prj, self.send_log)
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # tab_widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.bio_model_filter_tab, self.tr("Model filter"))
        self.tab_widget.addTab(self.bio_model_infoselection_tab, self.tr("Model selection"))


        # tatusTip
        self.bio_model_infoselection_tab.show_curve_pushbutton.installEventFilter(self)
        self.bio_model_infoselection_tab.hydrosignature_pushbutton.installEventFilter(self)
        self.bio_model_infoselection_tab.add_selected_to_main_pushbutton.installEventFilter(self)

        # signal
        self.tab_widget.currentChanged.connect(self.load_model_selected_to_available)

        self.general_layout = QVBoxLayout(self)
        self.general_layout.addWidget(self.tab_widget)
        self.general_layout.addWidget(self.status_bar)
        self.setGeometry(60, 95, 800, 600)
        self.setWindowTitle(self.tr("Biological model selector"))
        self.setWindowIcon(QIcon(self.name_icon))

    def open_bio_model_explorer(self, source_str):
        # source
        self.source_str = source_str

        bio_model_explorer_selection_dict = load_specific_properties(self.path_prj,
                                                                     ["bio_model_explorer_selection"])[0]

        if user_preferences.modified:
            self.bio_model_filter_tab.create_dico_select()
            self.bio_model_infoselection_tab.bio_model_explorer_selection_dict = self.bio_model_filter_tab.bio_model_explorer_selection_dict
        elif not user_preferences.modified and not bio_model_explorer_selection_dict:
            self.bio_model_filter_tab.create_dico_select()
            self.bio_model_infoselection_tab.bio_model_explorer_selection_dict = self.bio_model_filter_tab.bio_model_explorer_selection_dict
        else:
            self.bio_model_filter_tab.bio_model_explorer_selection_dict = bio_model_explorer_selection_dict
            self.bio_model_filter_tab.bio_model_explorer_selection_dict["selected"] = np.array(self.bio_model_filter_tab.bio_model_explorer_selection_dict["selected"])
            self.bio_model_infoselection_tab.bio_model_explorer_selection_dict = self.bio_model_filter_tab.bio_model_explorer_selection_dict

        # mainwindow
        mainwindow_center = self.nativeParentWidget().geometry().center()

        self.setGeometry(60, 95, 800, 600)
        rect_geom = self.frameGeometry()
        rect_geom.moveCenter(mainwindow_center)
        self.move(rect_geom.topLeft())
        # fill_first_time
        self.bio_model_filter_tab.fill_first_time()

        # if fstress
        if self.source_str == "fstress":
            # block
            self.bio_model_filter_tab.country_listwidget.selectAll()
            self.bio_model_filter_tab.country_listwidget.setEnabled(False)
            self.bio_model_filter_tab.aquatic_animal_type_listwidget.clearSelection()
            for item_num in range(self.bio_model_filter_tab.aquatic_animal_type_listwidget.count()):
                if str(self.bio_model_filter_tab.aquatic_animal_type_listwidget.item(item_num).text()) == "invertebrate":
                    self.bio_model_filter_tab.aquatic_animal_type_listwidget.item(item_num).setSelected(True)
            self.bio_model_filter_tab.aquatic_animal_type_listwidget.setEnabled(False)
        # # stat_hab
        # elif self.source_str == "stat_hab":
        #     # # block
        #     # self.bio_model_filter_tab.country_listwidget.selectAll()
        #     # self.bio_model_filter_tab.country_listwidget.setEnabled(False)
        #     # self.bio_model_filter_tab.aquatic_animal_type_listwidget.clearSelection()
        #     # for item_num in range(self.bio_model_filter_tab.aquatic_animal_type_listwidget.count()):
        #     #     if str(self.bio_model_filter_tab.aquatic_animal_type_listwidget.item(item_num).text()) == "fish":
        #     #         self.bio_model_filter_tab.aquatic_animal_type_listwidget.item(item_num).setSelected(True)
        #     # self.bio_model_filter_tab.aquatic_animal_type_listwidget.setEnabled(False)
        else:
            self.bio_model_filter_tab.country_listwidget.setEnabled(True)
            self.bio_model_filter_tab.aquatic_animal_type_listwidget.setEnabled(True)

        self.setModal(True)
        self.show()

    def load_model_selected_to_available(self):
        if self.tab_widget.currentIndex() == 0:  # model filter tab
            self.status_bar.showMessage(self.tr("Filter your models and then pass to 'Model selection' tab."))
        elif self.tab_widget.currentIndex() == 1:  # model selected tab
            bio_model_explorer_selection_dict = self.bio_model_filter_tab.bio_model_explorer_selection_dict
            biological_models_dict_gui = self.bio_model_filter_tab.biological_models_dict_gui
            self.bio_model_infoselection_tab.bio_model_explorer_selection_dict = bio_model_explorer_selection_dict
            self.bio_model_infoselection_tab.biological_models_dict_gui = biological_models_dict_gui
            self.bio_model_infoselection_tab.fill_available_aquatic_animal()
            self.status_bar.showMessage(self.tr("Select your models by drag and drop and "
                                                "then click on 'Validate selected models' button."))

    def refresh_user_bio_database(self):
        user_preferences.check_need_update_biology_models_json()
        user_preferences.format_biology_models_dict_togui()

        if user_preferences.diff_list:
            if "Error" in user_preferences.diff_list:
                self.send_log.emit(user_preferences.diff_list)
                self.send_log.emit(self.tr("The biological user models have not been changed."))
            else:
                self.send_log.emit(self.tr("Warning: ") + self.tr("User biological models ") + user_preferences.diff_list)
                self.send_log.emit(self.tr("The biological user models have been changed."))
                self.bio_model_filter_tab.biological_models_dict_gui = user_preferences.biological_models_dict.copy()
                self.bio_model_filter_tab.fill_first_time()
                self.bio_model_infoselection_tab.selected_aquatic_animal_listwidget.clear()
        else:
            self.send_log.emit(self.tr("The biological user models have not been changed."))

    def eventFilter(self, obj, event):
        '''
        Manual setStatusTip
        '''
        if event.type() == QEvent.Enter:
            # print("1", obj.statusTip(), obj.objectName())
            self.oldMessage = self.status_bar.currentMessage()
            self.status_bar.showMessage(obj.statusTip(), 0)
        elif event.type() == QEvent.Leave:
            # print("2", self.oldMessage, obj.objectName())
            self.status_bar.showMessage(self.oldMessage, 0)
            pass
        event.accept()
        return False

    def closeEvent(self, *args, **kwargs):
        self.bio_model_infoselection_tab.quit_biological_model_explorer()

    def showEvent(self, QShowEvent):
        self.load_model_selected_to_available()
        self.bio_model_infoselection_tab.add_selected_to_main_pushbutton.setFocus()


class BioModelFilterTab(QScrollArea):
    """
    This class contain first tab (Model filter).
    """
    send_selection = pyqtSignal(object, name='send_selection')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.tab_name = "model_filter"
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.msg2 = QMessageBox()
        self.biological_models_dict_gui = user_preferences.biological_models_dict.copy()
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
        inv_code_alternative_label = QLabel(self.tr("Invertebrate"))
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

        self.refresh_user_bio_database_push = QPushButton(self.tr("Refresh user biological database"))
        self.refresh_user_bio_database_push.setToolTip(self.tr("Refresh user biological models database in ") +
                                                       user_preferences.user_pref_biology_models)

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

        # pushbutton
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.refresh_user_bio_database_push)
        button_layout.setAlignment(Qt.AlignLeft)

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
        global_layout.addItem(button_layout)
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)

    def create_dico_select(self):
        # print("create_dico_select")
        self.bio_model_explorer_selection_dict = dict()
        for i, ky in enumerate(self.biological_models_dict_gui['orderedKeys']):
            # print(ky)
            if self.biological_models_dict_gui['orderedKeysmultilist'][i]:
                s1 = sorted({x for l in self.biological_models_dict_gui[ky] for x in l})
            else:
                s1 = sorted(set(self.biological_models_dict_gui[ky]))
            s2 = [True] * len(s1)
            self.bio_model_explorer_selection_dict[ky] = [s1, s2, True]
        self.bio_model_explorer_selection_dict[self.biological_models_dict_gui['orderedKeys'][0]][2] = True
        # dispatching 'code_alternative' into 'fish_code_alternative' and 'inv_code_alternative'
        lkyf, lkyi, lkyc = [], [], []
        for i, item in enumerate(self.biological_models_dict_gui['code_alternative']):
            if self.biological_models_dict_gui['aquatic_animal_type'][i] == 'fish':
                lkyf.append(item)
            if self.biological_models_dict_gui['aquatic_animal_type'][i] == 'invertebrate':
                lkyi.append(item)

        skyf = sorted({x for l in lkyf for x in l})
        skyi = sorted({x for l in lkyi for x in l})
        skyc = sorted({x for l in lkyc for x in l})
        self.bio_model_explorer_selection_dict['fish_code_alternative'] = [skyf, [True] * len(skyf), True]
        self.bio_model_explorer_selection_dict['inv_code_alternative'] = [skyi, [True] * len(skyi), True]
        self.bio_model_explorer_selection_dict['selected'] = np.ones((len(self.biological_models_dict_gui['country']),), dtype=bool)

    def fill_first_time(self):
        """
        this function build or rebuild the view of the biological models selected from the bio_model_explorer_selection_dict  and
        biological_models_dict_gui dictionnaries
        """
        # clean
        self.clear_filter(True)
        self.clear_filter_dispatch(True)

        if len(self.biological_models_dict_gui["country"]) != len(self.bio_model_explorer_selection_dict['selected']):
            self.create_dico_select()

        # fill
        bio_models_selected = np.ones((len(self.bio_model_explorer_selection_dict['selected']),), dtype=bool)
        for i, ky in enumerate(self.biological_models_dict_gui['orderedKeys']):
            if not self.bio_model_explorer_selection_dict[ky][2]:
                return
            listwidget = eval("self." + ky + "_listwidget")
            listwidget.blockSignals(True)
            if ky == 'country':
                for itemx in self.bio_model_explorer_selection_dict[ky][0]:
                    listwidget.addItem(itemx)
            lky = set()
            for index in range(listwidget.count()):
                ii = self.bio_model_explorer_selection_dict[ky][0].index(listwidget.item(index).text())
                if self.bio_model_explorer_selection_dict[ky][1][ii]:
                    listwidget.item(index).setSelected(True)
                    lky.add(self.bio_model_explorer_selection_dict[ky][0][ii])
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
                for item in self.bio_model_explorer_selection_dict[kynext][0]:
                    if item in sp:
                        listwidget.addItem(item)
                listwidget.blockSignals(False)
        sp = [x for x, y in zip(self.biological_models_dict_gui['code_alternative'],
                                list(bio_models_selected)) if y]
        sp = {x for y in sp for x in y}

        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            if self.bio_model_explorer_selection_dict[kyi][2]:
                listwidget = eval("self." + kyi + "_listwidget")
                listwidget.blockSignals(True)
                inditem = -1
                for ind, item in enumerate(self.bio_model_explorer_selection_dict[kyi][0]):
                    if item in sp:
                        listwidget.addItem(item)
                        inditem += 1
                        if self.bio_model_explorer_selection_dict[kyi][1][ind]:
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
                self.bio_model_explorer_selection_dict[kyi][2] = False  # all subkeys are off
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
            self.bio_model_explorer_selection_dict[ky][1] = [x in lky for x in self.bio_model_explorer_selection_dict[ky][0]]
        else:
            self.bio_model_explorer_selection_dict[ky][1] = [False] * len(self.bio_model_explorer_selection_dict[ky][1])
        self.bio_model_explorer_selection_dict['selected'] = np.ones((len(self.bio_model_explorer_selection_dict['selected']),),
                                                                     dtype=bool)
        for iky in range(next_key_ind):
            kyi = self.biological_models_dict_gui['orderedKeys'][iky]
            lky = {x for x, y in zip(self.bio_model_explorer_selection_dict[kyi][0], self.bio_model_explorer_selection_dict[kyi][1]) if y}
            if self.biological_models_dict_gui['orderedKeysmultilist'][iky]:  # if multi
                sky = [len(lky & set(x)) != 0 for x in self.biological_models_dict_gui[kyi]]
            else:  # if solo
                sky = [x in lky for x in self.biological_models_dict_gui[kyi]]
            self.bio_model_explorer_selection_dict['selected'] = np.logical_and(self.bio_model_explorer_selection_dict['selected'],
                                                                                np.array(sky))
            self.bio_model_explorer_selection_dict[kyi][2] = True
        if next_key_ind != len(self.biological_models_dict_gui['orderedKeys']):
            for indice in range(next_key_ind, len(self.biological_models_dict_gui['orderedKeys'])):
                # print("loop key", self.biological_models_dict_gui['orderedKeys'][indice])
                listwidget = eval("self." + self.biological_models_dict_gui['orderedKeys'][indice] + "_listwidget")
                self.bio_model_explorer_selection_dict[self.biological_models_dict_gui['orderedKeys'][indice]][
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
            self.bio_model_explorer_selection_dict['selected'] = np.zeros((len(self.bio_model_explorer_selection_dict['selected']),),
                                                                          dtype=bool)

    def result_to_selected(self, ky):
        """
        building the view selection of biological models
        after selection adding items in the following key
        :param ky: a dictionnary key belonging both to biological_models_dict_gui and bio_model_explorer_selection_dict dictionnaries and used to name listwidget associated
        """
        # print("result_to_selected", ky)
        sp = [x for x, y in zip(self.biological_models_dict_gui[ky], list(self.bio_model_explorer_selection_dict['selected']))
              if y]
        if self.biological_models_dict_gui['orderedKeysmultilist'][
            self.biological_models_dict_gui['orderedKeys'].index(ky)]:
            sp = {x for y in sp for x in y}
        else:
            sp = set(sp)
        # print(sp)
        self.bio_model_explorer_selection_dict[ky][1] = [x in sp for x in self.bio_model_explorer_selection_dict[ky][0]]
        self.bio_model_explorer_selection_dict[ky][2] = False  # the key is off
        # print(self.DicoSelect)
        # display
        listwidget = eval("self." + ky + "_listwidget")
        for ind, bo in enumerate(self.bio_model_explorer_selection_dict[ky][1]):
            if bo:
                listwidget.addItem(self.bio_model_explorer_selection_dict[ky][0][ind])
        listwidget.selectAll()

    def clear_filter_dispatch(self, first_time=False):
        """
        clearing 'fish_code_alternative' and 'inv_code_alternative' associated listwidgets
        """
        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            listwidget = eval("self." + kyi + "_listwidget")
            if not first_time:
                self.bio_model_explorer_selection_dict[kyi][2] = False  # all subkeys are off
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
        ky = self.sender().objectName()  # 'fish_code_alternative' or 'inv_code_alternative':
        listwidget = self.sender()
        selection = listwidget.selectedItems()
        self.bio_model_explorer_selection_dict['selected'] = np.ones((len(self.bio_model_explorer_selection_dict['selected']),),
                                                                     dtype=bool)
        for iky in range(len(self.biological_models_dict_gui['orderedKeys'])):
            kyi = self.biological_models_dict_gui['orderedKeys'][iky]
            lky = {x for x, y in zip(self.bio_model_explorer_selection_dict[kyi][0], self.bio_model_explorer_selection_dict[kyi][1]) if y}
            if self.biological_models_dict_gui['orderedKeysmultilist'][iky]:  # if multi
                sky = [len(lky & set(x)) != 0 for x in self.biological_models_dict_gui[kyi]]
            else:  # if solo
                sky = [x in lky for x in self.biological_models_dict_gui[kyi]]
            self.bio_model_explorer_selection_dict['selected'] = np.logical_and(self.bio_model_explorer_selection_dict['selected'],
                                                                                np.array(sky))
            self.bio_model_explorer_selection_dict[kyi][2] = True
        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            if kyi != ky:
                lkyi = {x for x, y in zip(self.bio_model_explorer_selection_dict[kyi][0], self.bio_model_explorer_selection_dict[kyi][1]) if y}
                skyi = [len(lkyi & set(x)) != 0 for x in self.biological_models_dict_gui['code_alternative']]
        lkyj = {selection_item.text() for selection_item in selection}
        self.bio_model_explorer_selection_dict[ky][1] = [x in lkyj for x in self.bio_model_explorer_selection_dict[ky][0]]
        skyj = [len(lkyj & set(x)) != 0 for x in self.biological_models_dict_gui['code_alternative']]
        askyj = np.logical_or(np.array(skyi), np.array(skyj))
        self.bio_model_explorer_selection_dict['selected'] = np.logical_and(self.bio_model_explorer_selection_dict['selected'], askyj)
        self.bio_model_explorer_selection_dict[ky][2] = True

    def result_to_selected_dispatch(self):
        """
        building the view selection of biological models
        after selection in the last 'regular' key/filter adding items in 'fish_code_alternative','inv_code_alternative' key/listwidgets
        :return:
        """
        sp = [x for x, y in zip(self.biological_models_dict_gui['code_alternative'],
                                list(self.bio_model_explorer_selection_dict['selected']))
              if y]
        sp = {x for y in sp for x in y}
        for kyi in ['fish_code_alternative', 'inv_code_alternative']:
            self.bio_model_explorer_selection_dict[kyi][1] = [x in sp for x in self.bio_model_explorer_selection_dict[kyi][0]]
            self.bio_model_explorer_selection_dict[kyi][2] = False  # the key is off
            listwidget = eval("self." + kyi + "_listwidget")
            for ind, bo in enumerate(self.bio_model_explorer_selection_dict[kyi][1]):
                if bo:
                    listwidget.addItem(self.bio_model_explorer_selection_dict[kyi][0][ind])
            listwidget.selectAll()


class BioModelInfoSelection(QScrollArea):
    """
    This class contain second tab (Model selection).
    """
    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.tab_name = "model_selected"
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.selected_fish_code_biological_model = None
        self.selected_aquatic_animal_list = []
        self.msg2 = QMessageBox()
        self.init_iu()
        self.lang = 0
        self.animal_picture_path = None
        self.process_manager_sc_plot = MyProcessManager("sc_plot")  # SC (Suitability Curve)
        self.process_manager_sc_hs_plot = MyProcessManager("sc_hs_plot")  # SC (Suitability Curve)

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
        self.available_aquatic_animal_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.available_aquatic_animal_listwidget.setDragDropMode(QAbstractItemView.DragOnly)
        self.available_aquatic_animal_listwidget.setSortingEnabled(True)

        # arrow available to selected
        self.arrow = QLabel()
        self.arrow.setPixmap(QPixmap(os.path.join(os.getcwd(), "file_dep", "icon", "triangle_black_closed_50_50.png")).copy(20, 0, 16, 50))

        self.selected_aquatic_animal_label = QLabel(self.tr("Selected models") + " (0)")
        self.selected_aquatic_animal_listwidget = QListWidget()
        self.selected_aquatic_animal_listwidget.setObjectName("selected_aquatic_animal")
        self.selected_aquatic_animal_listwidget.itemSelectionChanged.connect(lambda: self.show_info_fish("selected"))
        self.selected_aquatic_animal_listwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_aquatic_animal_listwidget.setDragDropMode(QAbstractItemView.DropOnly)
        self.selected_aquatic_animal_listwidget.setDefaultDropAction(Qt.MoveAction)
        self.selected_aquatic_animal_listwidget.setAcceptDrops(True)
        self.selected_aquatic_animal_listwidget.setSortingEnabled(True)
        self.selected_aquatic_animal_listwidget.itemDoubleClicked.connect(self.remove_fish)
        self.selected_aquatic_animal_listwidget.model().rowsInserted.connect(self.count_models_listwidgets)
        self.selected_aquatic_animal_listwidget.model().rowsRemoved.connect(self.count_models_listwidgets)

        # latin_name
        latin_name_title_label = QLabel(self.tr('Latin Name: '))
        self.latin_name_label = QLabel("")
        # show_curve
        self.show_curve_pushbutton = QPushButton(self.tr("Show habitat suitability indices"))
        self.show_curve_pushbutton.setStatusTip(self.tr("clic = selected stage ; SHIFT+clic = all stages"))
        self.show_curve_pushbutton.setToolTip(self.tr("Habitat Suitability Indices are curves used to quantify and \n"
                                                      "evaluate habitat quality for a specific species, based on \n"
                                                      "the known selection of particular habitat conditions during \n"
                                                      "specific periods of the species life history (Bovee 1986)."))
        self.show_curve_pushbutton.clicked.connect(self.show_pref)
        self.show_curve_pushbutton.setObjectName("show_curve_pushbutton")
        self.show_curve_pushbutton.setEnabled(False)
        # code_alternative
        code_alternative_title_label = QLabel(self.tr('Code alternative:'))
        self.code_alternative_label = QLabel("")
        # hydrosignature
        self.hydrosignature_pushbutton = QPushButton(self.tr("Show hydrosignature"))
        self.hydrosignature_pushbutton.setStatusTip(self.tr("clic = all stages"))
        self.hydrosignature_pushbutton.setToolTip(self.tr("A hydrosignature quantifies the hydraulic diversity \n"
                                                          "in any area/part of the aquatic space defined by either \n"
                                                          "volume or area percentages on a depth and current \n"
                                                          "velocity cross grid (Lecoarer 2007)."))
        self.hydrosignature_pushbutton.clicked.connect(self.show_hydrosignature)
        self.hydrosignature_pushbutton.setEnabled(False)
        # description
        description_title_label = QLabel(self.tr('Description:'))
        description_title_label.setAlignment(Qt.AlignTop)
        self.description_textedit = QTextEdit(self)  # where the log is show
        self.description_textedit.setFrameShape(QFrame.NoFrame)
        self.description_textedit.setReadOnly(True)
        # image fish
        self.animal_picture_label = ClickLabel()
        self.animal_picture_label.setStyleSheet("QLabel { background-color : white; color : black; }")
        # self.animal_picture_label.setFrameShape(QFrame.Panel)
        self.animal_picture_label.setAlignment(Qt.AlignCenter)
        self.animal_picture_label.clicked.connect(self.open_explorer_on_picture_path)

        # add
        self.add_selected_to_main_pushbutton = QPushButton(self.tr("Validate selected models"))
        self.add_selected_to_main_pushbutton.setStatusTip(self.tr("Validate selected models to send them to your "
                                                                  "habitat calculation tab."))
        self.add_selected_to_main_pushbutton.clicked.connect(self.add_selected_to_main)
        self.add_selected_to_main_pushbutton.setEnabled(False)

        # quit
        self.quit_biological_model_explorer_pushbutton = QPushButton(self.tr("Close"))
        self.quit_biological_model_explorer_pushbutton.clicked.connect(self.quit_biological_model_explorer)

        """ GROUP ET LAYOUT """
        # aquatic_animal
        self.aquatic_animal_layout = QGridLayout()
        self.aquatic_animal_layout.addWidget(self.available_aquatic_animal_label, 0, 0, Qt.AlignRight)
        self.aquatic_animal_layout.addWidget(self.available_aquatic_animal_listwidget, 1, 0)
        self.aquatic_animal_layout.addWidget(self.arrow, 1, 1)
        self.aquatic_animal_layout.addWidget(self.selected_aquatic_animal_label, 0, 2)
        self.aquatic_animal_layout.addWidget(self.selected_aquatic_animal_listwidget, 1, 2)

        # information_curve
        self.information_curve_group = QGroupBox(self.tr("Habitat Suitability Index information"))
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
        #self.selected_aquatic_animal_listwidget.clear()
        # line name
        item_list = []
        for selected_xml_ind, selected_xml_tf in enumerate(self.bio_model_explorer_selection_dict["selected"]):
            if selected_xml_tf:
                for selected_stage_ind, selected_stage_tf in enumerate(self.bio_model_explorer_selection_dict["stage_and_size"][1]):
                    if selected_stage_tf:
                        stage_wish = self.bio_model_explorer_selection_dict["stage_and_size"][0][selected_stage_ind]
                        if stage_wish in self.biological_models_dict_gui["stage_and_size"][selected_xml_ind]:
                            stage_ind = self.biological_models_dict_gui["stage_and_size"][selected_xml_ind].index(stage_wish)
                            item_list.append(
                                self.biological_models_dict_gui["latin_name"][selected_xml_ind] + " - " +
                                self.bio_model_explorer_selection_dict["stage_and_size"][0][selected_stage_ind] + " - " +
                                self.biological_models_dict_gui["code_biological_model"][selected_xml_ind] + " (" +
                                self.biological_models_dict_gui["hydraulic_type"][selected_xml_ind][stage_ind] + ", " +
                                self.biological_models_dict_gui["substrate_type"][selected_xml_ind][stage_ind] + ")"
                            )

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
        self.add_selected_to_main_pushbutton.setFocus()
        self.available_aquatic_animal_label.setText(self.tr("Available models") + " (" + str(self.available_aquatic_animal_listwidget.count()) + ")")
        self.selected_aquatic_animal_label.setText(self.tr("Selected models") + " (" + str(self.selected_aquatic_animal_listwidget.count()) + ")")
        if self.selected_aquatic_animal_listwidget.count() > 0:
            self.add_selected_to_main_pushbutton.setEnabled(True)
        else:
            self.add_selected_to_main_pushbutton.setEnabled(False)

    def remove_fish(self):
        """
        The function is used to remove fish species (or inverterbates species)
        """
        # remove it from available
        self.selected_aquatic_animal_listwidget.takeItem(self.selected_aquatic_animal_listwidget.currentRow())

        self.count_models_listwidgets()

    def show_info_fish(self, listwidget_source):
        """
        This function shows the useful information concerning the selected fish on the GUI.

        :param select:If False, the selected items comes from the QListWidgetcontaining the available fish.
                      If True, the items comes the QListWidget with the selected fish
        """

        listwidget = eval("self." + listwidget_source + "_aquatic_animal_listwidget")

        # get the file
        selection = listwidget.selectedItems()
        if len(selection) == 1:
            i1 = listwidget.currentItem()  # show the info concerning the one selected fish
        else:
            self.latin_name_label.setText("")
            self.code_alternative_label.setText("")
            self.description_textedit.setText("")
            self.animal_picture_label.clear()
            self.animal_picture_label.setText(self.tr("no image file"))
            self.animal_picture_path = None
            self.show_curve_pushbutton.setEnabled(False)
            self.hydrosignature_pushbutton.setEnabled(False)
            # set focus
            self.add_selected_to_main_pushbutton.setFocus()
            return

        # get info
        name_fish, stage, code_bio_model = bio_info_mod.get_name_stage_codebio_fromstr(i1.text()[:i1.text().rindex(" (")])
        self.selected_fish_code_biological_model = code_bio_model
        self.selected_fish_stage = stage
        self.selected_name_fish = name_fish
        i = self.biological_models_dict_gui["code_biological_model"].index(self.selected_fish_code_biological_model)

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
                print("Warning: " + xmlfile + " file does not exist \n")
                return
        except ET.ParseError:
            print("Warning: " + xmlfile + " file is not well-formed.\n")
            return

        # get the description from xml
        data = root.findall('.//Description')
        if len(data) > 0:
            found = False
            for d in data:
                if d.attrib['Language'] == self.lang:
                    description = d.text
                    description = re.sub("\s\s+", "\n", description)
                    self.description_textedit.setText(description[1:-1])
                    found = True
            if not found:
                description = data[0].text
                description = re.sub("\s\s+", "\n", description)
                self.description_textedit.setText(description[1:-1])

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

        # is hydrosignature
        data, vclass, hclass = bio_info_mod.get_hydrosignature(xmlfile)
        if isinstance(data, np.ndarray):
            self.hydrosignature_pushbutton.setEnabled(True)
        else:
            self.hydrosignature_pushbutton.setEnabled(False)

        # enable show_curve_pushbutton
        self.show_curve_pushbutton.setEnabled(True)

        # set focus
        self.add_selected_to_main_pushbutton.setFocus()

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
        if not self.selected_fish_code_biological_model:
            self.send_log.emit("Warning: " + self.tr("No fish selected to show Habitat Suitability Index"))
            return

        plot_attr = lambda: None
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            plot_attr.selected_fish_stage = None
        else:
            plot_attr.selected_fish_stage = self.selected_fish_stage
        plot_attr.i = self.biological_models_dict_gui["code_biological_model"].index(self.selected_fish_code_biological_model)
        plot_attr.aquatic_animal_type = self.biological_models_dict_gui["aquatic_animal_type"][plot_attr.i]
        plot_attr.xmlfile = self.biological_models_dict_gui["path_xml"][plot_attr.i]
        plot_attr.information_model_dict = bio_info_mod.get_biomodels_informations_for_database(plot_attr.xmlfile)
        plot_attr.sub_type = self.biological_models_dict_gui["substrate_type"][plot_attr.i]
        plot_attr.nb_plot = 1

        self.process_manager_sc_plot.set_sc_plot_mode(self.path_prj,
                                                 plot_attr,
                                                 load_project_properties(self.path_prj))

        self.process_manager_sc_plot.start()

    def show_hydrosignature(self):
        """
        This function make the link with function in bio_info_mod.py which allows to load and plot the data related
        to the hydrosignature.
        """

        if not self.selected_fish_code_biological_model:
            self.send_log.emit("Warning: " + self.tr("No fish selected to hydrosignature."))
            return

        # get the file
        i = self.biological_models_dict_gui["code_biological_model"].index(self.selected_fish_code_biological_model)

        plot_attr = lambda: None
        plot_attr.fishname = self.biological_models_dict_gui["latin_name"][i]
        plot_attr.xmlfile = self.biological_models_dict_gui["path_xml"][i]
        plot_attr.nb_plot = 1

        self.process_manager_sc_hs_plot.set_sc_hs_plot_mode(self.path_prj,
                                                 plot_attr,
                                                 load_project_properties(self.path_prj))

        self.process_manager_sc_hs_plot.start()

    def add_selected_to_main(self):
        # source
        source_str = self.nativeParentWidget().source_str

        # get selected models
        selected_aquatic_animal_list = []
        hydraulic_mode_list = []
        substrate_mode_list = []
        for item_index in range(self.selected_aquatic_animal_listwidget.count()):
            new_item_to_merge = self.selected_aquatic_animal_listwidget.item(item_index).text()[:self.selected_aquatic_animal_listwidget.item(item_index).text().rindex(" (")]
            selected_aquatic_animal_list.append(new_item_to_merge)
            # get info
            name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(new_item_to_merge)
            index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
            # get stage index
            index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)

            # get default_hydraulic_type
            default_hydraulic_type = user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage]
            hydraulic_type_available = user_preferences.biological_models_dict["hydraulic_type_available"][index_fish][index_stage]
            hydraulic_mode_list.append(hydraulic_type_available.index(default_hydraulic_type))

            # get default_substrate_type
            default_substrate_type = user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage]
            substrate_type_available = user_preferences.biological_models_dict["substrate_type_available"][index_fish][index_stage]
            substrate_mode_list.append(substrate_type_available.index(default_substrate_type))

        # create dict
        self.item_dict = dict(source_str=source_str,
                              selected_aquatic_animal_list=selected_aquatic_animal_list,
                              hydraulic_mode_list=hydraulic_mode_list,
                              substrate_mode_list=substrate_mode_list)

        # emit signal
        self.nativeParentWidget().send_fill.emit("")

        # clear
        self.selected_aquatic_animal_listwidget.clear()
        self.add_selected_to_main_pushbutton.setEnabled(False)

        # close window
        self.quit_biological_model_explorer()

    def quit_biological_model_explorer(self):
        # convert one key
        bio_model_explorer_selection_dict = self.bio_model_explorer_selection_dict.copy()
        bio_model_explorer_selection_dict["selected"] = self.bio_model_explorer_selection_dict["selected"].tolist()

        # save bio_model_explorer_selection_dict in xml project
        change_specific_properties(self.path_prj,
                                   preference_names=["bio_model_explorer_selection"],
                                   preference_values=[bio_model_explorer_selection_dict])

        self.parent().parent().parent().close()


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        QLabel.mousePressEvent(self, event)
