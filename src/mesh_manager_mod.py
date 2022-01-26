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
import numpy as np
import numpy.lib.recfunctions
import os.path
from time import sleep
from io import StringIO
import sys

from src.hdf5_mod import Hdf5Management
from src.data_2d_mod import Data2d


mesh_manager_available_headers = {"eliminate_hydraulic_class", "keep_cell_index",
                                  "eliminate_cell_index", "keep_hydraulic_class"}


def mesh_manager_from_file(filename):
    reach_unit_index = None
    mesh_manager_description = dict()
    warnings_list = []
    f = open(filename, "r")
    mesh_manager_description["mesh_manager_data"] = []
    hvcstr = f.readline().rstrip("\n").split()
    mesh_manager_description["header"] = hvcstr[0]
    if "cell_index" in mesh_manager_description["header"]:
        reach_unit_index = eval(hvcstr[1])
        mesh_manager_description["reach_index"] = reach_unit_index[0]
        mesh_manager_description["unit_index"] = reach_unit_index[1]

    if reach_unit_index:
        start_index = 2
    else:
        start_index = 1

    for item in hvcstr[start_index:]:
        if item == "":
            continue
        try:
            mesh_manager_description["mesh_manager_data"].append(int(item))
        except ValueError:
            warnings_list.append("Error: can't convert" + str(item) + "to integer.")
            return None, warnings_list

    # check_hs_class_validity
    valid = check_mesh_manager_data_validity(mesh_manager_description)

    if valid:
        return mesh_manager_description, warnings_list
    else:
        return None, warnings_list


def check_mesh_manager_data_validity(mesh_manager_description):
    """
    mesh_manager_data_validity
    """
    header = mesh_manager_description["header"]
    # header
    if header not in mesh_manager_available_headers:
        print("Error: mesh manager header (" + header + ") not recognized. Need : " + ", ".join(mesh_manager_available_headers))
        return False

    # TODO: data min and max..

    return True


def mesh_manager(mesh_manager_description, progress_value, q=[], print_cmd=False, project_properties={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    # progress
    progress_value.value = 10

    # load file
    hdf5_1 = Hdf5Management(project_properties["path_prj"], mesh_manager_description["hdf5_name"], new=False, edit=False)
    hdf5_1.load_hdf5(whole_profil=True)

    # index case
    eliminate = False
    if "eliminate" in mesh_manager_description["header"]:
        eliminate = True
    elif "keep" in mesh_manager_description["header"]:
        eliminate = False

    hydraulic_class = False
    if "hydraulic_class" in mesh_manager_description["header"]:
        hydraulic_class = True
        reach_index = list(range(len(hdf5_1.data_2d)))
        unit_index = list(range(len(hdf5_1.data_2d[0])))
    elif "cell_index" in mesh_manager_description["header"]:
        hydraulic_class = False
        # check if reach_index and unit_index exist in hdf5 file
        try:
            hdf5_1.data_2d[mesh_manager_description["reach_index"]]
        except IndexError:
            print("Error: specified reach_index (" + str(mesh_manager_description["reach_index"]) + ") not exist in "
                  + hdf5_1.filename)
            # warnings
            if not print_cmd:
                sys.stdout = sys.__stdout__
                if q:
                    q.put(mystdout)
                    sleep(0.1)  # to wait q.put() ..
            return
        try:
            hdf5_1.data_2d[mesh_manager_description["reach_index"]][mesh_manager_description["unit_index"]]
        except IndexError:
            print("Error: specified unit_index (" + str(mesh_manager_description["unit_index"]) +
                  ") not exist in selected reach_index (" + str(mesh_manager_description["reach_index"]) + ") in "
                  + hdf5_1.filename)
            # warnings
            if not print_cmd:
                sys.stdout = sys.__stdout__
                if q:
                    q.put(mystdout)
                    sleep(0.1)  # to wait q.put() ..
            return
        reach_index = [mesh_manager_description["reach_index"]]
        unit_index = [mesh_manager_description["unit_index"]]

    # loop
    for reach_number in reach_index:
        # progress
        delta_reach = 80 / len(reach_index)

        for unit_number in unit_index: #TODO transitoire

            # progress
            delta_unit = delta_reach / len(unit_index)

            # get cell_index
            if hydraulic_class:
                cell_array_bool = np.in1d(hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5_1.data_2d.hvum.hydraulic_class.name], mesh_manager_description["mesh_manager_data"])
                cell_index = np.argwhere(cell_array_bool).flatten().tolist()
            else:
                cell_index = mesh_manager_description["mesh_manager_data"]

            same_len = len(hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"]) == len(cell_index)

            # change data
            if eliminate:  # eliminate
                if same_len:
                    print("Warning: All cell of unit " + hdf5_1.data_2d[reach_number][unit_number].unit_name + " are removed.")

                hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"] = np.delete(hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"], cell_index, 0)
                hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"] = np.delete(hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"], cell_index, 0)
                hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"] = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"].drop(cell_index)
            else:  # keep
                if same_len:
                    print("Warning: All selected cell of unit " + hdf5_1.data_2d[reach_number][unit_number].unit_name + " are keep. Nothing happen.")
                hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"] = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["tin"][cell_index]
                hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"] = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"][cell_index]
                hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"] = hdf5_1.data_2d[reach_number][unit_number]["mesh"]["data"].iloc[cell_index]

            # remove_unused_node
            hdf5_1.data_2d[reach_number][unit_number].remove_unused_node()

            # progress
            progress_value.value = progress_value.value + delta_unit

    new_filename = hdf5_1.filename[:-4] + "_MM" + hdf5_1.extension

    # get_dimension
    hdf5_1.data_2d.get_dimension()
    # export new hdf5
    hdf5 = Hdf5Management(project_properties["path_prj"],
                          new_filename, new=True)
    if hdf5_1.extension == ".hyd":
        hdf5.create_hdf5_hyd(hdf5_1.data_2d,
                             hdf5_1.data_2d_whole,
                             project_properties)
    else:

        hdf5.create_hdf5_hab(hdf5_1.data_2d,
                             hdf5_1.data_2d_whole,
                             project_properties)
    # load original hydrosignature
    hdf5_original = Hdf5Management(project_properties["path_prj"],
                                hdf5_1.data_2d.filename, new=False, edit=False)
    hdf5_original.load_hydrosignature()
    # TODO: change new file hydrosignature
    # set to new file
    hdf5 = Hdf5Management(project_properties["path_prj"],
                          hdf5.filename, new=False, edit=True)
    hdf5.get_hdf5_attributes(close_file=False)
    hdf5.load_units_index()
    hdf5.load_data_2d()
    hdf5.load_whole_profile()
    hdf5.data_2d = hdf5_original.data_2d
    hdf5.write_hydrosignature(hs_export_mesh=hdf5_original.hs_mesh)
    hdf5.close_file()


    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0
