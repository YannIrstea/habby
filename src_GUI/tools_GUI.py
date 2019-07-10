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
    QComboBox, QMessageBox, QFrame, QCheckBox, QHeaderView, QLineEdit, QGridLayout , QFileDialog,\
    QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy, QScrollArea, QProgressBar, QTextEdit, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import os
import numpy as np
from src_GUI import preferences_GUI
from src import hdf5_mod
from src import tools_mod
from src import plot_mod


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
        self.tab_name = "tools"
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

        # tools frame
        tools_frame = QFrame()
        tools_frame.setFrameShape(QFrame.NoFrame)
        tools_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # interpolation group
        self.interpolation_group = InterpolationGroup(self.path_prj, self.name_prj, self.send_log)
        self.interpolation_group.setChecked(True)

        # other tool
        self.newtool_group = OtherToolToCreate(self.path_prj, self.name_prj, self.send_log)
        self.newtool_group.setChecked(False)

        # vertical layout
        self.setWidget(tools_frame)
        global_layout = QVBoxLayout(self)
        global_layout.setAlignment(Qt.AlignTop)
        tools_frame.setLayout(global_layout)
        global_layout.addWidget(self.interpolation_group)
        global_layout.addWidget(self.newtool_group)

        # refresh habi filenames
        self.refresh_hab_filenames()

    def refresh_hab_filenames(self):
        # get list of file name by type
        names = hdf5_mod.get_filename_by_type("habitat", os.path.join(self.path_prj, "hdf5"))
        self.interpolation_group.hab_filenames_qcombobox.clear()
        if names:
            # append_empty_element_to_list
            names = [""] + names
            # change list widget
            self.interpolation_group.hab_filenames_qcombobox.addItems(names)


class QGroupBoxCollapsible(QGroupBox):
    def __init__(self):
        super().__init__()
        self.setCheckable(True)
        self.setStyleSheet(
            'QGroupBox::indicator:unchecked {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:hover {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:pressed {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:checked {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:checked:hover {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:checked:pressed {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:indeterminate:hover {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:indeterminate:pressed {image: url(translation//icon//triangle_black_open_50_50.png);}'
        )
        #'QGroupBox::indicator:checked:hover {image: url(translation//triangle_black_closed.png);}'
        self.toggled.connect(lambda: self.toggle_group(self))
        self.setChecked(True)

    def toggle_group(self, ctrl):
        state = ctrl.isChecked()
        if state:
            ctrl.setFixedHeight(ctrl.sizeHint().height())
        else:
            ctrl.setFixedHeight(30)


