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
import time
import shutil
import shapefile
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src_GUI import output_fig_GUI


def open_hdf5(hdf5_name):
    """
    This is a function which opens an hdf5 file and check that it exists. It does not load the data. It only opens the
    files.
    :param hdf5_name: the path and name of the hdf5 file (string)
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


def open_hdf5_(hdf5_name, path_hdf5):
    """
    A function to load  hdf5 file.  If hdf5_name is an absolute path, the path_hdf5 is not used. If it is a relative path,
    the path is composed of the path to the 'hdf5' folder (path_hdf5/hdf5_name) composed with hdf5_name.
    return file object open, false or '', true if error occured

    :param hdf5_name: path and file name to the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    """
    # open the file
    if os.path.isabs(hdf5_name):
        file_ = open_hdf5(hdf5_name)
    else:
        if path_hdf5:
            file_ = open_hdf5(os.path.join(path_hdf5, hdf5_name))
        else:
            print('Error" No path to the project given although a relative path was provided')
            return "",True
    if file_ is None:
        print('Error: hdf5 file could not be open. \n')
        return "",True
    return file_,False


def load_hdf5_hyd(hdf5_name_hyd, path_hdf5='', merge=False):
    """
    A function to load the 2D hydrological data contained in the hdf5 file in the form required by HABBY. If
    hdf5_name_hyd is an absolute path, the path_hdf5 is not used. If hdf5_name_hyd is a relative path, the path is
    composed of the path to the project (path_hdf5) composed with hdf5_name_hyd.

    :param hdf5_name_hyd: filename of the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :param merge: If merge is True. this is a merge file with substrate data added
    :return: the connectivity table, the coordinates of the point, the height data, the velocity data
             on the coordinates, also substrate if merge is True.

    """

    # correct all change to the hdf5 form in the documentation!
    ikle_all_t = []
    point_all = []
    inter_vel_all = []
    inter_height_all = []
    substrate_all_pg = []
    substrate_all_dom = []
    failload = [[-99]], [[-99]], [[-99]], [[-99]]
    if merge:
        failload = [[-99]], [[-99]], [[-99]], [[-99]],[[-99]],[[-99]]

    file_hydro, bfailload=open_hdf5_(hdf5_name_hyd, path_hdf5)
    if bfailload:
        return failload

    # load the number of time steps #? attribut
    basename1 = 'Data_gen'
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_timestep"]
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name_hyd
            + ' an hydrological input? \n')
        file_hydro.close()
        return failload
    try:
        nb_t = list(gen_dataset.values())[0]
    except IndexError:
        print('Error: Time step are not found')
        file_hydro.close()
        return failload
    nb_t = np.array(nb_t)
    nb_t = int(nb_t)

    # load the number of reach #? attribut
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_reach"]
    except KeyError:
        print(
            'Error: the number of reaches is missing from the hdf5 file. \n')
        file_hydro.close()
        return failload
    nb_r = list(gen_dataset.values())[0]
    nb_r = np.array(nb_r)
    nb_r = int(nb_r)

    # load ikle
    basename1 = 'Data_2D'
    ikle_whole_all = []

    # ikle whole profile #? pourquoi pas du numpy direct ? indexError ??
    for r in range(0, nb_r):
        name_ik = basename1 + "/Whole_Profile/Reach_" + str(r) + "/ikle"
        try:
            gen_dataset = file_hydro[name_ik]
        except KeyError:
            print(
                'Error: the dataset for ikle (1) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        try:
            ikle_whole = list(gen_dataset.values())[0]
        except IndexError:
            print('Error: the dataset for ikle (3) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        ikle_whole = np.array(ikle_whole)
        ikle_whole_all.append(ikle_whole)
    ikle_all_t.append(ikle_whole_all)

    # ikle by time step  #? pourquoi pas du numpy direct ? indexError ??
    for t in range(0, nb_t):
        ikle_whole_all = []
        for r in range(0, nb_r):
            name_ik = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/ikle"
            try:
                gen_dataset = file_hydro[name_ik]
            except KeyError:
                print('Warning: the dataset for ikle (2) is missing from the hdf5 file for one time step. \n')
                file_hydro.close()
                return failload
            try:
                ikle_whole = list(gen_dataset.values())[0]
            except IndexError:
                print('Error: the dataset for ikle (4) is missing from the hdf5 file for one time step. \n')
                file_hydro.close()
                return failload
            ikle_whole = np.array(ikle_whole)
            ikle_whole_all.append(ikle_whole)
        ikle_all_t.append(ikle_whole_all)

    # coordinate of the point for the  whole profile #? pourquoi pas du numpy direct ? indexError ??
    point_whole_all = []
    for r in range(0, nb_r):
        name_pa = basename1 + "/Whole_Profile/Reach_" + str(r) + "/point_all"
        try:
            gen_dataset = file_hydro[name_pa]
        except KeyError:
            print(
                'Error: the dataset for coordinates of the points (1) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        try:
            point_whole = list(gen_dataset.values())[0]
        except IndexError:
            print('Error: the dataset for coordinates of the points (3) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        point_whole = np.array(point_whole)
        point_whole_all.append(point_whole)
    point_all.append(point_whole_all)
    # coordinate of the point by time step #? pourquoi pas du numpy direct ? indexError ??
    for t in range(0, nb_t):
        point_whole_all = []
        for r in range(0, nb_r):
            name_pa = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/point_all"
            try:
                gen_dataset = file_hydro[name_pa]
            except KeyError:
                print('Error: the dataset for coordinates of the points (2) is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            try:
                point_whole = list(gen_dataset.values())[0]
            except IndexError:
                print('Error: the dataset for coordinates of the points (4) is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            point_whole = np.array(point_whole)
            point_whole_all.append(point_whole)
        point_all.append(point_whole_all)

    # load height and velocity data
    inter_vel_all.append([])  # no data for the whole profile case
    inter_height_all.append([])
    if merge:
        substrate_all_pg.append([])
        substrate_all_dom.append([])
    for t in range(0, nb_t):
        h_all = []
        vel_all = []
        if merge:
            sub_pg_all = []
            sub_dom_all = []
        for r in range(0, nb_r):
            name_vel = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/inter_vel_all"
            name_he = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/inter_h_all"
            if merge:
                name_pg = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/data_substrate_pg"
                name_dom = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/data_substrate_dom"
            #velocity
            try:
                gen_dataset = file_hydro[name_vel]
            except KeyError:
                print('Error: the dataset for velocity is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            if len(list(gen_dataset.values())) ==0:
                print('Error: No velocity found in the hdf5 file. \n')
                file_hydro.close()
                return failload
            vel = list(gen_dataset.values())[0]
            vel = np.array(vel).flatten()
            vel_all.append(vel)
            #height
            try:
                gen_dataset = file_hydro[name_he]
            except KeyError:
                print('Error: the dataset for water height is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            if len(list(gen_dataset.values())) == 0:
                print('Error: No height found in the hdf5 file. \n')
                file_hydro.close()
                return failload
            heigh = list(gen_dataset.values())[0]
            heigh = np.array(heigh).flatten()
            h_all.append(heigh)
            #substrate
            if merge:
                try:
                    gen_datasetpg = file_hydro[name_pg]
                    gen_datasetdom = file_hydro[name_dom]
                except KeyError:
                    print('Error: the dataset for substrate is missing from the hdf5 file. \n')
                    file_hydro.close()
                    return failload
                try:
                    subpg = list(gen_datasetpg.values())[0]
                except IndexError:
                    print('Error: the dataset for substrate is missing from the hdf5 file (2). \n')
                    file_hydro.close()
                    return failload
                subpg = np.array(subpg).flatten()
                try:
                    subdom = list(gen_datasetdom.values())[0]
                except IndexError:
                    print('Error: the dataset for substrate is missing from the hdf5 file (3). \n')
                    file_hydro.close()
                    return failload
                subdom = np.array(subdom).flatten()
                sub_pg_all.append(subpg)
                sub_dom_all.append(subdom)
        inter_vel_all.append(vel_all)
        inter_height_all.append(h_all)
        if merge:
            substrate_all_dom.append(sub_dom_all)
            substrate_all_pg.append(sub_pg_all)
    file_hydro.close()
    if not merge:
        return ikle_all_t, point_all, inter_vel_all, inter_height_all
    else:
        return ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom


def load_timestep_name(hdf5_name, path_hdf5=''):
    """
    This function looks for the name of the timesteps in hydrological or merge hdf5. If it find the name
    of the time steps, it returns them. If not, it return an empty list.

    :param hdf5_name: the name of the merge or hydrological hdf5 file
    :param path_hdf5: the path to the hdf5
    :return: the name of the time step if they exist. Otherwise, an empty list
    """
    failload = []

    file_hydro,bfailload=open_hdf5_(hdf5_name, path_hdf5)
    if bfailload:
        return failload

    # get the name of the time steps
    basename1 = 'Data_2D'
    try:
        gen_dataset = file_hydro[basename1 + "/timestep_name"]
    except KeyError:   # in this case it happens often, it is not really an error
        file_hydro.close()
        return []
    sim_name1 = list(gen_dataset.values())[0]

    # bytes to string
    sim_name = []
    for i in range(0, len(sim_name1)):
        sim_name.append(bytes(sim_name1[i]).decode('utf-8'))
        sim_name[i] = sim_name[i].replace('\x00', '')  # why empty byte?
    file_hydro.close()
    return sim_name


def get_timestep_number(hdf5_name, path_hdf5): #? a changer si on utilise attributs
    """
       This function looks for the number of the timesteps/discharge in hydrological or merge hdf5.

       :param hdf5_name: the name of the merge or hydrological hdf5 file
       :param path_hdf5: the path to the hdf5
       :return: an int, the number of time step/discharge
       """

    failload = -99

    file_hydro,bfailload=open_hdf5_(hdf5_name, path_hdf5)
    if bfailload:
        return failload

    # get timestep number
    basename1 = 'Data_gen'
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_timestep"]
    except KeyError:
        print('The number of time step was not found (1)')
        file_hydro.close()
        return failload
    nb_timestep = list(gen_dataset.values())[0]
    try:
        timestep = np.array(nb_timestep)
        timestep = int(timestep)
    except ValueError:
        print('The number of time step was not found (2)')
        file_hydro.close()
        return failload
    file_hydro.close()
    return timestep


def load_sub_percent(hdf5_name_hyd, path_hdf5=''):
    """
    This function loads the substrate in percent form, if this info is present in the hdf5 file. It send a warning
    otherwise.

    :param hdf5_name_hyd: filename of the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :return:
    """
    failload = [-99]
    sub_per_all_t = []

    file_hydro,bfailload=open_hdf5(hdf5_name_hyd, path_hdf5)
    if bfailload:
        return failload

    # load the number of time steps
    basename1 = 'Data_gen'
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_timestep"]
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name_hyd
              + ' an hydrological input? \n')
        file_hydro.close()
        return failload
    try:
        nb_t = list(gen_dataset.values())[0]
    except IndexError:
        print('Error: Time step are not found')
        file_hydro.close()
        return failload
    nb_t = np.array(nb_t)
    nb_t = int(nb_t)

    # load the number of reach
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_reach"]
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. \n')
        file_hydro.close()
        return failload
    nb_r = list(gen_dataset.values())[0]
    nb_r = np.array(nb_r)
    nb_r = int(nb_r)

    # load the data of substrate in percentage
    basename1 = 'Data_2D'
    sub_per_all_t.append([])
    for t in range(0, nb_t):
        sub_per_all = []
        for r in range(0, nb_r):
            name_per = basename1 + "/Timestep_" + str(t) + "/Reach_" + str(r) + "/data_substrate_percentage"
            try:
                gen_datasetpg = file_hydro[name_per]
            except KeyError:
                print('Error: the dataset for substrate in percentage form is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            try:
                sub_per = list(gen_datasetpg.values())[0]
            except IndexError:
                print('Error: the dataset for substrate in precentage is missing from the hdf5 file (2). \n')
                file_hydro.close()
                return failload
            sub_per = np.array(sub_per).flatten()
            sub_per = np.reshape(sub_per, (int(len(sub_per)/8), 8))
            sub_per_all.append(sub_per)
        sub_per_all_t.append(sub_per_all)
    file_hydro.close()
    return sub_per_all_t


def load_hdf5_sub(hdf5_name_sub, path_hdf5, ind_const=False):
    """
    A function to load the substrate data contained in the hdf5 file. It also manage
    the constant cases. If hdf5_name_sub is an absolute path, the path_prj is not used. If it is a relative path,
    the path is composed of the path to the 'hdf5' folder (path_prj/hdf5_files) composed with hdf5_name_sub. it manages constant and
    vairable (based on a grid) cases. The code should be of cemagref type and the data is given as coarser and dominant.
    :param hdf5_name_sub: path and file name to the hdf5 file (string)
    :param path_prj: the path to the hdf5 file
    :param ind_const: If True this function return a boolean which indicates if the substrant is constant or not
    """

    # correct all change to the hdf5 form in the doc!
    ikle_sub = []
    point_all_sub = []
    if not ind_const:
        failload = [[-99]], [[-99]], [[-99]],[[-99]]
    else:
        failload = [[-99]], [[-99]], [[-99]], [[-99]], False
    constcase =False

    file_sub,bfailload=open_hdf5_(hdf5_name_sub, path_hdf5)
    if bfailload:
        return failload

    # manage the constant case
    constname = 'constant_sub_pg'
    if constname in file_sub:
        constcase= True
        try:
            sub_pg = file_sub[constname]
            sub_dom = file_sub['constant_sub_dom']
        except KeyError:
            print('Error:Constant substrate data is not found. \n')
            file_sub.close()
            return failload
        sub_pg = list(sub_pg.values())[0][0]
        sub_dom = list(sub_dom.values())[0][0]

    # the variable case
    else:
        # read the ikle data
        basename1 = 'ikle_sub'
        try:
            gen_dataset = file_sub[basename1]
        except KeyError:
            print('Error: the connectivity table for the substrate grid is missing from the hdf5 file. \n')
            file_sub.close()
            return failload
        # longer because we might have non-triangular value
        ikle_sub_no_order = list(gen_dataset.values())  # write the length in the hdf5?
        ikle_sub_no_order = np.squeeze(np.array(ikle_sub_no_order))
        ikle_sub = []
        for id in range(0, len(ikle_sub_no_order)):
            ns = 'p' + str(id)
            cell = gen_dataset[ns]
            ikle_sub.append(list(cell))

        # read the coordinate of the point forming the grid
        basename1 = 'coord_p_sub'
        try:
            gen_dataset = file_sub[basename1]
        except KeyError:
            print('Error: the connectivity table for the substrate grid is missing from the hdf5 file. \n')
            file_sub.close()
            return failload
        point_all_sub = list(gen_dataset.values())[0]
        point_all_sub = np.array(point_all_sub)

        # read the substrate data
        try:
            sub_pg = file_sub['data_sub_pg']
            sub_dom = file_sub['data_sub_dom']
        except KeyError:
            print('Error: No substrate data found. \n')
            return failload
        sub_pg = list(sub_pg.values())
        sub_pg = np.squeeze(np.array(sub_pg))
        sub_dom = list(sub_dom.values())
        sub_dom = np.squeeze(np.array(sub_dom))

    file_sub.close()
    if not ind_const:
        return ikle_sub, point_all_sub, sub_pg, sub_dom
    else:
        return ikle_sub, point_all_sub, sub_pg, sub_dom, constcase


def get_all_filename(dirname, ext):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    filenames = []
    for file in os.listdir(dirname):
        if file.endswith(ext):
            filenames.append(file)
    return filenames


def get_hdf5_name(model_name, name_prj, path_prj):
    """
    This function get the name of the hdf5 file containg the hydrological data for an hydrological model of type
    model_name. If there is more than one hdf5 file, it choose the last one. The path is the path from the
    project folder. Hence, it is not the absolute path.

    :param model_name: the name of the hydrological model as written in the attribute of the xml project file
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :return: the name of the hdf5 file
    """
    if model_name == 'MERGE':
        model_name2 = 'SUBSTRATE'  # merge data is in the subtrate tag in the xml files
    else:
        model_name2 = model_name

    # open the xml project file
    filename_path_pro = os.path.join(path_prj, name_prj + '.xml')
    if os.path.isfile(filename_path_pro):
        doc = ET.parse(filename_path_pro)
        root = doc.getroot()

        # get the path to hdf5
        pathhdf5 = root.find(".//Path_Hdf5")
        if pathhdf5 is None:
            print('Error: the path to the hdf5 file is not found (1) \n')
            return
        if pathhdf5.text is None:
            print('Error: the path to the hdf5 file is not found (2) \n')
            return
        pathhdf5 = os.path.join(path_prj, pathhdf5.text)
        if not os.path.isdir(pathhdf5):
            print('Error: the path to the hdf5 file is not correct \n')
            return

        # get the hdf5 name
        child = root.find(".//" + model_name2)
        if child is not None:
            if model_name == 'MERGE' or model_name == 'LAMMI':
                child = root.findall(".//" + model_name2 + '/hdf5_mergedata')
            elif model_name == 'SUBSTRATE':
                child = root.findall(".//" + model_name2 + '/hdf5_substrate')
            else:
                child = root.findall(".//" + model_name + '/hdf5_hydrodata')
            if len(child) > 0:
                # get the newest files
                files = []
                for c in child:
                    if c.text is not None and os.path.isfile(os.path.join(pathhdf5, c.text)):
                        files.append(os.path.join(pathhdf5, c.text))
                if len(files) == 0:
                    return
                name_hdf5 = max(files, key=os.path.getmtime)
                if len(name_hdf5) > 3:
                    if name_hdf5[:-3] == '.h5':
                        name_hdf5 = name_hdf5[:-3]
                return name_hdf5
            else:
                print('Warning: the hdf5 name for the model ' + model_name + ' was not found (1)')
                return 'default_name'
        else:
            # print('Warning: the data for the model ' + model_name + ' was not found (2)')
            return ''
    else:
        print('Error: no project found by load_hdf5')
        return ''


def get_initial_files(path_hdf5, hdf5_name):
    """
    This function looks into a merge file to find the hydraulic and subtrate file which
    were used to create this file.
    :param path_hdf5: the path to the hdf5 file
    :param hdf5_name: the name fo this hdf5 file
    :return: the name of the substrate and hydraulic file used to create the merge file
    """

    file,bfailload=open_hdf5_(hdf5_name, path_hdf5)
    if bfailload:
        return '',''

    # get the name
    try:
        sub_ini = file.attrs['sub_ini_name']
    except KeyError:
        sub_ini = ''
    try:
        hydro_ini = file.attrs['hydro_ini_name']
    except KeyError:
        hydro_ini = ''
    file.close()
    return sub_ini, hydro_ini


def add_habitat_to_merge(hdf5_name, path_hdf5, vh_cell, h_cell, v_cell, fish_name):
    """
    This function takes a merge file and add habitat data to it. The habitat data is given by cell. It also save the
    velocity and the water height by cell (and not by node)

    :param hdf5_name: the name of the merge file
    :param path_hdf5: the path to this file
    :param vh_cell: the habitat value by cell
    :param h_cell: the height data by cell
    :param v_cell: the velocity data by cell
    :param fish_name: the name of the fish (with the stage in it)
    """
    file_hydro, bfailload = open_hdf5_(hdf5_name, path_hdf5)
    if bfailload:
        return

    # load the number of time steps
    basename1 = 'Data_gen'
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_timestep"]
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name
              + ' an hydrological input? \n')
        return
    try:
        nb_t = list(gen_dataset.values())[0]
    except IndexError:
        print('Error: Time step are not found')
        return
    nb_t = np.array(nb_t)
    nb_t = int(nb_t)

    # load the number of reach
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_reach"]
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. \n')
        return
    nb_r = list(gen_dataset.values())[0]
    nb_r = np.array(nb_r)
    nb_r = int(nb_r)

    # add name and stage of fish
    if len(vh_cell) != len(fish_name):
        print('Error: length of the list of fish name is not coherent')
        file_hydro.close()
        return
    ascii_str = [n.strip().encode("ascii", "ignore") for n in fish_name]  # unicode is not ok with hdf5
    # not too pratical but rewriting hdf5 is really annoying
    # to load use list(for.keys()) and use all the one starting with data_habitat
    data_all = file_hydro.create_group('Data_habitat_' + time.strftime("%d_%m_%Y_at_%H_%M_%S"))
    name_fishg = data_all.create_group('Fish_name')
    name_fishg.create_dataset(name=hdf5_name, shape=(len(fish_name), ), data=ascii_str)  # , maxshape=None

    # habitat value and cell data
    m = 0
    all_ok = True
    # for all timestep
    for t in range(1, nb_t):
        there = data_all.create_group('Timestep_' + str(t - 1))
        # for all reach
        for r in range(0, nb_r):
            rhere = there.create_group('Reach_' + str(r))
            # for all fish
            for s in range(0, len(fish_name)):
                try:
                    habitatg = rhere.create_group('habitat_' + fish_name[s])
                except ValueError:
                    print('Warning: Two identical fish name are found \n')
                    habitatg = rhere.create_group('habitat_' + fish_name[s]+str(m))
                    m += 1
                aa = 1
                if len(vh_cell[s]) > 0:
                    try:
                        if len(vh_cell[s][t]) > 2:
                            habitatg.create_dataset(hdf5_name, [len(vh_cell[s][t][r]), 1],
                                                 data=vh_cell[s][t][r], maxshape=None)
                    except IndexError or ValueError:
                       print('Warning: One fish information could not be saved\n')

            velg = rhere.create_group('velocity_by_cell_reach_' + str(r))
            if len(v_cell[t][r]) > 0:
                velg.create_dataset(hdf5_name, [len(v_cell[t][r]), 1], data=h_cell[t][r],
                                    maxshape=None)
            velg = rhere.create_group('height_by_cell_reach_'+str(r))
            if len(h_cell[t][r]) > 0:
                velg.create_dataset(hdf5_name, [len(h_cell[t][r]), 1], data=h_cell[t][r],
                                    maxshape=None)

    file_hydro.close()
    time.sleep(1)  # as we need to insure different group of name


def get_habitat_value():
    print("aa")


def save_hdf5(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5, ikle_all_t, point_all_t, point_c_all_t,
              inter_vel_all_t, inter_h_all_t, xhzv_data=[], coord_pro=[], vh_pro=[], nb_pro_reach=[], merge=False,
              sub_pg_all_t=[], sub_dom_all_t=[], sub_per_all_t=[], sim_name=[], sub_ini_name='', hydro_ini_name='',
              save_option=None, version=0):
    """
    This function save the hydrological data in the hdf5 format.

    :param name_hdf5: the base name for the hdf5 file to be created (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param ikle_all_t: the connectivity table for all discharge, for all reaches and all time steps
    :param point_all_t: the point forming the grid, for all reaches and all time steps
    :param point_c_all_t: the point at the center of the cells, for all reaches and all time steps
    :param inter_vel_all_t: the velocity for all grid point, for all reaches and all time steps (by node)
    :param inter_h_all_t: the height for all grid point, for all reaches and all time steps (by node)
    :param xhzv_data: data linked with 1D model (only used when a 1D model was transformed to a 2D)
    :param coord_pro: data linked with 1.5D model or data created by dist_vist from a 1D model (profile data)
    :param vh_pro: data linked with 1.5D model or data created by dist_vist from a 1D model (velcoity and height data)
    :param nb_pro_reach: data linked with 1.5D model or data created by dist_vist from a 1D model (nb profile)
    :param merge: If True, the data is coming from the merging of substrate and hydrological data.
    :param sub_pg_all_t: the data of the coarser substrate given on the merged grid by cell. Only used if merge is True.
    :param sub_dom_all_t: the data of the dominant substrate given on the merged grid by cells. Only used if merge is True.
    :param sub_per_all_t: the data of the substreate by percentage. Only used with lammi (mostly)
    :param sim_name: the name of the simulation or the names of the time steps if the names are not [0,1,2,3, etc.]
    :param sub_ini_name: The name of the substrate hdf5 file from which the data originates
    :param hydro_ini_name: the name of the hydraulic hdf5 file from which the data originates
    :param save_option: If save_option is not none, the variable erase_idem which is usually given in the figure option
           is overwritten by save_option which is boolean. This is useful for habby cmd.
    :param version: The version number of HABBY


    **Technical comments**

    This function could look better inside the class SubHydroW where it was before. However, it was not possible
    to use it on the command line and it was not pratical for having two thread (it is impossible to have a method
    as a second thread)

    This function creates an hdf5 file which contains the hydrological data. First it creates an empty hdf5.
    Then it fill the hdf5 with data. For 1D model, it fill the data in 1D (the original data), then the 1.5D data
    created by dist_vitess2.py and finally the 2D data. For model in 2D it only saved 2D data. Hence, the 2D data
    is the data which is common to all model and which can always be loaded from a hydrological hdf5 created by
    HABBY. The 1D and 1.5D data is only present if the model is 1D or 1.5D. Here is some general info about the
    created hdf5:

    *   Name of the file: name_hdf5. If we save all file even if the model is re-run we add a time stamp.
        For example, test4_HEC-RAS_25_10_2016_12_23_23.h5.
    *   Position of the file: in the folder  figure_habby currently (probably in a project folder in the final software)
    *   Format of the hdf5 file:

        *   Dats_gen:  number of time step and number of reach
        *   Data_1D:  xhzv_data_all (given profile by profile)
        *   Data_15D :  vh_pro, coord_pro (given profile by profile in a dict) and nb_pro_reach.
        *   Data_2D : For each time step, for each reach: ikle, point, point_c, inter_h, inter_vel

    If a list has elements with a changing number of variables, it is necessary to create a dictionary to save
    this list in hdf5. For example, a dictionary will be needed to save the following list: [[1,2,3,4], [1,2,3]].
    This is used for example, to save data by profile as we can have profile with more or less points. We also note
    in the hdf5 attribute some important info such as the project name, path to the project, hdf5 version.
    This can be useful if an hdf5 is lost and is not linked with any project. We also add the name of the created
    hdf5 to the xml project file. Now we can load the hydrological data using this hdf5 file and the xml project file.

    When saving habitat data, we add a time stamp so that if re-run an habitat simulation, we do not loos all the data.
    When loading, the last data should be used.

    Hdf5 file do not support unicode. It is necessary to encode string to write them.

    """
    # to know if we have to save a new hdf5


    if save_option is None:
        save_opt = output_fig_GUI.load_fig_option(path_prj, name_prj)
        if save_opt['erase_id'] == 'True':  # xml is all in string
            erase_idem = True
        else:
            erase_idem = False
    else:
        erase_idem = save_option

    # create hdf5 name if we keep all files (need a time stamp)
    if not erase_idem:
        h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
    else:
        if name_hdf5[-3:] != '.h5':
            h5name = name_hdf5 + '.h5'
        else:
            h5name = name_hdf5
        if os.path.isfile(os.path.join(path_hdf5, h5name)):
            try:
                os.remove(os.path.join(path_hdf5, h5name))
            except PermissionError:
                    print("Could not save hdf5 file. It might be used by another program \n")
                    return

    # create a new hdf5
    fname = os.path.join(path_hdf5, h5name)
    file = h5py.File(fname, 'w')

    # create attributes
    file.attrs['Software'] = 'HABBY'
    file.attrs['Software_version'] = str(version)
    file.attrs['path_projet'] = path_prj
    file.attrs['name_projet'] = name_prj
    file.attrs['HDF5_version'] = h5py.version.hdf5_version
    file.attrs['h5py_version'] = h5py.version.version
    file.attrs['sub_ini_name'] = sub_ini_name
    file.attrs['hydro_ini_name'] = hydro_ini_name

    # create all datasets and group
    data_all = file.create_group('Data_gen')
    timeg = data_all.create_group('Nb_timestep')
    timeg.create_dataset(h5name, data=len(ikle_all_t) - 1)  # the first time step is for the whole profile
    nreachg = data_all.create_group('Nb_reach')
    nreachg.create_dataset(h5name, data=len(ikle_all_t[0]))
    # data by type of model (1D, 1.5D, 2D)
    if nb_dim == 1:
        Data_1D = file.create_group('Data_1D')
        xhzv_datag = Data_1D.create_group('xhzv_data')
        xhzv_datag.create_dataset(h5name, data=xhzv_data)
    if nb_dim < 2:
        Data_15D = file.create_group('Data_15D')
        adict = dict()
        for p in range(0, len(coord_pro)):
            ns = 'p' + str(p)
            adict[ns] = coord_pro[p]
        coord_prog = Data_15D.create_group('coord_pro')
        for k, v in adict.items():
            coord_prog.create_dataset(k, data=v)
            # coord_prog.create_dataset(h5name, [4, len(self.coord_pro[p][0])], data=self.coord_pro[p])
        for t in range(0, len(vh_pro)):
            there = Data_15D.create_group('Timestep_' + str(t))
            adict = dict()
            for p in range(0, len(vh_pro[t])):
                ns = 'p' + str(p)
                adict[ns] = vh_pro[t][p]
            for k, v in adict.items():
                there.create_dataset(k, data=v)
        nbproreachg = Data_15D.create_group('Number_profile_by_reach')
        nb_pro_reach2 = list(map(float, nb_pro_reach))
        nbproreachg.create_dataset(h5name, [len(nb_pro_reach2), 1], data=nb_pro_reach2)
    if nb_dim <= 2:
        warn_dry = True
        Data_2D = file.create_group('Data_2D')
        for t in range(0, len(ikle_all_t)):
            if t == 0:
                there = Data_2D.create_group('Whole_Profile')
            else:
                there = Data_2D.create_group('Timestep_' + str(t - 1))
            for r in range(0, len(ikle_all_t[t])):
                rhere = there.create_group('Reach_' + str(r))
                # ikle
                ikleg = rhere.create_group('ikle')
                if len(ikle_all_t[t][r]) > 0:
                    ikleg.create_dataset(h5name, [len(ikle_all_t[t][r]), len(ikle_all_t[t][r][0])],
                                         data=ikle_all_t[t][r])
                else:
                    if warn_dry:
                        print('Warning: Reach number ' + str(r) + ' has an empty grid. It might be entierely dry.')
                        warn_dry = False
                    ikleg.create_dataset(h5name, [len(ikle_all_t[t][r])], data=ikle_all_t[t][r])

                # coordinates
                point_allg = rhere.create_group('point_all')
                point_allg.create_dataset(h5name, [len(point_all_t[t][r]), 2], data=point_all_t[t][r])

                # coordinates center
                point_cg = rhere.create_group('point_c_all')
                if len(point_c_all_t)>0:
                    if len(point_c_all_t[t]) > 0 and not isinstance(point_c_all_t[t][0], float):
                        point_cg.create_dataset(h5name, [len(point_c_all_t[t][r]), 2], data=point_c_all_t[t][r])

                # velocity
                inter_velg = rhere.create_group('inter_vel_all')
                if len(inter_vel_all_t)>0:
                    if len(inter_vel_all_t[t]) > 0 and not isinstance(inter_vel_all_t[t][0], float):
                        inter_velg.create_dataset(h5name, [len(inter_vel_all_t[t][r]), 1],
                                                  data=inter_vel_all_t[t][r])
                # height
                inter_hg= rhere.create_group('inter_h_all')
                if len(inter_h_all_t) >0:
                    if len(inter_h_all_t[t]) > 0 and not isinstance(inter_h_all_t[t][0], float):
                        inter_hg.create_dataset(h5name, [len(inter_h_all_t[t][r]), 1],
                                                data=inter_h_all_t[t][r])

                # substrate data in the case it is a merged grid
                if merge:
                    data_subg = rhere.create_group('data_substrate_dom')
                    if len(sub_dom_all_t)>0:
                        if len(sub_dom_all_t[t]) > 0 and not isinstance(sub_dom_all_t[t][0], float):
                            data_subg.create_dataset(h5name, [len(sub_dom_all_t[t][r]), 1],
                                                data=sub_dom_all_t[t][r])
                    data_subg = rhere.create_group('data_substrate_pg')
                    if len(sub_pg_all_t) > 0:
                        if len(sub_pg_all_t[t]) > 0 and not isinstance(sub_pg_all_t[t][0], float):
                            data_subg.create_dataset(h5name, [len(sub_pg_all_t[t][r]), 1],
                                                     data=sub_pg_all_t[t][r])
                    if sub_per_all_t:
                        data_subg = rhere.create_group('data_substrate_percentage')
                        if len(sub_per_all_t[t]) > 0:
                            data_subg.create_dataset(h5name, [len(sub_per_all_t[t][r]), 8], data=sub_per_all_t[t][r])

        # save the name of the simulation/time steps if they exist
        if sim_name:
            ascii_str = [n.strip().encode("ascii", "ignore") for n in sim_name]  # unicode is not ok with hdf5
            tname_typeg = Data_2D.create_group('timestep_name')
            tname_typeg.create_dataset(h5name, (len(sim_name), 1), data=ascii_str)

    file.close()

    # save the file to the xml of the project
    if merge:
        type_hdf5 =  "hdf5_mergedata"
    else:
        type_hdf5 = "hdf5_hydrodata"

    filename_prj = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(filename_prj):
        print('Error: No project saved. Please create a project first in the General tab.\n')
        return
    else:
        doc = ET.parse(filename_prj)
        root = doc.getroot()
        child = root.find(".//" + model_type)
        # if the xml attribute do not exist yet, xml name should be saved
        if child is None:
            here_element = ET.SubElement(root, model_type)
            hdf5file = ET.SubElement(here_element, type_hdf5)
            hdf5file.text = h5name
        else:
            # if we save all files even identical file, we need to save xml
            if not erase_idem:
                hdf5file = ET.SubElement(child, type_hdf5)
                hdf5file.text = h5name
            # if the xml attribute exist and we do not save all file, we should only save attribute if new
            else:
                child2s = root.findall(".//" + model_type + "/" + type_hdf5)
                if child2s is not None:
                    found_att_text = False
                    for c in child2s:
                            if c.text == h5name:
                                found_att_text = True
                    if not found_att_text:
                        hdf5file = ET.SubElement(child, type_hdf5)
                        hdf5file.text = h5name
                else:
                    hdf5file = ET.SubElement(child, type_hdf5)
                    hdf5file.text = h5name

        doc.write(filename_prj)

    return


def save_hdf5_sub(path_hdf5, path_prj, name_prj, sub_pg, sub_dom, ikle_sub=[], coord_p=[], name_hdf5 ='', constsub=False,
                  model_type='SUBSTRATE', return_name=False):
    """
    This function creates an hdf5 with the substrate data. This hdf5 does not have the same form than the hdf5 file used
    to store hydrological or merge data. This hdf5 store the substrate data alone before it is merged with the
    hydrological info. The substrate info should be given in the cemagref code.

    :param path_hdf5: the path where the hdf5 file should be saved
    :param path_prj: the project path
    :param name_prj: the name of the project
    :param sub_pg: the coarser part of the substrate (array with length of ikle if const_sub is False, a float otherwise)
    :param sub_dom: the dominant part of the substrate (array with length of ikle if const_sub is False, a float otherwise)
    :param ikle_sub: the connectivity table for the substrate (only if constsub = False)
    :param coord_p: the point of the grid of the substrate (only if constsub = False)
    :param name_hdf5: the name of the substrate h5 file (without the timestamp). If not given, a default name is used.
    :param constsub: If True the substrate is a constant value
    :param model_type: the attribute for the xml file (usually SUBSTRATE)
    :param return_name: If True this function return the name of the substrate hdf5 name
    """

    # to know if we have to save a new hdf5
    save_opt = output_fig_GUI.load_fig_option(path_prj, name_prj)
    if save_opt['erase_id'] == 'True':  # xml is all in string
        erase_idem = True
    else:
        erase_idem = False
    save_xml = True

    if name_hdf5[-3:] == '.h5':
        name_hdf5 = name_hdf5[:-3]

    if constsub:  # constant value of substrate

        # create hdf5 name if we keep all the files (need a time stamp)
        if not erase_idem:
            if name_hdf5:
                h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
            else:
                h5name = 'Substrate_CONST_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
        # create hdf5 name if we erase identical files
        else:
            if name_hdf5:
                h5name = name_hdf5 + '.h5'
            else:
                h5name = 'Substrate_CONST.h5'
            if os.path.isfile(os.path.join(path_hdf5, h5name)):
                try:
                    os.remove(os.path.join(path_hdf5, h5name))
                except PermissionError:
                    print("Could not save hdf5 substrate data. It might be used by another program \n")
                    return
                save_xml = False


        # create a new hdf5
        fname = os.path.join(path_hdf5, h5name)
        file = h5py.File(fname, 'w')

        # create attributes
        file.attrs['path_projet'] = path_prj
        file.attrs['name_projet'] = name_prj
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version

        # add the constant value of substrate
        constsubpg = file.create_group('constant_sub_pg')
        if isinstance(sub_pg, float) or isinstance(sub_pg, int):
            constsubpg.create_dataset(h5name, [1, 1], data=sub_pg)
        else:
            print('Error: Constant substrate not recognized. (1) \n')
        constsubdom = file.create_group('constant_sub_dom')
        if isinstance(sub_dom, float) or isinstance(sub_dom, int):
            constsubdom.create_dataset(h5name, [1, 1], data=sub_dom)
        else:
            print('Error: Constant substrate not recognized. (2) \n')

        file.close()

    else:  # grid

        # create hdf5 name
        if not erase_idem:
            if name_hdf5:
                h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
            else:
                h5name = 'Substrate_VAR_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
        # create hdf5 name if we erase identical files
        else:
            if name_hdf5:
                h5name = name_hdf5 + '.h5'
            else:
                h5name = 'Substrate_VAR.h5'
            if os.path.isfile(os.path.join(path_hdf5, h5name)):
                try:
                    os.remove(os.path.join(path_hdf5, h5name))
                except PermissionError:
                    print('Could not save hdf5 substrate file. It might be used by another program \n')
                    return
                save_xml = False

        # create a new hdf5
        fname = os.path.join(path_hdf5, h5name)
        file = h5py.File(fname, 'w')

        # create attributes
        file.attrs['path_projet'] = path_prj
        file.attrs['name_projet'] = name_prj
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version

        # save ikle, coordonate and data
        ikleg = file.create_group('ikle_sub')
        coordpg = file.create_group('coord_p_sub')
        if len(ikle_sub) > 0:
            # the grid is not necessary triangular for the subtrate
            for id, c in enumerate(ikle_sub):
                ns = 'p' + str(id)
                ikleg.create_dataset(ns, data=c)

        coordpg.create_dataset(h5name, [len(coord_p), 2], data=coord_p)

        # substrate data (cemagref code ususally)
        datasubpg = file.create_group('data_sub_pg')
        if len(ikle_sub) == len(sub_pg):
            datasubpg.create_dataset(h5name, [len(sub_pg),1], data=sub_pg)
        else:
            print('Error: Substrate data not recognized (1) \n')
        datasubpg = file.create_group('data_sub_dom')
        if len(ikle_sub) == len(sub_dom):
            datasubpg.create_dataset(h5name, [len(sub_dom), 1], data=sub_dom)
        else:
            print('Error: Substrate data not recognized (2) \n')

        file.close()

    # save the file to the xml of the project
    filename_prj = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(filename_prj):
        print('Error: No project saved. Please create a project first in the General tab.\n')
        return
    else:
        if save_xml:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//" + model_type)
            if child is None:
                stathab_element = ET.SubElement(root, model_type)
                hdf5file = ET.SubElement(stathab_element, "hdf5_substrate")
                hdf5file.text = h5name
            else:
                hdf5file = ET.SubElement(child, "hdf5_substrate")
                hdf5file.text = h5name
            doc.write(filename_prj)

    if return_name:
        return h5name
    else:
        return


def copy_files(names,paths, path_input):
    """
    This function copied the input files to the project file. The input files are usually contains in the input
    project file. It is ususally done on a second thread as it might be long.

    For the moment this function cannot send warning and error to the GUI. As input should have been cheked before
    by HABBY, this should not be a problem.

    :param names: the name of the files to be copied (list of string)
    :param paths: the path to these files (list of string)
    :param path_input: the path where to send the input (string)
    """

    if not os.path.isdir(path_input):
        print('Error: Folder not found to copy inputs \n')
        return

    if len(names) != len(paths):
        print('Error: the number of file to be copied is not equal to the number of paths')
        return

    for i in range(0, len(names)):
        if names[i] != 'unknown file':
            src = os.path.join(paths[i], names[i])
            # if the file is too big, the GUI is freezed
            if os.path.getsize(src) > 200 * 1024 * 1024:
                print('Warning: One input file was larger than 200MB and therefore was not copied to the project'
                      ' folder. It is necessary to copy this file manually to the input folder if one wants to use the '
                      'restart file or the log file to load this data auomatically again. \n')
            else:
                if os.path.isfile(src):
                    dst = os.path.join(path_input, names[i])
                    shutil.copy(src, dst)


def addition_hdf5(path1, hdf51, path2, hdf52, name_prj, path_prj, model_type, path_hdf5, merge=False, erase_id=True,
                  return_name=False, name_out=''):
    """
    This function merge two hdf5 together. The hdf5 files should be of hydrological or merge type and both grid should
    in the same coordinate system. It is not possible to have one merge file and one hydrological hdf5 file. They both
    should be of the same type. The two grid are added as two separeted river reach.

    :param path1: the path to the first hydrological hdf5
    :param hdf51: the name of the first hdf5 file
    :param path2: the path to the second hdf5
    :param hdf52: the name of the second hdf5
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: the type of model (used to save the new file name into the project xml file)
    :param path_hdf5: the path where to save the hdf5 (ususally path_prj, but not always)
    :param merge: If True, this is a merge hdf5 file and not only hydraulic data. Boolean.
    :param erase_id: If true and if a similar hdf5 exist, il will be erased
    :param reteurn_name: If True, it return the name of the created hdf5
    :param name_out: name of the new hdf5 (optional)

    """
    substrate_all_dom1 = []
    substrate_all_dom2 = []
    substrate_all_pg1 = []
    substrate_all_pg2 = []

    # load first hdf5
    if merge:
        [ikle1, point1, inter_vel1, inter_height1, substrate_all_pg1, substrate_all_dom1] \
            = load_hdf5_hyd(hdf51, path1, merge)
    else:
        [ikle1, point1, inter_vel1, inter_height1] = load_hdf5_hyd(hdf51, path1, merge)

    # load second hdf5
    if merge:
        [ikle2, point2, inter_vel2, inter_height2, substrate_all_pg2, substrate_all_dom2] \
            = load_hdf5_hyd(hdf52, path2, merge)
    else:
        [ikle2, point2, inter_vel2, inter_height2] = load_hdf5_hyd(hdf52, path2, merge)

    if len(ikle1) == 0 or len(ikle2) == 0:
        return
    if ikle1 == [[-99]] or ikle2 == [[-99]]:
        print('Error: Could not load the chosen hdf5. \n')
        return

    # check time step and load time step name
    if len(ikle1) != len(ikle2):
        print('Error: the number of time step between the two hdf5 is not coherent. \n')
        return
    sim_name = load_timestep_name(hdf51, path1)

    # add the second grid as new reach
    # reach grids can intersect in HABBY
    for t in range(0, len(ikle1)):
        ikle1[t].extend(ikle2[t])
        point1[t].extend(point2[t])
        inter_vel1[t].extend(inter_vel2[t])
        inter_height1[t].extend(inter_height2[t])
        if merge:
            substrate_all_pg1[t].extend(substrate_all_pg2[t])
            substrate_all_dom1[t].extend(substrate_all_dom2[t])

    # save the new data

    if merge:
        new_hdf5_name = 'ADDMERGE' + hdf51[5:-3] + '_AND' + hdf52[5:-3]
        if name_out:
            new_hdf5_name = name_out
        save_hdf5(new_hdf5_name, name_prj, path_prj, model_type, 2, path_hdf5, ikle1, point1, [],
                  inter_vel1, inter_height1, merge=merge, sub_pg_all_t=substrate_all_pg1,
                  sub_dom_all_t=substrate_all_dom1, sim_name=sim_name,save_option=erase_id)
    else:
        new_hdf5_name = 'ADDHYDRO' + hdf51[5:-3] + '_AND' + hdf52[5:-3]
        if name_out:
            new_hdf5_name = name_out
        save_hdf5(new_hdf5_name, name_prj, path_prj, model_type, 2, path_hdf5, ikle1, point1, [],
                  inter_vel1, inter_height1, merge=merge, sim_name=sim_name, save_option=erase_id)

    # return name if necessary (often used if more than two hdf5 are added at the same time)
    if return_name:
        return new_hdf5_name


def create_shapfile_hydro(name_hdf5, path_hdf5, path_shp, merge=True, erase_id=True):
    """
    This function creates a shapefile with the hydraulic and shapefile data. This can be used to check how the data
    was merged. The shapefile will have the same name than the hdf5 file. There are some similairites between this
    function and the function in calcul_hab.py (save_hab_shape). It might be useful to change both function if
    corrections must be done.

    :param name_hdf5: the name of the hdf5 file (with .h5 extension)
    :param path_hdf5: the path to the hdf5 file
    :param path_shp: The path where the shapefile will be created
    :param erase_id: Should we kept all shapefile or erase old files if they comes from the same model
    :param merge: If ture, the hdf5 file is a merge file with substrate data (usually True)
    """

    [ikle_all_t, point_all_t, vel_nodes, height_node, sub_pg_data, sub_dom_data] = load_hdf5_hyd(name_hdf5,
                                                                                                 path_hdf5, merge)
    if ikle_all_t == [[-99]] or len(ikle_all_t) < 1:
        return
    sim_name = load_timestep_name(name_hdf5, path_hdf5)

    # we needs the data by cells and not nodes
    # optmization possibility: save the data in the hdf5 and re-use it for the habitat calculation
    vel_data = [[]]
    height_data = [[]]
    for t in range(1, len(ikle_all_t)):  # ikle_all_t[0] has no velocity
        ikle_all = ikle_all_t[t]
        vel_all = vel_nodes[t]
        he_all = height_node[t]
        vel_data_here = []
        height_data_here = []
        for r in range(0, len(ikle_all)):
            ikle = ikle_all[r]
            try:
                v = vel_all[r]
                h = he_all[r]
            except IndexError:
                print('Velocity data was missing for one time step. Could not create a shapefile to check data. \n')
                return
            # get data by cells
            try:
                v1 = v[ikle[:, 0]]
                v2 = v[ikle[:, 1]]
                v3 = v[ikle[:, 2]]
                v_cell = 1.0 / 3.0 * (v1 + v2 + v3)
                vel_data_here.append(v_cell)

                h1 = h[ikle[:, 0]]
                h2 = h[ikle[:, 1]]
                h3 = h[ikle[:, 2]]
                h_cell = 1.0 / 3.0 * (h1 + h2 + h3)
                height_data_here.append(h_cell)
            except IndexError:
                vel_data_here.append([])
                vel_data_here.append([])
        vel_data.append(vel_data_here)
        height_data.append(height_data_here)

    # we do not print the first time step with the whole profile

    for t in range(1, len(ikle_all_t)):
        ikle_here = ikle_all_t[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            w = shapefile.Writer(shapefile.POLYGON)
            w.autoBalance = 1

            # get the triangle
            nb_reach = len(ikle_all_t[t])
            for r in range(0, nb_reach):
                ikle_r = ikle_all_t[t][r]
                point_here = point_all_t[t][r]
                for i in range(0, len(ikle_r)):
                    p1 = list(point_here[ikle_r[i][0]])
                    p2 = list(point_here[ikle_r[i][1]])
                    p3 = list(point_here[ikle_r[i][2]])
                    w.poly(parts=[[p1, p2, p3, p1]])  # the double [[]] is important or it bugs, but why?

            if t > 0:
                # attribute
                w.field('velocity', 'F', 50, 8)
                w.field('water heig', 'F', 50, 8)
                w.field('conveyance', 'F', 50, 8)
                if merge:
                    w.field('sub_coarser', 'F', 50, 8)
                    w.field('sub_dom', 'F', 50, 8)

                # fill attribute
                for r in range(0, nb_reach):
                    vel = vel_data[t][r]
                    height = height_data[t][r]
                    sub_pg = sub_pg_data[t][r]
                    sub_dom = sub_dom_data[t][r]
                    ikle_r = ikle_all_t[t][r]
                    for i in range(0, len(ikle_r)):
                        data_here = ()
                        if merge:
                            data_here += vel[i], height[i], vel[i] * height[i], sub_pg[i], sub_dom[i]
                        else:
                            data_here += vel[i], height[i], vel[i] * height[i]
                        # the * pass tuple to function argument
                        w.record(*data_here)

            w.autoBalance = 1

            # save
            name_base = name_hdf5[:-3]
            if not erase_id:
                if not sim_name:
                    name1 = name_base + '_t_' + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
                else:
                    name1 = name_base + '_t_' + sim_name[t - 1] + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
            else:
                if not sim_name:
                    name1 = name_base + '_t_' + str(t) + '.shp'
                else:
                    name1 = name_base + '_t_' + sim_name[t - 1] + '.shp'
                if os.path.isfile(os.path.join(path_shp, name1)):
                    try:
                        os.remove(os.path.join(path_shp, name1))
                    except PermissionError:
                        print('Error: The shapefile is currently open in an other program. Could not be re-written \n')
                        return

            w.save(os.path.join(path_shp, name1))
