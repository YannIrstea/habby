from PyQt5.QtCore import QTranslator, pyqtSignal, QThread, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox
from PyQt5.QtGui import QPixmap, QFont
import os


class BioInfo(QWidget):
    """
    This class contains the tab with the biological information (the curves of preference)
    """

    send_log = pyqtSignal(str, name='send_log')
    """
    A Pyqtsignal to write the log.
    """

    def __init__(self, path_prj, name_prj):
        super().__init__()
        self.path_prj = path_prj
        self.name_prj = name_prj
        self.path_bio = './biology'
        self.imfish = os.path.join(self.path_bio, 'BAM.png')


        self.init_iu()

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        # the available marged data
        l0 = QLabel(self.tr('<b> Substrate and hydraulic data </b>'))
        self.m_all = QComboBox()

        # fish selected
        l1 = QLabel(self.tr('<b> Available Fish and Guild </b>'))
        l2 = QLabel(self.tr('<b> Selected Fish and Guild </b>'))
        self.list_f = QListWidget()
        self.list_s = QListWidget()
        self.bs = QPushButton(self.tr('Select'))
        self.bsel = QPushButton(self.tr('Save selected curves'))
        self.runhab = QPushButton(self.tr('Compute Habitat Value'))
        self.runhab.setStyleSheet("background-color: #31D656")
        spacer1 = QSpacerItem(1, 50)
        spacer2 = QSpacerItem(200, 1)

        # info on pref
        l4 = QLabel(self.tr('<b> Information on the suitability curve</b>'))
        l5 = QLabel(self.tr('Latin Name: '))
        self.com_name = QLabel('Barbus meridionalis')
        l7 = QLabel(self.tr('ONEMA fish code: '))
        self.fish_code = QLabel('BAM')
        l8 = QLabel(self.tr('Description:'))
        self.descr = QLabel(self.tr('kdsadkasdlksa;dlkas;dlksa ;dkas;dlska;dska ;dlaskd;laskd;asldkasl;dksa;dlsadkas;ldska;dl'
                                    'dksa;dlksa;dkasd;lksad; laskdlaskd;askdalsdka;lsdkals ;dk;asldka;sldka;dka;ldkweproiweporiw'
                                   ))
        self.descr.setWordWrap(True)
        self.descr.setMaximumSize(300,100)
        self.pref_curve = QPushButton(self.tr('Show suitability curve'))

        # image fish
        self.pic = QLabel()
        # use full ABSOLUTE path to the image, not relative
        self.pic.setPixmap(QPixmap(os.path.join(os.getcwd(), self.imfish)).scaled(200,70, Qt.KeepAspectRatio))  # 800 500

        # hydrosignature
        l9 = QLabel(self.tr('<b> Hydrological conditions of the measurement </b>'))
        l10 = QLabel(self.tr('(HydroSignature)'))
        self.pichs = QLabel()
        # use full ABSOLUTE path to the image, not relative
        self.pichs.setPixmap(
            QPixmap(os.path.join(os.getcwd(), 'test_hs.png')).scaled(250,250, Qt.KeepAspectRatio))  # 800 500

        # search possibility
        l3 = QLabel(self.tr('<b> Search biological models </b>'))
        self.keys = QComboBox()
        l02 = QLabel('is equal to')
        self.cond1 = QLineEdit()

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
        self.layout4.addWidget(self.descr,8,1 ,1 , 2)
        self.layout4.addWidget(self.pic, 10, 0)
        self.layout4.addWidget(self.runhab, 7, 3)
        self.layout4.addWidget(self.pref_curve, 8, 3)

        self.layout4.addWidget(l9,1,3)
        self.layout4.addWidget(l10, 2, 3)
        self.layout4.addWidget(self.pichs, 3, 3,1, 2)

        self.layout4.addWidget(l3, 11, 0)
        self.layout4.addWidget(self.keys,12, 0)
        self.layout4.addWidget(l02,12, 1)
        self.layout4.addWidget(self.cond1,12, 2)
        self.layout4.addWidget(self.bs, 12, 3)

        self.layout4.addItem(spacer1, 0, 2)
        self.layout4.addItem(spacer2, 3, 3)
        self.setLayout(self.layout4)


    def create_database_gui(self):
        """
        This function calls the function which create the database if a change is recognized when HABBY start.
        If a suistability curves is added to HABBY, one must restarted to ass it to the database.
        """
