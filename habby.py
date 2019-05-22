"""
An open-source software to estimate habitat suitability:
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
import sys
from src_GUI import main_window_GUI
from src import func_for_cmd_mod
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
import multiprocessing
import os


global HABBY_VERSION
HABBY_VERSION = 0.24


def main():
    """
    This is the main for HABBY. If no argument is given, the PyQt interface
    is called. If argument are given, HABBY is called from the command line.
    In this case, it can call restart (read a list of command from a file) or
    read a command written on the cmd or apply a command to a type of file
    (key word ALL before the command and name of the file with asterisk).
    For more complicated case, one can directly do a python script using
    the function from HABBY.
    """
    # set version

    # graphical user interface is called if no argument
    if len(sys.argv) == 1:
        """
        GUI
        """
        # create app
        app = QApplication(sys.argv)


        # Create and display the splash screen
        splash_pix = QPixmap('translation/habby_icon.png')
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())
        splash.show()
        app.processEvents()

        # create windows
        ex = main_window_GUI.MainWindows(HABBY_VERSION)
        app.setActiveWindow(ex)

        # close the splash screen
        splash.finish(ex)

        # close
        sys.exit(app.exec_())

        # os._exit()

    # otherwise we use the command line
    else:
        """
        command line
        """
        # get path and project name
        namedir = 'result_cmd3'
        path_bio = './biology'
        # find the best path_prj
        settings = QSettings('irstea', 'HABBY' + str(HABBY_VERSION))
        name_prj = settings.value('name_prj')
        path_prj = settings.value('path_prj')
        proj_def = False
        if not path_prj:
            path_prj = os.path.join(os.path.abspath('output_cmd'), namedir)
            name_prj = 'DefaultProj'
            proj_def = True
        elif not os.path.isdir(path_prj):
            path_prj = os.path.join(os.path.abspath('output_cmd'), namedir)
            name_prj = 'DefaultProj'
            proj_def = True
        # index to remove
        path_prj_index = None
        name_prj_index = None
        path_bio_index = None

        for id, opt in enumerate(sys.argv):
            if len(opt) > 8:
                if opt[:8] == 'path_prj':
                    path_prj = opt[9:]
                    path_prj_index = id
                    proj_def = False
                if opt[:8] == 'name_prj':
                    name_prj = opt[9:]
                    name_prj_index = id
                if opt[:8] == 'path_bio':
                    path_bio = opt[9:]
                    path_bio_index = id

        # remove if arg
        if path_prj_index and name_prj_index and path_bio_index:
            sys.argv = [v for i,v in enumerate(sys.argv) if i not in [path_prj_index, name_prj_index, path_bio_index]]
        elif path_prj_index and name_prj_index:
            sys.argv = [v for i, v in enumerate(sys.argv) if i not in [path_prj_index, name_prj_index]]
        elif path_prj_index and not name_prj_index and not path_bio_index:
            del sys.argv[path_prj_index]
        elif not path_prj_index and name_prj_index and not path_bio_index:
            del sys.argv[name_prj_index]
        elif not path_prj_index and not name_prj_index and path_bio_index:
            del sys.argv[path_bio_index]
        else:
            pass

        if proj_def:
            print('Warning: Could not find a project path. Saved data in '
                  + path_prj
                  + '. Habby needs write permission \n.')

        # create an empty project if not existing before
        filename_empty = os.path.abspath('src_GUI/empty_proj.xml')
        if not os.path.isdir(path_prj):
            os.makedirs(path_prj)
        if not os.path.isfile(os.path.join(path_prj, name_prj + '.xml')):
            func_for_cmd_mod.copyfile(filename_empty,
                                      os.path.join(path_prj, name_prj + '.xml'))

        # check if enough argument
        if len(sys.argv) == 0 or len(sys.argv) == 1:
            print(" Not enough argument was given. \
                    At least one argument should be given")
            return

        if sys.argv[1] == 'RESTART':
            if len(sys.argv) != 3:
                print('Error: the RESTART command needs the name of \
                      the restart file as input.')
                return
            func_for_cmd_mod.habby_restart(sys.argv[2], name_prj, path_prj,
                                           path_bio)
        elif sys.argv[1] == 'ALL':
            if len(sys.argv) < 2:
                print('Error: the ALL command needs at least one argument.')
            all_arg = ['habby_cmd.py'] + sys.argv[2:]
            func_for_cmd_mod.habby_on_all(all_arg, name_prj, path_prj, path_bio)
        else:
            all_arg = sys.argv[1:]
            func_for_cmd_mod.all_command(all_arg, name_prj, path_prj, path_bio)


if __name__ == '__main__':
    # necessary to freeze the application with parallel process
    multiprocessing.freeze_support()
    main()
