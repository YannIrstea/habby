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
import time
from io import StringIO
from struct import unpack, pack

import matplotlib.pyplot as plt
import numpy as np

from src import hdf5_mod
from src import manage_grid_mod
from src_GUI import preferences_GUI


def load_telemac_and_cut_grid(description_from_indexHYDRAU_file, progress_value, q=[], print_cmd=False, project_preferences={}):
    """
    This function calls the function load_telemac and call the function cut_2d_grid(). Orginally, this function
    was part of the TELEMAC class in Hydro_GUI_2.py but it was separated to be able to have a second thread, which
    is useful to avoid freezing the GUI.

    :param name_hdf5: the base name of the created hdf5 (string)
    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param units_index : List of integer values representing index of units (timestep or discharge). If not specify,
            all timestep are selected (from cmd command).
    :param q: used by the second thread to get the error back to the GUI at the end of the thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param project_preferences: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    """
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    minwh = project_preferences['min_height_hyd']

    # progress
    progress_value.value = 10

    # check if hydrau_description_multiple
    if type(description_from_indexHYDRAU_file) == dict:  # hydrau_description simple (one .hyd)
        file_number = 1
        description_from_indexHYDRAU_file = [description_from_indexHYDRAU_file]
    elif type(description_from_indexHYDRAU_file) == list:  # hydrau_description_multiple (several .hyd)
        file_number = len(description_from_indexHYDRAU_file)

    for hyd_file in range(0, file_number):
        filename_source = description_from_indexHYDRAU_file[hyd_file]["filename_source"].split(", ")

        # get data_2d_whole_profile
        data_2d_whole_profile = dict()
        data_2d_whole_profile["tin"] = [[]]  # always one reach
        data_2d_whole_profile["xy_center"] = [[]]  # always one reach
        data_2d_whole_profile["xy"] = [[]]  # always one reach
        data_2d_whole_profile["z"] = [[]]  # always one reach
        data_2d_whole_profile["unit_correspondence"] = [[]]  # always one reach
        for i, file in enumerate(filename_source):
            # _, _, xy, tin, xy_center, _ = load_telemac(file, pathfilet)
            data_2d_telemac, description_from_telemac_file = load_telemac(file, description_from_indexHYDRAU_file[hyd_file]["path_filename_source"])
            if data_2d_telemac == [-99] and description_from_telemac_file == [-99]:
                q.put(mystdout)
                return
            data_2d_whole_profile["tin"][0].append(data_2d_telemac["tin"])
            data_2d_whole_profile["xy_center"][0].append(data_2d_telemac["xy_center"])
            data_2d_whole_profile["xy"][0].append(data_2d_telemac["xy"])
            if description_from_telemac_file["hyd_unit_z_equal"]:
                data_2d_whole_profile["z"][0].append(data_2d_telemac["z"][0])
            elif not description_from_telemac_file["hyd_unit_z_equal"]:
                for unit_num in range(len(description_from_indexHYDRAU_file[hyd_file]["unit_list"])):
                    data_2d_whole_profile["z"][0].append(data_2d_telemac["z"][unit_num])

            data_2d_whole_profile["unit_correspondence"][0].append(str(i))

        # create temporary list sorted to check if the whole profiles are equal to the first one (sort xy_center)
        temp_list = data_2d_whole_profile["xy_center"][0]
        for i in range(len(temp_list)):
            temp_list[i].sort(axis=0)
        # TODO: sort function may be unadapted to check TIN equality between units
        whole_profil_egual_index = []
        for i in range(len(temp_list)):
            if i == 0:
                whole_profil_egual_index.append(i)
            if i > 0:
                if np.array_equal(temp_list[i], temp_list[0]):
                    whole_profil_egual_index.append(i)
                else:
                    whole_profil_egual_index.append("diff")
        if "diff" in whole_profil_egual_index:  # if "diff" in list : all tin are different (one tin by unit)
            data_2d_whole_profile["unit_correspondence"] = True
        if "diff" not in whole_profil_egual_index:  # one tin for all unit
            data_2d_whole_profile["tin"][0] = [data_2d_whole_profile["tin"][0][0]]
            data_2d_whole_profile["xy_center"][0] = [data_2d_whole_profile["xy_center"][0][0]]
            data_2d_whole_profile["xy"][0] = [data_2d_whole_profile["xy"][0][0]]
            data_2d_whole_profile["unit_correspondence"] = False

        # progress from 10 to 90 : from 0 to len(units_index)
        delta = int(80 / int(description_from_indexHYDRAU_file[hyd_file]["unit_number"]))

        # cut the grid to have the precise wet area and put data in new form
        data_2d = dict()
        data_2d["tin"] = [[]]  # always one reach
        data_2d["i_whole_profile"] = [[]]  # always one reach
        data_2d["xy"] = [[]]  # always one reach
        data_2d["h"] = [[]]  # always one reach
        data_2d["v"] = [[]]  # always one reach
        data_2d["z"] = [[]]  # always one reach
        data_2d["max_slope_bottom"] = [[]]  # always one reach
        data_2d["max_slope_energy"] = [[]]  # always one reach
        data_2d["shear_stress"] = [[]]  # always one reach
        data_2d["total_wet_area"] = [[]]
        # get unit list from telemac file
        file_list = description_from_indexHYDRAU_file[hyd_file]["filename_source"].split(", ")
        if len(file_list) > 1:
            unit_number_list = []
            unit_list_from_telemac_file_list = []
            for file_indexHYDRAU in file_list:
                unit_number, unit_list_from_telemac_file = get_time_step(
                    file_indexHYDRAU,
                    description_from_indexHYDRAU_file[hyd_file]["path_filename_source"])
                unit_number_list.append(unit_number)
                unit_list_from_telemac_file_list.append(unit_list_from_telemac_file)
        if len(file_list) == 1:
            unit_number, unit_list_from_telemac_file = get_time_step(
                description_from_indexHYDRAU_file[hyd_file]["filename_source"],
                description_from_indexHYDRAU_file[hyd_file]["path_filename_source"])
        # get unit list from indexHYDRAU file
        if "timestep_list" in description_from_indexHYDRAU_file[hyd_file].keys():
            unit_list_from_indexHYDRAU_file = description_from_indexHYDRAU_file[hyd_file]["timestep_list"]
        else:
            unit_list_from_indexHYDRAU_file = description_from_indexHYDRAU_file[hyd_file]["unit_list"]
        # get unit index to load
        if len(unit_list_from_telemac_file) == 1 and len(unit_list_from_indexHYDRAU_file) == 1:
            unit_index_list = [0]
        else:
            if len(file_list) > 1:
                if list(set(unit_number_list))[0] == 1:  # one time step by file
                    unit_index_list = [0] * len(file_list)
                if list(set(unit_number_list))[0] > 1:  # several time step by file
                    unit_index_list = []
                    for i, time_step in enumerate(unit_list_from_indexHYDRAU_file):
                        if time_step in unit_list_from_telemac_file_list[i]:
                            unit_index_list.append(unit_list_from_telemac_file_list[i].index(time_step))
            else:
                unit_index_list = []  # for all cases with specific timestep indicate
                for unit_wish in unit_list_from_indexHYDRAU_file:
                    if unit_wish in unit_list_from_telemac_file:
                        unit_index_list.append(unit_list_from_telemac_file.index(unit_wish))

        if not data_2d_whole_profile["unit_correspondence"]:
            # conca xy with z value to facilitate the cutting of the grid (interpolation)
            xy = np.insert(data_2d_telemac["xy"],
                           2,
                           values=data_2d_telemac["z"][0],
                           axis=1)  # Insert values before column 2
        else:
            data_2d_telemac, description_from_telemac_file = load_telemac(file,
                                                                          description_from_indexHYDRAU_file[
                                                                              hyd_file]["path_filename_source"])

        for i, unit_num in enumerate(unit_index_list):
            if len(file_list) > 1:
                data_2d_telemac, description_from_telemac_file = load_telemac(file_list[i],
                                                                              description_from_indexHYDRAU_file[
                                                                                  hyd_file]["path_filename_source"])
                # conca xy with z value to facilitate the cutting of the grid (interpolation)
                xy = np.insert(data_2d_telemac["xy"],
                               2,
                               values=data_2d_telemac["z"][unit_num],
                               axis=1)  # Insert values before column 2

            [tin_data, xy_cuted, h_data, v_data, ind_new] = manage_grid_mod.cut_2d_grid(data_2d_telemac["tin"],
                                                                                        xy,
                                                                                        # with z value (facilitate)
                                                                                        data_2d_telemac["h"][
                                                                                            unit_num],
                                                                                        data_2d_telemac["v"][
                                                                                            unit_num],
                                                                                        progress_value,
                                                                                        delta,
                                                                                        project_preferences[
                                                                                            "CutMeshPartialyDry"],
                                                                                        minwh)

            if not isinstance(tin_data, np.ndarray):
                print("Error: cut_2d_grid")
                q.put(mystdout)
                return

            max_slope_bottom, max_slope_energy, shear_stress = manage_grid_mod.slopebottom_lopeenergy_shearstress_max(
                xy1=xy_cuted[tin_data[:, 0]][:, [0, 1]],
                z1=xy_cuted[tin_data[:, 0]][:, 2],
                h1=h_data[tin_data[:, 0]],
                v1=v_data[tin_data[:, 0]],
                xy2=xy_cuted[tin_data[:, 1]][:, [0, 1]],
                z2=xy_cuted[tin_data[:, 1]][:, 2],
                h2=h_data[tin_data[:, 1]],
                v2=v_data[tin_data[:, 1]],
                xy3=xy_cuted[tin_data[:, 2]][:, [0, 1]],
                z3=xy_cuted[tin_data[:, 2]][:, 2],
                h3=h_data[tin_data[:, 2]],
                v3=v_data[tin_data[:, 2]])

            # get points coord
            pa = xy_cuted[tin_data[:, 0]][:, [0, 1]]
            pb = xy_cuted[tin_data[:, 1]][:, [0, 1]]
            pc = xy_cuted[tin_data[:, 2]][:, [0, 1]]

            # # get area (based on Heron's formula)
            # d1 = np.sqrt((pb[:, 0] - pa[:, 0]) ** 2 + (pb[:, 1] - pa[:, 1]) ** 2)
            # d2 = np.sqrt((pc[:, 0] - pb[:, 0]) ** 2 + (pc[:, 1] - pb[:, 1]) ** 2)
            # d3 = np.sqrt((pc[:, 0] - pa[:, 0]) ** 2 + (pc[:, 1] - pa[:, 1]) ** 2)
            # s2 = (d1 + d2 + d3) / 2
            # area = s2 * (s2 - d1) * (s2 - d2) * (s2 - d3)
            # area[area < 0] = 0  # -1e-11, -2e-12, etc because some points are so close
            # area = area ** 0.5
            # area_reach = np.sum(area)

            # get area2
            area = 0.5 * abs((pb[:, 0] - pa[:, 0]) * (pc[:, 1] - pa[:, 1]) - (pc[:, 0] - pa[:, 0]) * (pb[:, 1] - pa[:, 1]))
            area_reach = np.sum(area)

            # save data in dict
            data_2d["tin"][0].append(tin_data)
            data_2d["i_whole_profile"][0].append(ind_new)
            data_2d["xy"][0].append(xy_cuted[:, :2])
            data_2d["h"][0].append(h_data)
            data_2d["v"][0].append(v_data)
            data_2d["z"][0].append(xy_cuted[:, 2])
            data_2d["max_slope_bottom"][0].append(max_slope_bottom)
            data_2d["max_slope_energy"][0].append(max_slope_energy)
            data_2d["shear_stress"][0].append(shear_stress)
            data_2d["total_wet_area"][0].append(area_reach)

        # ALL CASE SAVE TO HDF5
        progress_value.value = 90  # progress

        # hyd description
        hyd_description = dict()
        hyd_description["hyd_filename_source"] = description_from_indexHYDRAU_file[hyd_file]["filename_source"]
        hyd_description["hyd_model_type"] = description_from_indexHYDRAU_file[hyd_file]["model_type"]
        hyd_description["hyd_model_dimension"] = description_from_indexHYDRAU_file[hyd_file]["model_dimension"]
        hyd_description["hyd_variables_list"] = "h, v, z"
        hyd_description["hyd_epsg_code"] = description_from_indexHYDRAU_file[hyd_file]["epsg_code"]
        hyd_description["hyd_reach_list"] = description_from_indexHYDRAU_file[hyd_file]["reach_list"]
        hyd_description["hyd_reach_number"] = description_from_indexHYDRAU_file[hyd_file]["reach_number"]
        hyd_description["hyd_reach_type"] = description_from_indexHYDRAU_file[hyd_file]["reach_type"]
        hyd_description["hyd_unit_list"] = [description_from_indexHYDRAU_file[hyd_file]["unit_list"]]
        hyd_description["hyd_unit_number"] = description_from_indexHYDRAU_file[hyd_file]["unit_number"]
        hyd_description["hyd_unit_type"] = description_from_indexHYDRAU_file[hyd_file]["unit_type"]
        hyd_description["hyd_varying_mesh"] = data_2d_whole_profile["unit_correspondence"]
        hyd_description["hyd_cuted_mesh_partialy_dry"] = project_preferences["CutMeshPartialyDry"]

        if hyd_description["hyd_varying_mesh"]:
            hyd_description["hyd_unit_z_equal"] = False
        else:
            # TODO : check if all z values are equal between units
            hyd_description["hyd_unit_z_equal"] = True

        del data_2d_whole_profile['unit_correspondence']
        # if not project_preferences["CutMeshPartialyDry"]:
        #     namehdf5_old = os.path.splitext(description_from_indexHYDRAU_file[hyd_file]["hdf5_name"])[0]
        #     exthdf5_old = os.path.splitext(description_from_indexHYDRAU_file[hyd_file]["hdf5_name"])[1]
        #     description_from_indexHYDRAU_file[hyd_file]["hdf5_name"] = namehdf5_old + "_no_cut" + exthdf5_old

        # remove unused keys
        del data_2d_whole_profile["xy_center"]

        # create hdf5
        hdf5 = hdf5_mod.Hdf5Management(description_from_indexHYDRAU_file[hyd_file]["path_prj"],
                                       description_from_indexHYDRAU_file[hyd_file]["hdf5_name"])
        hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description, project_preferences)

        # progress
        progress_value.value = 100

    if not print_cmd:
        # create_indexHYDRAU_text_file
        create_indexHYDRAU_text_file(description_from_indexHYDRAU_file)
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_telemac(namefilet, pathfilet):
    """
    A function which load the telemac data using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: the velocity, the height, the coordinate of the points of the grid, the connectivity table.
    """
    faiload = [-99], [-99]

    filename_path_res = os.path.join(pathfilet, namefilet)
    # load the data and do some test
    if not os.path.isfile(filename_path_res):
        print('Error: The telemac file does not exist. Cannot be loaded.')
        return faiload
    blob, ext = os.path.splitext(namefilet)
    if ext != '.res' and ext != '.slf':
        print('Warning: The extension of the telemac file is not .res or .slf')
    try:
        telemac_data = Selafin(filename_path_res)
    except ValueError or KeyError:
        print('Error: The telemac file cannot be loaded.')
        return faiload

    # time step name
    nbtimes = telemac_data.tags['times'].size
    timestep = telemac_data.tags['times']

    # put the velocity and height data in the array and list
    v = []
    h = []
    z = []
    for t in range(0, nbtimes):
        foundu = foundv = False
        val_all = telemac_data.getvalues(t)
        vt = []
        ht = []
        zt = []
        bt = []
        # load variable based on their name (english or french)
        for id, n in enumerate(telemac_data.varnames):
            n = n.decode('utf-8')
            if 'VITESSE MOY' in n or 'MEAN VELOCITY' in n:
                vt = val_all[:, id]
            if 'VITESSE U' in n or 'VELOCITY U' in n:
                vu = val_all[:, id]
                foundu = True
            if 'VITESSE V' in n or 'VELOCITY V' in n:
                vv = val_all[:, id]
                foundv = True
            if 'WATER DEPTH' in n or "HAUTEUR D'EAU" in n:
                ht = val_all[:, id]
            if 'FOND' in n or 'BOTTOM' in n:
                bt = val_all[:, id]

        if foundu and foundv:
            vt = np.sqrt(vu ** 2 + vv ** 2)

        if len(vt) == 0:
            print('Error: The variable name of the telemec file were not recognized. (1) \n')
            return faiload
        if len(ht) == 0:
            print('Error: The variable name of the telemec file were not recognized. (2) \n')
            return faiload
        v.append(vt)
        h.append(ht)
        z.append(bt)
    # TODO: improve check equality
    if all(z[0] == z[nbtimes - 1]):  # first == last
        #print("all z are equal for each time step")
        all_z_equal = True
        #coord_p = np.array([telemac_data.meshx, telemac_data.meshy, z[0]])
    else:
        all_z_equal = False
    coord_p = np.array([telemac_data.meshx, telemac_data.meshy])
    coord_p = coord_p.T
    ikle = telemac_data.ikle2

    # get the center of the cell
    # center of element
    p1 = coord_p[ikle[:, 0], :]
    p2 = coord_p[ikle[:, 1], :]
    p3 = coord_p[ikle[:, 2], :]
    coord_c_x = 1.0 / 3.0 * (p1[:, 0] + p2[:, 0] + p3[:, 0])
    coord_c_y = 1.0 / 3.0 * (p1[:, 1] + p2[:, 1] + p3[:, 1])
    coord_c = np.array([coord_c_x, coord_c_y]).T

    # description telemac data dict
    description_from_telemac_file = dict()
    description_from_telemac_file["hyd_filename_source"] = namefilet
    description_from_telemac_file["hyd_model_type"] = "TELEMAC"
    description_from_telemac_file["hyd_model_dimension"] = str(2)
    description_from_telemac_file["hyd_unit_list"] = ", ".join(list(map(str, timestep)))
    description_from_telemac_file["hyd_unit_number"] = str(len(list(map(str, timestep))))
    description_from_telemac_file["hyd_unit_type"] = "timestep"
    description_from_telemac_file["hyd_unit_z_equal"] = all_z_equal

    # data 2d dict
    data_2d = dict()
    data_2d["h"] = np.array(h, dtype=np.float64)
    data_2d["v"] = np.array(v, dtype=np.float64)
    data_2d["z"] = np.array(z, dtype=np.float64)
    data_2d["xy"] = coord_p
    data_2d["tin"] = ikle
    data_2d["xy_center"] = coord_c

    del telemac_data
    #     return v, h, coord_p, ikle, coord_c, timestep
    return data_2d, description_from_telemac_file


