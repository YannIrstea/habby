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
import json
import os
from shutil import copy as sh_copy
from time import strftime

from habby import AppDataFolders, HABBY_VERSION_STR
from src import bio_info_mod
from src.dev_tools_mod import sort_homogoeneous_dict_list_by_on_key


class UserPreferences(AppDataFolders):
    """
    The class UserPreferences manage habby user preferences
    """

    def __init__(self):
        super().__init__()
        # state
        self.modified = False
        self.user_preference_cruve_list = []
        # default preferences data
        self.data = self.create_defaut_user_preferences()
        # biological models
        self.path_bio = os.path.join("biology", "models")  # path to biological
        # biological_models_dict
        self.biological_models_dict = dict()
        # differences between old database and new database
        self.diff_list = ""

    # GENERAL
    def create_user_preferences_structure(self):
        # check if code is started from habby.py wd or another wd path
        splited_path = os.getcwd().split("\\")
        if "habby" in splited_path:
            if splited_path.index("habby") != len(splited_path) - 1:
                # change wd
                os.chdir("\\".join(splited_path[:splited_path.index("habby") + 1]))
                # create_appdata_folders
                if not os.path.exists(self.user_pref_habby_user_settings_path):
                    self.create_appdata_folders()

        # preferences
        self.create_and_clear_temp_folder()
        self.create_or_load_user_preferences()
        # MODEL BIO
        self.create_or_update_biology_models_json()

    # PREFERENCES
    def create_and_clear_temp_folder(self):
        # if not exist : craete it
        if not os.path.isdir(self.user_pref_temp_path):
            os.mkdir(self.user_pref_temp_path)  # recreate folder (empty)
        # if exist : clear content
        else:
            try:
                filesToRemove = [os.path.join(self.user_pref_temp_path, f) for f in os.listdir(self.user_pref_temp_path)]
                for f in filesToRemove:
                    os.remove(f)
            except:
                print("Error: Can't remove temps files. They are opened by another programme. Close them "
                      "and try again.")

    def create_defaut_user_preferences(self):
        return dict(habby_version=HABBY_VERSION_STR,
                        language="english",  # english, french, spanish
                         name_prj="",
                         path_prj="",
                         recent_project_path=[],
                         recent_project_name=[],
                         theme="classic",  # classic, dark
                         wind_position=(50, 75, 950, 720),  # X position, Y position, height, width
                         lammi_sub_classification_code="EDF",  # EDF or Cemagref for lammi data
                         lammi_calculation_method="FEM")  # FVM or FEM for lammi data

    def create_or_load_user_preferences(self):
        if not os.path.isfile(self.user_pref_habby_file_path):  # check if preferences file exist
            self.save_user_preferences_json()  # create it
        else:
            # if new key added to user_preferences : recreate a new
            existing_dict = self.load_user_preferences_json()  # load it
            if existing_dict.keys() == self.data.keys():
                self.data = existing_dict
            else:
                # recreate new
                self.data = self.create_defaut_user_preferences()
                self.save_user_preferences_json()  # erase file

            # if new version of habby : recreate a new
            try:
                user_old_habby_version = str(self.data["habby_version"])
            except KeyError:
                user_old_habby_version = "0.0.0"
            user_old_habby_version = tuple(map(int, user_old_habby_version.split('.')))  # version tuple
            HABBY_VERSION_TUPLE = tuple(map(int, HABBY_VERSION_STR.split('.')))  # version tuple
            if user_old_habby_version < HABBY_VERSION_TUPLE:  # X.Y.Z version level
                self.data = self.create_defaut_user_preferences()
                self.save_user_preferences_json()  # erase file

    def save_user_preferences_json(self):
        with open(self.user_pref_habby_file_path, "wt") as write_file:
            json.dump(self.data, write_file, indent=4)

    def load_user_preferences_json(self):
        with open(self.user_pref_habby_file_path, "r") as read_file:
            data_dict = json.load(read_file)
        return data_dict

    # MODEL BIO
    def get_list_xml_model_files(self):
        # habby sources
        self.models_from_habby = []
        for root, _, fichiers in os.walk(self.path_bio):
            for fichier in fichiers:
                if fichier.endswith(".xml"):
                    self.models_from_habby.append(os.path.join(root, fichier))
        self.picture_from_habby = []
        for root, _, fichiers in os.walk(self.path_bio):
            for fichier in fichiers:
                if fichier.endswith(".png"):
                    self.picture_from_habby.append(os.path.join(root, fichier))
        # user sources
        self.models_from_user_appdata = []
        for root, _, fichiers in os.walk(self.user_pref_biology_models):
            for fichier in fichiers:
                if fichier.endswith(".xml"):
                    self.models_from_user_appdata.append(os.path.join(root, fichier))
        self.picture_from_user_appdata = []
        for root, _, fichiers in os.walk(self.user_pref_biology_models):
            for fichier in fichiers:
                if fichier.endswith(".png"):
                    self.picture_from_user_appdata.append(os.path.join(root, fichier))

    def create_or_update_biology_models_json(self):
        # if not exist
        if not os.path.isfile(self.user_pref_biology_models_db_file):
            self.create_biology_models_dict()
            self.create_biology_models_json()
            self.format_biology_models_dict_togui()
            self.modified = True
            self.diff_list = ""

        # if exist
        else:
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
                                      code_biological_model=[],  # unsortable
                                      modification_date=[],  # unsortable
                                      latin_name=[],  # unsortable
                                      path_xml=[],  # unsortable
                                      path_img=[])

        # for each source
        for xml_origine in ["habby", "user"]:
            if xml_origine == "habby":
                xml_list = self.models_from_habby
            elif xml_origine == "user":
                xml_list = self.models_from_user_appdata

            # for each xml file
            for file_ind, xml_filename in enumerate(xml_list):
                # get_biomodels_informations_for_database
                information_model_dict = bio_info_mod.get_biomodels_informations_for_database(xml_filename)
                if type(information_model_dict) == dict:
                    # check if user model added exist in habby database .xml name (same as code_alternative)
                    continue_tf = False
                    if os.path.basename(xml_filename) in [os.path.basename(path_xml) for path_xml in biological_models_dict["path_xml"]]:
                        self.user_preference_cruve_list.append(
                            "Warning: The recently added preference curve " + xml_filename + " is invalid. Filename already exists. Please fix it and re-run HABBY or refresh user biological database.")
                        continue_tf = True
                    if information_model_dict["code_biological_model"] in biological_models_dict["code_biological_model"]:
                        self.user_preference_cruve_list.append(
                            "Warning: The recently added preference curve " + xml_filename + " is invalid. CdBiologicalModel already exists. Please fix it and re-run HABBY or refresh user biological database.")
                        continue_tf = True
                    if continue_tf:
                        continue

                    # append in dict
                    biological_models_dict["country"].append(information_model_dict["country"])
                    biological_models_dict["aquatic_animal_type"].append(information_model_dict["aquatic_animal_type"])
                    biological_models_dict["model_type"].append(information_model_dict["model_type"])
                    biological_models_dict["stage_and_size"].append(information_model_dict["stage_and_size"])
                    biological_models_dict["hydraulic_type"].append(information_model_dict["hydraulic_type"])
                    biological_models_dict["hydraulic_type_available"].append(
                        information_model_dict["hydraulic_type_available"])
                    biological_models_dict["substrate_type"].append(information_model_dict["substrate_type"])
                    biological_models_dict["substrate_type_available"].append(
                        information_model_dict["substrate_type_available"])
                    biological_models_dict["guild"].append(information_model_dict["guild"])
                    biological_models_dict["xml_origine"].append(xml_origine)
                    biological_models_dict["made_by"].append(information_model_dict["made_by"])
                    # last sortable
                    biological_models_dict["code_alternative"].append(information_model_dict["code_alternative"])
                    # save data unsortable
                    biological_models_dict["code_biological_model"].append(information_model_dict["code_biological_model"])
                    biological_models_dict["modification_date"].append(information_model_dict["modification_date"])
                    biological_models_dict["latin_name"].append(information_model_dict["latin_name"])
                    biological_models_dict["path_xml"].append(xml_filename)
                    biological_models_dict["path_img"].append(information_model_dict["path_img"])
                elif type(information_model_dict) == str:
                    self.diff_list = self.diff_list + "\n" + information_model_dict

        # sort by latin name
        self.biological_models_dict = sort_homogoeneous_dict_list_by_on_key(biological_models_dict,
                                                                            "code_biological_model")

    def create_biology_models_json(self):
        # save database
        with open(self.user_pref_biology_models_db_file, "wt") as write_file:
            json.dump(self.biological_models_dict, write_file, indent=4)

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
        # create_biology_models_dict (new)
        self.create_biology_models_dict()

        # load json (existing)
        biological_models_dict_from_json = self.load_biology_models_json()

        # check diff all
        if biological_models_dict_from_json != self.biological_models_dict:
            self.modified = True

        # check condition
        if self.modified:  # update json
            # get differences
            diff_key_list = ""
            diff_key_inverse_list = ""
            for key in biological_models_dict_from_json.keys():
                set_old = set(list(map(str, biological_models_dict_from_json[key])))
                set_new = set(list(map(str, self.biological_models_dict[key])))
                # new
                set_diff = set_new - set_old
                if set_diff:
                    diff_key_list += str(set_diff) + ", "
                # old
                set_diff_inverse = set_old - set_new
                if set_diff_inverse:
                    diff_key_inverse_list += str(set_diff_inverse) + ", "

            if diff_key_list or diff_key_inverse_list:
                # new xml curve (from AppData user)
                if "xml" in diff_key_list and "user" in diff_key_list:
                    diff_list = []
                    existing_path_xml_list = list(map(str, biological_models_dict_from_json["path_xml"]))
                    new_path_xml_list = list(map(str, self.biological_models_dict["path_xml"]))
                    new_xml_list = list(set(existing_path_xml_list) ^ set(new_path_xml_list))
                    # warning and copy to save AppData folder
                    if new_xml_list:
                        new_biology_models_save_folder = os.path.join(self.user_pref_biology_models_save,
                                                                      strftime("%d_%m_%Y_at_%H_%M_%S"))
                        if not os.path.isdir(new_biology_models_save_folder):
                            os.mkdir(new_biology_models_save_folder)
                        for new_xml_element in new_xml_list:
                            # xml
                            if os.path.exists(new_xml_element):
                                sh_copy(new_xml_element, new_biology_models_save_folder)
                                # is image file specified in xml file ?
                                information_model_dict = bio_info_mod.get_biomodels_informations_for_database(new_xml_element)
                                if information_model_dict["path_img"] is not None:
                                    if os.path.exists(information_model_dict["path_img"]):
                                        sh_copy(information_model_dict["path_img"], new_biology_models_save_folder)
                                    else:
                                        information_model_dict["path_img"] = None
                                # append
                                diff_list.append(os.path.basename(new_xml_element))
                        self.diff_list = ", ".join(diff_list) + " added by user."

                # deleted xml curve (from AppData user)
                if "xml" in diff_key_inverse_list and "user" in diff_key_inverse_list:
                    diff_inverse_list = []
                    existing_path_xml_list = list(map(str, biological_models_dict_from_json["path_xml"]))
                    new_path_xml_list = list(map(str, self.biological_models_dict["path_xml"]))
                    removed_xml_list = list(set(existing_path_xml_list) ^ set(new_path_xml_list))
                    # warning
                    if removed_xml_list:
                        for new_xml_element in removed_xml_list:
                            diff_inverse_list.append(os.path.basename(new_xml_element))
                        self.diff_list = ", ".join(diff_inverse_list) + " removed by user."
            else:
                self.diff_list = diff_key_list

            self.create_biology_models_json()

    def load_biology_models_json(self):
        # load_biology_models_json
        with open(self.user_pref_biology_models_db_file, "r") as read_file:
            biological_models_dict = json.load(read_file)
        return biological_models_dict


user_preferences = UserPreferences()
user_preferences.create_user_preferences_structure()
#print("create instance", user_preferences)