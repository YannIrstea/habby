"""
This file is part of the free software:
 _   _   ___  ______________   __
| | | | / _ \ | ___ \ ___ \ \ / /
| |_| |/ /_\ \| |_/ / |_/ /\ V / 
|  _  ||  _  || ___ \ ___ \ \ /  
| | | || | | || |_/ / |_/ / | |  
\_| |_/\_| |_/\____/\____/  \_/  

Copyright (c) IRSTEA-EDF-AFB 2017

Licence CeCILL v2.1

https://github.com/YannIrstea/habby

"""
import sys
import matplotlib
matplotlib.use("Qt5Agg")
import numpy as np
from numpy import arange, sin, pi
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QMainWindow, QApplication, QSizePolicy, QVBoxLayout, QPushButton
from PyQt5.QtCore import *
from PyQt5.QtGui import QCursor
class MyMplCanvas(FigureCanvas):
    #Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        # We want the axes cleared every time plot() is called
        self.axes.hold(False)

        self.compute_initial_figure()
        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def compute_initial_figure(self):
        pass


class MyStaticMplCanvas(MyMplCanvas):
    #Simple canvas with a sine plot.
    def compute_initial_figure(self):
        t = arange(0.0, 3.0, 0.01)
        s = sin(2*pi*t)
        self.axes.plot(t, s)

class PlotDialog(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.plot_layout = QVBoxLayout(self)
        self.plot_canvas = MyStaticMplCanvas(self, width=5, height=4, dpi=100)

        self.navi_toolbar = NavigationToolbar(self.plot_canvas, self)
        self.plot_layout.addWidget(self.plot_canvas)  # the matplotlib canvas
        self.plot_layout.addWidget(self.navi_toolbar)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    dialog = PlotDialog()
    dialog.show()
    sys.exit(app.exec_())
