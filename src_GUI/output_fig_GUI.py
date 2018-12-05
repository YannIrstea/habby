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
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, \
    QLineEdit, QSpacerItem, QComboBox, QMessageBox,\
    QCheckBox, QScrollArea, QFrame
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import numpy as np
import os


class outputW(QScrollArea):
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
        self.namecmap = ['coolwarm','jet','magma','viridis', 'inferno', 'plasma', 'Blues',
                         'Greens', 'Greys', 'Oranges', 'Purples',
                         'Reds', 'gist_earth', 'terrain', 'ocean', ]
        self.msg2 = QMessageBox()
        self.init_iu()

    def init_iu(self):

        # read actual figure option
        fig_dict = load_fig_option(self.path_prj, self.name_prj)

        # on half of the widget, give options to create the figure
        # figrst write the QLabel
        self.fig0l = QLabel(self.tr('<b> Figures Options </b> '), self)
        self.fig1l = QLabel(self.tr('Figure Size [cm]'), self)
        self.fig2l = QLabel(self.tr('Color Map 1'), self)
        self.fig3l = QLabel(self.tr('Color Map 2'), self)
        self.fig5l = QLabel(self.tr('Font Size'), self)
        self.fig6l = QLabel(self.tr('Line Width'), self)
        self.fig7l = QLabel(self.tr('Grid'), self)
        self.fig8l = QLabel(self.tr('Time step [for all time steps: -99]'))
        self.fig9l = QLabel(self.tr('Plot raw loaded data'))
        self.fig10l = QLabel(self.tr('Figure Format'))
        self.fig11l = QLabel(self.tr('Resolution [dpi]'))
        self.fig12l = QLabel(self.tr('Type of fish name'))

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # then fill the size
        self.fig1 = QLineEdit(str(fig_dict['width']) + ',' + str(fig_dict['height']))

        # fill the colormap options
        self.fig2 = QComboBox()
        self.fig2.addItems(self.namecmap)
        namecmap1 = fig_dict['color_map1']
        index = self.fig2.findText(namecmap1)
        self.fig2.setCurrentIndex(index)
        self.fig3 = QComboBox()
        self.fig3.addItems(self.namecmap)
        namecmap1 = fig_dict['color_map2']
        index = self.fig2.findText(namecmap1)
        self.fig3.setCurrentIndex(index)

        # fill other options
        self.fig5 = QLineEdit(str(fig_dict['font_size']))
        self.fig6 = QLineEdit(str(fig_dict['line_width']))
        self.fig7a = QCheckBox(self.tr('On'), self)
        self.fig7a.clicked.connect(lambda: self.check_uncheck(self.fig7a, self.fig7b))
        self.fig7b = QCheckBox(self.tr('Off'), self)
        self.fig7b.clicked.connect(lambda: self.check_uncheck(self.fig7b, self.fig7a))
        if fig_dict['grid'] == 'True':   # is a string not a boolean
            self.fig7a.setChecked(True)
            self.fig7b.setChecked(False)
        else:
            self.fig7a.setChecked(False)
            self.fig7b.setChecked(True)

        # fill the option for the time steps
        self.fig8 = QLineEdit('0,1')
        self.fig8.setText(str(fig_dict['time_step'])[1:-1])  # [1:-1] because of []

        # choose if we should plot the data from the 1D model (before the grid is created)
        self.fig9a = QCheckBox(self.tr('Yes'), self)
        self.fig9a.clicked.connect(lambda: self.check_uncheck(self.fig9a, self.fig9b))
        self.fig9b = QCheckBox(self.tr('No'), self)
        self.fig9b.clicked.connect(lambda: self.check_uncheck(self.fig9b, self.fig9a))
        if fig_dict['raw_data'] == 'True':   # is a string not a boolean
            self.fig9a.setChecked(True)
            self.fig9b.setChecked(False)
        else:
            self.fig9a.setChecked(False)
            self.fig9b.setChecked(True)
        self.fig10 = QComboBox()
        # DO NOT change order here 0,1,2,3 aew used afterward
        self.fig10.addItems(['png and pdf', 'png', 'jpg', 'pdf', self.tr('do not save figures')])
        self.fig10.setCurrentIndex(int(fig_dict['format']))

        # choose the resolution of the figures
        self.fig11 = QLineEdit(str(fig_dict['resolution']))

        # how to write the fish name in the calcul of habitat
        self.fig12 = QComboBox()
        self.fig12.addItems([self.tr('Latin Name'), self.tr('French Common Name'), self.tr('English Common Name'),
                             self.tr('Code ONEMA')])  # order matters here, add stuff at the end!
        self.fig12.setCurrentIndex(int(fig_dict['fish_name_type']))

        # marker for habitat and preference file
        self.out9 = QLabel(self.tr('Markers for habitat figures'))
        self.out9a = QCheckBox(self.tr('Yes'))
        self.out9a.clicked.connect(lambda: self.check_uncheck(self.out9a, self.out9b))
        self.out9b = QCheckBox(self.tr('No'))
        self.out9b.clicked.connect(lambda: self.check_uncheck(self.out9b, self.out9a))
        if fig_dict['marker'] == 'True':  # is a string not a boolean
            self.out9a.setChecked(True)
            self.out9b.setChecked(False)
        else:
            self.out9a.setChecked(False)
            self.out9b.setChecked(True)

        # output options on the lower half,
        self.out0 = QLabel(self.tr(' <b> Output Options </b>'))
        self.out1 = QLabel(self.tr('Detailed text file'))
        self.out1a = QCheckBox(self.tr('Yes'))
        self.out1a.clicked.connect(lambda: self.check_uncheck(self.out1a, self.out1b))
        self.out1b = QCheckBox(self.tr('No'))
        self.out1b.clicked.connect(lambda: self.check_uncheck(self.out1b, self.out1a))
        if fig_dict['text_output'] == 'True':   # is a string not a boolean
            self.out1a.setChecked(True)
            self.out1b.setChecked(False)
        else:
            self.out1a.setChecked(False)
            self.out1b.setChecked(True)
        self.out2 = QLabel(self.tr('Shapefile'))
        self.out2a = QCheckBox(self.tr('Yes'))
        self.out2a.clicked.connect(lambda: self.check_uncheck(self.out2a, self.out2b))
        self.out2b = QCheckBox(self.tr('No'))
        self.out2b.clicked.connect(lambda: self.check_uncheck(self.out2b, self.out2a))
        if fig_dict['shape_output'] == 'True':   # is a string not a boolean
            self.out2a.setChecked(True)
            self.out2b.setChecked(False)
        else:
            self.out2a.setChecked(False)
            self.out2b.setChecked(True)
        self.out3 = QLabel(self.tr('Paraview input'))
        self.out3a = QCheckBox(self.tr('Yes'))
        self.out3a.clicked.connect(lambda: self.check_uncheck(self.out3a, self.out3b))
        self.out3b = QCheckBox(self.tr('No'))
        self.out3b.clicked.connect(lambda: self.check_uncheck(self.out3b, self.out3a))
        if fig_dict['paraview'] == 'True':   # is a string not a boolean
            self.out3a.setChecked(True)
            self.out3b.setChecked(False)
        else:
            self.out3a.setChecked(False)
            self.out3b.setChecked(True)
        self.out4 = QLabel(self.tr('Fish Information'))
        self.out4a = QCheckBox(self.tr('Yes'))
        self.out4a.clicked.connect(lambda: self.check_uncheck(self.out4a, self.out4b))
        self.out4b = QCheckBox(self.tr('No'))
        self.out4b.clicked.connect(lambda: self.check_uncheck(self.out4b, self.out4a))
        if fig_dict['fish_info'] == 'True':  # is a string not a boolean
            self.out4a.setChecked(True)
            self.out4b.setChecked(False)
        else:
            self.out4a.setChecked(False)
            self.out4b.setChecked(True)

        # other options
        self.outgen = QLabel(self.tr(' <b> General Options </b>'))
        self.l1 = QLabel(self.tr('2D minimum water height [m]'))
        self.hopt = QLineEdit(str(fig_dict['min_height_hyd']))
        # erase data or not
        self.out5 = QLabel(self.tr('Erase data if identical model'))
        self.out5a = QCheckBox(self.tr('Yes'))
        self.out5a.clicked.connect(lambda: self.check_uncheck(self.out5a, self.out5b))
        self.out5b = QCheckBox(self.tr('No'))
        self.out5b.clicked.connect(lambda: self.check_uncheck(self.out5b, self.out5a))
        if fig_dict['erase_id'] == 'True':  # is a string not a boolean
            self.out5a.setChecked(True)
            self.out5b.setChecked(False)
        else:
            self.out5a.setChecked(False)
            self.out5b.setChecked(True)

        # save
        self.saveb = QPushButton(self.tr('Save options'))
        self.saveb.clicked.connect(self.save_option_fig)

        # empty frame scrolable
        content_widget = QFrame()

        self.layout = QGridLayout(content_widget)
        self.layout.addWidget(self.fig0l, 0, 0)
        self.layout.addWidget(self.fig1l, 1, 0)
        self.layout.addWidget(self.fig2l, 2, 0)
        self.layout.addWidget(self.fig3l, 3, 0)
        self.layout.addWidget(self.fig5l, 4, 0)
        self.layout.addWidget(self.fig6l, 5, 0)
        self.layout.addWidget(self.fig7l, 6, 0)
        self.layout.addWidget(self.fig8l, 7, 0)
        self.layout.addWidget(self.fig9l, 8, 0)
        self.layout.addWidget(self.fig10l, 9, 0)
        self.layout.addWidget(self.fig11l, 10, 0)
        self.layout.addWidget(self.fig12l, 11, 0)
        self.layout.addWidget(self.out9, 12, 0)

        self.layout.addWidget(self.fig1, 1, 1 ,1, 2)
        self.layout.addWidget(self.fig2, 2, 1, 1, 2)
        self.layout.addWidget(self.fig3, 3, 1, 1, 2)
        self.layout.addWidget(self.fig5, 4, 1, 1, 2)
        self.layout.addWidget(self.fig6, 5, 1, 1, 2)
        self.layout.addWidget(self.fig7a, 6, 1, 1, 1)
        self.layout.addWidget(self.fig7b, 6, 2, 1, 1)
        self.layout.addWidget(self.fig8, 7, 1, 1, 2)
        self.layout.addWidget(self.fig9a, 8, 1, 1, 1)
        self.layout.addWidget(self.fig9b, 8, 2, 1, 1)
        self.layout.addWidget(self.fig10, 9, 1, 1, 2)
        self.layout.addWidget(self.fig11, 10, 1, 1, 2)
        self.layout.addWidget(self.fig12, 11, 1, 1, 2)
        self.layout.addWidget(self.out9a, 12, 1, 1, 1)
        self.layout.addWidget(self.out9b, 12, 2, 1, 1)

        self.layout.addWidget(self.outgen, 0, 3)
        self.layout.addWidget(self.l1, 1, 3)
        self.layout.addWidget(self.hopt, 1, 4,1, 2)
        self.layout.addWidget(self.out5, 2, 3)
        self.layout.addWidget(self.out5a, 2, 4)
        self.layout.addWidget(self.out5b, 2, 5)

        self.layout.addWidget(self.out0, 3, 3,2,1)
        self.layout.addWidget(self.out1, 5, 3)
        self.layout.addWidget(self.out1a, 5, 4)
        self.layout.addWidget(self.out1b, 5, 5)
        self.layout.addWidget(self.out2, 6, 3)
        self.layout.addWidget(self.out2a, 6, 4)
        self.layout.addWidget(self.out2b, 6, 5)
        self.layout.addWidget(self.out3, 7, 3)
        self.layout.addWidget(self.out3a, 7, 4)
        self.layout.addWidget(self.out3b, 7, 5)
        self.layout.addWidget(self.out4, 8, 3)
        self.layout.addWidget(self.out4a, 8, 4)
        self.layout.addWidget(self.out4b, 8, 5)
        self.layout.addWidget(self.saveb, 21, 4, 1, 2)

        self.layout.setAlignment(Qt.AlignTop)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content_widget)

    def check_uncheck(self, main_checkbox, other_checkbox):
        """
        This function is used to check a box when the user clied on it and unckeked another passed as parameter

        :param main_checkbox: A QCheckBox which sould by selected
        :param other_checkbox: A QCheckbox which should be "unticked" when main_checkbox is selected by the user
        """
        main_checkbox.setChecked(True)
        other_checkbox.setChecked(False)

    def save_option_fig(self):
        """
        A function which save the options for the figures in the xlm project file. The options for the figures are
        contained in a dictionnary. The idea is to give this dictinnory in argument to all the fonction which create
        figures. In the xml project file, the options for the figures are saved under the attribute "Figure_Option".

        If you change things here, it is necessary to start a new project as the old projects will not be compatible.
        For the new version of HABBY, it will be necessary to insure compatibility by adding xml attribute.
        """

        # get default option
        fig_dict = create_default_figoption()

        # get the data and check validity
        # fig_size
        fig_size = self.fig1.text()
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
        c1 = str(self.fig2.currentText())
        if c1:
            fig_dict['color_map1'] = c1
        c2 = str(self.fig3.currentText())
        if c2:
            fig_dict['color_map2'] = c2
        # font size
        font_size = self.fig5.text()
        if font_size:
            try:
                fig_dict['font_size'] = int(font_size)
            except ValueError:
                self.send_log.emit('Error: Font size should be an integer. \n')
        # line width
        line_width = self.fig6.text()
        if line_width:
            try:
                fig_dict['line_width'] = int(line_width)
            except ValueError:
                self.send_log.emit('Error: Line width should be an integer. \n')
        # grid
        if self.fig7a.isChecked() and self.fig7b.isChecked():
            self.send_log.emit('Error: Grid cannot be on and off at the same time. \n')
        if self.fig7a.isChecked():
            fig_dict['grid'] = True
        elif self.fig7b.isChecked():
            fig_dict['grid'] = False
        # time step
        fig_dict['time_step'] = str(self.fig8.text())
        # raw data
        if self.fig9a.isChecked() and self.fig9b.isChecked():
            self.send_log.emit('Error: The option to plot raw output cannot be on and off at the same time. \n')
        if self.fig9a.isChecked():
            fig_dict['raw_data'] = True
        elif self.fig9b.isChecked():
            fig_dict['raw_data'] = False
        # format
        fig_dict['format'] = str(self.fig10.currentIndex())
        # resolution
        try:
            fig_dict['resolution'] = int(self.fig11.text())
        except ValueError:
            self.send_log.emit('Error: the resolution should be an integer. \n')
        if fig_dict['resolution'] < 0:
            self.send_log.emit('Error: The resolution should be higher than zero \n')
            return
        if fig_dict['resolution'] > 2000:
            self.send_log.emit('Warning: The resolution is higher than 2000 dpi. Figures might be very large.\n')

        # fish name type
        fig_dict['fish_name_type'] = int(self.fig12.currentIndex())
        # marker
        if self.out9a.isChecked():
            fig_dict['marker'] = True
        elif self.out9b.isChecked():
            fig_dict['marker'] = False
        # outputs
        if self.out1a.isChecked() and self.out1b.isChecked():
            self.send_log.emit('Error: Text Output cannot be on and off at the same time. \n')
        if self.out1a.isChecked():
            fig_dict['text_output'] = True
        elif self.out1b.isChecked():
            fig_dict['text_output'] = False
        if self.out2a.isChecked() and self.out2b.isChecked():
            self.send_log.emit('Error: Shapefile output cannot be on and off at the same time. \n')
        if self.out2a.isChecked():
            fig_dict['shape_output'] = True
        elif self.out2b.isChecked():
            fig_dict['shape_output'] = False
        if self.out3a.isChecked() and self.out3b.isChecked():
            self.send_log.emit('Error: Paraview cannot be on and off at the same time. \n')
        if self.out3a.isChecked():
            fig_dict['paraview'] = True
        elif self.out3b.isChecked():
            fig_dict['paraview'] = False
        if self.out4a.isChecked():
            fig_dict['fish_info'] = True
        elif self.out4b.isChecked():
            fig_dict['fish_info'] = False
        # other option
        try:
            fig_dict['min_height_hyd'] = float(self.hopt.text())
        except ValueError:
            self.send_log.emit('Error: Minimum Height should be a number')
        if self.out5a.isChecked():
            fig_dict['erase_id'] = True
        elif self.out5b.isChecked():
            fig_dict['erase_id'] = False

        # save the data in the xml file
        # open the xml project file
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Image Options Not Saved"))
            self.msg2.setText(
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
        else:
            doc = ET.parse(fname)
            root = doc.getroot()
            child1 = root.find(".//Figure_Option")
            if child1 is not None: # modify existing option
                width1 = root.find(".//Width")
                height1 = root.find(".//Height")
                colormap1 = root.find(".//ColorMap1")
                colormap2 = root.find(".//ColorMap2")
                fontsize1 = root.find(".//FontSize")
                linewidth1 = root.find(".//LineWidth")
                grid1 = root.find(".//Grid")
                time1 = root.find(".//TimeStep")
                raw1 = root.find(".//PlotRawData")
                format1 = root.find(".//Format")
                reso1 = root.find(".//Resolution")
                fish1 = root.find(".//FishNameType")
                marker1 = root.find(".//Marker")
                text1 = root.find(".//TextOutput")
                shape1 = root.find(".//ShapeOutput")
                para1 = root.find(".//ParaviewOutput")
                langfig1 = root.find(".//LangFig")
                hopt1 = root.find(".//MinHeight")
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
                time1 = ET.SubElement(child1, 'TimeStep')
                raw1 = ET.SubElement(child1, "PlotRawData")
                format1 = ET.SubElement(child1, "Format")
                reso1 = ET.SubElement(child1, "Resolution")
                fish1 = ET.SubElement(child1, "FishNameType")
                marker1 = ET.SubElement(child1,"Marker")
                text1 = ET.SubElement(child1, "TextOutput")
                shape1 = ET.SubElement(child1, "ShapeOutput")
                para1 = ET.SubElement(child1, "ParaviewOutput")
                langfig1 = ET.SubElement(child1, "LangFig")
                hopt1 = ET.SubElement(child1, "MinHeight")
                fishinfo1 = ET.SubElement(child1, "FishInfo")
                erase1 = ET.SubElement(child1,"EraseId")
            width1.text = str(fig_dict['width'])
            height1.text = str(fig_dict['height'])
            colormap1.text = fig_dict['color_map1']
            colormap2.text = fig_dict['color_map2']
            fontsize1.text = str(fig_dict['font_size'])
            linewidth1.text = str(fig_dict['line_width'])
            grid1.text = str(fig_dict['grid'])
            time1.text = str(fig_dict['time_step']) # -99 is all time steps
            raw1.text = str(fig_dict['raw_data'])
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
            hopt1.text = str(fig_dict['min_height_hyd'])
            fishinfo1.text = str(fig_dict['fish_info'])
            erase1.text = str(fig_dict['erase_id'])
            doc.write(fname)

        self.send_log.emit('The new options for the figures are saved. \n')
        self.send_log.emit('# Modifications of figure options. \n')
        # self.send_log.emit('restart     SAVE_OPTION_FIG')


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
        #print('Error: project is not found \n')
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
            time1 = root.find(".//TimeStep")
            raw1 = root.find(".//PlotRawData")
            format1 = root.find(".//Format")
            marker1 = root.find(".//Marker")
            reso1 = root.find(".//Resolution")
            fish1 = root.find(".//FishNameType")
            text1 = root.find(".//TextOutput")
            shape1 = root.find(".//ShapeOutput")
            para1 = root.find(".//ParaviewOutput")
            langfig1 = root.find(".//LangFig")
            hopt1 = root.find(".//MinHeight")
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
                if time1 is not None:
                    fig_dict['time_step'] = time1.text # -99 is all
                if raw1 is not None:
                    fig_dict['raw_data'] = raw1.text
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
                if langfig1 is not None:
                    fig_dict['language'] = int(langfig1.text)
                if hopt1 is not None:
                    fig_dict['min_height_hyd'] = float(hopt1.text)
                if fish1 is not None:
                    fig_dict['fish_info'] = fishinfo1.text
                if erase1 is not None:
                    fig_dict['erase_id'] = erase1.text
            except ValueError:
                print('Error: Figure Options are not of the right type.\n')

    fig_dict['time_step'] = fig_dict['time_step'].split(',')
    try:
        fig_dict['time_step'] = list(map(int, fig_dict['time_step']))
    except ValueError:
        print('Error: Time step could not be read in the options')  # sendLog not read yet

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
    fig_dict['time_step'] = '1,-1'
    fig_dict['raw_data'] = 'False'
    fig_dict['format'] = 3
    fig_dict['resolution'] = 800
    fig_dict['fish_name_type'] = 0
    fig_dict['text_output'] = 'True'
    fig_dict['shape_output'] = 'True'
    fig_dict['paraview'] = 'True'
    fig_dict['fish_info'] = 'True'
    # this is dependant on the language of the application not the user choice in the output tab
    fig_dict['language'] = 0  # 0 english, 1 french
    fig_dict['min_height_hyd'] = 0.001  # water height under 1mm is not accounted for
    fig_dict['marker'] = 'True'  # Add point to line plot
    fig_dict['erase_id'] = 'True'
    fig_dict['type_plot'] = 'display'

    return fig_dict


if __name__ == '__main__':
    pass
