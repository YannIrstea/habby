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
import shutil
import json
import sys
from platform import system as operatingsystem

operatingsystem_str = operatingsystem()

from src.hydraulic_results_manager_mod import HydraulicModelInformation
from src.variable_unit_mod import HydraulicVariableUnitManagement


def create_default_project_properties_dict(all_export_enabled=False):
    """
    This function creates the default dictionnary of project user preferences.
    """
    # init
    project_preferences = dict()

    # general
    project_preferences['name_prj'] = ""
    project_preferences['path_prj'] = ""
    project_preferences['path_last_file_loaded'] = ""
    project_preferences['file_log'] = ""
    project_preferences['file_script'] = ""
    project_preferences['file_restart'] = ""
    project_preferences['save_log'] = True
    project_preferences['user_name'] = ""
    project_preferences['description'] = ""
    project_preferences['version_habby'] = ""
    project_preferences['path_bio'] = os.path.join("biology", "models")
    project_preferences['path_input'] = 'input'
    project_preferences['path_hdf5'] = 'hdf5'
    project_preferences['path_figure'] = os.path.join('output', 'figures')
    project_preferences['path_text'] = os.path.join('output', 'text')
    project_preferences['path_gis'] = os.path.join('output', 'GIS')
    project_preferences['path_3d'] = os.path.join('output', '3D')
    project_preferences['HS_input_class'] = dict(path="",
                                                 file="")

    project_preferences['min_height_hyd'] = 0.001  # node mesh minimum water height consider like dry
    project_preferences['cut_mesh_partialy_dry'] = True  # cut of not mesh partialy wet
    project_preferences['erase_id'] = True  # erase file (hdf5, outputs) if exist. if not set date/hour in filename
    project_preferences['copy_input_files'] = True
    project_preferences['mode'] = ""  # GUI or CLI

    # output (first element list == for .hyd and second element list == for .hab)
    project_preferences['mesh_whole_profile'] = [all_export_enabled, all_export_enabled]  # shapefile mesh whole profile
    project_preferences['point_whole_profile'] = [all_export_enabled, all_export_enabled]  # shapefile point whole profile
    project_preferences['mesh_units'] = [all_export_enabled, all_export_enabled]  # shapefile mesh by unit
    project_preferences['point_units'] = [all_export_enabled, all_export_enabled]  # shapefile point by unit
    project_preferences['elevation_whole_profile'] = [all_export_enabled, all_export_enabled]  # mesh .stl of topography whole profile (vertical_exaggeration)
    project_preferences['variables_units'] = [all_export_enabled, all_export_enabled]  # mesh .pvd and .vtu by unit (vertical_exaggeration)
    project_preferences['habitat_text'] = [False, True]  # .txt with detail values by mesh
    project_preferences['detailled_text'] = [all_export_enabled, all_export_enabled]  # .txt with detail values by mesh
    project_preferences['fish_information'] = [all_export_enabled, all_export_enabled]  # image of fish informations
    project_preferences['vertical_exaggeration'] = 10  # paraview vertical exageration
    project_preferences['pvd_variable_z'] = HydraulicVariableUnitManagement().level.name_gui

    # figures
    project_preferences['height'] = 11.2  # cm
    project_preferences['width'] = 16  # cm
    project_preferences['color_map'] = 'jet'
    if operatingsystem_str == "Linux":
        project_preferences["font_family"] = "DejaVu Sans"
    else:
        project_preferences["font_family"] = "Arial"
    project_preferences['font_size'] = 9
    project_preferences['line_width'] = 1
    project_preferences['grid'] = False  # grid on plot
    project_preferences['format'] = ".png"  # png, pdf
    project_preferences['resolution'] = 300  # dpi
    project_preferences['fish_name_type'] = 0  # latin_name, french, english, code_alternative
    project_preferences['marker'] = True  # Add point to line plot
    project_preferences['hs_axe_mod'] = 1  # hs axe mod visualisation

    # gui
    project_preferences['physic_tabs'] = False
    project_preferences['stat_tabs'] = False
    project_preferences['language'] = 0  # 0 english, 1 french
    project_preferences['selected_aquatic_animal_list'] = dict(selected_aquatic_animal_list=[],
                                                                hydraulic_mode_list=[],
                                                                substrate_mode_list=[])
    project_preferences['bio_model_explorer_selection'] = dict()

    # data
    hydraulic_model_information = HydraulicModelInformation()
    for attribute_model in hydraulic_model_information.attribute_models_list:
        project_preferences[attribute_model] = dict(path="", hdf5=[])

    project_preferences['STATHAB'] = dict(path="", hdf5=[])
    project_preferences['ESTIMHAB'] = dict(path="", hdf5=[])

    project_preferences['SUBSTRATE'] = dict(path="", hdf5=[])
    project_preferences['HABITAT'] = dict(path="", hdf5=[])

    return project_preferences


