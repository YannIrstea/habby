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
from operator import concat
from functools import reduce
import numpy as np

from src import bio_info_mod


class ConfigHabby:
    """
    The class ConfigHabby manage habby user configuration
    """

    def __init__(self):
        # biological models allowed by HABBY dict
        self.biological_models_requirements_dict = dict(ModelType=["univariate suitability index curves"],
                                                        #
                                                        UnitVariable=[["PreferenceHeightOfWater","HeightOfWaterClasses"], ["PreferenceVelocity","VelocityClasses"] ],
                                                        UnitSymbol=[["m", "cm"], ["m/s", "cm/s"]],
                                                        UnitFactor = [[1,0.01],[1,0.01]])



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
        self.path_bio = os.path.join("biology", "models")  # path to biological
        # biological_models_dict
        self.biological_models_dict = dict()
        # biological_models_dict_set
        self.biological_models_dict_set = dict(country=[],
                                      aquatic_animal_type=[],
                                      model_type=[],
                                      stage_and_size=[],
                                      guild=[],
                                      xml_origine=[],
                                      made_by=[],
                                      code_alternative=[])

        # folders Irstea/HABBY
        appauthor = "Irstea"
        appname = "HABBY"
        self.user_config_habby_path = AppDirs(appname, appauthor).user_config_dir
        self.user_config_habby_file_path = os.path.join(self.user_config_habby_path, "habby_config.json")
        self.user_config_biology_models = os.path.join(self.user_config_habby_path, "biology", "user_models")
        self.user_config_biology_models_db_file = os.path.join(self.user_config_habby_path, "biology",
                                                                "models_db.json")
        self.user_config_temp_path = os.path.join(self.user_config_habby_path, "temp")
        self.user_config_log_path = os.path.join(self.user_config_habby_path, "log")
        self.user_config_crashlog_file = os.path.join(self.user_config_habby_path, "log", "habby_crash.log")

    # GENERAL
    def create_config_habby_structure(self):
        # CONFIG
        self.create_appdata_folders()
        self.create_empty_temp()
        self.create_default_or_load_config_habby()
        # MODEL BIO
        self.create_or_update_biology_models_json()

    # CONFIG
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

    def save_config_json(self):
        with open(self.user_config_habby_file_path, "wt") as write_file:
            json.dump(self.data, write_file)

    def load_config_json(self):
        with open(self.user_config_habby_file_path, "r") as read_file:
            self.data = json.load(read_file)

    # MODEL BIO
    def get_list_xml_model_files(self):
        # get list of xml files
        self.models_from_habby = sorted(
            [f for f in os.listdir(self.path_bio) if os.path.isfile(os.path.join(self.path_bio, f)) and ".xml" in f])
        self.picture_from_habby = sorted(
            [f for f in os.listdir(self.path_bio) if os.path.isfile(os.path.join(self.path_bio, f)) and ".png" in f])
        self.models_from_user_appdata = sorted([f for f in os.listdir(self.user_config_biology_models) if
                                                os.path.isfile(
                                                    os.path.join(self.user_config_biology_models, f)) and ".xml" in f])
        self.picture_from_user_appdata = sorted([f for f in os.listdir(self.user_config_biology_models) if
                                                 os.path.isfile(
                                                     os.path.join(self.user_config_biology_models, f)) and ".png" in f])

    def create_or_update_biology_models_json(self):
        # if not exist
        if not os.path.isfile(self.user_config_biology_models_db_file):
            self.create_biology_models_dict()
            self.create_biology_models_json()
            self.format_biology_models_dict_togui()

        # if exist
        elif os.path.isfile(self.user_config_biology_models_db_file):
            self.check_need_update_biology_models_json()
            self.format_biology_models_dict_togui()

    def create_biology_models_dict(self):
        self.get_list_xml_model_files()

        # biological_models_dict
        biological_models_dict = dict(country=[],  # sortable
                                      aquatic_animal_type=[],  # sortable
                                      model_type=[],  # sortable
                                      stage_and_size=[],  # sortable
                                      hydraulic_type=[],  # sortable
                                      guild=[],  # sortable
                                      xml_origine=[],  # sortable
                                      made_by=[],  # sortable
                                      substrate_type=[],  # sortable
                                      code_alternative=[],  # sortable
                                      cd_biological_model=[],  # unsortable
                                      modification_date=[],  # unsortable
                                      latin_name=[],  # unsortable
                                      path_xml=[],  # unsortable
                                      path_img=[])

        # for each source
        for xml_origine in ["user", "habby"]:
            if xml_origine == "habby":
                xml_list = self.models_from_habby
                path_bio = self.path_bio
            if xml_origine == "user":
                xml_list = self.models_from_user_appdata
                path_bio = self.user_config_biology_models

            # for each xml file
            for file_ind, xml_filename in enumerate(xml_list):
                # get path
                path_xml = os.path.join(path_bio, xml_filename)
                # get_biomodels_informations_for_database
                information_model_dict = bio_info_mod.get_biomodels_informations_for_database(path_xml)
                # append in dict
                biological_models_dict["country"].append(information_model_dict["country"])
                biological_models_dict["aquatic_animal_type"].append(information_model_dict["aquatic_animal_type"])
                biological_models_dict["model_type"].append(information_model_dict["ModelType"])
                biological_models_dict["stage_and_size"].append(information_model_dict["stage_and_size"])
                biological_models_dict["hydraulic_type"].append(information_model_dict["hydraulic_type"])
                biological_models_dict["guild"].append(information_model_dict["guild"])
                biological_models_dict["xml_origine"].append(xml_origine)
                biological_models_dict["substrate_type"].append(information_model_dict["substrate_type"])
                biological_models_dict["made_by"].append(information_model_dict["MadeBy"])
                # last sortable
                biological_models_dict["code_alternative"].append(information_model_dict["CdAlternative"])
                # save data unsortable
                biological_models_dict["cd_biological_model"].append(information_model_dict["CdBiologicalModel"])
                biological_models_dict["modification_date"].append(information_model_dict["modification_date"])
                biological_models_dict["latin_name"].append(information_model_dict["LatinName"])
                biological_models_dict["path_xml"].append(path_xml)
                biological_models_dict["path_img"].append(information_model_dict["path_img"])

        # sort by latin name
        indice_sorted = [biological_models_dict["cd_biological_model"].index(x) for x in sorted(biological_models_dict["cd_biological_model"])]
        for key in biological_models_dict.keys():
            key_list = []
            for ind_num, ind_ind in enumerate(indice_sorted):
                key_list.append(biological_models_dict[key][ind_ind])
            biological_models_dict[key] = key_list

        self.biological_models_dict = biological_models_dict

    def create_biology_models_json(self):
        # save database
        with open(self.user_config_biology_models_db_file, "wt") as write_file:
            json.dump(self.biological_models_dict, write_file)

    def format_biology_models_dict_togui(self):
        # new key orderedKeysmultilist for gui
        self.biological_models_dict["orderedKeysmultilist"] = []

        # format for gui
        for key in self.biological_models_dict_set.keys():
            if type(self.biological_models_dict[key][0]) == list:
                self.biological_models_dict["orderedKeysmultilist"].append(True)
                #self.biological_models_dict[key] = [set(element) for element in self.biological_models_dict[key]]
            else:
                self.biological_models_dict["orderedKeysmultilist"].append(False)
        self.biological_models_dict["selected"] = np.ones(len(self.biological_models_dict["country"]), dtype=bool)
        self.biological_models_dict["orderedKeys"] = ["country", "aquatic_animal_type", "model_type", "stage_and_size",
                                    "guild", "xml_origine", "made_by"]

    def check_need_update_biology_models_json(self):
        # init
        path_xml = False
        modification_date = False

        # create_biology_models_dict
        self.create_biology_models_dict()

        # load existing json
        biological_models_dict_from_json = self.load_biology_models_json()

        # check == filename
        if biological_models_dict_from_json["path_xml"] != self.biological_models_dict["path_xml"]:
            path_xml = True

        # check == date
        if biological_models_dict_from_json["modification_date"] != self.biological_models_dict["modification_date"]:
            modification_date = True

        # check == len(keys)
        if len(biological_models_dict_from_json.keys()) != len(self.biological_models_dict.keys()):  # -1 because orderedKeys
            modification_date = True

        # check condition
        if path_xml or modification_date:  # update json
            self.create_biology_models_json()

    def load_biology_models_json(self):
        # load_biology_models_json
        with open(self.user_config_biology_models_db_file, "r") as read_file:
            biological_models_dict = json.load(read_file)
        return biological_models_dict

    # TEMP FOLDER
    def create_empty_temp(self):
        try:
            shutil.rmtree(self.user_config_temp_path)  # remove folder (and its files)
            os.mkdir(self.user_config_temp_path)  # recreate folder (empty)
        except:
            print("Error: Can't remove temps files. They are opened by another programme. Close them "
                  "and try again.")


CONFIG_HABBY = ConfigHabby()
CONFIG_HABBY.create_config_habby_structure()
