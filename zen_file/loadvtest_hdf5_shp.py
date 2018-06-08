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
# Purpose: A small application test to load HEC RAS data in XML form
#
# Author:      Diane.Von-Gunten
#
# Created:     08/02/2016
# Copyright:   (c) Diane.Von-Gunten 2016
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#
from PyQt5.QtCore import QCoreApplication, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QToolTip, QPushButton, QWidget, QLabel, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QGridLayout
import xml.etree.ElementTree as ET
import sys
import numpy as np
#import matplotlib
import shapefile
import h5py

#opening one main windows which contain the application
class Example(QMainWindow):

##    #this is our velocity data which we will use in different widgets
##    #we can use signal with emit
##    valueUpdated = pyqtSignal(int)

    def __init__(self):
        #one attribute with the velocity and the poistion of the velocity
        self.velocity = np.zeros((2, 65, 20))
        #call the normal constructor of QWidget
        super(Example, self).__init__()
        #call an additional function during initialisation
        self.initUI()

    #give everything which should open if you open the application
    def initUI(self):

        #create one Window

        self.setGeometry(300, 200, 500, 150)
        self.setWindowTitle('Test for PyQt v4 - Increase velocity')

        #add an exit option in the menu bar with shortcut
        exitAction = QAction(QIcon('exit.png'), '&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(qApp.quit)

        #add the exit option to the menu bar
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)

        #add an exit button
        qbtn = QPushButton('Quit', self)
        qbtn.clicked.connect(QCoreApplication.instance().quit)

        #add a button to open XML file
        filebutton = QPushButton('Open an XML File (HEC-RAS)')
        filebutton.clicked.connect(self.showDialog)

        #add a button to export the data to hdf5
        exporthdf5 = QPushButton('Export to .hdf5',self)
        exporthdf5.clicked.connect(self.hdf5_export)

        #add a button to export the data to .shp
        exportshp= QPushButton('Export to .shp', self)
        exportshp.clicked.connect(self.shp_export)

        #add a button to import the data to hdf5
        importhdf5 = QPushButton('Open hdf5 File', self)
        importhdf5.clicked.connect(self.hdf5_import)


        #add two buttons
        add2 = QPushButton('Add 2 m/s', self)
        #clicked.connect is expecting a fnuction without argument
        #so we call an extra lambda function to be able to give an argument
        add2.clicked.connect(lambda: self.add2f(10))
        add4 = QPushButton('Add 4 m/s', self)
        add4.clicked.connect(self.add4f)

        #add a button to export the data to txt
        expor = QPushButton('Export to .txt', self)
        expor.clicked.connect(self.exportf)


        #we add a small text
        l1 = QLabel('Let\'s be quicker!', self)

        #we go for a grid layout
        grid = QGridLayout()
        #we add a central widget to the main windows (which have a lay-out already)
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        centralWidget.setLayout(grid)
        #we add the create buttom
        grid.addWidget(filebutton,1,1)
        grid.addWidget(l1,0,0)
        grid.addWidget(expor, 0,2)
        grid.addWidget(qbtn, 3,1)
        grid.addWidget(add2,1,0)
        grid.addWidget(add4, 2,0)
        grid.addWidget(exporthdf5,2,2)
        grid.addWidget(importhdf5,2,1)
        grid.addWidget(exportshp,1,2)
        self.show()

#-----------------------------------------------------------------------
    #the function to open and read the XML file from HEC RAS
    def showDialog(self):

        #find the filename based on use choice
        #why [0] : getOpenFilename return a tuple [0,1,2], we need only the filename
        filename = QFileDialog.getOpenFileName(self, 'Open File', '.')[0]
        print('a'+filename+'b')

        #exeption: you should be able to clik on "cancel"
        if not filename: #if the string is empty
             print(' I did not load the xml file.')

        else:
            #parse the whole xml
            doc = ET.parse(filename)
            root = doc.getroot()
            #find where all velocity info are
            #.// all child ./ only first child
            a = root.findall(".//Velocity")

            #pass the data from Element type to double type.

            #to have a first estimation of the number of velocity in one strech
            #PROBLEM: length is changing!!!
            vel0 = str(a[0].text).split()
            nb_vel = len(vel0)

            #number of station
            nbstat = len(a)

            #create the empty array
            #data = [[[0 for x in range(nbstat)] for x in range(nb_vel+2)] for x in range(2)] #without nump
            #the +2 is there because of the changing size
            data = np.zeros((2, nbstat, nb_vel+1))

            #fill the array
            #a better method probably exist
            for i in range(0,nbstat):
                    b = str(a[i].text)
                    b2 = b.split()

                    for j in range(0,len(b2)):
                        b3 = b2[j].split(',')
                        data[0][i][j] = float(b3[0])
                        data[1][i][j] = float(b3[1])

            #pass the data in attribute to be used by other widget
            self.velocity = data

            print('I load the xml file')
