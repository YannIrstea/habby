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
import bisect
import time
import sys
from io import StringIO
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from time import time
from scipy.interpolate import interp1d

from src_GUI import preferences_GUI
from src import hdf5_mod
from src import bio_info_mod
from src.substrate_mod import pref_substrate_dominant_from_percentage_description, pref_substrate_coarser_from_percentage_description


def calc_hab_and_output(hdf5_file, path_hdf5, pref_list, stages_chosen, fish_names, name_fish_sh, run_choice, path_bio,
                        path_txt, progress_value, q=[], print_cmd=False, project_preferences={},
                        aquatic_animal_type="fish", xmlfiles=[]):
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
    # progress
    progress_value.value = 10

    # print output
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # load hab file
    hdf5 = hdf5_mod.Hdf5Management(os.path.dirname(path_hdf5), hdf5_file)
    hdf5.load_hdf5_hab()

    # fig options
    if not project_preferences:
        project_preferences = preferences_GUI.load_project_preferences(hdf5.path_prj, hdf5.name_prj)

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
                 progress_value)

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
                      name_fish_sh, project_preferences, path_bio)

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def calc_hab(data_2d, data_description, merge_name, path_merge, xmlfile, stages, run_choice, aquatic_animal_type, progress_value):
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
    failload = [-99], [-99], [-99], [-99], [-99], [-99]
    vh_all_t_sp = []
    spu_all_t_sp = []
    area_c_all_t = []  # area by cell for each reach each time step
    found_stage = 0

    if len(xmlfile) != len(stages):
        print('Error: Number of stage and species is not coherent. \n')
        return failload

    if len(xmlfile) == 0:
        print('Error: No fish species chosen. \n')
        return failload

    # progress
    delta = (90 - progress_value.value) / len(xmlfile)

    # for each suitability curve
    for idx, bio_name in enumerate(xmlfile):
        aquatic_animal_type_select = aquatic_animal_type[idx]
        # load bio data
        [pref_height, pref_vel, pref_sub, code_fish, name_fish, stade_bios] = bio_info_mod.read_pref(bio_name, aquatic_animal_type_select)

        # hyd opt
        hyd_opt = run_choice["hyd_opt"][idx]
        # sub opt
        sub_opt = run_choice["sub_opt"][idx]
        if pref_height == [-99]:
            print('Error: preference file could not be loaded. \n')
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
                    if pref_height[1][-1] == 0:
                        print(f"Warning: Last x height value set to 100m : {name_fish} {stade_bio}")
                        pref_height[0][-1] = 100
                    if pref_vel[1][-1] == 0:
                        print(f"Warning: Last x velocity value set to 100m/s : {name_fish} {stade_bio}")
                        pref_vel[0][-1] = 100
                # invertebrate case
                elif aquatic_animal_type_select == "invertebrate":
                    pref_height = pref_height[idx2]
                    if pref_height[1][-1] == 0:
                        print(f"Warning: Last x height value set to 100m : {name_fish} {stade_bio}")
                        pref_height[0][-1] = 100

                # compute
                vh_all_t, spu_all_t, area_c_all_t, progress_value = \
                    calc_hab_norm(data_2d, data_description, name_fish, pref_vel, pref_height, pref_sub, hyd_opt, sub_opt,
                                  progress_value, delta, aquatic_animal_type_select)

                # append data
                vh_all_t_sp.append(vh_all_t)
                spu_all_t_sp.append(spu_all_t)

        if found_stage == 0:
            print('Error: the name of the fish stage are not coherent \n')
            return failload

    return vh_all_t_sp, spu_all_t_sp, area_c_all_t


