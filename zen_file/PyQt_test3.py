#-------------------------------------------------------------------------------
# Name:        module1
# Purpose: To test PyQt - ouvire une nouvelle fenetre sans fermer la premiere
#
# Author:      Diane.Von-Gunten
#
# Created:     05/02/2016
# Copyright:   (c) Diane.Von-Gunten 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
#import pymesh
#from PyQt5 import QtGui


class Example2(QWidget):

    def __init__(self):
        #call the normal constructor of QWidget
        super().__init__()
        #call an additinal function during initialisation
        self.initUI2()


    def initUI2(self):
        l1 = QLabel('This winodws has been changed', self)

        bbox = QVBoxLayout()
        bbox.addWidget(l1)

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('An other Windows')
        self.show()


class Example(QWidget):

    def __init__(self):
        #call the normal constructor of QWidget
        super().__init__()
        #call an additinal function during initialisation
        self.initUI()
        self.child = None


    def initUI(self):


        change = QPushButton('Change me', self)
        change.clicked.connect(self.change_me)

        lcd = QLCDNumber(self)
        sld = QSlider(Qt.Horizontal, self)

        vbox = QVBoxLayout()
        vbox .addWidget(lcd)
        vbox.addWidget(sld)
        vbox.addWidget(change)

        self.setLayout(vbox)
        sld.valueChanged.connect(lcd.display)

        l1 = QLabel('ZetCode', self)
        l1.move(35, 40)

        self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Signal & slot')
        self.show()

    def change_me(self):

        self.child = Example2()
        self.child.show()

def main():
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
