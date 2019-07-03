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

from habby import AppDataFolders
from src import bio_info_mod
from src.tools_mod import sort_homogoeneous_dict_list_by_on_key


class UserPreferences(AppDataFolders):
    """
    The class UserPreferences manage habby user preferences
    """

    def __init__(self):
        super().__init__()
        # state
        self.modified = False
        # biological models allowed by HABBY dict
        self.biological_models_requirements_dict = dict(ModelType=["univariate suitability index curves"],
                                                        #
                                                        UnitVariable=[
                                                            ["PreferenceHeightOfWater", "HeightOfWaterClasses"],
                                                            ["PreferenceVelocity", "VelocityClasses"]],
                                                        UnitSymbol=[["m", "cm"], ["m/s", "cm/s"]],
                                                        UnitFactor=[[1, 0.01], [1, 0.01]])

        # default preferences data
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

    # GENERAL
    def create_user_preferences_structure(self):
        print("create_user_preferences_structure")
        # preferences
        self.create_and_clear_temp_folder()
        self.create_or_load_user_preferences()
        # MODEL BIO
        self.create_or_update_biology_models_json()

<<<<<<< HEAD
    # preferences
    def create_and_clear_temp_folder(self):
        # if not exist : craete it
        if not os.path.isdir(self.user_preferences_temp_path):
=======
    # PREFERENCES
    def create_empty_temp(self):
        try:
            shutil.rmtree(self.user_preferences_temp_path)  # remove folder (and its files)
>>>>>>> ee063b5429ffe7d6dca7436d21f0b3b9122ccdfe
            os.mkdir(self.user_preferences_temp_path)  # recreate folder (empty)
        # if exist : clear content
        else:
            try:
                filesToRemove = [os.path.join(self.user_preferences_temp_path, f) for f in os.listdir(self.user_preferences_temp_path)]
                for f in filesToRemove:
                    os.remove(f)
            except:
                print("Error: Can't remove temps files. They are opened by another programme. Close them "
                      "and try again.")

    def create_or_load_user_preferences(self):
        if not os.path.isfile(self.user_preferences_habby_file_path):  # check if preferences file exist
            self.save_user_preferences_json()  # create it
        else:
            self.load_user_preferences_json()  # load it

    def save_user_preferences_json(self):
        with open(self.user_preferences_habby_file_path, "wt") as write_file:
            json.dump(self.data, write_file)

    def load_user_preferences_json(self):
        with open(self.user_preferences_habby_file_path, "r") as read_file:
            self.data = json.load(read_file)

    # MODEL BIO
    def get_list_xml_model_files(self):
        # get list of xml files
        self.models_from_habby = sorted(
            [f for f in os.listdir(self.path_bio) if os.path.isfile(os.path.join(self.path_bio, f)) and ".xml" in f])
        self.picture_from_habby = sorted(
            [f for f in os.listdir(self.path_bio) if os.path.isfile(os.path.join(self.path_bio, f)) and ".png" in f])
        self.models_from_user_appdata = sorted([f for f in os.listdir(self.user_preferences_biology_models) if
                                                os.path.isfile(
                                                    os.path.join(self.user_preferences_biology_models, f)) and ".xml" in f])
        self.picture_from_user_appdata = sorted([f for f in os.listdir(self.user_preferences_biology_models) if
                                                 os.path.isfile(
                                                     os.path.join(self.user_preferences_biology_models, f)) and ".png" in f])

    def create_or_update_biology_models_json(self):
        # if not exist
        if not os.path.isfile(self.user_preferences_biology_models_db_file):
            self.create_biology_models_dict()
            self.create_biology_models_json()
            self.format_biology_models_dict_togui()

        # if exist
        elif os.path.isfile(self.user_preferences_biology_models_db_file):
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
                                      hydraulic_type_available=[],  # unsortable
                                      guild=[],  # sortable
                                      xml_origine=[],  # sortable
                                      made_by=[],  # sortable
                                      substrate_type=[],  # sortable
                                      substrate_type_available=[],  # unsortable
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
                path_bio = self.user_preferences_biology_models

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
                biological_models_dict["hydraulic_type_available"].append(
                    information_model_dict["hydraulic_type_available"])
                biological_models_dict["substrate_type"].append(information_model_dict["substrate_type"])
                biological_models_dict["substrate_type_available"].append(
                    information_model_dict["substrate_type_available"])
                biological_models_dict["guild"].append(information_model_dict["guild"])
                biological_models_dict["xml_origine"].append(xml_origine)
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
        self.biological_models_dict = sort_homogoeneous_dict_list_by_on_key(biological_models_dict,
                                                                            "cd_biological_model")

    def create_biology_models_json(self):
        # save database
        with open(self.user_preferences_biology_models_db_file, "wt") as write_file:
            json.dump(self.biological_models_dict, write_file)

    def format_biology_models_dict_togui(self):
        # orderedKeys that MUST ! correspond to listwidgets filtersnames
        self.biological_models_dict["orderedKeys"] = ["country", "aquatic_animal_type", "model_type", "stage_and_size",
                                                      "guild", "xml_origine", "made_by"]

        # new key orderedKeysmultilist for gui
        self.biological_models_dict["orderedKeysmultilist"] = []

        # format for gui
        for key in self.biological_models_dict["orderedKeys"]:
            if type(self.biological_models_dict[key][0]) == list:
                self.biological_models_dict["orderedKeysmultilist"].append(True)
            else:
                self.biological_models_dict["orderedKeysmultilist"].append(False)

    def check_need_update_biology_models_json(self):
        # create_biology_models_dict
        self.create_biology_models_dict()

        # load existing json
        biological_models_dict_from_json = self.load_biology_models_json()

        # check all
        if biological_models_dict_from_json != self.biological_models_dict:
            self.modified = True

        # check condition
        if self.modified:  # update json
            # get differences
            self.diff_list = ""
            for key in biological_models_dict_from_json:
                set_old = set(list(map(str, biological_models_dict_from_json[key])))
                set_new = set(list(map(str, self.biological_models_dict[key])))
                set_diff = set_new - set_old
                if set_diff:
                    self.diff_list += str(set_diff) + ", "
            self.create_biology_models_json()

    def load_biology_models_json(self):
        # load_biology_models_json
        with open(self.user_preferences_biology_models_db_file, "r") as read_file:
            biological_models_dict = json.load(read_file)
        return biological_models_dict


user_preferences = UserPreferences()
user_preferences.create_user_preferences_structure()
print("create instance", user_preferences)