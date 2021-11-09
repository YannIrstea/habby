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
import sys
from io import StringIO
from time import sleep
import numpy as np
from scipy.interpolate import interp1d, griddata

from src.hdf5_mod import Hdf5Management
from src.bio_info_mod import read_pref, copy_or_not_user_pref_curve_to_input_folder
from src.substrate_mod import sandre_to_cemagref_by_percentage_array, sandre_to_cemagref_array, \
    pref_substrate_coarser_from_percentage_description, pref_substrate_dominant_from_percentage_description
from src.translator_mod import get_translator


def calc_hab_and_output(hab_filename, animal_variable_list, progress_value, q=[], print_cmd=False,
                        project_preferences={}):
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
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    # load data and get variable to compute
    hdf5_path = os.path.dirname(os.path.join(project_preferences['path_prj'], "hdf5"))
    hdf5 = Hdf5Management(hdf5_path, hab_filename, new=False, edit=True)
    hdf5.load_hdf5(user_target_list=animal_variable_list)

    # progress
    delta_animal = 80 / len(animal_variable_list)

    # for each animal
    for animal in animal_variable_list:
        """ get bio model """
        # load bio data
        information_model_dict = read_pref(animal.pref_file)
        # search stage
        stage_index = None
        for i, stade_bio in enumerate(information_model_dict["stage_and_size"]):
            if animal.stage == stade_bio:
                stage_index = i

        # model_var
        model_var = information_model_dict["hab_variable_list"][stage_index]

        if animal.model_type == 'univariate suitability index curves':
            if "HEM" in information_model_dict["hydraulic_type_available"][stage_index]:
                pref_hem_data = model_var.variable_list.get_from_name(hdf5.data_2d.hvum.shear_stress.name).data
                if pref_hem_data[0][-1] == 0:
                    pref_hem_data[0][-1] = 1000
            else:
                if hdf5.data_2d.hvum.h.name in model_var.variable_list.names():
                    pref_height = model_var.variable_list.get_from_name(hdf5.data_2d.hvum.h.name).data
                    # if the last value ends in 0 then change the corresponding value to x at 100 m
                    if pref_height[1][-1] == 0:
                        pref_height[0].append(1000)
                        pref_height[1].append(0)
                if hdf5.data_2d.hvum.v.name in model_var.variable_list.names():
                    pref_vel = model_var.variable_list.get_from_name(hdf5.data_2d.hvum.v.name).data
                    # if the last value ends in 0 then change the corresponding value to x at 100 m
                    if pref_vel[1][-1] == 0:
                        pref_vel[0].append(100)
                        pref_vel[1].append(0)
                if model_var.variable_list.subs():
                    pref_sub = np.array(model_var.variable_list.get_from_name(model_var.variable_list.subs()[0].name).data)

        else:  # bivariate
            pref_height = model_var.variable_list.get_from_name(hdf5.data_2d.hvum.h.name).data
            pref_vel = model_var.variable_list.get_from_name(hdf5.data_2d.hvum.v.name).data

        # progress
        delta_reach = delta_animal / hdf5.data_2d.reach_number

        # for each reach
        for reach_number in range(hdf5.data_2d.reach_number):
            warning_shearstress_list = []
            warning_range_list = []
            # progress
            delta_unit = delta_reach / hdf5.data_2d[reach_number].unit_number

            # for each unit
            for unit_number in range(hdf5.data_2d[reach_number].unit_number):

                """ get 2d data """
                height_t = hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5.data_2d.hvum.h.name].to_numpy()
                vel_t = hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5.data_2d.hvum.v.name].to_numpy()

                if animal.aquatic_animal_type in {"invertebrate", "crustacean"} and "HEM" in information_model_dict["hydraulic_type_available"][stage_index]:
                    shear_stress_t = hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5.data_2d.hvum.shear_stress.name].to_numpy()
                ikle_t = hdf5.data_2d[reach_number][unit_number]["mesh"]["tin"]
                area = hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5.data_2d.hvum.area.name]

                """ compute habitat """
                # univariate
                if animal.model_type == 'univariate suitability index curves':
                    if "HEM" in information_model_dict["hydraulic_type_available"][stage_index]:
                        """ HEM pref """
                        # get pref x and y
                        pref_shearstress = pref_hem_data[0]
                        pref_values = pref_hem_data[2]
                        # nterp1d(...... kind='previous') for values <0.0771
                        pref_shearstress = [0.0] + pref_shearstress
                        pref_values = pref_values + [pref_values[-1]]
                        # check range suitability VS range input data
                        if max(pref_shearstress) < np.nanmax(shear_stress_t):
                            warning_range_list.append(unit_number)
                        # hem_interp_function
                        hem_interp_f = interp1d(pref_shearstress, pref_values,
                                                kind='previous', bounds_error=False, fill_value=np.nan)
                        with np.errstate(divide='ignore', invalid='ignore'):
                            hv = hem_interp_f(shear_stress_t.flatten())
                        if any(np.isnan(shear_stress_t)):
                            warning_shearstress_list.append(unit_number)
                    else:
                        """ hydraulic pref """
                        if animal.hyd_opt in ["HV", "H"]:  # get H pref value
                            if max(pref_height[0]) < height_t.max():  # check range suitability VS range input data
                                warning_range_list.append(unit_number)
                            h_pref_c = np.interp(height_t, pref_height[0], pref_height[1], left=np.nan,
                                                 right=np.nan)
                        if animal.hyd_opt in ["HV", "V"]:  # get V pref value
                            if max(pref_vel[0]) < vel_t.max():  # check range suitability VS range input data
                                warning_range_list.append(unit_number)
                            v_pref_c = np.interp(vel_t, pref_vel[0], pref_vel[1], left=np.nan, right=np.nan)

                        """ substrate pref """
                        # Neglect
                        if animal.sub_opt == "Neglect":
                            s_pref_c = np.array([1] * ikle_t.shape[0])
                        else:
                            # conca substrate data_2d to on numpy array
                            sub_t = np.empty(shape=(ikle_t.shape[0], len(
                                hdf5.data_2d.hvum.hdf5_and_computable_list.hdf5s().subs().names())),
                                             dtype=np.int64)
                            for sub_class_num, sub_class_name in enumerate(
                                    hdf5.data_2d.hvum.hdf5_and_computable_list.hdf5s().subs().names()):
                                sub_t[:, sub_class_num] = hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][
                                    sub_class_name]

                            # substrate_classification_code
                            hsi_sub_classification_code = model_var.variable_list.get_from_name(model_var.variable_list.subs()[0].name).unit
                            data_2d_sub_classification_code = hdf5.data_2d.hvum.hdf5_and_computable_list.hdf5s().subs()[0].unit

                            # # sub_classification_code conversion ?
                            # print("------------------------")
                            # print("Warning: data_2d", data_2d_sub_classification_code)
                            # print("Warning: hsi", hsi_sub_classification_code)
                            if data_2d_sub_classification_code == "Sandre" and hsi_sub_classification_code == "Cemagref":
                                # convert substrate data_2d to Cemagref
                                if len(hdf5.data_2d.hvum.hdf5_and_computable_list.hdf5s().subs()) > 2:  # percentage
                                    sub_t = sandre_to_cemagref_by_percentage_array(sub_t)
                                else:
                                    sub_t = sandre_to_cemagref_array(sub_t)
                            elif data_2d_sub_classification_code == "Cemagref" and hsi_sub_classification_code == "Sandre":
                                # convert substrate hsi to Cemagref
                                pref_sub = sandre_to_cemagref_by_percentage_array(pref_sub)

                            # Coarser-Dominant
                            if animal.sub_opt == "Coarser-Dominant":
                                if hdf5.data_2d.sub_classification_method == "percentage":
                                    s_pref_c_coarser = pref_substrate_coarser_from_percentage_description(
                                        pref_sub[1], sub_t)
                                    s_pref_c_dom = pref_substrate_dominant_from_percentage_description(
                                        pref_sub[1], sub_t)
                                    s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                                elif hdf5.data_2d.sub_classification_method == "coarser-dominant":
                                    s_pref_c_coarser = pref_sub[1][sub_t[:, 0] - 1]
                                    s_pref_c_dom = pref_sub[1][sub_t[:, 1] - 1]
                                    s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                            # Coarser
                            elif animal.sub_opt == "Coarser":
                                if hdf5.data_2d.sub_classification_method == "percentage":
                                    s_pref_c = pref_substrate_coarser_from_percentage_description(
                                        pref_sub[1], sub_t)
                                elif hdf5.data_2d.sub_classification_method == "coarser-dominant":
                                    s_pref_c = pref_sub[1][sub_t[:, 0] - 1]
                            # Dominant
                            elif animal.sub_opt == "Dominant":
                                if hdf5.data_2d.sub_classification_method == "percentage":
                                    s_pref_c = pref_substrate_dominant_from_percentage_description(
                                        pref_sub[1], sub_t)
                                elif hdf5.data_2d.sub_classification_method == "coarser-dominant":
                                    s_pref_c = pref_sub[1][sub_t[:, 1] - 1]
                            # Percentage
                            else:
                                s_pref_c = np.sum((sub_t / 100) * pref_sub[1], axis=1)

                        """ compute habitat value """
                        try:
                            # HV
                            if "H" in animal.hyd_opt and "V" in animal.hyd_opt:
                                hv = h_pref_c * v_pref_c * s_pref_c
                                hv[h_pref_c == 0] = 0
                                hv[v_pref_c == 0] = 0
                                hv[s_pref_c == 0] = 0
                            # H
                            elif "H" in animal.hyd_opt:
                                hv = h_pref_c * s_pref_c
                                hv[h_pref_c == 0] = 0
                                hv[s_pref_c == 0] = 0
                            # V
                            elif "V" in animal.hyd_opt:
                                hv = v_pref_c * s_pref_c
                                hv[v_pref_c == 0] = 0
                                hv[s_pref_c == 0] = 0
                            # Neglect
                            else:
                                hv = s_pref_c
                        except ValueError:
                            print('Error: ' + qt_tr.translate("calcul_hab_mod",
                                                              'One time step misses substrate, velocity or water height value.'))
                            hv = [-99]

                # bivariate suitability index models
                else:
                    # height data
                    if max(pref_height) < height_t.max():  # check range suitability VS range input data
                        warning_range_list.append(unit_number)
                    # velocity data
                    if max(pref_vel) < vel_t.max():  # check range suitability VS range input data
                        warning_range_list.append(unit_number)

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
                    hv = griddata(pref_xy_repeated, model_var.hv, xy_input, method='linear')[0]

                # compute summary
                wua = np.nansum(hv * area)
                if any(np.isnan(hv)):
                    area = np.sum(hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5.data_2d.hvum.area.name][~np.isnan(hv)])
                    # global_hv = wua / area
                    percent_area_unknown = (1 - (area / hdf5.data_2d[reach_number][unit_number].total_wet_area)) * 100  # next to 1 in top quality, next to 0 is bad or EVIL !
                else:
                    percent_area_unknown = 0.0
                global_hv = wua / hdf5.data_2d[reach_number][unit_number].total_wet_area

                # get data
                hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name] = hv
                if len(animal.wua) < hdf5.data_2d.reach_number:
                    animal.wua.append([])
                    animal.hv.append([])
                    animal.percent_area_unknown.append([])
                animal.wua[reach_number].append(wua)
                animal.hv[reach_number].append(global_hv)
                animal.percent_area_unknown[reach_number].append(percent_area_unknown)

                # progress
                progress_value.value = int(progress_value.value + delta_unit)

            # WARNINGS
            if warning_range_list:
                warning_range_list = list(set(warning_range_list))
                warning_range_list.sort()
                # get unit name
                unit_names = []
                for warning_unit_num in warning_range_list:
                    unit_names.append(hdf5.data_2d.unit_list[reach_number][warning_unit_num])
                print(f"Warning: " + qt_tr.translate("calcul_hab_mod",
                                                     "Unknown habitat values produced for ") + model_var.name + qt_tr.translate(
                    "calcul_hab_mod",
                    ", his suitability curve range is not sufficient according to the hydraulics of unit(s) : ") +
                      ", ".join(str(x) for x in unit_names) + qt_tr.translate("calcul_hab_mod",
                                                                              " of reach : ") +
                      hdf5.data_2d.reach_list[reach_number])
            # WARNINGS HEM
            if animal.aquatic_animal_type in {"invertebrate", "crustacean"}:
                if warning_shearstress_list:
                    warning_shearstress_list.sort()
                    # get unit name
                    unit_names = []
                    for warning_unit_num in warning_shearstress_list:
                        unit_names.append(hdf5.data_2d.unit_list[reach_number][warning_unit_num])
                    print(f"Warning: " + qt_tr.translate("calcul_hab_mod",
                                                         "Unknown habitat values produced for ") + model_var.name + " " + animal.stage + qt_tr.translate(
                        "calcul_hab_mod", ", the shear stress data present unknown values in unit(s) : ") +
                          ", ".join(str(x) for x in unit_names) + qt_tr.translate("calcul_hab_mod",
                                                                                  " of reach : ") +
                          hdf5.data_2d.reach_list[reach_number])

    # progress
    progress_value.value = 90

    # saving hdf5 data of the habitat value
    hdf5.add_fish_hab(animal_variable_list)

    # copy_or_not_user_pref_curve_to_input_folder
    for animal2 in animal_variable_list:
        copy_or_not_user_pref_curve_to_input_folder(animal2, project_preferences)

    # export
    export_dict = dict()
    nb_export = 0
    for key in hdf5.available_export_list:
        if project_preferences[key][1]:
            nb_export += 1
        export_dict[key + "_" + hdf5.extension[1:]] = project_preferences[key][1]

    # export_spu_txt
    hdf5.export_spu_txt()

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0