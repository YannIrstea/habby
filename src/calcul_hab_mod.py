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
import numpy as np
import sys
from io import StringIO
from scipy.interpolate import interp1d, griddata
from pandas import DataFrame

import src.tools_mod
from src import hdf5_mod
from src import bio_info_mod
from src.project_properties_mod import load_project_properties
from src.substrate_mod import sandre_to_cemagref_array, sandre_to_cemagref_by_percentage_array, pref_substrate_dominant_from_percentage_description, pref_substrate_coarser_from_percentage_description
from src.tools_mod import get_translator
from src.variable_unit_mod import HydraulicVariableUnitManagement, HydraulicVariable


def calc_hab_and_output(hab_filename, animal_variable_list, progress_value, q=[], print_cmd=False, project_preferences={}):
    """
    This function calculates the habitat and create the outputs for the habitat calculation. The outputs are: text
    output (spu and cells by cells), shapefile, paraview files, one 2d figure by time step. The 1d figure
    is done on the main thread as we want to show it to the user on the GUI. This function is called by calc_hab_GUI.py
    on a second thread to minimize the freezing on the GUI.

    :param hab_filename: the name of the hdf5 with the results
    :param path_hdf5: the path to the merged file
    :param pref_file_list: the name of the xml biological data
    :param stage_list: the stage chosen (youngs, adults, etc.). List with the same length as bio_names.
    :param code_alternative_list: the name of the chosen fish
    :param name_fish_sh: In a shapefile, max 8 character for the column name. Hence, a modified name_fish is needed.
    :param run_choice: dict with two lists : one for hyd opt and second for sub opt
    :param path_bio: The path to the biological folder (with all files given in bio_names)
    :param path_txt: the path where to save the text file
    :param path_shp: the path where to save shapefile
    :param path_para: the path where to save paraview output
    :param path_im: the path where to save the image
    :param path_im_bio: the path where are the image of the fish
    :param q: used in the second thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param project_preferences: the options to crete the figure if save_fig1d is True
    :param xmlfiles: the list of the xml file (only useful to get the preference curve report, so not used by habby_cmd)

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line. We make the switch here.
    """
    # print output
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # get translation
    qt_tr = get_translator(project_preferences['path_prj'])

    # progress
    progress_value.value = 10

    # if exists
    if not os.path.exists(os.path.join(project_preferences['path_prj'], "hdf5", hab_filename)):
        print('Error: ' + qt_tr.translate("calcul_hab_mod", "The specified file : " + hab_filename + " don't exist."))
        if q and not print_cmd:
            q.put(mystdout)
            return
        else:
            return

    # load data and get variable to compute
    hdf5 = hdf5_mod.Hdf5Management(os.path.dirname(os.path.join(project_preferences['path_prj'], "hdf5")), hab_filename)
    hdf5.load_hdf5_hab(user_target_list=animal_variable_list)
    hdf5.data_2d.hvum = hdf5.hvum

    # progress
    progress_value.value = 20

    warning_range_list = []

    # progress
    delta_reach = (90 - progress_value.value) / hdf5.data_2d.reach_num

    # for each reach
    for reach_num in range(hdf5.data_2d.reach_num):
        # progress
        delta_unit = delta_reach / hdf5.data_2d.unit_num
        # for each unit
        for unit_num in range(hdf5.data_2d.unit_num):
            # progress
            delta_animal = delta_unit / len(animal_variable_list)
            # for each animal
            for animal_variable in animal_variable_list:
                # information_model_dict
                information_model_dict = bio_info_mod.get_biomodels_informations_for_database(animal_variable.pref_file)
                # load bio data
                pref_height, pref_vel, pref_sub, sub_code, code_fish, name_fish, stade_bios = bio_info_mod.read_pref(animal_variable.pref_file,
                                                                                                                       animal_variable.aquatic_animal_type)
                # search stage
                stage_index = None
                for i, stade_bio in enumerate(stade_bios):
                    if animal_variable.stage == stade_bio:
                        stage_index = i

                # fish case
                if animal_variable.aquatic_animal_type == "fish":
                    pref_height = pref_height[stage_index]
                    pref_vel = pref_vel[stage_index]
                    pref_sub = np.array(pref_sub[stage_index])

                    # if the last value ends in 0 then change the corresponding value to x at 100 m
                    if animal_variable.model_type != 'bivariate suitability index models':
                        if pref_height[1][-1] == 0:
                            #print("Warning: " + qt_tr.translate("calcul_hab_mod", "Last x height value set to 100m : ") + name_fish + " " + stade_bio)
                            pref_height[0].append(1000)
                            pref_height[1].append(0)
                        if pref_vel[1][-1] == 0:
                            #print("Warning: " + qt_tr.translate("calcul_hab_mod", "Last x velocity value set to 100m/s : ") + name_fish + " " + stade_bio)
                            pref_vel[0].append(1000)
                            pref_vel[1].append(0)

                # invertebrate case
                elif animal_variable.aquatic_animal_type == "invertebrate":
                    pref_height = pref_height[stage_index]
                    if pref_height[-1] == 0:
                        #print("Warning: " + qt_tr.translate("calcul_hab_mod", "Last x height value set to 100m :") + name_fish + stade_bio)
                        pref_height[-1] = 100

                s_pref_c = 1

                if animal_variable.aquatic_animal_type == "invertebrate":
                    warning_shearstress_list = []

                height_t = hdf5.data_2d[reach_num][unit_num]["mesh"]["data"][hdf5.data_2d.hvum.h.name]
                vel_t = hdf5.data_2d[reach_num][unit_num]["mesh"]["data"][hdf5.data_2d.hvum.v.name]
                if animal_variable.aquatic_animal_type == "invertebrate":
                    shear_stress_t = hdf5.data_2d[reach_num][unit_num]["mesh"]["data"][
                        hdf5.data_2d.hvum.shear_stress.name]
                ikle_t = hdf5.data_2d[reach_num][unit_num]["mesh"]["tin"]
                area = hdf5.data_2d[reach_num][unit_num]["mesh"]["data"]["area"]

                # univariate
                if animal_variable.model_type != 'bivariate suitability index models':
                    # HEM
                    if animal_variable.aquatic_animal_type == "invertebrate":
                        """ HEM pref """
                        # get pref x and y
                        pref_shearstress = pref_height
                        pref_values = pref_sub[0]
                        # nterp1d(...... kind='previous') for values <0.0771
                        pref_shearstress = [0.0] + pref_shearstress
                        pref_values = pref_values + [pref_values[-1]]
                        # check range suitability VS range input data
                        if max(pref_shearstress) < np.nanmax(shear_stress_t):
                            warning_range_list.append(unit_num)
                        # hem_interp_function
                        hem_interp_f = interp1d(pref_shearstress, pref_values,
                                                kind='previous', bounds_error=False, fill_value=np.nan)
                        with np.errstate(divide='ignore', invalid='ignore'):
                            vh = hem_interp_f(shear_stress_t.flatten())
                        if any(np.isnan(shear_stress_t)):
                            warning_shearstress_list.append(unit_num)

                    # fish case
                    if animal_variable.aquatic_animal_type == "fish":
                        """ hydraulic pref """
                        # get H pref value
                        if animal_variable.hyd_opt in ["HV", "H"]:
                            if max(pref_height[
                                       0]) < height_t.max():  # check range suitability VS range input data
                                warning_range_list.append(unit_num)
                            h_pref_c = np.interp(height_t, pref_height[0], pref_height[1], left=np.nan,
                                                 right=np.nan)

                        # get V pref value
                        if animal_variable.hyd_opt in ["HV", "V"]:
                            if max(pref_vel[
                                       0]) < vel_t.max():  # check range suitability VS range input data
                                warning_range_list.append(unit_num)
                            v_pref_c = np.interp(vel_t, pref_vel[0], pref_vel[1], left=np.nan, right=np.nan)

                        """ substrate pref """
                        # Neglect
                        if animal_variable.sub_opt == "Neglect":
                            s_pref_c = np.array([1] * ikle_t.shape[0])
                        else:
                            # convert classification code sandre to cemagref
                            # TODO: no input data conversion if pref curve is sandre or antoher

                            sub_t = np.empty(shape=(ikle_t.shape[0], len(
                                hdf5.data_2d.hvum.hdf5_and_computable_list.hdf5s().subs().names())),
                                             dtype=np.int64)
                            for sub_class_num, sub_class_name in enumerate(
                                    hdf5.data_2d.hvum.hdf5_and_computable_list.hdf5s().subs().names()):
                                sub_t[:, sub_class_num] = hdf5.data_2d[reach_num][unit_num]["mesh"]["data"][
                                    sub_class_name]

                            if hdf5.data_description["sub_classification_code"] == "Sandre":
                                if hdf5.data_description["sub_classification_method"] == "percentage":
                                    sub_t = sandre_to_cemagref_by_percentage_array(sub_t)
                                else:
                                    sub_t = sandre_to_cemagref_array(sub_t)
                            # Coarser-Dominant
                            if animal_variable.sub_opt == "Coarser-Dominant":
                                if hdf5.data_description["sub_classification_method"] == "percentage":
                                    s_pref_c_coarser = pref_substrate_coarser_from_percentage_description(
                                        pref_sub[1], sub_t)
                                    s_pref_c_dom = pref_substrate_dominant_from_percentage_description(
                                        pref_sub[1], sub_t)
                                    s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                                elif hdf5.data_description["sub_classification_method"] == "coarser-dominant":
                                    s_pref_c_coarser = pref_sub[1][sub_t[:, 0] - 1]
                                    s_pref_c_dom = pref_sub[1][sub_t[:, 1] - 1]
                                    s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                            # Coarser
                            elif animal_variable.sub_opt == "Coarser":
                                if hdf5.data_description["sub_classification_method"] == "percentage":
                                    s_pref_c = pref_substrate_coarser_from_percentage_description(
                                        pref_sub[1], sub_t)
                                elif hdf5.data_description["sub_classification_method"] == "coarser-dominant":
                                    s_pref_c = pref_sub[1][sub_t[:, 0] - 1]
                            # Dominant
                            elif animal_variable.sub_opt == "Dominant":
                                if hdf5.data_description["sub_classification_method"] == "percentage":
                                    s_pref_c = pref_substrate_dominant_from_percentage_description(
                                        pref_sub[1], sub_t)
                                elif hdf5.data_description["sub_classification_method"] == "coarser-dominant":
                                    s_pref_c = pref_sub[1][sub_t[:, 1] - 1]
                            # Percentage
                            else:
                                if information_model_dict["substrate_type"][stage_index] == "Dominant":  # dominant curve
                                    s_pref_c = pref_substrate_dominant_from_percentage_description(
                                        pref_sub[1], sub_t)
                                if information_model_dict["substrate_type"][stage_index] == "Dominant":  # dominant curve
                                    s_pref_c = pref_substrate_coarser_from_percentage_description(
                                        pref_sub[1], sub_t)

                        """ compute habitat value """
                        try:
                            # HV
                            if "H" in animal_variable.hyd_opt and "V" in animal_variable.hyd_opt:
                                vh = h_pref_c * v_pref_c * s_pref_c
                                vh[h_pref_c == 0] = 0
                                vh[v_pref_c == 0] = 0
                                vh[s_pref_c == 0] = 0
                            # H
                            elif "H" in animal_variable.hyd_opt:
                                vh = h_pref_c * s_pref_c
                                vh[h_pref_c == 0] = 0
                                vh[s_pref_c == 0] = 0
                            # V
                            elif "V" in animal_variable.hyd_opt:
                                vh = v_pref_c * s_pref_c
                                vh[v_pref_c == 0] = 0
                                vh[s_pref_c == 0] = 0
                            # Neglect
                            else:
                                vh = s_pref_c
                        except ValueError:
                            print('Error: ' + qt_tr.translate("calcul_hab_mod",
                                                              'One time step misses substrate, velocity or water height value.'))
                            vh = [-99]

                # bivariate suitability index models
                else:
                    # height data
                    if max(pref_height) < height_t.max():  # check range suitability VS range input data
                        warning_range_list.append(unit_num)
                    # velocity data
                    if max(pref_vel) < vel_t.max():  # check range suitability VS range input data
                        warning_range_list.append(unit_num)

                    # prep data
                    pref_vel = np.array(pref_vel)
                    pref_height = np.array(pref_height)
                    pref_xy_repeated = []
                    for row in range(len(pref_height)):
                        x_coord = np.repeat(pref_height[row], len(pref_vel))
                        y_coord = pref_vel
                        pref_xy_repeated.extend(list(zip(x_coord, y_coord)))
                    pref_xy_repeated = np.array(pref_xy_repeated)
                    xy_input = np.dstack((vel_t, height_t))

                    # calc from model points
                    vh = griddata(pref_xy_repeated, pref_sub, xy_input, method='linear')[0]

                spu_reach = np.nansum(vh * area)

                # append
                if not "hv_data" in hdf5.data_2d[reach_num][unit_num]["mesh"].keys():
                    hdf5.data_2d[reach_num][unit_num]["mesh"]["hv_data"] = DataFrame()
                hdf5.data_2d[reach_num][unit_num]["mesh"]["hv_data"][animal_variable.name] = vh
                animal_variable.spu = spu_reach

                # WARNINGS
                if warning_range_list:
                    warning_range_list = list(set(warning_range_list))
                    warning_range_list.sort()
                    # get unit name
                    unit_names = []
                    for warning_unit_num in warning_range_list:
                        unit_names.append(hdf5.data_description["hyd_unit_list"][reach_num][warning_unit_num])
                    print(f"Warning: " + qt_tr.translate("calcul_hab_mod",
                                                         "Unknown habitat values produced for ") + name_fish + qt_tr.translate(
                        "calcul_hab_mod",
                        ", his suitability curve range is not sufficient according to the hydraulics of unit(s) : ") +
                          ", ".join(str(x) for x in unit_names) + qt_tr.translate("calcul_hab_mod",
                                                                                  " of reach : ") + hdf5.data_description[
                              "hyd_reach_list"])
                # WARNINGS HEM
                if animal_variable.aquatic_animal_type == "invertebrate":
                    if warning_shearstress_list:
                        warning_shearstress_list.sort()
                        # get unit name
                        unit_names = []
                        for warning_unit_num in warning_shearstress_list:
                            unit_names.append(hdf5.data_description["hyd_unit_list"][reach_num][warning_unit_num])
                        print(f"Warning: " + qt_tr.translate("calcul_hab_mod",
                                                             "Unknown habitat values produced for ") + name_fish + qt_tr.translate(
                            "calcul_hab_mod", ", the shear stress data present unknown values in unit(s) : ") +
                              ", ".join(str(x) for x in unit_names) + qt_tr.translate("calcul_hab_mod",
                                                                                      " of reach : ") +
                              hdf5.data_description["hyd_reach_list"])

                # progress
                progress_value.value = int(progress_value.value + delta_animal)

    # progress
    progress_value.value = 90

    # saving hdf5 data of the habitat value
    hdf5.add_fish_hab(animal_variable_list)

    # copy xml curves to input project folder
    names = []
    paths = []
    for i in range(len(run_choice["pref_file_list"])):
        if "INRAE_EDF_OFB" in os.path.dirname(run_choice["pref_file_list"][i]):  # user case
            name_xml = os.path.basename(run_choice["pref_file_list"][i])
            name_png = os.path.splitext(os.path.basename(run_choice["pref_file_list"][i]))[0] + ".png"
            names.append(name_xml)
            names.append(name_png)
            path = os.path.dirname(run_choice["pref_file_list"][i])
            paths.append(path)
            paths.append(path)
    if names:
        if not os.path.exists(os.path.join(project_preferences["path_input"], "user_models")):
            os.makedirs(os.path.join(project_preferences["path_input"], "user_models"))
        src.tools_mod.copy_files(names, paths, os.path.join(hdf5.path_prj, "input", "user_models"))

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return

