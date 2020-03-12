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
from src import estimhab_mod
import glob
import matplotlib.pyplot as plt

from lxml import etree as ET
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QHBoxLayout, QVBoxLayout,  \
    QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QSpacerItem, QGroupBox, QSizePolicy, \
    QAbstractItemView, QMessageBox, QScrollArea, QFrame
from PyQt5.QtGui import QFont, QIcon
from multiprocessing import Process, Value
import sys
from io import StringIO
from src import hdf5_mod
from src.tools_mod import DoubleClicOutputGroup
from src_GUI.data_explorer_GUI import MyProcessList
from src.project_properties_mod import load_project_properties


class StatModUseful(QScrollArea):
    """
    This class is not called directly by HABBY, but it is the parent class of EstihabW and FstressW. As fstress and
    estimhab have a similar graphical user interface, this architecture allows to re-use some functions between the
    two classes, which saves a bit of coding.
    """
    send_log = pyqtSignal(str, name='send_log')
    """
    PyQtsignal to write the log.
    """
    show_fig = pyqtSignal()
    """
    PyQtsignal to show the figures.
    """

    def __init__(self):
        self.path_bio = 'biology'
        self.eq1 = QLineEdit()
        self.ew1 = QLineEdit()
        self.eh1 = QLineEdit()
        self.eq2 = QLineEdit()
        self.ew2 = QLineEdit()
        self.eh2 = QLineEdit()
        self.eqmin = QLineEdit()
        self.eqmax = QLineEdit()
        self.eqtarget = QLineEdit()
        self.target_lineedit_list = [self.eqtarget]
        self.add_qtarget_button = QPushButton()
        self.add_qtarget_button.setIcon(QIcon(os.path.join(os.getcwd(), "translation", "icon", "plus.png")))
        self.add_qtarget_button.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
        self.list_f = QListWidget()
        self.selected_aquatic_animal_qtablewidget = QListWidget()
        self.msge = QMessageBox()
        self.fish_selected = []
        self.qall = []  # q1 q2 qmin qmax q50. Value cannot be added directly because of stathab.

        super().__init__()

    def add_fish(self):
        """
        The function is used to select a new fish species (or inverterbrate)
        """
        items = self.list_f.selectedItems()
        ind = []
        if items:
            for i in range(0, len(items)):
                # avoid to have the same fish multiple times
                if items[i].text() in self.fish_selected:
                    pass
                else:
                    self.fish_selected.append(items[i].text())

        # order the list (careful QLIstWidget do not order as sort from list)
        if self.fish_selected:
            self.fish_selected.sort()
            self.selected_aquatic_animal_qtablewidget.clear()
            self.selected_aquatic_animal_qtablewidget.addItems(self.fish_selected)
            # bold for selected fish
            font = QFont()
            font.setBold(True)
            for i in range(0, self.list_f.count()):
                for f in self.fish_selected:
                    if f == self.list_f.item(i).text():
                        self.list_f.item(i).setFont(font)

    def remove_fish(self):
        """
        The function is used to remove fish species (or inverterbates species)
        """
        item = self.selected_aquatic_animal_qtablewidget.takeItem(self.selected_aquatic_animal_qtablewidget.currentRow())
        try:
            self.fish_selected.remove(item.text())
        except ValueError:
            pass
        # bold for selected fish
        font = QFont()
        font.setBold(False)
        for i in range(0, self.list_f.count()):
            if item.text() == self.list_f.item(i).text():
                self.list_f.item(i).setFont(font)
        item = None

    def remove_all_fish(self):
        """
        This function removes all fishes from the selected fish
        """
        self.selected_aquatic_animal_qtablewidget.clear()
        self.list_f.clear()
        self.fish_selected = []
        self.list_f.addItems(self.data_fish[:, 0])

    def add_sel_fish(self):
        """
        This function loads the xml file and check if some fish were selected before. If yes, we add them to the list
        """

        # open the xml file
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            # get the selected fish
            child = root.find(".//Habitat/fish_selected")
            if child is not None:
                fish_selected_b = child.text
                if fish_selected_b is not None:
                    if ',' in fish_selected_b:
                        fish_selected_b = fish_selected_b.split(',')
                    # show it
                    for i in range(0, self.list_f.count()):
                        self.list_f.clearSelection()
                        self.list_f.setCurrentRow(i)
                        items = self.list_f.selectedItems()
                        if items:
                            fish_l = items[0].text()
                            if fish_l in fish_selected_b:  # do not work with space here
                                self.add_fish()

    def find_path_im_est(self):
        """
        A function to find the path where to save the figues. Careful there is similar function in hydro_sub_GUI.py.
        Do not mix it up

        :return: path_im a string which indicates the path to the folder where are save the images.
        """
        # to insure the existence of a path
        path_im = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            child = root.find(".//path_figure")
            if child is None:
                path_test = os.path.join(self.path_prj, r'/figures')
                if os.path.isdir(path_test):
                    path_im = path_test
                else:
                    path_im = self.path_prj
            else:
                path_im = os.path.join(self.path_prj, child.text)
        else:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_im

    def find_path_hdf5_est(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in hydro_sub_GUI.py and in
        stathab_c. By default, path_hdf5 is in the project folder in the folder 'hdf5'.
        """

        path_hdf5 = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            path_hdf5 = load_project_properties(self.path_prj)["path_hdf5"]
            # parser = ET.XMLParser(remove_blank_text=True)
            # doc = ET.parse(filename_path_pro, parser)
            # root = doc.getroot()
            # child = root.find(".//path_hdf5")
            # if child is None:
            #     path_hdf5 = os.path.join(self.path_prj, 'hdf5')
            # else:
            #     path_hdf5 = os.path.join(self.path_prj, child.text)
        else:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_hdf5

    def find_path_text_est(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_hdf5 is in the project folder in the folder 'hdf5'.
        """

        path_text = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            child = root.find(".//path_text")
            if child is None:
                path_text = os.path.join(self.path_prj, r'/output/text')
            else:
                path_text = os.path.join(self.path_prj, child.text)
        else:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_text

    def find_path_output_est(self, att):
        """
        A function to find the path where to save the shapefile, paraview files and other future format. Here, we gave
        the xml attribute as argument so this functin can be used to find all path needed. However, it is less practical
        to use as the function above as one should remember the xml tribute to call this function. However, it can be
        practical to use to add new folder. Careful a similar function is in Hydro_GUI_2.py.

        :param att: the xml attribute (from the xml project file) linked to the path needed, without the .//

        """

        path_out = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            child = root.find(".//" + att)
            if child is None:
                return self.path_prj
            else:
                path_out = os.path.join(self.path_prj, child.text)
        else:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_out

    def find_path_input_est(self):
        """
        A function to find the path where to save the input file. Careful a similar one is in hydro_sub_GUI.py. By default,
        path_input indicates the folder 'input' in the project folder.
        """

        path_input = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            child = root.find(".//path_input")
            if child is None:
                path_input = os.path.join(self.path_prj, r'/input')
            else:
                path_input = os.path.join(self.path_prj, child.text)
        else:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_input

    def send_err_log(self):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout before calling this function. It only sends the hundred first errors
        to avoid freezing the GUI. A similar function exists in hydro_sub_GUI.py. Correct both if necessary.
        """
        max_send = 100
        if self.mystdout is not None:
            str_found = self.mystdout.getvalue()
        else:
            return
        str_found = str_found.split('\n')
        for i in range(0, min(len(str_found), max_send)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
            if i == max_send - 1:
                self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", 'too many information for the GUI.'))

    def check_all_q(self):
        """
        This function checks the range of the different discharge and send a warning if we are out of the range
        estimated reasonable (based on the manual from Estimhab and FStress). This is not used by Stathab.

        It uses the variable self.qall which is a list of float composed of q1, q2, qsim1, qsim2, q50. This function
        only send warning and it used to check the entry before the calculation.
        """

        if self.qall[0] < self.qall[1]:
            q1 = self.qall[0]
            q2 = self.qall[1]
        else:
            q2 = self.qall[0]
            q1 = self.qall[1]

        if q2 < 2 * q1:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", 'Measured discharges are not very different. The results might '
                               'not be realistic. \n'))
        if (self.qall[4] < q1 / 10 or self.qall[4] > 5 * q2) and self.qall[4] != -99:  # q50 not always necessary
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", 'Q50 should be between q1/10 and 5*q2 for optimum results.'))
        if self.qall[2] < q1 / 10 or self.qall[2] > 5 * q2:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", 'Discharge range should be between q1/10 and 5*q2 for optimum results (1).'))
        if self.qall[3] < q1 / 10 or self.qall[3] > 5 * q2:
            self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", 'Discharge range should be between q1/10 and 5*q2 for optimum results (2).'))


class EstimhabW(StatModUseful):
    """
    The Estimhab class provides the graphical interface for the version of the Estimhab model written in HABBY.
    The Estimhab model is described elsewhere. EstimhabW() just loads the data for Estimhab given by the user.
    """

    save_signal_estimhab = pyqtSignal()
    """
    PyQtsignal to save the Estimhab data.
    """

    def __init__(self, path_prj, name_prj):

        super().__init__()
        self.tab_name = "estimhab"
        self.eq50 = QLineEdit()
        self.esub = QLineEdit()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_bio_estimhab = os.path.join(self.path_bio, 'estimhab')
        self.process_list = MyProcessList("plot")
        self.total_lineedit_number = 1
        self.VH = []
        self.SPU = []
        self.filenames = []  # a list which link the name of the fish name and the xml file
        self.init_iu()

    def init_iu(self):

        """
        This function is used to initialized an instance of the EstimhabW() class. It is called by __init__().

         **Technical comments and walk-through**

         First we looked if some data for Estimhab was saved before by an user. If yes, we will fill the GUI with
         the information saved before. Estimhab information is saved in hdf5 file format and the path/name of the
         hdf5 file is saved in the xml project file. So we open the xml project file and look if the name of an hdf5
         file was saved for Estimhab. If yes, the hdf5 file is read.

         The format of hdf5 file is relatively simple. Each input data for Estimhab has its own dataset (qmes, hmes,
         wmes, q50, qrange, and substrate).  Then, we have a list of string which are a code for the fish species which
         were analyzed.  All the data contained in hdf5 file is loaded into variable.

         The different label are written on the graphical interface. Then, two QListWidget are modified. The first
         list contains all the fish species on which HABBY has info (see XML Estimhab format for more info).
         The second list is the fish selected by the user on which Estimhab will be run. Here, we link these lists
         with two functions so that the user can select/deselect fish using the mouse. The function name are add_fish()
         and remove_fish().

         Then, we fill the first list. HABBY look up all file of xml type in the “Path_bio” folder (the one indicated in
         the xml project file under the attribute “Path_bio”).  The name are them modified so that the only the name of
         species appears (and not the full path). We set the layout with all the different QLineEdit where the user
         can write the needed data.

         Estimhab model is saved using a function situated in MainWindows_1.py  (frankly, I am not so sure why I did put
         the save function there, but anyway). So the save button just send a signal to MainWindows
         here, which save the data.
        """

        available_model_label = QLabel(self.tr('Available'))
        selected_model_label = QLabel(self.tr('Selected'))

        self.lineedit_width = 50
        self.spacer_width = 50

        # input
        q1_layout = QHBoxLayout()
        q1_layout.addWidget(QLabel('Q1 [m<sup>3</sup>/s]'))
        q1_layout.addWidget(self.eq1)
        q1_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.eq1.setFixedWidth(self.lineedit_width)

        q2_layout = QHBoxLayout()
        q2_layout.addWidget(QLabel('Q2 [m<sup>3</sup>/s]'))
        q2_layout.addWidget(self.eq2)
        q2_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.eq2.setFixedWidth(self.lineedit_width)

        w1_layout = QHBoxLayout()
        w1_layout.addWidget(QLabel(self.tr("Width1 [m]")))
        w1_layout.addWidget(self.ew1)
        w1_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.ew1.setFixedWidth(self.lineedit_width)

        w2_layout = QHBoxLayout()
        w2_layout.addWidget(QLabel(self.tr("Width2 [m]")))
        w2_layout.addWidget(self.ew2)
        w2_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.ew2.setFixedWidth(self.lineedit_width)

        h1_layout = QHBoxLayout()
        h1_layout.addWidget(QLabel(self.tr("Height1 [m]")))
        h1_layout.addWidget(self.eh1)
        self.eh1.setFixedWidth(self.lineedit_width)

        h2_layout = QHBoxLayout()
        h2_layout.addWidget(QLabel(self.tr("Height2 [m]")))
        h2_layout.addWidget(self.eh2)
        self.eh2.setFixedWidth(self.lineedit_width)

        q50_layout = QHBoxLayout()
        q50_layout.addWidget(QLabel('Qmedian/Q50 [m<sup>3</sup>/s]'))
        q50_layout.addWidget(self.eq50)
        q50_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.eq50.setFixedWidth(self.lineedit_width)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(QLabel(self.tr('Mean substrate size [m]')))
        sub_layout.addWidget(self.esub)
        sub_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.esub.setFixedWidth(self.lineedit_width)

        # output
        q1out_layout = QHBoxLayout()
        q1out_layout.addWidget(QLabel(self.tr("Qmin [m<sup>3</sup>/s]")))
        q1out_layout.addWidget(self.eqmin)
        q1out_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.eqmin.setFixedWidth(self.lineedit_width)

        q2out_layout = QHBoxLayout()
        q2out_layout.addWidget(QLabel(self.tr("Qmax [m<sup>3</sup>/s]")))
        q2out_layout.addWidget(self.eqmax)
        q2out_layout.addItem(QSpacerItem(self.spacer_width, 1))
        self.eqmax.setFixedWidth(self.lineedit_width)

        self.q2target_layout = QHBoxLayout()
        self.q2target_layout.addWidget(QLabel(self.tr("Qtarget [m<sup>3</sup>/s]")))
        self.q2target_layout.addWidget(self.eqtarget)
        self.q2target_layout.addWidget(self.add_qtarget_button)
        self.add_qtarget_button.clicked.connect(self.add_new_qtarget)
        self.eqtarget.setFixedWidth(self.lineedit_width)

        # create lists with the possible fishes
        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_f.setDragDropMode(QAbstractItemView.DragDrop)
        self.list_f.setDefaultDropAction(Qt.MoveAction)
        self.list_f.setAcceptDrops(True)
        self.list_f.setSortingEnabled(True)

        self.selected_aquatic_animal_qtablewidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.selected_aquatic_animal_qtablewidget.setDragDropMode(QAbstractItemView.DragDrop)
        self.selected_aquatic_animal_qtablewidget.setDefaultDropAction(Qt.MoveAction)
        self.selected_aquatic_animal_qtablewidget.setAcceptDrops(True)
        self.selected_aquatic_animal_qtablewidget.setSortingEnabled(True)

        # insist on white background color (for linux, mac)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        # send model
        button1 = QPushButton(self.tr('Run and save ESTIMHAB'), self)
        button1.setStyleSheet("background-color: #47B5E6; color: black")
        button1.clicked.connect(self.run_estmihab)

        # empty frame scrolable
        content_widget = QFrame()

        # hydraulic_data_group
        hydraulic_data_group = QGroupBox(self.tr('Hydraulic data input'))
        hydraulic_data_layout = QGridLayout(hydraulic_data_group)
        hydraulic_data_layout.addLayout(q1_layout, 0, 0)
        hydraulic_data_layout.addLayout(w1_layout, 0, 1)
        hydraulic_data_layout.addLayout(h1_layout, 0, 2)
        hydraulic_data_layout.addLayout(q2_layout, 1, 0)
        hydraulic_data_layout.addLayout(w2_layout, 1, 1)
        hydraulic_data_layout.addLayout(h2_layout, 1, 2)
        hydraulic_data_layout.addLayout(q50_layout, 2, 0)
        hydraulic_data_layout.addLayout(sub_layout, 2, 1)
        hydraulic_data_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.doubleclick_input_group = DoubleClicOutputGroup()
        hydraulic_data_group.installEventFilter(self.doubleclick_input_group)
        self.doubleclick_input_group.double_clic_signal.connect(self.reset_hydraulic_data_input_group)

        # hydraulic_data_output_group
        hydraulic_data_output_group = QGroupBox(self.tr('Hydraulic data desired'))
        hydraulic_data_layout = QGridLayout(hydraulic_data_output_group)
        hydraulic_data_layout.addLayout(q1out_layout, 0, 0)
        hydraulic_data_layout.addLayout(q2out_layout, 0, 1)
        hydraulic_data_layout.addLayout(self.q2target_layout, 0, 2)
        hydraulic_data_output_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.doubleclick_output_group = DoubleClicOutputGroup()
        hydraulic_data_output_group.installEventFilter(self.doubleclick_output_group)
        self.doubleclick_output_group.double_clic_signal.connect(self.reset_hydraulic_data_output_group)

        # models_group
        models_group = QGroupBox(self.tr('Biological models'))
        models_layout = QGridLayout(models_group)
        models_layout.addWidget(available_model_label, 0, 0)
        models_layout.addWidget(selected_model_label, 0, 1)
        models_layout.addWidget(self.list_f, 1, 0)
        models_layout.addWidget(self.selected_aquatic_animal_qtablewidget, 1, 1)
        models_layout.addWidget(button1, 2, 1)
        self.doubleclick_models_group = DoubleClicOutputGroup()
        models_group.installEventFilter(self.doubleclick_models_group)
        self.doubleclick_models_group.double_clic_signal.connect(self.reset_models_group)

        # gereral_layout
        self.layout3 = QVBoxLayout(content_widget)
        self.layout3.addWidget(hydraulic_data_group, Qt.AlignLeft)
        self.layout3.addWidget(hydraulic_data_output_group)
        self.layout3.addWidget(models_group)

        # self.setLayout(self.layout3)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

        # load the data if it exist already
        self.open_estimhab_hdf5()

        # add all fish name from a directory to the QListWidget self.list_f
        self.read_fish_name()

    def add_new_qtarget(self):
        # count existing number of lineedit
        total_widget_number = self.q2target_layout.count()
        self.total_lineedit_number = total_widget_number - 2  # first : qlabel and last : qpushbutton
        setattr(self, 'new_qtarget' + str(total_widget_number - 1), QLineEdit())
        getattr(self, 'new_qtarget' + str(total_widget_number - 1)).setFixedWidth(self.lineedit_width)
        self.target_lineedit_list.append(getattr(self, 'new_qtarget' + str(total_widget_number - 1)))
        self.q2target_layout.insertWidget(total_widget_number - 1, getattr(self, 'new_qtarget' + str(total_widget_number - 1)))
        self.total_lineedit_number = self.total_lineedit_number + 1

    def reset_hydraulic_data_input_group(self):
        print("reset_hydraulic_data_input_group")
        # remove txt in lineedit
        self.eq1.setText("")
        self.eq2.setText("")
        self.ew1.setText("")
        self.ew2.setText("")
        self.eh1.setText("")
        self.eh2.setText("")
        self.eq50.setText("")
        self.esub.setText("")

    def reset_hydraulic_data_output_group(self):
        # remove txt in lineedit
        self.eqmin.setText("")
        self.eqmax.setText("")
        self.eqtarget.setText("")
        # remove lineedits qtarget
        for i in reversed(range(2, self.q2target_layout.count() - 1)):
            self.q2target_layout.itemAt(i).widget().setParent(None)
            self.total_lineedit_number = self.total_lineedit_number - 1
        self.target_lineedit_list = [self.eqtarget]

    def reset_models_group(self):
        if self.selected_aquatic_animal_qtablewidget.count() > 0:
            self.selected_aquatic_animal_qtablewidget.clear()
            self.read_fish_name()

    def read_fish_name(self):
        """
        This function reads all latin fish name from the xml files which are contained in the biological directory
        related to estimhab.
        """

        all_xmlfile = glob.glob(os.path.join(self.path_bio_estimhab, r'*.xml'))

        # get selected fish
        selected_fish = []
        for index in range(self.selected_aquatic_animal_qtablewidget.count()):
            selected_fish.append(self.selected_aquatic_animal_qtablewidget.item(index).text())

        fish_names = []
        xml_file_to_keep = []
        for f in all_xmlfile:
            # open xml
            try:
                try:
                    docxml = ET.parse(f)
                    root = docxml.getroot()
                except IOError:
                    self.send_log.emit("Warning: " + self.tr("The .habby project file ") + f + self.tr(" could not be open.\n"))
                    return
            except ET.ParseError:
                self.send_log.emit("Warning: " + self.tr("The .habby project file ") + f + self.tr(" is not well-formed.\n"))
                return

            # find fish name
            fish_name = root.find(".//LatinName")
            # None is null for python 3
            if fish_name is not None:
                fish_name = fish_name.text.strip()

            # find fish stage
            stage = root.find(".//estimhab/stage")
            # None is null for python 3
            if stage is not None:
                stage = stage.text.strip()
            if stage != 'all_stage':
                fish_name += ' ' + stage

            # check if selected
            if fish_name not in selected_fish:
                # add to the list
                item = QListWidgetItem(fish_name)
                item.setData(1, f)
                self.list_f.addItem(item)

                fish_names.append(fish_name)
                xml_file_to_keep.append(f)
        # remove xml files
        for xml_file in reversed(all_xmlfile):
            if xml_file not in xml_file_to_keep:
                all_xmlfile.remove(xml_file)

        # remember fish name and xml filename
        self.filenames = [fish_names, all_xmlfile]

    def open_estimhab_hdf5(self):
        """
        This function opens the hdf5 data created by estimhab
        """

        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(fname):
            aa = 1
            # parser = ET.XMLParser(remove_blank_text=True)
            # doc = ET.parse(fname, parser)
            # root = doc.getroot()
            # child = root.find(".//ESTIMHAB_data")
            # if child is not None:  # if there is data for ESTIHAB
            #     fname_h5 = child.text
            #     path_hdf5 = self.find_path_hdf5_est()
            #     fname_h5 = os.path.join(path_hdf5, fname_h5)
            #     if os.path.isfile(fname_h5):
            #         # create hdf5
            #         hdf5 = hdf5_mod.Hdf5Management(self.path_prj,
            #                                        fname_h5)
            #         hdf5.load_hdf5_estimhab()
            #
            #         # chosen fish
            #         for i in range(0, len(hdf5.estimhab_dict["fish_list"])):
            #             item = QListWidgetItem(hdf5.estimhab_dict["fish_list"][i])
            #             item.setData(1, hdf5.estimhab_dict["xml_list"][i])
            #             self.selected_aquatic_animal_qtablewidget.addItem(item)
            #
            #         # input data
            #         self.eq1.setText(str(hdf5.estimhab_dict["q"][0]))
            #         self.eq2.setText(str(hdf5.estimhab_dict["q"][1]))
            #         self.eh1.setText(str(hdf5.estimhab_dict["h"][0]))
            #         self.eh2.setText(str(hdf5.estimhab_dict["h"][1]))
            #         self.ew1.setText(str(hdf5.estimhab_dict["w"][0]))
            #         self.ew2.setText(str(hdf5.estimhab_dict["w"][1]))
            #         self.eq50.setText(str(hdf5.estimhab_dict["q50"]))
            #         self.eqmin.setText(str(hdf5.estimhab_dict["qrange"][0]))
            #         self.eqmax.setText(str(hdf5.estimhab_dict["qrange"][1]))
            #         self.esub.setText(str(hdf5.estimhab_dict["substrate"]))
            #         # qtarg
            #         if len(hdf5.estimhab_dict["targ_q_all"]) > 0:
            #             self.eqtarget.setText(str(hdf5.estimhab_dict["targ_q_all"][0]))
            #             while self.total_lineedit_number != len(hdf5.estimhab_dict["targ_q_all"]):
            #                 self.add_new_qtarget()
            #             for qtarg_num, qtarg_value in enumerate(hdf5.estimhab_dict["targ_q_all"][1:]):
            #                 getattr(self, 'new_qtarget' + str(qtarg_num + 2)).setText(str(qtarg_value))

        else:
            self.send_log.emit('Error: ' + self.tr('The hdf5 file related to ESTIMHAB does not exist.'))

    def change_folder(self):
        """
        A small method to change the folder which indicates where is the biological data
        """
        # user find new path
        self.path_bio_estimhab = QFileDialog.getExistingDirectory(self, self.tr("Open Directory"), os.getenv('HOME'))
        # update list
        self.list_f.clear()
        all_file = glob.glob(os.path.join(self.path_bio_estimhab, r'*.xml'))
        # make it look nicer
        for i in range(0, len(all_file)):
            all_file[i] = all_file[i].replace(self.path_bio_estimhab, "")
            all_file[i] = all_file[i].replace("\\", "")
            all_file[i] = all_file[i].replace(".xml", "")
            item = QListWidgetItem(all_file[i])
            # add them to the menu
            self.list_f.addItem(item)

    def run_estmihab(self):
        """
        A function to execute Estimhab by calling the estimhab function.

        **Technical comment**

        This is the function making the link between the GUI and the source code proper. The source code for Estimhab
        is in src/Estimhab.py.

        This function loads in memory the data given in the graphical interface and call sthe Estimhab model.
        The data could be written by the user now or it could be data which was saved in the hdf5 file before and
        loaded when HABBY was open (and the init function called).  We check that all necessary data is present and
        that the data given makes sense (e.g.,the minimum discharge should not be bigger than the maximal discharge,
        the data should be a float, etc.). We then remove the duplicate fish species (in case the user select one
        specie twice) and the Estimhab model is called. The log is then written (see the paragraph on the log for more
        information). Next, the figures created by Estimmhab are shown. As there is only a short number of outputs
        for Estimhab, we create a figure in all cases (it could be changed by adding a checkbox on the GUI like
        in the Telemac or other hydrological class).

        """
        # prepare data
        try:
            q = [float(self.eq1.text().replace(",", ".")), float(self.eq2.text().replace(",", "."))]
            w = [float(self.ew1.text().replace(",", ".")), float(self.ew2.text().replace(",", "."))]
            h = [float(self.eh1.text().replace(",", ".")), float(self.eh2.text().replace(",", "."))]
            q50 = float(self.eq50.text().replace(",", "."))
            qrange = [float(self.eqmin.text().replace(",", ".")), float(self.eqmax.text().replace(",", "."))]
            qtarget_values_list = []
            for qtarg_lineedit in self.target_lineedit_list:
                if qtarg_lineedit.text():
                    qtarget_values_list.append(float(qtarg_lineedit.text().replace(",", ".")))
            substrate = float(self.esub.text().replace(",", "."))
        except ValueError:
            self.send_log.emit('Error: ' + self.tr('Some data are empty or not float. Cannot run Estimhab'))
            return

        # get the list of xml file
        fish_list = []
        fish_name2 = []
        for i in range(0, self.selected_aquatic_animal_qtablewidget.count()):
            fish_item = self.selected_aquatic_animal_qtablewidget.item(i)
            fish_item_str = fish_item.text()
            fish_list.append(os.path.basename(fish_item.data(1)))
            fish_name2.append(fish_item_str)
        # check internal logic
        if not fish_list:
            self.send_log.emit('Error: ' + self.tr('No fish selected. Cannot run Estimhab.'))
            return
        if qrange[0] >= qrange[1]:
            self.send_log.emit('Error: ' + self.tr('Minimum discharge bigger or equal to max discharge. Cannot run Estimhab.'))
            return
        if qtarget_values_list:
            for qtarg in qtarget_values_list:
                if qtarg < qrange[0] or qtarg > qrange[1]:
                    self.send_log.emit(
                        'Error: ' + self.tr('Target discharge is not between Qmin and Qmax. Cannot run Estimhab.'))
                    return
        if q[0] == q[1]:
            self.send_log.emit('Error: ' + self.tr('Estimhab needs two differents measured discharges.'))
            return
        if h[0] == h[1]:
            self.send_log.emit('Error: ' + self.tr('Estimhab needs two different measured height.'))
            return
        if w[0] == w[1]:
            self.send_log.emit('Error: ' + self.tr('Estimhab needs two different measured width.'))
            return
        if (q[0] > q[1] and h[0] < h[1]) or (q[0] > q[1] and w[0] < w[1]) or (q[1] > q[0] and h[1] < h[0]) \
                or (q[1] > q[0] and w[1] < w[0]):
            self.send_log.emit('Error: ' + self.tr('Discharge, width, and height data are not coherent.'))
            return
        if q[0] <= 0 or q[1] <= 0 or w[0] <= 0 or w[1] <= 0 or h[0] <= 0 or h[1] <= 0 or qrange[0] <= 0 or qrange[1] <= 0 \
                or substrate <= 0 or q50 <= 0:
            self.send_log.emit('Error: ' + self.tr('Negative or zero data found. Could not run estimhab.'))
            return
        if substrate > 3:
            self.send_log.emit('Error: ' + self.tr('Substrate is too large. Could not run estimhab.'))
            return

        self.send_log.emit(self.tr('# Computing: ESTIMHAB...'))

        # check if the discharge range is realistic with the result
        self.qall = [q[0], q[1], qrange[0], qrange[1], q50]
        self.check_all_q()

        # run and save
        project_preferences = load_project_properties(self.path_prj)
        sys.stdout = mystdout = StringIO()

        estimhab_dict = dict(q=q,
                             w=w,
                             h=h,
                             q50=q50,
                             qrange=qrange,
                             qtarg=qtarget_values_list,
                             substrate=substrate,
                             path_bio=self.path_bio_estimhab,
                             xml_list=fish_list,
                             fish_list=fish_name2)

        state = Value("i", 0)

        self.p = Process(target=estimhab_mod.estimhab_and_save_hdf5,
                         args=(estimhab_dict, project_preferences, self.path_prj,
                               state))
        self.process_list.append((self.p, state))

        # wait end process
        while state.value != 1:
            pass

        fname_no_path = self.name_prj + '_ESTIMHAB' + '.hab'
        fnamep = os.path.join(self.path_prj, self.name_prj + '.habby')
        parser = ET.XMLParser(remove_blank_text=True)
        doc = ET.parse(fnamep, parser)
        root = doc.getroot()
        tree = ET.ElementTree(root)
        child = root.find(".//ESTIMHAB_data")
        # test if there is already estimhab data in the project
        if child is None:
            child = ET.SubElement(root, "ESTIMHAB_data")
            child.text = fname_no_path
        else:
            child.text = fname_no_path
        tree.write(fnamep, pretty_print=True)

        # log info
        str_found = mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])

        self.send_log.emit(
            self.tr("Estimhab computation done. Figure and text files created."))
        self.send_log.emit("py    data = [" + str(q) + ',' + str(w) + ',' + str(h) + ',' + str(q50) +
                           ',' + str(substrate) + ']')
        self.send_log.emit("py    qrange =[" + str(qrange[0]) + ',' + str(qrange[1]) + ']')
        self.send_log.emit("py    path1= os.path.join(os.path.dirname(path_bio),'" + self.path_bio_estimhab + "')")
        fish_list_str = "py    fish_list = ["
        for i in range(0, len(fish_list)):
            fish_list_str += "'" + fish_list[i] + "',"
        fish_list_str = fish_list_str[:-1] + ']'
        self.send_log.emit(fish_list_str)
        self.send_log.emit("py    [VH, SPU] = estimhab.estimhab(data[0], data[1], data[2], data[3] ,"
                           " qrange, data[4], path1, fish_list, '.', True, {}, '.')\n")
        self.send_log.emit("restart RUN_ESTIMHAB")
        self.send_log.emit("restart    q0: " + str(q[0]))
        self.send_log.emit("restart    q1: " + str(q[1]))
        self.send_log.emit("restart    w0: " + str(w[0]))
        self.send_log.emit("restart    w1: " + str(w[1]))
        self.send_log.emit("restart    h0: " + str(h[0]))
        self.send_log.emit("restart    h1: " + str(h[1]))
        self.send_log.emit("restart    q50: " + str(q50))
        self.send_log.emit("restart    sub: " + str(substrate))
        self.send_log.emit("restart    min qrange: " + str(qrange[0]))
        self.send_log.emit("restart    max qrange: " + str(qrange[1]))


if __name__ == '__main__':
    pass
