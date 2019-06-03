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


class ConfigHabby:
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
        # folders
        appauthor = "Irstea"
        appname = "HABBY"
        self.dirs = AppDirs(appname, appauthor)
        self.user_config_habby_file = os.path.join(self.dirs.user_config_dir, "habby_config.json")
        # check if folders exist
        if not os.path.isdir(self.dirs.user_config_dir):
            os.makedirs(self.dirs.user_config_dir)
        # check if config file exist
        if not os.path.isfile(self.user_config_habby_file):
            self.save_data()  # create it
        else:
            self.load_data()  # load it

    def save_data(self):
        print("save_json")
        with open(self.user_config_habby_file, "wt") as write_file:
            json.dump(self.data, write_file)

    def load_data(self):
        print("load_json")
        with open(self.user_config_habby_file, "r") as read_file:
            self.data = json.load(read_file)


