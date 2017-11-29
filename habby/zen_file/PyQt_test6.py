#-------------------------------------------------------------------------------
# Name:        module1
# Purpose: To test PyQt - One MainWindo and 2 Main Widget in one class
#
# Author:      Diane.Von-Gunten
#
# Created:     05/02/2016
# Copyright:   (c) Diane.Von-Gunten 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import sys
#from PyQt5.QtWidgets import (QWidget, QToolTip, QPushButton, QApplication, QMessageBox, )
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QGridLayout, QStackedWidget
from PyQt5.QtGui import QIcon

class Example(QMainWindow):



    def __init__(self):

        #an attribute to say which Main widget to use
        self.n_wid = 0
        #call the normal constructor of QWidget
        super().__init__()
        #call an additinal function during initialisation
        self.initUI()



    def initUI(self):

        #create two stacked Widget

        #create the 2 Widget
        self.stack1 = QWidget()
        self.stack2 = QWidget()
        #initialise them
        self.stack1UI()
        self.stack2UI()
        #create the staked Widget
        self.stack = QStackedWidget (self)
        self.stack.addWidget(self.stack1)
        self.stack.addWidget(self.stack2)

        #choose
        self.stack.setCurrentIndex(self.n_wid)


        #create a menu bar which stay on regardless of the chosen widget
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)

        exitAction2 = QAction(QIcon('exit.png'), '&Rien', self)
        exitAction2.setStatusTip('Ne fait vraiment rien')

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)
        fileMenu2 = menubar.addMenu('Menu inutile')
        fileMenu2.addAction(exitAction2)

        self.setCentralWidget(self.stack)

        #set geometry
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('Change Windows 2')
        self.show()

    def stack1UI(self):
         layout1 = QGridLayout()
         l1 = QLabel('Test', self)
         change = QPushButton('Change me', self)
         change.clicked.connect(self.change_me)

         layout1.addWidget(l1,1,1)
         layout1.addWidget(change,0,3)
         self.stack1.setLayout(layout1)


    def stack2UI(self):
         layout2 = QGridLayout()
         l2 = QLabel('Test 2', self)
         change2 = QPushButton('Change me 2', self)
         change2.clicked.connect(self.change_me)

         layout2.addWidget(l2,1,1)
         layout2.addWidget(change2,1,2)
         self.stack2.setLayout(layout2)

    def change_me(self):

        if self.n_wid == 0:
            self.n_wid = 1
        else:
            self.n_wid = 0
        self.stack.setCurrentIndex(self.n_wid)

def main():
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
