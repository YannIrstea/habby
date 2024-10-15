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
import multiprocessing
import os
import sys
import traceback
import time
from datetime import datetime
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen, QGraphicsOpacityEffect
from appdirs import AppDirs

HABBY_VERSION_STR = "1.6.4"


class AppDataFolders:
    """
    The class preferencesHabby manage habby user preferences
    """

    def __init__(self):
        #print("__init__AppDataFolders")
        # folders Irstea/HABBY
        appauthor = "INRAE_EDF_OFB"
        appname = "HABBY"
        # INRAE_EDF_OFB and HABBY
        self.user_pref_habby_author_path = AppDirs(appname, appauthor).user_config_dir
        # saves
        self.user_pref_biology_models_save = os.path.join(self.user_pref_habby_author_path, "saves")
        # user_settings
        self.user_pref_habby_user_settings_path = os.path.join(self.user_pref_habby_author_path, "user_settings")
        # user_preferences.json
        self.user_pref_habby_file_path = os.path.join(self.user_pref_habby_user_settings_path, "user_preferences.json")
        # user_models
        self.user_pref_biology_models = os.path.join(self.user_pref_habby_user_settings_path, "biology", "user_models")
        # models_db.json
        self.user_pref_biology_models_db_file = os.path.join(self.user_pref_habby_user_settings_path, "biology", "models_db.json")
        # temp
        self.user_pref_temp_path = os.path.join(self.user_pref_habby_user_settings_path, "temp")
        # log_path
        self.user_pref_log_path = os.path.join(self.user_pref_habby_user_settings_path, "log")
        # log_file
        self.user_pref_crashlog_file = os.path.join(self.user_pref_habby_user_settings_path, "log", "habby_crash.log")

    # preferences
    def create_appdata_folders(self):
        # INRAE_EDF_OFB and HABBY
        if not os.path.isdir(self.user_pref_habby_author_path):
            os.makedirs(self.user_pref_habby_author_path)
        # saves
        if not os.path.isdir(self.user_pref_biology_models_save):
            os.makedirs(self.user_pref_biology_models_save)
        # user_settings
        if not os.path.isdir(self.user_pref_habby_user_settings_path):
            os.makedirs(self.user_pref_habby_user_settings_path)
        # user_models
        if not os.path.isdir(self.user_pref_biology_models):
            os.makedirs(self.user_pref_biology_models)
        # temp
        if not os.path.isdir(self.user_pref_temp_path):
            os.mkdir(self.user_pref_temp_path)
        # log_path
        if not os.path.isdir(self.user_pref_log_path):
            os.mkdir(self.user_pref_log_path)

    def crash_management_output(self, error_type, error_value, error_traceback):
        """
        catch exception before crashes program write it in habby_crash.log
        """
        # print to consol
        traceback.print_exception(error_type, error_value, error_traceback)

        # text
        text = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n" + ''.join(traceback.format_tb(error_traceback)) +\
               str(error_type).split("'")[1] + ": " +\
               str(error_value)

        # write to crash_log file
        with open(self.user_pref_crashlog_file, 'w') as f:
            f.write(text)
        # exit python
        raise SystemExit


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
    # current working directory
    if os.path.basename(sys.argv[0]) == "habby.py":  # from script
        # change current working directory
        os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    else:  # from exe
        try:
            this_file = __file__
        except NameError:
            this_file = sys.argv[0]
        this_file = os.path.abspath(this_file)
        if getattr(sys, 'frozen', False):
            application_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        else:
            application_path = os.path.dirname(this_file)
        os.chdir(application_path)  # change current working directory

    # GUI
    if len(sys.argv) <= 2 and 'LIST_COMMAND' not in sys.argv:
        """
        GUI
        """
        #print("GUI")
        from src_GUI import main_window_GUI
        import numpy as np
        # os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "2"  # try to ajust font size widget for windows
        # create app
        app = QApplication(sys.argv)

        # Create and display image splash screen
        time_between_image = 0.02
        delta_opacity = 0.1
        splash = QSplashScreen()
        splash.setPixmap(QPixmap('file_dep/splash_screen.png'))
        # splashscreen progressively displayed (with transparency)
        effect = QGraphicsOpacityEffect()
        splash.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        app.processEvents()
        splash.show()
        for opacity_value in np.arange(delta_opacity, 1.0 + delta_opacity, delta_opacity):
            time.sleep(time_between_image)
            effect.setOpacity(opacity_value)
            app.processEvents()

        # create windows
        if len(sys.argv) == 1:
            ex = main_window_GUI.MainWindows()
        if len(sys.argv) == 2:  # open existing project with .exe
            project_path = sys.argv[1]
            if os.path.exists(project_path) and project_path.split(".")[-1] == "habby":
                ex = main_window_GUI.MainWindows(project_path)
            else:
                return

        app.setActiveWindow(ex)

        # splashscreen progressively disappear (with transparency)
        for opacity_value in np.flip(np.arange(0.0, 1.0, delta_opacity)):
            time.sleep(time_between_image)
            effect.setOpacity(opacity_value)
            app.processEvents()
        splash.finish(ex)  # close splashscreen

        # close
        sys.exit(app.exec_())

    # CLI
    else:
        """
        CLI
        """
        #print("CLI")

        from src import func_for_cmd_mod

        # get path_prj and name_prj
        path_prj = None
        name_prj = None
        path_prj_index = None
        for id, opt in enumerate(sys.argv):
            if len(opt) > 8:
                if opt[:8] == 'path_prj':
                    path_prj = opt[9:]
                    name_prj = os.path.basename(path_prj)
                    path_prj_index = id

        if not path_prj and 'LIST_COMMAND' not in sys.argv:
            print("Error : Project path argument not found.")
            return
        else:
            if path_prj_index:
                # remove path_prj arg
                sys.argv.pop(path_prj_index)

        # check if enough argument
        if len(sys.argv) == 0 or len(sys.argv) == 1:
            print(" Not enough argument was given. \
                    At least one argument should be given")
            return

        # RESTART MODE
        elif sys.argv[1] == 'RESTART':
            if len(sys.argv) != 3:
                print('Error: the RESTART command needs the name of \
                      the restart file as input.')
                return
            func_for_cmd_mod.habby_restart(sys.argv[2], name_prj, path_prj)
        # ALL
        elif sys.argv[1] == 'ALL':
            if len(sys.argv) < 2:
                print('Error: the ALL command needs at least one argument.')
            all_arg = ['habby_cmd.py'] + sys.argv[2:]
            func_for_cmd_mod.habby_on_all(all_arg, name_prj, path_prj)
        else:
            all_arg = sys.argv[1:]
            func_for_cmd_mod.all_command(all_arg, name_prj, path_prj, HABBY_VERSION_STR)


if __name__ == '__main__':
    # with parallel process, don't import in this file an instance object
    # otherwise it will be re-created for each process started (EVIL)
    appdatafolders = AppDataFolders()
    appdatafolders.create_appdata_folders()
    sys.excepthook = appdatafolders.crash_management_output  # catch exception before crashes program write it in habby_crash.log
    multiprocessing.freeze_support()  # necessary to freeze the application with parallel process
    multiprocessing.set_start_method("spawn")  # enable plot.show() on linux system
    main()