def create_project_structure(path_prj, save_log, version_habby, user_name, description, mode="GUI"):
    """
    create_project_structure
    :param path_prj:
    :param save_log:
    :param version_habby:
    :param user_name:
    :param description:
    :param mode:
    :return:
    """
    # create_default_project_properties_dict
    project_preferences = create_default_project_properties_dict()

    # check if folder exist
    if not os.path.exists(path_prj):
        os.makedirs(path_prj)

    # get name
    name_prj = os.path.basename(path_prj)

    # update dict
    project_preferences["name_prj"] = name_prj
    project_preferences["path_prj"] = path_prj
    project_preferences["save_log"] = save_log
    project_preferences["file_log"] = os.path.join(path_prj, name_prj + '.log')
    if operatingsystem_str == "Linux":
        script_ext = ".sh"
    elif operatingsystem_str == "Windows":
        script_ext = ".bat"
    else:
        script_ext = ".sh"

    project_preferences["file_script"] = os.path.join(path_prj, name_prj + script_ext)
    project_preferences["file_restart"] = os.path.join(path_prj, 'restart_' + name_prj + '.log')
    project_preferences["version_habby"] = version_habby
    project_preferences["user_name"] = user_name
    project_preferences["description"] = description
    project_preferences["path_input"] = os.path.join(path_prj, project_preferences['path_input'])  # path input
    project_preferences["path_hdf5"] = os.path.join(path_prj, project_preferences['path_hdf5'])  # path hdf5
    project_preferences["path_figure"] = os.path.join(path_prj, project_preferences['path_figure'])  # path figures
    project_preferences["path_text"] = os.path.join(path_prj, project_preferences['path_text'])  # path text output
    project_preferences["path_gis"] = os.path.join(path_prj, project_preferences['path_gis'])  # path_gis
    project_preferences["path_3d"] = os.path.join(path_prj, project_preferences['path_3d'])  # path_3d
    project_preferences["mode"] = mode

    # create .habby project file
    save_project_properties(path_prj, project_preferences)

    # create the log files by copying the existing "basic" log files (log0.txt and restart_log0.txt)
    if name_prj != '':
        # log
        shutil.copy(os.path.join('files_dep', 'log0.txt'), os.path.join(path_prj, name_prj + '.log'))
        # restart
        shutil.copy(os.path.join('files_dep', 'restart_log0.txt'), os.path.join(path_prj,
                                                                              'restart_' + name_prj +
                                                                              '.log'))
        # script
        path_prj_script = path_prj + "_restarted"
        if sys.argv[0][-3:] == ".py":
            cmd_str = '"' + sys.executable + '" "' + sys.argv[0] + '"' + ' CREATE_PROJECT path_prj="' + path_prj_script + '"'
        else:
            cmd_str = '"' + sys.executable + '"' + ' CREATE_PROJECT path_prj="' + path_prj_script + '"'

        with open(project_preferences["file_script"], "w", encoding='utf8') as myfile:
            myfile.write(cmd_str + "\n")

    # create a default directory for the figures and the hdf5
    if not os.path.exists(project_preferences["path_input"]):
        os.makedirs(project_preferences["path_input"])
    # if not os.path.exists(os.path.join(project_preferences["path_input"], "user_models")):
    #     os.makedirs(os.path.join(project_preferences["path_input"], "user_models"))
    if not os.path.exists(project_preferences["path_hdf5"]):
        os.makedirs(project_preferences["path_hdf5"])
    if not os.path.exists(os.path.join(path_prj, 'output')):
        os.makedirs(os.path.join(path_prj, 'output'))
    if not os.path.exists(project_preferences["path_figure"]):
        os.makedirs(project_preferences["path_figure"])
    if not os.path.exists(project_preferences["path_text"]):
        os.makedirs(project_preferences["path_text"])
    if not os.path.exists(project_preferences["path_gis"]):
        os.makedirs(project_preferences["path_gis"])
    if not os.path.exists(project_preferences["path_3d"]):
        os.makedirs(project_preferences["path_3d"])

    # create the concurrency file
    filenamec = os.path.join(os.path.join(path_prj, 'hdf5'), 'check_concurrency.txt')
    if os.path.isdir(os.path.join(path_prj, 'hdf5')):
        with open(filenamec, 'wt') as f:
            f.write('open')