def create_indexHYDRAU_text_file(description_from_indexHYDRAU_file):
    """ ONE HDF5 """
    # one case (one hdf5 produced)
    if len(description_from_indexHYDRAU_file) == 1:
        filename_path = os.path.join(description_from_indexHYDRAU_file[0]["path_prj"], "input", "indexHYDRAU.txt")
        # telemac case
        telemac_case = description_from_indexHYDRAU_file[0]["hydrau_case"]

        # column filename
        filename_column = description_from_indexHYDRAU_file[0]["filename_source"].split(", ")

        # nb_row
        nb_row = len(filename_column)

        """ CASE unknown """
        if telemac_case == "unknown":
            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            time_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]

            # headers
            headers = "filename" + "\t" + "T[" + time_unit + "]"

            # first line
            if description_from_indexHYDRAU_file[0]["unit_list"] == \
                    description_from_indexHYDRAU_file[0]["unit_list_full"]:
                unit_data = "all"
            else:
                index = [i for i, item in enumerate(description_from_indexHYDRAU_file[0]["unit_list_full"]) if
                         item in description_from_indexHYDRAU_file[0]["unit_list"]]
                my_sequences = []
                for idx, item in enumerate(index):
                    if not idx or item - 1 != my_sequences[-1][-1]:
                        my_sequences.append([item])
                    else:
                        my_sequences[-1].append(item)
                from_to_string_list = []
                for sequence in my_sequences:
                    start = min(sequence)
                    start_string = description_from_indexHYDRAU_file[0]["unit_list_full"][start]
                    end = max(sequence)
                    end_string = description_from_indexHYDRAU_file[0]["unit_list_full"][end]
                    if start == end:
                        start_end_string = start_string
                    if start != end:
                        start_end_string = start_string + "/" + end_string
                    from_to_string_list.append(start_end_string)
                unit_data = ";".join(from_to_string_list)
            linetowrite = filename_column[0] + "\t" + unit_data

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 1.a """
        if telemac_case == "1.a":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # first line
            linetowrite = filename_column[0] + "\t" + str(description_from_indexHYDRAU_file[0]["unit_list"][0])
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 1.b """
        if telemac_case == "1.b":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]" + "\t" + "T[s]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # first line
            linetowrite = filename_column[0] + "\t" + str(description_from_indexHYDRAU_file[0]["unit_list"][0])
            linetowrite = linetowrite + "\t" + description_from_indexHYDRAU_file[0]["unit_list_full"][0]
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column
            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 2.a """
        if telemac_case == "2.a":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # lines
            linetowrite = ""
            for row in range(nb_row):
                linetowrite += filename_column[row] + "\t" + str(description_from_indexHYDRAU_file[0]["unit_list"][row])
                if reach_column_presence:
                    linetowrite = linetowrite + "\t" + reach_column + "\n"
                else:
                    linetowrite = linetowrite + "\n"
            # remove last "\n"
            linetowrite = linetowrite[:-1]

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 2.b """
        if telemac_case == "2.b":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]" + "\t" + "T[s]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # lines
            linetowrite = ""
            for row in range(nb_row):
                linetowrite += filename_column[row] + "\t" + str(
                    description_from_indexHYDRAU_file[0]["unit_list"][row]) + "\t" + description_from_indexHYDRAU_file[0]["timestep_list"][row]
                if reach_column_presence:
                    linetowrite = linetowrite + "\t" + reach_column + "\n"
                else:
                    linetowrite = linetowrite + "\n"
            # remove last "\n"
            linetowrite = linetowrite[:-1]

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 3.a 3.b """
        if telemac_case == "3.a" or telemac_case == "3.b":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            time_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "T[" + time_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"

            # first line
            if description_from_indexHYDRAU_file[0]["unit_list"] == description_from_indexHYDRAU_file[0]["unit_list_full"]:
                unit_data = "all"
            else:
                index = [i for i, item in enumerate(description_from_indexHYDRAU_file[0]["unit_list_full"]) if item in description_from_indexHYDRAU_file[0]["unit_list"]]
                my_sequences = []
                for idx, item in enumerate(index):
                    if not idx or item - 1 != my_sequences[-1][-1]:
                        my_sequences.append([item])
                    else:
                        my_sequences[-1].append(item)
                from_to_string_list = []
                for sequence in my_sequences:
                    start = min(sequence)
                    start_string = description_from_indexHYDRAU_file[0]["unit_list_full"][start]
                    end = max(sequence)
                    end_string = description_from_indexHYDRAU_file[0]["unit_list_full"][end]
                    if start == end:
                        start_end_string = start_string
                    if start != end:
                        start_end_string = start_string + "/" + end_string
                    from_to_string_list.append(start_end_string)

                unit_data = ";".join(from_to_string_list)
            linetowrite = filename_column[0] + "\t" + unit_data
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column
            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        # write text file
        with open(filename_path, 'wt') as f:
            f.write(text)

    """ MULTI HDF5 """
    # multi case (several hdf5 produced)
    if len(description_from_indexHYDRAU_file) > 1:
        if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
            reach_column_presence = False
        else:
            reach_column_presence = True
            reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

        unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
        start = unit_type.find('[')
        end = unit_type.find(']')
        time_unit = unit_type[start + 1:end]
        # epsg_code
        epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
        # headers
        headers = "filename" + "\t" + "T[" + time_unit + "]"
        if reach_column_presence:
            headers = headers + "\t" + "reachname"

        # text
        text = epsg_code + "\n" + headers

        for i_hdf5, hdf5_file in enumerate(range(len(description_from_indexHYDRAU_file))):
            filename_path = os.path.join(description_from_indexHYDRAU_file[i_hdf5]["path_prj"], "input", "indexHYDRAU.txt")
            # telemac case
            telemac_case = description_from_indexHYDRAU_file[i_hdf5]["hydrau_case"]

            # column filename
            filename_column = description_from_indexHYDRAU_file[i_hdf5]["filename_source"].split(", ")

            if telemac_case == "4.a" or telemac_case == "4.b" or telemac_case == "unknown":
                if description_from_indexHYDRAU_file[i_hdf5]["reach_list"] == "unknown":
                    reach_column_presence = False
                else:
                    reach_column_presence = True
                    reach_column = description_from_indexHYDRAU_file[i_hdf5]["reach_list"].split(", ")[0]

                # first line
                if description_from_indexHYDRAU_file[i_hdf5]["unit_list"] == description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"]:
                    unit_data = "all"
                else:
                    index = [i for i, item in enumerate(description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"]) if item in description_from_indexHYDRAU_file[i_hdf5]["unit_list"]]
                    my_sequences = []
                    for idx, item in enumerate(index):
                        if not idx or item - 1 != my_sequences[-1][-1]:
                            my_sequences.append([item])
                        else:
                            my_sequences[-1].append(item)
                    from_to_string_list = []
                    for sequence in my_sequences:
                        start = min(sequence)
                        start_string = description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"][start]
                        end = max(sequence)
                        end_string = description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"][end]
                        if start == end:
                            start_end_string = start_string
                        if start != end:
                            start_end_string = start_string + "/" + end_string
                        from_to_string_list.append(start_end_string)

                    unit_data = ";".join(from_to_string_list)
                linetowrite = filename_column[0] + "\t" + unit_data
                if reach_column_presence:
                    linetowrite = linetowrite + "\t" + reach_column

                text = text + "\n" + linetowrite

        # write text file
        with open(filename_path, 'wt') as f:
            f.write(text)


def get_time_step(namefilet, pathfilet):
    """
    A function which load the telemac time step using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: timestep
    """
    faiload = [-99], [-99], [-99], [-99], [-99], [-99]

    filename_path_res = os.path.join(pathfilet, namefilet)
    # load the data and do some test
    if not os.path.isfile(filename_path_res):
        print('Error: The telemac file does not exist. Cannot be loaded.')
        return faiload
    blob, ext = os.path.splitext(namefilet)
    if ext != '.res' and ext != '.slf' and ext != '.srf':
        print('Warning: The extension of the telemac file is not .res or .slf or .srf')
    try:
        telemac_data = Selafin(filename_path_res)
    except ValueError or KeyError:
        print('Error: The telemac file cannot be loaded.')
        return faiload

    # time step name
    nbtimes = telemac_data.tags['times'].size
    timestep = telemac_data.tags['times']
    timestep_string = []
    for i in range(len(timestep)):
        timestep_string.append(str(timestep[i]))

    return nbtimes, timestep_string


def plot_vel_h(coord_p2, h, v, path_im, timestep=[-1]):
    """
     a function to plot the velocity and height which are the output from TELEMAC. It is used to debug.
     It is not used direclty by HABBY.

     :param coord_p2: the coordinates of the point forming the grid
     :param h: the  water height
     :param v: the velocity
     :param path_im: the path where the image should be saved (string)
     :param timestep: which time step should be plotted
    """
    # plt.rcParams['figure.figsize'] = 7, 3
    # plt.close()
    plt.rcParams['font.size'] = 10

    for i in timestep:
        plt.figure()
        cm = plt.cm.get_cmap('terrain')
        sc = plt.scatter(coord_p2[:, 0], coord_p2[:, 1], c=h[i], vmin=np.nanmin(h[i]), vmax=np.nanmax(h[i]), s=6,
                         cmap=cm,
                         edgecolors='none')
        # sc = plt.tricontourf(coord_p2[:,0], coord_p2[:,1], ikle_all[r], h[i], min=0, max=np.nanmax(h[i]), cmap=cm)
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Telemac data - water height at time step ' + str(i))
        cbar = plt.colorbar()
        cbar.ax.set_ylabel('Water height [m]')
        plt.savefig(os.path.join(path_im, "telemac_height_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'))
        plt.savefig(os.path.join(path_im, "telemac_height_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'))
        # plt.close()

        plt.figure()
        cm = plt.cm.get_cmap('terrain')
        sc = plt.scatter(coord_p2[:, 0], coord_p2[:, 1], c=v[i], vmin=np.nanmin(v[i]), vmax=np.nanmax(v[i]), s=6,
                         cmap=cm,
                         edgecolors='none')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Telemac data - velocity at time step ' + str(i))
        cbar = plt.colorbar()
        cbar.ax.set_ylabel('Velocity [m/s]')
        plt.savefig(os.path.join(path_im, "telemac_vel_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'))
        plt.savefig(os.path.join(path_im, "telemac_vel_t" + str(i) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'))
        # plt.close()
    # plt.show()


def getendianfromchar(fileslf, nchar):
    """
    Get the endian encoding
        "<" means little-endian
        ">" means big-endian
    """
    pointer = fileslf.tell()
    endian = ">"
    l, c, chk = unpack(endian + 'i' + str(nchar) + 'si', \
                       fileslf.read(4 + nchar + 4))
    if chk != nchar:
        endian = "<"
        fileslf.seek(pointer)
        l, c, chk = unpack(endian + 'i' + str(nchar) + 'si', \
                           fileslf.read(4 + nchar + 4))
    if l != chk:
        print('Error: ... Cannot read ' + str(nchar) + \
              ' characters from your binary file')
        print('     +> Maybe it is the wrong file format ?')
    fileslf.seek(pointer)
    return endian


def getfloattypefromfloat(fileslf, endian, nfloat):
    """
    Get float precision
    """
    pointer = fileslf.tell()
    ifloat = 4
    cfloat = 'f'
    l = unpack(endian + 'i', fileslf.read(4))
    if l[0] != ifloat * nfloat:
        ifloat = 8
        cfloat = 'd'
    r = unpack(endian + str(nfloat) + cfloat, fileslf.read(ifloat * nfloat))
    chk = unpack(endian + 'i', fileslf.read(4))
    if l != chk:
        print('Error: ... Cannot read ' + str(nfloat) + ' floats from your binary file')
        print('     +> Maybe it is the wrong file format ?')
    fileslf.seek(pointer)
    return cfloat, ifloat


class Selafin(object):
    """
    Selafin file format reader for Telemac 2D. Create an object for reading data from a slf file.
    Adapted from the original script 'parserSELAFIN.py' from the open Telemac distribution.

    :param filename: the name of the binary Selafin file
    """

    def __init__(self, filename):
        self.file = {}
        self.file.update({'name': filename})
        # "<" means little-endian, ">" means big-endian
        self.file.update({'endian': ">"})
        self.file.update({'float': ('f', 4)})  # 'f' size 4, 'd' = size 8
        self.datetime = [0, 0, 0, 0, 0, 0]
        if filename != '':
            self.file.update({'hook': open(filename, 'rb')})
            # ~~> checks endian encoding
            self.file['endian'] = getendianfromchar(self.file['hook'], 80)
            # ~~> header parameters
            self.tags = {'meta': self.file['hook'].tell()}
            self.getheadermetadataslf()
            # ~~> sizes and connectivity
            self.getheaderintegersslf()
            # ~~> checks float encoding
            self.file['float'] = getfloattypefromfloat(self.file['hook'], \
                                                       self.file['endian'], self.npoin3)
            # ~~> xy mesh
            self.getheaderfloatsslf()
            # ~~> time series
            self.tags = {'cores': [], 'times': []}
            self.gettimehistoryslf()
        else:
            self.title = ''
            self.nbv1 = 0
            self.nbv2 = 0
            self.nvar = self.nbv1 + self.nbv2
            self.varindex = range(self.nvar)
            self.iparam = []
            self.nelem3 = 0
            self.npoin3 = 0
            self.ndp3 = 0
            self.nplan = 1
            self.nelem2 = 0
            self.npoin2 = 0
            self.ndp2 = 0
            self.nbv1 = 0
            self.varnames = []
            self.varunits = []
            self.nbv2 = 0
            self.cldnames = []
            self.cldunits = []
            self.ikle3 = []
            self.ikle2 = []
            self.ipob2 = []
            self.ipob3 = []
            self.meshx = []
            self.meshy = []
            self.tags = {'cores': [], 'times': []}
        self.fole = {}
        self.fole.update({'name': ''})
        self.fole.update({'endian': self.file['endian']})
        self.fole.update({'float': self.file['float']})
        self.tree = None
        self.neighbours = None
        self.edges = None

    def getheadermetadataslf(self):
        """
        Get header information
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        # ~~ Read title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        l, self.title, chk = unpack(endian + 'i80si', fileslf.read(4 + 80 + 4))
        # ~~ Read NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        l, self.nbv1, self.nbv2, chk = \
            unpack(endian + 'iiii', fileslf.read(4 + 8 + 4))
        self.nvar = self.nbv1 + self.nbv2
        self.varindex = range(self.nvar)
        # ~~ Read variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.varnames = []
        self.varunits = []
        for _ in range(self.nbv1):
            l, vn, vu, chk = unpack(endian + 'i16s16si', \
                                    fileslf.read(4 + 16 + 16 + 4))
            self.varnames.append(vn)
            self.varunits.append(vu)
        self.cldnames = []
        self.cldunits = []
        for _ in range(self.nbv2):
            l, vn, vu, chk = unpack(endian + 'i16s16si', \
                                    fileslf.read(4 + 16 + 16 + 4))
            self.cldnames.append(vn)
            self.cldunits.append(vu)
        # ~~ Read iparam array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        d = unpack(endian + '12i', fileslf.read(4 + 40 + 4))
        self.iparam = np.asarray(d[1:11])
        # ~~ Read DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if self.iparam[9] == 1:
            d = unpack(endian + '8i', fileslf.read(4 + 24 + 4))
            self.datetime = np.asarray(d[1:9])

    def getheaderintegersslf(self):
        """
        Get dimensions and descritions (mesh)
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        # ~~ Read nelem3, npoin3, ndp3, nplan ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        l, self.nelem3, self.npoin3, self.ndp3, self.nplan, chk = \
            unpack(endian + '6i', fileslf.read(4 + 16 + 4))
        self.nelem2 = self.nelem3
        self.npoin2 = self.npoin3
        self.ndp2 = self.ndp3
        self.nplan = max(1, self.nplan)
        if self.iparam[6] > 1:
            self.nplan = self.iparam[6]  # /!\ How strange is that ?
            self.nelem2 = self.nelem3 / (self.nplan - 1)
            self.npoin2 = self.npoin3 / self.nplan
            self.ndp2 = self.ndp3 / 2
        # ~~ Read the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        fileslf.seek(4, 1)
        self.ikle3 = np.array(unpack(endian + str(self.nelem3 * self.ndp3) \
                                     + 'i', fileslf.read(4 * self.nelem3 * self.ndp3))) - 1
        fileslf.seek(4, 1)
        self.ikle3 = self.ikle3.reshape((self.nelem3, self.ndp3))
        if self.nplan > 1:
            self.ikle2 = np.compress(np.repeat([True, False], self.ndp2), \
                                     self.ikle3[0:self.nelem2], axis=1)
        else:
            self.ikle2 = self.ikle3
        # ~~ Read the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        fileslf.seek(4, 1)
        self.ipob3 = np.asarray(unpack(endian + str(self.npoin3) + 'i', \
                                       fileslf.read(4 * self.npoin3)))
        fileslf.seek(4, 1)
        self.ipob2 = self.ipob3[0:self.npoin2]

    def getheaderfloatsslf(self):
        """
        Get the mesh coordinates
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        # ~~ Read the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
        ftype, fsize = self.file['float']
        fileslf.seek(4, 1)
        self.meshx = np.asarray(unpack(endian + str(self.npoin3) + ftype, \
                                       fileslf.read(fsize * self.npoin3))[0:self.npoin2])
        fileslf.seek(4, 1)
        # ~~ Read the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~
        fileslf.seek(4, 1)
        self.meshy = np.asarray(unpack(endian + str(self.npoin3) + ftype, \
                                       fileslf.read(fsize * self.npoin3))[0:self.npoin2])
        fileslf.seek(4, 1)

    def gettimehistoryslf(self):
        """
        Get the timesteps
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        ftype, fsize = self.file['float']
        ats = []
        att = []
        while True:
            try:
                att.append(fileslf.tell())
                # ~~ Read AT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                fileslf.seek(4, 1)
                ats.append(unpack(endian + ftype, fileslf.read(fsize))[0])
                fileslf.seek(4, 1)
                # ~~ Skip Values ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                fileslf.seek(self.nvar * (4 + fsize * self.npoin3 + 4), 1)
            except:
                att.pop(len(att) - 1)  # since the last record failed the try
                break
        self.tags.update({'cores': att})
        self.tags.update({'times': np.asarray(ats)})

    def getvariablesat(self, frame, varindexes):
        """
        Get the values for the variables at a particular time step
        """
        fileslf = self.file['hook']
        endian = self.file['endian']
        ftype, fsize = self.file['float']
        if fsize == 4:
            z = np.zeros((len(varindexes), self.npoin3), dtype=np.float32)
        else:
            z = np.zeros((len(varindexes), self.npoin3), dtype=np.float64)
        # if tags has 31 frames, len(tags)=31 from 0 to 30,
        # then frame should be >= 0 and < len(tags)
        if frame < len(self.tags['cores']) and frame >= 0:
            fileslf.seek(self.tags['cores'][frame])
            fileslf.seek(4 + fsize + 4, 1)
            for ivar in range(self.nvar):
                fileslf.seek(4, 1)
                if ivar in varindexes:
                    z[varindexes.index(ivar)] = unpack(endian + \
                                                       str(self.npoin3) + ftype, \
                                                       fileslf.read(fsize * self.npoin3))
                else:
                    fileslf.seek(fsize * self.npoin3, 1)
                fileslf.seek(4, 1)
        return z

    def getvalues(self, t):
        """
        Get the values for the variables at time t
        """
        varsor = self.getvariablesat(t, self.varindex)
        return varsor.transpose()

    def appendheaderslf(self):
        """
        Write the header file
        """
        f = self.fole['hook']
        endian = self.fole['endian']
        ftype, fsize = self.fole['float']
        # ~~ Write title ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i80si', 80, self.title, 80))
        # ~~ Write NBV(1) and NBV(2) ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'iiii', 4 + 4, self.nbv1, self.nbv2, 4 + 4))
        # ~~ Write variable names and units ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        for i in range(self.nbv1):
            f.write(pack(endian + 'i', 32))
            f.write(pack(endian + '16s', self.varnames[i]))
            f.write(pack(endian + '16s', self.varunits[i]))
            f.write(pack(endian + 'i', 32))
        for i in range(self.nbv2):
            f.write(pack(endian + 'i', 32))
            f.write(pack(endian + '16s', self.cldnames[i]))
            f.write(pack(endian + '16s', self.cldunits[i]))
            f.write(pack(endian + 'i', 32))
        # ~~ Write IPARAM array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', 4 * 10))
        for i in range(len(self.iparam)):
            f.write(pack(endian + 'i', self.iparam[i]))
        f.write(pack(endian + 'i', 4 * 10))
        # ~~ Write DATE/TIME array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if self.iparam[9] == 1:
            f.write(pack(endian + 'i', 4 * 6))
            for i in range(6):
                f.write(pack(endian + 'i', self.datetime[i]))
            f.write(pack(endian + 'i', 4 * 6))
        # ~~ Write NELEM3, NPOIN3, NDP3, NPLAN ~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + '6i', 4 * 4, self.nelem3, self.npoin3, \
                     self.ndp3, 1, 4 * 4))  # /!\ where is NPLAN ?
        # ~~ Write the IKLE array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', 4 * self.nelem3 * self.ndp3))
        f.write(pack(endian + str(self.nelem3 * self.ndp3) + 'i', *(self.ikle3.ravel() + 1)))
        f.write(pack(endian + 'i', 4 * self.nelem3 * self.ndp3))
        # ~~ Write the IPOBO array ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', 4 * self.npoin3))
        f.write(pack(endian + str(self.npoin3) + 'i', *(self.ipob3)))
        f.write(pack(endian + 'i', 4 * self.npoin3))
        # ~~ Write the x-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', fsize * self.npoin3))
        # f.write(pack(endian+str(self.NPOIN3)+ftype,*(np.tile(self.MESHX,self.NPLAN))))
        for i in range(self.nplan):
            f.write(pack(endian + str(self.npoin2) + ftype, *(self.meshx)))
        f.write(pack(endian + 'i', fsize * self.npoin3))
        # ~~ Write the y-coordinates of the nodes ~~~~~~~~~~~~~~~~~~~~~~~
        f.write(pack(endian + 'i', fsize * self.npoin3))
        # f.write(pack(endian+str(self.NPOIN3)+ftype,*(np.tile(self.MESHY,self.NPLAN))))
        for i in range(self.nplan):
            f.write(pack(endian + str(self.npoin2) + ftype, *(self.meshy)))
        f.write(pack(endian + 'i', fsize * self.npoin3))

    def appendcoretimeslf(self, t):
        f = self.fole['hook']
        endian = self.fole['endian']
        ftype, fsize = self.fole['float']
        # Print time record
        # if type(t) == type(0.0):
        f.write(pack(endian + 'i' + ftype + 'i', fsize, t, fsize))
        # else:
        #    f.write(pack(endian + 'i' + ftype + 'i', fsize, self.tags['times'][t], fsize))

    def appendcorevarsslf(self, varsor):
        f = self.fole['hook']
        endian = self.fole['endian']
        ftype, fsize = self.fole['float']
        # Print variable records
        for v in varsor.transpose():
            f.write(pack(endian + 'i', fsize * self.npoin3))
            f.write(pack(endian + str(self.npoin3) + ftype, *(v)))
            f.write(pack(endian + 'i', fsize * self.npoin3))

    def putcontent(self, fileName, times, values):
        self.fole.update({'name': fileName})
        self.fole.update({'hook': open(fileName, 'wb')})
        self.appendheaderslf()
        npoin = self.npoin2
        nbrow = values.shape[0]
        if nbrow % npoin != 0:
            raise Exception(u'The number of values is not equal to the number of nodes : %d' % npoin)
        for i in range(times.size):
            self.appendcoretimeslf(times[i])
            self.appendcorevarsslf(values[i * npoin:(i + 1) * npoin, :])
        self.fole.update({'hook': self.fole['hook'].close()})

    def addcontent(self, fileName, times, values):
        self.fole.update({'hook': open(fileName, 'ab')})
        npoin = self.npoin2
        nbrow = values.shape[0]
        if nbrow % npoin != 0:
            raise Exception(u'The number of values is not equal to the number of nodes : %d' % npoin)
        for i in range(times.size):
            self.appendcoretimeslf(times[i])
            self.appendcorevarsslf(values[i * npoin:(i + 1) * npoin, :])
        self.fole.update({'hook': self.fole['hook'].close()})

    def __del__(self):
        """
        Destructor method
        """
        if self.file['name'] != '':
            self.file.update({'hook': self.file['hook'].close()})


if __name__ == "__main__":
    namefile = 'mersey.res'
    pathfile = r'D:\Diane_work\output_hydro\telemac_py'
    [v, h, coord_p, ikle, coord_c] = load_telemac(namefile, pathfile)
    plot_vel_h(coord_p, h, v)