class InterpolationGroup(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.init_ui()
        # Signal Connection

    def init_ui(self):
        # group title
        self.setTitle(self.tr("Interpolation tool"))

        """ Available data """
        habitat_filenames_qlabel = QLabel(self.tr('Select an habitat file'))
        self.hab_filenames_qcombobox = QComboBox()
        self.hab_filenames_qcombobox.currentIndexChanged.connect(self.names_hab_change)
        habitat_reach_qlabel = QLabel(self.tr("Select a reach if not done"))
        self.hab_reach_qcombobox = QComboBox()
        self.hab_reach_qcombobox.currentIndexChanged.connect(self.reach_hab_change)
        unit_min_title_qlabel = QLabel(self.tr("unit min :"))
        unit_max_title_qlabel = QLabel(self.tr("unit max :"))
        unit_type_title_qlabel = QLabel(self.tr("unit type :"))
        self.unit_min_qlabel = QLabel("")
        self.unit_max_qlabel = QLabel("")
        self.unit_type_qlabel = QLabel("")
        fish_available_qlabel = QLabel(self.tr('fish(s) :'))
        self.fish_available_qlistwidget = QListWidget()
        self.fish_available_qlistwidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.export_empty_text_pushbutton = QPushButton(self.tr("export empty required text file"))
        self.export_empty_text_pushbutton.clicked.connect(self.export_empty_text_file)

        available_firstlayout = QVBoxLayout()
        available_firstlayout.setAlignment(Qt.AlignTop)
        available_firstlayout.addWidget(habitat_filenames_qlabel)
        available_firstlayout.addWidget(self.hab_filenames_qcombobox)
        available_firstlayout.addWidget(habitat_reach_qlabel)
        available_firstlayout.addWidget(self.hab_reach_qcombobox)
        units_info_gridlayout = QGridLayout()
        available_firstlayout.addLayout(units_info_gridlayout)  # stretch factor
        available_firstlayout.addWidget(fish_available_qlabel)
        available_firstlayout.addWidget(self.fish_available_qlistwidget)
        available_firstlayout.addWidget(self.export_empty_text_pushbutton)
        units_info_gridlayout.addWidget(unit_min_title_qlabel, 0, 0)
        units_info_gridlayout.addWidget(unit_max_title_qlabel, 1, 0)
        units_info_gridlayout.addWidget(unit_type_title_qlabel, 2, 0)
        units_info_gridlayout.addWidget(self.unit_min_qlabel, 0, 1)
        units_info_gridlayout.addWidget(self.unit_max_qlabel, 1, 1)
        units_info_gridlayout.addWidget(self.unit_type_qlabel, 2, 1)

        """ Required data """
        # sequence layout
        fromsequence_group = QGroupBox(self.tr("from a sequence (press ENTER once the data has been entered)"))
        from_qlabel = QLabel(self.tr('from'))
        self.from_qlineedit = QLineEdit()
        self.from_qlineedit.returnPressed.connect(self.display_required_units_from_sequence)
        to_qlabel = QLabel(self.tr('to'))
        self.to_qlineedit = QLineEdit()
        self.to_qlineedit.returnPressed.connect(self.display_required_units_from_sequence)
        by_qlabel = QLabel(self.tr('by'))
        self.by_qlineedit = QLineEdit()
        self.by_qlineedit.returnPressed.connect(self.display_required_units_from_sequence)
        require_secondlayout = QGridLayout()
        require_secondlayout.addWidget(from_qlabel, 1, 0)
        require_secondlayout.addWidget(self.from_qlineedit, 1, 1)
        require_secondlayout.addWidget(to_qlabel, 1, 2)
        require_secondlayout.addWidget(self.to_qlineedit, 1, 3)
        require_secondlayout.addWidget(by_qlabel, 1, 4)
        require_secondlayout.addWidget(self.by_qlineedit, 1, 5)
        fromsequence_group.setLayout(require_secondlayout)

        # txt layout
        fromtext_group = QGroupBox(self.tr("from .txt file"))
        self.fromtext_qpushbutton = QPushButton(self.tr('choose .txt file'))
        self.fromtext_qpushbutton.clicked.connect(self.display_required_units_from_txtfile)
        fromtext_layout = QHBoxLayout()
        fromtext_layout.addWidget(self.fromtext_qpushbutton)
        fromtext_group.setLayout(fromtext_layout)

        # units layout
        require_units_qlabel = QLabel(self.tr('desired units and interpolated habitat values :'))
        self.require_unit_qtableview = QTableView()
        self.require_unit_qtableview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.require_unit_qtableview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.require_unit_qtableview.verticalHeader().setVisible(True)
        self.require_unit_qtableview.horizontalHeader().setVisible(True)
        mytablemodel = MyTableModel("", "", "", "")
        self.require_unit_qtableview.setModel(mytablemodel)
        self.plot_chronicle_qpushbutton = QPushButton(self.tr('View interpolate chronicle'))
        self.plot_chronicle_qpushbutton.clicked.connect(self.plot_chronicle)
        self.plot_chronicle_qpushbutton.setEnabled(False)
        self.export_txt_chronicle_qpushbutton = QPushButton(self.tr('Export interpolate chronicle'))
        self.export_txt_chronicle_qpushbutton.clicked.connect(self.export_chronicle)
        self.export_txt_chronicle_qpushbutton.setEnabled(False)

        """ Available data """
        available_data_layout = QHBoxLayout()
        available_data_layout.addLayout(available_firstlayout)
        available_data_group = QGroupBox(self.tr("Available data"))
        available_data_group.setLayout(available_data_layout)

        """ Required data """
        self.require_data_layout = QVBoxLayout()
        require_data_group = QGroupBox(self.tr("Desired data"))
        require_data_group.setLayout(self.require_data_layout)

        require_first_layout = QHBoxLayout()
        require_first_layout.addWidget(fromsequence_group)
        require_first_layout.addWidget(fromtext_group)
        self.require_data_layout.addLayout(require_first_layout)

        require_unit_layout = QVBoxLayout()
        require_unit_layout.addWidget(require_units_qlabel)
        require_unit_layout.addWidget(self.require_unit_qtableview)
        plot_export_layout = QHBoxLayout()
        plot_export_layout.addWidget(self.plot_chronicle_qpushbutton)
        plot_export_layout.addWidget(self.export_txt_chronicle_qpushbutton)
        require_unit_layout.addLayout(plot_export_layout)

        unit_hv_layout = QHBoxLayout()
        unit_hv_layout.addLayout(require_unit_layout)
        self.require_data_layout.addLayout(unit_hv_layout)

        """ interpolation layout """
        hbox_layout = QHBoxLayout()
        hbox_layout.addWidget(available_data_group, 1)  # stretch factor
        hbox_layout.addWidget(require_data_group, 3)  # stretch factor
        self.setLayout(hbox_layout)

    def disable_and_clean_group_widgets(self, checker):
        # available
        self.unit_min_qlabel.setText("")
        self.unit_max_qlabel.setText("")
        self.unit_type_qlabel.setText("")
        self.fish_available_qlistwidget.clear()
        self.export_empty_text_pushbutton.setEnabled(checker)
        self.fromtext_qpushbutton.setEnabled(checker)
        # desired
        self.from_qlineedit.setText("")
        self.to_qlineedit.setText("")
        self.by_qlineedit.setText("")
        self.plot_chronicle_qpushbutton.setEnabled(checker)
        self.export_txt_chronicle_qpushbutton.setEnabled(checker)
        self.require_unit_qtableview.model().clear()

    def names_hab_change(self):
        """
        Ajust item list according to hdf5 filename selected by user
        """
        hdf5name = self.hab_filenames_qcombobox.currentText()
        # no file
        if not hdf5name:
            # clean
            self.disable_and_clean_group_widgets(False)
        # file
        if hdf5name:
            # clean
            self.disable_and_clean_group_widgets(True)

            # create hdf5 class to get hdf5 inforamtions
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file()
            self.hab_reach_qcombobox.clear()
            if len(hdf5.reach_name) == 1:
                reach_names = hdf5.reach_name
            else:
                reach_names = [""] + hdf5.reach_name
            self.hab_reach_qcombobox.addItems(reach_names)

    def reach_hab_change(self):
        #print("reach change")
        hdf5name = self.hab_filenames_qcombobox.currentText()
        reach_name = self.hab_reach_qcombobox.currentText()
        # no file
        if not reach_name:
            # clean
            self.disable_and_clean_group_widgets(False)
        # file
        if reach_name:
            # clean
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            hdf5.open_hdf5_file()
            unit_type = hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hyd unit type")]
            fish_list = hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hab fish list")].split(", ")
            fish_list.sort()
            reach_index = hdf5.reach_name.index(reach_name)
            units_name = hdf5.units_name[reach_index]

            # hab
            if fish_list != [""]:
                self.fish_available_qlistwidget.addItems(fish_list)
                self.fish_available_qlistwidget.selectAll()
            if units_name:
                # set min and max unit for from to by
                unit_num = list(map(float, units_name))
                min_unit = min(unit_num)
                max_unit = max(unit_num)
                self.unit_min_qlabel.setText(str(min_unit))
                self.unit_max_qlabel.setText(str(max_unit))
                self.unit_type_qlabel.setText(unit_type)
                self.from_qlineedit.setText(str(min_unit))
                self.to_qlineedit.setText(str(max_unit))

    def display_required_units_from_sequence(self):
        # is value entry ?
        if self.from_qlineedit.text() == "" or self.to_qlineedit.text() == "" or self.by_qlineedit.text() == "":
            self.send_log.emit('Error: Sequence values must be specified (from, to and by).')
            return

        # is fish ?
        selection = self.fish_available_qlistwidget.selectedItems()
        fish_names = [item.text() for item in selection]
        if fish_names == [""] or fish_names == []:
            self.send_log.emit('Error: There no selected fish.')
            return

        # ok
        else:
            from_sequ = float(self.from_qlineedit.text())  # from
            to_sequ = float(self.to_qlineedit.text())  # to
            by_sequ = float(self.by_qlineedit.text())  # by

            # dict range
            chonicle_from_seq = dict(units=list(self.frange(from_sequ, to_sequ, by_sequ)))

            # types
            text_unit = self.unit_type_qlabel.text()
            types_from_seq = dict(units=text_unit[text_unit.find('[') + 1:text_unit.find(']')])

            # display
            self.create_model_array_and_display(chonicle_from_seq, types_from_seq, source="seq")

    def display_required_units_from_txtfile(self):
        # is fish ?
        selection = self.fish_available_qlistwidget.selectedItems()
        fish_names = [item.text() for item in selection]
        if fish_names == [""] or fish_names == []:
            self.send_log.emit('Error: There no selected fish.')
            return

        # find the filename based on user choice
        filename_path = QFileDialog.getOpenFileName(self,
                                                    self.tr("Select file"),
                                                    self.path_prj,
                                                    "File (*.txt)")[0]

        # exeption: you should be able to clik on "cancel"
        if filename_path:
            chronicle_from_file, types_from_file = tools_mod.read_chronicle_from_text_file(filename_path)

            if not chronicle_from_file:
                self.send_log.emit(types_from_file)
            if chronicle_from_file:
                # display
                self.create_model_array_and_display(chronicle_from_file, types_from_file, source=filename_path)

    def create_model_array_and_display(self, chronicle, types, source):
        # get fish selected
        selection = self.fish_available_qlistwidget.selectedItems()
        fish_names = [item.text() for item in selection]

        # get filename
        hdf5name = self.hab_filenames_qcombobox.currentText()

        # load hdf5 data
        hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
        hdf5.load_hdf5_hab(whole_profil=False, fish_names=fish_names)

        # get reach_name
        reach_index = hdf5.reach_name.index(self.hab_reach_qcombobox.currentText())

        # check matching units for interpolation
        valid, text = tools_mod.check_matching_units(hdf5.data_description, types)

        if not valid:
            self.send_log.emit("Warning : Interpolation not done." + text)

        if valid:
            data_to_table, horiz_headers, vertical_headers = tools_mod.compute_interpolation(hdf5.data_description,
                                                                                         fish_names,
                                                                                         reach_index,
                                                                                         chronicle,
                                                                                         types,
                                                                                         rounddata=True)

            self.mytablemodel = MyTableModel(data_to_table, horiz_headers, vertical_headers, source=source)
            self.require_unit_qtableview.model().clear()
            self.require_unit_qtableview.setModel(self.mytablemodel)  # set model
            # ajust width
            header = self.require_unit_qtableview.horizontalHeader()
            for i in range(len(horiz_headers)):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            self.require_unit_qtableview.verticalHeader().setDefaultSectionSize(
                self.require_unit_qtableview.verticalHeader().minimumSectionSize())
            self.plot_chronicle_qpushbutton.setEnabled(True)
            self.export_txt_chronicle_qpushbutton.setEnabled(True)
            self.send_log.emit("Interpolation done. Interpolated values can now be view in graphic and export in text file.")

    def frange(self, start, stop, step):
        i = start
        while i <= stop:
            yield i
            i += step

    def export_empty_text_file(self):
        hdf5name = self.hab_filenames_qcombobox.currentText()
        if hdf5name:
            # create hdf5 class
            hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
            # get hdf5 inforamtions
            hdf5.get_hdf5_attributes()
            unit_type = hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hyd unit type")]
            fish_list = hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hab fish list")].split(", ")
            units_name = hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hyd unit list")].split(", ")
            unit_num = list(map(float, units_name))
            min_unit = min(unit_num)
            max_unit = max(unit_num)

            # export
            exported = tools_mod.export_empty_text_from_hdf5(unit_type, min_unit, max_unit, hdf5name, self.path_prj)
            if exported:
                self.send_log.emit("Empty text has been exported in 'output/text' project folder. Open and fill it "
                                   "with the desired values and then import it in HABBY.")
            if not exported:
                self.send_log.emit('Error: The file has not been exported as it may be opened by another program.')

    def plot_chronicle(self):
        # get filename
        hdf5name = self.hab_filenames_qcombobox.currentText()

        # fish names and units names from tableview
        fish_names_hv_spu = self.mytablemodel.colnames
        fish_names = []
        for fish in fish_names_hv_spu:
            if "hv_" in fish:
                fish_names.append(fish.replace("hv_", ""))
            if "spu_" in fish:
                fish_names.append(fish.replace("spu_", ""))
        fish_names = list(set(fish_names))

        # seq or txt
        source = self.mytablemodel.source

        # reread from seq (tablemodel)
        if source == "seq":
            chronicle = dict(units=list(map(float, self.mytablemodel.rownames)))
            types = dict(units=self.unit_type_qlabel.text())
        # reread from text file (re-read file)
        else:
            chronicle, types = tools_mod.read_chronicle_from_text_file(source)

        # load figure option
        project_preferences = preferences_GUI.load_project_preferences(self.path_prj,
                                                           self.name_prj)

        # load hdf5 data
        hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
        hdf5.load_hdf5_hab(whole_profil=False, fish_names=fish_names)

        reach_index = hdf5.reach_name.index(self.hab_reach_qcombobox.currentText())

        # recompute
        data_to_table, horiz_headers, vertical_headers = tools_mod.compute_interpolation(hdf5.data_description,
                                                                                         fish_names,
                                                                                         reach_index,
                                                                                         chronicle,
                                                                                         types,
                                                                                         False)
        plot_mod.plot_interpolate_chronicle(data_to_table,
                                            horiz_headers,
                                            vertical_headers,
                                            hdf5.data_description,
                                            fish_names,
                                            types,
                                            project_preferences)

    def export_chronicle(self):
        # get filename
        hdf5name = self.hab_filenames_qcombobox.currentText()

        # fish names and units names from tableview
        fish_names_hv_spu = self.mytablemodel.colnames
        fish_names = []
        for fish in fish_names_hv_spu:
            if "hv_" in fish:
                fish_names.append(fish.replace("hv_", ""))
            if "spu_" in fish:
                fish_names.append(fish.replace("spu_", ""))
        fish_names = list(set(fish_names))

        # seq or txt
        source = self.mytablemodel.source

        # reread from seq (tablemodel)
        if source == "seq":
            chronicle = dict(units=list(map(float, self.mytablemodel.rownames)))
            # types
            text_unit = self.unit_type_qlabel.text()
            types = dict(units=text_unit[text_unit.find('[') + 1:text_unit.find(']')])
        # reread from text file (re-read file)
        else:
            chronicle, types = tools_mod.read_chronicle_from_text_file(source)

        # load figure option
        project_preferences = preferences_GUI.load_project_preferences(self.path_prj,
                                                            self.name_prj)

        # load hdf5 data
        hdf5 = hdf5_mod.Hdf5Management(self.path_prj, hdf5name)
        hdf5.load_hdf5_hab(whole_profil=False, fish_names=fish_names)

        reach_index = hdf5.reach_name.index(self.hab_reach_qcombobox.currentText())

        # recompute interpolation
        data_to_table, horiz_headers, vertical_headers = tools_mod.compute_interpolation(hdf5.data_description,
                                                                                         fish_names,
                                                                                         reach_index,
                                                                                         chronicle,
                                                                                         types,
                                                                                         False)
        # export text
        exported = tools_mod.export_text_interpolatevalues(data_to_table,
                                                           horiz_headers,
                                                           vertical_headers,
                                                           hdf5.data_description,
                                                           types,
                                                           project_preferences)
        if exported:
            self.send_log.emit("Interpolated text file has been exported in 'output/text' project folder.")
        if not exported:
            self.send_log.emit('Error: File not exported as it may be opened by another program.')


class OtherToolToCreate(QGroupBoxCollapsible):
    """
    This class is a subclass of class QGroupBox.
    """

    def __init__(self, path_prj, name_prj, send_log):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.send_log = send_log
        self.init_ui()

    def init_ui(self):
        # group title
        self.setTitle(self.tr("New tools to come"))
        hbox_layout = QHBoxLayout()
        spacer = QSpacerItem(1, 50)
        self.qpushbutton_test = QPushButton("test")
        self.qpushbutton_test.clicked.connect(self.test_function_dev)
        hbox_layout.addItem(spacer)
        hbox_layout.addWidget(self.qpushbutton_test)
        self.setLayout(hbox_layout)

    def test_function_dev(self):
        print("test_function_dev")
        1 / 0
        print("test_function_dev")


class MyTableModel(QStandardItemModel):
    def __init__(self, data_to_table, horiz_headers, vertical_headers, source, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        # save source
        self.source = source
        # model data for table view
        if data_to_table and horiz_headers and vertical_headers:
            for row_index in range(len(vertical_headers)):
                line_string_list = []
                for column_index in range(len(horiz_headers)):
                    line_string_list.append(QStandardItem(data_to_table[row_index][column_index]))
                self.appendRow(line_string_list)
            # save data to export and plot
            self.rownames = vertical_headers
            self.colnames = horiz_headers
            # headers
            horiz_headers = [head.replace("_", "\n") for head in horiz_headers]
            self.setHorizontalHeaderLabels(horiz_headers)
            self.setVerticalHeaderLabels(vertical_headers)

    def get_data_from_column(self, column):
        col_index = self.colnames.index(column)
        data_to_get = []
        for row_nb in range(len(self.rownames)):
            data_to_get.append(self.item(row_nb, col_index).text())
        return data_to_get