def calc_hab_norm(data_2d, hab_description, name_fish, pref_vel, pref_height, pref_sub, hyd_opt, sub_opt, progress_value, delta, aquatic_animal_type_select="fish", take_sub=True):
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
    delta_reach = delta / len(data_2d["h"])

    # for each reach
    for reach_num in range(len(data_2d["tin"])):
        vh_all = []
        area_c_all = []
        spu_all = []

        # progress
        delta_unit = delta_reach / len(data_2d["h"][reach_num])
        warning_range_list = []

        if aquatic_animal_type_select == "invertebrate":
            warning_shearstress_list = []

        # for each unit
        for unit_num in range(len(data_2d["h"][reach_num])):
            height_t = data_2d["h"][reach_num][unit_num]
            vel_t = data_2d["v"][reach_num][unit_num]
            if aquatic_animal_type_select == "invertebrate":
                shear_stress_t = data_2d["shear_stress"][reach_num][unit_num]
            sub_t = data_2d["sub"][reach_num][unit_num]
            ikle_t = data_2d["tin"][reach_num][unit_num]
            point_t = data_2d["xy"][reach_num][unit_num]

            if len(ikle_t) == 0:
                print('Warning: The connectivity table was not well-formed for one reach (1) \n')
                vh = [-99]
                spu_reach = -99
                area = [-99]
            elif len(ikle_t[0]) < 3:
                print('Warning: The connectivity table was not well-formed for one reach (2) \n')
                vh = [-99]
                spu_reach = -99
                area = [-99]
            else:
                # get area (based on Heron's formula)
                p1 = point_t[ikle_t[:, 0], :]
                p2 = point_t[ikle_t[:, 1], :]
                p3 = point_t[ikle_t[:, 2], :]
                d1 = np.sqrt((p2[:, 0] - p1[:, 0]) ** 2 + (p2[:, 1] - p1[:, 1]) ** 2)
                d2 = np.sqrt((p3[:, 0] - p2[:, 0]) ** 2 + (p3[:, 1] - p2[:, 1]) ** 2)
                d3 = np.sqrt((p3[:, 0] - p1[:, 0]) ** 2 + (p3[:, 1] - p1[:, 1]) ** 2)
                s2 = (d1 + d2 + d3) / 2
                area = s2 * (s2 - d1) * (s2 - d2) * (s2 - d3)
                area[area < 0] = 0  # -1e-11, -2e-12, etc because some points are so close
                area = area ** 0.5

                # HEM
                if aquatic_animal_type_select == "invertebrate":
                    """ HEM pref """
                    # get pref x and y
                    pref_shearstress = pref_height[0]
                    pref_values = pref_height[1]
                    # nterp1d(...... kind='previous') for values <0.0771
                    pref_shearstress = [0.0] + pref_shearstress
                    pref_values = pref_values + [pref_values[-1]]
                    # check range suitability VS range input data
                    if max(pref_shearstress) < np.nanmax(shear_stress_t):
                        warning_range_list.append(unit_num)
                    # hem_interp_function
                    hem_interp_f = interp1d(pref_shearstress, pref_values,
                                            kind='previous', bounds_error=False, fill_value=np.nan)
                    vh = hem_interp_f(shear_stress_t.flatten())
                    if any(np.isnan(shear_stress_t)):
                        warning_shearstress_list.append(unit_num)

                # fish case
                if aquatic_animal_type_select == "fish":
                    """ hydraulic pref """
                    # get H pref value
                    if hyd_opt in ["HV", "H"]:
                        h1 = height_t[ikle_t[:, 0]]
                        h2 = height_t[ikle_t[:, 1]]
                        h3 = height_t[ikle_t[:, 2]]
                        h_cell = 1.0 / 3.0 * (h1 + h2 + h3)
                        # check range suitability VS range input data
                        if max(pref_height[0]) < h_cell.max():
                            warning_range_list.append(unit_num)
                        h_pref_c = np.interp(h_cell, pref_height[0], pref_height[1], left=np.nan, right=np.nan)

                    # get V pref value
                    if hyd_opt in ["HV", "V"]:
                        v1 = vel_t[ikle_t[:, 0]]
                        v2 = vel_t[ikle_t[:, 1]]
                        v3 = vel_t[ikle_t[:, 2]]
                        v_cell = 1.0 / 3.0 * (v1 + v2 + v3)
                        # check range suitability VS range input data
                        if max(pref_vel[0]) < v_cell.max():
                            warning_range_list.append(unit_num)
                        v_pref_c = np.interp(v_cell, pref_vel[0], pref_vel[1], left=np.nan, right=np.nan)

                    """ substrate pref """
                    if sub_opt == "Neglect":  # Neglect
                        s_pref_c = np.array([1] * len(sub_t))
                    elif sub_opt == "Coarser-Dominant":  # Coarser-Dominant
                        if hab_description["sub_classification_method"] == "percentage":
                            s_pref_c_coarser = pref_substrate_coarser_from_percentage_description(pref_sub[1], sub_t)
                            s_pref_c_dom = pref_substrate_dominant_from_percentage_description(pref_sub[1], sub_t)
                            s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                        elif hab_description["sub_classification_method"] == "coarser-dominant":
                            s_pref_c_coarser = pref_sub[1][sub_t[:, 0] - 1]
                            s_pref_c_dom = pref_sub[1][sub_t[:, 1] - 1]
                            s_pref_c = (0.2 * s_pref_c_coarser) + (0.8 * s_pref_c_dom)
                    elif sub_opt == "Coarser":  # Coarser
                        if hab_description["sub_classification_method"] == "percentage":
                            s_pref_c = pref_substrate_coarser_from_percentage_description(pref_sub[1], sub_t)
                        elif hab_description["sub_classification_method"] == "coarser-dominant":
                            s_pref_c = pref_sub[1][sub_t[:, 0] - 1]
                    elif sub_opt == "Dominant":  # Dominant
                        if hab_description["sub_classification_method"] == "percentage":
                            s_pref_c = pref_substrate_dominant_from_percentage_description(pref_sub[1], sub_t)
                        elif hab_description["sub_classification_method"] == "coarser-dominant":
                            s_pref_c = pref_sub[1][sub_t[:, 1] - 1]
                    else:  # percentage
                        for st in range(0, 8):
                            s0 = s[:, st]
                            sthere = np.zeros((len(s0),)) + st + 1
                            s_pref_st = find_pref_value(sthere, pref_sub)
                            if st == 0:
                                s_pref_c = s_pref_st * s0 / 100
                            else:
                                s_pref_c += s0 / 100 * s_pref_st

                    """ compute habitat value """
                    try:
                        # HV
                        if "H" in hyd_opt and "V" in hyd_opt:
                            vh = h_pref_c * v_pref_c * s_pref_c
                        # H
                        elif "H" in hyd_opt:
                            vh = h_pref_c * s_pref_c
                        # V
                        elif "V" in hyd_opt:
                            vh = v_pref_c * s_pref_c
                        # Neglect
                        else:
                            vh = s_pref_c
                    except ValueError:
                        print('Error: One time step misses substrate, velocity or water height value \n')
                        vh = [-99]

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
            print(f"Warning: Unknown habitat values produced for {name_fish}, his suitability curve range is not sufficient according to the hydraulics of unit n°" +
                  ", ".join(str(x) for x in warning_range_list) + " of reach n°" + str(reach_num))
        # HEM
        if aquatic_animal_type_select == "invertebrate":
            if warning_shearstress_list:
                print(f"Warning: Unknown habitat values produced for {name_fish}, the shear stress data present unknown values in unit n°" +
                      ", ".join(str(x) for x in warning_shearstress_list) + " of reach n°" + str(reach_num))

    return vh_all_t, spu_all_t, area_c_all_t, progress_value


def find_pref_value(data, pref):
    """
    This function finds the preference value associated with the data for each cell. For this, it finds the last
    point of the preference curve under the data and it makes a linear interpolation with the next data to
    find the preference value. As preference value is sorted, it uses the module bisect to accelerate the process.

    :param data: the data on the cells (for one time step, on reach)
    :param pref: the pref data [pref, class data]
    """

    pref = np.array(pref)
    pref_f = pref[1]  # the preferene value
    pref_d = pref[0]  # the data linked with it
    pref_data = []

    for d in data:
        indh = bisect.bisect(pref_d, d) - 1  # about 3 time quicker than max(np.where(x_ini <= x_p[i])), ordered
        if indh < 0:
            indh = 0
        dmin = pref_d[indh]
        prefmin = pref_f[indh]
        if indh < len(pref_d) - 1:
            dmax = pref_d[indh + 1]
            prefmax = pref_f[indh + 1]
            if dmax == dmin:  # does not happen theorically
                pref_data_here = prefmin
            else:
                a1 = (prefmax - prefmin) / (dmax - dmin)
                b1 = prefmin - a1 * dmin
                pref_data_here = a1 * d + b1
                # This is a test to reproduce lammi result as best as possible
                # if pref_data_here > 0.98:
                #     pref_data_here = 1
                # if pref_data_here < 0.02:
                #     pref_data_here = 0
                if pref_data_here < 0 or pref_data_here > 1:
                    # the linear interpolation sometimes creates value like -5.55e-17
                    if -1e-3 < pref_data_here < 0:
                        pref_data_here = 0
                    elif 1 < pref_data_here < 1 + 1e10:
                        pref_data_here = 1
                    else:
                        if d < 0:
                            print('Warning: Water or heigth data is smaller than zero. \n')
                        else:
                            print('Warning: preference data is not between 0 and 1. \n')
            pref_data.append(pref_data_here)
        else:
            pref_data.append(pref_f[indh])

    pref_data = np.array(pref_data)

    return pref_data


