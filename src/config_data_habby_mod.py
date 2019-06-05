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
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
import json
import os
import shutil
from appdirs import AppDirs

from src import bio_info_mod


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
        # biological models
        self.path_bio = os.path.join("biology", "models") # path to biological
        self.biological_models_dict = dict(country=[],               # sortable
                                      aquatic_animal_type=[],   # sortable
                                      model_type=[],            # sortable
                                      stage_and_size=[],        # sortable
                                      guild=[],                 # sortable
                                      xml_origine=[],           # sortable
                                      made_by=[],               # sortable
                                      code_alternative=[],      # sortable
                                      path_xml=[],              # unsortable
                                      path_png=[]               # unsortable
                                      )
        # folders Irstea/HABBY
        appauthor = "Irstea"
        appname = "HABBY"
        self.user_config_habby_path = AppDirs(appname, appauthor).user_config_dir
        self.user_config_habby_file_path = os.path.join(self.user_config_habby_path, "habby_config.json")
        self.user_config_biology_models = os.path.join(self.user_config_habby_path, "biology", "models")
        self.user_config_biology_models_database = os.path.join(self.user_config_biology_models, "models_db.json")
        self.user_config_temp_path = os.path.join(self.user_config_habby_path, "temp")
        self.user_config_log_path = os.path.join(self.user_config_habby_path, "log")
        self.user_config_crashlog_file = os.path.join(self.user_config_habby_path, "log", "habby_crash.log")

    def create_config_habby_structure(self):
        self.create_appdata_folders()
        self.create_default_or_load_config_habby()
        self.create_biology_models_json()
        self.create_empty_temp()

    def create_appdata_folders(self):
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

    def create_default_or_load_config_habby(self):
        if not os.path.isfile(self.user_config_habby_file_path):  # check if config file exist
            self.save_config_json()  # create it
        else:
            self.load_config_json()  # load it

    def create_biology_models_json(self):
        models_from_habby = sorted([f for f in os.listdir(self.path_bio) if os.path.isfile(os.path.join(self.path_bio, f)) and ".xml" in f])
        picture_from_habby = sorted([f for f in os.listdir(self.path_bio) if os.path.isfile(os.path.join(self.path_bio, f)) and ".png" in f])
        models_from_user_appdata = sorted([f for f in os.listdir(self.user_config_biology_models) if os.path.isfile(os.path.join(self.path_bio, f)) and ".xml" in f])
        picture_from_user_appdata = sorted([f for f in os.listdir(self.user_config_biology_models) if os.path.isfile(os.path.join(self.path_bio, f)) and ".png" in f])

        # for each source
        for xml_origine in ["habby", "user"]:
            if xml_origine == "habby":
                xml_list = models_from_habby
                png_list = picture_from_habby
            if xml_origine == "user":
                xml_list = models_from_user_appdata
                png_list = picture_from_user_appdata

            # for each xml file
            for file_ind, xml_filename in enumerate(xml_list):
                # get path
                path_xml = os.path.join(self.path_bio, xml_filename)
                path_png = os.path.join(self.path_bio, png_list[file_ind])
                # get_biomodels_informations_for_database
                stage_and_size, ModelType, MadeBy, CdAlternative = bio_info_mod.get_biomodels_informations_for_database(path_xml)
                # for each stage
                for stage in stage_and_size:
                    # save data sortable
                    self.biological_models_dict["country"].append("France")  # TODO: get real info
                    self.biological_models_dict["aquatic_animal_type"].append("fish")  # TODO: get real info
                    self.biological_models_dict["model_type"].append(ModelType)
                    self.biological_models_dict["stage_and_size"].append(stage)
                    self.biological_models_dict["guild"].append("mono")  # TODO: get real info
                    self.biological_models_dict["xml_origine"].append(xml_origine)
                    self.biological_models_dict["made_by"].append(MadeBy)
                    # last sortable
                    self.biological_models_dict["code_alternative"].append(CdAlternative)
                    # save data unsortable
                    self.biological_models_dict["path_xml"].append(path_xml)
                    self.biological_models_dict["path_png"].append(path_png)

        with open(self.user_config_biology_models_database, "wt") as write_file:
            json.dump(self.biological_models_dict, write_file)

    def create_empty_temp(self):
        try:
            shutil.rmtree(self.user_config_temp_path)  # remove folder (and its files)
            os.mkdir(self.user_config_temp_path)  # recreate folder (empty)
        except:
            print("Error: Can't remove temps files. They are opened by another programme. Close them "
                               "and try again.")

    def save_config_json(self):
        with open(self.user_config_habby_file_path, "wt") as write_file:
            json.dump(self.data, write_file)

    def load_config_json(self):
        with open(self.user_config_habby_file_path, "r") as read_file:
            self.data = json.load(read_file)


