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
import h5py

from src import hdf5_mod
from src.tools_mod import create_empty_data_2d_dict, create_empty_data_2d_whole_profile_dict, frange
from src import manage_grid_mod
from src.project_properties_mod import create_default_project_properties_dict
from src import hydro_input_file_mod


def load_basement(namefilet, pathfilet):
    """
    A function which load the telemac data using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: the velocity, the height, the coordinate of the points of the grid, the connectivity table.
    """
    return_error = False, False, False
    warning_list = []

    # open file
    filename_path = os.path.join(pathfilet, namefilet)
    if os.path.isfile(filename_path):
        try:
            file2D = h5py.File(filename_path, 'r')
        except OSError:
            warning_list.append('Error: unable to open the hdf file.\n')
            return return_error
    else:
        warning_list.append('Error: The hdf5 file does not exist.\n')
        return return_error

    # simulation dict
    simulation_dict = eval(file2D[".config"]["simulation"][:].tolist()[0])["SIMULATION"]
    # variables_available = simulation_dict["OUTPUT"]  # hydraulic_variables
    timestep_float_list = list(frange(simulation_dict["TIME"]["start"],
                           simulation_dict["TIME"]["end"],
                           simulation_dict["TIME"]["out"]))  # timestep_float_list
    nbtimes = len(timestep_float_list)  # nbtimes
    #
    # # setup_dict
    # setup_dict = eval(file2D[".config"]["model"][:].tolist()[0])["SETUP"]

    # get group
    CellAll_group = file2D["CellsAll"]  # CellAll_group
    NodesAll_group = file2D["NodesAll"]  # NodesAll_group
    RESULTS_group = file2D["RESULTS"]  # CellAll_group

    # get data mesh
    mesh_nb = CellAll_group["set"][:][0]
    mesh_tin = CellAll_group["Topology"][:].astype(np.int64)
    mesh_z = CellAll_group["BottomEl"][:].flatten()
    # get data node
    node_nb = NodesAll_group["set"][:][0]
    node_xyz = NodesAll_group["Coordnts"][:]
    node_xy = node_xyz[:, (0, 1)]
    node_z = node_xyz[:, 2]
    if node_z.min() == 0 and node_z.max() == 0:
        print("Warning: All nodes elevation data are aqual to 0.")

    # result data
    mesh_h = np.zeros((mesh_nb, nbtimes), dtype=np.float64)
    mesh_v = np.zeros((mesh_nb, nbtimes), dtype=np.float64)
    dataset_name_list = list(RESULTS_group["CellsAll"]["HydState"])
    for timestep_num in range(nbtimes):
        result_hyd_array = RESULTS_group["CellsAll"]["HydState"][dataset_name_list[timestep_num]][:]
        # h
        mesh_water_level = result_hyd_array[:, 0]
        # v1
        mesh_water_velocity1 = result_hyd_array[:, 1]
        # v2
        mesh_water_velocity2 = result_hyd_array[:, 2]
        # append
        mesh_h[:, timestep_num] = mesh_water_level - mesh_z
        mesh_v[:, timestep_num] = mesh_water_velocity1 + mesh_water_velocity2

    # finite_volume_to_finite_element_triangularxy
    mesh_tin = np.column_stack([mesh_tin, np.ones(len(mesh_tin), dtype=mesh_tin[0].dtype) * -1])  # add -1 column
    mesh_tin, node_xyz, node_h, node_v = manage_grid_mod.finite_volume_to_finite_element_triangularxy(mesh_tin,
                                                                                   node_xyz,
                                                                                    mesh_h,
                                                                                    mesh_v)

    # return to list
    node_h_list = []
    node_v_list = []
    for unit_num in range(nbtimes):
        node_h_list.append(node_h[:, unit_num])
        node_v_list.append(node_v[:, unit_num])

    # description telemac data dict
    description_from_file = dict()
    description_from_file["filename_source"] = namefilet
    description_from_file["model_type"] = "BASEMENT2D"
    description_from_file["model_dimension"] = str(2)
    description_from_file["unit_list"] = ", ".join(list(map(str, timestep_float_list)))
    description_from_file["unit_number"] = str(nbtimes)
    description_from_file["unit_type"] = "time [s]"
    description_from_file["unit_z_equal"] = True  # TODO : check

    # data 2d dict (one reach by file and varying_mesh==False)
    data_2d = create_empty_data_2d_dict(reach_number=1,
                                        node_variables=["h", "v"])
    data_2d["mesh"]["tin"][0] = mesh_tin
    data_2d["node"]["xy"][0] = node_xy
    data_2d["node"]["z"][0] = node_z
    data_2d["node"]["data"]["h"][0] = node_h_list
    data_2d["node"]["data"]["v"][0] = node_v_list
    #     return v, h, coord_p, ikle, coord_c, timestep
    return data_2d, description_from_file


def get_time_step(namefilet, pathfilet):
    """
    A function which load the telemac time step using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: timestep
    """
    return_error = False, False, False
    warning_list = []

    # open file
    filename_path = os.path.join(pathfilet, namefilet)
    if os.path.isfile(filename_path):
        try:
            file2D = h5py.File(filename_path, 'r')
        except OSError:
            warning_list.append('Error: unable to open the hdf file.\n')
            return return_error
    else:
        warning_list.append('Error: The hdf5 file does not exist.\n')
        return return_error

    simulation_dict = eval(file2D[".config"]["simulation"][:].tolist()[0])

    hydraulic_variables = simulation_dict["SIMULATION"]["OUTPUT"]
    timestep_float_list = list(frange(simulation_dict["SIMULATION"]["TIME"]["start"],
                           simulation_dict["SIMULATION"]["TIME"]["end"],
                           simulation_dict["SIMULATION"]["TIME"]["out"]))
    timestep_string_list = list(map(str, timestep_float_list))
    nbtimes = len(timestep_float_list)

    return nbtimes, timestep_string_list, warning_list

