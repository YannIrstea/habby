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
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFrame, QSizePolicy, QSpacerItem, QGroupBox, QDialog, QPushButton, QLabel, QGridLayout, \
    QLineEdit, QComboBox, QMessageBox, QFormLayout, QCheckBox

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import numpy as np
import os


class PreferenceWindow(QDialog):
    """
    The class which support the creation and management of the output. It is notably used to select the options to
    create the figures.

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
        self.is_modification = False
        # list with the available color map
        self.namecmap = ['coolwarm', 'jet', 'magma', 'viridis', 'inferno', 'plasma', 'Blues',
                         'Greens', 'Greys', 'Oranges', 'Purples',
                         'Reds', 'gist_earth', 'terrain', 'ocean', ]
        self.msg2 = QMessageBox()
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
        self.vertical_exaggeration_lineedit.setAlignment(Qt.AlignCenter)
        self.vertical_exaggeration_lineedit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.vertical_exaggeration_lineedit.setFixedHeight(self.point_units_hyd.sizeHint().height())
        self.vertical_exaggeration_lineedit.setFixedWidth(75)

        self.elevation_whole_profile_hyd = QCheckBox("")
        self.elevation_whole_profile_hyd.setObjectName("elevation_whole_profile_hyd")

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
        fig_size_label = QLabel(self.tr('Figure Size [cm]'), self)
        self.fig_size_lineedit = QLineEdit("")

        # color_map
        color_map_label = QLabel(self.tr('Color Map 1'), self)
        self.color_map_combobox = QComboBox()
        self.color_map_combobox.addItems(self.namecmap)

        # color_map2
        color_map2_label = QLabel(self.tr('Color Map 2'), self)
        self.color_map2_combobox = QComboBox()
        self.color_map2_combobox.addItems(self.namecmap)

        # font_size
        font_size_label = QLabel(self.tr('Font Size'), self)
        self.font_size_lineedit = QLineEdit("")

        # line_width
        line_width_label = QLabel(self.tr('Line Width'), self)
        self.line_width_lineedit = QLineEdit("")

        # grid
        grid_label = QLabel(self.tr('Grid'), self)
        self.grid_checkbox = QCheckBox("", self)

        # fig_forma
        fig_format_label = QLabel(self.tr('Figure Format'))
        self.fig_format_combobox = QComboBox()
        self.fig_format_combobox.addItems(['png and pdf', 'png', 'jpg', 'pdf', self.tr('do not save figures')])

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

        # save
        self.save_pref_button = QPushButton(self.tr('Save and close'))
        self.save_pref_button.clicked.connect(self.save_preferences)

        self.close_pref_button = QPushButton(self.tr('Close'))
        self.close_pref_button.clicked.connect(self.close_preferences)

        """ LAYOUT """
        # general options
        layout_general_options = QFormLayout()
        general_options_group = QGroupBox(self.tr("General"))
        general_options_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        general_options_group.setLayout(layout_general_options)
        layout_general_options.addRow(self.cut_2d_grid_label, self.cut_2d_grid_checkbox)
        layout_general_options.addRow(min_height_label, self.min_height_lineedit)
        layout_general_options.addRow(self.erase_data_label, self.erase_data_checkbox)  # , Qt.AlignLeft

        # exports options
        self.layout_available_exports = QGridLayout()
        available_exports_group = QGroupBox(self.tr("Output"))
        self.doubleclick_check_uncheck_filter = DoubleClicOutputGroup()
        available_exports_group.installEventFilter(self.doubleclick_check_uncheck_filter)
        self.doubleclick_check_uncheck_filter.double_clic_signal.connect(self.check_uncheck_all_checkboxs_at_once)

        available_exports_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        available_exports_group.setLayout(self.layout_available_exports)

        # row 0
        self.layout_available_exports.addWidget(QLabel(".hyd"), 0, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(QLabel(".hab"), 0, 3, Qt.AlignCenter)
        # row 1
        self.layout_available_exports.addWidget(QLabel("Shapefile (.shp)"), 1, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh whole profile")), 1, 1)
        self.layout_available_exports.addWidget(self.mesh_whole_profile_hyd, 1, 2, Qt.AlignCenter)
        # row 2
        self.layout_available_exports.addWidget(QLabel("Shapefile (.shp)"), 2, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Point whole profile")), 2, 1)
        self.layout_available_exports.addWidget(self.point_whole_profile_hyd, 2, 2, Qt.AlignCenter)
        # row 3
        self.layout_available_exports.addWidget(QLabel("Shapefile (.shp)"), 3, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh units")), 3, 1)
        self.layout_available_exports.addWidget(self.mesh_units_hyd, 3, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.mesh_units_hab, 3, 3, Qt.AlignCenter)
        # row 4
        self.layout_available_exports.addWidget(QLabel("Shapefile (.shp)"), 4, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Point units")), 4, 1)
        self.layout_available_exports.addWidget(self.point_units_hyd, 4, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.point_units_hab, 4, 3, Qt.AlignCenter)
        # row 5
        self.layout_available_exports.addWidget(QHLine(), 5, 0, 1, 4)
        # row 6
        self.layout_available_exports.addWidget(vertical_exaggeration, 6, 0, 1, 2)
        self.layout_available_exports.addWidget(self.vertical_exaggeration_lineedit, 6, 2, 1, 2, Qt.AlignCenter)
        # row 7
        self.layout_available_exports.addWidget(QLabel("3D (.stl)"), 7, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Mesh whole profile")), 7, 1)
        self.layout_available_exports.addWidget(self.elevation_whole_profile_hyd, 7, 2, Qt.AlignCenter)
        # row 8
        self.layout_available_exports.addWidget(QLabel("3D (.pvd, .vtu)"), 8, 0)
        self.layout_available_exports.addWidget(QLabel(self.tr("Variables units")), 8, 1)
        self.layout_available_exports.addWidget(self.variables_units_hyd, 8, 2, Qt.AlignCenter)
        self.layout_available_exports.addWidget(self.variables_units_hab, 8, 3, Qt.AlignCenter)
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
        figures_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        figures_group.setLayout(layout_figures)
        layout_figures.addRow(fig_size_label, self.fig_size_lineedit)
        layout_figures.addRow(color_map_label, self.color_map_combobox)
        layout_figures.addRow(color_map2_label, self.color_map2_combobox)
        layout_figures.addRow(font_size_label, self.font_size_lineedit)
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
        layout.addWidget(self.save_pref_button, 3, 1)  # , 1, 1
        layout.addWidget(self.close_pref_button, 3, 2)  # , 1, 1

        self.setWindowTitle(self.tr("Preferences"))
        self.setWindowIcon(QIcon(self.name_icon))

    def connect_modifications_signal(self):
        self.cut_2d_grid_checkbox.stateChanged.connect(self.set_modification_presence)
        self.min_height_lineedit.textChanged.connect(self.set_modification_presence)
        self.erase_data_checkbox.stateChanged.connect(self.set_modification_presence)
        self.vertical_exaggeration_lineedit.textChanged.connect(self.set_modification_presence)
        for checkbox in self.output_checkbox_list:
            checkbox.stateChanged.connect(self.set_modification_presence)
        self.fig_size_lineedit.textChanged.connect(self.set_modification_presence)
        self.color_map_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.color_map2_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.font_size_lineedit.textChanged.connect(self.set_modification_presence)
        self.line_width_lineedit.textChanged.connect(self.set_modification_presence)
        self.grid_checkbox.stateChanged.connect(self.set_modification_presence)
        self.fig_format_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.resolution_lineedit.textChanged.connect(self.set_modification_presence)
        self.type_fishname_combobox.currentIndexChanged.connect(self.set_modification_presence)
        self.marquers_hab_fig_checkbox.stateChanged.connect(self.set_modification_presence)

    def set_pref_gui_from_dict(self):
        # read actual figure option
        fig_dict = load_fig_option(self.path_prj, self.name_prj)

        # min_height_hyd
        self.min_height_lineedit.setText(str(fig_dict['min_height_hyd']))

        # CutMeshPartialyDry
        if fig_dict['CutMeshPartialyDry']:  # is a string not a boolean
            self.cut_2d_grid_checkbox.setChecked(True)
        else:
            self.cut_2d_grid_checkbox.setChecked(False)

        # erase_id
        if fig_dict['erase_id']:  # is a string not a boolean
            self.erase_data_checkbox.setChecked(True)
        else:
            self.erase_data_checkbox.setChecked(False)

        # vertical_exaggeration
        self.vertical_exaggeration_lineedit.setText(str(fig_dict["vertical_exaggeration"]))

        # check uncheck output checkboxs
        for checkbox in self.output_checkbox_list:
            type = checkbox.objectName()[-3:]
            if type == "hyd":
                index = 0
            if type == "hab":
                index = 1
            checkbox.setChecked(fig_dict[checkbox.objectName()[:-4]][index])

        # color_map
        self.color_map_combobox.setCurrentIndex(self.color_map_combobox.findText(fig_dict['color_map1']))
        self.color_map2_combobox.setCurrentIndex(self.color_map_combobox.findText(fig_dict['color_map2']))

        # fig_size
        self.fig_size_lineedit.setText(str(fig_dict['width']) + ',' + str(fig_dict['height']))

        # font size
        self.font_size_lineedit.setText(str(fig_dict['font_size']))

        # line_width
        self.line_width_lineedit.setText(str(fig_dict['line_width']))

        # grid
        if fig_dict['grid']:  # is a string not a boolean
            self.grid_checkbox.setChecked(True)
        else:
            self.grid_checkbox.setChecked(False)

        # format
        self.fig_format_combobox.setCurrentIndex(int(fig_dict['format']))

        # resolution
        self.resolution_lineedit.setText(str(fig_dict['resolution']))

        # fish_name_type
        self.type_fishname_combobox.setCurrentIndex(int(fig_dict['fish_name_type']))

        # marker
        if fig_dict['marker']:  # is a string not a boolean
            self.marquers_hab_fig_checkbox.setChecked(True)
        else:
            self.marquers_hab_fig_checkbox.setChecked(False)

    def open_preferences(self):
        self.set_pref_gui_from_dict()
        self.connect_modifications_signal()
        self.check_modifications_presence()
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

    def save_preferences(self):
        """
        A function which save the options for the figures in the xlm project file. The options for the figures are
        contained in a dictionnary. The idea is to give this dictinnory in argument to all the fonction which create
        figures. In the xml project file, the options for the figures are saved under the attribute "Figure_Option".

        If you change things here, it is necessary to start a new project as the old projects will not be compatible.
        For the new version of HABBY, it will be necessary to insure compatibility by adding xml attribute.
        """
        # really user want to save ?
        if self.is_modification:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Preferences modified"))
            self.msg2.setText(self.tr("Do you really want to save and close new preferences ?"))
            self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            res = self.msg2.exec_()

            # delete
            if res == QMessageBox.No:
                return

        # get default option for security
        fig_dict = create_default_figoption()

        # get the data and check validity
        # fig_size
        fig_size = self.fig_size_lineedit.text()
        if fig_size:
            fig_size = fig_size.split(',')
            try:
                fig_dict['width'] = np.float(fig_size[0])
                fig_dict['height'] = np.float(fig_size[1])
            except IndexError:
                self.send_log.emit('Error: The size of the figure should be in the format: num1,num2.\n')
            except ValueError:
                self.send_log.emit('Error: The size of the figure should be in the format: num1,num2.\n')
        # color map
        c1 = str(self.color_map_combobox.currentText())
        if c1:
            fig_dict['color_map1'] = c1
        c2 = str(self.color_map2_combobox.currentText())
        if c2:
            fig_dict['color_map2'] = c2
        # font size
        font_size = self.font_size_lineedit.text()
        if font_size:
            try:
                fig_dict['font_size'] = int(font_size)
            except ValueError:
                self.send_log.emit('Error: Font size should be an integer. \n')
        # line width
        line_width = self.line_width_lineedit.text()
        if line_width:
            try:
                fig_dict['line_width'] = int(line_width)
            except ValueError:
                self.send_log.emit('Error: Line width should be an integer. \n')
        # grid
        if self.grid_checkbox.isChecked():
            fig_dict['grid'] = True
        else:
            fig_dict['grid'] = False
        # format
        fig_dict['format'] = str(self.fig_format_combobox.currentIndex())
        # resolution
        try:
            fig_dict['resolution'] = int(self.resolution_lineedit.text())
        except ValueError:
            self.send_log.emit('Error: the resolution should be an integer. \n')
        if fig_dict['resolution'] < 0:
            self.send_log.emit('Error: The resolution should be higher than zero \n')
            return
        if fig_dict['resolution'] > 2000:
            self.send_log.emit('Warning: The resolution is higher than 2000 dpi. Figures might be very large.\n')

        # fish name type
        fig_dict['fish_name_type'] = int(self.type_fishname_combobox.currentIndex())
        # marker
        if self.marquers_hab_fig_checkbox.isChecked():
            fig_dict['marker'] = True
        else:
            fig_dict['marker'] = False

        # outputs
        for checkbox in self.output_checkbox_list:
            type = checkbox.objectName()[-3:]
            if type == "hyd":
                index = 0
            if type == "hab":
                index = 1
            if checkbox.isChecked():
                fig_dict[checkbox.objectName()[:-4]][index] = True
            else:
                fig_dict[checkbox.objectName()[:-4]][index] = False

        # vertical_exaggeration
        try:
            int(self.vertical_exaggeration_lineedit.text())
            if int(self.vertical_exaggeration_lineedit.text()) < 1:
                self.send_log.emit("Error: Vertical exaggeration value must be superior than 1. Value set to 1.")
                fig_dict['vertical_exaggeration'] = 1
        except:
            self.send_log.emit("Error: Vertical exaggeration value is not integer. Value set to 1.")
            fig_dict['vertical_exaggeration'] = 1

        # other option
        try:
            fig_dict['min_height_hyd'] = float(self.min_height_lineedit.text())
        except ValueError:
            self.send_log.emit('Error: Minimum Height should be a number')
        if self.erase_data_checkbox.isChecked():
            fig_dict['erase_id'] = True
        else:
            fig_dict['erase_id'] = False
        # CutMeshPartialyDry
        if self.cut_2d_grid_checkbox.isChecked():
            fig_dict['CutMeshPartialyDry'] = True
        else:
            fig_dict['CutMeshPartialyDry'] = False

        # save the data in the xml file
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')

        # save the name and the path in the xml .prj file
        if not os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Unsaved preferences"))
            self.msg2.setText(
                self.tr("Create or open an HABBY project."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            child1 = root.find(".//Figure_Option")
            if child1 is not None:  # modify existing option
                width1 = root.find(".//Width")
                height1 = root.find(".//Height")
                colormap1 = root.find(".//ColorMap1")
                colormap2 = root.find(".//ColorMap2")
                fontsize1 = root.find(".//FontSize")
                linewidth1 = root.find(".//LineWidth")
                grid1 = root.find(".//Grid")
                format1 = root.find(".//Format")
                reso1 = root.find(".//Resolution")
                fish1 = root.find(".//FishNameType")
                marker1 = root.find(".//Marker")

                for checkbox_name in self.checkbox_list_set:
                    locals()[checkbox_name] = root.find(".//" + checkbox_name)

                vertical_exaggeration1 = root.find(".//vertical_exaggeration")

                langfig1 = root.find(".//LangFig")
                hopt1 = root.find(".//MinHeight")
                CutMeshPartialyDry = root.find(".//CutMeshPartialyDry")
                erase1 = root.find(".//EraseId")
            else:  # save in case no fig option exist
                child1 = ET.SubElement(root, 'Figure_Option')
                width1 = ET.SubElement(child1, 'Width')
                height1 = ET.SubElement(child1, 'Height')
                colormap1 = ET.SubElement(child1, 'ColorMap1')
                colormap2 = ET.SubElement(child1, 'ColorMap2')
                fontsize1 = ET.SubElement(child1, 'FontSize')
                linewidth1 = ET.SubElement(child1, 'LineWidth')
                grid1 = ET.SubElement(child1, 'Grid')
                format1 = ET.SubElement(child1, "Format")
                reso1 = ET.SubElement(child1, "Resolution")
                fish1 = ET.SubElement(child1, "FishNameType")
                marker1 = ET.SubElement(child1, "Marker")

                for checkbox_name in self.checkbox_list_set:
                    locals()[checkbox_name] = ET.SubElement(child1, checkbox_name)
                vertical_exaggeration1 = ET.SubElement(child1, "vertical_exaggeration")
                langfig1 = ET.SubElement(child1, "LangFig")
                hopt1 = ET.SubElement(child1, "MinHeight")
                CutMeshPartialyDry = ET.SubElement(child1, "CutMeshPartialyDry")
                erase1 = ET.SubElement(child1, "EraseId")
            width1.text = str(fig_dict['width'])
            height1.text = str(fig_dict['height'])
            colormap1.text = fig_dict['color_map1']
            colormap2.text = fig_dict['color_map2']
            fontsize1.text = str(fig_dict['font_size'])
            linewidth1.text = str(fig_dict['line_width'])
            grid1.text = str(fig_dict['grid'])
            format1.text = str(fig_dict['format'])
            reso1.text = str(fig_dict['resolution'])
            # usually not useful, but should be added to new options for comptability with older project
            if fish1 is None:
                fish1 = ET.SubElement(child1, "FishNameType")
            fish1.text = str(fig_dict['fish_name_type'])
            marker1.text = str(fig_dict['marker'])
            if langfig1 is None:
                langfig1 = ET.SubElement(child1, "LangFig")
            langfig1.text = str(fig_dict['language'])

            for checkbox_name in self.checkbox_list_set:
                locals()[checkbox_name].text = str(fig_dict[checkbox_name])
            if vertical_exaggeration1 is None:
                vertical_exaggeration1 = ET.SubElement(child1, "vertical_exaggeration")
            vertical_exaggeration1.text = str(fig_dict["vertical_exaggeration"])
            # text1.text = str(fig_dict['text_output'])
            # shape1.text = str(fig_dict['shape_output'])
            # para1.text = str(fig_dict['paraview'])
            # stl1.text = str(fig_dict['stl'])
            # fishinfo1.text = str(fig_dict['fish_info'])

            hopt1.text = str(fig_dict['min_height_hyd'])
            CutMeshPartialyDry.text = str(fig_dict['CutMeshPartialyDry'])
            erase1.text = str(fig_dict['erase_id'])
            doc.write(fname)

        self.send_log.emit('# Preferences saved.')
        self.close()

    def close_preferences(self):
        # really user want to save ?
        if self.is_modification:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Preferences modified"))
            self.msg2.setText(self.tr("Do you really want to close preferences without saving your changes ?"))
            self.msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            res = self.msg2.exec_()

            # delete
            if res == QMessageBox.Yes:
                self.send_log.emit('Preferences not saved.')
                self.close()
                return
            if res == QMessageBox.No:
                return

        # close window if opened
        self.close()


def set_lang_fig(nb_lang, path_prj, name_prj):
    """
    This function write in the xml file in which langugage the figures should be done. This is kept in the
    group of attribute in the Figure_Option
    :param lang: An int indicating the langugage (0 for english, 1 for french,...)
    :param path_prj: the path to the project
    :param name_prj: the name of the project
    """

    # save the data in the xml file
    # open the xml project file
    fname = os.path.join(path_prj, name_prj + '.xml')
    # save the name and the path in the xml .prj file
    if not os.path.isfile(fname):
        # print('Error: project is not found \n')
        return
    else:
        doc = ET.parse(fname)
        root = doc.getroot()
        child1 = root.find(".//Figure_Option")
        if child1 is not None:  # modify existing option
            langfig1 = root.find(".//LangFig")
            if langfig1 is None:
                langfig1 = ET.SubElement(child1, "LangFig")
            langfig1.text = str(nb_lang)
            doc.write(fname)


def load_fig_option(path_prj, name_prj):
    """
    This function loads the figure option saved in the xml file and create a dictionnary will be given to the functions
    which create the figures to know the different options chosen by the user. If the options are not written, this
    function uses data by default which are in the fonction create_default_fig_options().

    :param path_prj: the path to the xml project file
    :param name_prj: the name to this file
    :return: the dictionary containing the figure options

    """

    fig_dict = create_default_figoption()
    fname = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(fname) and name_prj != '':  # no project exists
        pass
    elif name_prj == '':
        pass
    elif not os.path.isfile(fname):  # the project is not found
        print('Warning: No project file (.xml) found.\n')
    else:
        doc = ET.parse(fname)
        root = doc.getroot()
        child1 = root.find(".//Figure_Option")
        if child1 is not None:  # modify existing option
            width1 = root.find(".//Width")
            height1 = root.find(".//Height")
            colormap1 = root.find(".//ColorMap1")
            colormap2 = root.find(".//ColorMap2")
            fontsize1 = root.find(".//FontSize")
            linewidth1 = root.find(".//LineWidth")
            grid1 = root.find(".//Grid")
            format1 = root.find(".//Format")
            marker1 = root.find(".//Marker")
            reso1 = root.find(".//Resolution")
            fish1 = root.find(".//FishNameType")
            mesh_whole_profile = root.find(".//mesh_whole_profile")
            point_whole_profile = root.find(".//point_whole_profile")
            mesh_units = root.find(".//mesh_units")
            point_units = root.find(".//point_units")
            vertical_exaggeration = root.find(".//vertical_exaggeration")
            elevation_whole_profile = root.find(".//elevation_whole_profile")
            variables_units = root.find(".//variables_units")
            detailled_text = root.find(".//detailled_text")
            fish_information = root.find(".//fish_information")
            langfig1 = root.find(".//LangFig")
            hopt1 = root.find(".//MinHeight")
            CutMeshPartialyDry = root.find(".//CutMeshPartialyDry")
            erase1 = root.find(".//EraseId")
            try:
                if width1 is not None:
                    fig_dict['width'] = float(width1.text)
                if height1 is not None:
                    fig_dict['height'] = float(height1.text)
                if colormap1 is not None:
                    fig_dict['color_map1'] = colormap1.text
                if colormap2 is not None:
                    fig_dict['color_map2'] = colormap2.text
                if fontsize1 is not None:
                    fig_dict['font_size'] = int(fontsize1.text)
                if linewidth1 is not None:
                    fig_dict['line_width'] = int(linewidth1.text)
                if grid1 is not None:
                    fig_dict['grid'] = grid1.text
                if format1 is not None:
                    fig_dict['format'] = format1.text
                if marker1 is not None:
                    fig_dict['marker'] = marker1.text
                if reso1 is not None:
                    fig_dict['resolution'] = int(reso1.text)
                if fish1 is not None:
                    fig_dict['fish_name_type'] = fish1.text
                if mesh_whole_profile is not None:
                    fig_dict['mesh_whole_profile'] = eval(mesh_whole_profile.text)
                if point_whole_profile is not None:
                    fig_dict['point_whole_profile'] = eval(point_whole_profile.text)
                if mesh_units is not None:
                    fig_dict['mesh_units'] = eval(mesh_units.text)
                if point_units is not None:
                    fig_dict['point_units'] = eval(point_units.text)
                if vertical_exaggeration is not None:
                    fig_dict['vertical_exaggeration'] = int(vertical_exaggeration.text)
                if elevation_whole_profile is not None:
                    fig_dict['elevation_whole_profile'] = eval(elevation_whole_profile.text)
                if variables_units is not None:
                    fig_dict['variables_units'] = eval(variables_units.text)
                if detailled_text is not None:
                    fig_dict['detailled_text'] = eval(detailled_text.text)
                if fish_information is not None:
                    fig_dict['fish_information'] = eval(fish_information.text)
                if langfig1 is not None:
                    fig_dict['language'] = int(langfig1.text)
                if hopt1 is not None:
                    fig_dict['min_height_hyd'] = float(hopt1.text)
                if CutMeshPartialyDry is not None:
                    fig_dict['CutMeshPartialyDry'] = CutMeshPartialyDry.text
                if erase1 is not None:
                    fig_dict['erase_id'] = erase1.text
            except ValueError:
                print('Error: Figure Options are not of the right type.\n')

    return fig_dict


def create_default_figoption():
    """
    This function creates the default dictionnary of option for the figure.
    """
    fig_dict = {}
    fig_dict['height'] = 7
    fig_dict['width'] = 10
    fig_dict['color_map1'] = 'coolwarm'
    fig_dict['color_map2'] = 'jet'
    fig_dict['font_size'] = 12
    fig_dict['line_width'] = 1
    fig_dict['grid'] = False
    fig_dict['format'] = 3
    fig_dict['resolution'] = 800
    fig_dict['fish_name_type'] = 0

    fig_dict['mesh_whole_profile'] = [False, False]
    fig_dict['point_whole_profile'] = [False, False]
    fig_dict['mesh_units'] = [False, False]
    fig_dict['point_units'] = [False, False]
    fig_dict['vertical_exaggeration'] = 10
    fig_dict['elevation_whole_profile'] = [True, True]
    fig_dict['variables_units'] = [True, True]
    fig_dict['detailled_text'] = [True, True]
    fig_dict['fish_information'] = [True, True]

    # this is dependant on the language of the application not the user choice in the output tab
    fig_dict['language'] = 0  # 0 english, 1 french
    fig_dict['min_height_hyd'] = 0.001  # water height under 1mm is not accounted for
    fig_dict['CutMeshPartialyDry'] = True
    fig_dict['marker'] = True  # Add point to line plot
    fig_dict['erase_id'] = True
    fig_dict['type_plot'] = 'display'

    return fig_dict


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class DoubleClicOutputGroup(QObject):
    double_clic_signal = pyqtSignal()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick:
            self.double_clic_signal.emit()
            return True  # eat double click
        else:
            # standard event processing
            return QObject.eventFilter(self, obj, event)


if __name__ == '__main__':
    pass
