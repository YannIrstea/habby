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
import h5py
import os
import numpy as np
import matplotlib.pyplot as plt
import time
import sys
from io import StringIO
from copy import deepcopy
from scipy.interpolate import griddata

from src import manage_grid_mod
from src import hdf5_mod
from src.project_manag_mod import create_default_project_preferences_dict
from src.tools_mod import create_empty_data_2d_dict, create_empty_data_2d_whole_profile_dict, check_data_2d_dict_size, check_data_2d_dict_validity


def load_hec_ras_2d_and_cut_grid(hydrau_description, progress_value, q=[], print_cmd=False, project_preferences={}):
    # name_hdf5, filename, path, name_prj, path_prj, model_type, nb_dim, path_hdf5, q=[],
    #                                  print_cmd=False, project_preferences={}
    """
    This function calls load_hec_ras_2d and the cut_2d_grid function. Hence, it loads the data,
    pass it from cell to node (as data output in hec-ras is by cells) and it cut the grid to
    get only the wetted area. This was done before in the HEC_RAS2D Class in hydro_gui_2.py, but it was necessary to
    create a separate function to called this task in a second thread to avoid freezing the GUI.

    :param name_hdf5: the base name of the created hdf5 (string)
    :param filename: the name of the file containg the results of HEC-RAS in 2D. (string)
    :param path: the path where the file is (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param q: used by the second thread to get the error back to the GUI at the end of the thread
    :param print_cmd: If True will print the error and warning to the cmd. If False, send it to the GUI.
    :param project_preferences: the figure option, used here to get the minimum water height to have a wet node (can be > 0)

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windoows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line.

    """
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_preferences_dict()
    minwh = project_preferences['min_height_hyd']

    # progress
    progress_value.value = 5

    # load
    data_2d_from_hecras2d, description_from_hecras2d = load_hec_ras2d(hydrau_description["filename_source"],
                                                                      hydrau_description["path_filename_source"])
    if not data_2d_from_hecras2d and not data_2d_from_hecras2d:
        q.put(mystdout)
        return

    # progress
    progress_value.value = 10

    # create empty dict
    data_2d_whole_profile = create_empty_data_2d_whole_profile_dict(int(description_from_hecras2d["reach_number"]))  # always one reach by file
    description_from_hecras2d["unit_correspondence"] = [[]] * int(description_from_hecras2d["reach_number"])  # multi reach by file

    # create empty dict
    data_2d = create_empty_data_2d_dict(1,  # always one reach
                                        mesh_variables=list(data_2d_from_hecras2d["mesh"]["data"].keys()),
                                        node_variables=list(data_2d_from_hecras2d["node"]["data"].keys()))

    # progress from 10 to 90 : from 0 to len(units_index)
    delta = int(80 / int(description_from_hecras2d["unit_number"]))

    # for each reach
    for reach_num in range(int(description_from_hecras2d["reach_number"])):
        data_2d_whole_profile["mesh"]["tin"].append([])
        data_2d_whole_profile["node"]["xy"].append([])
        data_2d_whole_profile["node"]["z"].append([])

        # for each units
        description_from_hecras2d["unit_list"] = [description_from_hecras2d["unit_list"].split(", ")]
        for unit_num in range(len(description_from_hecras2d["unit_list"][reach_num])):
            # get unit from according to user selection
            if hydrau_description["unit_list_tf"][reach_num][unit_num]:
                # conca xy with z value to facilitate the cutting of the grid (interpolation)
                xy = np.insert(data_2d_from_hecras2d["node"]["xy"][reach_num],
                               2,
                               values=data_2d_from_hecras2d["node"]["z"][reach_num],
                               axis=1)  # Insert values before column 2

                # remove mesh dry and cut partialy dry in option
                tin_data, xy_cuted, h_data, v_data, i_whole_profile = manage_grid_mod.cut_2d_grid(
                    data_2d_from_hecras2d["mesh"]["tin"][reach_num],
                    xy,
                    data_2d_from_hecras2d["node"]["data"]["h"][reach_num][unit_num],
                    data_2d_from_hecras2d["node"]["data"]["v"][reach_num][unit_num],
                    progress_value,
                    delta,
                    project_preferences["cut_mesh_partialy_dry"],
                    unit_num,
                    minwh
                    )

                if not isinstance(tin_data, np.ndarray):  # error or warning
                    if not tin_data:  # error
                        print("Error: " + "cut_2d_grid")
                        q.put(mystdout)
                        return
                    elif tin_data:   # warning
                        hydrau_description["unit_list_tf"][reach_num][unit_num] = False
                        # print("Warning: " + qt_tr.translate("rubar1d2d_mod", "The mesh of timestep ") + unit_name + qt_tr.translate("rubar1d2d_mod", " is entirely dry."))
                        continue  # Continue to next iteration.
                else:
                    # get original data
                    data_2d_whole_profile["mesh"]["tin"][reach_num].append(data_2d_from_hecras2d["mesh"]["tin"][reach_num])
                    data_2d_whole_profile["node"]["xy"][reach_num].append(data_2d_from_hecras2d["node"]["xy"][reach_num])
                    data_2d_whole_profile["node"]["z"][reach_num].append(data_2d_from_hecras2d["node"]["z"][reach_num])

                    # get cuted grid
                    data_2d["mesh"]["tin"][reach_num].append(tin_data)
                    data_2d["mesh"]["i_whole_profile"][reach_num].append(i_whole_profile)
                    for mesh_variable in data_2d_from_hecras2d["mesh"]["data"].keys():
                        data_2d["mesh"]["data"][mesh_variable][reach_num].append(data_2d_from_hecras2d["mesh"]["data"][mesh_variable][0][unit_num][i_whole_profile])
                    data_2d["node"]["xy"][reach_num].append(xy_cuted[:, :2])
                    data_2d["node"]["z"][reach_num].append(xy_cuted[:, 2])
                    data_2d["node"]["data"]["h"][reach_num].append(h_data)
                    data_2d["node"]["data"]["v"][reach_num].append(v_data)

    # refresh unit (if unit mesh entirely dry)
    for reach_num in reversed(range(int(description_from_hecras2d["reach_number"]))):  # for each reach
        for unit_num in reversed(range(len(description_from_hecras2d["unit_list"][reach_num]))):
            if not hydrau_description["unit_list_tf"][reach_num][unit_num]:
                description_from_hecras2d["unit_list"][reach_num].pop(unit_num)
    description_from_hecras2d["unit_number"] = str(len(description_from_hecras2d["unit_list"][0]))

    # varying mesh ?
    for reach_num in range(int(description_from_hecras2d["reach_number"])):
        temp_list = deepcopy(data_2d_whole_profile["node"]["xy"][reach_num])
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
            description_from_hecras2d["unit_correspondence"][reach_num] = whole_profil_egual_index

        if len(set(whole_profil_egual_index)) == 1:  # one tin for all unit
            data_2d_whole_profile["mesh"]["tin"][reach_num] = [data_2d_whole_profile["mesh"]["tin"][reach_num][0]]
            data_2d_whole_profile["node"]["xy"][reach_num] = [data_2d_whole_profile["node"]["xy"][reach_num][0]]

    # ALL CASE SAVE TO HDF5
    progress_value.value = 90  # progress

    # hyd description
    hyd_description = dict()
    hyd_description["hyd_filename_source"] = description_from_hecras2d["filename_source"]
    hyd_description["hyd_path_filename_source"] = description_from_hecras2d["path_filename_source"]
    hyd_description["hyd_model_type"] = description_from_hecras2d["model_type"]
    hyd_description["hyd_2D_numerical_method"] = "FiniteVolumeMethod"
    hyd_description["hyd_model_dimension"] = description_from_hecras2d["model_dimension"]
    hyd_description["hyd_mesh_variables_list"] = ", ".join(list(data_2d_from_hecras2d["mesh"]["data"].keys()))
    hyd_description["hyd_node_variables_list"] = ", ".join(list(data_2d_from_hecras2d["node"]["data"].keys()))
    hyd_description["hyd_epsg_code"] = "unknown"
    hyd_description["hyd_reach_list"] = "unknown"
    hyd_description["hyd_reach_number"] = description_from_hecras2d["reach_number"]
    hyd_description["hyd_reach_type"] = "river"
    hyd_description["hyd_unit_list"] = description_from_hecras2d["unit_list"]
    hyd_description["hyd_unit_number"] = description_from_hecras2d["unit_number"]
    hyd_description["hyd_unit_type"] = description_from_hecras2d["unit_type"]
    hyd_description["unit_correspondence"] = description_from_hecras2d["unit_correspondence"]
    hyd_description["hyd_cuted_mesh_partialy_dry"] = str(project_preferences["cut_mesh_partialy_dry"])

    hyd_description["hyd_varying_mesh"] = False
    if hyd_description["hyd_varying_mesh"]:
        hyd_description["hyd_unit_z_equal"] = False
    else:
        # TODO : check if all z values are equal between units
        hyd_description["hyd_unit_z_equal"] = True

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(project_preferences["path_prj"],
                                   hydrau_description["hdf5_name"])
    hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description, project_preferences)

    # progress
    progress_value.value = 100
    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_hec_ras2d(filename, path):
    """
    The goal of this function is to load 2D data from Hec-RAS in the version 5.

    :param filename: the name of the file containg the results of HEC-RAS in 2D. (string)
    :param path: the path where the file is (string)
    :return: velocity and height at the center of the cells, the coordinate of the point of the cells,
             the coordinates of the center of the cells and the connectivity table. Each output is a list of numpy array
             (one array by 2D flow area)

    **How to obtain the input file**

    The file neede as input is an hdf5 file (.hdf) created automatically by Hec-Ras. There are many .hdf created by
    Hec-Ras. The one to choose is the one with the extension p0X.hdf (not g0x.hdf). It is usually the largest file in
    the results folder.

    **Technical comments**

    Outputs from HEC-RAS in 2D are in the hdf5 format. However, it is not possible to directly use the output of HEC-RAS
    as an hdf5 input for HABBY. Indeed, even if they are both in hdf5, the formats of the hdf5 files are different
    (and would miss some important info for HABBY).  So we still need to load the HEC-RAS data in HABBY even if in 2D.

    This function call the function get_trianglar grid which is in rubar1d2d_mod.py.

    **Walk-through**

    The name and path of the file is given as input to the load_hec_ras_2D function. Usually this is done by the class
    HEC_RAS() in the GUI.  We load the file using the h5py module. This module opens and reads hdf5 file.

    Then we can read different part of the hdf5 file when we know the address of it (this is a bit like a file system).
    In hdf5 file of Hec-RAS, this first thing is to get the names of the flow area in “Geometry/2D Flow Area”. In
    general, this is the name of each reach, but it could be lake or pond also. In an hdf5 file, to see the name of
    the member in a group, use: list("group".keys())

    Then, we go to “Geometry/2D Flow Area/<name>/FacePoint Coordinates” to get the points forming the grid.
    We can also get the connectivity table (or ikle) to the path “Geometry/2D Flow Area/<name>/Cells Face Point Indexes”
    We also get the elevations of the cells. However, this is just the minimum elevation of the cells, so it is
    to be used only for a quick estimation. We then get the water depth by cell.
    The velocity is given by face of the cells and is averaged to get it on the middle of the cells.

    To get Hec-Ras data by nodes, it is necessary to intepolate the data. There is a function to do this in
    manage_grid_8.
    """
    filename_path = os.path.join(path, filename)

    # check extension
    blob, ext = os.path.splitext(filename)
    if ext == '.hdf' or ext == '.h5':
        pass
    else:
        print('Warning: The file does not seem to be of Hec-ras2D (hdf) type.')

    # initialization
    coord_p_all = []
    coord_c_all = []
    elev_p_all = []
    elev_c_all = []
    ikle_all = []
    vel_c_all = []
    water_depth_c_all = []
    vel_t_all = []
    water_depth_t_all = []

    # open file
    if os.path.isfile(filename_path):
        try:
            file2D = h5py.File(filename_path, 'r')
        except OSError:
            print("Error: unable to open the hdf file.")
            return [-99], [-99], [-99], [-99], [-99], [-99], [-99]
    else:
        print('Error: The hdf5 file does not exist.')
        return [-99], [-99], [-99], [-99], [-99], [-99], [-99]

    # geometry and grid data
    geometry_base = file2D["Geometry/2D Flow Areas"]
    # Old version of HEC-RAS2D ?
    try:
        name_area = geometry_base["Names"][:].astype(str).tolist()
    except KeyError:
        # New version of HEC-RAS2D ?
        try:
            name_area = geometry_base["Attributes"]["Name"].astype(str).tolist()
        except KeyError:
            print('Error: Name of flow area could not be extracted. Check format of the hdf file.')
            return [-99], [-99], [-99], [-99], [-99], [-99], [-99]
        # print(list(geometry.items()))
    try:
        for i in range(0, len(name_area)):
            name_area_i = name_area[i]
            path_h5_geo = "Geometry/2D Flow Areas" + '/' + name_area_i
            geometry = file2D[path_h5_geo]
            # print(list(geometry.keys()))
            # basic geometry
            coord_p = np.array(geometry["FacePoints Coordinate"])
            coord_c = np.array(geometry["Cells Center Coordinate"])
            ikle = np.array(geometry["Cells FacePoint Indexes"], dtype=np.int64)
            elev_c = geometry["Cells Minimum Elevation"][:]
            coord_p_all.append(coord_p)
            coord_c_all.append(coord_c)
            ikle_all.append(ikle)
            elev_c_all.append(elev_c)
    except KeyError:
        print('Error: Geometry data could not be extracted. Check format of the hdf file.')
        return [-99], [-99], [-99], [-99], [-99], [-99], [-99]

    # water depth
    for i in range(len(name_area)):
        name_area_i = name_area[i]
        path_h5_geo = '/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas' \
                      + '/' + name_area_i
        result = file2D[path_h5_geo]
        water_depth = np.array(result['Depth'])
        water_depth_c_all.append(water_depth)

    # TODO : velocity verifier que les vecteurs unitaires 'normaux' aux faces sont en fait des vecteurs normaux de vitesses
    nbtstep = 0
    for i in range(len(name_area)):
        # velocity is given on the side of the cells.
        # It is to be averaged to find the norm of speed in the middle of the cells.
        cells_face_all = np.array(geometry["Cells Face and Orientation Values"])
        cells_face = cells_face_all[:, 0]
        where_is_cells_face = np.array(geometry["Cells Face and Orientation Info"])
        where_is_cells_face1 = where_is_cells_face[:, 1]
        face_unit_vec = np.array(geometry["Faces NormalUnitVector and Length"])
        face_unit_vec = face_unit_vec[:, :2]
        velocity = result["Face Velocity"][:]
        new_vel = np.hstack((face_unit_vec, velocity.T))  # for optimization (looking for face is slow)
        # new_elev = np.hstack((face_unit_vec, elevation.reshape(elevation.shape[0], 1)))
        lim_b = 0
        nbtstep = velocity.shape[0]
        vel_c = np.zeros((len(coord_c_all[i]), nbtstep))
        for c in range(len(coord_c_all[i])):
            # find face
            nb_face = where_is_cells_face1[c]
            lim_a = lim_b
            lim_b = lim_a + nb_face
            face = cells_face[lim_a:lim_b]
            # vel
            data_face = new_vel[face, :]
            data_face_t = data_face[:, 2:].T
            add_vec_x = np.sum(data_face_t * data_face[:, 0], axis=1)
            add_vec_y = np.sum(data_face_t * data_face[:, 1], axis=1)
            vel_c[c, :] = np.sqrt(add_vec_x ** 2 + add_vec_y ** 2) / nb_face
        vel_c_all.append(vel_c)

        if np.isnan(elev_c_all[i]).any():
            print('Warning: '+str(name_area[i])+'there are cells where the center elevation is unknown  we are using Faces Minimum Elevation to calculate them')
            # elevation FacePoints
            faces_facepoint_indexes = geometry["Faces FacePoint Indexes"][:]
            face_center_point = np.mean([coord_p_all[i][faces_facepoint_indexes[:, 0]], coord_p_all[i][faces_facepoint_indexes[:, 1]]], axis=0)
            elev_f = geometry["Faces Minimum Elevation"][:]
            elev_c_all3 = griddata(face_center_point, elev_f, coord_c_all[i])
            elev_c_all[i][np.isnan(elev_c_all[i])] = elev_c_all3[np.isnan(elev_c_all[i])]
            if np.isnan(elev_c_all[i]).any():
                print('Warning: there are still cells where the center elevation is unknown')

        elev_p = griddata(coord_c_all[i], elev_c_all[i], coord_p_all[i])
        # elev_f = geometry["Faces Minimum Elevation"][:]
        # elev_p3 = griddata(face_center_point, elev_f, coord_p_all[i])
        # elev_p[np.isnan(elev_p)] = elev_p3[np.isnan(elev_p)]
        # elev_p = griddata(coord_c_all[i], elev_c_all[i], coord_p_all[i])
        # elev_f = geometry["Faces Minimum Elevation"][:]
        # faces_facepoint_indexes = geometry["Faces FacePoint Indexes"][:]
        # elev_p2 = np.zeros((len(coord_p_all[i])))
        # for point_index in range(len(coord_p_all[i])):
        #     first_bool = faces_facepoint_indexes[:, 0] == point_index
        #     second_bool = faces_facepoint_indexes[:, 1] == point_index
        #     elev_p2[point_index] = (np.sum(elev_f[first_bool]) + np.sum(elev_f[second_bool])) / \
        #                           (np.sum(first_bool) + np.sum(second_bool))
        # elev_p[np.isnan(elev_p)] = elev_p2[np.isnan(elev_p)]
        if np.isnan(elev_p).any() :
            for point_index in np.where(np.isnan(elev_p))[0]:    # for point_index in range(len(coord_p_all[i]))
                first_bool = faces_facepoint_indexes[:, 0] == point_index
                second_bool = faces_facepoint_indexes[:, 1] == point_index
                elev_p[point_index] = (np.sum(elev_f[first_bool]) + np.sum(elev_f[second_bool])) / \
                                      (np.sum(first_bool) + np.sum(second_bool))
        if np.isnan(elev_p).any():
            print('Warning: there are still points/nodes where the elevation is unknown')

        elev_p_all.append(elev_p)

    # get data time step by time step
    for t in range(0, nbtstep):
        water_depth_t = []
        vel_t = []
        for i in range(0, len(name_area)):
            water_depth_t.append(water_depth_c_all[i][t])
            vel_t.append(vel_c_all[i][:, t])
        water_depth_t_all.append(water_depth_t)
        vel_t_all.append(vel_t)

    # name of the time step
    timesteps = []
    try:
        timesteps = list(file2D["/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
                                "/Time Date Stamp"])
    except KeyError:
        pass
    for idx, t in enumerate(timesteps):
        timesteps[idx] = t.decode('utf-8')
        timesteps[idx] = timesteps[idx].replace(':', '-')

    # get a triangular grid as hec-ras output are not triangular
    coord_p_all = np.column_stack([coord_p_all[0], elev_p_all[0]])
    coord_p_all = [coord_p_all]
    coord_c_all = np.column_stack([coord_c_all[0], elev_c_all[0]])
    coord_c_all = [coord_c_all]

    ikle_all, coord_c_all, coord_p_all,  water_depth_t_all2,vel_t_all2 = get_triangular_grid_hecras(
        ikle_all, coord_c_all, coord_p_all,  water_depth_t_all,vel_t_all)

    # finite_volume_to_finite_element_triangularxy
    coord_p_all = coord_p_all[0]
    ikle = np.column_stack([ikle_all[0], np.ones(len(ikle_all[0]), dtype=ikle_all[0].dtype) * -1])  # add -1 column
    h_array = np.empty((len(water_depth_t_all2[0][0]), len(timesteps)), dtype=np.float)
    v_array = np.empty((len(vel_t_all2[0][0]), len(timesteps)), dtype=np.float)
    for reach_num in range(len(ikle_all)):
        for unit_num in range(len(timesteps)):
            h_array[:, unit_num] = np.array(water_depth_t_all2[unit_num][reach_num])
            v_array[:, unit_num] = np.array(vel_t_all2[unit_num][reach_num])
    ikle, xyz, h, v = manage_grid_mod.finite_volume_to_finite_element_triangularxy(ikle, coord_p_all,
                                                                                       h_array,
                                                                                       v_array)

    # description telemac data dict
    description_from_file = dict()
    description_from_file["filename_source"] = filename
    description_from_file["path_filename_source"] = path
    description_from_file["model_type"] = "HECRAS2D"
    description_from_file["model_dimension"] = str(2)
    description_from_file["unit_list"] = ", ".join(timesteps)
    description_from_file["unit_number"] = str(len(timesteps))
    description_from_file["unit_type"] = "timestep [s]"
    description_from_file["unit_z_equal"] = True
    description_from_file["reach_number"] = str(len(name_area))
    description_from_file["reach_name"] = ", ".join(name_area)

    # reset to list and separate xy to z
    h_list = []
    v_list = []
    for timestep_index in range(len(timesteps)):
        h_list.append(h[:, timestep_index])
        v_list.append(v[:, timestep_index])
    xy = xyz[:, (0, 1)]
    z = xyz[:, 2]

    # data 2d dict
    data_2d = create_empty_data_2d_dict(1,
                                        node_variables=["h", "v"])
    data_2d["mesh"]["tin"][0] = ikle
    data_2d["node"]["xy"][0] = xy
    data_2d["node"]["z"][0] = z
    data_2d["node"]["data"]["h"][0] = h_list
    data_2d["node"]["data"]["v"][0] = v_list

    return data_2d, description_from_file


