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
from PyQt5.QtWidgets import QGroupBox, QPushButton, QLabel, QGridLayout, \
    QLineEdit, QComboBox, QMessageBox, QFormLayout, \
    QCheckBox, QScrollArea, QFrame

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import numpy as np
import os


class PreferenceWindow(QScrollArea):
    """
    The class which support the creation and management of the output. It is notably used to select the options to
    create the figures.

    """
    send_log = pyqtSignal(str, name='send_log')
    """
    A PyQtsignal used to write the log.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
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
        
        # read actual figure option
        fig_dict = load_fig_option(self.path_prj, self.name_prj)

        """ WIDGETS """
        # cut_2d_grid
        self.cut_2d_grid_label = QLabel(self.tr('Cut hydraulic mesh partialy wet'))
        self.cut_2d_grid_checkbox = QCheckBox(self.tr(''))
        if fig_dict['Cut2Dgrid'] == 'True':  # is a string not a boolean
            self.cut_2d_grid_checkbox.setChecked(True)
        else:
            self.cut_2d_grid_checkbox.setChecked(False)
            
        # min_height
        min_height_label = QLabel(self.tr('2D minimum water height [m]'))
        self.min_height_lineedit = QLineEdit(str(fig_dict['min_height_hyd']))

        # erase_data
        self.erase_data_label = QLabel(self.tr('Erase file if exist'))
        self.erase_data_checkbox = QCheckBox(self.tr(''))
        if fig_dict['erase_id'] == 'True':  # is a string not a boolean
            self.erase_data_checkbox.setChecked(True)
        else:
            self.erase_data_checkbox.setChecked(False)

        # detailed_text_out
        detailed_text_out_label = QLabel(self.tr('Detailed text (.txt)'))
        self.detailed_text_out_checkbox = QCheckBox(self.tr(''))
        if fig_dict['text_output'] == 'True':  # is a string not a boolean
            self.detailed_text_out_checkbox.setChecked(True)
        else:
            self.detailed_text_out_checkbox.setChecked(False)
        
        # shape_out
        shape_out_label = QLabel(self.tr('Shapefile (.shp)'))
        self.shape_out_checkbox = QCheckBox(self.tr(''))
        if fig_dict['shape_output'] == 'True':  # is a string not a boolean
            self.shape_out_checkbox.setChecked(True)
        else:
            self.shape_out_checkbox.setChecked(False)

        # 3d_stl
        stl_out_label = QLabel(self.tr('3D stereolithography (.stl)'))
        self.stl_out_checkbox = QCheckBox(self.tr(''))
        if fig_dict['stl'] == 'True':  # is a string not a boolean
            self.stl_out_checkbox.setChecked(True)
        else:
            self.stl_out_checkbox.setChecked(False)

        # paraview_out
        paraview_out_label = QLabel(self.tr('3D Paraview (.pvd, .vtu)'))
        self.paraview_out_checkbox = QCheckBox(self.tr(''))
        if fig_dict['paraview'] == 'True':  # is a string not a boolean
            self.paraview_out_checkbox.setChecked(True)
        else:
            self.paraview_out_checkbox.setChecked(False)
        
        # fish_info
        fish_info_label = QLabel(self.tr('Fish Information (.pdf)'))
        self.fish_info_checkbox = QCheckBox(self.tr(''))
        if fig_dict['fish_info'] == 'True':  # is a string not a boolean
            self.fish_info_checkbox.setChecked(True)
        else:
            self.fish_info_checkbox.setChecked(False)
        
        # fig_size
        fig_size_label = QLabel(self.tr('Figure Size [cm]'), self)
        self.fig_size_lineedit = QLineEdit(str(fig_dict['width']) + ',' + str(fig_dict['height']))

        # color_map
        color_map_label = QLabel(self.tr('Color Map 1'), self)
        self.color_map_combobox = QComboBox()
        self.color_map_combobox.addItems(self.namecmap)
        namecmap1 = fig_dict['color_map1']
        index = self.color_map_combobox.findText(namecmap1)
        self.color_map_combobox.setCurrentIndex(index)
        
        # color_map2
        color_map2_label = QLabel(self.tr('Color Map 2'), self)
        self.color_map2_combobox = QComboBox()
        self.color_map2_combobox.addItems(self.namecmap)
        namecmap1 = fig_dict['color_map2']
        index = self.color_map_combobox.findText(namecmap1)
        self.color_map2_combobox.setCurrentIndex(index)
        
        # font_size
        font_size_label = QLabel(self.tr('Font Size'), self)
        self.font_size_lineedit = QLineEdit(str(fig_dict['font_size']))

        # line_width
        line_width_label = QLabel(self.tr('Line Width'), self)
        self.line_width_lineedit = QLineEdit(str(fig_dict['line_width']))

        # grid
        grid_label = QLabel(self.tr('Grid'), self)
        self.grid_checkbox = QCheckBox("", self)
        if fig_dict['grid'] == 'True':  # is a string not a boolean
            self.grid_checkbox.setChecked(True)
        else:
            self.grid_checkbox.setChecked(False)

        # fig_forma
        fig_format_label = QLabel(self.tr('Figure Format'))
        self.fig_format_combobox = QComboBox()
        self.fig_format_combobox.addItems(['png and pdf', 'png', 'jpg', 'pdf', self.tr('do not save figures')])
        self.fig_format_combobox.setCurrentIndex(int(fig_dict['format']))
        
        # resolution
        resolution_label = QLabel(self.tr('Resolution [dpi]'))
        self.resolution_lineedit = QLineEdit(str(fig_dict['resolution']))
        
        # type_fishname
        type_fishname_label = QLabel(self.tr('Type of fish name'))
        self.type_fishname_combobox = QComboBox()
        self.type_fishname_combobox.addItems([self.tr('Latin Name'), self.tr('French Common Name'), self.tr('English Common Name'),
                                              self.tr('Code ONEMA')])  # order matters here, add stuff at the end!
        self.type_fishname_combobox.setCurrentIndex(int(fig_dict['fish_name_type']))
        
        # marquers_hab_fig
        marquers_hab_fig_label = QLabel(self.tr('Markers for habitat figures'))
        self.marquers_hab_fig_checkbox = QCheckBox(self.tr(''))
        if fig_dict['marker'] == 'True':  # is a string not a boolean
            self.marquers_hab_fig_checkbox.setChecked(True)
        else:
            self.marquers_hab_fig_checkbox.setChecked(False)
       
        # save
        self.save_pref_button = QPushButton(self.tr('Save and close'))
        self.save_pref_button.clicked.connect(self.save_preferences)

        self.close_pref_button = QPushButton(self.tr('Close'))
        self.close_pref_button.clicked.connect(self.close_preferences)

        """ LAYOUT """
        # general
        layout_general_options = QFormLayout()
        general_options_group = QGroupBox(self.tr("General"))
        general_options_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        general_options_group.setLayout(layout_general_options)
        layout_general_options.addRow(self.cut_2d_grid_label, self.cut_2d_grid_checkbox)
        layout_general_options.addRow(min_height_label, self.min_height_lineedit)

        # exports
        layout_available_exports = QFormLayout()
        available_exports_group = QGroupBox(self.tr("Output"))
        available_exports_group.setStyleSheet('QGroupBox {font-weight: bold;}')
        available_exports_group.setLayout(layout_available_exports)
        layout_available_exports.addRow(self.erase_data_label, self.erase_data_checkbox)  # , Qt.AlignLeft
        layout_available_exports.addRow(detailed_text_out_label, self.detailed_text_out_checkbox)
        layout_available_exports.addRow(shape_out_label, self.shape_out_checkbox)
        layout_available_exports.addRow(stl_out_label, self.stl_out_checkbox)
        layout_available_exports.addRow(paraview_out_label, self.paraview_out_checkbox)
        layout_available_exports.addRow(fish_info_label, self.fish_info_checkbox)

        # figure
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
        content_widget = QFrame()  # empty frame scrolable
        layout = QGridLayout(content_widget)
        layout.addWidget(general_options_group, 0, 0)
        layout.addWidget(available_exports_group, 1, 0)
        layout.addWidget(figures_group, 0, 1, 3, 2)
        layout.addWidget(self.save_pref_button, 3, 1)  # , 1, 1
        layout.addWidget(self.close_pref_button, 3, 2)  # , 1, 1
        layout.setAlignment(Qt.AlignTop)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

    def save_preferences(self):
        """
        A function which save the options for the figures in the xlm project file. The options for the figures are
        contained in a dictionnary. The idea is to give this dictinnory in argument to all the fonction which create
        figures. In the xml project file, the options for the figures are saved under the attribute "Figure_Option".

        If you change things here, it is necessary to start a new project as the old projects will not be compatible.
        For the new version of HABBY, it will be necessary to insure compatibility by adding xml attribute.
        """
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
            self.send_log.emit('Error: Grid cannot be on and off at the same time. \n')
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
        if self.detailed_text_out_checkbox.isChecked():
            self.send_log.emit('Error: Text Output cannot be on and off at the same time. \n')
        if self.detailed_text_out_checkbox.isChecked():
            fig_dict['text_output'] = True
        else:
            fig_dict['text_output'] = False
        if self.shape_out_checkbox.isChecked():
            self.send_log.emit('Error: Shapefile output cannot be on and off at the same time. \n')
        if self.shape_out_checkbox.isChecked():
            fig_dict['shape_output'] = True
        else:
            fig_dict['shape_output'] = False

        if self.paraview_out_checkbox.isChecked():
            self.send_log.emit('Error: Paraview cannot be on and off at the same time. \n')
        if self.paraview_out_checkbox.isChecked():
            fig_dict['paraview'] = True
        else:
            fig_dict['paraview'] = False

        if self.stl_out_checkbox.isChecked():
            self.send_log.emit('Error: Paraview cannot be on and off at the same time. \n')
        if self.stl_out_checkbox.isChecked():
            fig_dict['stl'] = True
        else:
            fig_dict['stl'] = False

        if self.fish_info_checkbox.isChecked():
            fig_dict['fish_info'] = True
        else:
            fig_dict['fish_info'] = False
        # other option
        try:
            fig_dict['min_height_hyd'] = float(self.min_height_lineedit.text())
        except ValueError:
            self.send_log.emit('Error: Minimum Height should be a number')
        if self.erase_data_checkbox.isChecked():
            fig_dict['erase_id'] = True
        else:
            fig_dict['erase_id'] = False
        # Cut2Dgrid
        if self.cut_2d_grid_checkbox.isChecked():
            self.send_log.emit('Error: Paraview cannot be on and off at the same time. \n')
        if self.cut_2d_grid_checkbox.isChecked():
            fig_dict['Cut2Dgrid'] = True
        else:
            fig_dict['Cut2Dgrid'] = False

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
                text1 = root.find(".//TextOutput")
                shape1 = root.find(".//ShapeOutput")
                para1 = root.find(".//ParaviewOutput")
                stl1 = root.find(".//stlOutput")
                langfig1 = root.find(".//LangFig")
                hopt1 = root.find(".//MinHeight")
                Cut2Dgrid = root.find(".//Cut2Dgrid")
                fishinfo1 = root.find(".//FishInfo")
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
                text1 = ET.SubElement(child1, "TextOutput")
                shape1 = ET.SubElement(child1, "ShapeOutput")
                para1 = ET.SubElement(child1, "ParaviewOutput")
                stl1 = ET.SubElement(child1, "stlOutput")
                langfig1 = ET.SubElement(child1, "LangFig")
                hopt1 = ET.SubElement(child1, "MinHeight")
                Cut2Dgrid = ET.SubElement(child1, "Cut2Dgrid")
                fishinfo1 = ET.SubElement(child1, "FishInfo")
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
            text1.text = str(fig_dict['text_output'])
            shape1.text = str(fig_dict['shape_output'])
            para1.text = str(fig_dict['paraview'])
            stl1.text = str(fig_dict['stl'])
            hopt1.text = str(fig_dict['min_height_hyd'])
            Cut2Dgrid.text = str(fig_dict['Cut2Dgrid'])
            fishinfo1.text = str(fig_dict['fish_info'])
            erase1.text = str(fig_dict['erase_id'])
            doc.write(fname)

        self.send_log.emit('# The new options for the figures are saved.')
        self.send_log.emit('# Modifications of figure options.')
        if self.parent():
            self.close_preferences()

    def close_preferences(self):
        # close window if opened
        try:
            self.parent().close()
        except:
            print("bug")


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
            text1 = root.find(".//TextOutput")
            shape1 = root.find(".//ShapeOutput")
            para1 = root.find(".//ParaviewOutput")
            stl1 = root.find(".//stlOutput")
            langfig1 = root.find(".//LangFig")
            hopt1 = root.find(".//MinHeight")
            Cut2Dgrid = root.find(".//Cut2Dgrid")
            fishinfo1 = root.find(".//FishInfo")
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
                if text1 is not None:
                    fig_dict['text_output'] = text1.text
                if shape1 is not None:
                    fig_dict['shape_output'] = shape1.text
                if para1 is not None:
                    fig_dict['paraview'] = para1.text
                if stl1 is not None:
                    fig_dict['stl'] = stl1.text
                if langfig1 is not None:
                    fig_dict['language'] = int(langfig1.text)
                if hopt1 is not None:
                    fig_dict['min_height_hyd'] = float(hopt1.text)
                if Cut2Dgrid is not None:
                    fig_dict['Cut2Dgrid'] = Cut2Dgrid.text
                if fish1 is not None:
                    fig_dict['fish_info'] = fishinfo1.text
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
    fig_dict['grid'] = 'False'
    fig_dict['format'] = 3
    fig_dict['resolution'] = 800
    fig_dict['fish_name_type'] = 0
    fig_dict['text_output'] = 'True'
    fig_dict['shape_output'] = 'True'
    fig_dict['paraview'] = 'True'
    fig_dict['stl'] = 'True'
    fig_dict['fish_info'] = 'True'
    # this is dependant on the language of the application not the user choice in the output tab
    fig_dict['language'] = 0  # 0 english, 1 french
    fig_dict['min_height_hyd'] = 0.001  # water height under 1mm is not accounted for
    fig_dict['Cut2Dgrid'] = 'True'
    fig_dict['marker'] = 'True'  # Add point to line plot
    fig_dict['erase_id'] = 'True'
    fig_dict['type_plot'] = 'display'

    return fig_dict


if __name__ == '__main__':
    pass
