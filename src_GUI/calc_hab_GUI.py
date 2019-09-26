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
from multiprocessing import Process, Queue, Value

from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QHBoxLayout, \
    QComboBox, QTableWidget, \
    QSizePolicy, QFrame, QCheckBox, QWidget

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src_GUI import estimhab_GUI
from src import calcul_hab_mod
from src import hdf5_mod
from src.project_manag_mod import load_project_preferences
from src.user_preferences_mod import user_preferences
from src.bio_info_mod import get_name_stage_codebio_fromstr
from src.tools_mod import sort_homogoeneous_dict_list_by_on_key


class BioInfo(estimhab_GUI.StatModUseful):
    """
    This class contains the tab with the biological information (the curves of preference). It inherites from
    StatModUseful. StatModuseful is a QWidget, with some practical signal (send_log and show_fig) and some functions
    to find path_im and path_bio (the path where to save image) and to manage lists.
    """
    get_list_merge = pyqtSignal()
    """
     A Pyqtsignal which indicates to chronice_GUI.py that the merge list should be changed. In Main_Windows.py,
     the new list of merge file is found and send to the ChonicleGui class.
    """

    def __init__(self, path_prj, name_prj, lang='French'):
        super().__init__()
        self.tab_name = "calc hab"
        self.lang = lang
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.imfish = ''
        self.current_hab_informations_dict = None
        # find the path bio
        try:
            try:
                docxml = ET.parse(os.path.join(self.path_prj, self.name_prj + '.habby'))
                root = docxml.getroot()
            except IOError:
                self.send_log.emit("Warning: " + self.tr("The .habby project file does not exist."))
                return
        except ET.ParseError:
            self.send_log.emit("Warning: " + self.tr("The .habby project file is not well-formed."))
            return
        pathbio_child = root.find(".//Path_Bio")
        if pathbio_child is not None:
            if os.path.isdir(pathbio_child.text):
                self.path_bio = pathbio_child.text
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
        # self.name_database = 'pref_bio.db'
        self.timer = QTimer()
        self.running_time = 0
        self.timer.timeout.connect(self.show_prog)
        self.plot_new = False
        self.tooltip = []  # the list with tooltip of merge file (useful for chronicle_GUI.py)
        self.ind_current = None
        self.general_option_hyd_combobox_index = 0
        self.general_option_sub_combobox_index = 0

        self.default_color = "#A6C313"  # "#A6C313"  # #A6C313 (green Irstea)
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

        self.p = Process(target=None)  # second process

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
        l0 = QLabel(self.tr('<b> Habitat file(s) </b>'))
        self.m_all = QComboBox()
        self.m_all.currentTextChanged.connect(lambda: self.fill_selected_models_listwidets([]))
        self.m_all.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        # create lists with the possible fishes
        # right buttons for both QListWidget managed in the MainWindows class
        self.explore_bio_model_pushbutton = QPushButton(self.tr('Add models'))
        self.explore_bio_model_pushbutton.setObjectName("calc_hab")
        self.explore_bio_model_pushbutton.clicked.connect(self.open_bio_model_explorer)

        self.remove_all_bio_model_pushbutton = QPushButton(self.tr("Remove all models"))
        self.remove_all_bio_model_pushbutton.clicked.connect(self.remove_all_fish)

        self.remove_sel_bio_model_pushbutton = QPushButton(self.tr("Remove selected models"))
        self.remove_sel_bio_model_pushbutton.clicked.connect(self.remove_sel_fish)

        self.create_duplicate_from_selection_pushbutton = QPushButton(self.tr("Create duplciate from selection"))
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
            #self.general_option_hyd_combobox.setStyle(QCommonStyle())
        self.general_option_hyd_combobox.activated.connect(self.set_once_all_hyd_combobox)
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

        self.runhab = QPushButton(self.tr('Compute Habitat Value'))
        self.runhab.setStyleSheet("background-color: #47B5E6; color: black")
        self.runhab.clicked.connect(self.run_habitat_value)

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
        self.update_merge_list()

        # empty frame scrolable
        content_widget = QFrame()

        # layout
        self.layout4 = QGridLayout(content_widget)
        layout_prov_input = QHBoxLayout()
        layout_prov_input.addWidget(l0)
        layout_prov_input.addWidget(self.m_all)
        self.layout4.addLayout(layout_prov_input, 0, 0, 1, 4, Qt.AlignLeft)  #

        layout_prov = QGridLayout()
        layout_prov.addWidget(self.explore_bio_model_pushbutton, 0, 0)
        layout_prov.addWidget(self.create_duplicate_from_selection_pushbutton, 1, 0)
        layout_prov.addWidget(self.remove_all_bio_model_pushbutton, 0, 1)
        layout_prov.addWidget(self.remove_sel_bio_model_pushbutton, 1, 1)
        layout_prov.addWidget(self.remove_duplicate_model_pushbutton, 2, 1)
        self.layout4.addLayout(layout_prov, 1, 0, 1, 4, Qt.AlignLeft)  #

        # 1 column
        self.layout4.addWidget(self.bio_model_choosen_title_label, 2, 0)
        self.layout4.addWidget(self.selected_aquatic_animal_qtablewidget, 3, 0)
        # 2 column
        layout_prov2 = QHBoxLayout()
        layout_prov2.addWidget(QLabel(self.tr("hydraulic mode")))
        layout_prov2.addWidget(self.general_option_hyd_combobox)
        self.layout4.addLayout(layout_prov2, 2, 1)
        self.layout4.addWidget(self.hyd_mode_qtablewidget, 3, 1)
        # 3 column
        layout_prov3 = QHBoxLayout()
        layout_prov3.addWidget(QLabel(self.tr("substrate mode")))
        layout_prov3.addWidget(self.general_option_sub_combobox)
        self.layout4.addLayout(layout_prov3, 2, 2)
        self.layout4.addWidget(self.sub_mode_qtablewidget, 3, 2)

        # 4e column
        self.layout4.addWidget(self.exist_title_label, 2, 3)
        self.layout4.addWidget(self.presence_qtablewidget, 3, 3, 1, 1)

        # 5e column
        self.layout4.addWidget(self.presence_scrollbar, 3, 4, 1, 1)

        self.layout4.addWidget(self.runhab, 5, 2, 1, 3, Qt.AlignRight)
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
        # load selected_aquatic_animal_dict in xml project
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        doc = ET.parse(fname)
        root = doc.getroot()
        # geo data
        child1 = root.find('.//selected_aquatic_animal_list_calc_hab')
        if child1 is not None:
            self.selected_aquatic_animal_dict = eval(child1.text)
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
                index_fish = user_preferences.biological_models_dict["cd_biological_model"].index(code_bio_model)
                # get stage index
                index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)
                default_hydraulic_type = user_preferences.biological_models_dict["hydraulic_type"][index_fish][index_stage]
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
                index_fish = user_preferences.biological_models_dict["cd_biological_model"].index(code_bio_model)
                # get stage index
                index_stage = user_preferences.biological_models_dict["stage_and_size"][index_fish].index(stage)
                default_substrate_type = user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage]
                # set positon to combobox
                self.sub_mode_qtablewidget.cellWidget(index, 0).setCurrentIndex(
                    substrate_type_available.index(default_substrate_type))
            if not default:
                if new_sub_str in substrate_type_available:
                    # set positon to combobox
                    self.sub_mode_qtablewidget.cellWidget(index, 0).setCurrentIndex(substrate_type_available.index(new_sub_str))

    def color_hyd_combobox(self):
        """
        if one of hydraulic qtablewidget comboboxs changed : color of combobox current item is changed
        """
        model_index = int(self.sender().objectName())
        new_hyd_mode_index = self.sender().currentIndex()

        self.get_current_hab_informations()

        # get info
        item_str = self.selected_aquatic_animal_qtablewidget.cellWidget(model_index, 0).text()
        name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
        index_fish = user_preferences.biological_models_dict["cd_biological_model"].index(code_bio_model)
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

    def check_if_model_exist_in_hab(self, model_index):
        # 1 column
        item_str = self.selected_aquatic_animal_qtablewidget.cellWidget(model_index, 0).text()
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
        self.get_current_hab_informations()
        for model_index in range(self.selected_aquatic_animal_qtablewidget.rowCount()):
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
        item_str = self.selected_aquatic_animal_qtablewidget.cellWidget(model_index, 0).text()
        name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
        index_fish = user_preferences.biological_models_dict["cd_biological_model"].index(code_bio_model)
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
            # index_to_keep = [new_item_text_dict["selected_aquatic_animal_list"].index(x) for x in new_item_text_dict["selected_aquatic_animal_list"] if x not in self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]]
            # self.selected_aquatic_animal_dict["selected_aquatic_animal_list"].extend([new_item_text_dict["selected_aquatic_animal_list"][i] for i in index_to_keep])
            # self.selected_aquatic_animal_dict["hydraulic_mode_list"].extend([new_item_text_dict["hydraulic_mode_list"][i] for i in index_to_keep])
            # self.selected_aquatic_animal_dict["substrate_mode_list"].extend([new_item_text_dict["substrate_mode_list"][i] for i in index_to_keep])
            # self.selected_aquatic_animal_dict = sort_homogoeneous_dict_list_by_on_key(self.selected_aquatic_animal_dict, "selected_aquatic_animal_list")
            self.selected_aquatic_animal_dict["selected_aquatic_animal_list"].extend(new_item_text_dict["selected_aquatic_animal_list"])
            self.selected_aquatic_animal_dict["hydraulic_mode_list"].extend(new_item_text_dict["hydraulic_mode_list"])
            self.selected_aquatic_animal_dict["substrate_mode_list"].extend(new_item_text_dict["substrate_mode_list"])
            self.selected_aquatic_animal_dict = sort_homogoeneous_dict_list_by_on_key(self.selected_aquatic_animal_dict, "selected_aquatic_animal_list")

        # get_current_hab_informations
        self.get_current_hab_informations()

        # total_item
        total_item = len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"])

        # clear
        self.selected_aquatic_animal_qtablewidget.clear()
        self.hyd_mode_qtablewidget.clear()
        self.sub_mode_qtablewidget.clear()
        self.presence_qtablewidget.clear()

        # if .hab :
        if self.current_hab_informations_dict:
            self.selected_aquatic_animal_qtablewidget.setRowCount(total_item)
            self.hyd_mode_qtablewidget.setRowCount(total_item)
            self.sub_mode_qtablewidget.setRowCount(total_item)
            self.presence_qtablewidget.setRowCount(total_item)

            # block HEM
            if not self.current_hab_informations_dict["dimension_ok"] or not self.current_hab_informations_dict["z_presence_ok"]:  # not 2d or not z
                self.general_option_hyd_combobox.model().item(self.all_hyd_choice.index("HEM")).setEnabled(False)
                self.send_log.emit("NB: " + self.tr("Hydraulic HEM computation option is disable for habitat calculation  (hydraulic data in .hab are not of 2D type or do not contain z-values)."))
            else:
                self.general_option_hyd_combobox.model().item(self.all_hyd_choice.index("HEM")).setEnabled(True)

            # block_percentage
            if not self.current_hab_informations_dict["percentage_ok"]:
                self.general_option_sub_combobox.model().item(self.all_sub_choice.index("Percentage")).setEnabled(False)
                self.send_log.emit("NB: " + self.tr("Substrate percentage computation option is disable for habitat calculation (substrate classification method in .hab is not in percentage)."))
            else:
                self.general_option_sub_combobox.model().item(self.all_sub_choice.index("Percentage")).setEnabled(True)

            # add new item if not exist
            for index, item_str in enumerate(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"]):
                # add label item
                self.selected_aquatic_animal_qtablewidget.setCellWidget(index, 0, QLabel(item_str))
                self.selected_aquatic_animal_qtablewidget.setRowHeight(index, 27)

                # get info
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(item_str)
                index_fish = user_preferences.biological_models_dict["cd_biological_model"].index(code_bio_model)
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
                else:
                    item_combobox_hyd.setStyleSheet(self.combobox_style_user)
                item_combobox_hyd.model().item(default_choice_index).setBackground(QColor(self.default_color))
                if not self.current_hab_informations_dict["dimension_ok"] or not self.current_hab_informations_dict["z_presence_ok"]:  # not 2d or not z
                    if "HEM" in hydraulic_type_available:
                        item_combobox_hyd.model().item(hydraulic_type_available.index("HEM")).setEnabled(False)
                item_combobox_hyd.setCurrentIndex(choosen_index)
                item_combobox_hyd.currentIndexChanged.connect(self.color_hyd_combobox)
                item_combobox_hyd.activated.connect(self.change_general_hyd_combobox)
                # add combobox item
                self.hyd_mode_qtablewidget.setCellWidget(index, 0, item_combobox_hyd)
                self.hyd_mode_qtablewidget.setRowHeight(index, 27)

                """ SUB """
                # # change language
                # for num in range(len(user_preferences.biological_models_dict["substrate_type_available"][index_fish][index_stage])):
                #     user_preferences.biological_models_dict["substrate_type_available"][index_fish][index_stage][num] = self.tr(user_preferences.biological_models_dict["substrate_type_available"][index_fish][index_stage][num])
                # user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage] = self.tr(
                #         user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage])
                # get default_substrate_type
                substrate_type_available = user_preferences.biological_models_dict["substrate_type_available"][index_fish][index_stage]

                # create combobox
                item_combobox_sub = QComboBox()
                item_combobox_sub.setObjectName(str(index))
                item_combobox_sub.addItems(substrate_type_available)
                choosen_index = self.selected_aquatic_animal_dict["substrate_mode_list"][index]
                default_choice_index = substrate_type_available.index(user_preferences.biological_models_dict["substrate_type"][index_fish][index_stage])
                if choosen_index == default_choice_index:
                    item_combobox_sub.setStyleSheet(self.combobox_style_default)
                else:
                    item_combobox_sub.setStyleSheet(self.combobox_style_user)
                item_combobox_sub.model().item(default_choice_index).setBackground(QColor(self.default_color))
                if not self.current_hab_informations_dict["percentage_ok"]:
                    if "Percentage" in substrate_type_available:
                        item_combobox_sub.model().item(substrate_type_available.index("Percentage")).setEnabled(False)
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

    def create_duplicate_from_selection(self):
        # selected items
        index_to_duplicate_list = [item.row() for item in self.selected_aquatic_animal_qtablewidget.selectedIndexes()]

        if index_to_duplicate_list:
            # get items
            for index in index_to_duplicate_list:
                # get text
                label = self.selected_aquatic_animal_qtablewidget.cellWidget(index, 0)
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
        if self.m_all.currentText():
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, self.m_all.currentText())
            hdf5.open_hdf5_file(False)

            # init
            required_dict = dict(
                dimension_ok=False,
                z_presence_ok=False,
                percentage_ok=False,
                fish_list=[])

            if hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hyd model dimension")] == "2":
                required_dict["dimension_ok"] = True
            if "z" in hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hyd variables list")]:
                required_dict["z_presence_ok"] = True
            if "percentage" in hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("sub classification method")]:
                required_dict["percentage_ok"] = True
            required_dict["fish_list"] = hdf5.fish_list

            self.current_hab_informations_dict = required_dict

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

    def save_selected_aquatic_animal_list_calc_hab(self):
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
            selected_aquatic_animal_list_calc_hab = dict(selected_aquatic_animal_list=self.selected_aquatic_animal_dict["selected_aquatic_animal_list"],
                                                         hydraulic_mode_list=hydraulic_mode_list,
                                                         substrate_mode_list=substrate_mode_list,
                                                         general_hyd_sub_combobox_index=[self.general_option_hyd_combobox.currentIndex(),
                                                                                         self.general_option_sub_combobox.currentIndex()])

            # save in xml project
            fname = os.path.join(self.path_prj, self.name_prj + '.habby')
            doc = ET.parse(fname)
            root = doc.getroot()
            # geo data
            child1 = root.find('.//selected_aquatic_animal_list_calc_hab')
            if child1 is None:
                child1 = ET.SubElement(root, 'selected_aquatic_animal_list_calc_hab')
                child1.text = str(selected_aquatic_animal_list_calc_hab)
            else:
                child1.text = str(selected_aquatic_animal_list_calc_hab)
            doc.write(fname)

    def update_merge_list(self):
        """
        This function goes in the projet xml file and gets all available merged data. Usually, it is called
        by Substrate() (when finished to merge some data) or at the start of HABBY.

        We add a "tooltip" which indicates the orginal hydraulic and substrate files.
        """

        xmlfile = os.path.join(self.path_prj, self.name_prj + '.habby')
        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                self.send_log.emit("Warning: " + self.tr("The .habby project file does not exist."))
                return
        except ET.ParseError:
            self.send_log.emit("Warning: " + self.tr("The .habby project file is not well-formed."))
            return

        self.m_all.blockSignals(True)
        self.m_all.clear()
        self.tooltip = []
        self.hdf5_merge = []

        # get filename
        files = root.findall('.//hdf5_habitat')
        files = reversed(files)  # get the newest first

        path_hdf5 = self.find_path_hdf5_est()

        # add it to the list
        if files is not None:
            for idx, f in enumerate(files):
                if os.path.isfile(os.path.join(path_hdf5, f.text)):
                    [sub_ini, hydro_ini] = hdf5_mod.get_initial_files(path_hdf5, f.text)
                    hydro_ini = os.path.basename(hydro_ini)
                    textini = 'Hydraulic: ' + hydro_ini + '\nSubstrate :' + sub_ini
                    if len(f.text) < 55:
                        self.m_all.addItem(f.text)
                    else:
                        blob = f.text[:55] + '...'
                        self.m_all.addItem(blob)
                    self.m_all.setItemData(idx, textini, Qt.ToolTipRole)
                    self.tooltip.append(textini)
                    name = f.text
                    self.hdf5_merge.append(name)
                else:
                    self.send_log.emit("Warning: " + f.text + self.tr(", this .hab file has been deleted by the user."))
                    # TODO : It will be deleted from the .xml file.
        # a signal to indicates to Chronicle_GUI.py to update the merge file
        self.get_list_merge.emit()

        self.m_all.blockSignals(False)

        # check_uncheck_allmodels_presence
        self.fill_selected_models_listwidets([])

    def run_habitat_value(self):
        """
        This function runs HABBY to get the habitat value based on the data in a "merged" hdf5 file and the chosen
        preference files.

        We should not add a comma in the name of the selected fish.
        """

        # disable the button
        self.runhab.setDisabled(True)
        self.send_log.emit(self.tr('# Calculating: habitat value...'))

        # get the figure options and the type of output to be created
        project_preferences = load_project_preferences(self.path_prj, self.name_prj)

        # remove duplicate
        self.remove_duplicates()

        # get the name of the xml biological file of the selected fish and the stages to be analyzed
        pref_list = []
        stages_chosen = []
        name_fish_list = []
        hyd_opt_list = []
        sub_opt_list = []
        name_fish_sh = []  # because max 10 characters in attribute table of shapefile
        name_fish_sel = ''  # for the xml project file
        aquatic_animal_type = []
        xmlfiles = []
        for i in range(len(self.selected_aquatic_animal_dict["selected_aquatic_animal_list"])):
            # check if not exist
            if not self.presence_qtablewidget.cellWidget(i, 0).layout().itemAt(0).widget().isChecked():
                # get info from 1 list widget
                label = self.selected_aquatic_animal_qtablewidget.cellWidget(i, 0)
                fish_item_text = label.text()
                name_fish, stage, code_bio_model = get_name_stage_codebio_fromstr(fish_item_text)
                name_fish_sel += fish_item_text + ","
                name_fish_list.append(code_bio_model)
                index_fish = user_preferences.biological_models_dict["cd_biological_model"].index(code_bio_model)
                pref_list.append(user_preferences.biological_models_dict["path_xml"][index_fish])
                stages_chosen.append(stage)
                name_fish_sh_text = code_bio_model + "_" + stage
                name_fish_sh.append(name_fish_sh_text)
                # name_fish_sel += name_fish + ','
                xmlfiles.append(user_preferences.biological_models_dict["path_xml"][index_fish].split("\\")[-1])
                # get info from 2 list widget
                hyd_opt_list.append(self.hyd_mode_qtablewidget.cellWidget(i, 0).currentText())
                # get info from 3 list widget
                sub_opt_list.append(self.sub_mode_qtablewidget.cellWidget(i, 0).currentText())
                aquatic_animal_type.append(user_preferences.biological_models_dict["aquatic_animal_type"][index_fish])

        if xmlfiles:
            # save the selected fish in the xml project file
            try:
                try:
                    filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
                    docxml = ET.parse(filename_path_pro)
                    root = docxml.getroot()
                except IOError:
                    self.send_log.emit("Warning: " + self.tr("The .habby project file does not exist \n"))
                    return
            except ET.ParseError:
                self.send_log.emit("Warning: " + self.tr("The .habby project file is not well-formed.\n"))
                return
            hab_child = root.find(".//Habitat")
            if hab_child is None:
                blob = ET.SubElement(root, "Habitat")
                hab_child = root.find(".//Habitat")
            fish_child = root.find(".//Habitat/Fish_Selected")
            if fish_child is None:
                blob = ET.SubElement(hab_child, "Fish_Selected")
                fish_child = root.find(".//Habitat/Fish_Selected")
            fish_child.text = name_fish_sel[:-1]  # last comma
            docxml.write(filename_path_pro)

            # get the name of the merged file
            path_hdf5 = self.find_path_hdf5_est()
            ind = self.m_all.currentIndex()
            if len(self.hdf5_merge) > 0:
                hdf5_file = self.hdf5_merge[ind]
            else:
                self.runhab.setDisabled(False)
                self.send_log.emit('Error: ' + self.tr('No merged hydraulic files available.'))
                return

            # show progressbar
            self.nativeParentWidget().progress_bar.setRange(0, 100)
            self.nativeParentWidget().progress_bar.setValue(0)
            self.nativeParentWidget().progress_bar.setVisible(True)

            # get the path where to save the different outputs (function in estimhab_GUI.py)
            path_txt = self.find_path_text_est()
            path_im = self.find_path_im_est()
            path_shp = self.find_path_output_est("Path_Shape")
            path_para = self.find_path_output_est("Path_Visualisation")

            # get the type of option choosen for the habitat calculation
            run_choice = dict(hyd_opt=hyd_opt_list,
                              sub_opt=sub_opt_list)

            # only useful if we want to also show the 2d figure in the GUI
            self.hdf5_file = hdf5_file
            self.path_hdf5 = path_hdf5
            path_im_bioa = os.path.join(os.getcwd(), self.path_im_bio)

            # send the calculation of habitat and the creation of output
            self.timer.start(100)  # to refresh progress info
            self.q4 = Queue()
            self.progress_value = Value("i", 0)
            self.p = Process(target=calcul_hab_mod.calc_hab_and_output,
                             args=(hdf5_file, path_hdf5, pref_list, stages_chosen,
                                   name_fish_list, name_fish_sh, run_choice,
                                   self.path_bio, path_txt, self.progress_value,
                                   self.q4, False, project_preferences, aquatic_animal_type,
                                   xmlfiles))
            self.p.name = "Habitat calculation"
            self.p.start()

            # log
            self.send_log.emit("py    file1='" + hdf5_file + "'")
            self.send_log.emit("py    path1= os.path.join(path_prj, 'hdf5')")
            self.send_log.emit("py    pref_list= ['" + "', '".join(pref_list) + "']")
            self.send_log.emit("py    stages= ['" + "', '".join(stages_chosen) + "']")
            self.send_log.emit("py    type=" + str(run_choice))
            self.send_log.emit("py    name_fish1 = ['" + "', '".join(name_fish) + "']")
            self.send_log.emit("py    name_fish2 = ['" + "', '".join(name_fish_sh) + "']")
            self.send_log.emit(
                "py    calcul_hab.calc_hab_and_output(file1, path1 ,pref_list, stages, name_fish1, name_fish2, type, "
                "path_bio, path_prj, path_prj, path_prj, path_prj, [], True, [])")
            self.send_log.emit("restart RUN_HABITAT")
            self.send_log.emit("restart    file1: " + hdf5_file)
            self.send_log.emit("restart    list of preference file: " + ",".join(pref_list))
            self.send_log.emit("restart    stages chosen: " + ",".join(stages_chosen))
            self.send_log.emit("restart    type of calculation: " + str(run_choice))
        else:
            # disable the button
            self.runhab.setDisabled(False)
            self.send_log.emit(self.tr('Warning: Nothing to compute ! Models selected and their options exist in .hab'))

    def show_prog(self):
        """
        This function is linked with the timer started in run_habitat_value. It is run regulary and
        check if the function on the second thread have finised created the figures. If yes,
        this function create the 1d figure for the HABBY GUI.
        """

        # say in the Stauts bar that the processus is alive
        if self.p.is_alive():
            self.running_time += 0.100  # this is useful for GUI to update the running, should be logical with self.Timer()
            # get the langugage
            project_preferences = load_project_preferences(self.path_prj, self.name_prj)
            # send the message
            self.send_log.emit(self.tr("Process 'Habitat computation' is alive and run since ") + str(round(self.running_time)) + " sec.")
            self.nativeParentWidget().progress_bar.setValue(int(self.progress_value.value))
            self.nativeParentWidget().kill_process.setVisible(True)

        # when the loading is finished
        if not self.q4.empty():
            self.timer.stop()
            self.mystdout = self.q4.get()
            self.send_err_log()

            # give the possibility of sending a new simulation
            self.runhab.setDisabled(False)

            self.send_log.emit(self.tr('Habitat computation is finished (computation time = ') + str(
                round(self.running_time)) + " s).")
            self.send_log.emit(self.tr("Figures and files can be displayed and exported from 'Data explorer' tab."))

            # put the timer back to zero and clear status bar
            self.running_time = 0
            self.send_log.emit(self.tr("clear status bar"))
            self.plot_new = False
            # refresh plot gui list file
            self.nativeParentWidget().central_widget.data_explorer_tab.refresh_filename()
            self.nativeParentWidget().central_widget.tools_tab.refresh_hab_filenames()
            self.running_time = 0
            self.nativeParentWidget().kill_process.setVisible(False)
            # check_uncheck_allmodels_presence
            self.check_uncheck_allmodels_presence()

        if not self.p.is_alive():
            # enable the button to call this functin directly again
            self.timer.stop()

            # give the possibility of sending a new simulation
            self.runhab.setDisabled(False)
            self.nativeParentWidget().kill_process.setVisible(False)

            # put the timer back to zero
            self.running_time = 0
            self.send_log.emit(self.tr("clear status bar"))
            # check_uncheck_allmodels_presence
            self.check_uncheck_allmodels_presence()


if __name__ == '__main__':
    pass
