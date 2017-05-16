import h5py
import os
import numpy as np
import time
import shutil
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def open_hdf5(hdf5_name):
    """
    This is a function which open an hdf5 file and check that it exists. it does not load the data. It only opens the
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


def load_hdf5_hyd(hdf5_name_hyd, path_hdf5 = '', merge=False):
    """
    A function to load the 2D hydrological data contains in the hdf5 file in the form required by HABBY. f hdf5_name_sub
    is an absolute path, the path_prj is not used. If it is a relative path, the path is composed of the path to the
    project (path_prj) composed with hdf5_name_sub.

    :param hdf5_name_hyd: filename of the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :param merge: If merge is True. this is a merged file with substrate data added
    :return: the connectivity table, the coordinates of the point, the height data, the velocity data on the coordinates.

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

    # open the file with checking for the path
    if os.path.isabs(hdf5_name_hyd):
        file_hydro = open_hdf5(hdf5_name_hyd)
    else:
        if path_hdf5:
            file_hydro = open_hdf5(os.path.join(path_hdf5, hdf5_name_hyd))
        else:
            print('Error" No path to the project given although a relative path was provided')
            return failload
    if file_hydro is None:
        print('Error: hdf5 file could not be open. \n')
        return failload

    # load the number of time steps
    basename1 = 'Data_gen'
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_timestep"]
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name_hyd
            + ' an hydrological input? \n')
        return failload
    try:
        nb_t = list(gen_dataset.values())[0]
    except IndexError:
        print('Error: Time step are not found')
        return failload
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
        try:
            ikle_whole = list(gen_dataset.values())[0]
        except IndexError:
            print('Error: the dataset for ikle (3) is missing from the hdf5 file. \n')
            return failload
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
                    'Error: the dataset for ikle (2) is missing from the hdf5 file for one time step. \n')
                return failload
            try:
                ikle_whole = list(gen_dataset.values())[0]
            except IndexError:
                print('Error: the dataset for ikle (4) is missing from the hdf5 file for one time step. \n')
                return failload
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
        try:
            point_whole = list(gen_dataset.values())[0]
        except IndexError:
            print('Error: the dataset for coordinates of the points (3) is missing from the hdf5 file. \n')
            return failload
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
                print('Error: the dataset for coordinates of the points (2) is missing from the hdf5 file. \n')
                return failload
            try:
                point_whole = list(gen_dataset.values())[0]
            except IndexError:
                print('Error: the dataset for coordinates of the points (4) is missing from the hdf5 file. \n')
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
                return failload
            if len(list(gen_dataset.values())) ==0:
                print('Error: No velocity found in the hdf5 file. \n')
                return failload
            vel = list(gen_dataset.values())[0]
            vel = np.array(vel).flatten()
            vel_all.append(vel)
            #height
            try:
                gen_dataset = file_hydro[name_he]
            except KeyError:
                print('Error: the dataset for water height is missing from the hdf5 file. \n')
                return failload
            if len(list(gen_dataset.values())) == 0:
                print('Error: No height found in the hdf5 file. \n')
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
                    return failload
                try:
                    subpg = list(gen_datasetpg.values())[0]
                except IndexError:
                    print('Error: the dataset for substrate is missing from the hdf5 file (2). \n')
                    return failload
                subpg = np.array(subpg).flatten()
                try:
                    subdom = list(gen_datasetdom.values())[0]
                except IndexError:
                    print('Error: the dataset for substrate is missing from the hdf5 file (3). \n')
                    return failload
                subdom = np.array(subdom).flatten()
                sub_pg_all.append(subpg)
                sub_dom_all.append(subdom)
        inter_vel_all.append(vel_all)
        inter_height_all.append(h_all)
        if merge:
            substrate_all_dom.append(sub_dom_all)
            substrate_all_pg.append(sub_pg_all)

    if not merge:
        return ikle_all_t, point_all, inter_vel_all, inter_height_all
    else:
        return ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom


def load_hdf5_sub(hdf5_name_sub, path_hdf5):
    """
    A function to load the substrate data contained in the hdf5 file. It also manage
    the constant cases. If hdf5_name_sub is an absolute path, the path_prj is not used. If it is a relative path,
    the path is composed of the path to the 'hdf5' folder (path_prj/fichier_hdf5) composed with hdf5_name_sub. it manages constant and
    vairable (based on a grid) cases. The code should be of cemagref type and the data is given as coarser and dominant.

    :param hdf5_name_sub: path and file name to the hdf5 file (string)
    :param path_prj: the path to the hdf5 file
    """

    # correct all change to the hdf5 form in the doc!
    ikle_sub = []
    point_all_sub = []
    failload = [[-99]], [[-99]], [[-99]],[[-99]]

    # open the file
    if os.path.isabs(hdf5_name_sub):
        file_sub = open_hdf5(hdf5_name_sub)
    else:
        if path_hdf5:
            file_sub = open_hdf5(os.path.join(path_hdf5, hdf5_name_sub))
        else:
            print('Error" No path to the project given although a relative path was provided')
            return failload
    if file_sub is None:
        print('Error: hdf5 file could not be open. \n')
        return failload

    # manage the constant case
    constname = 'constant_sub_pg'
    if constname in file_sub:
        try:
            sub_pg = file_sub[constname]
            sub_dom = file_sub['constant_sub_dom']
        except KeyError:
            print('Error:Constant substrate data is not found. \n')
            return failload
        sub_pg = list(sub_pg.values())[0]
        sub_dom = list(sub_dom.values())[0]

    # the variable case
    else:
        # read the ikle data
        basename1 = 'ikle_sub'
        try:
            gen_dataset = file_sub[basename1]
        except KeyError:
            print('Error: the connectivity table for the substrate grid is missing from the hdf5 file. \n')
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

    return ikle_sub, point_all_sub, sub_pg, sub_dom