def save_hab_txt(data_2d, hab_description, vh_data, area_c_all, vel_data, height_data, name_fish, path_txt, name_base,
                 sim_name=[], erase_id=False):
    """
    This function print the text output. We create one set of text file by time step. Each Reach is separated by the
    key work REACH follwoed by the reach number (strating from 0). There are three files by time steps: one file which
    gives the connectivity table (starting at 0), one file with the point coordinates in the
    coordinate systems of the hydraulic models (x,y), one file wiche gives the results.
    In all three files, the first column is the reach number. In the results files, the next columns are velocity,
    height, substrate, habitat value for each species. Use tab instead of space to help with excel import.

    The name and the form of the files do not change with the chosen language. The idea is that these files are quite big
    and that they will mostly be used by computer program. So it is easier for the user if the name and form is coherent.

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vel_data: the velocity by reach by time step on the cell (not node!)
    :param height_data: the height by reach by time step on the cell (not node!)
    :param vh_data: the habitat value data by speces by reach by tims tep
    :param area_c_all: the area by reach by time step on the cell (not node!)
    :param name_fish: the list of fish latin name + stage
    :param path_txt: the path where to save the text file
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the simulation/time step (list of strings)
    :param erase_id: If True, we erase old text file from identical hydraulic model
    """

    # [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
    #     hdf5_mod.load_hdf5_hyd_and_merge(name_merge_hdf5, path_hdf5, merge=True)

    data_2d, hab_description



    if ikle == [-99]:
        return

    if not os.path.exists(path_txt):
        print('Error: the path to save the text file do not exists. \n')
        return

    if len(sim_name) > 0 and len(sim_name) != len(ikle) - 1:
        sim_name = []

    # we do not print the first time step with the whole profile
    nb_reach = len(ikle[0])
    for t in range(1, len(ikle)):
        ikle_here = ikle[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            # choose the name of the text file
            if not erase_id:
                if not sim_name:
                    name1 = 'xy_' + 't_' + str(t) + '_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") \
                            + '.txt'
                    name2 = 'gridcell_' + 't_' + str(t) + '_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") \
                            + '.txt'
                    name3 = 'result_' + 't_' + str(t) + '_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") \
                            + '.txt'
                else:
                    name1 = 'xy_' + 't_' + sim_name[t - 1] + '_' + name_base + '_' + \
                            time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    name2 = 'gridcell_' + 't_' + sim_name[t - 1] + '_' + name_base + '_' + \
                            time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    name3 = 'result_' + 't_' + sim_name[t - 1] + '_' + name_base + '_' + \
                            time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
            else:
                if not sim_name:
                    name1 = 'xy_' + 't_' + str(t) + '_' + name_base + '.txt'
                    name2 = 'gridcell_' + 't_' + str(t) + '_' + name_base + '.txt'
                    name3 = 'result_' + 't_' + str(t) + '_' + name_base + '.txt'
                else:
                    name1 = 'xy_' + 't_' + sim_name[t - 1] + '_' + name_base + '.txt'
                    name2 = 'gridcell_' + 't_' + sim_name[t - 1] + '_' + name_base + '.txt'
                    name3 = 'result_' + 't_' + sim_name[t - 1] + '_' + name_base + '.txt'
                try:
                    if os.path.isfile(os.path.join(path_txt, name1)):
                        os.remove(os.path.join(path_txt, name1))
                    if os.path.isfile(os.path.join(path_txt, name2)):
                        os.remove(os.path.join(path_txt, name2))
                    if os.path.isfile(os.path.join(path_txt, name3)):
                        os.remove(os.path.join(path_txt, name3))
                except PermissionError:
                    print('Error: Could not modfiy the text file. Might be open in another prgram\n')
                    return
            name1 = os.path.join(path_txt, name1)
            name2 = os.path.join(path_txt, name2)
            name3 = os.path.join(path_txt, name3)

            # grid
            with open(name2, 'wt', encoding='utf-8') as f:
                for r in range(0, nb_reach):
                    ikle_here = ikle[t][r]
                    f.write('REACH ' + str(r) + '\n')
                    f.write('reach\tcell1\tcell2\tcell3' + '\n')
                    for c in ikle_here:
                        f.write(str(r) + '\t' + str(c[0]) + '\t' + str(c[1]) + '\t' + str(c[2]) + '\n')
            # point
            with open(name1, 'wt', encoding='utf-8') as f:
                for r in range(0, nb_reach):
                    p_here = point[t][r]
                    f.write('REACH ' + str(r) + '\n')
                    f.write('reach\tx\ty' + '\n')
                    for p in p_here:
                        f.write(str(r) + '\t' + str(p[0]) + '\t' + str(p[1]) + '\n')
            # result
            with open(name3, 'wt', encoding='utf-8') as f:
                for r in range(0, nb_reach):
                    s_here = area_c_all[t][r]
                    v_here = vel_data[t][r]
                    h_here = height_data[t][r]
                    sub_pg = sub_pg_data[t][r]
                    sub_dom = sub_dom_data[t][r]
                    f.write('REACH ' + str(r) + '\n')
                    # header 1
                    header = 'reach\tcells\tarea\tvelocity\theight\tcoarser_substrate\tdominant_substrate'
                    for i in range(0, len(name_fish)):
                        header += '\tVH' + str(i)
                    header += '\n'
                    f.write(header)
                    # header 2
                    header = '[]\t[]\t[m2]\t[m/s]\t[m]\t[Code_Cemagref]\t[Code_Cemagref]'
                    for i in name_fish:
                        i = i.replace(' ', '_')  # so space/tab is only a separator
                        header += '\t' + i
                    header += '\n'
                    f.write(header)
                    # data
                    for i in range(0, len(v_here)):
                        vh_str = ''
                        for j in range(0, len(name_fish)):
                            try:
                                vh_str += str(vh_data[j][t][r][i]) + '\t'
                            except IndexError:
                                print('Error: Results could not be written to text file. \n')
                                return
                        f.write(str(r) + '\t' + str(i) + '\t' + str(s_here[i]) + '\t' + str(v_here[i]) + '\t' + str(
                            h_here[i]) + '\t' +
                                str(sub_pg[i]) + '\t' + str(sub_dom[i]) + '\t' + vh_str + '\n')


def save_spu_txt(area_all, spu_all, hab_description, sim_name=[], lang=0, erase_id=False):
    """
    This function create a text files with the folowing columns: the tiem step, the reach number, the area of the
    reach and the spu for each fish species. Use tab instead of space to help with excel import.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_txt: the path where to save the text file
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the time step
    :param lang: an int which indicates the chosen language (0 is english)
    :param erase_id: If True, we erase old text file from identical hydraulic model
    """
    path_txt = os.path.join(hab_description["path_project"], "output", "text")
    if not os.path.exists(path_txt):
        print('Error: the path to the text file is not found. Text files not created \n')

    name_base = os.path.splitext(hab_description["hab_filename"])[0]
    sim_name = hab_description["hyd_unit_list"].split(", ")
    name_fish = hab_description["hab_fish_list"].split(", ")
    unit_type = hab_description["hyd_unit_type"][hab_description["hyd_unit_type"].find('[') + 1:hab_description["hyd_unit_type"].find(']')]


    if not erase_id:
        if lang == 0:
            name = 'wua_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
        else:
            name = 'spu_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
    else:
        if lang == 0:
            name = 'wua_' + name_base + '.txt'
        else:
            name = 'spu_' + name_base + '.txt'
        if os.path.isfile(os.path.join(path_txt, name)):
            try:
                os.remove(os.path.join(path_txt, name))
            except PermissionError:
                print('Error: Could not modify text file as it is open in another program. \n')
                return

    name = os.path.join(path_txt, name)
    if len(sim_name) > 0 and len(sim_name) != len(area_all[0]):
        sim_name = []

    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:

        # header
        if lang == 0:
            header = 'reach\tunit\treach_area'
        else:
            header = 'troncon\tunit\taire_troncon'
        for i in range(0, len(name_fish)):
            if lang == 0:
                header += '\tWUA' + str(i) + '\tHV' + str(i)
            else:
                header += '\tSPU' + str(i) + '\tVH' + str(i)
        header += '\n'
        f.write(header)
        # header 2
        header = '[]\t[' + unit_type + ']\t[m2]'
        for i in name_fish:
            header += '\t[m2]\t[]'
        header += '\n'
        f.write(header)
        # header 3
        header = 'all\tall\tall '
        for i in name_fish:
            i = i.replace(' ', '_')  # so space is always a separator
            header += '\t' + i + '\t' + i
        header += '\n'
        f.write(header)

        for reach_num in range(0, len(area_all)):
            for unit_num in range(0, len(area_all[reach_num])):
                if not sim_name:
                    data_here = str(reach_num) + '\t' + str(unit_num) + '\t' + str(area_all[reach_num][unit_num])
                else:
                    data_here = str(reach_num) + '\t' + sim_name[unit_num] + '\t' + str(area_all[reach_num][unit_num])
                for fish_num in range(0, len(name_fish)):
                    data_here += '\t' + str(spu_all[fish_num][reach_num][unit_num])
                    try:
                        data_here += '\t' + str(spu_all[fish_num][reach_num][unit_num] / area_all[reach_num][unit_num])
                    except TypeError:
                        data_here += '\t' + 'NaN'
                data_here += '\n'
                f.write(data_here)


def save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base, project_preferences={}, sim_name=[], erase_id=False,
                     do_save=True):
    """
    This function creates the figure of the spu as a function of time for each reach. if there is only one
    time step, it reverse to a bar plot. Otherwise it is a line plot.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_im: the path where to save the image
    :param project_preferences: the dictionnary with the figure options
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the time steps if not 0,1,2,3
    :param erase_id: If True, figure from identical simuation are erased
    :param do_save: If False, the figure is not saved, but the figure is returned to be used for something else
    """

    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    if project_preferences['font_size'] > 7:
        plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
    fig = plt.figure()

    if len(spu_all) != len(name_fish):
        print('Error: Number of fish name and number of WUA data is not coherent \n')
        return

    try:
        nb_reach = len(area_all)  # we might have failed time step
    except TypeError:  # or all failed time steps -99
        # print('Error: No reach found. Is the hdf5 corrupted? \n')
        return

    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # for each reach
    for reach_num in range(0, nb_reach):
        if sim_name and len(area_all[reach_num]) != len(sim_name):
            sim_name = []

        # one time step - bar
        if len(area_all[reach_num]) == 1:
            # SPU
            data_bar = []
            for s in range(0, len(name_fish)):
                data_bar.append(spu_all[r][s][1][r])
            y_pos = np.arange(len(spu_all))
            if r > 0:
                fig = plt.figure()
            fig.add_subplot(211)
            if data_bar:
                data_bar2 = np.array(data_bar)
                plt.bar(y_pos, data_bar2, 0.5)
                plt.xticks(y_pos + 0.25, name_fish)
            if project_preferences['language'] == 0:
                plt.ylabel('WUA [m^2]')
            elif project_preferences['language'] == 1:
                plt.ylabel('SPU [m^2]')
            else:
                plt.ylabel('WUA [m^2]')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            if project_preferences['language'] == 0:
                plt.title('Weighted Usable Area for the Reach ' + str(r))
            elif project_preferences['language'] == 1:
                plt.title('Surface Ponderée Utile pour le Troncon: ' + str(r))
            else:
                plt.title('Weighted Usable Area for the Reach ' + str(r))
            # VH
            fig.add_subplot(212)
            if data_bar:
                data_bar2 = np.array(data_bar)
                plt.bar(y_pos, data_bar2 / area_all[-1][r], 0.5)
                plt.xticks(y_pos + 0.25, name_fish)
            if project_preferences['language'] == 0:
                plt.ylabel('HV (WUA/A) []')
            elif project_preferences['language'] == 1:
                plt.ylabel('VH (SPU/A) []')
            else:
                plt.ylabel('HV (WUA/A) []')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            plt.ylim(0, 1)
            if project_preferences['language'] == 0:
                plt.title('Habitat value for the Reach ' + str(r))
            elif project_preferences['language'] == 1:
                plt.title("Valeur d'Habitat:  " + str(r))
            else:
                plt.title('Habitat value for the Reach ' + str(r))
            if not erase_id:
                name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_base + '_Reach_' + str(r)
                test = remove_image(name, path_im, format1)
                #if not test:
                    #return
            plt.tight_layout()
            if do_save:
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

        # many time step - lines
        if len(area_all[reach_num]) >= 2:
            for fish_num in range(len(name_fish)):
                y_data_spu = np.array(spu_all[fish_num][reach_num])
                #y_data_vh = y_data_spu / np.array(area_all[reach_num])
                if sim_name:
                    try:
                        x_data = np.array(list(map(float, sim_name)))
                    except:
                        print("can't convert unit name to float")
                        return
                if not sim_name:
                    x_data = np.array(list(range(len(spu_all[reach_num][0]))))

                plt.plot(x_data, y_data_spu, label=name_fish[fish_num], marker=mar)





            # t_all = []
            # # SPU
            # fig = plt.figure()
            # fig.add_subplot(211)
            # for s in range(0, len(spu_all)):
            #     data_plot = []
            #     t_all = []
            #     for t in range(0, len(area_all)):
            #         if spu_all[s][t] and spu_all[s][t][r] != -99:
            #             data_plot.append(spu_all[s][t][r])
            #             sum_data_spu[s][t] += spu_all[s][t][r]
            #             t_all.append(t)
            #     t_all_s = t_all
            #     plt.plot(t_all, data_plot, label=name_fish[s], marker=mar)



            if project_preferences['language'] == 0:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('WUA [m$^2$]')
                plt.title('Weighted Usable Area for the Reach ' + str(reach_num))
            elif project_preferences['language'] == 1:
                plt.xlabel('Pas de temps/débit [ ]')
                plt.ylabel('SPU [m$^2$]')
                plt.title('Surface Ponderée pour le troncon ' + str(reach_num))
            else:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('WUA [m$^2$]')
                plt.title('Weighted Usable Area for the Reach ' + str(reach_num))
            plt.legend(fancybox=True, framealpha=0.5)  # make the legend transparent
            if sim_name:
                if len(sim_name[0]) > 5:
                    rot = 'vertical'
                else:
                    rot = 'horizontal'
                if len(sim_name) < 25:
                    plt.xticks(x_data, sim_name, rotation=rot)
                elif len(sim_name) < 100:
                    plt.xticks(x_data[::3], sim_name[::3], rotation=rot)
                else:
                    plt.xticks(x_data[::10], sim_name[::10], rotation=rot)
            # VH
            ax = fig.add_subplot(212)
            # t_all = []
            # for s in range(0, len(spu_all)):
            #     data_plot = []
            #     t_all = []
            #     for t in range(0, len(area_all)):
            #         if spu_all[s][t] and spu_all[s][t][r] != -99:
            #             data_here = spu_all[s][t][r] / area_all[t][r]
            #             data_plot.append(data_here)
            #             sum_data_spu_div[s][t] += data_here
            #             t_all.append(t)
            #     plt.plot(t_all, data_plot, label=name_fish[s], marker=mar)

            for fish_num in range(len(name_fish)):
                y_data_vh = np.array(spu_all[fish_num][reach_num]) / np.array(area_all[reach_num])
                if sim_name:
                    try:
                        x_data = np.array(list(map(float, sim_name)))
                    except:
                        print("can't convert unit name to float")
                        return
                if not sim_name:
                    x_data = np.array(list(range(len(spu_all[reach_num][0]))))

                plt.plot(x_data, y_data_vh, label=name_fish[fish_num], marker=mar)

            if project_preferences['language'] == 0:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value for the Reach ' + str(reach_num))
            elif project_preferences['language'] == 1:
                plt.xlabel('Pas de temps/débit [ ]')
                plt.ylabel('HV (SPU/A) []')
                plt.title("Valeur d'habitat pour le troncon " + str(reach_num))
            else:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value for the Reach ' + str(reach_num))
            plt.ylim(0, 1)
            if sim_name:
                if len(sim_name[0]) > 5:
                    rot = 'vertical'
                else:
                    rot = 'horizontal'
                if len(sim_name) < 25:
                    plt.xticks(x_data, sim_name, rotation=rot)
                elif len(sim_name) < 100:
                    plt.xticks(x_data[::3], sim_name[::3], rotation=rot)
                else:
                    plt.xticks(x_data[::10], sim_name[::10], rotation=rot)
            plt.tight_layout()
            if not erase_id:
                name = 'WUA_' + name_base + '_Reach_' + str(reach_num) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_base + '_Reach_' + str(reach_num)
                test = remove_image(name, path_im, format1)
                if not test:
                    return
            if do_save:
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

            # all reach
            if nb_reach > 1:
                plt.close('all')  # only show the last reach
                fig = plt.figure()
                fig.add_subplot(211)
                for s in range(0, len(spu_all)):
                    plt.plot(t_all_s, sum_data_spu[s][t_all_s], label=name_fish[s], marker=mar)
                if project_preferences['language'] == 0:
                    plt.xlabel('Computational step or discharge')
                    plt.ylabel('WUA [m^2]')
                    plt.title('Weighted Usable Area for All Reaches')
                elif project_preferences['language'] == 1:
                    plt.xlabel('Pas de temps/débit')
                    plt.ylabel('SPU [m^2]')
                    plt.title('Surface Ponderée pour tous les Troncons')
                else:
                    plt.xlabel('Computational step or discharge')
                    plt.ylabel('WUA [m^2]')
                    plt.title('Weighted Usable Area for All Reaches')
                plt.legend(fancybox=True, framealpha=0.5)
                if sim_name:
                    if len(sim_name[0]) > 5:
                        rot = 'vertical'
                    else:
                        rot = 'horizontal'
                    if len(sim_name) < 25:
                        plt.xticks(t_all, sim_name, rotation=rot)
                    elif len(sim_name) < 100:
                        plt.xticks(t_all[::3], sim_name[::3], rotation=rot)
                    else:
                        plt.xticks(t_all[::10], sim_name[::10], rotation=rot)
                # VH
                fig.add_subplot(212)
                for s in range(0, len(spu_all)):
                    plt.plot(t_all, sum_data_spu_div[s][t_all], label=name_fish[s], marker=mar)
                if project_preferences['language'] == 0:
                    plt.xlabel('Computational step or discharge ')
                    plt.ylabel('HV (WUA/A) []')
                    plt.title('Habitat Value For All Reaches')
                elif project_preferences['language'] == 1:
                    plt.xlabel('Pas de temps/débit')
                    plt.ylabel('HV (SPU/A) []')
                    plt.title("Valeurs d'Habitat Pour Tous Les Troncons")
                else:
                    plt.xlabel('Computational step or discharge ')
                    plt.ylabel('HV (WUA/A) []')
                    plt.title('Habitat Value For All Reaches')
                plt.ylim(0, 1)
                plt.tight_layout()
                if sim_name:
                    if len(sim_name[0]) > 5:
                        rot = 'vertical'
                    else:
                        rot = 'horizontal'
                    if len(sim_name) < 25:
                        plt.xticks(t_all, sim_name, rotation=rot)
                    elif len(sim_name) < 100:
                        plt.xticks(t_all[::3], sim_name[::3], rotation=rot)
                    else:
                        plt.xticks(t_all[::10], sim_name[::10], rotation=rot)
                if not erase_id:
                    name = 'WUA_' + name_base + '_All_Reach_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    name = 'WUA_' + name_base + '_All_Reach_'
                    test = remove_image(name, path_im, format1)
                    if not test:
                        return
                if do_save:
                    if format1 == 0 or format1 == 1:
                        plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
                    if format1 == 0 or format1 == 3:
                        plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
                    if format1 == 2:
                        plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

        if not do_save:
            return fig


