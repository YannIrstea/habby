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
import os
import json
from appdirs import AppDirs
import shutil
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox


class ConfigHabby:
    """
    The class ConfigHabby manage habby user configuration
    """
    def __init__(self):
        # default config data
        self.data = dict(language="english",  # english, french, spanish
                         name_prj="",
                         path_prj="",
                         recent_project_path="",
                         recent_project_name="",
                         selected_tabs=(True, True, False),  # physic, statistic, research
                         theme="classic",  # classic, dark
                         wind_position=(50, 75, 950, 720))  # X position, Y position, height, width
        # folders Irstea/HABBY
        appauthor = "Irstea"
        appname = "HABBY"
        self.dirs = AppDirs(appname, appauthor)
        self.user_config_habby_path = self.dirs.user_config_dir
        self.user_config_habby_file_path = os.path.join(self.dirs.user_config_dir, "habby_config.json")
        self.user_config_biology_models = os.path.join(self.user_config_habby_path, "biology", "models")
        self.user_config_temp_path = os.path.join(self.user_config_habby_path, "temp")
        self.user_config_log_path = os.path.join(self.user_config_habby_path, "log")
        self.user_config_crashlog_file = os.path.join(self.user_config_habby_path, "log", "crash_log.txt")

    def create_config_habby_structure(self):
        print("create_config_habby_structure")
        self.create_appdata_folders()
        self.create_default_or_load_config_habby()
        self.create_config_biology_models()
        self.create_empty_temp()

    def create_appdata_folders(self):
        print("create_appdata_folders")
        # user_config_habby_file_path
        if not os.path.isdir(self.user_config_habby_path):
            os.makedirs(self.user_config_habby_path)
        # user_config_biology_models
        if not os.path.isdir(self.user_config_biology_models):
            os.makedirs(self.user_config_biology_models)
        # user_config_temp_path
        if not os.path.isdir(self.user_config_temp_path):
            os.mkdir(self.user_config_temp_path)
        # user_config_log_path
        if not os.path.isdir(self.user_config_log_path):
            os.mkdir(self.user_config_log_path)
        # user_config_crashlog_file
        if not os.path.isfile(self.user_config_crashlog_file):
            open(self.user_config_crashlog_file, "w+").close()

    def create_default_or_load_config_habby(self):
        print("create_default_or_load_config_habby")
        if not os.path.isfile(self.user_config_habby_file_path):  # check if config file exist
            self.save_json()  # create it
        else:
            self.load_json()  # load it

    def create_config_biology_models(self):
        print("create_config_biology_models")

    def create_empty_temp(self):
        print("create_empty_temp")
        try:
            shutil.rmtree(self.user_config_temp_path)  # remove folder (and its files)
            os.mkdir(self.user_config_temp_path)  # recreate folder (empty)
        except:
            print("Error: Can't remove temps files. They are opened by another programme. Close them "
                               "and try again.")

    def save_json(self):
        print("save_json")
        with open(self.user_config_habby_file_path, "wt") as write_file:
            json.dump(self.data, write_file)

    def load_json(self):
        print("load_json")
        with open(self.user_config_habby_file_path, "r") as read_file:
            self.data = json.load(read_file)


