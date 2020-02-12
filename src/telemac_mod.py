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
from PyQt5.QtCore import QCoreApplication as qt_tr
import matplotlib.pyplot as plt
import numpy as np
from copy import deepcopy

from src import hdf5_mod
from src.tools_mod import create_empty_data_2d_dict, create_empty_data_2d_whole_profile_dict
from src import manage_grid_mod
from src.project_manag_mod import create_default_project_preferences_dict
from src import hydro_input_file_mod


def load_telemac_and_cut_grid(hydrau_description, progress_value, q=[], print_cmd=False, project_preferences={}):
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
        project_preferences = create_default_project_preferences_dict()
    minwh = project_preferences['min_height_hyd']

    # progress
    progress_value.value = 10

    # check if hydrau_description_multiple
    if type(hydrau_description) == dict:  # hydrau_description simple (one .hyd)
        file_number = 1
        hydrau_description = [hydrau_description]
    elif type(hydrau_description) == list:  # hydrau_description_multiple (several .hyd)
        file_number = len(hydrau_description)

    for hyd_file in range(0, file_number):
        filename_source = hydrau_description[hyd_file]["filename_source"].split(", ")

        # get data_2d_whole_profile
        data_2d_whole_profile = create_empty_data_2d_whole_profile_dict(1)  # always one reach by file
        hydrau_description[hyd_file]["unit_correspondence"] = [[]]  # always one reach by file
        for i, file in enumerate(filename_source):
            # _, _, xy, tin, xy_center, _ = load_telemac(file, pathfilet)
            data_2d_telemac, description_from_telemac_file = load_telemac(file, hydrau_description[hyd_file]["path_filename_source"])
            if data_2d_telemac == [-99] and description_from_telemac_file == [-99]:
                q.put(mystdout)
                return
            data_2d_whole_profile["mesh"]["tin"][0].append(data_2d_telemac["mesh"]["tin"][0])
            data_2d_whole_profile["node"]["xy"][0].append(data_2d_telemac["node"]["xy"][0])
            if description_from_telemac_file["hyd_unit_z_equal"]:
                data_2d_whole_profile["node"]["z"][0].append(data_2d_telemac["node"]["z"][0][0])
            elif not description_from_telemac_file["hyd_unit_z_equal"]:
                for unit_num in range(len(hydrau_description[hyd_file]["unit_list"])):
                    data_2d_whole_profile["node"]["z"][0].append(data_2d_telemac["node"]["z"][0][unit_num])

        # create temporary list sorted to check if the whole profiles are equal to the first one (sort xy_center)
        temp_list = deepcopy(data_2d_whole_profile["node"]["xy"][0])
        for i in range(len(temp_list)):
            temp_list[i].sort(axis=0)
        # TODO: sort function may be unadapted to check TIN equality between units
        whole_profil_egual_index = []
        it_equality = 0
        for i in range(len(temp_list)):
            if i == 0:
                whole_profil_egual_index.append(it_equality)
            if i > 0:
                if np.array_equal(temp_list[i], temp_list[it_equality]):  # equal
                    whole_profil_egual_index.append(it_equality)
                else:
                    it_equality = i
                    whole_profil_egual_index.append(it_equality)  # diff
        hydrau_description[hyd_file]["unit_correspondence"][0] = whole_profil_egual_index
        if len(filename_source) == 1:  # one file : one reach, varying_mesh==False
            hydrau_description[hyd_file]["unit_correspondence"][0] = whole_profil_egual_index * int(hydrau_description[hyd_file]["unit_number"])

        if len(set(whole_profil_egual_index)) == 1:  # one tin for all unit
            data_2d_whole_profile["mesh"]["tin"][0] = [data_2d_whole_profile["mesh"]["tin"][0][0]]
            data_2d_whole_profile["node"]["xy"][0] = [data_2d_whole_profile["node"]["xy"][0][0]]

        # progress from 10 to 90 : from 0 to len(units_index)
        delta = int(80 / int(hydrau_description[hyd_file]["unit_number"]))

        # cut the grid to have the precise wet area and put data in new form
        data_2d = create_empty_data_2d_dict(1,  # always one reach
                                            mesh_variables=list(data_2d_telemac["mesh"]["data"].keys()),
                                            node_variables=list(data_2d_telemac["node"]["data"].keys()))

        # get unit list from telemac file
        file_list = hydrau_description[hyd_file]["filename_source"].split(", ")
        if len(file_list) > 1:
            unit_number_list = []
            unit_list_from_telemac_file_list = []
            for file_indexHYDRAU in file_list:
                unit_number, unit_list_from_telemac_file = get_time_step(
                    file_indexHYDRAU,
                    hydrau_description[hyd_file]["path_filename_source"])
                unit_number_list.append(unit_number)
                unit_list_from_telemac_file_list.append(unit_list_from_telemac_file)
        if len(file_list) == 1:
            unit_number, unit_list_from_telemac_file = get_time_step(
                hydrau_description[hyd_file]["filename_source"],
                hydrau_description[hyd_file]["path_filename_source"])
        # get unit list from indexHYDRAU file
        if "timestep_list" in hydrau_description[hyd_file].keys():
            if len(hydrau_description[hyd_file]["timestep_list"]) == len(file_list):
                unit_list_from_indexHYDRAU_file = hydrau_description[hyd_file]["timestep_list"]
            else:
                unit_list_from_indexHYDRAU_file = hydrau_description[hyd_file]["unit_list"]
        else:
            unit_list_from_indexHYDRAU_file = hydrau_description[hyd_file]["unit_list"]
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

        # same mesh for all units : conca xy array with first z array
        if len(set(hydrau_description[hyd_file]["unit_correspondence"][0])) == 1:
            # conca xy with z value to facilitate the cutting of the grid (interpolation)
            xy = np.insert(data_2d_telemac["node"]["xy"][0],
                           2,
                           values=data_2d_telemac["node"]["z"][0][0],
                           axis=1)  # Insert values before column 2
        else:
            data_2d_telemac, description_from_telemac_file = load_telemac(file,
                                                                          hydrau_description[
                                                                              hyd_file]["path_filename_source"])

        for i, unit_num in enumerate(unit_index_list):
            if len(file_list) > 1:
                data_2d_telemac, description_from_telemac_file = load_telemac(file_list[i],
                                                                              hydrau_description[
                                                                                  hyd_file]["path_filename_source"])
                # conca xy with z value to facilitate the cutting of the grid (interpolation)
                xy = np.insert(data_2d_telemac["node"]["xy"][0],
                               2,
                               values=data_2d_telemac["node"]["z"][0][unit_num],
                               axis=1)  # Insert values before column 2

            tin_data, xy_cuted, h_data, v_data, i_whole_profile = manage_grid_mod.cut_2d_grid(data_2d_telemac["mesh"]["tin"][0],
                                                                                        xy,
                                                                                        data_2d_telemac["node"]["data"]["h"][0][
                                                                                            unit_num],
                                                                                        data_2d_telemac["node"]["data"]["v"][0][
                                                                                            unit_num],
                                                                                        progress_value,
                                                                                        delta,
                                                                                        project_preferences[
                                                                                            "cut_mesh_partialy_dry"],
                                                                                        unit_num,
                                                                                        minwh)

            if not isinstance(tin_data, np.ndarray):  # error or warning
                if not tin_data:  # error
                    print("Error: " + qt_tr.translate("telemac_mod", "cut_2d_grid"))

                    q.put(mystdout)
                    return
                elif tin_data:  # entierly dry
                    hydrau_description[hyd_file]["unit_list_tf"][unit_num] = False
                    # print("Warning: " + qt_tr.translate("telemac_mod", "The mesh of timestep ") + description_from_telemac_file["unit_list"][0][unit_num] + qt_tr.translate("telemac_mod", " is entirely dry."))
                    continue  # Continue to next iteration.
            else:
                # save data in dict
                data_2d["mesh"]["tin"][0].append(tin_data)
                data_2d["mesh"]["i_whole_profile"][0].append(i_whole_profile)
                for mesh_variable in data_2d_telemac["mesh"]["data"].keys():
                    data_2d["mesh"]["data"][mesh_variable][0].append(data_2d_telemac["mesh"]["data"][mesh_variable][0][unit_num][i_whole_profile])
                data_2d["node"]["xy"][0].append(xy_cuted[:, :2])
                data_2d["node"]["z"][0].append(xy_cuted[:, 2])
                data_2d["node"]["data"]["h"][0].append(h_data)
                data_2d["node"]["data"]["v"][0].append(v_data)

        # refresh unit (if warning)
        # for reach_num in reversed(range(int(hydrau_description[hyd_file]["reach_number"]))):  # for each reach
        #     for unit_num in reversed(range(len(hydrau_description[hyd_file]["unit_list"][reach_num]))):
        #         if not hydrau_description[hyd_file]["unit_list_tf"][reach_num][unit_num]:
        #             hydrau_description[hyd_file]["unit_list"][reach_num].pop(unit_num)
        #hydrau_description["unit_number"] = str(len(hydrau_description[hyd_file]["unit_list"][0]))

        # ALL CASE SAVE TO HDF5
        progress_value.value = 90  # progress

        # hyd description
        hyd_description = dict()
        hyd_description["hyd_filename_source"] = hydrau_description[hyd_file]["filename_source"]
        hyd_description["hyd_path_filename_source"] = hydrau_description[hyd_file]["path_filename_source"]
        hyd_description["hyd_model_type"] = hydrau_description[hyd_file]["model_type"]
        hyd_description["hyd_2D_numerical_method"] = "FiniteElementMethod"
        hyd_description["hyd_model_dimension"] = hydrau_description[hyd_file]["model_dimension"]
        hyd_description["hyd_mesh_variables_list"] = ", ".join(list(data_2d_telemac["mesh"]["data"].keys()))
        hyd_description["hyd_node_variables_list"] = ", ".join(list(data_2d_telemac["node"]["data"].keys()))
        hyd_description["hyd_epsg_code"] = hydrau_description[hyd_file]["epsg_code"]
        hyd_description["hyd_reach_list"] = hydrau_description[hyd_file]["reach_list"]
        hyd_description["hyd_reach_number"] = hydrau_description[hyd_file]["reach_number"]
        hyd_description["hyd_reach_type"] = hydrau_description[hyd_file]["reach_type"]
        hyd_description["hyd_unit_list"] = [hydrau_description[hyd_file]["unit_list"]]
        hyd_description["hyd_unit_number"] = str(len(hydrau_description[hyd_file]["unit_list"]))
        hyd_description["hyd_unit_type"] = hydrau_description[hyd_file]["unit_type"]
        hyd_description["unit_correspondence"] = hydrau_description[hyd_file]["unit_correspondence"]
        hyd_description["hyd_cuted_mesh_partialy_dry"] = project_preferences["cut_mesh_partialy_dry"]

        # create hdf5
        hdf5 = hdf5_mod.Hdf5Management(hydrau_description[hyd_file]["path_prj"],
                                       hydrau_description[hyd_file]["hdf5_name"])
        hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description, project_preferences)

        # prog
        progress_value.value = 95

        # create_index_hydrau_text_file
        if not hydrau_description[hyd_file]["index_hydrau"]:
            hydro_input_file_mod.create_index_hydrau_text_file(hydrau_description)

        # prog
        progress_value.value = 100

    if not print_cmd:
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
        print('Error: ' + qt_tr.translate("telemac_mod", 'The telemac file does not exist. Cannot be loaded.'))
        return faiload
    blob, ext = os.path.splitext(namefilet)
    if ext != '.res' and ext != '.slf':
        print('Warning: ' + qt_tr.translate("telemac_mod", 'The extension of the telemac file is not .res or .slf'))
    try:
        telemac_data = Selafin(filename_path_res)
    except ValueError or KeyError:
        print('Error: ' + qt_tr.translate("telemac_mod", 'The telemac file cannot be loaded.'))
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
                vt = val_all[:, id].astype(np.float64)
            if 'VITESSE U' in n or 'VELOCITY U' in n:
                vu = val_all[:, id].astype(np.float64)
                foundu = True
            if 'VITESSE V' in n or 'VELOCITY V' in n:
                vv = val_all[:, id].astype(np.float64)
                foundv = True
            if 'WATER DEPTH' in n or "HAUTEUR D'EAU" in n:
                ht = val_all[:, id].astype(np.float64)
            if 'FOND' in n or 'BOTTOM' in n:
                bt = val_all[:, id].astype(np.float64)

        if foundu and foundv:
            vt = np.sqrt(vu ** 2 + vv ** 2)

        if len(vt) == 0:
            print('Error: ' + qt_tr.translate("telemac_mod", 'The variable name of the telemec file were not recognized. (1) \n'))
            return faiload
        if len(ht) == 0:
            print('Error: ' + qt_tr.translate("telemac_mod", 'The variable name of the telemec file were not recognized. (2) \n'))
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
    ikle = telemac_data.ikle2.astype(np.int64)

    # description telemac data dict
    description_from_telemac_file = dict()
    description_from_telemac_file["hyd_filename_source"] = namefilet
    description_from_telemac_file["hyd_model_type"] = "TELEMAC"
    description_from_telemac_file["hyd_model_dimension"] = str(2)
    description_from_telemac_file["hyd_unit_list"] = ", ".join(list(map(str, timestep)))
    description_from_telemac_file["hyd_unit_number"] = str(len(list(map(str, timestep))))
    description_from_telemac_file["hyd_unit_type"] = "timestep"
    description_from_telemac_file["hyd_unit_z_equal"] = all_z_equal

    # data 2d dict (one reach by file and varying_mesh==False)
    data_2d = create_empty_data_2d_dict(reach_number=1,
                                        node_variables=["h", "v"])
    data_2d["mesh"]["tin"][0] = ikle
    data_2d["node"]["xy"][0] = coord_p
    data_2d["node"]["z"][0] = z
    data_2d["node"]["data"]["h"][0] = h
    data_2d["node"]["data"]["v"][0] = v

    del telemac_data
    #     return v, h, coord_p, ikle, coord_c, timestep
    return data_2d, description_from_telemac_file


def get_time_step(namefilet, pathfilet):
    """
    A function which load the telemac time step using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: timestep
    """
    faiload = False, False

    filename_path_res = os.path.join(pathfilet, namefilet)
    # load the data and do some test
    if not os.path.isfile(filename_path_res):
        print('Error: ' + qt_tr.translate("telemac_mod", 'The telemac file does not exist. Cannot be loaded.'))
        return faiload
    blob, ext = os.path.splitext(namefilet)
    if ext != '.res' and ext != '.slf' and ext != '.srf':
        print('Warning: ' + qt_tr.translate("telemac_mod", 'The extension of the telemac file is not .res or .slf or .srf'))
    try:
        telemac_data = Selafin(filename_path_res)
    except ValueError or KeyError:
        print('Error: ' + qt_tr.translate("telemac_mod", 'The telemac file cannot be loaded.'))
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
        print('Error: ' + qt_tr.translate("telemac_mod", 'Cannot read ') + str(nchar) + \
              qt_tr.translate("telemac_mod", ' characters from your binary file. Maybe it is the wrong file format ?'))
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
        print('Error: ' + qt_tr.translate("telemac_mod", 'Cannot read ') + str(nfloat) + ' floats from your binary file. Maybe it is the wrong file format ?')
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