def get_time_step(filename_path):
    # open file
    if os.path.isfile(filename_path):
        try:
            file2D = h5py.File(filename_path, 'r')
        except OSError:
            print("Error: unable to open the hdf file.")

    # name of the time step
    timesteps = []
    try:
        timesteps = list(file2D["/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
                                "/Time Date Stamp"])
    except KeyError:
        pass
    for idx, t in enumerate(timesteps):
        timesteps[idx] = t.decode('utf-8')
        timesteps[idx] = timesteps[idx].replace(':', '-')
    return len(timesteps), timesteps


def get_triangular_grid_hecras(ikle_all, coord_c_all, point_all, h, v):
    """
    In Hec-ras, it is possible to have non-triangular cells, often rectangular cells This function transform the
    "mixed" grid to a triangular grid. For this,
    it uses the centroid of each cell with more than three side and it create a triangle by side (linked with the
    center of the cell). A similar function exists in rubar1d2d_mod.py, but, as there are only one reach in rubar
    and because ikle is different in hec-ras, it was hard to merge both functions together.

    This function can only be used if the original grid is the same for all time steps. The grid created is different
    for each time steps.

    :param ikle_all: the connectivity table by reach (list of np.array)
    :param coord_c_all: the coordinate of the centroid of the cell by reach
    :param point_all: the points of the grid
    :param h: data on water height [by time step [by reach
    :param v: data on velocity [by time step [by reach
    :return: the updated ikle, coord_c (the center of the cell , must be updated ) and xyz (the grid coordinate)
    """

    nb_reach = len(ikle_all)
    nbtime = len(v)
    v_all = []
    h_all = []

    # initilization
    for t in range( nbtime):
        empty = [None] * nb_reach
        v_all.append(empty)
        h_all.append(empty)

    # create the new grid for each reach
    for r in range( nb_reach):
        coord_c = list(coord_c_all[r])
        ikle = list(ikle_all[r])
        xyz = list(point_all[r])

        nbtime = len(v)
        # now create the triangular grid
        likle = len(ikle)
        to_be_delete = []
        len_c = []
        for c in range(likle):
            ikle[c] = [item for item in ikle[c] if item >= 0]  # get rid of the minus 1 in ikle
            ikle_c = ikle[c]

            # in hec-ras, the perimeter cells are in the ikle, so we have cells with only two point
            if len(ikle_c) < 3:
                len_c.append(0)
                to_be_delete.append(c)
            if len(ikle_c) == 3:
                len_c.append(1)
            # we neglect it here
            if len(ikle_c) > 3:
                # the new cell is compose of triangle where one point is the centroid and two points are side of
                # the polygon which composed the cells before. The first new triangular cell take the place of the
                # old one (to avoid changing the order of ikle), the other are added at the end
                # no change to v and h for the first triangular data, change afterwards
                xyz.append(coord_c[c])
                # first triangular cell (erase the old one)
                ikle[c] = [ikle_c[0], ikle_c[1], len(xyz) - 1]
                p1 = xyz[- 1]
                coord_c[c] = (xyz[ikle_c[0]] + xyz[ikle_c[1]] + p1) / 3
                len_c.append(len(ikle_c) - 1)
                # next triangular cell
                for s in range(1, len(ikle_c) - 1):
                    ikle.append([ikle_c[s], ikle_c[s + 1], len(xyz) - 1])
                    coord_c.append((xyz[ikle_c[s]] + xyz[ikle_c[s + 1]] + p1) / 3)
                    # for t in range(0, nbtime):
                    #     v2[t].append(v[t][r][c])
                    #     h2[t].append(h[t][r][c])
                # last triangular cells
                ikle.append([ikle_c[-1], ikle_c[0], len(xyz) - 1])
                coord_c.append((xyz[ikle_c[-1]] + xyz[ikle_c[0]] + p1) / 3)
                # for t in range(0, nbtime):
                #     v2[t].append(v[t][r][c])
                #     h2[t].append(h[t][r][c])

        # no empty cell
        for i in sorted(to_be_delete, reverse=True):
            del ikle[i]
            del coord_c[i]

        # add grid by reach
        ikle_all[r] = np.array(ikle, dtype=np.int64)
        point_all[r] = np.array(xyz)
        coord_c_all[r] = np.array(coord_c)

        # put the data in the new cells (np.array to save memeory if a lot of time step)
        h2 = np.zeros((nbtime, len(ikle)))
        v2 = np.zeros((nbtime, len(ikle)))

        h = np.array(h)
        v = np.array(v)

        m = likle - len(to_be_delete)
        for c in range(0, likle):
            if len_c[c] > 0.5:
                h2[:, c] = h[:, r, c]
                v2[:, c] = v[:, r, c]
                if len_c[c] > 1:
                    for s in range(1, len_c[c]):
                        h2[:, m] = h[:, r, c]
                        v2[:, m] = v[:, r, c]
                        m += 1
                    h2[:, m] = h[:, r, c]
                    v2[:, m] = v[:, r, c]
                    m += 1

        # add data by time step
        for t in range(0, nbtime):
            v_all[t][r] = v2[t, :]  # list of np.array
            h_all[t][r] = h2[t, :]

    return ikle_all, coord_c_all, point_all, h_all, v_all