def save_vh_fig_2d(name_merge_hdf5, path_hdf5, vh_all_t_sp, path_im, name_fish, name_base, project_preferences={}, time_step=[-1],
                   sim_name=[], save_fig=True, erase_id=False):
    """
    This function creates 2D map of the habitat value for each species at
    the time step asked. All reaches are ploted on the same figure.

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vh_all_t_sp: the habitat value for all reach all time step all species
    :param path_im: the path where to save the figure
    :param name_fish: the name and stage of the studied species
    :param name_base: the string on which to base the figure name
    :param project_preferences: the dictionnary with the figure options
    :param time_step: which time step should be plotted
    :param sim_name: the name of the time step if not 0,1,2,3
    :param save_fig: If True the figure is saved

    """

    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator

    b = 0
    # get grid data from hdf5
    [ikle_all_t, point_all_t, blob, blob, sub_pg_data, sub_dom_data] = \
        hdf5_mod.load_hdf5_hyd_and_merge(name_merge_hdf5, path_hdf5, merge=True)
    if ikle_all_t == [-99]:
        return
    # format name fish
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    if max(time_step) - 1 > len(sim_name):
        sim_name = []

    # create the figure for each species, and each time step
    all_patches = []
    for sp in range(0, len(vh_all_t_sp)):
        vh_all_t = vh_all_t_sp[sp]
        rt = 0

        for t in time_step:
            try:
                ikle_t = ikle_all_t[t]
                all_ok = True
            except IndexError:
                print('Warning: Figure not created for one time step as the time step was not found \n')
                all_ok = False  # continue is not ok in try
            if all_ok:
                point_t = point_all_t[t]
                if abs(t) < len(vh_all_t):
                    vh_t = vh_all_t[t]
                    fig, ax = plt.subplots(1)  # new figure
                    norm = mpl.colors.Normalize(vmin=0, vmax=1)

                    for r in range(0, len(vh_t)):
                        try:
                            ikle = ikle_t[r]
                        except IndexError:
                            print('Number of reach is not coherent. Could not plot figure. \n')
                            return
                        if len(ikle) < 3:
                            pass
                        else:
                            coord_p = point_t[r]
                            vh = vh_t[r]

                            # plot the habitat value
                            cmap = plt.get_cmap(project_preferences['color_map2'])
                            colors = cmap(vh)
                            if sp == 0:  # for optimization (the grid is always the same for each species)
                                n = len(vh)
                                patches = []
                                for i in range(0, n):
                                    verts = []
                                    for j in range(0, 3):
                                        verts_j = coord_p[int(ikle[i][j]), :]
                                        verts.append(verts_j)
                                    polygon = Polygon(verts, closed=True, edgecolor='w')
                                    patches.append(polygon)
                                if len(vh_all_t_sp) > 1:
                                    all_patches.append(patches)
                            else:
                                patches = all_patches[rt]

                            collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
                            # collection.set_color(colors) too slow
                            collection.set_array(np.array(vh))
                            ax.add_collection(collection)
                            ax.autoscale_view()
                            ax.ticklabel_format(useOffset=False)
                            plt.axis('equal')
                            # cbar = plt.colorbar()
                            # cbar.ax.set_ylabel('Substrate')
                            if r == 0:
                                plt.xlabel('x coord []')
                                plt.ylabel('y coord []')
                                if t == -1:
                                    if not sim_name:
                                        if project_preferences['language'] == 0:
                                            plt.title('Habitat Value of ' + name_fish[sp] + '- Last Computational Step')
                                        elif project_preferences['language'] == 1:
                                            plt.title(
                                                "Valeur d'Habitat pour " + name_fish[sp] + '- Dernière Simulation')
                                        else:
                                            plt.title('Habitat Value of ' + name_fish[sp] + '- Last Computational Step')
                                    else:
                                        if project_preferences['language'] == 0:
                                            plt.title('Habitat Value of ' + name_fish[sp] + '- Computational Step: ' +
                                                      sim_name[-1])
                                        elif project_preferences['language'] == 1:
                                            plt.title(
                                                "Valeur d'Habitat pour " + name_fish[sp] + '- Pas de temps/débit: ' +
                                                sim_name[-1])
                                        else:
                                            plt.title('Habitat Value of ' + name_fish[sp] + '- Computational Step: ' +
                                                      sim_name[-1])
                                else:
                                    if not sim_name:
                                        if project_preferences['language'] == 0:
                                            plt.title(
                                                'Habitat Value of ' + name_fish[sp] + '- Computational Step: ' + str(t))
                                        elif project_preferences['language'] == 1:
                                            plt.title(
                                                "Valeur d'Habitat pour " + name_fish[sp] + '- Pas de temps/débit: '
                                                + str(t))
                                    else:
                                        if project_preferences['language'] == 0:
                                            plt.title('Habitat Value of ' + name_fish[sp] + '- Copmutational Step: '
                                                      + sim_name[t - 1])
                                        elif project_preferences['language'] == 1:
                                            plt.title(
                                                "Valeur d'Habitat pour " + name_fish[sp] + '- Pas de temps/débit: ' +
                                                sim_name[t - 1])
                            ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure
                            rt += 1

                            # colorbar
                            # Set norm to correspond to the data for which
                            # the colorbar will be used.
                            # ColorbarBase derives from ScalarMappable and puts a colorbar
                            # in a specified axes, so it has everything needed for a
                            # standalone colorbar.  There are many more kwargs, but the
                            # following gives a basic continuous colorbar with ticks
                            # and labels.
                            cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
                            if project_preferences['language'] == 0:
                                cb1.set_label('HV []')
                            elif project_preferences['language'] == 1:
                                cb1.set_label('VH []')
                            else:
                                cb1.set_label('HV []')

                    # save figure
                    if save_fig:
                        if not erase_id:
                            if not sim_name:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + str(t) + '_' + \
                                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                            elif t - 1 >= 0 and sim_name[t - 1]:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + sim_name[t - 1] + '_' + \
                                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                            elif t == -1:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + sim_name[-1] + '_' + \
                                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                            else:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + str(t) + '_' + \
                                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                        else:
                            if not sim_name:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + str(t)
                            elif t - 1 >= 0 and sim_name[t - 1]:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + sim_name[t - 1]
                            elif t == -1:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + sim_name[-1]
                            else:
                                name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + str(t)
                            test = remove_image(name_fig, path_im, format1)
                            if not test:
                                return

                        if format1 == 0 or format1 == 1:
                            plt.savefig(os.path.join(path_im, name_fig + '.png'), dpi=project_preferences['resolution'],
                                        transparent=True)
                        if format1 == 0 or format1 == 3:
                            plt.savefig(os.path.join(path_im, name_fig + '.pdf'), dpi=project_preferences['resolution'],
                                        transparent=True)
                        if format1 == 2:
                            plt.savefig(os.path.join(path_im, name_fig + '.jpg'), dpi=project_preferences['resolution'],
                                        transparent=True)


