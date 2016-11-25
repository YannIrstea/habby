import h5py
import os
import numpy as np


def open_hdf5(hdf5_name):
    """
    This is a function which open an hdf5 file and check that it exists
    :param hdf5_name: the path and name of the hdf5 file (string)
    :return:
    """
    blob, ext = os.path.splitext(hdf5_name)
    if ext != '.h5':
        print('Warning: the file should be of hdf5 type. \n')
    if os.path.isfile(hdf5_name):
        try:
            file = h5py.File(hdf5_name, 'r+')
        except OSError:
            print('Error: the hdf5 file could not be loaded.\n')
            return None
    else:
        print("Error: The hdf5 file is not found. \n")
        print('Error: ' + hdf5_name + '\n')
        return None

    return file


def load_hdf5_hyd(hdf5_name_hyd):
    """
    A function to load the hydrological data contains in the hdf5 file
    :param hdf5_name_hyd: path and filename of the hdf5 file (string)
    :return:
    """

    ikle_all_t = []
    point_all = []
    inter_vel_all = []
    inter_height_all = []
    failload = [[-99]], [[-99]], [[-99]], [[-99]]

    # open the file
    file_hydro = open_hdf5(hdf5_name_hyd)
    if file_hydro is None:
        print('Error: hdf5 file could not be open. \n')
        return failload

    # load the number of time steps
    basename1 = 'Data_gen'
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_timestep"]
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name_hyd
            + ' an hydrological input? \n')
        return failload
    nb_t = list(gen_dataset.values())[0]
    nb_t = np.array(nb_t)
    nb_t = int(nb_t)
    # load the number of reach
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_reach"]
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. \n')
        return failload
    nb_r = list(gen_dataset.values())[0]
    nb_r = np.array(nb_r)
    nb_r = int(nb_r)

    # load ikle
    basename1 = 'Data_2D'
    ikle_whole_all = []
    # ikle whole porfile
    for r in range(0, nb_r):
        name_ik = basename1 + "/Whole_Profile/Reach_" + str(r) + "/ikle"
        try:
            gen_dataset = file_hydro[name_ik]
        except KeyError:
            print(
                'Error: the dataset for ikle (1) is missing from the hdf5 file. \n')
            return failload
        ikle_whole = list(gen_dataset.values())[0]
        ikle_whole = np.array(ikle_whole)
        ikle_whole_all.append(ikle_whole)
    ikle_all_t.append(ikle_whole_all)
    # ikle by time step
    for t in range(0, nb_t):
        ikle_whole_all = []
        for r in range(0, nb_r):
            name_ik = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/ikle"
            try:
                gen_dataset = file_hydro[name_ik]
            except KeyError:
                print(
                    'Error: the dataset for ikle (2) is missing from the hdf5 file. \n')
                return failload
            ikle_whole = list(gen_dataset.values())[0]
            ikle_whole = np.array(ikle_whole)
            ikle_whole_all.append(ikle_whole)
        ikle_all_t.append(ikle_whole_all)

    # coordinate of the point for the  whole profile
    point_whole_all = []
    for r in range(0, nb_r):
        name_pa = basename1 + "/Whole_Profile/Reach_" + str(r) + "/point_all"
        try:
            gen_dataset = file_hydro[name_pa]
        except KeyError:
            print(
                'Error: the dataset for coordinates of the points (1) is missing from the hdf5 file. \n')
            return failload
        point_whole = list(gen_dataset.values())[0]
        point_whole = np.array(point_whole)
        point_whole_all.append(point_whole)
    point_all.append(point_whole_all)
    # coordinate of the point by time step
    for t in range(0, nb_t):
        point_whole_all = []
        for r in range(0, nb_r):
            name_pa = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/point_all"
            try:
                gen_dataset = file_hydro[name_pa]
            except KeyError:
                print(
                    'Error: the dataset for coordinates of the points (2) is missing from the hdf5 file. \n')
                return failload
            point_whole = list(gen_dataset.values())[0]
            point_whole = np.array(point_whole)
            point_whole_all.append(point_whole)
        point_all.append(point_whole_all)

    # load height and velocity data
    inter_vel_all.append([])  # no data for the whole profile case
    inter_height_all.append([])
    for t in range(0, nb_t):
        h_all = []
        vel_all = []
        for r in range(0, nb_r):
            name_vel = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/inter_vel_all"
            name_he = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/inter_h_all"
            try:
                gen_dataset = file_hydro[name_vel]
            except KeyError:
                print(
                    'Error: the dataset for velocity is missing from the hdf5 file. \n')
                return failload
            vel = list(gen_dataset.values())[0]
            vel = np.array(vel)
            vel_all.append(vel)
            try:
                gen_dataset = file_hydro[name_he]
            except KeyError:
                print(
                    'Error: the dataset for water height is missing from the hdf5 file. \n')
                return failload
            heigh = list(gen_dataset.values())[0]
            heigh = np.array(heigh)
            h_all.append(heigh)
        inter_vel_all.append(vel_all)
        inter_height_all.append(h_all)

    return ikle_all_t, point_all, inter_vel_all, inter_height_all


def load_hdf5_sub(hdf5_name_sub):
    """
    A function to load the substrate data contained in the hdf5 file
    :param hdf5_name_sub: path and file name to the hdf5 file (string)
    :return:
    """
    ikle_sub = []
    point_all_sub = []
    data_sub = []
    failload = [-99], [-99], [-99]

    # open the file
    file_sub = open_hdf5(hdf5_name_sub)
    if file_sub is None:
        print('Error: hdf5 file could not be open. \n')
        return failload

    # read the ikle data
    basename1 = 'ikle_sub'
    try:
        gen_dataset = file_sub[basename1]
    except KeyError:
        print('Error: the connectivity table for the substrate grid is missing from the hdf5 file. \n')
        return failload

    ikle_sub = list(gen_dataset.values())[0]
    ikle_sub = np.array(ikle_sub)

    # read the coordinate of the point forming the grid
    basename1 = 'coord_p_sub'
    try:
        gen_dataset = file_sub[basename1]
    except KeyError:
        print('Error: the connectivity table for the substrate grid is missing from the hdf5 file. \n')
        return failload

    point_all_sub = list(gen_dataset.values())[0]
    point_all_sub = np.array(point_all_sub)

    # read the substrate data
    # NOT DONE YET AS THE FORM OF THE SUBSTRATE INFO IS UNKNOWN

    return ikle_sub, point_all_sub, data_sub