def save_project_properties(path_prj, project_preferences):
    name_prj = os.path.basename(path_prj)

    with open(os.path.join(path_prj, name_prj + '.habby'), "w") as write_file:
        json.dump(project_preferences, write_file, indent=4)


def load_project_properties(path_prj):
    """
    This function loads the figure option saved in the xml file and create a dictionnary will be given to the functions
    which create the figures to know the different options chosen by the user. If the options are not written, this
    function uses data by default which are in the fonction create_default_project_properties_dict().

    :param path_prj: the path to the xml project file
    :param name_prj: the name to this file
    :return: the dictionary containing the figure options
    """
    # name_prj
    name_prj = os.path.basename(path_prj)
    project_file_abs_path = os.path.join(path_prj, name_prj + '.habby')

    if not os.path.isfile(project_file_abs_path) and name_prj != '':  # no project exists
        pass
    elif name_prj == '':
        pass
    elif not os.path.isfile(project_file_abs_path):  # the project is not found
        print('Warning: No project file (.habby) found.\n')
    else:
        with open(project_file_abs_path, "r") as read_file:
            project_preferences = json.load(read_file)

    # check if project move
    if path_prj != project_preferences["path_prj"]:  # update all path
        project_preferences["name_prj"] = name_prj
        project_preferences["path_prj"] = path_prj
        project_preferences["file_log"] = os.path.join(path_prj, name_prj + '.log')
        if operatingsystem_str == "Linux":
            script_ext = ".sh"
        elif operatingsystem_str == "Windows":
            script_ext = ".bat"
        else:
            script_ext = ".sh"
        project_preferences["file_script"] = os.path.join(path_prj, name_prj + script_ext)
        project_preferences["file_restart"] = os.path.join(path_prj, 'restart_' + name_prj + '.log')
        project_preferences["path_input"] = os.path.join(path_prj, 'input')  # path input
        project_preferences["path_hdf5"] = os.path.join(path_prj, 'hdf5')  # path hdf5
        project_preferences["path_figure"] = os.path.join(path_prj, 'output', 'figures')  # path figures
        project_preferences["path_text"] = os.path.join(path_prj, 'output', 'text')  # path text output
        project_preferences["path_gis"] = os.path.join(path_prj, 'output', 'GIS')  # path_gis
        project_preferences["path_3d"] = os.path.join(path_prj, 'output', '3D')  # path_3d

    return project_preferences


def change_specific_properties(path_prj, preference_names, preference_values):
    """
    :param path_prj: path_prj
    :param preference_names: list of preferences names
    :param preference_values: list of preferences values
    """
    # load_project_properties
    project_preferences = load_project_properties(path_prj)

    # change value
    for preference_name, preference_value in zip(preference_names, preference_values):
        project_preferences[preference_name] = preference_value

    # save_project_properties
    save_project_properties(path_prj, project_preferences)


def load_specific_properties(path_prj, preference_names):
    """
    load
    :param path_prj: path_prj
    :param preference_names: list of preferences names
    :return: preference_value : list of preferences values
    """
    # load_project_properties
    project_preferences = load_project_properties(path_prj)

    # load values
    preference_value = []
    for preference_name in preference_names:
        try:
            preference_value.append(project_preferences[preference_name])
        except KeyError:
            print("Error: Actual project must be deleted because it is from an older version of HABBY. " + preference_name + " have been set to default value. .")
            project_preferences_default = create_default_project_properties_dict()
            preference_value = project_preferences_default[preference_name]
    return preference_value


def enable_disable_all_exports(path_prj, enabled=False):
    available_export_list = ["mesh_whole_profile",  # GPKG
                             "point_whole_profile",  # GPKG
                             "mesh_units",  # GPKG
                             "point_units",  # GPKG
                             "elevation_whole_profile",  # stl
                             "variables_units",  # PVD
                             "detailled_text",  # txt
                             "fish_information"]

    # load_project_properties
    project_preferences = load_project_properties(path_prj)

    # change value
    for preference_name in available_export_list:
        project_preferences[preference_name] = [enabled, enabled]

    # save_project_properties
    save_project_properties(path_prj, project_preferences)

