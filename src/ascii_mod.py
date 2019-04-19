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
import numpy as np

from src_GUI import preferences_GUI
from src import hdf5_mod
from src import manage_grid_mod


def load_ascii_and_cut_grid(file_path, progress_value, q=[], print_cmd=False, fig_opt={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not fig_opt:
        fig_opt = preferences_GUI.create_default_figoption()
    minwh = fig_opt['min_height_hyd']

    # progress
    progress_value.value = 10

    # load data from txt file
    data_2d_from_ascii, data_2d_whole_profile, data_description = load_ascii_model(file_path)

    data_2d = dict()
    data_2d["tin"] = [[]]  # always one reach
    data_2d["i_whole_profile"] = [[]]  # always one reach
    data_2d["xy"] = [[]]  # always one reach
    data_2d["h"] = [[]]  # always one reach
    data_2d["v"] = [[]]  # always one reach
    data_2d["z"] = [[]]  # always one reach

    # progress from 10 to 90 : from 0 to len(units_index)
    delta = int(80 / int(data_description["unit_number"]))
    
    # for each units
    for i, unit_index in enumerate(data_description["hyd_unit_list"].split(", ")):
        # conca xy with z value to facilitate the cutting of the grid (interpolation)
        xy = np.insert(data_2d["xy"],
                       2,
                       values=data_2d["z"],
                       axis=1)  # Insert values before column 2
        [tin_data, xy_data, h_data, v_data, ind_new] = manage_grid_mod.cut_2d_grid(data_2d_from_ascii["tin"],
                                                                                   xy,
                                                                                   data_2d_from_ascii["h"][unit_index],
                                                                                   data_2d_from_ascii["v"][unit_index],
                                                                                   progress_value,
                                                                                   delta,
                                                                                   minwh,
                                                                                   True)
        if not isinstance(tin_data, np.ndarray):
            print("Error: cut_2d_grid")
            q.put(mystdout)
            return
    
        data_2d["tin"][0].append(tin_data)
        data_2d["i_whole_profile"][0].append(ind_new)
        data_2d["xy"][0].append(xy_data[:, :2])
        data_2d["h"][0].append(h_data)
        data_2d["v"][0].append(v_data)
        data_2d["z"][0].append(xy_data[:, 2])

    # ALL CASE SAVE TO HDF5
    progress_value.value = 90  # progress

    # hyd description
    hyd_description = dict()
    hyd_description["hyd_filename_source"] = data_description["filename_source"]
    hyd_description["hyd_model_type"] = data_description["model_type"]
    hyd_description["hyd_model_dimension"] = data_description["model_dimension"]
    hyd_description["hyd_variables_list"] = "h, v, z"
    hyd_description["hyd_epsg_code"] = data_description["epsg_code"]
    hyd_description["hyd_reach_list"] = data_description["reach_list"]
    hyd_description["hyd_reach_number"] = data_description["reach_number"]
    hyd_description["hyd_reach_type"] = data_description["reach_type"]
    hyd_description["hyd_unit_list"] = data_description["unit_list"]
    hyd_description["hyd_unit_number"] = data_description["unit_number"]
    hyd_description["hyd_unit_type"] = data_description["unit_type"]
    hyd_description["hyd_unit_wholeprofile"] = str(data_2d_whole_profile["unit_correspondence"])
    hyd_description["hyd_unit_z_equal"] = "all"

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(data_description["path_prj"],
                                   data_description["hdf5_name"])
    hdf5.create_hdf5_hyd(data_2d,
                         data_2d_whole_profile,
                         hyd_description)

    # progress
    progress_value.value = 92

    # export_mesh_whole_profile_shp
    hdf5.export_mesh_whole_profile_shp(fig_opt)

    # progress
    progress_value.value = 96

    # export shape
    hdf5.export_mesh_shp(fig_opt)

    # progress
    progress_value.value = 98

    # export_point_shp
    hdf5.export_point_shp(fig_opt)

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_ascii_model(file_path):
    # Yann function reading txt
    data_2d = dict()
    data_2d_whole_profile = dict()
    data_description = dict()
    return data_2d, data_2d_whole_profile, data_description


def get_time_step(file_path):
    faiload = [-99], [-99]
    # file exist ?
    if not os.path.isfile(file_path):
        print('Error: The ascci text file does not exist. Cannot be loaded.')
        return faiload

    nbtimes = 0
    timestep_string = "0"

    return nbtimes, timestep_string
