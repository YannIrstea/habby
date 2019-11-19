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

from src import hdf5_mod
from src import bio_info_mod
from src.project_manag_mod import load_project_preferences
from src.substrate_mod import sandre_to_cemagref_array, sandre_to_cemagref_by_percentage_array, pref_substrate_dominant_from_percentage_description, pref_substrate_coarser_from_percentage_description
from src.tools_mod import get_translator


def calc_hab_and_output(hdf5_file, path_hdf5, pref_list, stages_chosen, fish_names, name_fish_sh, run_choice, path_bio,
                        path_txt, progress_value, q=[], print_cmd=False, project_preferences={},
                        aquatic_animal_type=[], xmlfiles=[]):
    """
    This function calculates the habitat and create the outputs for the habitat calculation. The outputs are: text
    output (spu and cells by cells), shapefile, paraview files, one 2d figure by time step. The 1d figure
    is done on the main thread as we want to show it to the user on the GUI. This function is called by calc_hab_GUI.py
    on a second thread to minimize the freezing on the GUI.

    :param hdf5_file: the name of the hdf5 with the results
    :param path_hdf5: the path to the merged file
    :param pref_list: the name of the xml biological data
    :param stages_chosen: the stage chosen (youngs, adults, etc.). List with the same length as bio_names.
    :param fish_names: the name of the chosen fish
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
    # get translation
    qt_tr = get_translator(project_preferences['path_prj'], project_preferences['name_prj'])
    # progress
    progress_value.value = 10

    # print output
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # load data and get variable to compute
    hdf5 = hdf5_mod.Hdf5Management(os.path.dirname(path_hdf5), hdf5_file)
    hdf5.load_hdf5_hab()
    variable_mesh = ["area", "height", "velocity"]
    HEM_computation = False
    if "invertebrate" in aquatic_animal_type:
        HEM_computation = True
        if int(hdf5.data_description["hyd_model_dimension"]) == 1:
            print("Error: To compute shearstress for invertebrates, the dimension of the hydraulic model "
                  ".hab must be at least 2D.")
            HEM_computation = False
        if not hdf5.data_description["hyd_cuted_mesh_partialy_dry"]:
            print("Warning: To compute the shearstress for invertebrates, the partially dry hydraulic meshes in the "
                  ".hab file must be cuted (option in general preferences). Invertebrate models will not be computed.")
            HEM_computation = False

    if HEM_computation:
        variable_mesh = variable_mesh + ["shear_stress"]
    else:
        # invertebrate indice
        invertebrate_indice = [x for x in range(len(aquatic_animal_type)) if aquatic_animal_type[x] == "invertebrate"]
        # remove invertebrate models
        for i in reversed(invertebrate_indice):
            aquatic_animal_type.pop(i)
            fish_names.pop(i)
            name_fish_sh.pop(i)
            pref_list.pop(i)
            stages_chosen.pop(i)
            run_choice["hyd_opt"].pop(i)
            run_choice["sub_opt"].pop(i)

    # compute_variables
    hdf5.compute_variables(variables_mesh=variable_mesh)

    # fig options
    if not project_preferences:
        project_preferences = load_project_preferences(hdf5.path_prj, hdf5.name_prj)

    # progress
    progress_value.value = 20

    # calcuation habitat
    [vh_all_t_sp, spu_all, area_c_all] = \
        calc_hab(hdf5.data_2d,
                 hdf5.data_description,
                 hdf5_file,
                 path_hdf5,
                 pref_list,
                 stages_chosen,
                 run_choice,
                 aquatic_animal_type,
                 progress_value,
                 qt_tr)

    # valid ?
    if vh_all_t_sp == [-99]:
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # name fish with stage
    for fish_ind, fish_name in enumerate(fish_names):
        stage_i = stages_chosen[fish_ind]
        hyd_opt_i = run_choice["hyd_opt"][fish_ind]
        sub_opt_i = run_choice["sub_opt"][fish_ind]
        fish_names[fish_ind] = fish_name + "_" + stage_i + "_" + hyd_opt_i + "_" + sub_opt_i

    # progress
    progress_value.value = 90

    # saving hdf5 data of the habitat value
    hdf5.add_fish_hab(vh_all_t_sp, area_c_all, spu_all, fish_names, pref_list, stages_chosen,
                      name_fish_sh, project_preferences, aquatic_animal_type)

    # copy xml curves to input project folder
    names = [os.path.basename(pref_list[i]) for i in range(len(pref_list))]
    paths = [os.path.join(os.getcwd(), os.path.dirname(pref_list[i])) for i in range(len(pref_list))]
    hdf5_mod.copy_files(names, paths, os.path.join(hdf5.path_prj, "input"))

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def calc_hab(data_2d, data_description, merge_name, path_merge, xmlfile, stages, run_choice, aquatic_animal_type, progress_value, qt_tr):
    """
    This function calculates the habitat value. It loads substrate and hydrology data from an hdf5 files and it loads
    the biology data from the xml files. It is possible to have more than one stage by xml file (usually the three
    stages are in the xml files). There are more than one method to calculte the habitat so the parameter opt indicate
    which metho to use. 0-> usde coarser substrate, 1 -> use dominant substrate

    :param merge_name: the name of the hdf5 with the results
    :param path_merge: the path to the merged file
    :param bio_names: the name of the xml biological data
    :param stages: the stage chosen (youngs, adults, etc.). List with the same length as bio_names.
    :param path_bio: The path to the biological folder (with all files given in bio_names
    :param run_choice: dict with two lists : one for hyd opt and second for sub opt
    :return: the habiatat value for all species, all time, all reach, all cells.
    """
    failload = [-99], [-99], [-99]
    vh_all_t_sp = []
    spu_all_t_sp = []
    area_c_all_t = []  # area by cell for each reach each time step
    found_stage = 0

    if len(xmlfile) != len(stages):
        print('Error: ' + qt_tr.translate("calcul_hab_mod", 'Number of stage and species is not coherent.'))
        return failload

    if len(xmlfile) == 0:
        print('Error: ' + qt_tr.translate("calcul_hab_mod", 'No fish species chosen.'))
        return failload

    # progress
    delta = (90 - progress_value.value) / len(xmlfile)

    # for each suitability curve
    for idx, bio_name in enumerate(xmlfile):
        aquatic_animal_type_select = aquatic_animal_type[idx]
        # load bio data
        information_model_dict = bio_info_mod.get_biomodels_informations_for_database(bio_name)
        [pref_height, pref_vel, pref_sub, sub_code, code_fish, name_fish, stade_bios] = bio_info_mod.read_pref(bio_name, aquatic_animal_type_select)
        # hyd opt
        hyd_opt = run_choice["hyd_opt"][idx]
        # sub opt
        sub_opt = run_choice["sub_opt"][idx]
        if pref_height == [-99]:
            print('Error: ' + qt_tr.translate("calcul_hab_mod", 'Preference file could not be loaded.'))
            return failload

        # for each stage
        for idx2, stade_bio in enumerate(stade_bios):
            if stages[idx] == stade_bio:
                found_stage += 1
                # fish case
                if aquatic_animal_type_select == "fish":
                    pref_height = pref_height[idx2]
                    pref_vel = pref_vel[idx2]
                    pref_sub = np.array(pref_sub[idx2])

                    # if the last value ends in 0 then change the corresponding value to x at 100 m
                    if information_model_dict["ModelType"] != 'bivariate suitability index models':
                        if pref_height[1][-1] == 0:
                            #print("Warning: " + qt_tr.translate("calcul_hab_mod", "Last x height value set to 100m : ") + name_fish + " " + stade_bio)
                            pref_height[0].append(1000)
                            pref_height[1].append(0)
                        if pref_vel[1][-1] == 0:
                            #print("Warning: " + qt_tr.translate("calcul_hab_mod", "Last x velocity value set to 100m/s : ") + name_fish + " " + stade_bio)
                            pref_vel[0].append(1000)
                            pref_vel[1].append(0)

                # invertebrate case
                elif aquatic_animal_type_select == "invertebrate":
                    pref_height = pref_height[idx2]
                    if pref_height[-1] == 0:
                        #print("Warning: " + qt_tr.translate("calcul_hab_mod", "Last x height value set to 100m :") + name_fish + stade_bio)
                        pref_height[-1] = 100

                # compute
                vh_all_t, spu_all_t, area_c_all_t, progress_value = \
                    calc_hab_norm(data_2d, data_description, name_fish, pref_vel, pref_height, pref_sub, hyd_opt, sub_opt,
                                  information_model_dict["substrate_type"][idx2], information_model_dict["ModelType"],
                                  progress_value, delta, qt_tr, aquatic_animal_type_select)

                # append data
                vh_all_t_sp.append(vh_all_t)
                spu_all_t_sp.append(spu_all_t)

        if found_stage == 0:
            print('Error: ' + qt_tr.translate("calcul_hab_mod", 'The name of the fish stage are not coherent.'))
            return failload

    return vh_all_t_sp, spu_all_t_sp, area_c_all_t


def calc_hab_norm(data_2d, hab_description, name_fish, pref_vel, pref_height, pref_sub, hyd_opt, sub_opt, model_sub_classification_method, model_type, progress_value, delta, qt_tr, aquatic_animal_type_select="fish"):
    """
    This function calculates the habitat suitiabilty index (f(H)xf(v)xf(sub)) for each and the SPU which is the sum of
    all habitat suitability index weighted by the cell area for each reach. It is called by clac_hab_norm.

    :param ikle_all_t: the connectivity table for all time step, all reach
    :param point_all_t: the point of the grid
    :param vel: the velocity data for all time step, all reach
    :param height: the water height data for all time step, all reach
    :param sub: the substrate data (can be coarser or dominant substrate based on function's call)
    :param pref_vel: the preference index for the velcoity (for one life stage)
    :param pref_sub: the preference index for the substrate  (for one life stage)
    :param pref_height: the preference index for the height  (for one life stage)
    :param percent: If True, the variable sub is in percent form, not in the form dominant/coarser
    :param take_sub: If False, the substrate data is neglected.
    :return: vh of one life stage, area, habitat value

    """
    s_pref_c = 1
    vh_all_t = []  # time step 0 is whole profile, no data
    spu_all_t = []
    area_c_all_t = []

    # progress
    prog = progress_value.value
    delta_reach = delta / len(data_2d["node"]["data"]["h"])

    # for each reach
    for reach_num in range(len(data_2d["mesh"]["tin"])):
        vh_all = []
        area_c_all = []
        spu_all = []

        # progress
        delta_unit = delta_reach / len(data_2d["node"]["data"]["h"][reach_num])
        warning_range_list = []

        if aquatic_animal_type_select == "invertebrate":
            warning_shearstress_list = []

        # for each unit
        for unit_num in range(len(data_2d["node"]["data"]["h"][reach_num])):
            height_t = data_2d["mesh"]["data"]["h"][reach_num][unit_num]
            vel_t = data_2d["mesh"]["data"]["v"][reach_num][unit_num]
            if aquatic_animal_type_select == "invertebrate":
                shear_stress_t = data_2d["mesh"]["data"]["shear_stress"][reach_num][unit_num]
            sub_t = data_2d["mesh"]["data"]["sub"][reach_num][unit_num]
            ikle_t = data_2d["mesh"]["tin"][reach_num][unit_num]
            area = data_2d["mesh"]["data"]["area"][reach_num][unit_num]
            if len(ikle_t) == 0:
                print('Warning: ' + qt_tr.translate("calcul_hab_mod", 'The connectivity table was not well-formed for one reach (1) \n'))
                vh = [-99]
                spu_reach = -99
                area = [-99]
            elif len(ikle_t[0]) < 3:
                print('Warning: ' + qt_tr.translate("calcul_hab_mod", 'The connectivity table was not well-formed for one reach (2) \n'))
                vh = [-99]
                spu_reach = -99
                area = [-99]
            else:
                # univariate
                if model_type != 'bivariate suitability index models':
                    # HEM
                    if aquatic_animal_type_select == "invertebrate":
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
                    if aquatic_animal_type_select == "fish":
                        """ hydraulic pref """
                        # get H pref value
                        if hyd_opt in ["HV", "H"]:
                            if max(pref_height[0]) < height_t.max():  # check range suitability VS range input data
                                warning_range_list.append(unit_num)
                            h_pref_c = np.interp(height_t, pref_height[0], pref_height[1], left=np.nan, right=np.nan)

                        # get V pref value
                        if hyd_opt in ["HV", "V"]:
                            if max(pref_vel[0]) < vel_t.max():  # check range suitability VS range input data
                                warning_range_list.append(unit_num)
                            v_pref_c = np.interp(vel_t, pref_vel[0], pref_vel[1], left=np.nan, right=np.nan)

                        """ substrate pref """
                        # Neglect
                        if sub_opt == "Neglect":
                            s_pref_c = np.array([1] * len(sub_t))
                        else:
                            # convert classification code sandre to cemagref
                            # TODO: no input data conversion if pref curve is sandre or antoher
                            if hab_description["sub_classification_code"] == "Sandre":
                                if hab_description["sub_classification_method"] == "percentage":
                                    sub_t = sandre_to_cemagref_by_percentage_array(sub_t)
                                else:
                                    sub_t = sandre_to_cemagref_array(sub_t)
                            # Coarser-Dominant
                            if sub_opt == "Coarser-Dominant":
                                if hab_description["sub_classification_method"] == "percentage":
                                    s_pref_c_coarser = pref_substrate_coarser_from_percentage_description(pref_sub[1], sub_t)
                                    s_pref_c_dom = pref_substrate_dominant_from_percentage_description(pref_sub[1], sub_t)
                                    s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                                elif hab_description["sub_classification_method"] == "coarser-dominant":
                                    s_pref_c_coarser = pref_sub[1][sub_t[:, 0] - 1]
                                    s_pref_c_dom = pref_sub[1][sub_t[:, 1] - 1]
                                    s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                            # Coarser
                            elif sub_opt == "Coarser":
                                if hab_description["sub_classification_method"] == "percentage":
                                    s_pref_c = pref_substrate_coarser_from_percentage_description(pref_sub[1], sub_t)
                                elif hab_description["sub_classification_method"] == "coarser-dominant":
                                    s_pref_c = pref_sub[1][sub_t[:, 0] - 1]
                            # Dominant
                            elif sub_opt == "Dominant":
                                if hab_description["sub_classification_method"] == "percentage":
                                    s_pref_c = pref_substrate_dominant_from_percentage_description(pref_sub[1], sub_t)
                                elif hab_description["sub_classification_method"] == "coarser-dominant":
                                    s_pref_c = pref_sub[1][sub_t[:, 1] - 1]
                            # Percentage
                            else:
                                if model_sub_classification_method == "Dominant":  # dominant curve
                                    s_pref_c = pref_substrate_dominant_from_percentage_description(pref_sub[1], sub_t)
                                if model_sub_classification_method == "Dominant":  # dominant curve
                                    s_pref_c = pref_substrate_coarser_from_percentage_description(pref_sub[1], sub_t)

                        """ compute habitat value """
                        try:
                            # HV
                            if "H" in hyd_opt and "V" in hyd_opt:
                                vh = h_pref_c * v_pref_c * s_pref_c
                                vh[h_pref_c == 0] = 0
                                vh[v_pref_c == 0] = 0
                                vh[s_pref_c == 0] = 0
                            # H
                            elif "H" in hyd_opt:
                                vh = h_pref_c * s_pref_c
                                vh[h_pref_c == 0] = 0
                                vh[s_pref_c == 0] = 0
                            # V
                            elif "V" in hyd_opt:
                                vh = v_pref_c * s_pref_c
                                vh[v_pref_c == 0] = 0
                                vh[s_pref_c == 0] = 0
                            # Neglect
                            else:
                                vh = s_pref_c
                        except ValueError:
                            print('Error: ' + qt_tr.translate("calcul_hab_mod", 'One time step misses substrate, velocity or water height value.'))
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

            vh_all.append(vh)
            area_c_all.append(area)
            spu_all.append(spu_reach)

            # progress
            prog += delta_unit
            progress_value.value = int(prog)

        vh_all_t.append(vh_all)
        spu_all_t.append(spu_all)
        area_c_all_t.append(area_c_all)
        if warning_range_list:
            warning_range_list = list(set(warning_range_list))
            warning_range_list.sort()
            # get unit name
            unit_names = []
            for warning_unit_num in warning_range_list:
                unit_names.append(hab_description["hyd_unit_list"][reach_num][warning_unit_num])
            print(f"Warning: " + qt_tr.translate("calcul_hab_mod", "Unknown habitat values produced for ") + name_fish + qt_tr.translate("calcul_hab_mod", ", his suitability curve range is not sufficient according to the hydraulics of unit(s) : ") +
                  ", ".join(str(x) for x in unit_names) + qt_tr.translate("calcul_hab_mod", " of reach : ") + hab_description["hyd_reach_list"])
        # HEM
        if aquatic_animal_type_select == "invertebrate":
            if warning_shearstress_list:
                warning_shearstress_list.sort()
                # get unit name
                unit_names = []
                for warning_unit_num in warning_shearstress_list:
                    unit_names.append(hab_description["hyd_unit_list"][reach_num][warning_unit_num])
                print(f"Warning: " + qt_tr.translate("calcul_hab_mod", "Unknown habitat values produced for ") + name_fish + qt_tr.translate("calcul_hab_mod", ", the shear stress data present unknown values in unit(s) : ") +
                      ", ".join(str(x) for x in unit_names) + qt_tr.translate("calcul_hab_mod", " of reach : ") + hab_description["hyd_reach_list"])

    return vh_all_t, spu_all_t, area_c_all_t, progress_value
