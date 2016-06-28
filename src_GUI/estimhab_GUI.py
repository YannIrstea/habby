
import os
from src import estimhab
import glob
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from PyQt5.QtCore import QTranslator, pyqtSignal, QSettings
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QAbstractItemView, QMessageBox
import h5py
import sys
from io import StringIO

class EstimhabW(QWidget):
    """
    A class to load the widget controlling the ESTIMHAB model
    """

    save_signal_estimhab = pyqtSignal()
    send_log = pyqtSignal(str, name='send_log')
    show_fig = pyqtSignal()

    def __init__(self, path_prj, name_prj):

        self.path_bio = './/biologie'
        self.eq1 = QLineEdit()
        self.ew1 = QLineEdit()
        self.eh1 = QLineEdit()
        self.eq2 = QLineEdit()
        self.ew2 = QLineEdit()
        self.eh2 = QLineEdit()
        self.eqmin = QLineEdit()
        self.eqmax = QLineEdit()
        self.eq50 = QLineEdit()
        self.esub = QLineEdit()
        self.list_f = QListWidget()
        self.list_s = QListWidget()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.VH = []
        self.SPU = []
        self.msge = QMessageBox()
        self.fish_selected = []

        super().__init__()
        self.init_iu()

    def init_iu(self):

        # load the data if it exist already
        fname = os.path.join(self.path_prj, self.name_prj+'.xml')
        if os.path.isfile(fname):
            doc = ET.parse(fname)
            root = doc.getroot()
            child = root.find(".//ESTIMHAB_data")
            if child is not None: # if there is data for ESTIHAB
                fname_h5 = child.text
                fname_h5 = os.path.join(self.path_prj, fname_h5)
                if os.path.isfile(fname_h5):
                    file_estimhab = h5py.File(fname_h5,'r+')
                    # hydrological data
                    dataset_name = ['qmes', 'hmes', 'wmes', 'q50', 'qrange', 'substrate']
                    list_qline = [self.eq1,self.eq2,self.eh1,self.eh2,self.ew1,self.ew2,self.eq50, self.eqmin, self.eqmax, self.esub]
                    c = 0
                    for i in range(0, len(dataset_name)):
                        dataset = file_estimhab[dataset_name[i]]
                        dataset = list(dataset.values())[0]
                        for j in range(0, len(dataset)):
                            data_str = str(dataset[j])
                            list_qline[c].setText(data_str[1:-1])  # get rid of []
                            c += 1
                    # chosen fish
                    dataset = file_estimhab['fish_type']
                    dataset = list(dataset.values())[0]
                    for i in range(0,len(dataset)):
                        dataset_i = str(dataset[i])
                        self.list_s.addItem(dataset_i[3:-2])
                        self.fish_selected.append(dataset_i[3:-2])

                    file_estimhab.close()
                else:
                    self.msge.setIcon(QMessageBox.Warning)
                    self.msge.setWindowTitle(self.tr("hdf5 ESTIMHAB"))
                    self.msge.setText(self.tr("The hdf5 file related to ESTIMHAB does not exist"))
                    self.msge.setStandardButtons(QMessageBox.Ok)
                    self.msge.show()

        # Data hydrological
        l1 = QLabel(self.tr('<b>Hydrological Data</b>'))
        l2 = QLabel(self.tr('Q [m3/sec]'))
        l3 = QLabel(self.tr('Width [m]'))
        l4 = QLabel(self.tr('Height [m]'))
        l5 = QLabel(self.tr('<b>Median discharge Q50 [m3/sec]</b>'))
        l6 = QLabel(self.tr('<b> Mean substrate size [m] </b>'))
        l7 = QLabel(self.tr('<b> Discharge range </b>'))
        l8 = QLabel(self.tr('Qmin and Qmax [m3/sec]'))
        # data fish type
        l10 = QLabel(self.tr('<b>Available Fish and Guild </b>'))
        l11 = QLabel(self.tr('Selected Fish'))
        # create lists with the possible fishes

        self.list_f.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_f.itemClicked.connect(self.add_fish)

        self.list_s.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_s.itemClicked.connect(self.remove_fish)
        # add  all test file in a directory
        all_file = glob.glob(os.path.join(self.path_bio,r'*.xml'))
        # make them look nicer
        for i in range(0, len(all_file)):
            all_file[i] = all_file[i].replace(self.path_bio, "")
            all_file[i] = all_file[i].replace("\\", "")
            all_file[i] = all_file[i].replace(".xml", "")
            # add the list
            item = QListWidgetItem(all_file[i])
            self.list_f.addItem(item)

        # send model
        button1 = QPushButton(self.tr('Save and Run ESTIMHAB'), self)
        button1.setStyleSheet("background-color: darkCyan")
        button1.clicked.connect(self.save_signal_estimhab.emit)
        button1.clicked.connect(self.run_estmihab)
        button2 = QPushButton(self.tr('Change folder (fish data)'), self)
        button2.clicked.connect(self.change_folder)
        button3 = QPushButton(self.tr('Save Data'), self)
        button3.clicked.connect(self.save_signal_estimhab.emit)
        self.layout3 = QGridLayout()
        self.layout3.addWidget(l1, 0, 0)
        self.layout3.addWidget(l2, 1, 0)
        self.layout3.addWidget(l3, 1, 1)
        self.layout3.addWidget(l4, 1, 2)
        self.layout3.addWidget(self.eq1, 2, 0)
        self.layout3.addWidget(self.ew1, 2, 1)
        self.layout3.addWidget(self.eh1, 2, 2)
        self.layout3.addWidget(self.eq2, 3, 0)
        self.layout3.addWidget(self.ew2, 3, 1)
        self.layout3.addWidget(self.eh2, 3, 2)
        self.layout3.addWidget(l5, 4, 0)
        self.layout3.addWidget(self.eq50, 5, 0)
        self.layout3.addWidget(l6, 4, 1)
        self.layout3.addWidget(self.esub, 5, 1)
        self.layout3.addWidget(l7, 6, 0)
        self.layout3.addWidget(self.eqmin, 7, 0)
        self.layout3.addWidget(self.eqmax, 7, 1)
        self.layout3.addWidget(l8, 7, 2)
        self.layout3.addWidget(l10, 8, 0)
        self.layout3.addWidget(l11, 8, 1)
        self.layout3.addWidget(self.list_f, 9, 0)
        self.layout3.addWidget(self.list_s, 9, 1)
        self.layout3.addWidget(button1, 10, 2)
        self.layout3.addWidget(button3, 10, 1)
        self.layout3.addWidget(button2, 10, 0)
        self.setLayout(self.layout3)

    def change_folder(self):
        """
        a small method to change the folder where is the biological data
        :return: None
        """
        # user find new path
        self.path_bio = QFileDialog.getExistingDirectory()
        # update list
        self.list_f.clear()
        all_file = glob.glob(os.path.join(self.path_bio,r'*.xml'))
        # make it look nicer
        for i in range(0, len(all_file)):
            all_file[i] = all_file[i].replace(self.path_bio, "")
            all_file[i] = all_file[i].replace("\\", "")
            all_file[i] = all_file[i].replace(".xml", "")
            item = QListWidgetItem(all_file[i])
            # add them to the menu
            self.list_f.addItem(item)

    def run_estmihab(self):
        """
        A function to execute estimhab
        :return: None
        """
        # prepare data
        try:
            q = [float(self.eq1.text()), float(self.eq2.text())]
            w = [float(self.ew1.text()), float(self.ew2.text())]
            h = [float(self.eh1.text()), float(self.eh2.text())]
            q50 = float(self.eq50.text())
            qrange = [float(self.eqmin.text()), float(self.eqmax.text())]
            substrate = float(self.esub.text())
        except ValueError:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Some data are empty or not float. Cannot run Estimhab"))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        fish_list = []
        for i in range(0, self.list_s.count()):
            fish_item = self.list_s.item(i)
            fish_item_str = fish_item.text()
            fish_list.append(fish_item_str)

        # check internal logic
        if not fish_list:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("No fish selected. Cannot run Estimhab."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if qrange[0] >= qrange[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Minimum dicharge bigger or equal to max discharge. Cannot run Estimhab."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if q[0] == q[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Estimhab needs two different measured discharge."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if h[0] == h[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Estimhab needs two different measured height."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        if w[0] == w[1]:
            self.msge.setIcon(QMessageBox.Warning)
            self.msge.setWindowTitle(self.tr("run ESTIMHAB"))
            self.msge.setText(self.tr("Estimhab needs two different measured width."))
            self.msge.setStandardButtons(QMessageBox.Ok)
            self.msge.show()
            return
        fish_list = list(set(fish_list))  # it will remove duplicate, but change the list order!
        # run
        path_im = self.find_path_im_est()
        sys.stdout = mystdout = StringIO()
        [self.VH, self.SPU] = estimhab.estimhab(q, w, h, q50, qrange, substrate, self.path_bio, fish_list, path_im, True)

        #log info
        self.send_log.emit(self.tr('# Run: Estimhab'))
        str_found = mystdout.getvalue()
        str_found = str_found.split('\n')
        for i in range(0, len(str_found)):
            if len(str_found[i]) > 1:
                self.send_log.emit(str_found[i])
        self.send_log.emit("py    data = [" + str(q) + ',' + str(w) + ',' +str(h) + ',' + str(q50) +
                           ',' + str(substrate) + ']')
        self.send_log.emit("py    qrange =[" + str(qrange[0]) + ',' + str(qrange[1]) + ']' )
        self.send_log.emit("py    path1='" + self.path_bio + "'")
        fish_list_str = "py    fish_list = ["
        for i in range(0,len(fish_list)):
            fish_list_str += "'" + fish_list[i] + "',"
        fish_list_str = fish_list_str[:-1] + ']'
        self.send_log.emit(fish_list_str)
        self.send_log.emit("py    [VH, SPU] = estimhab.estimhab(data[0], data[1], data[2], data[3] ,"
                           " qrange, data[4], path1, fish_list, '.', True)\n")
        self.send_log.emit("restart Run_Estimab")
        self.send_log.emit("restart    data: " + str(q) + ',' + str(w) + ',' + str(h) + ',' + str(q50) +
                           ',' + str(substrate)+ str(qrange[0]) + ',' + str(qrange[1]))
        self.send_log.emit("restart    fish: " + fish_list_str)

        # we always do a figure for estmihab
        self.show_fig.emit()

    def add_fish(self):
        items = self.list_f.selectedItems()
        if items:
            for i in range(0,len(items)):
                # avoid to have the same fish multiple times
                if items[i].text() in self.fish_selected:
                    pass
                else:
                    self.list_s.addItem(items[i].text())
                    self.fish_selected.append(items[i].text())

    def remove_fish(self):
        item = self.list_s.takeItem(self.list_s.currentRow())
        self.fish_selected.remove(item.text())
        item = None

    def find_path_im_est(self):
        """
        A function to find the path where to save the figues, careful a simialr one is in hydro_GUI_2
        :return: path_im
        """
        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.xml')
        if os.path.isfile(filename_path_pro):
            doc = ET.parse(filename_path_pro)
            root = doc.getroot()
            child = root.find(".//Path_Figure")
            if child is None:
                path_im = os.path.join(self.path_prj, 'figures_habby')
            else:
                path_im = child.text
        else:
            self.msg2.setIcon(QMessageBox.Warning)
            self.msg2.setWindowTitle(self.tr("Save Hydrological Data"))
            self.msg2.setText( \
                self.tr("The project is not saved. Save the project in the General tab before saving data."))
            self.msg2.setStandardButtons(QMessageBox.Ok)
            self.msg2.show()
            return
        return path_im