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
import sys
from multiprocessing import Process, Queue, Value, Event

from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QHBoxLayout, QGroupBox, \
    QComboBox, QTableWidget, QTableWidgetItem, \
    QSizePolicy, QFrame, QCheckBox, QWidget

from src_GUI import estimhab_GUI
from src_GUI.process_manager_GUI import ProcessProgLayout
from src import hdf5_mod
from src.project_properties_mod import load_project_properties, load_specific_properties, change_specific_properties, save_project_properties
from src.user_preferences_mod import user_preferences
from src.bio_info_mod import get_name_stage_codebio_fromstr
from src.dev_tools_mod import sort_homogoeneous_dict_list_by_on_key
from src.variable_unit_mod import HydraulicVariableUnitList


class BioInfo(estimhab_GUI.StatModUseful):
    """
    This class contains the tab with the biological information (the curves of preference). It inherites from
    StatModUseful. StatModuseful is a QWidget, with some practical signal (send_log and show_fig) and some functions
    to find path_im and path_bio (the path where to save image) and to manage lists.
    """
    allmodels_presence = pyqtSignal()
    """
     A Pyqtsignal which indicates to chronice_GUI.py that the merge list should be changed. In Main_Windows.py,
     the new list of merge file is found and send to the ChonicleGui class.
    """

    def __init__(self, path_prj, name_prj, lang='French'):
        super().__init__()

        self.tab_name = "calc hab"
        self.tab_position = 3
        self.lang = lang
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.imfish = ''
        self.current_hab_informations_dict = None
        self.path_bio = load_specific_properties(self.path_prj, ["path_bio"])[0]
        self.path_im_bio = self.path_bio
        # self.path_bio is defined in StatModUseful.
        self.data_fish = []  # all data concerning the fish
        # attribute from the xml which the user can search the database
        # the name should refect the xml attribute or bio_info.load_xml_name() should be changed
        # can be changed but with caution
        # coorect here for new language by adding an attribute in the form "langue"_common_name
        # stage have to be the first attribute !
        self.attribute_acc = ['Stage', 'French_common_name', 'English_common_name', 'Code_ONEMA', 'Code_Sandre',
                              'LatinName', 'CdBiologicalModel']
        self.all_hyd_choice = ["Default",
                               "User",
                               'HV',
                               'H',
                               'V',
                               'HEM',
                               "Neglect"]
        self.all_sub_choice = ["Default",
                               "User",
                               "Coarser-Dominant",
                               'Coarser',
                               'Dominant',
                               'Percentage',
                               'Neglect']
        self.hdf5_merge = []  # the list with the name and path of the hdf5 file
        self.text_ini = []  # the text with the tooltip
        self.plot_new = False
        self.ind_current = None
        self.general_option_hyd_combobox_index = 0
        self.general_option_sub_combobox_index = 0

        self.default_color = "#A6C313"  # #A6C313 (green Irstea)  # #0DB39F (green INRAE)  blue Irstea (71, 181, 230)
        self.user_color = "black"
        # "QComboBox:!editable {background: " + self.default_color + "}"  # OK en black edition mais bizar en classic
        # "background: " + self.default_color # colorize all background
        # "QComboBox: {background: green; color: " + self.default_color + "}" # nada
        self.combobox_style_default = "QComboBox:!on {background-color: " + self.default_color + "; border-radius: 1px}"
        self.combobox_style_user = "QComboBox:!on {border-radius: 1px}"  # font-weight: bold;
        self.selected_aquatic_animal_dict = dict(selected_aquatic_animal_list=[],
                                                 hydraulic_mode_list=[],
                                                 substrate_mode_list=[])
        self.load_selected_aquatic_animal_dict()
        self.user_target_list = HydraulicVariableUnitList()

        self.stop = Event()
        self.q = Queue()
        self.progress_value = Value("d", 0)
        self.p = Process(target=None)

        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # the available merged data
        l0 = QLabel(self.tr('Habitat file(s)'))
        self.habitat_file_combobox = QComboBox()
        self.habitat_file_combobox.currentTextChanged.connect(lambda: self.fill_selected_models_listwidets([]))
        self.habitat_file_combobox.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # create lists with the possible fishes
        # right buttons for both QListWidget managed in the MainWindows class
        self.explore_bio_model_pushbutton = QPushButton(self.tr('Add models'))
        self.explore_bio_model_pushbutton.setObjectName("calc_hab")
        self.explore_bio_model_pushbutton.clicked.connect(self.open_bio_model_explorer)

        self.remove_all_bio_model_pushbutton = QPushButton(self.tr("Remove all models"))
        self.remove_all_bio_model_pushbutton.clicked.connect(self.remove_all_fish)

        self.remove_sel_bio_model_pushbutton = QPushButton(self.tr("Remove selected models"))
        self.remove_sel_bio_model_pushbutton.clicked.connect(self.remove_sel_fish)

        self.create_duplicate_from_selection_pushbutton = QPushButton(self.tr("Create duplicate from selection"))
        self.create_duplicate_from_selection_pushbutton.clicked.connect(self.create_duplicate_from_selection)

        self.remove_duplicate_model_pushbutton = QPushButton(self.tr("Remove duplicates models"))
        self.remove_duplicate_model_pushbutton.clicked.connect(self.remove_duplicates)

        # 1 column
        self.bio_model_choosen_title_label = QLabel(self.tr("Biological models choosen"))
        self.selected_aquatic_animal_qtablewidget = QTableWidget()
        self.selected_aquatic_animal_qtablewidget.setColumnCount(1)
        self.selected_aquatic_animal_qtablewidget.horizontalHeader().setStretchLastSection(True)
        self.selected_aquatic_animal_qtablewidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selected_aquatic_animal_qtablewidget.verticalHeader().setVisible(False)
        self.selected_aquatic_animal_qtablewidget.horizontalHeader().setVisible(False)
        # 2 column
        self.hyd_mode_qtablewidget = QTableWidget()
        self.hyd_mode_qtablewidget.setColumnCount(1)
        self.hyd_mode_qtablewidget.horizontalHeader().setStretchLastSection(True)
        self.hyd_mode_qtablewidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.hyd_mode_qtablewidget.verticalHeader().setVisible(False)
        self.hyd_mode_qtablewidget.horizontalHeader().setVisible(False)
        self.general_option_hyd_combobox = QComboBox()
        self.general_option_hyd_combobox.addItems(self.all_hyd_choice)
        self.general_option_hyd_combobox.model().item(0).setBackground(QColor(self.default_color))
        self.general_option_hyd_combobox.setCurrentIndex(self.general_option_hyd_combobox_index)
        if self.general_option_hyd_combobox_index == 0:  # default
            self.general_option_hyd_combobox.setStyleSheet(self.combobox_style_default)
        else:
            self.general_option_hyd_combobox.setStyleSheet(self.combobox_style_user)
        self.general_option_hyd_combobox.activated.connect(self.set_once_all_hyd_combobox)
        width_size = self.general_option_hyd_combobox.minimumSizeHint().width()
        width_size = width_size + (width_size * 0.2)
        self.general_option_hyd_combobox.setMinimumWidth(width_size)
        # 3 column
        self.sub_mode_qtablewidget = QTableWidget()
        self.sub_mode_qtablewidget.setColumnCount(1)
        self.sub_mode_qtablewidget.horizontalHeader().setStretchLastSection(True)
        self.sub_mode_qtablewidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sub_mode_qtablewidget.verticalHeader().setVisible(False)
        self.sub_mode_qtablewidget.horizontalHeader().setVisible(False)
        self.general_option_sub_combobox = QComboBox()
        self.general_option_sub_combobox.addItems(self.all_sub_choice)
        self.general_option_sub_combobox.model().item(0).setBackground(QColor(self.default_color))
        self.general_option_sub_combobox.setCurrentIndex(self.general_option_sub_combobox_index)
        if self.general_option_sub_combobox_index == 0:  # default
            self.general_option_sub_combobox.setStyleSheet(self.combobox_style_default)
        else:
            self.general_option_sub_combobox.setStyleSheet(self.combobox_style_user)
        self.general_option_sub_combobox.activated.connect(self.set_once_all_sub_combobox)
        # 4 column
        self.exist_title_label = QLabel(self.tr("exist in .hab"))
        self.presence_qtablewidget = QTableWidget()
        self.presence_qtablewidget.setColumnCount(1)
        self.presence_qtablewidget.horizontalHeader().setStretchLastSection(True)
        self.presence_qtablewidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.presence_qtablewidget.verticalHeader().setVisible(False)
        self.presence_qtablewidget.horizontalHeader().setVisible(False)

        # progress_layout
        self.progress_layout = ProcessProgLayout(self.run_habitat_value,
                                                 send_log=self.send_log,
                                                 process_type="hab",
                                                 send_refresh_filenames=self.allmodels_presence)  # load_polygon_substrate_pushbutton
        self.progress_layout.run_stop_button.setText(self.tr("Compute habitat"))

        # 5 column
        self.presence_scrollbar = self.presence_qtablewidget.verticalScrollBar()

        # scroll bar together
        self.selected_aquatic_animal_qtablewidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.selected_aquatic_animal_qtablewidget.verticalScrollBar().setEnabled(True)
        self.selected_aquatic_animal_qtablewidget.verticalScrollBar().valueChanged.connect(self.change_scroll_position)
        self.hyd_mode_qtablewidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hyd_mode_qtablewidget.verticalScrollBar().setEnabled(False)
        self.hyd_mode_qtablewidget.verticalScrollBar().valueChanged.connect(self.change_scroll_position)
        self.sub_mode_qtablewidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.sub_mode_qtablewidget.verticalScrollBar().setEnabled(False)
        self.sub_mode_qtablewidget.verticalScrollBar().valueChanged.connect(self.change_scroll_position)
        self.presence_qtablewidget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.presence_qtablewidget.verticalScrollBar().setEnabled(True)
        self.presence_qtablewidget.verticalScrollBar().valueChanged.connect(self.change_scroll_position)

        # fill hdf5 list
        #self.update_merge_list()

        # empty frame scrolable
        content_widget = QFrame()

        # layout
        self.layout4 = QGridLayout(content_widget)
        layout_prov_input = QHBoxLayout()
        layout_prov_input.addWidget(l0)
        layout_prov_input.addWidget(self.habitat_file_combobox)
        self.layout4.addLayout(layout_prov_input, 0, 0, 1, 4, Qt.AlignLeft)  #

        model_groupbox = QGroupBox(self.tr("Model to compute"))
        layout_prov = QGridLayout()
        layout_prov.addWidget(self.explore_bio_model_pushbutton, 0, 0)
        layout_prov.addWidget(self.create_duplicate_from_selection_pushbutton, 1, 0)
        layout_prov.addWidget(self.remove_all_bio_model_pushbutton, 0, 1)
        layout_prov.addWidget(self.remove_sel_bio_model_pushbutton, 1, 1)
        layout_prov.addWidget(self.remove_duplicate_model_pushbutton, 2, 1)
        model_groupbox.setLayout(layout_prov)
        self.layout4.addWidget(model_groupbox, 1, 0, 1, 4, Qt.AlignLeft)  #

        # 1 column
        self.layout4.addWidget(self.bio_model_choosen_title_label, 2, 0)
        self.layout4.addWidget(self.selected_aquatic_animal_qtablewidget, 3, 0)
        # 2 column
        layout_prov2 = QHBoxLayout()
        layout_prov2.addWidget(QLabel(self.tr("hydraulic option")))
        layout_prov2.addWidget(self.general_option_hyd_combobox)
        self.layout4.addLayout(layout_prov2, 2, 1)
        self.layout4.addWidget(self.hyd_mode_qtablewidget, 3, 1)
        # 3 column
        layout_prov3 = QHBoxLayout()
        layout_prov3.addWidget(QLabel(self.tr("substrate option")))
        layout_prov3.addWidget(self.general_option_sub_combobox)
        self.layout4.addLayout(layout_prov3, 2, 2)
        self.layout4.addWidget(self.sub_mode_qtablewidget, 3, 2)
        # 4e column
        self.layout4.addWidget(self.exist_title_label, 2, 3)
        self.layout4.addWidget(self.presence_qtablewidget, 3, 3, 1, 1)
        # 5e column
        self.layout4.addWidget(self.presence_scrollbar, 3, 4, 1, 1)

        self.layout4.addLayout(self.progress_layout, 5, 0, 1, 4)
        self.layout4.setColumnStretch(0, 30)
        self.layout4.setColumnStretch(1, 10)
        self.layout4.setColumnStretch(2, 10)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

        self.presence_qtablewidget.setColumnWidth(0, self.exist_title_label.width())
        self.presence_qtablewidget.setFixedWidth(self.exist_title_label.width())

    def change_scroll_position(self, index):
        self.selected_aquatic_animal_qtablewidget.verticalScrollBar().setValue(index)
        self.hyd_mode_qtablewidget.verticalScrollBar().setValue(index)
        self.sub_mode_qtablewidget.verticalScrollBar().setValue(index)
        self.presence_qtablewidget.verticalScrollBar().setValue(index)

    def open_bio_model_explorer(self):
        self.nativeParentWidget().bio_model_explorer_dialog.open_bio_model_explorer("calc_hab")

    def load_selected_aquatic_animal_dict(self):
        self.selected_aquatic_animal_dict = load_specific_properties(self.path_prj, ["selected_aquatic_animal_list"])[0]

        if len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]) > 1:
            self.general_option_hyd_combobox_index = self.selected_aquatic_animal_dict["general_hyd_sub_combobox_index"][0]
            self.general_option_sub_combobox_index = self.selected_aquatic_animal_dict["general_hyd_sub_combobox_index"][1]
            # remove key
            del self.selected_aquatic_animal_dict["general_hyd_sub_combobox_index"]

    def remove_all_fish(self):
        """
        This function removes all fishes from the selected fish
        """
        self.selected_aquatic_animal_qtablewidget.clear()
        self.selected_aquatic_animal_qtablewidget.setRowCount(0)
        self.hyd_mode_qtablewidget.clear()
        self.hyd_mode_qtablewidget.setRowCount(0)
        self.sub_mode_qtablewidget.clear()
        self.sub_mode_qtablewidget.setRowCount(0)
        self.presence_qtablewidget.clear()
        self.presence_qtablewidget.setRowCount(0)
        self.selected_aquatic_animal_dict = dict(selected_aquatic_animal_list=[],
                                                     hydraulic_mode_list=[],
                                                     substrate_mode_list=[])
        self.bio_model_choosen_title_label.setText(self.tr("Biological models choosen (") + str(0) + ")")

    def remove_sel_fish(self):
        # selected items
        index_to_remove_list = [item.row() for item in self.selected_aquatic_animal_qtablewidget.selectedIndexes()]

        if index_to_remove_list:
            # remove items
            for index in reversed(range(len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]))):
                if index in index_to_remove_list:
                    self.selected_aquatic_animal_qtablewidget.removeRow(index)
                    self.hyd_mode_qtablewidget.removeRow(index)
                    self.sub_mode_qtablewidget.removeRow(index)
                    self.presence_qtablewidget.removeRow(index)

            # remove element list in dict
            for key in self.selected_aquatic_animal_dict.keys():
                for index_to_remove in reversed(index_to_remove_list):
                    self.selected_aquatic_animal_dict[key].pop(index_to_remove)
        # total item
        total_item = self.selected_aquatic_animal_qtablewidget.rowCount()
        self.bio_model_choosen_title_label.setText(self.tr("Biological models choosen (") + str(total_item) + ")")

    def set_once_all_hyd_combobox(self):
        """
        from hydraulic mode combobox, set all comboboxs in qtablewidget to same mode.
        """
        default = False
        new_hyd_str = self.general_option_hyd_combobox.currentText()
        if new_hyd_str == "User":
            self.general_option_hyd_combobox.setStyleSheet(self.combobox_style_user)
            return
        if new_hyd_str == "Default":
            default = True
            self.general_option_hyd_combobox.setStyleSheet(self.combobox_style_default)
        else:
            self.general_option_hyd_combobox.setStyleSheet(self.combobox_style_user)
        for index, item_str in enumerate(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]):
            # get combobox
            combobox = self.hyd_mode_qtablewidget.cellWidget(index, 0)
            # get item
            hydraulic_type_available = [combobox.itemText(i) for i in range(combobox.count())]

            if default:
                # get default
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
                index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
                # get stage index
                index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)
                default_hydraulic_type = user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage]
                # is default available by .hab data ?
                if default_hydraulic_type == "HEM" and (not self.current_hab_informations_dict["dimension_ok"] or not self.current_hab_informations_dict[
                        "z_presence_ok"] or not self.current_hab_informations_dict[
                        "shear_stress_ok"]):  # not 2d or not z
                        default_hydraulic_type = "Neglect"
                        self.hyd_mode_qtablewidget.cellWidget(index, 0).setToolTip(
                            self.tr(".hab data not adapted :\nnot 2d data, not z node data or no shear_stress data."))
                # set positon to combobox
                self.hyd_mode_qtablewidget.cellWidget(index, 0).setCurrentIndex(hydraulic_type_available.index(default_hydraulic_type))
            if not default:
                if new_hyd_str in hydraulic_type_available:
                    # set positon to combobox
                    self.hyd_mode_qtablewidget.cellWidget(index, 0).setCurrentIndex(hydraulic_type_available.index(new_hyd_str))

    def set_once_all_sub_combobox(self):
        """
        from substrate mode combobox, set all comboboxs in qtablewidget to same mode.
        """
        default = False
        new_sub_str = self.general_option_sub_combobox.currentText()
        if new_sub_str == "User":
            self.general_option_sub_combobox.setStyleSheet(self.combobox_style_user)
            return
        if new_sub_str == "Default":
            default = True
            self.general_option_sub_combobox.setStyleSheet(self.combobox_style_default)
        else:
            self.general_option_sub_combobox.setStyleSheet(self.combobox_style_user)
        for index, item_str in enumerate(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]):
            # get combobox
            combobox = self.sub_mode_qtablewidget.cellWidget(index, 0)
            # get item
            substrate_type_available = [combobox.itemText(i) for i in range(combobox.count())]
            if default:
                # get default
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
                index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
                # get stage index
                index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)
                # get default_substrate_type
                default_substrate_type = user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage]
                # set position to combobox
                self.sub_mode_qtablewidget.cellWidget(index, 0).setCurrentIndex(substrate_type_available.index(default_substrate_type))
            else:
                if new_sub_str in substrate_type_available:
                    # set positon to combobox
                    self.sub_mode_qtablewidget.cellWidget(index, 0).setCurrentIndex(substrate_type_available.index(new_sub_str))

    def check_if_model_exist_in_hab(self, model_index):
        # 1 column
        item_str = self.selected_aquatic_animal_qtablewidget.item(model_index, 0).text()
        name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
        # 2 column
        hyd_opt_str = self.hyd_mode_qtablewidget.cellWidget(model_index, 0).currentText()
        # 3 column
        sub_opt_str = self.sub_mode_qtablewidget.cellWidget(model_index, 0).currentText()
        # 4 column
        item_checkbox = self.presence_qtablewidget.cellWidget(model_index, 0).layout().itemAt(0).widget()

        # get full name
        fish_name_full = code_bio_model + "_" + stage + "_" + hyd_opt_str + "_" + sub_opt_str

        # check or not
        if fish_name_full in self.current_hab_informations_dict["fish_list"]:
            item_checkbox.setChecked(True)
        else:
            item_checkbox.setChecked(False)

    def check_uncheck_allmodels_presence(self):
        print("check_uncheck_allmodels_presence")
        self.get_current_hab_informations()
        for model_index in range(self.selected_aquatic_animal_qtablewidget.rowCount()):
            self.check_if_model_exist_in_hab(model_index)

    def color_hyd_combobox(self):
        """
        if one of hydraulic qtablewidget comboboxs changed : color of combobox current item is changed
        """
        model_index = int(self.sender().objectName())
        new_hyd_mode_index = self.sender().currentIndex()

        self.get_current_hab_informations()

        # get info
        item_str = self.selected_aquatic_animal_qtablewidget.item(model_index, 0).text()
        name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
        index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
        index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)
        hydraulic_type_available = [self.sender().itemText(i) for i in range(self.sender().count())]
        default_choice_index = hydraulic_type_available.index(user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage])

        # change color if default choosen
        if new_hyd_mode_index == default_choice_index:
            self.sender().setStyleSheet(self.combobox_style_default)
        else:
            self.sender().setStyleSheet(self.combobox_style_user)

        # change selected_aquatic_animal_dict
        self.selected_aquatic_animal_dict["hydraulic_mode_list"][model_index] = new_hyd_mode_index

        # check if exist
        self.check_if_model_exist_in_hab(model_index)

    def change_general_hyd_combobox(self):
        model_index = int(self.sender().objectName())
        new_hyd_mode_index = self.sender().currentIndex()
        # get current general sub combobox item
        current_text = self.general_option_hyd_combobox.currentText()
        if current_text != "User":
            self.general_option_hyd_combobox.blockSignals(True)
            self.general_option_hyd_combobox.setCurrentIndex(1)
            self.general_option_hyd_combobox.blockSignals(False)
            self.general_option_hyd_combobox.setStyleSheet(self.combobox_style_user)

            # change in dict
            self.selected_aquatic_animal_dict["hydraulic_mode_list"][model_index] = new_hyd_mode_index

    def color_sub_combobox(self):
        """
        if one of substrate qtablewidget comboboxs changed : color of combobox current item is changed
        """
        model_index = int(self.sender().objectName())
        new_sub_mode_index = self.sender().currentIndex()

        self.get_current_hab_informations()

        # get info
        item_str = self.selected_aquatic_animal_qtablewidget.item(model_index, 0).text()
        name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
        index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
        index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)
        substrate_type_available = [self.sender().itemText(i) for i in range(self.sender().count())]
        default_choice_index = substrate_type_available.index(user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage])
        if new_sub_mode_index == default_choice_index:
            self.sender().setStyleSheet(self.combobox_style_default)
        else:
            self.sender().setStyleSheet(self.combobox_style_user)

        # change selected_aquatic_animal_dict
        self.selected_aquatic_animal_dict["substrate_mode_list"][model_index] = new_sub_mode_index

        # check if exist
        self.check_if_model_exist_in_hab(model_index)

    def change_general_sub_combobox(self):
        model_index = int(self.sender().objectName())
        new_sub_mode_index = self.sender().currentIndex()
        # get current general sub combobox item
        current_text = self.general_option_sub_combobox.currentText()
        if current_text != "User":
            self.general_option_sub_combobox.blockSignals(True)
            self.general_option_sub_combobox.setCurrentIndex(1)
            self.general_option_sub_combobox.blockSignals(False)
            self.general_option_sub_combobox.setStyleSheet(self.combobox_style_user)
            # change in dict
            self.selected_aquatic_animal_dict["substrate_mode_list"][model_index] = new_sub_mode_index

    def fill_selected_models_listwidets(self, new_item_text_dict):
        #print("fill_selected_models_listwidets", self.sender())
        # if new added remove duplicates
        if new_item_text_dict and self.selected_aquatic_animal_dict:  # add models from bio model selector  (default + user if exist)
            self.selected_aquatic_animal_dict["selected_aquatic_animal_list"].extend(new_item_text_dict["selected_aquatic_animal_list"])
            self.selected_aquatic_animal_dict["hydraulic_mode_list"].extend(new_item_text_dict["hydraulic_mode_list"])
            self.selected_aquatic_animal_dict["substrate_mode_list"].extend(new_item_text_dict["substrate_mode_list"])
            if "general_hyd_sub_combobox_index" in self.selected_aquatic_animal_dict.keys():
                del self.selected_aquatic_animal_dict["general_hyd_sub_combobox_index"]
            self.selected_aquatic_animal_dict = sort_homogoeneous_dict_list_by_on_key(self.selected_aquatic_animal_dict,
                                                                                      "selected_aquatic_animal_list")

        # get_current_hab_informations
        self.get_current_hab_informations()

        # clear
        self.selected_aquatic_animal_qtablewidget.clear()
        self.hyd_mode_qtablewidget.clear()
        self.sub_mode_qtablewidget.clear()
        self.presence_qtablewidget.clear()

        # if .hab :
        if self.current_hab_informations_dict:
            # check if user pref curve file has been removed by user (AppData) to remove it in
            # selected_aquatic_animal_dict
            for index in reversed(range(len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]))):
                # get bio info
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"][index])
                if not code_bio_model in user_preferences.biological_models_dict["code_biological_model"]:
                    # remove it
                    self.selected_aquatic_animal_dict["selected_aquatic_animal_list"].pop(index)

            if new_item_text_dict:
                if not new_item_text_dict["selected_aquatic_animal_list"]:
                    self.send_log.emit("Warning: " + self.tr("No models added (no selection)."))

            # total_item
            total_item = len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"])

            # set table size
            self.selected_aquatic_animal_qtablewidget.setRowCount(total_item)
            self.hyd_mode_qtablewidget.setRowCount(total_item)
            self.sub_mode_qtablewidget.setRowCount(total_item)
            self.presence_qtablewidget.setRowCount(total_item)

            # block HEM
            if not self.current_hab_informations_dict["dimension_ok"] or not self.current_hab_informations_dict["z_presence_ok"]:  # not 2d or not z
                self.general_option_hyd_combobox.model().item(self.all_hyd_choice.index("HEM")).setEnabled(False)
                if new_item_text_dict:
                    if new_item_text_dict["selected_aquatic_animal_list"]:
                        self.send_log.emit("NB: " + self.tr("Hydraulic HEM computation option is disable for habitat calculation  (hydraulic data in .hab are not of 2D type or do not contain z-values)."))
            else:
                self.general_option_hyd_combobox.model().item(self.all_hyd_choice.index("HEM")).setEnabled(True)

            # block_percentage
            if not self.current_hab_informations_dict["percentage_ok"]:
                self.general_option_sub_combobox.model().item(self.all_sub_choice.index("Percentage")).setEnabled(False)
                if new_item_text_dict:
                    if new_item_text_dict["selected_aquatic_animal_list"]:
                        self.send_log.emit("NB: " + self.tr("Substrate percentage computation option is disable for habitat calculation (substrate classification method in .hab is not in percentage)."))
            else:
                self.general_option_sub_combobox.model().item(self.all_sub_choice.index("Percentage")).setEnabled(True)

            # add new item if not exist
            for index, item_str in enumerate(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]):
                """ NAME """
                label_cell = QTableWidgetItem(item_str)
                label_cell.setToolTip(item_str)
                self.selected_aquatic_animal_qtablewidget.setItem(index, 0, label_cell)
                self.selected_aquatic_animal_qtablewidget.setRowHeight(index, 27)

                # get bio info
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
                index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)

                # get stage index
                index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)

                """ HYD """
                # # change language
                # for num in range(len(user_preferences.biological_models_dict["hydraulic_type_available"][index_fish][index_stage])):
                #     user_preferences.biological_models_dict["hydraulic_type_available"][index_fish][index_stage][num] = self.tr(user_preferences.biological_models_dict["hydraulic_type_available"][index_fish][index_stage][num])
                # user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage] = self.tr(user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage])
                # get default_hydraulic_type
                hydraulic_type_available = user_preferences.biological_models_dict["hydraulic_type_available"][index_fish][index_stage]

                # create combobox
                item_combobox_hyd = QComboBox()
                item_combobox_hyd.setObjectName(str(index))
                item_combobox_hyd.addItems(hydraulic_type_available)
                choosen_index = self.selected_aquatic_animal_dict["hydraulic_mode_list"][index]
                default_choice_index = hydraulic_type_available.index(user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage])
                if choosen_index == default_choice_index:
                    item_combobox_hyd.setStyleSheet(self.combobox_style_default)
                    item_combobox_hyd.setToolTip(
                        self.tr("default hydraulic option from biological model file."))
                else:
                    item_combobox_hyd.setStyleSheet(self.combobox_style_user)
                item_combobox_hyd.model().item(default_choice_index).setBackground(QColor(self.default_color))
                if "HEM" in hydraulic_type_available:
                    if not self.current_hab_informations_dict["dimension_ok"] or not self.current_hab_informations_dict["z_presence_ok"] or not self.current_hab_informations_dict["shear_stress_ok"]:  # not 2d or not z
                        item_combobox_hyd.model().item(hydraulic_type_available.index("HEM")).setEnabled(False)
                        item_combobox_hyd.model().item(hydraulic_type_available.index("HEM")).setToolTip(
                            self.tr(".hab data not adapted :\nnot 2d data, not z node data or no shear_stress data."))
                        self.hyd_mode_qtablewidget.selectRow(hydraulic_type_available.index("Neglect"))
                        choosen_index = hydraulic_type_available.index("Neglect")
                        item_combobox_hyd.setToolTip(
                            self.tr(".hab data not adapted :\nnot 2d data, not z node data or no shear_stress data."))
                item_combobox_hyd.setCurrentIndex(choosen_index)
                item_combobox_hyd.currentIndexChanged.connect(self.color_hyd_combobox)
                item_combobox_hyd.activated.connect(self.change_general_hyd_combobox)
                # add combobox item
                self.hyd_mode_qtablewidget.setCellWidget(index, 0, item_combobox_hyd)
                self.hyd_mode_qtablewidget.setRowHeight(index, 27)

                """ SUB """
                # get default_substrate_type
                substrate_type_available = user_preferences.biological_models_dict["substrate_type_available"][index_fish][index_stage]

                # create combobox
                item_combobox_sub = QComboBox()
                item_combobox_sub.setObjectName(str(index))
                item_combobox_sub.addItems(substrate_type_available)
                choosen_index = self.selected_aquatic_animal_dict["substrate_mode_list"][index]
                default_choice_index = substrate_type_available.index(user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage])
                if self.current_hab_informations_dict["sub_mapping_method"] == "constant":
                    default_choice_index = substrate_type_available.index("Neglect")
                    item_combobox_sub.model().item(default_choice_index).setBackground(QColor(self.default_color))
                    item_combobox_sub.model().item(default_choice_index).setToolTip(
                        self.tr(".hab sub data is constant values. Computing habitat values with constant "
                                "substrate data is not encouraged."))
                    item_combobox_sub.setToolTip(
                        self.tr(".hab sub data is constant values. Computing habitat values with constant "
                                "substrate data is not encouraged."))
                    if self.general_option_sub_combobox.currentIndex() == 0:
                        choosen_index = default_choice_index
                if choosen_index == default_choice_index:
                    item_combobox_sub.setStyleSheet(self.combobox_style_default)
                    item_combobox_sub.setToolTip(
                        self.tr("default substrate option from biological model file."))
                else:
                    item_combobox_sub.setStyleSheet(self.combobox_style_user)
                item_combobox_sub.model().item(default_choice_index).setBackground(QColor(self.default_color))
                if not self.current_hab_informations_dict["percentage_ok"]:
                    if "Percentage" in substrate_type_available:
                        item_combobox_sub.model().item(substrate_type_available.index("Percentage")).setEnabled(False)
                        if choosen_index == substrate_type_available.index("Percentage"):
                            choosen_index = 0
                item_combobox_sub.setCurrentIndex(choosen_index)
                item_combobox_sub.currentIndexChanged.connect(self.color_sub_combobox)
                item_combobox_sub.activated.connect(self.change_general_sub_combobox)
                # add combobox item
                self.sub_mode_qtablewidget.setCellWidget(index, 0, item_combobox_sub)
                self.sub_mode_qtablewidget.setRowHeight(index, 27)

                """ EXIST """
                item_checkbox = QCheckBox()
                item_checkbox.setEnabled(False)
                item_checkbox.setObjectName(str(index))
                # get full name
                fish_name_full = code_bio_model + "_" + stage + "_" + item_combobox_hyd.currentText() + "_" + item_combobox_sub.currentText()
                # check or not
                if fish_name_full in self.current_hab_informations_dict["fish_list"]:
                    item_checkbox.setChecked(True)
                else:
                    item_checkbox.setChecked(False)
                cell_widget = QWidget()
                lay_out = QHBoxLayout(cell_widget)
                lay_out.addWidget(item_checkbox)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(lay_out)
                # add item_checkbox
                self.presence_qtablewidget.setCellWidget(index, 0, cell_widget)
                self.presence_qtablewidget.setRowHeight(index, 27)

            # general
            self.bio_model_choosen_title_label.setText(self.tr("Biological models choosen (") + str(total_item) + ")")
            if self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]:
                self.progress_layout.run_stop_button.setEnabled(True)

            # save model selection calhab
            self.save_selected_aquatic_animal_list_prj()

        else:
            self.progress_layout.run_stop_button.setEnabled(False)
            if new_item_text_dict:
                self.send_log.emit("Warning: " + self.tr("Create a .hab file before adding models."))

    def create_duplicate_from_selection(self):
        # selected items
        index_to_duplicate_list = [item.row() for item in self.selected_aquatic_animal_qtablewidget.selectedIndexes()]

        if index_to_duplicate_list:
            # get items
            for index in index_to_duplicate_list:
                # get text
                label = self.selected_aquatic_animal_qtablewidget.item(index, 0)
                label_text = label.text()

                # get hyd modes + current
                hyd_combobox = self.hyd_mode_qtablewidget.cellWidget(index, 0)
                hyd_current_index = hyd_combobox.currentIndex()

                # get sub modes + current
                sub_combobox = self.sub_mode_qtablewidget.cellWidget(index, 0)
                sub_current_index = sub_combobox.currentIndex()

                # append new data
                self.selected_aquatic_animal_dict["selected_aquatic_animal_list"].append(label_text)
                self.selected_aquatic_animal_dict["hydraulic_mode_list"].append(hyd_current_index)
                self.selected_aquatic_animal_dict["substrate_mode_list"].append(sub_current_index)

            self.selected_aquatic_animal_dict = sort_homogoeneous_dict_list_by_on_key(self.selected_aquatic_animal_dict,
                                                                                      "selected_aquatic_animal_list")
            self.fill_selected_models_listwidets([])

    def get_current_hab_informations(self):
        # create hdf5 class
        if self.habitat_file_combobox.currentText():
            try:
                hdf5 = hdf5_mod.Hdf5Management(self.path_prj, self.habitat_file_combobox.currentText(), new=False,
                                               edit=False)
                hdf5.get_hdf5_attributes(close_file=True)
                hdf5.check_if_file_is_valid_for_calc_hab()
                self.current_hab_informations_dict = hdf5.required_dict_calc_hab
            except OSError:
                self.habitat_file_combobox.removeItem(self.habitat_file_combobox.currentIndex())

    def remove_duplicates(self):
        # get full name
        full_names = []
        for idx, model in enumerate(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]):
            full_name = model + "_" + str(self.selected_aquatic_animal_dict["hydraulic_mode_list"][idx]) + "_" + str(self.selected_aquatic_animal_dict["substrate_mode_list"][idx])
            full_names.append(full_name)

        index_to_keep = [idx for idx, item in enumerate(full_names) if item not in full_names[:idx]]
        self.selected_aquatic_animal_dict["selected_aquatic_animal_list"] = [self.selected_aquatic_animal_dict["selected_aquatic_animal_list"][i] for i in index_to_keep]
        self.selected_aquatic_animal_dict["hydraulic_mode_list"] = [self.selected_aquatic_animal_dict["hydraulic_mode_list"][i] for i in index_to_keep]
        self.selected_aquatic_animal_dict["substrate_mode_list"] = [self.selected_aquatic_animal_dict["substrate_mode_list"][i] for i in index_to_keep]
        self.fill_selected_models_listwidets([])

    def save_selected_aquatic_animal_list_prj(self):
        # if .hab :
        if self.current_hab_informations_dict:
            # get hydraulic and substrate mode
            hydraulic_mode_list = []
            substrate_mode_list = []
            for index, item_str in enumerate(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]):
                # get combobox
                combobox_hyd = self.hyd_mode_qtablewidget.cellWidget(index, 0)
                hydraulic_mode_list.append(combobox_hyd.currentIndex())
                combobox_sub = self.sub_mode_qtablewidget.cellWidget(index, 0)
                substrate_mode_list.append(combobox_sub.currentIndex())

            # cnvert to dict
            selected_aquatic_animal_dict = dict(selected_aquatic_animal_list=self.selected_aquatic_animal_dict["selected_aquatic_animal_list"],
                                                         hydraulic_mode_list=hydraulic_mode_list,
                                                         substrate_mode_list=substrate_mode_list,
                                                         general_hyd_sub_combobox_index=[self.general_option_hyd_combobox.currentIndex(),
                                                                                         self.general_option_sub_combobox.currentIndex()])

            # save
            change_specific_properties(self.path_prj,
                                       preference_names=["selected_aquatic_animal_list"],
                                       preference_values=[selected_aquatic_animal_dict])

    def update_merge_list(self):
        """
        This function goes in the projet xml file and gets all available merged data. Usually, it is called
        by Substrate() (when finished to merge some data) or at the start of HABBY.

        We add a "tooltip" which indicates the orginal hydraulic and substrate files.
        """
        # open the file
        try:
            try:
                # load
                project_properties = load_project_properties(self.path_prj)
                files = project_properties["HABITAT"]["hdf5"]
            except IOError:
                self.send_log.emit("Warning: " + self.tr("The .habby project file does not exist."))
                return
        except:
            self.send_log.emit("Warning: " + self.tr("The .habby project file is not well-formed."))
            return
        current_file = self.habitat_file_combobox.currentText()
        self.habitat_file_combobox.blockSignals(True)
        self.habitat_file_combobox.clear()
        self.hdf5_merge = []

        # get filename
        path_hdf5 = self.find_path_hdf5_est()

        # add it to the list
        if files is not None:
            for idx, f in enumerate(files):
                if os.path.isfile(os.path.join(path_hdf5, f)):
                    hdf5_file = hdf5_mod.Hdf5Management(self.path_prj, f, new=False, edit=False)
                    try:
                        hdf5_file.get_hdf5_attributes(close_file=False)
                        if hdf5_file.file_object:
                            hydro_ini = hdf5_file.data_2d.hyd_filename_source
                            sub_ini = hdf5_file.data_2d.sub_filename_source
                            hydro_ini = os.path.basename(hydro_ini)
                            textini = 'Hydraulic: ' + hydro_ini + '\nSubstrate: ' + sub_ini
                            self.habitat_file_combobox.addItem(f)
                            self.habitat_file_combobox.setItemData(idx, textini, Qt.ToolTipRole)
                            name = f
                            self.hdf5_merge.append(name)
                        hdf5_file.close_file()
                    except:
                        print("Error: HABBY " + f + " seems to be corrupted. Delete it manually.")
                else:
                    self.send_log.emit("Warning: " + f + self.tr(", this .hab file has been deleted by the user."))
                    # remove
                    project_properties["HABITAT"]["hdf5"].remove(f)

        if current_file and current_file in files:
            self.habitat_file_combobox.setCurrentIndex(files.index(current_file))
        # save
        save_project_properties(self.path_prj, project_properties)

        self.habitat_file_combobox.blockSignals(False)

        # check_uncheck_allmodels_presence
        self.fill_selected_models_listwidets([])

    def run_habitat_value(self):
        """
        This function runs HABBY to get the habitat value based on the data in a "merged" hdf5 file and the chosen
        preference files.

        We should not add a comma in the name of the selected fish.
        """
        # remove duplicate
        self.remove_duplicates()

        # get the name of the xml biological file of the selected fish and the stages to be analyzed
        pref_file_list = []
        stage_list = []
        name_fish_sel = ''  # for the xml project file
        self.user_target_list = HydraulicVariableUnitList()

        for i in range(len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"])):
            # check if not exist
            if not self.presence_qtablewidget.cellWidget(i, 0).layout().itemAt(0).widget().isChecked():
                # options
                hyd_opt = self.hyd_mode_qtablewidget.cellWidget(i, 0).currentText()
                sub_opt = self.sub_mode_qtablewidget.cellWidget(i, 0).currentText()
                # get info from 1 list widget
                label = self.selected_aquatic_animal_qtablewidget.item(i, 0)
                fish_item_text = label.text()
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(fish_item_text)
                if hyd_opt == "Neglect" and sub_opt == "Neglect":
                    self.send_log.emit('Warning: ' + fish_item_text + self.tr(" model options are Neglect and Neglect for hydraulic and substrate options. This calculation will not be performed."))
                    continue
                index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
                name_fish_sel += fish_item_text + ","

                # append_new_habitat_variable
                self.user_target_list.append_new_habitat_variable(code_bio_model,
                                                            stage,
                                                             hyd_opt,
                                                             sub_opt,
                                                             user_preferences.biological_models_dict["aquatic_animal_type"][index_fish],
                                                             user_preferences.biological_models_dict["model_type"][index_fish],
                                                             user_preferences.biological_models_dict["path_xml"][index_fish],
                                                                  user_preferences.biological_models_dict["path_img"][index_fish])

        if self.user_target_list:
            # get the name of the merged file
            path_hdf5 = self.find_path_hdf5_est()
            ind = self.habitat_file_combobox.currentIndex()
            if len(self.hdf5_merge) > 0:
                hab_filename = self.hdf5_merge[ind]
            else:
                self.send_log.emit('Error: ' + self.tr('No merged hydraulic files available.'))
                return

            # only useful if we want to also show the 2d figure in the GUI
            self.hdf5_file = hab_filename
            self.path_hdf5 = path_hdf5

            # process_manager
            self.progress_layout.process_manager.set_hab_mode(self.path_prj,
                                                                      self.user_target_list,
                                                                      hab_filename,
                                                                      load_project_properties(self.path_prj))
            # process_prog_show
            self.progress_layout.start_process()

            self.create_script()
        else:
            # disable the button
            self.progress_layout.run_stop_button.setEnabled(True)
            self.progress_layout.progress_bar.setValue(0.0)
            self.progress_layout.progress_label.setText(
                "{0:.0f}/{1:.0f}".format(0.0, 1.0))
            self.send_log.emit(self.tr('Warning: Nothing to compute !'))

    def create_script(self):
        # path_prj
        path_prj_script = self.path_prj + "_restarted"

        # cli
        if sys.argv[0][-3:] == ".py":
            exe_cmd = '"' + sys.executable + '" "' + sys.argv[0] + '"'
        else:
            exe_cmd = '"' + sys.executable + '"'
        script_function_name = "RUN_HABITAT"
        cmd_str = exe_cmd + ' ' + script_function_name + \
                  ' hab=' + self.hdf5_file + \
                  ' pref_file_list=' + ",".join(self.user_target_list.pref_files()) + \
                  ' stage_list=' + ",".join(self.user_target_list.stages()) + \
                  ' hyd_opt=' + ",".join([var.hyd_opt for var in self.user_target_list]) + \
                  ' sub_opt=' + ",".join([var.sub_opt for var in self.user_target_list]) + \
                  ' path_prj="' + path_prj_script + '"'
        self.send_log.emit("script" + cmd_str)

        # py
        cmd_str = F"\t# RUN_HABITAT\n" \
                  F"\tfrom src.bio_info_mod import get_biomodels_informations_for_database\n" \
                  F"\tfrom src.calcul_hab_mod import calc_hab_and_output\n" \
                  F"\tfrom src.variable_unit_mod import HydraulicVariableUnitList\n\n"
        cmd_str = cmd_str + F"\trun_choice = dict()\n" \
                            F"\trun_choice['pref_file_list'] = {repr(self.user_target_list.pref_files())}\n" \
                            F"\trun_choice['stage_list'] = {repr(self.user_target_list.stages())}\n" \
                            F"\trun_choice['hyd_opt'] = {repr([var.hyd_opt for var in self.user_target_list])}\n" \
                            F"\trun_choice['sub_opt'] = {repr([var.sub_opt for var in self.user_target_list])}\n"
        cmd_str = cmd_str + F"\tanimal_variable_list = HydraulicVariableUnitList()\n" \
                            F"\tfor i in range(len(run_choice['pref_file_list'])):\n" \
                            F"\t\tinformation_model_dict = get_biomodels_informations_for_database(run_choice['pref_file_list'][i])\n" \
                            F"\t\tanimal_variable_list.append_new_habitat_variable(information_model_dict['code_biological_model'], " \
                            F"run_choice['stage_list'][i], run_choice['hyd_opt'][i], run_choice['sub_opt'][i], " \
                            F"information_model_dict['aquatic_animal_type'], information_model_dict['model_type'], " \
                            F"run_choice['pref_file_list'][i])\n"
        cmd_str = cmd_str + F"\tcalc_hab_and_output(hab_filename={repr(self.hdf5_file)}, " \
                            F"animal_variable_list=animal_variable_list, " \
                            F"progress_value=Value('d', 0), " \
                            F"q=Queue(), " \
                            F"print_cmd=True, " \
                            F"project_properties=load_project_properties({repr(path_prj_script)}))" + "\n"
        self.send_log.emit("py" + cmd_str)


if __name__ == '__main__':
    pass