def get_all_filename(dirname, ext):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename+dir) for each extension
    """
    filenames = []
    for file in os.listdir(dirname):
        if file.endswith(ext):
            filenames.append(file)
    return filenames


def get_hdf5_name(model_name, name_prj, path_prj):
    """
    This function get the name of the hdf5 file containg the hydrological data for an hydrological model of type
    model_name. If there is more than one hdf5 file, it choose the last one. Tha path is the path from the
    project folder. Hencem, it is not the absolute path.

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
        child = root.find(".//" + model_name2)
        if child is not None:
            if model_name == 'MERGE' or model_name == 'LAMMI':
                child = root.findall(".//" + model_name2 + '/hdf5_mergedata')
            elif model_name == 'SUBSTRATE':
                child = root.findall(".//" + model_name2 + '/hdf5_substrate')
            else:
                child = root.findall(".//" + model_name + '/hdf5_hydrodata')
            if len(child) > 0:
                return child[-1].text
            else:
                print('Warning: the data for the model ' + model_name + ' was not found (1)')
                return ''
        else:
            print('Warning: the data for the model ' + model_name + ' was not found (2)')
            return ''
    else:
        print('Error: no project found by load_hdf5')
        return ''


def save_hdf5(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5, ikle_all_t, point_all_t, point_c_all_t, inter_vel_all_t,
              inter_h_all_t, xhzv_data=[], coord_pro=[], vh_pro=[], nb_pro_reach=[], merge=False, sub_pg_all_t=[], sub_dom_all_t=[]):
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

    *   Name of the file: name_hdf5  + date/time.h5.  For example, test4_HEC-RAS_25_10_2016_12_23_23.h5.
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

    Hdf5 file do not support unicode. It is necessary to encode string to write them.

    """

    # create hdf5 name
    h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'

    # create a new hdf5
    fname = os.path.join(path_hdf5, h5name)
    file = h5py.File(fname, 'w')

    # create attributes
    file.attrs['path_projet'] = path_prj
    file.attrs['name_projet'] = name_prj
    file.attrs['HDF5_version'] = h5py.version.hdf5_version
    file.attrs['h5py_version'] = h5py.version.version

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
                    print('Warning: Reach number ' + str(r) + ' has an empty grid. It might be entierely dry.')
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

    file.close()

    # save the file to the xml of the project
    filename_prj = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(filename_prj):
        print('Error: No project saved. Please create a project first in the General tab.\n')
        return
    else:
        doc = ET.parse(filename_prj)
        root = doc.getroot()
        child = root.find(".//" + model_type)
        if child is None:
            here_element = ET.SubElement(root, model_type)
            if not merge:
                hdf5file = ET.SubElement(here_element, "hdf5_hydrodata")
            else:
                hdf5file = ET.SubElement(here_element, "hdf5_mergedata")
        else:
            if not merge:
                hdf5file = ET.SubElement(child, "hdf5_hydrodata")
            else:
                hdf5file = ET.SubElement(child, "hdf5_mergedata")

        hdf5file.text = h5name

        doc.write(filename_prj)

    return


def save_hdf5_sub(path_hdf5, path_prj, name_prj, sub_pg, sub_dom,ikle_sub=[], coord_p=[], name_hdf5 ='', constsub=False,
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

    if constsub:  # constant value of substrate

        # create hdf5 name
        if name_hdf5:
            h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
        else:
            h5name = 'Substrate_CONST_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'

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
        if name_hdf5:
            h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'
        else:
            h5name = 'Substrate_VAR_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.h5'

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
        doc = ET.parse(filename_prj)
        root = doc.getroot()
        child = root.find(".//" + model_type)
        if child is None:
            stathab_element = ET.SubElement(root, model_type)
            hdf5file = ET.SubElement(stathab_element, "hdf5_substrate")
            hdf5file.text = h5name
        else:
            hdf5file = root.find(".//" + "hdf5_substrate")
            hdf5file = ET.SubElement(child, "hdf5_substrate")
            hdf5file.text = h5name
            #else:
                #hdf5file.text = hdf5file.text + ', ' + h5name  # keep the name of the old and new file
                #hdf5file.text = h5name  # keep only the new file
        doc.write(filename_prj)

    if return_name:
        return h5name
    else:
        return


def copy_files(names,paths, path_input):
    """
    This function copied the input files to the project file. The input files are usually contains in the input
    project file. It is ususally done on a second thread as it might be long.

    For the moment this function cannot send warning and error to the GUI. As input shoudl have been cheked before
    by HABBY, this should not be a problem.

    :param names: the name of the files to be copied (list of string)
    :param paths: the path to these files (list of string)
    :param path_input: the path where to send the input (string)
    """

    if not os.path.isdir(path_input):
        print('Error: Folder not found to copy inputs \n')
        return

    if len(names) != len(paths):
        print('Error: the number of file to be copied is not equalt to the number of paths')
        return

    for i in range(0, len(names)):
        if names[i] != 'unknown file':
            src = os.path.join(paths[i], names[i])
            if os.path.isfile(src):
                dst = os.path.join(path_input, names[i])
                shutil.copy(src, dst)