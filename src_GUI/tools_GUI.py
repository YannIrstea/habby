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
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication, QVariant, QAbstractTableModel
from PyQt5.QtWidgets import QPushButton, QLabel, QListWidget, QAbstractItemView, QSpacerItem, \
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, QLineEdit, QGridLayout ,\
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QProgressBar, QTextEdit, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from src_GUI import preferences_GUI
from src_GUI import data_explorer_GUI
from src import hdf5_mod
from src import plot_mod
from src import tools_mod

from multiprocessing import Process, Queue, Value
import os


class ToolsTab(QScrollArea):
    """
    This class contains the tab with Graphic production biological information (the curves of preference).
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQt signal to send the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.mystdout = None
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.msg2 = QMessageBox()
        self.plot_list_combobox = QComboBox()
        self.plot_previous_button = QPushButton("<<")
        self.plot_next_button = QPushButton(">>")
        self.plot_wigdet_layout = QHBoxLayout()
        self.init_iu()

    def init_iu(self):
        # DataExplorerFrame
        self.tools_frame = ToolsFrame()

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # add layout
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(self.tools_frame)

        # refresh habi filenames
        self.refresh_hab_filenames()

    def refresh_hab_filenames(self):
        # get list of file name by type
        names = hdf5_mod.get_filename_by_type("habitat", os.path.join(self.path_prj, "hdf5"))
        self.tools_frame.hab_filenames_qcombobox.clear()
        if names:
            # change list widget
            self.tools_frame.hab_filenames_qcombobox.addItems(names)


class ToolsFrame(QFrame):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """ Available data """
        # First layout
        self.habitat_filenames_qlabel = QLabel(self.tr('habitat filenames'))
        self.hab_filenames_qcombobox = QComboBox()
        self.hab_filenames_qcombobox.currentIndexChanged.connect(self.names_hab_change)
        self.fish_available_qlabel = QLabel(self.tr('available fish'))
        self.fish_available_qlistwidget = QListWidget()
        self.fish_available_qlistwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.export_empty_text_pushbutton = QPushButton(self.tr("export empty required text file"))
        self.available_firstlayout = QVBoxLayout()
        self.available_firstlayout.setAlignment(Qt.AlignTop)
        self.available_firstlayout.addWidget(self.habitat_filenames_qlabel)
        self.available_firstlayout.addWidget(self.hab_filenames_qcombobox)
        self.available_firstlayout.addWidget(self.fish_available_qlabel)
        self.available_firstlayout.addWidget(self.fish_available_qlistwidget)
        self.available_firstlayout.addWidget(self.export_empty_text_pushbutton)

        # second layout
        self.available_units_qlabel = QLabel(self.tr('available units'))
        self.available_units_qlistwidget = QListWidget()
        self.available_units_qlistwidget.setMinimumWidth(50)
        self.available_units_qlistwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.available_second_layout = QVBoxLayout()
        self.available_second_layout.setAlignment(Qt.AlignTop)
        self.available_second_layout.addWidget(self.available_units_qlabel)
        self.available_second_layout.addWidget(self.available_units_qlistwidget)

        """ Required data """
        # txt layout
        self.fromtext_group = QGroupBox(self.tr("from .txt file"))
        self.fromtext_qpushbutton = QPushButton(self.tr('choose .txt file'))
        fromtext_layout = QHBoxLayout()
        fromtext_layout.addWidget(self.fromtext_qpushbutton)
        self.fromtext_group.setLayout(fromtext_layout)

        # sequence layout
        self.fromsequence_group = QGroupBox(self.tr("from a sequence"))
        self.from_qlabel = QLabel(self.tr('from'))
        self.from_qlineedit = QLineEdit()
        self.to_qlabel = QLabel(self.tr('to'))
        self.to_qlineedit = QLineEdit()
        self.by_qlabel = QLabel(self.tr('by'))
        self.by_qlineedit = QLineEdit()
        self.by_qlineedit.returnPressed.connect(self.display_required_units_from_sequence)
        require_secondlayout = QGridLayout()
        require_secondlayout.addWidget(self.from_qlabel, 1, 0)
        require_secondlayout.addWidget(self.from_qlineedit, 1, 1)
        require_secondlayout.addWidget(self.to_qlabel, 1, 2)
        require_secondlayout.addWidget(self.to_qlineedit, 1, 3)
        require_secondlayout.addWidget(self.by_qlabel, 1, 4)
        require_secondlayout.addWidget(self.by_qlineedit, 1, 5)
        self.fromsequence_group.setLayout(require_secondlayout)

        # units layout
        self.require_units_qlabel = QLabel(self.tr('requied units and interpolated habitat values'))
        self.require_unit_qtableview = QTableView()
        self.require_unit_qtableview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.require_unit_qtableview.verticalHeader().setVisible(True)
        self.require_unit_qtableview.horizontalHeader().setVisible(True)

        # # hv layout
        # self.require_hv_qlabel = QLabel(self.tr('hv interpolated'))
        # self.require_hv_qtableview = QTableView()

        """ Available data """
        available_data_layout = QHBoxLayout()
        available_data_layout.addLayout(self.available_firstlayout, 4)
        available_data_layout.addLayout(self.available_second_layout, 1)
        available_data_group = QGroupBox(self.tr("Available data"))
        available_data_group.setLayout(available_data_layout)

        """ Required data """
        require_data_layout = QVBoxLayout()
        require_data_group = QGroupBox(self.tr("Required data"))
        require_data_group.setLayout(require_data_layout)

        require_first_layout = QHBoxLayout()
        require_first_layout.addWidget(self.fromtext_group)
        require_first_layout.addWidget(self.fromsequence_group)
        require_data_layout.addLayout(require_first_layout)

        require_unit_layout = QVBoxLayout()
        require_unit_layout.addWidget(self.require_units_qlabel)
        require_unit_layout.addWidget(self.require_unit_qtableview)

        # require_hv_layout = QVBoxLayout()
        # require_hv_layout.addWidget(self.require_hv_qlabel)
        # require_hv_layout.addWidget(self.require_hv_qtableview)

        unit_hv_layout = QHBoxLayout()
        unit_hv_layout.addLayout(require_unit_layout)
        # unit_hv_layout.addLayout(require_hv_layout)
        require_data_layout.addLayout(unit_hv_layout)

        """ glabal layout """
        hbox_layout = QHBoxLayout()
        hbox_layout.addWidget(available_data_group)
        hbox_layout.addWidget(require_data_group)
        global_layout = QVBoxLayout(self)
        global_layout.addLayout(hbox_layout)
        spacer = QSpacerItem(1, 200)
        global_layout.addItem(spacer)

        # add layout to group
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def names_hab_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        hdf5name = self.hab_filenames_qcombobox.currentText()
        if hdf5name:
            self.available_units_qlistwidget.clear()
            self.fish_available_qlistwidget.clear()

            # create hdf5 class
            hdf5_management = hdf5_mod.Hdf5Management(self.parent().parent().path_prj,
                                                      hdf5name)
            # get variables
            fish_list = hdf5_management.get_hdf5_fish_names()

            # get units
            units_name = hdf5_management.get_hdf5_units_name()

            # hab
            if fish_list:
                self.fish_available_qlistwidget.addItems(fish_list)
                self.fish_available_qlistwidget.selectAll()
            if units_name:
                self.available_units_qlistwidget.addItems(units_name)
                # set min and max unit for from to by
                unit_num = list(map(float, units_name))
                min_unit = min(unit_num)
                max_unit = max(unit_num)
                self.from_qlineedit.setText(str(min_unit))
                self.to_qlineedit.setText(str(max_unit))

    def display_required_units_from_sequence(self):
        # from
        from_sequ = float(self.from_qlineedit.text())
        # to
        to_sequ = float(self.to_qlineedit.text())
        # by
        by_sequ = float(self.by_qlineedit.text())

        # range
        unit_list = list(frange(from_sequ, to_sequ, by_sequ))

        # dict
        unit_dict = dict(units=unit_list)

        # display
        self.create_model_array_and_display(unit_dict)

    def create_model_array_and_display(self, dict_values):
        # get fish selected
        selection = self.fish_available_qlistwidget.selectedItems()
        fish_names = [item.text() for item in selection]

        # get unit required
        unit_list = list(dict_values["units"])

        # get filename
        hdf5name = self.hab_filenames_qcombobox.currentText()

        # load hdf5 data
        hdf5_management = hdf5_mod.Hdf5Management(self.parent().parent().path_prj,
                                                  hdf5name)
        data_2d, data_description = hdf5_management.load_hdf5_hab(whole_profil=False, fish_names=fish_names)

        data_to_table, horiz_headers, vertical_headers = tools_mod.compute_interpolation(data_description,
                                                                                         fish_names,
                                                                                         dict_values)

        # model data for table view
        tablemodel = QStandardItemModel()
        for row_index in range(len(vertical_headers)):
            line_string_list = []
            for column_index in range(len(horiz_headers)):
                line_string_list.append(QStandardItem(data_to_table[row_index][column_index]))
            tablemodel.appendRow(line_string_list)
        # headers
        horiz_headers = [head.replace("_", "\n") for head in horiz_headers]
        tablemodel.setHorizontalHeaderLabels(horiz_headers)
        tablemodel.setVerticalHeaderLabels(vertical_headers)

        # set model
        self.require_unit_qtableview.setModel(tablemodel)
        # ajust width
        header = self.require_unit_qtableview.horizontalHeader()
        for i in range(len(horiz_headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.require_unit_qtableview.verticalHeader().setDefaultSectionSize(
            self.require_unit_qtableview.verticalHeader().minimumSectionSize())


def frange(start, stop, step):
    i = start
    while i < stop:
        yield i
        i += step