def plot_hist_hydro(hdf5_file, path_hdf5, vel_c_all_t, height_c_all_t, area_c_all_t, project_preferences, path_im, timestep,
                    name_base, sim_name=[], erase_id=False):
    """
    This function plots an historgram of the hydraulic and substrate data for the selected timestep. This historgramm
    is weighted by the area of the cell. The data is based on the height and velocity data by cell and not on the node.

    :param hdf5_file: the name of the hdf5 file
    :param path_hdf5: the path to this file
    :param vel_c_all_t: the velcoity for all reach all time step by cell
    :param height_c_all_t: the water height for all reach all time step by cell
    :param area_c_all_t: the aire of cells for all reach, all time step
    :param project_preferences: the figure options
    :param path_im: the path where to save the images
    :param timestep: a list with the time step to be plotted
    :param name_base: the base on which to form the figure name
    :param sim_name: the name of the time steps when not 0,1,2,3
    :param erase_id: If True, we erase a figure with an identical name
    """
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make fifgure ediable in adobe illustrator

    if max(timestep) - 1 > len(sim_name):
        sim_name = []

    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        hdf5_mod.load_hdf5_hyd_and_merge(hdf5_file, path_hdf5, merge=True)
    if ikle == [[-99]]:
        return

    # we do not print the first time step with the whole profile

    for t in timestep:
        try:
            ikle_here = ikle[t][0]
        except IndexError:
            print('Error: Figure not created. Number of time step was not coherent with hydrological info.\n')
            return
        if len(ikle_here) < 2:  # time step failed
            pass
        else:
            vel_all = vel_c_all_t[t]
            height_all = height_c_all_t[t]
            sub_pg_all = sub_pg_data[t]
            area_all = area_c_all_t[t]

            for r in range(0, len(vel_all)):  # each reach
                if r == 0:
                    vel_app = list(vel_all[0])
                    height_app = list(height_all[0])
                    sub_pg_app = list(sub_pg_all[0])
                    area_app = list(area_all[0])
                else:
                    vel_app.extend(list(vel_all[r]))
                    height_app.extend(list(height_all[r]))
                    sub_pg_app.extend(list(sub_pg_all[r]))
                    area_app.extend(list(area_all[r]))

            fig = plt.figure()
            # velocity
            fig.add_subplot(221)
            plt.hist(vel_app, 20, weights=area_app, facecolor='blue')
            if project_preferences['language'] == 0:
                if t == -1:
                    plt.suptitle('Hydraulic Data - Last Computational Step - ' + name_base)
                else:
                    plt.suptitle('Hydraulic Data - Computational Step: ' + str(t) + ' - ' + name_base)
                plt.title('Velocity by Cells')
                plt.xlabel('velocity [m/sec]')
                plt.ylabel('number of occurence')
            elif project_preferences['language'] == 1:
                if t == -1:
                    plt.suptitle('Histogramme de Données Hydrauliques - Dernier Pas de Temps/Débit - ' + name_base)
                else:
                    plt.suptitle('Histogramme de Données Hydrauliques - Pas de Temps/Débit: ' + str(t) + ' - ' +
                                 name_base)
                plt.title('Vitesse par cellule')
                plt.xlabel('vitesse [m/sec]')
                plt.ylabel('fréquence')
            else:
                if t == -1:
                    plt.suptitle('Hydraulic Data - Last Computational Step - ' + name_base)
                else:
                    plt.suptitle('Hydraulic Data - Computational Step: ' + str(t) + ' - ' + name_base)
                plt.title('Velocity by Cells')
                plt.xlabel('velocity [m/sec]')
                plt.ylabel('number of occurence')
            # height
            fig.add_subplot(222)
            plt.hist(height_app, 20, weights=area_app, facecolor='aquamarine')
            if project_preferences['language'] == 0:
                plt.title('Height by cells')
                plt.xlabel('velocity [m/sec]')
                plt.ylabel('number of occurence')
            elif project_preferences['language'] == 1:
                plt.title("Hauteur d'eau par cellule")
                plt.xlabel('hauteur [m]')
                plt.ylabel('fréquence')
            else:
                plt.title('Height by cells')
                plt.xlabel('velocity [m/sec]')
                plt.ylabel('number of occurence')
            # substrate
            fig.add_subplot(224)
            plt.hist(sub_pg_app, weights=area_app, facecolor='lightblue', bins=np.arange(0.5, 8.5))
            if project_preferences['language'] == 0:
                plt.title('Coarser substrate data')
                plt.xlabel('substrate - code cemagref')
                plt.ylabel('number of occurence')
            elif project_preferences['language'] == 1:
                plt.title('Données de substrat - Plus gros')
                plt.xlabel('substrat - code cemagref')
                plt.ylabel('fréquence')
            else:
                plt.title('Coarser substrate data')
                plt.xlabel('substrate - code cemagref')
                plt.ylabel('number of occurence')
            # debit unitaire
            fig.add_subplot(223)
            q_unit = np.array(vel_app) * np.array(height_app)
            plt.hist(q_unit, 20, weights=area_app, facecolor='deepskyblue')
            if project_preferences['language'] == 0:
                plt.title('Elementary flow')
                plt.xlabel('v * h * 1m [m$^{3}$/sec]')
                plt.ylabel('number of occurence')
            elif project_preferences['language'] == 1:
                plt.title('Début unitaire')
                plt.xlabel('v * h * 1m [m$^{3}$/sec]')
                plt.ylabel('fréquence')
            else:
                plt.title('Elementary flow')
                plt.xlabel('v * h * 1m [m$^{3}$/sec]')
                plt.ylabel('number of occurence')

            plt.tight_layout(rect=[0., 0., 1, 0.95])
            if not erase_id:
                if not sim_name:
                    name = 'Hist_Hydro' + name_base + '_t_' + str(t) + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                elif t - 1 >= 0:
                    name = 'Hist_Hydro' + name_base + '_t_' + sim_name[t - 1] + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                elif t == -1:
                    name = 'Hist_Hydro' + name_base + '_t_' + sim_name[-1] + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    name = 'Hist_Hydro' + name_base + '_t_' + str(t) + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                if not sim_name:
                    name = 'Hist_Hydro' + name_base + '_t_' + str(t) + '_All_Reach'
                elif t - 1 >= 0:
                    name = 'Hist_Hydro' + name_base + '_t_' + sim_name[t - 1] + '_All_Reach'
                elif t == -1:
                    name = 'Hist_Hydro' + name_base + '_t_' + sim_name[-1] + '_All_Reach'
                else:
                    name = 'Hist_Hydro' + name_base + '_t_' + str(t) + '_All_Reach'
                test = remove_image(name, path_im, format1)
                if not test:
                    return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)


