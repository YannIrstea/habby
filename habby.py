import sys
from src_GUI import Main_windows_1
from PyQt5.QtWidgets import QApplication
import multiprocessing
# from PyQt5.QtCore import pyqtRemoveInputHook

def main():

    # pyqtRemoveInputHook()  # should remove a QCoreApplication:: exec Warning

    # create app
    app = QApplication(sys.argv)
    # create windows
    ex = Main_windows_1.MainWindows()

    # close
    sys.exit(app.exec_())
    #os._exit()

if __name__ == '__main__':
    # necessarry to freeze the application with parrallel process
    multiprocessing.freeze_support()
    main()
