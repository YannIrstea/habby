from PyQt5.QtCore import QTranslator, pyqtSignal, QThread
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QLabel, QGridLayout, QAction, qApp, \
    QTabWidget, QLineEdit, QTextEdit, QFileDialog, QSpacerItem, QListWidget,  QListWidgetItem, QComboBox, QMessageBox,\
    QStackedWidget, QRadioButton, QCheckBox


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
        self.init_iu()
        self.path_prj = path_prj
        self.name_prj = name_prj

    def init_iu(self):
        """
        Used in the initialization by __init__()
        """

        l1 = QLabel(self.tr('<b> Available Fish and Guild </b>'))
        l2 = QLabel(self.tr('<b> Selected Fish </b>'))
        l3 = QLabel(self.tr('Find fish (3 letters code)'))
        self.codefish = QLineEdit(' ')
        self.lf = QLabel(self.tr('No fish found'))
        self.ls = QLabel(self.tr('No fish selected'))
        self.list_f = QListWidget()
        self.list_s = QListWidget()
        self.bs = QPushButton(self.tr('Select all'))
        self.bc = QPushButton(self.tr('Curve information'))
        self.bsel = QPushButton(self.tr('Save selected curves'))
        spacer1 = QSpacerItem(1, 200)
        spacer2 = QSpacerItem(200, 1)

        self.layout4 = QGridLayout()
        self.layout4.addWidget(l1, 1, 0)
        self.layout4.addWidget(l2, 1, 1)
        self.layout4.addWidget(l3, 0, 0)
        self.layout4.addWidget(self.list_f, 2, 0, 2, 1)
        self.layout4.addWidget(self.list_s, 2, 1, 2, 1)
        self.layout4.addWidget(self.lf, 4, 0)
        self.layout4.addWidget(self.ls, 4, 1)
        self.layout4.addWidget(self.codefish, 0, 1)
        self.layout4.addWidget(self.bs, 0, 2)
        self.layout4.addWidget(self.bc, 5, 0)
        self.layout4.addWidget(self.bsel, 4, 2)
        self.layout4.addItem(spacer1, 6, 1)
        self.layout4.addItem(spacer2, 1, 4)
        self.setLayout(self.layout4)