def plot_hist_biology(vh_all_t_sp, area_c_all_t, name_fish, project_preferences, path_im, timestep, name_base, sim_name=[],
                      erase_id=False):
    """
    This function plot the historgram of the habitat value for the slected species and time step. This historgramm
    is weighted by the area of the cell.

    :param vh_all_t_sp: The habitat value by cell by reach by time step by species
    :param area_c_all_t: the area of each cell
    :param name_fish: the name of the fish chosen
    :param project_preferences: the figure options
    :param path_im: the path where to save the images
    :param timestep: a list with the time step to be plotted
    :param name_base: the base on which to form the figure name
    :param sim_name: the name of the time steps when not 0,1,2,3
    :param erase_id: If True, we erase a figure with an identical name
    """
    spu_all = []
    area_all = []

    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make figure ediable in adobe illustrator

    if max(timestep) - 1 > len(sim_name):
        sim_name = []

    for t in timestep:
        for s in range(0, len(vh_all_t_sp)):
            # add all reach together
            try:
                for r in range(0, len(area_c_all_t[t])):
                    if r == 0:
                        spu_all = list(vh_all_t_sp[s][t][0])
                        area_all = list(area_c_all_t[t][0])
                    else:
                        spu_all.extend(list(vh_all_t_sp[s][t][r]))
                        area_all.extend(list(area_c_all_t[t][r]))
            except IndexError:
                print('Error: The histrogram of the spu could not be created because the length of the '
                      'data was not coherent \n')
                return

            # plot four sub-figure by figure
            p = s % 4
            if p == 0:
                fig = plt.figure()
                fig.add_subplot(221)  # why (22p) does not work?
                if project_preferences['language'] == 0:
                    if t == -1:
                        plt.suptitle('Habitat Data - Last Computational Step - ' + name_base)
                    else:
                        plt.suptitle('Habitat Data - Computational Step: ' + str(t) + ' - ' + name_base)
                elif project_preferences['language'] == 1:
                    if t == -1:
                        plt.suptitle("Histogramme de Données d'Habitat - Dernier Pas de Temps/Débit - " + name_base)
                    else:
                        plt.suptitle("Histogramme de Données d'Habitat- Pas de Temps/Débit: " + str(t) + ' - ' +
                                     name_base)
                else:
                    if t == -1:
                        plt.suptitle('Habitat Data - Last Computational Step - ' + name_base)
                    else:
                        plt.suptitle('Habitat Data - Computational Step: ' + str(t) + ' - ' + name_base)
            if p == 1:
                fig.add_subplot(222)
            if p == 2:
                fig.add_subplot(223)
            if p == 3:
                fig.add_subplot(224)
            plt.hist(spu_all, weights=area_all, facecolor='lightblue', bins=np.arange(-0.05, 1.05, 0.1))
            if project_preferences['language'] == 0:
                plt.title('Habitat Value ' + name_fish[s])
                plt.xlabel('habitat value [ ]')
                plt.ylabel('number of occurence')
            elif project_preferences['language'] == 1:
                plt.title("Valeur d'Habitat " + name_fish[s])
                plt.xlabel("valeur d'habitat [ ] ")
                plt.ylabel('fréquence')
            else:
                plt.title('Habitat Value ' + name_fish[s])
                plt.xlabel('habitat value [ ]')
                plt.ylabel('number of occurence')
            plt.xlim(-0.07, 1.07)

            if p == 0 and s > 3 or s == len(vh_all_t_sp) - 1:
                plt.tight_layout(rect=[0., 0., 1, 0.95])
                if not erase_id:
                    if not sim_name:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + str(t) + '_All_Reach_' + \
                               time.strftime("%d_%m_%Y_at_%H_%M_%S")
                    elif t - 1 >= 0:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + sim_name[t - 1] + '_All_Reach_' + \
                               time.strftime("%d_%m_%Y_at_%H_%M_%S")
                    elif t == -1:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + sim_name[-1] + '_All_Reach_' + \
                               time.strftime("%d_%m_%Y_at_%H_%M_%S")
                    else:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + str(t) + '_All_Reach_' + \
                               time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    if not sim_name:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + str(t) + '_All_Reach'
                    elif t - 1 >= 0:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + sim_name[t - 1] + '_All_Reach'
                    elif t == -1:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + sim_name[-1] + '_All_Reach'
                    else:
                        name = 'Hist_Spu_' + name_base + str(s + 1) + '_t_' + str(t) + '_All_Reach'
                    test = remove_image(name, path_im, format1)
                    if not test:
                        return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)
