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
from src.project_properties_mod import create_default_project_properties_dict
from src import hydro_input_file_mod


def load_basement(namefilet, pathfilet):
    """
    A function which load the telemac data using the Selafin class.

    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :return: the velocity, the height, the coordinate of the points of the grid, the connectivity table.
    """
    #TODO

    # description telemac data dict
    description_from_telemac_file = dict()
    description_from_telemac_file["filename_source"] = namefilet
    description_from_telemac_file["model_type"] = "TELEMAC"
    description_from_telemac_file["model_dimension"] = str(2)
    description_from_telemac_file["unit_list"] = ", ".join(list(map(str, timestep)))
    description_from_telemac_file["unit_number"] = str(len(list(map(str, timestep))))
    description_from_telemac_file["unit_type"] = "time [s]"
    description_from_telemac_file["unit_z_equal"] = all_z_equal

    # data 2d dict (one reach by file and varying_mesh==False)
    data_2d = create_empty_data_2d_dict(reach_number=1,
                                        node_variables=["h", "v"])
    data_2d["mesh"]["tin"][0] = ikle
    data_2d["node"]["xy"][0] = coord_p
    if all_z_equal:
        data_2d["node"]["z"][0] = z[0]
    else:
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
    # TODO
    return nbtimes, timestep_string

