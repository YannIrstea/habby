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
#-------------------------------------------------------------------------------
# Name:        module1
# Purpose: test a drop menu to have a lot of option
#
# Author:      Diane.Von-Gunten
#
# Created:     23/02/2016
# Copyright:   (c) Diane.Von-Gunten 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------
import sys
import glob
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QGridLayout, QComboBox
from PyQt5.QtGui import QIcon

class Example(QMainWindow):

    def __init__(self):

        #call the normal constructor of QWidget
        super().__init__()
        #call an additinal function during initialisation
        self.initUI()

    def initUI(self):

         #create a menu bar which stay on regardless of the chosen widget
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)
        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)

        #add a combo box avec 200 choices
        self.cw= Class1()
        self.setCentralWidget(self.cw)


        #set geometry
        #self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('Un Long Menu')
        self.show()

class Class1(QWidget):

     def __init__(self):

        #call the normal constructor of QWidget
        super().__init__()
        #call an additinal function during initialisation
        self.stack1UI()


     def stack1UI(self):

        #create drop down menu
        self.combo = QComboBox()

        #add  all test file in a directory
        all_file= glob.glob('./file_test/*.txt')
        #make them look nicer
        for i in range(0,len(all_file)):
            print(all_file[i])

            all_file[i] =all_file[i].replace("./file_test\\","")
            all_file[i] = all_file[i].replace(".txt","")

        #add them to the menu
        self.combo.addItems(all_file)

        #connect with a function
        self.combo.currentIndexChanged.connect(self.selectionchange)

        #grid
        layout1 = QGridLayout()
        layout1.addWidget(self.combo,0,0)
        self.setLayout(layout1)

     #simple function
     def selectionchange(self,i):
        print(self.combo.currentText())



def main():
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
