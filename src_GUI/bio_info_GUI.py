from io import StringIO
from PyQt5.QtCore import QTranslator, pyqtSignal, QThread, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox, QAbstractItemView, QSizePolicy, QScrollArea
from PyQt5.QtGui import QPixmap, QFont
import os
import sys
import time
import numpy as np
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import bio_info
from src_GUI import estimhab_GUI


class BioInfo(estimhab_GUI.StatModUseful):
    """
    This class contains the tab with the biological information (the curves of preference). It inherites from
    StatModUseful. StatModuseful is a QWidget, with some practical signal (send_log and show_fig) and some functions
    to find path_im and path_bio (the path wher to save image) and to manage lists.
    """

    def __init__(self, path_prj, name_prj, lang='French'):
        super().__init__()
        self.lang = lang
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.imfish = ''

        # attribute from the xml which the user can search the database
        # the name should refect the xml attribute or bio_info.load_xml_name() should be changed
        # can be changed but with caution
        # coorect here for new language by adding an attribute in the form "langue"_common_name
        # stage have to be the first attribute !
        self.attribute_acc = ['Stage', 'French_common_name','English_common_name', 'Code_ONEMA', 'Code_Sandre',
                              'LatinName', 'CdBiologicalModel']
        self.name_database = 'pref_bio.db'

        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        # the available merged data
        l0 = QLabel(self.tr('<b> Substrate and hydraulic data </b>'))
        self.m_all = QComboBox()

        # create lists with the possible fishes
        l1 = QLabel(self.tr('<b> Available Fish and Guild </b>'))
        l2 = QLabel(self.tr('<b> Selected Fish and Guild </b>'))
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_f.itemClicked.connect(self.add_fish)
        self.list_s.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_s.itemClicked.connect(self.remove_fish)
        self.list_f.itemActivated.connect(self.add_fish)
        self.list_s.itemActivated.connect(self.remove_fish)
        self.runhab = QPushButton(self.tr('Compute Habitat Value'))
        self.runhab.setStyleSheet("background-color: #31D656")
        spacer1 = QSpacerItem(1, 1)
        spacer2 = QSpacerItem(300, 1)

        # info on pref
        l4 = QLabel(self.tr('<b> Information on the suitability curve</b>'))
        l5 = QLabel(self.tr('Latin Name: '))
        self.com_name = QLabel()
        l7 = QLabel(self.tr('ONEMA fish code: '))
        self.fish_code = QLabel('')
        l8 = QLabel(self.tr('Description:'))
        self.descr = QLabel()
        self.pref_curve = QPushButton(self.tr('Show suitability curve'))

        # get a scollable area for the decription which might be long
        self.scroll = QScrollArea()
        self.vbar = self.scroll.verticalScrollBar()
        self.descr.setWordWrap(True)
        self.descr.setMaximumSize(200,210)
        self.descr.setAlignment(Qt.AlignTop)
        self.descr.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.descr.setTextFormat(Qt.RichText)
        self.scroll.setWidget(self.descr)
        # to have the Qlabel at the right size
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('background-color: white')
        self.vbar.setStyleSheet('background-color: lightGrey')

        # image fish
        self.pic = QLabel()

        # hydrosignature
        self.hs = QPushButton(self.tr('Show Hydrosignature'))
        self.hs.clicked.connect(self.show_hydrosignature)

        # search possibility
        l3 = QLabel(self.tr('<b> Search biological models </b>'))
        self.keys = QComboBox()
        self.keys.addItems(self.attribute_acc)
        l02 = QLabel('is equal to')
        l02.setAlignment(Qt.AlignCenter)
        self.cond1 = QLineEdit()
        self.bs = QPushButton(self.tr('Select suitability curve'))
        self.bs.clicked.connect(self.select_fish)

        # fill in list of fish
        sys.stdout = self.mystdout = StringIO()
        self.data_fish = bio_info.load_xml_name(self.path_bio, self.attribute_acc)
        sys.stdout = sys.__stdout__
        #self.send_err_log()
        self.list_f.addItems(self.data_fish[:, 0])
        self.list_f.itemClicked.connect(self.show_info_fish)
        # fill hdf5 list
        self.update_merge_list()

        # layout
        self.layout4 = QGridLayout()
        self.layout4.addWidget(l0, 0, 0)
        self.layout4.addWidget(self.m_all, 0, 1, 1, 2)

        self.layout4.addWidget(l1, 1, 0)
        self.layout4.addWidget(l2, 1, 1)
        self.layout4.addWidget(self.list_f, 2, 0, 2, 1)
        self.layout4.addWidget(self.list_s, 2, 1, 2, 2)

        self.layout4.addWidget(l4, 5,0)
        self.layout4.addWidget(l5, 6, 0)
        self.layout4.addWidget(self.com_name, 6, 1)
        self.layout4.addWidget(l7, 7, 0)
        self.layout4.addWidget(self.fish_code,7, 1)
        self.layout4.addWidget(l8,8,0)
        self.layout4.addWidget(self.scroll, 8, 1, 3, 2) # in fact self.descr is in self.scoll
        self.layout4.addWidget(self.pic, 10, 0)

        self.layout4.addWidget(self.runhab, 3, 3)
        self.layout4.addWidget(self.pref_curve, 8, 3)
        self.layout4.addWidget(self.hs, 9, 3)

        self.layout4.addWidget(l3, 11, 0)
        self.layout4.addWidget(self.keys,12, 0)
        self.layout4.addWidget(l02,12, 1)
        self.layout4.addWidget(self.cond1,12, 2)
        self.layout4.addWidget(self.bs, 12, 3)

        self.layout4.addItem(spacer1, 0, 2)
        self.layout4.addItem(spacer2, 3, 3)
        self.setLayout(self.layout4)

    def show_info_fish(self):
        """
        This function shows the useful information concerning the selected fish on the GUI
        """

        # get the file
        i = self.list_f.currentRow() # show the info concerning the one selected fish
        xmlfile = os.path.join(self.path_bio, self.data_fish[i, 2])

        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml file does not exist \n")
                return
        except ET.ParseError:
            print("Warning: the xml file is not well-formed.\n")
            return

        # should be found again because attribute_acc can change
        # get the data code ONEMA
        # for the moment only one code alternativ possible
        data = root.find('.//CdAlternative')
        if data is not None:
            if data.attrib['OrgCdAlternative']:
                if data.attrib['OrgCdAlternative'] == 'ONEMA':
                    self.fish_code.setText(data.text)

        # get the latin name
        data = root.find('.//LatinName')
        if data is not None:
            self.com_name.setText(data.text)

        # get the description
        data = root.findall('.//Description')
        if data is not None:
            found= False
            for d in data:
                if d.attrib['Language'] == self.lang:
                    self.descr.setText(d.text)
                    found = True
            if not found:
                self.descr.setText(d[0].text)

        # get the image fish
        data = root.find('.//Image')
        if data is not None:
            self.imfish = data.text
            # use full ABSOLUTE path to the image, not relative
            self.pic.setPixmap(QPixmap(os.path.join(os.getcwd(), os.path.join(self.path_bio, self.imfish))
                                       ).scaled(200, 70, Qt.KeepAspectRatio))  # 800 500

    def show_hydrosignature(self):
        """
        This function make the link with function in bio_info.py which allows to load and plot the data realted
        to the hydrosignature.
        """

        # get the file
        i = self.list_f.currentRow()
        xmlfile = os.path.join(self.path_bio, self.data_fish[i, 2])
        # do the plot
        bio_info.plot_hydrosignature(xmlfile)
        # show the plot
        self.show_fig.emit()

    def select_fish(self):
        """
        This function select the fish which corresponds at the chosen criteria by the user. The type of criteria
        is given in the list self.keys and the criteria is given in self.cond1. The condition should exactly
        match the criteria. Sign such as * does not work.
        """
        # get item s to be selected
        i = self.keys.currentIndex() # item type
        cond = self.cond1.text()
        if i == 0:
            i = -1 # i +2=1 for the key called 'stage' which is on the second colum of self.data_type
        if cond in self.data_fish[:, i+2]:
            inds = np.where(self.data_fish[:, i+2] == cond)[0]
        else:
            self.send_log.emit(self.tr('Warning: No suitability curve found for the last selection. \n'))
            return

        # get the new selection
        for ind in inds:
            self.list_f.setCurrentRow(int(ind))
            # add the fish to the QListView
            self.add_fish()

    def update_merge_list(self):
        """
        This function goes in the projet xml file and gets all available merged data. Usually, it is called
        by Substrate() (when finished to merge some data) or at the start of HABBY.
        """

        xmlfile = os.path.join(self.path_prj, self.name_prj +'.xml')
        # open the file
        try:
            try:
                docxml = ET.parse(xmlfile)
                root = docxml.getroot()
            except IOError:
                print("Warning: the xml project file does not exist \n")
                return
        except ET.ParseError:
            print("Warning: the xml project file is not well-formed.\n")
            return

        self.m_all.clear()

        # get filename
        files = root.findall('.//hdf5_mergedata')

        # add it to the list
        if files is not None:
            for f in files:
                if len(f.text) <30:
                    self.m_all.addItem(f.text)
                else:
                    blob = f.text[:30] + '...'
                    self.m_all.addItem(blob)




