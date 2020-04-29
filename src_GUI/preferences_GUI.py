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
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QSizePolicy, QGroupBox, QDialog, QPushButton, QLabel, QGridLayout, \
    QLineEdit, QComboBox, QMessageBox, QFormLayout, QCheckBox, QHBoxLayout
import numpy as np
import os

from src.tools_mod import DoubleClicOutputGroup, QHLine
from src.project_properties_mod import load_project_properties, create_default_project_properties_dict, \
    save_project_properties
from src.variable_unit_mod import HydraulicVariableUnitManagement


class ProjectPropertiesDialog(QDialog):
    """
    The class which support the creation and management of the output. It is notably used to select the options to
    create the figures.

    """
    send_log = pyqtSignal(str, name='send_log')
    cut_mesh_partialy_dry_signal = pyqtSignal(bool,
                                              name='cut_mesh_partialy_dry_signal')  # to change suffix no_cut
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj, name_icon):

        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.name_icon = name_icon
        self.is_modification = False
        # list with the available color map
        self.namecmap = ['coolwarm', 'jet', 'magma', 'viridis', 'inferno', 'plasma', 'Blues',
                         'Greens', 'Greys', 'Oranges', 'Purples',
                         'Reds', 'gist_earth', 'terrain', 'ocean']
        self.msg2 = QMessageBox()
        self.hvum = HydraulicVariableUnitManagement()
        self.init_iu()

    def init_iu(self):
        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        """ WIDGETS """
        """ general widgets """
        # cut_2d_grid
        self.cut_2d_grid_label = QLabel(self.tr('Cut hydraulic mesh partialy wet'))
        self.cut_2d_grid_checkbox = QCheckBox(self.tr(''))

        # min_height
        min_height_label = QLabel(self.tr('2D minimum water height [m]'))
        self.min_height_lineedit = QLineEdit("")

        # erase_data
        self.erase_data_label = QLabel(self.tr('Erase file if exist'))
        self.erase_data_checkbox = QCheckBox(self.tr(''))

        """ outputs widgets """
        self.mesh_whole_profile_hyd = QCheckBox("")
        self.mesh_whole_profile_hyd.setObjectName("mesh_whole_profile_hyd")

        self.point_whole_profile_hyd = QCheckBox("")
        self.point_whole_profile_hyd.setObjectName("point_whole_profile_hyd")

        self.mesh_units_hyd = QCheckBox("")
        self.mesh_units_hab = QCheckBox("")
        self.mesh_units_hyd.setObjectName("mesh_units_hyd")
        self.mesh_units_hab.setObjectName("mesh_units_hab")

        self.point_units_hyd = QCheckBox("")
        self.point_units_hab = QCheckBox("")
        self.point_units_hyd.setObjectName("point_units_hyd")
        self.point_units_hab.setObjectName("point_units_hab")

        vertical_exaggeration = QLabel("3D vertical exaggeration")
        self.vertical_exaggeration_lineedit = QLineEdit("10")
        self.vertical_exaggeration_lineedit.setToolTip(self.tr("Exaggeration coefficient of z nodes values (all 3D)"))
        self.vertical_exaggeration_lineedit.setAlignment(Qt.AlignCenter)
        self.vertical_exaggeration_lineedit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.vertical_exaggeration_lineedit.setFixedHeight(self.point_units_hyd.sizeHint().height())
        self.vertical_exaggeration_lineedit.setFixedWidth(75)

        self.elevation_whole_profile_hyd = QCheckBox("")
        self.elevation_whole_profile_hyd.setObjectName("elevation_whole_profile_hyd")

        self.pvd_variable_z_combobox = QComboBox()
        self.pvd_variable_z_combobox.setToolTip(self.tr("Choose the variable to assign to the z nodes (3D)"))
        self.variables_units_hyd = QCheckBox("")
        self.variables_units_hab = QCheckBox("")
        self.variables_units_hyd.setObjectName("variables_units_hyd")
        self.variables_units_hab.setObjectName("variables_units_hab")

        self.detailled_text_hyd = QCheckBox("")
        self.detailled_text_hab = QCheckBox("")
        self.detailled_text_hyd.setObjectName("detailled_text_hyd")
        self.detailled_text_hab.setObjectName("detailled_text_hab")

        self.fish_information_hab = QCheckBox("")
        self.fish_information_hab.setObjectName("fish_information_hab")

        self.output_checkbox_list = [self.mesh_whole_profile_hyd,
                                     self.point_whole_profile_hyd,
                                     self.mesh_units_hyd,
                                     self.mesh_units_hab,
                                     self.point_units_hyd,
                                     self.point_units_hab,
                                     self.elevation_whole_profile_hyd,
                                     self.variables_units_hyd,
                                     self.variables_units_hab,
                                     self.detailled_text_hyd,
                                     self.detailled_text_hab,
                                     self.fish_information_hab]

        self.checkbox_list_set = list(set([checkbox.objectName()[:-4] for checkbox in self.output_checkbox_list]))

        """ figure widgets """
        # fig_size
        fig_size_label = QLabel(self.tr('Figure size (w,h) [cm]'), self)
        self.fig_size_lineedit = QLineEdit("")
        self.fig_size_lineedit.setToolTip(self.tr("width, height"))
        fig_size_label.setToolTip(self.tr("width, height"))

        # color_map
        color_map_label = QLabel(self.tr('Color map'), self)
        self.color_map_combobox = QComboBox()
        self.color_map_combobox.addItems(self.namecmap)

        # font_size
        font_size_label = QLabel(self.tr('Font size'), self)
        self.font_size_lineedit = QLineEdit("")

        # font_family
        font_family_label = QLabel(self.tr('Font family'), self)
        self.font_family_combobox = QComboBox()
        self.font_family_combobox.addItems(["Arial", "Calibri", "Times New Roman", "Tahoma", "DejaVu Sans"])

        # line_width
        line_width_label = QLabel(self.tr('Line width'), self)
        self.line_width_lineedit = QLineEdit("")

        # grid
        grid_label = QLabel(self.tr('Grid'), self)
        self.grid_checkbox = QCheckBox("", self)

        # fig_forma
        fig_format_label = QLabel(self.tr('Figure format'))
        self.fig_format_combobox = QComboBox()
        self.fig_format_combobox.addItems(['.png', '.pdf'])

        # resolution
        resolution_label = QLabel(self.tr('Resolution [dpi]'))
        self.resolution_lineedit = QLineEdit("")

        # type_fishname
        type_fishname_label = QLabel(self.tr('Type of fish name'))
        self.type_fishname_combobox = QComboBox()
        self.type_fishname_combobox.addItems([self.tr('Latin Name'), self.tr('French Common Name'), self.tr('English Common Name'),
                                              self.tr('Code ONEMA')])  # order matters here, add stuff at the end!

        # marquers_hab_fig
        marquers_hab_fig_label = QLabel(self.tr('Markers for habitat figures'))
        self.marquers_hab_fig_checkbox = QCheckBox(self.tr(''))

        # reset default
        self.reset_by_default_pref = QPushButton(self.tr('Reset by default'))
        self.reset_by_default_pref.clicked.connect(lambda: self.set_pref_gui_from_dict(default=True))

        # save
        self.save_pref_button = QPushButton(self.tr('OK'))
        self.save_pref_button.clicked.connect(self.save_preferences)

        # close
        self.close_pref_button = QPushButton(self.tr('Cancel'))
        self.close_pref_button.clicked.connect(self.close_preferences)

        """ LAYOUT """
        # general options
        layout_general_options = QFormLayout()
        general_options_group = QGroupBox(self.tr("General"))
        #general_options_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        general_options_group.setLayout(layout_general_options)
        layout_general_options.addRow(self.cut_2d_grid_label, self.cut_2d_grid_checkbox)
        layout_general_options.addRow(min_height_label, self.min_height_lineedit)
        layout_general_options.addRow(self.erase_data_label, self.erase_data_checkbox)  # , Qt.AlignLeft

        # exports options
        self.layout_available_exports = QGridLayout()
        available_exports_group = QGroupBox(self.tr("Default exports"))
        self.doubleclick_check_uncheck_filter = DoubleClicOutputGroup()
        available_exports_group.installEventFilter(self.doubleclick_check_uncheck_filter)
        self.doubleclick_check_uncheck_filter.double_clic_signal.connect(self.check_uncheck_all_checkboxs_at_once)

        #available_exports_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        available_exports_group.setLayout(self.layout_available_exports)

        # row 0
        self.layout_available_exports.addWidget(QLabel(".hyd"), 0, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(QLabel(".hab"), 0, 3, Qt.AlignCenter)
        # row 1
        self.layout_available_exports.addWidget(QLabel("Geopackage (.gpkg)"), 1, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh whole profile")), 1, 1)
        self.layout_available_exports.addWidget(self.mesh_whole_profile_hyd, 1, 2, Qt.AlignCenter)
        # row 2
        self.layout_available_exports.addWidget(QLabel("Geopackage (.gpkg)"), 2, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Point whole profile")), 2, 1)
        self.layout_available_exports.addWidget(self.point_whole_profile_hyd, 2, 2, Qt.AlignCenter)
        # row 3
        self.layout_available_exports.addWidget(QLabel("Geopackage (.gpkg)"), 3, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh units")))
        self.layout_available_exports.addWidget(self.mesh_units_hyd, 3, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.mesh_units_hab, 3, 3, Qt.AlignCenter)
        # row 4
        self.layout_available_exports.addWidget(QLabel("Geopackage (.gpkg)"), 4, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Point units")), 4, 1)
        self.layout_available_exports.addWidget(self.point_units_hyd, 4, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.point_units_hab, 4, 3, Qt.AlignCenter)
        # row 5
        self.layout_available_exports.addWidget(QHLine(), 5, 0, 1, 4)
        # row 6
        self.layout_available_exports.addWidget(QLabel("3D (.stl)"), 6, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh whole profile")), 6, 1)
        self.layout_available_exports.addWidget(self.elevation_whole_profile_hyd, 6, 2, Qt.AlignCenter)
        # row 7
        self.layout_available_exports.addWidget(QLabel("3D (.pvd, .vtu)"), 7, 0)
        self.pvd_variable_z_layout = QHBoxLayout()
        self.pvd_variable_z_layout.addWidget(QLabel(self.tr("Mesh units")))
        self.pvd_variable_z_layout.addWidget(self.pvd_variable_z_combobox)
        self.layout_available_exports.addLayout(self.pvd_variable_z_layout, 7, 1)
#        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh units")), 7, 1)
        self.layout_available_exports.addWidget(self.variables_units_hyd, 7, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.variables_units_hab, 7, 3, Qt.AlignCenter)
        # row 8
        self.layout_available_exports.addWidget(vertical_exaggeration, 8, 0, 1, 2)
        self.layout_available_exports.addWidget(self.vertical_exaggeration_lineedit, 8, 2, 1, 2, Qt.AlignCenter)
        # row 9
        self.layout_available_exports.addWidget(QHLine(), 9, 0, 1, 4)
        # row 10
        self.layout_available_exports.addWidget(QLabel("Text (.txt)"), 10, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Detailled txt file")), 10, 1)
        self.layout_available_exports.addWidget(self.detailled_text_hyd, 10, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.detailled_text_hab, 10, 3, Qt.AlignCenter)
        # row 11
        self.layout_available_exports.addWidget(QLabel("Text (.pdf)"), 11, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Fish informations")), 11, 1)
        self.layout_available_exports.addWidget(self.fish_information_hab, 11, 3, Qt.AlignCenter)

        # figure options
        layout_figures = QFormLayout()
        figures_group = QGroupBox(self.tr("Figures"))
        #figures_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        figures_group.setLayout(layout_figures)
        layout_figures.addRow(fig_size_label, self.fig_size_lineedit)
        layout_figures.addRow(color_map_label, self.color_map_combobox)
        layout_figures.addRow(font_size_label, self.font_size_lineedit)
        layout_figures.addRow(font_family_label, self.font_family_combobox)
        layout_figures.addRow(line_width_label, self.line_width_lineedit)
        layout_figures.addRow(grid_label, self.grid_checkbox)
        layout_figures.addRow(fig_format_label, self.fig_format_combobox)
        layout_figures.addRow(resolution_label, self.resolution_lineedit)
        layout_figures.addRow(type_fishname_label, self.type_fishname_combobox)
        layout_figures.addRow(marquers_hab_fig_label, self.marquers_hab_fig_checkbox)

        # general
        layout = QGridLayout(self)
        layout.addWidget(general_options_group, 0, 0)
        layout.addWidget(available_exports_group, 1, 0)
        layout.addWidget(figures_group, 0, 1, 3, 2)
        layout.addWidget(self.reset_by_default_pref, 3, 0, Qt.AlignLeft)
        layout.addWidget(self.save_pref_button, 3, 1)  # , 1, 1
        layout.addWidget(self.close_pref_button, 3, 2)  # , 1, 1

        self.setWindowTitle(self.tr("Project properties"))
        self.setWindowIcon(QIcon(self.name_icon))

    def connect_modifications_signal(self):
        self.cut_2d_grid_checkbox.stateChanged.connect(self.set_modification_presence)
        self.min_height_lineedit.textChanged.connect(self.set_modification_presence)
        self.erase_data_checkbox.stateChanged.connect(self.set_modification_presence)
        self.pvd_variable_z_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.vertical_exaggeration_lineedit.textChanged.connect(self.set_modification_presence)
        for checkbox in self.output_checkbox_list:
            checkbox.stateChanged.connect(self.set_modification_presence)
        self.fig_size_lineedit.textChanged.connect(self.set_modification_presence)
        self.color_map_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.font_size_lineedit.textChanged.connect(self.set_modification_presence)
        self.line_width_lineedit.textChanged.connect(self.set_modification_presence)
        self.grid_checkbox.stateChanged.connect(self.set_modification_presence)
        self.fig_format_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.resolution_lineedit.textChanged.connect(self.set_modification_presence)
        self.type_fishname_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.marquers_hab_fig_checkbox.stateChanged.connect(self.set_modification_presence)

    def set_pref_gui_from_dict(self, default=False):
        if default:
            project_preferences = create_default_project_properties_dict()
        else:
            # read actual figure option
            project_preferences = load_project_properties(self.path_prj)

        # min_height_hyd
        self.min_height_lineedit.setText(str(project_preferences['min_height_hyd']))

        # CutMeshPartialyDry
        if project_preferences['cut_mesh_partialy_dry']:  # is a string not a boolean
            self.cut_2d_grid_checkbox.setChecked(True)
        else:
            self.cut_2d_grid_checkbox.setChecked(False)

        # erase_id
        if project_preferences['erase_id']:  # is a string not a boolean
            self.erase_data_checkbox.setChecked(True)
        else:
            self.erase_data_checkbox.setChecked(False)

        # pvd_variable_z_combobox
        item_list = [self.hvum.z.name_gui,
                     self.hvum.h.name_gui,
                     self.hvum.v.name_gui,
                     self.hvum.level.name_gui,
                     self.hvum.hydraulic_head.name_gui,
                     self.hvum.conveyance.name_gui,
                     self.hvum.froude.name_gui
                     ]
        self.pvd_variable_z_combobox.clear()
        self.pvd_variable_z_combobox.addItems(item_list)
        self.pvd_variable_z_combobox.setCurrentIndex(item_list.index(project_preferences["pvd_variable_z"]))

        # vertical_exaggeration
        self.vertical_exaggeration_lineedit.setText(str(project_preferences["vertical_exaggeration"]))

        # check uncheck output checkboxs
        for checkbox in self.output_checkbox_list:
            type = checkbox.objectName()[-3:]
            if type == "hyd":
                index = 0
            if type == "hab":
                index = 1
            checkbox.setChecked(project_preferences[checkbox.objectName()[:-4]][index])

        # color_map
        self.color_map_combobox.setCurrentIndex(self.color_map_combobox.findText(project_preferences['color_map']))

        # fig_size
        self.fig_size_lineedit.setText(str(project_preferences['width']) + ',' + str(project_preferences['height']))

        # font size
        self.font_size_lineedit.setText(str(project_preferences['font_size']))

        # font_family
        font_family_list = [self.font_family_combobox.itemText(i) for i in range(self.font_family_combobox.count())]
        self.font_family_combobox.setCurrentIndex(font_family_list.index(project_preferences['font_family']))

        # line_width
        self.line_width_lineedit.setText(str(project_preferences['line_width']))

        # grid
        if project_preferences['grid']:  # is a string not a boolean
            self.grid_checkbox.setChecked(True)
        else:
            self.grid_checkbox.setChecked(False)

        # format
        fig_format_list = [self.fig_format_combobox.itemText(i) for i in range(self.fig_format_combobox.count())]
        self.fig_format_combobox.setCurrentIndex(fig_format_list.index(project_preferences['format']))

        # resolution
        self.resolution_lineedit.setText(str(project_preferences['resolution']))

        # fish_name_type
        self.type_fishname_combobox.setCurrentIndex(int(project_preferences['fish_name_type']))

        # marker
        if project_preferences['marker']:  # is a string not a boolean
            self.marquers_hab_fig_checkbox.setChecked(True)
        else:
            self.marquers_hab_fig_checkbox.setChecked(False)

    def open_preferences(self):
        self.set_pref_gui_from_dict()
        self.connect_modifications_signal()
        self.check_modifications_presence()
        self.setModal(True)
        self.show()

    def check_modifications_presence(self):
        self.is_modification = False

    def set_modification_presence(self):
        self.is_modification = True

    def check_uncheck_all_checkboxs_at_once(self):
        # uncheck all
        if self.mesh_whole_profile_hyd.isChecked():
            [checkbox.setChecked(False) for checkbox in self.output_checkbox_list]
        else:
            [checkbox.setChecked(True) for checkbox in self.output_checkbox_list]

    def collect_project_preferences_choice(self):
        """
        Function to collect user choices of project preferences GUI
        """
        # get default option for security and facility
        project_preferences = load_project_properties(self.path_prj)

        fig_size = self.fig_size_lineedit.text()
        if fig_size:
            fig_size = fig_size.split(',')
            try:
                project_preferences['width'] = np.float(fig_size[0])
                project_preferences['height'] = np.float(fig_size[1])
            except IndexError:
                self.send_log.emit('Error: ' + self.tr('The size of the figure should be in the format: num1,num2.\n'))
            except ValueError:
                self.send_log.emit('Error: ' + self.tr('The size of the figure should be in the format: num1,num2.\n'))
        # color map
        c1 = str(self.color_map_combobox.currentText())
        if c1:
            project_preferences['color_map'] = c1
        # font size
        font_size = self.font_size_lineedit.text()
        if font_size:
            try:
                project_preferences['font_size'] = int(font_size)
            except ValueError:
                self.send_log.emit('Error: ' + self.tr('Font size should be an integer. \n'))
        # font_family
        font_family = self.font_family_combobox.currentText()
        if font_family:
            try:
                project_preferences['font_family'] = font_family
            except ValueError:
                self.send_log.emit('Error: ' + self.tr('Font family not recognized. \n'))
        # line width
        line_width = self.line_width_lineedit.text()
        if line_width:
            try:
                project_preferences['line_width'] = int(line_width)
            except ValueError:
                self.send_log.emit('Error: ' + self.tr('Line width should be an integer. \n'))
        # grid
        if self.grid_checkbox.isChecked():
            project_preferences['grid'] = True
        else:
            project_preferences['grid'] = False
        # format
        project_preferences['format'] = self.fig_format_combobox.currentText()
        # resolution
        try:
            project_preferences['resolution'] = int(self.resolution_lineedit.text())
        except ValueError:
            self.send_log.emit('Error: ' + self.tr('The resolution should be an integer. \n'))
        if project_preferences['resolution'] < 0:
            self.send_log.emit('Error: ' + self.tr('The resolution should be higher than zero \n'))
            return
        if project_preferences['resolution'] > 2000:
            self.send_log.emit(
                'Warning: ' + self.tr('The resolution is higher than 2000 dpi. Figures might be very large.\n'))

        # fish name type
        project_preferences['fish_name_type'] = int(self.type_fishname_combobox.currentIndex())
        # marker
        if self.marquers_hab_fig_checkbox.isChecked():
            project_preferences['marker'] = True
        else:
            project_preferences['marker'] = False

        # outputs
        for checkbox in self.output_checkbox_list:
            type = checkbox.objectName()[-3:]
            if type == "hyd":
                index = 0
            if type == "hab":
                index = 1
            if checkbox.isChecked():
                project_preferences[checkbox.objectName()[:-4]][index] = True
            else:
                project_preferences[checkbox.objectName()[:-4]][index] = False

        # vertical_exaggeration
        try:
            project_preferences['vertical_exaggeration'] = int(self.vertical_exaggeration_lineedit.text())
            if int(self.vertical_exaggeration_lineedit.text()) < 1:
                self.send_log.emit(
                    "Error: " + self.tr("Vertical exaggeration value must be superior than 1. Value set to 1."))
                project_preferences['vertical_exaggeration'] = 1
        except:
            self.send_log.emit("Error: " + self.tr("Vertical exaggeration value is not integer. Value set to 1."))
            project_preferences['vertical_exaggeration'] = 1

        # pvd_variable_z
        project_preferences['pvd_variable_z'] = self.pvd_variable_z_combobox.currentText()

        # other option
        try:
            project_preferences['min_height_hyd'] = float(self.min_height_lineedit.text())
        except ValueError:
            self.send_log.emit('Error: ' + self.tr('Minimum Height should be a number'))
        if self.erase_data_checkbox.isChecked():
            project_preferences['erase_id'] = True
        else:
            project_preferences['erase_id'] = False
        # CutMeshPartialyDry
        if self.cut_2d_grid_checkbox.isChecked():
            project_preferences['cut_mesh_partialy_dry'] = True
        else:
            project_preferences['cut_mesh_partialy_dry'] = False

        return project_preferences

    def save_preferences(self):
        """
        A function which save the options for the figures in the xlm project file. The options for the figures are
        contained in a dictionnary. The idea is to give this dictinnory in argument to all the fonction which create
        figures. In the xml project file, the options for the figures are saved under the attribute "Figure_Option".

        If you change things here, it is necessary to start a new project as the old projects will not be compatible.
        For the new version of HABBY, it will be necessary to insure compatibility by adding xml attribute.
        """
        project_preferences = self.collect_project_preferences_choice()

        # project_preferences['cut_mesh_partialy_dry'] to change suffix no_cut
        self.cut_mesh_partialy_dry_signal.emit(project_preferences['cut_mesh_partialy_dry'])

        # save the data in the xml file
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')

        # save the name and the path in the xml .prj file
        if not os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Project properties unsaved"))
            self.msg2.setText(
                self.tr("Create or open an HABBY project."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        else:
            save_project_properties(self.path_prj, project_preferences)

        self.send_log.emit(self.tr('# Project properties saved.'))
        self.close()

    def close_preferences(self):
        # # really user want to save ?
        # if self.is_modification:
        #     self.msg2.setIcon(QMessageBox.Warning)
        #     self.msg2.setWindowTitle(self.tr("Preferences modified"))
        #     self.msg2.setText(self.tr("Do you really want to close preferences without saving your changes ?"))
        #     self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        #     res = self.msg2.exec_()
        #
        #     # delete
        #     if res == QMessageBox.Yes:
        #         self.send_log.emit('Preferences not saved.')
        #         self.close()
        #         return
        #     if res == QMessageBox.No:
        #         return

        # close window if opened
        self.close()


if __name__ == '__main__':
    pass
