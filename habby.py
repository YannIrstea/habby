import sys
from src_GUI import Main_windows_1
from src import func_for_cmd
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication
import multiprocessing
import os


def main():
    """
    This is the main for HABBY. If no argument is given, the PyQt interface is called. If argument are given, HABBY is
    called from the command line. In this case, it can call restart (read a list of command from a
    file) or read a command written on the cmd or apply a command to a type of file (key word ALL before the command and
    name of the file with asterisk). For more complicated case, one can directly do a python script using the function
    from HABBY.
    """

    # graphical user interafce is called if no argument
    if len(sys.argv) == 1:
        # create app
        app = QApplication(sys.argv)
        # create windows
        ex = Main_windows_1.MainWindows()
        app.setActiveWindow(ex)

        # close
        sys.exit(app.exec_())
        #os._exit()
    # otherwise we use the command line
    else:
        """
        command line
        """

        # get path and project name

        namedir = 'result_cmd3'
        path_bio = './biology'
        version = 0.2
        # find the best path_prj
        settings = QSettings('irstea', 'HABBY' + str(version))
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
        for id, opt in enumerate(sys.argv):
            if len(opt) > 8:
                if opt[:8] == 'path_prj':
                    path_prj = opt[9:]
                    del sys.argv[id]
                    proj_def = False
                if opt[:8] == 'name_prj':
                    name_prj = opt[9:]
                    del sys.argv[id]
                if opt[:8] == 'path_bio':
                    path_bio = opt[9:]
                    del sys.argv[id]
        if proj_def:
            print('Warning: Could not find a project path. Saved data in ' + path_prj + '. Habby needs'
                                                                                        ' write permission \n.')

        # create an empty project if not existing gbefore
        filename_empty = os.path.abspath('src_GUI/empty_proj.xml')
        if not os.path.isdir(path_prj):
            os.makedirs(path_prj)
        if not os.path.isfile(os.path.join(path_prj, name_prj + '.xml')):
            func_for_cmd.copyfile(filename_empty, os.path.join(path_prj, name_prj + '.xml'))

        # check if enough argument
        if len(sys.argv) == 0 or len(sys.argv) == 1:
            print(" Not enough argument was given. At least one argument should be given")
            return

        if sys.argv[1] == 'RESTART':
            if len(sys.argv) != 3:
                print('Error: the RESTART command needs the name of the restart file as input.')
                return
            func_for_cmd.habby_restart(sys.argv[2], name_prj, path_prj, path_bio)
        elif sys.argv[1] == 'ALL':
            if len(sys.argv) < 2:
                print('Error: the ALL command needs at least one argument.')
            all_arg = ['habby_cmd.py'] + sys.argv[2:]
            func_for_cmd.habby_on_all(all_arg, name_prj, path_prj, path_bio)
        else:
            all_arg = sys.argv
            func_for_cmd.all_command(all_arg, name_prj, path_prj, path_bio)


if __name__ == '__main__':
    # necessarry to freeze the application with parrallel process
    multiprocessing.freeze_support()
    main()
