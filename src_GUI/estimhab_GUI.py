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
import glob
from lxml import etree as ET
from PyQt5.QtCore import pyqtSignal, Qt, QCoreApplication
from PyQt5.QtWidgets import QPushButton, QLabel, QGridLayout, QHBoxLayout, QVBoxLayout,  \
    QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QSpacerItem, QGroupBox, QSizePolicy, \
    QAbstractItemView, QMessageBox, QScrollArea, QFrame, QRadioButton
from PyQt5.QtGui import QFont, QPixmap
from multiprocessing import Process
import sys
from io import StringIO

from src_GUI.dev_tools_GUI import DoubleClicOutputGroup, change_button_color
from src.process_manager_mod import MyProcessManager
from src.project_properties_mod import load_project_properties, change_specific_properties, load_specific_properties
from src.dev_tools_mod import isstranumber
from src.tools_mod import read_chronicle_from_text_file
from src.estimhab_mod import estimhab_process, read_fishname


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
        super().__init__()
        self.lineedit_width = 50
        self.path_bio = 'biology'
        self.eq1 = QLineEdit()
        self.ew1 = QLineEdit()
        self.eh1 = QLineEdit()
        self.eq2 = QLineEdit()
        self.ew2 = QLineEdit()
        self.eh2 = QLineEdit()
        self.eqmin = QLineEdit()
        self.eqmax = QLineEdit()
        self.eqby = QLineEdit()
        self.list_f = QListWidget()
        self.selected_aquatic_animal_qtablewidget = QListWidget()
        self.chro_file_path = ""
        self.msge = QMessageBox()
        self.fish_selected = []
        self.qall = []  # q1 q2 qmin qmax q50. Value cannot be added directly because of stathab.

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
        A function to find the path where to save the figues. Careful there is similar function in sub_and_merge_GUI.py.
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
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_im

    def find_path_hdf5_est(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in sub_and_merge_GUI.py and in
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
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_hdf5

    def find_path_text_est(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in estimhab_GUI.py. By default,
        path_hdf5 is in the project folder in the folder 'hdf5'.
        """

        # filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        # if os.path.isfile(filename_path_pro):
        #     parser = ET.XMLParser(remove_blank_text=True)
        #     doc = ET.parse(filename_path_pro, parser)
        #     root = doc.getroot()
        #     child = root.find(".//path_text")
        #     if child is None:
        #         path_text = os.path.join(self.path_prj, r'/output/text')
        #     else:
        #         path_text = os.path.join(self.path_prj, child.text)
        # else:
        #     self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return os.path.join(self.path_prj, "output", "text")

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
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))

        return path_out

    def find_path_input_est(self):
        """
        A function to find the path where to save the input file. Careful a similar one is in sub_and_merge_GUI.py. By default,
        path_input indicates the folder 'input' in the project folder.
        """

        # path_input = 'no_path'
        #
        # filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        # if os.path.isfile(filename_path_pro):
        #     parser = ET.XMLParser(remove_blank_text=True)
        #     doc = ET.parse(filename_path_pro, parser)
        #     root = doc.getroot()
        #     child = root.find(".//path_input")
        #     if child is None:
        #         path_input = os.path.join(self.path_prj, r'/input')
        #     else:
        #         path_input = os.path.join(self.path_prj, child.text)
        # else:
        #     self.send_log.emit('Warning: ' + QCoreApplication.translate("StatModUseful", "The project is not saved. Save the project in the General tab."))
        project_properties = load_project_properties(self.path_prj)
        path_input = project_properties['path_input']

        return path_input

    def send_err_log(self):
        """
        This function sends the errors and the warnings to the logs.
        The stdout was redirected to self.mystdout before calling this function. It only sends the hundred first errors
        to avoid freezing the GUI. A similar function exists in sub_and_merge_GUI.py. Correct both if necessary.
        """
        max_send = 400
        if self.mystdout is not None:
            str_found = self.mystdout.getvalue()
        else:
            return
        str_found = str_found.split('\n')
        for i in range(0, min(len(str_found), max_send)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
            if i == max_send - 1:
                self.send_log.emit(self.fr('Warning: ') + self.tr('Too many information for the GUI.'))

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
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", 'Measured discharges are not very different. The results might '
                               'not be realistic. \n'))
        if (self.qall[4] < q1 / 10 or self.qall[4] > 5 * q2) and self.qall[4] != -99:  # q50 not always necessary
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", 'Q50 should be between q1/10 and 5*q2 for optimum results.'))
        if self.qall[2] < q1 / 10 or self.qall[2] > 5 * q2:
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", 'Discharge range should be between q1/10 and 5*q2 for optimum results (1).'))
        if self.qall[3] < q1 / 10 or self.qall[3] > 5 * q2:
            self.send_log.emit(QCoreApplication.translate("StatModUseful", 'Warning: ') + QCoreApplication.translate("StatModUseful", 'Discharge range should be between q1/10 and 5*q2 for optimum results (2).'))


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
        self.tab_position = 7
        self.model_type = "Estimhab"
        self.eq50 = QLineEdit()
        self.esub = QLineEdit()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_bio_estimhab = os.path.join(self.path_bio, 'estimhab')
        self.path_last_file_loaded = self.path_prj
        self.total_lineedit_number = 1
        self.init_iu()
        self.process_manager = MyProcessManager("estimhab_plot")
        self.read_estimhab_dict()
        self.fill_input_data()
        self.fill_fish_name()
        self.check_if_ready_to_compute()
        self.eq1.textChanged.connect(self.check_if_ready_to_compute)
        self.eq2.textChanged.connect(self.check_if_ready_to_compute)
        self.ew1.textChanged.connect(self.check_if_ready_to_compute)
        self.ew2.textChanged.connect(self.check_if_ready_to_compute)
        self.eh1.textChanged.connect(self.check_if_ready_to_compute)
        self.eh2.textChanged.connect(self.check_if_ready_to_compute)
        self.eq50.textChanged.connect(self.check_if_ready_to_compute)
        self.eqmin.textChanged.connect(self.check_if_ready_to_compute)
        self.eqmax.textChanged.connect(self.check_if_ready_to_compute)
        self.eqby.textChanged.connect(self.check_if_ready_to_compute)
        self.esub.textChanged.connect(self.check_if_ready_to_compute)
        self.selected_aquatic_animal_qtablewidget.model().rowsInserted.connect(self.check_if_ready_to_compute)
        self.selected_aquatic_animal_qtablewidget.model().rowsRemoved.connect(self.check_if_ready_to_compute)

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
        self.arrow = QLabel()
        self.arrow.setPixmap(
            QPixmap(os.path.join(os.getcwd(), "file_dep", "icon", "triangle_black_closed_50_50.png")).copy(20, 0, 16,
                                                                                                           50))
        selected_model_label = QLabel(self.tr('Selected'))

        self.spacer_width = 20

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
        self.eqmin.setFixedWidth(self.lineedit_width)
        self.eqmax.setFixedWidth(self.lineedit_width)
        self.eqby.setFixedWidth(self.lineedit_width)
        self.fromseq_group = QGroupBox()
        fromseq_layout = QHBoxLayout(self.fromseq_group)
        fromseq_layout.addWidget(QLabel(self.tr("Qmin")))
        fromseq_layout.addWidget(self.eqmin)
        fromseq_layout.addItem(QSpacerItem(self.spacer_width, 1))
        fromseq_layout.addWidget(QLabel(self.tr("Qmax")))
        fromseq_layout.addWidget(self.eqmax)
        fromseq_layout.addItem(QSpacerItem(self.spacer_width, 1))
        fromseq_layout.addWidget(QLabel(self.tr("Qby")))
        fromseq_layout.addWidget(self.eqby)
        fromseq_layout.addWidget(QLabel(self.tr("[m<sup>3</sup>/s]")))
        
        self.fromtxt_group = QGroupBox()
        fromtxt_layout = QHBoxLayout(self.fromtxt_group)
        fromtxt_layout.addWidget(QLabel(self.tr("Choose file")))
        self.fromtxt_lineedit = QLineEdit("")
        self.fromtxt_lineedit.setEnabled(False)
        self.fromtxt_lineedit.textChanged.connect(self.check_if_ready_to_compute)
        fromtxt_layout.addWidget(self.fromtxt_lineedit)
        self.chro_file_pushbutton = QPushButton("...")
        self.chro_file_pushbutton.clicked.connect(self.choose_chro_file)
        self.chro_file_pushbutton.setFixedWidth(self.spacer_width)
        fromtxt_layout.addWidget(self.chro_file_pushbutton)

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
        self.show_button = QPushButton(self.tr('Show Estimhab output'), self)
        self.show_button.clicked.connect(lambda: self.export_estmihab(True))
        change_button_color(self.show_button, "#47B5E6")
        self.show_button.setEnabled(False)
        self.export_button = QPushButton(self.tr('Export Estimhab output'), self)
        self.export_button.clicked.connect(lambda: self.export_estmihab(False))
        change_button_color(self.export_button, "#47B5E6")
        self.export_button.setEnabled(False)

        # empty frame scrolable
        content_widget = QFrame()

        # hydraulic_data_group
        hydraulic_data_group = QGroupBox(self.tr('Hydraulic data input'))
        hydraulic_data_group.setToolTip(self.tr("Double click to reset the input data group."))
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

        # models_group
        models_group = QGroupBox(self.tr('Biological models'))
        models_layout = QGridLayout(models_group)
        models_layout.addWidget(available_model_label, 0, 0, Qt.AlignRight)
        models_layout.addWidget(selected_model_label, 0, 2)
        models_layout.addWidget(self.list_f, 1, 0)
        models_layout.addWidget(self.arrow, 1, 1)
        models_layout.addWidget(self.selected_aquatic_animal_qtablewidget, 1, 2)
        self.doubleclick_models_group = DoubleClicOutputGroup()
        models_group.installEventFilter(self.doubleclick_models_group)
        self.doubleclick_models_group.double_clic_signal.connect(self.reset_models_group)

        # hydraulic_data_output_group
        hydraulic_data_output_group = QGroupBox(self.tr('Desired output data'))
        hydraulic_data_layout = QGridLayout(hydraulic_data_output_group)

        self.fromseq_radiobutton = QRadioButton(self.tr("from a sequence"))
        self.fromseq_radiobutton.setChecked(True)
        self.fromseq_radiobutton.clicked.connect(self.out_type_change)
        self.fromseq_radiobutton.clicked.connect(self.check_if_ready_to_compute)
        self.fromtxt_radiobutton = QRadioButton(self.tr("from .txt file"))
        self.fromtxt_radiobutton.clicked.connect(self.out_type_change)
        self.fromtxt_radiobutton.clicked.connect(self.check_if_ready_to_compute)
        hydraulic_data_layout.addWidget(self.fromseq_radiobutton, 0, 0)
        hydraulic_data_layout.addWidget(self.fromtxt_radiobutton, 0, 1)
        hydraulic_data_layout.addWidget(self.fromseq_group, 1, 0)
        hydraulic_data_layout.addWidget(self.fromtxt_group, 1, 1)
        comput_button_layout = QHBoxLayout()
        comput_button_layout.addWidget(self.show_button)
        comput_button_layout.addItem(QSpacerItem(self.spacer_width, 1))
        comput_button_layout.addWidget(self.export_button)
        comput_button_layout.addStretch()
        hydraulic_data_layout.addLayout(comput_button_layout, 2, 0)
        self.fromseq_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.doubleclick_output_group = DoubleClicOutputGroup()
        self.fromseq_group.setToolTip(self.tr("Double click to reset the outpout data group."))
        self.fromseq_group.installEventFilter(self.doubleclick_output_group)
        self.doubleclick_output_group.double_clic_signal.connect(self.reset_hydraulic_data_output_group)
        self.out_type_change()

        # gereral_layout
        self.layout3 = QVBoxLayout(content_widget)
        self.layout3.addWidget(hydraulic_data_group, Qt.AlignLeft)
        self.layout3.addWidget(models_group)
        self.layout3.addWidget(hydraulic_data_output_group)
        # self.setLayout(self.layout3)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setWidget(content_widget)

    def out_type_change(self):
        if self.fromseq_radiobutton.isChecked():
            self.fromseq_group.setEnabled(True)
            self.fromtxt_group.setEnabled(False)
        if self.fromtxt_radiobutton.isChecked():
            self.fromseq_group.setEnabled(False)
            self.fromtxt_group.setEnabled(True)

    def reset_hydraulic_data_input_group(self):
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
        self.eqby.setText("")

    def reset_models_group(self):
        if self.selected_aquatic_animal_qtablewidget.count() > 0:
            self.selected_aquatic_animal_qtablewidget.clear()
            self.fill_fish_name(True)

    def read_estimhab_dict(self):
        """
        This function opens the json data created by estimhab
        """
        # load_project_properties
        self.estimhab_dict = load_specific_properties(self.path_prj,
                                                      [self.model_type])[0]

    def fill_fish_name(self, reset=False):
        """
        This function reads all latin fish name from the xml files which are contained in the biological directory
        related to estimhab and fill GUI fish names
        """
        all_xmlfile = glob.glob(os.path.join(self.path_bio_estimhab, r'*.xml'))
        selected_fish = []
        if not reset:
            if self.estimhab_dict:
                selected_fish = self.estimhab_dict["xml_list"]

        fish_names = read_fishname(all_xmlfile)
        for fish_ind, fish_xml in enumerate(all_xmlfile):
            # check if not selected
            if fish_xml not in selected_fish:
                # add to the list
                item = QListWidgetItem(fish_names[fish_ind])
                item.setData(1, all_xmlfile[fish_ind])
                self.list_f.addItem(item)
            else:
                # add to the list
                item2 = QListWidgetItem(fish_names[fish_ind])
                item2.setData(1, all_xmlfile[fish_ind])
                self.selected_aquatic_animal_qtablewidget.addItem(item2)

    def fill_input_data(self):
        if self.estimhab_dict:
            # input data
            self.eq1.setText(str(self.estimhab_dict["q"][0]))
            self.eq2.setText(str(self.estimhab_dict["q"][1]))
            self.eh1.setText(str(self.estimhab_dict["h"][0]))
            self.eh2.setText(str(self.estimhab_dict["h"][1]))
            self.ew1.setText(str(self.estimhab_dict["w"][0]))
            self.ew2.setText(str(self.estimhab_dict["w"][1]))
            self.eq50.setText(str(self.estimhab_dict["q50"]))
            if type(self.estimhab_dict["qrange"]) == str:
                self.fromtxt_lineedit.setText(self.estimhab_dict["qrange"])
                self.fromtxt_radiobutton.setChecked(True)
                self.chro_file_path = self.estimhab_dict["qrange"]
            else:
                self.fromseq_radiobutton.setChecked(True)
                self.eqmin.setText(str(self.estimhab_dict["qrange"][0]))
                self.eqmax.setText(str(self.estimhab_dict["qrange"][1]))
                self.eqby.setText(str(self.estimhab_dict["qrange"][2]))
            self.esub.setText(str(self.estimhab_dict["substrate"]))
            self.out_type_change()

    def check_if_ready_to_compute(self):
        self.export_button.setEnabled(False)
        self.show_button.setEnabled(False)
        all_string_selection = (self.eq1.text(),
                                self.eq2.text(),
                                self.ew1.text(),
                                self.ew2.text(),
                                self.eh1.text(),
                                self.eh2.text(),
                                self.eq50.text(),
                                self.esub.text())
        # minimum one fish and string in input lineedits to enable run_stop_button
        if self.selected_aquatic_animal_qtablewidget.count() > 0 and "" not in all_string_selection:
            # output
            if self.fromseq_radiobutton.isChecked():
                if self.eqmin.text() and self.eqmax.text() and self.eqby.text():
                    self.export_button.setEnabled(True)
                    self.show_button.setEnabled(True)
            elif self.fromtxt_radiobutton.isChecked():
                if self.fromtxt_lineedit.text():
                    self.export_button.setEnabled(True)
                    self.show_button.setEnabled(True)

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

    def choose_chro_file(self):
        self.chro_file_path = ""
        project_properties = load_project_properties(self.path_prj)
        if "Estimhab" in project_properties.keys():
            if "qrange" in project_properties["Estimhab"].keys():
                qrange = project_properties["Estimhab"]["qrange"]
                if type(qrange) == str:  # chronicle
                    if os.path.exists(qrange):
                        self.chro_file_path = qrange

        # find the filename based on user choice
        filename_path = QFileDialog.getOpenFileName(self,
                                                    self.tr("Select file"),
                                                    self.chro_file_path,
                                                    "File (*.txt)")[0]

        # exeption: you should be able to clik on "cancel"
        if filename_path:
            self.path_last_file_loaded = os.path.dirname(filename_path)
            chronicle_from_file, types_from_file = read_chronicle_from_text_file(filename_path)

            if not chronicle_from_file:
                self.send_log.emit(types_from_file)
            else:
                self.chro_file_path = filename_path
                self.fromtxt_lineedit.setText(filename_path)
        else:
            self.send_log.emit(self.tr("Warning: Please specify a file."))

    def export_estmihab(self, show):
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
            substrate = float(self.esub.text().replace(",", "."))
            if self.fromtxt_radiobutton.isChecked():
                qrange = self.chro_file_path
            else:
                qrange = [float(self.eqmin.text().replace(",", ".")),
                          float(self.eqmax.text().replace(",", ".")),
                          float(self.eqby.text().replace(",", "."))]
        except ValueError:
            self.send_log.emit('Error: ' + self.tr('Some data are empty or not float. Cannot run Estimhab'))
            return

        # get the list of xml file
        xml_list = []
        for i in range(0, self.selected_aquatic_animal_qtablewidget.count()):
            fish_item = self.selected_aquatic_animal_qtablewidget.item(i)
            fish_item_str = fish_item.text()
            xml_list.append(fish_item.data(1))
        # input
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
        if q[0] <= 0 or q[1] <= 0 or w[0] <= 0 or w[1] <= 0 or h[0] <= 0 or h[1] <= 0 or substrate <= 0 or q50 <= 0:
            self.send_log.emit('Error: ' + self.tr('Negative or zero data found. Could not run Estimhab.'))
            return
        if substrate > 3:
            self.send_log.emit('Error: ' + self.tr('Substrate is too large. Could not run Estimhab.'))
            return
        # output
        if not xml_list:
            self.send_log.emit('Error: ' + self.tr('No fish selected. Cannot run Estimhab.'))
            return
        if type(qrange) != str:  # seq
            if qrange[0] == "" or qrange[1] == "" or qrange[2] == "":
                self.send_log.emit('Error: ' + self.tr('The sequence values must be specified (from, to and by).'))
                return
            if not isstranumber(qrange[0]) or not isstranumber(qrange[1]) or not isstranumber(qrange[2]):
                self.send_log.emit('Error: ' + self.tr('The sequence values must be of numerical type.'))
                return
            if qrange[0] >= qrange[1]:
                self.send_log.emit('Error: ' + self.tr('Minimum discharge bigger or equal to max discharge. Cannot run Estimhab.'))
                return
            if not float(qrange[0]) > 0:
                self.send_log.emit('Error: ' + self.tr('From sequence value must be strictly greater than 0.'))
                return
            if not float(qrange[1]) > 0:
                self.send_log.emit('Error: ' + self.tr('To sequence value must be strictly greater than 0.'))
                return
            if not float(qrange[2]) > 0:
                self.send_log.emit('Error: ' + self.tr('By sequence value must be strictly greater than 0.'))
                return
            # check if the discharge range is realistic with the result
            self.qall = [q[0], q[1], qrange[0], qrange[1], q50]
            self.check_all_q()
        else:  # chro
            pass

        self.send_log.emit(self.tr('# Computing: Estimhab...'))

        # run and save
        sys.stdout = mystdout = StringIO()

        self.estimhab_dict = dict(q=q,
                             w=w,
                             h=h,
                             q50=q50,
                             qrange=qrange,
                             substrate=substrate,
                             path_bio=self.path_bio_estimhab,
                             xml_list=xml_list)

        # change_specific_properties
        change_specific_properties(self.path_prj,
                                   ["Estimhab"],
                                   [self.estimhab_dict])

        project_properties = load_project_properties(self.path_prj)

        # compute
        p = Process(target=estimhab_process,
                         args=(project_properties, True, None), name="Estimhab")
        p.start()
        p.join()

        # show
        if show:
            # plot
            plot_attr = lambda: None
            plot_attr.nb_plot = 1
            self.process_manager.set_estimhab_plot_mode(self.path_prj,
                                                        plot_attr,
                                                        project_properties)
            self.process_manager.start()

        # log info
        str_found = mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
        if show:
            self.send_log.emit(
                self.tr("Estimhab computation done. Figure and text files created in output project folder."))
        else:
            self.send_log.emit(
                self.tr("Estimhab computation done. Text files created in output project folder."))
        self.send_log.emit("py    data = [" + str(q) + ',' + str(w) + ',' + str(h) + ',' + str(q50) +
                           ',' + str(substrate) + ']')
        # self.send_log.emit("py    qrange =[" + str(qrange[0]) + ',' + str(qrange[1]) + ']')
        self.send_log.emit("py    path1= os.path.join(os.path.dirname(path_bio),'" + self.path_bio_estimhab + "')")
        fish_list_str = "py    fish_list = ["
        for i in range(0, len(xml_list)):
            fish_list_str += "'" + xml_list[i] + "',"
        fish_list_str = fish_list_str[:-1] + ']'
        self.send_log.emit(fish_list_str)
        self.send_log.emit("py    [OSI, WUA] = estimhab.estimhab(data[0], data[1], data[2], data[3] ,"
                           " qrange, data[4], path1, fish_list, '.', True, {}, '.')\n")
        # self.send_log.emit("restart RUN_ESTIMHAB")
        # self.send_log.emit("restart    q0: " + str(q[0]))
        # self.send_log.emit("restart    q1: " + str(q[1]))
        # self.send_log.emit("restart    w0: " + str(w[0]))
        # self.send_log.emit("restart    w1: " + str(w[1]))
        # self.send_log.emit("restart    h0: " + str(h[0]))
        # self.send_log.emit("restart    h1: " + str(h[1]))
        # self.send_log.emit("restart    q50: " + str(q50))
        # self.send_log.emit("restart    sub: " + str(substrate))
        # self.send_log.emit("restart    min qrange: " + str(qrange[0]))
        # self.send_log.emit("restart    max qrange: " + str(qrange[1]))


if __name__ == '__main__':
    pass
