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
    mesh_manager_description["reach_index"] = []
    mesh_manager_description["unit_index"] = []
    hvcstr = f.readlines()
    strheader=''
    imesh_manager_description=-1
    for iline,line in enumerate(hvcstr):
        line = line.replace("#","").rstrip("\n").split()
        if len(line) !=0:
            if isinstance(line[0],str) and not line[0].isnumeric() :
                mesh_manager_description["header"] = line[0].lower()
                if strheader=='':
                    strheader=mesh_manager_description["header"]
                else:
                    if strheader!=mesh_manager_description["header"]:
                        return None, 'the mesh_manager_description header is not constant keep on '+strheader
                if "cell_index" in mesh_manager_description["header"]:
                    reach_unit_index = eval(line[1])
                    mesh_manager_description["reach_index"].append(reach_unit_index[0])
                    mesh_manager_description["unit_index"].append(reach_unit_index[1])

                if reach_unit_index: #eliminate or keep cell_index
                    start_index = 2
                else: #eliminate or keep hydraulic_class
                    start_index = 1
            else:
                if strheader == '':
                    return None, 'a mesh_manager_description header is compulsory at the beginning of the file'
                start_index=0
            line_mesh_manager_data = []
            for item in line[start_index:]:
                if item == "":
                    continue
                try:
                    line_mesh_manager_data.append(int(item))

                except ValueError:
                    warnings_list.append("Error: can't convert " + str(item) + " to integer.")
                    return None, warnings_list
            if start_index==0:
                mesh_manager_description["mesh_manager_data"][imesh_manager_description].extend(line_mesh_manager_data)
            else:
                imesh_manager_description +=1
                mesh_manager_description["mesh_manager_data"].append(line_mesh_manager_data)


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
    hdf5_original = Hdf5Management(project_properties["path_prj"], mesh_manager_description["hdf5_name"], new=False, edit=False)
    hdf5_original.load_hdf5(user_target_list="all", whole_profil=True)

    # index case
    eliminate = False
    if "eliminate" in mesh_manager_description["header"]:
        eliminate = True
    elif "keep" in mesh_manager_description["header"]:
        eliminate = False

    # init
    reach_index = []
    unit_index = []

    hydraulic_class = False
    if "hydraulic_class" in mesh_manager_description["header"]:
        hydraulic_class = True
        for reach_number in range(len(hdf5_original.data_2d)):
            for unit_number in range(len(hdf5_original.data_2d[reach_number])):
                reach_index.append(reach_number)
                unit_index.append(unit_number)
        # check if hs_mesh (hydrosginature mesh)
        if not hdf5_original.hs_mesh:
            print("Error: " + mesh_manager_description["header"] + " is not possible on " + hdf5_original.filename + ". The latter is not a 2d mesh from hydrosignature.")
            # warnings
            if not print_cmd:
                sys.stdout = sys.__stdout__
                if q:
                    q.put(mystdout)
                    sleep(0.1)  # to wait q.put() ..
            return

    elif "cell_index" in mesh_manager_description["header"]:
        hydraulic_class = False
        # check if reach_index and unit_index for each row of mesh_manager file exist in hdf5 file
        for mm_row_index in range(len(mesh_manager_description["reach_index"])):
            try:
                hdf5_original.data_2d[mesh_manager_description["reach_index"][mm_row_index]]
            except TypeError or IndexError:
                print("Error: specified reach_index (" + str(mesh_manager_description["reach_index"][mm_row_index]) + ") not exist in "
                      + hdf5_original.filename)
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return
            try:
                hdf5_original.data_2d[mesh_manager_description["reach_index"][mm_row_index]][mesh_manager_description["unit_index"][mm_row_index]]
            except IndexError:
                print("Error: specified unit_index (" + str(mesh_manager_description["unit_index"][mm_row_index]) +
                      ") not exist in selected reach_index (" + str(mesh_manager_description["reach_index"][mm_row_index]) + ") in "
                      + hdf5_original.filename)
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return
        reach_index = mesh_manager_description["reach_index"]
        unit_index = mesh_manager_description["unit_index"]

    # progress
    delta_row = 80 / len(reach_index)

    animal_variable_list = hdf5_original.data_2d.hvum.hdf5_and_computable_list.habs()

    for mm_row_index in range(len(reach_index)):
        reach_number = reach_index[mm_row_index]
        unit_number = unit_index[mm_row_index]
        # get cell_index
        if hydraulic_class:
            cell_array_bool = np.in1d(hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5_original.data_2d.hvum.hydraulic_class.name], mesh_manager_description["mesh_manager_data"])
            cell_index = np.argwhere(cell_array_bool).flatten().tolist()
        else:
            cell_index = mesh_manager_description["mesh_manager_data"][mm_row_index]

        # TODO: improve check
        tin_flattened = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["tin"]
        for cell_index_el in cell_index:
            if cell_index_el not in tin_flattened:
                print("Error: specified cell index " + str(cell_index_el) +
                      " not exist in mesh of unit " + str(unit_number) + " of reach " + str(reach_number) + " of " +hdf5_original.filename)
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return

        # change data
        if eliminate:  # eliminate
            hdf5_original.data_2d[reach_number][unit_number]["mesh"]["tin"] = np.delete(hdf5_original.data_2d[reach_number][unit_number]["mesh"]["tin"], cell_index, 0)
            hdf5_original.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"] = np.delete(hdf5_original.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"], cell_index, 0)
            hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"] = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"].drop(cell_index)
        else:  # keep
            hdf5_original.data_2d[reach_number][unit_number]["mesh"]["tin"] = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["tin"][cell_index]
            hdf5_original.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"] = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"][cell_index]
            hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"] = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"].iloc[cell_index]

        # remove_unused_node
        hdf5_original.data_2d[reach_number][unit_number].remove_unused_node()

        # refresh hsi summary
        if animal_variable_list:
            for animal_index, animal_variable in enumerate(animal_variable_list):
                area = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5_original.data_2d.hvum.area.name]
                hsi = hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"][animal_variable.name]
                hdf5_original.data_2d[reach_number][unit_number].total_wet_area = np.sum(area)
                # compute summary
                wua = np.nansum(hsi * area)
                if any(np.isnan(hsi)):
                    area = np.sum(hdf5_original.data_2d[reach_number][unit_number]["mesh"]["data"][hdf5_original.data_2d.hvum.area.name][~np.isnan(hsi)])
                    # osi = wua / area
                    percent_area_unknown = (1 - (area / hdf5_original.data_2d[reach_number][unit_number].total_wet_area)) * 100  # next to 1 in top quality, next to 0 is bad or EVIL !
                else:
                    percent_area_unknown = 0.0
                osi = wua / hdf5_original.data_2d[reach_number][unit_number].total_wet_area
                # save data
                animal_variable_list[animal_index].wua[reach_number][unit_number] = wua
                animal_variable_list[animal_index].osi[reach_number][unit_number] = osi
                animal_variable_list[animal_index].percent_area_unknown[reach_number][unit_number] = percent_area_unknown

        # progress
        progress_value.value = progress_value.value + delta_row

    # prog
    progress_value.value = 90.0

    hdf5_original.data_2d.hvum.hdf5_and_computable_list = hdf5_original.data_2d.hvum.hdf5_and_computable_list.no_habs()
    hdf5_original.data_2d.hvum.hdf5_and_computable_list.extend(animal_variable_list)

    # new_filename
    new_filename = hdf5_original.filename[:-4] + "_MM" + hdf5_original.extension

    # mm
    for key, value in mesh_manager_description.items():
        if key not in ("hdf5_name", "hdf5_name_list"):
            setattr(hdf5_original.data_2d, "mm_" + key, value)

    # get_dimension
    hdf5_original.data_2d.get_dimension()

    # export hdf5_new
    hdf5_new = Hdf5Management(project_properties["path_prj"],
                          new_filename, new=True)
    if hdf5_original.extension == ".hyd":
        hdf5_new.create_hdf5_hyd(hdf5_original.data_2d,
                             hdf5_original.data_2d_whole,
                             project_properties)
    else:
        hdf5_new.create_hdf5_hab(hdf5_original.data_2d,
                             hdf5_original.data_2d_whole,
                             project_properties)  # remove_fish_hab

    # write hydrosignature to new file
    if hdf5_new.hs_calculated:
        hdf5_original = Hdf5Management(project_properties["path_prj"],
                                    hdf5_original.data_2d.filename, new=False, edit=False)
        hdf5_original.load_hydrosignature()
        # TODO: change new file hydrosignature
        # set to new file
        hdf5_new = Hdf5Management(project_properties["path_prj"],
                              hdf5_new.filename, new=False, edit=True)
        hdf5_new.get_hdf5_attributes(close_file=False)
        hdf5_new.load_units_index()
        hdf5_new.load_data_2d()
        hdf5_new.load_whole_profile()
        hdf5_new.data_2d = hdf5_original.data_2d
        hdf5_new.write_hydrosignature(hs_export_mesh=hdf5_original.hs_mesh)
        hdf5_new.close_file()

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0