#-----------------------------------------------------
    #the export function
    # a funtion to write the velocity as ascii file
    def exportf(self):
        #if numpy is not installed
        #xt if file does not exist, we could use if there
        #with open('velocity.txt','wt') as f:
            #f.write(str(self.velocity[0][4][4]))
        #ask for a file name?
        np.savetxt('velocity.txt', np.squeeze(self.velocity[1,:,:]))
        print('I export the file')

#----------------------------------------------------------
#create a hdf5 file and save it

    def hdf5_export(self):
        print('I export the data to the hdf5 format')

        #create an empty hdf5 file using all default prop.
        file = h5py.File('dset.h5','w')
        #create a data set into the group called file
        size_vel = self.velocity.shape
        dataset = file.create_dataset('dset', size_vel, data = self.velocity)

        #close
        file.close()

#-----------------------------------------------------
#export the data the .shp format

    def shp_export(self):

        #define the x coordinate (we could get it from the XML file also)
        nb_stat = self.velocity.shape[1]
        x_coor = np.arange(0,nb_stat, 0.1)

        #define an y corrdinate for a simpler test case
        nb_v = self.velocity.shape[2]
        y_corr = np.arange(0,nb_v, 0.1)

        #create a shape file of polygon type
        w = shapefile.Writer(shapefile.POLYGON)

## simple shape file to test how it works
##        #define the attribute table (C is for string and F for float, N for integer)
##        w.field('FIRST_FLD','C','40')
##        w.field('SECOND_FLD','F',10,8)
##
##        #create a first polygon
##        w.poly(parts=[[[1,5],[5,5],[5,1]]])
##        w.record('First',45.6)
##
##        #create a second polygon
##        w.poly(parts=[[[1,6],[1,5],[5,5]]])
##        w.record('Second',12.4)

        #define the attribute table
        w.field('VELOCITY','F',10,8)

        #Create each polygon and fill the attibute table
        #cf. drawing for the polygon
        for i in range(0, nb_stat -1):

            #!!!! there is no good reason for this -7
            #but so do not have to manage cases where the number of velocity is not the same in one strech
            for j in range(0, nb_v-7):
                 #create the polygone, point run clock wise
                 w.poly(parts=[[ [x_coor[i],self.velocity[0,i,j]],[x_coor[i],self.velocity[0,i,j+1]],[x_coor[i+1],self.velocity[0,i+1,j+1]],[x_coor[i+1],self.velocity[0,i+1,j]] ]])
##                 print ('new polygon')
##                 print(self.velocity[0,i,j])
##                 print(self.velocity[0,i,j+1])
##                 print(self.velocity[0,i+1,j])
##                 print(self.velocity[0,i+1,j+1])
##                 w.poly(parts=[[ [x_coor[i],y_corr[j]],[x_coor[i],y_corr[j+1]],[x_coor[i+1],y_corr[j+1]],[x_coor[i+1],y_corr[j]] ]])
                 #add the velocity
                 w.record(self.velocity[1,i,j])


        #save the shape file
        w.save('mytest')

        print('I export the file to .shp format')


#---------------------------------------------------------
#load the hd5 file created before
    def hdf5_import(self):

        #find the filename based on use choice
        #why [0] : getOpenFilename return a tuple [0,1,2], we need only the filename
        filename = QFileDialog.getOpenFileName(self, 'Open File', '.')[0]

        #in case you click on cancel
        if not filename: #if the string is empty
             print('I did not load the hdf5 file.')

        else:

            #load an existing hdf5 file
            file = h5py.File(filename,'r+')

            #load the exisiting dataset
            #we called the dataset dset in the function above
            #it does not work otherwise
            dataset = file['dset']

            #load the data
            #pass the data in attribute to be used by other widget
            #change type drom dataset to array
            self.velocity = np.array(dataset)

            #close
            file.close()

            print('I load the hdf5 file')


#------------------------------------------------------------

    #the add 2
    def add2f(self, testarg):
        self.velocity[1,:,:] = self.velocity[1,:,:] +2.0
        print('I add 2')

##        a= self.valueUpdated.emit(mytestarg)
##        print(a)

    def add4f(self):
        self.velocity[1,:,:] = self.velocity[1,:,:] + 4.0
        print('I add 4')

#--------------------------------------------------

def main():

    #create a Qt App
    app = QApplication(sys.argv)
    #create our example
    ex = Example()
    #manage exit
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