def figure_hec_ras2d(v_all, h_all, elev_all, coord_p_all, coord_c_all, ikle_all, path_im, time_step=[0], flow_area=[0],
                     max_point=-99):
    """
    This is a function to plot figure of the output from hec-ras 2D. This function is only used to debug, not directly by HABBY.

    :param v_all: a list of np array representing the velocity at the center of the cells
    :param h_all:  a list of np array representing the water depth at the center of the cells
    :param elev_all: a list of np array representing the mimium elevation of each cells
    :param coord_p_all: a list of np array representing the coordinates of the points of the grid
    :param coord_c_all: a list of np array representing the coordinates of the centers of the grid
    :param ikle_all: a list of np array representing the connectivity table
           one array by flow area
    :param time_step: which time_step should be plotted (default, the first one)
    :param flow_area: which flow_area should be plotted (default, the first one)
    :param max_point: the number of cell to be drawn when reconstructing the grid (it might long)
    :param path_im: the path where the figure should be saved

    **Technical comment**

    This function creates three figures which represent: a) the grid of the loaded models b) the water height and
    c) the velocity.

    The two last figures will be modified when the data will be loaded by node and not by cells. So we will not explai
    n them here as they should be re-written.

    The first figure is used to plot the gird. If we would plot the grid by drawing one side of each triangle
    separately, it would be very long to draw. To optimize the process, we use the prepare_grid function.
    """
    # figure size
    # plt.close()
    fig_size_inch = (8, 6)
    # plt.rcParams['figure.figsize'] = 7, 3
    plt.rcParams['font.size'] = 10

    # for each chosen flow_area
    for f in flow_area:
        ikle = ikle_all[f]
        coord_p = coord_p_all[f]
        coord_c = coord_c_all[f]
        elev = elev_all[f]

        # plot grid
        [xlist, ylist] = prepare_grid(ikle, coord_p)
        fig = plt.figure()
        # sc2 = plt.scatter(coord_p[:, 0], coord_p[:, 1], s=0.07, color='r')
        # sc1 = plt.scatter(point_dam_levee[:, 0], point_dam_levee[:, 1], s=0.07, color='k')
        plt.plot(xlist, ylist, c='b', linewidth=0.2)
        plt.plot(coord_c[:, 0], coord_c[:, 1], '*b')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Grid ')
        plt.savefig(os.path.join(path_im, "HEC2D_grid_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(os.path.join(path_im, "HEC2D_grid" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        # plt.close()

        # size of the marker (to avoid having to pale, unclear figure)
        # this is a rough estimation, no need for precise number here
        d1 = 0.5 * np.sqrt(
            (coord_c[1, 0] - coord_c[0, 0]) ** 2 + (coord_c[1, 1] - coord_c[0, 1]) ** 2)  # dist in coordinate
        dist_data = np.mean(
            [np.max(coord_c[:, 0]) - np.min(coord_c[:, 0]), np.max(coord_c[:, 1]) - np.min(coord_c[:, 1])])
        f_len = fig_size_inch[0] * 72  # point is 1/72 inch
        transf = f_len / dist_data
        s1 = 3.1 * (d1 * transf) ** 2 / 2  # markersize is given as an area
        s2 = s1 / 10

        # # elevation
        # fig = plt.figure()
        # cm = plt.cm.get_cmap('terrain')
        # sc = plt.scatter(coord_c[:, 0], coord_c[:, 1], c=elev, vmin=np.nanmin(elev), vmax=np.nanmax(elev), s=s1,cmap=cm, edgecolors='none')
        # cbar = plt.colorbar(sc)
        # cbar.ax.set_ylabel('Elev. [m]')
        # plt.xlabel('x coord []')
        # plt.ylabel('y coord []')
        # plt.title('Elevation above sea level')
        # plt.savefig(os.path.join(path_im, "HEC2D_elev_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        # plt.savefig(os.path.join(path_im, "HEC2D_elev_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        # #plt.close()

        # for each chosen time step
        for t in time_step:
            vel_c = v_all[t][f]
            water_depth = h_all[t][f]
            # plot water depth
            # water_deptht = np.squeeze(water_depth[t, :])
            scatter_plot(coord_c, water_depth, 'Water Depth [m]', 'terrain', 8, t)
            plt.savefig(os.path.join(path_im, "HEC2D_waterdepth_t" + str(t) + '_' + time.strftime(
                "%d_%m_%Y_at_%H_%M_%S") + '.png'))
            plt.savefig(os.path.join(path_im, "HEC2D_waterdepth_t" + str(t) + '_' + time.strftime(
                "%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
            # plt.close()

            # plot velocity
            # vel_c0 = vel_c[:, t]
            scatter_plot(coord_c, vel_c, 'Vel. [m3/sec]', 'gist_ncar', 8, t)
            plt.savefig(
                os.path.join(path_im, "HEC2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
            plt.savefig(
                os.path.join(path_im, "HEC2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
            # plt.close()

    plt.show()


def prepare_grid(ikle, coord_p, max_point=-99):
    """
    This is a function to put in the new form the data forming the grid to accelerate the plotting of the grid. This function creates
    a list of points of the grid which are re-ordered compared to the usual list of grid point (the variable coord_p
    here). These points are reordered so that it is possible to draw only one line to form the grid (one point can
    appears more than once). The grid is drawn as one long line and not as a succession of small lines, which is
    quicker. When this new list is created by prepare_function(), it is send back to figure-hec_ras_2D and plotted.

    :param ikle: the connectivity table
    :param coord_p: the coordinates of the point
    :param max_point: if the grid is very big, it is possible to only plot the first points, up to max_points (int)
    :return: a list of x and y coordinates ordered.
    """
    if max_point < 0 or max_point > len(ikle):
        max_point = len(ikle)

    # prepare grid
    xlist = []
    ylist = []
    for i in range(0, max_point):
        pi = 0
        # get rid of the minus 1 in ikle useful to plot the initial squared grid
        # ikle2 = [item for item in ikle[i] if item >= 0]
        while pi < len(ikle[i]) - 1:
            # The conditions should be tested in this order to avoid to go out of the array
            p = ikle[i][pi]  # we start at 0 in python, careful about -1 or not
            p2 = ikle[i][pi + 1]
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = ikle[i][pi]
        p2 = ikle[i][0]
        xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
        xlist.append(None)
        ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
        ylist.append(None)

    return xlist, ylist


def scatter_plot(coord, data, data_name, my_cmap, s1, t):
    """
    The function to plot the scatter of the data. Will not be used in the final version, but can be useful to
    plot data by cells.

    :param coord: the coordinates of the point
    :param data: the data to be plotted (np.array)
    :param data_name: the name of the data (string)
    :param my_cmap: the color map (string with matplotlib colormap name)
    :param s1: the size of the dot for the scatter
    :param t: the time step being plotted
    """
    s2 = s1 / 10
    fig = plt.figure()
    cm = plt.cm.get_cmap(my_cmap)
    # cm = plt.cm.get_cmap('plasma')

    data_big = data[data > 0]
    # sc = plt.hexbin(coord_c[:, 0], coord_c[:, 1], C=vel_c0, gridsize=70, cmap=cm)
    if np.sum(data_big) > 0:
        sc = plt.scatter(coord[data > 0, 0], coord[data > 0, 1], c=data_big, vmin=np.nanmin(data_big), \
                         vmax=np.nanmax(data_big), s=s1, cmap=cm, edgecolors='none')
        cbar = plt.colorbar(sc)
        cbar.ax.set_ylabel(data_name)
    else:
        plt.text(np.mean(coord[:, 0]), np.mean(coord[:, 1]), 'Data is null. No plotting possible')
    sc = plt.scatter(coord[data == 0, 0], coord[data == 0, 1], c='0.5', s=s2, cmap=cm, edgecolors='none')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    if t == -1:
        plt.title(data_name + ' at the last time step')
    else:
        plt.title(data_name + ' at time step ' + str(t))


def main():
    """
    Used to test this module independantly of HABBY.
    """
    path = r'C:\Users\diane.von-gunten\HABBY\test_data'
    filename = 'Muncie.p04.hdf'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    a = time.clock()
    [v, h, elev, coord_p, coord_c, ikle] = load_hec_ras2d(filename, path)
    b = time.clock()
    print('Time to load data:' + str(b - a) + 'sec')
    figure_hec_ras2d(v, h, elev, coord_p, coord_c, ikle, path_im, [50], [0])


if __name__ == '__main__':
    main()
