
from PyQt5.QtCore import QTranslator, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import numpy as np
import os

class outputW(QWidget):
    """
    The class which support the creation and management of the output
    """
    send_log = pyqtSignal(str, name='send_log')

    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        # list with the available color map
        self.namecmap = ['magma','viridis', 'inferno', 'plasma', 'Blues',
                         'Greens', 'Greys', 'Oranges', 'Purples',
                         'Reds', 'gist_earth', 'terrain', 'ocean', ]
        self.init_iu()

    def init_iu(self):

        # read actual figure option
        fig_dict = load_fig_option(self.path_prj, self.name_prj)

        # on half of the widget, give options to create the figure
        self.fig0l = QLabel(self.tr('<b> Figures Options </b>'), self)
        self.fig1l = QLabel(self.tr('Figure Size'), self)
        self.fig2l = QLabel(self.tr('Color Map 1'), self)
        self.fig3l = QLabel(self.tr('Color Map 2'), self)
        # self.fig4l = QLabel(self.tr('Line Color'), self)
        # http://pyqt.sourceforge.net/Docs/PyQt4/qcolordialog.html
        # you should check to have enough color than the number of line to plot
        self.fig5l = QLabel(self.tr('Font Size'), self)
        self.fig6l = QLabel(self.tr('Line Width'), self)
        self.fig7l = QLabel(self.tr('Grid'), self)
        self.fig8l = QLabel(self.tr('Dot size'), self)

        self.fig1 = QLineEdit(str(fig_dict['width']) + ',' + str(fig_dict['height']))
        #self.fig1bisl = QLabel(self.tr('format: width,height [cm]'), self)
        # color map needs to be updated also!
        self.fig2 = QComboBox()
        self.fig2.addItems(self.namecmap)
        self.fig3 = QComboBox()
        self.fig3.addItems(self.namecmap)
        self.fig5 = QLineEdit(str(fig_dict['font_size']))
        self.fig6 = QLineEdit(str(fig_dict['line_width']))
        self.fig7a = QCheckBox(self.tr('On'), self)
        self.fig7b = QCheckBox(self.tr('Off'), self)
        if fig_dict['grid'] == 'True':   # is a string not a boolean
            self.fig7a.setChecked(True)
            self.fig7b.setChecked(False)
        else:
            self.fig7a.setChecked(False)
            self.fig7b.setChecked(True)
        self.fig8 = QLineEdit(str(fig_dict['scatter_s']))
        self.saveb =QPushButton(self.tr('Save options'))
        self.saveb.clicked.connect(self.save_option_fig)

        spacer = QSpacerItem(300, 10)
        spacer2 = QSpacerItem(10, 70)

        self.layout = QGridLayout()
        self.layout.addWidget(self.fig0l, 0, 0)
        self.layout.addWidget(self.fig1l, 1, 0)
        self.layout.addWidget(self.fig2l, 2, 0)
        self.layout.addWidget(self.fig3l, 3, 0)
        #self.layout.addWidget(self.fig4l, 0, 0)
        self.layout.addWidget(self.fig5l, 4, 0)
        self.layout.addWidget(self.fig6l, 5, 0)
        self.layout.addWidget(self.fig7l, 6, 0)
        self.layout.addWidget(self.fig8l, 7, 0)
        self.layout.addWidget(self.fig1, 1, 1,1,2)
        #self.layout.addWidget(self.fig1bisl, 1, 2)
        self.layout.addWidget(self.fig2, 2, 1, 1, 2)
        self.layout.addWidget(self.fig3, 3, 1, 1, 2)
        #self.layout.addWidget(self.fig4, 1, 4)
        self.layout.addWidget(self.fig5, 4, 1, 1, 2)
        self.layout.addWidget(self.fig6, 5, 1, 1, 2)
        self.layout.addWidget(self.fig7a, 6, 1, 1, 1)
        self.layout.addWidget(self.fig7b, 6, 2, 1, 1)
        self.layout.addWidget(self.fig8, 7, 1, 1, 2)
        self.layout.addWidget(self.saveb, 8, 1, 1, 2)
        self.layout.addItem(spacer, 5, 3)
        self.layout.addItem(spacer2, 8, 2)

        self.setLayout(self.layout)

    def save_option_fig(self):
        """
        A function which save the options for the figure in the xlm project file
        :return:
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
            fig_dict['color_map2'] = c1
        # font size
        font_size = self.fig5.text()
        if font_size:
            try:
                fig_dict['font_size'] = int(font_size)
            except ValueError:
                self.send_log.emit('Error: Font size should be an integer. \n')
        # line width
        font_size = self.fig6.text()
        if font_size:
            try:
                fig_dict['font_size'] = int(font_size)
            except ValueError:
                self.send_log.emit('Error: Font size should be an integer. \n')
        # grid
        if self.fig7a.isChecked() and self.fig7b.isChecked():
            self.send_log.emit('Error: Grid cannot be on and off at the same time. \n')
        if self.fig7a.isChecked():
            fig_dict['grid'] = True
        elif self.fig7b.isChecked():
            fig_dict['grid'] = False
        # scatter
        scatter_size = self.fig8.text()
        if scatter_size:
            try:
                fig_dict['scatter_s'] = int(scatter_size)
            except ValueError:
                self.send_log.emit('Error: Size of the dots in the scatter plot should be an integer. \n')

        # save the data in the xml file
        # open the xml project file
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        # save the name and the path in the xml .prj file
        if not os.path.isfile(fname):
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Project Not Saved"))
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
                dot_size1 = root.find(".//ScatterS")
            else: # save in case no fig option exist
                child1 = ET.SubElement(root, 'Figure_Option')
                width1 = ET.SubElement(child1, 'Width')
                height1 = ET.SubElement(child1, 'Height')
                colormap1 = ET.SubElement(child1, 'ColorMap1')
                colormap2 = ET.SubElement(child1, 'ColorMap2')
                fontsize1 = ET.SubElement(child1, 'FontSize')
                linewidth1 = ET.SubElement(child1, 'LineWidth')
                grid1 = ET.SubElement(child1, 'Grid')
                dot_size1 = ET.SubElement(child1, 'ScatterS')
            width1.text = str(fig_dict['width'])
            height1.text = str(fig_dict['height'])
            colormap1.text = fig_dict['color_map1']
            colormap2.text = fig_dict['color_map2']
            fontsize1.text = str(fig_dict['font_size'])
            linewidth1.text = str(fig_dict['line_width'])
            grid1.text = str(fig_dict['grid'])
            dot_size1.text = str(fig_dict['scatter_s'])
            doc.write(fname)

        self.send_log.emit('The new options for the figures are saved. \n')
        self.send_log.emit('py     save_option_fig() - correct this')
        self.send_log.emit('restart     SAVE_OPTION_FIG')


def load_fig_option(path_prj, name_prj):
    """
    load the figure option saved in the xml file. If the options are not written or if the porject is not saved,
    use data by default.
    :param path_prj: the path to the xml project file
    :param name_prj: the name to this file
    :return: the dictionary containing the figure option
    """

    fig_dict = create_default_figoption()
    fname = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(fname) and name_prj != '':  # no project exists
        pass
    elif not os.path.isfile(fname):  # the project is not found
        print('Error: No project file (.xml) found.\n')
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
            dot_size1 = root.find(".//ScatterS")
            try:
                fig_dict['width'] = float(width1.text)
                fig_dict['height'] = float(height1.text)
                fig_dict['color_map1'] = colormap1.text
                fig_dict['color_map2'] = colormap2.text
                fig_dict['font_size'] = int(fontsize1.text)
                fig_dict['line_width'] = int(linewidth1.text)
                fig_dict['grid'] = grid1.text
                fig_dict['scatter_s'] = int(dot_size1.text)
            except ValueError:
                print('Error: Figure Options are not of the right type.\n')
    return fig_dict

def create_default_figoption():
    """
    create the default dictionnary of option for the figure (static)
    :return:
    """
    fig_dict = {}
    fig_dict['height'] = 7
    fig_dict['width'] = 10
    fig_dict['color_map1'] = 'terrain'
    fig_dict['color_map2'] = 'gist_earth'
    fig_dict['font_size'] = 12
    fig_dict['line_width'] = 1
    fig_dict['grid'] = False
    fig_dict['scatter_s'] = 5000

    return fig_dict












