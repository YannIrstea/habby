
import os
import sys
import re
from io import StringIO
import numpy as np
import matplotlib.pyplot as plt
import time
from struct import unpack
from struct import error as errstruct
from src import Hec_ras06
from src import manage_grid_8
from src import load_hdf5
from src import dist_vistess2
from src_GUI import output_fig_GUI
import matplotlib as mpl


def load_mascaret_and_create_grid(name_hdf5, path_hdf5,name_prj, path_prj,model_type,namefile,pathfile, interpo_choice
                                 ,manning_data, nb_point_vel, show_fig_1D, pro_add, q=[], path_im='.', print_cmd=False):
    """
    This function is used to load the mascaret data by calling the load_mascaret() function and to create the grid
    by calling the grid_and_interpo function in manage_grid_8. This function is called in a second thread by the class
    Mascaret() in Hydro_grid_2(). It also distribute the velocity by calling dist_vitess2.

    :param name_hdf5: the name of the hdf5 to be created (string)
    :param path_hdf5: the path to the hdf5 to be created (string)
    :param model_type: the name of the model (mascaret in most case, but given as argument in case we change
           the form of the name)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param namefile: the name of the geo file and the data file, which contains respectively geographical data and
           the ouput data (see open_hec_ras() for more precision) -> list of string
    :param pathfile: the absolute path to the file chosen into namefile -> list of string
    :param interpo_choice: the interpolation type (int: 0,1,2 or 3). See grid_and_interpo() for mroe details.
    :param manning_data: Contains the manning data. It can be in an array form (variable) or as a float (constant)
    :param nb_point_vel: the number of velcoity point by whole profile
    :param show_fig_1D: A boolean. If True, image from the 1D data are created and savec
    :param q: used by the second thread.
    :param pro_add: the number of addictional profile (one used for interpolation_choice 1 and 2)
    :param path_im: the path where to save the figure
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line. We make the switch here.
    """

    # load mascaret
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach, timestep] \
        = load_mascaret(namefile[0], namefile[1], namefile[2], pathfile[0], pathfile[1], pathfile[2])
    if coord_pro == [-99]:
        print('Error: Mascaret data not loaded. \n')
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # image if necessary
    if show_fig_1D:
        fig_opt = output_fig_GUI.load_fig_option(path_prj, name_prj)
        pro = [0, 1, 2]
        reach = [0]
        if fig_opt['time_step'][0] == -99:
            tfig = range(0, len(xhzv_data))
        else:
            tfig = fig_opt['time_step']
            tfig = list(map(int, tfig))

        figure_mascaret(coord_pro, coord_r, xhzv_data, on_profile, nb_pro_reach, fig_opt, name_pro, name_reach, path_im,
                        pro, tfig, reach)

    # distribute the velocity
    vh_pro = dist_vistess2.distribute_velocity(manning_data, nb_point_vel, coord_pro, xhzv_data, on_profile)

    # create the grid
    [ikle_all_t, point_all_t, point_c_all_t, inter_vel_all_t, inter_h_all_t] \
        = manage_grid_8.grid_and_interpo(vh_pro, coord_pro, nb_pro_reach, interpo_choice, pro_add)

    # save the hdf5 file
    for idx, t in enumerate(timestep):
        timestep[idx] = str(t)
    load_hdf5.save_hdf5(name_hdf5, name_prj, path_prj, model_type, 1.5, path_hdf5, ikle_all_t, point_all_t,
                        point_c_all_t, inter_vel_all_t, inter_h_all_t, [], coord_pro, vh_pro, nb_pro_reach,
                        sim_name=timestep)
    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def load_mascaret(file_gen, file_geo, file_res, path_gen, path_geo, path_res):
    """
    The function is used to load the mascaret data. It load the geofile and the general file. Then, it re-forms the
    geometrical data. Next, it loads the output data from mascaret. Fianally, it looks which outputs is close to
    a profile and which outputs is not linked with a profile as there are some outputs given between profiles.

    :param file_gen: the xcas .xml file giving general info about the model (string)
    :param file_geo: the file containting the profile data (.geo) (string)
    :param file_res: the files containting the mascaret output in the Optyca format (.opt) (string)
    :param path_gen: the path to the xcas file or .cas file (string). By default, choose the xcas file.
    :param path_geo: the path to the geo file (string)
    :param path_res: the path to the res file (string)
    :return: the coordinates of the profile (x,y,z, dist along the profile), the coordinate of the river (x,y), name of
            reach and profile, data height and velocity (list by time step), list of bollean indicating which data is
            on the profile and the number of profile by reach.
    """

    # load the geofile (not georeferenced)
    blob, ext = os.path.splitext(file_geo)
    if ext == '.geo':
        [coord_pro1, name_pro, name_reach, nb_pro_reach, abscisse, bt] = open_geo_mascaret(file_geo, path_geo)
    else:
        print('Error: the geo file should be of .geo type.\n')
        return [-99], [-99], [-99], [-99], [-99], [-99], [-99]
    if name_reach == ['-99']:
        print('Error: .geo data not loaded. \n')
        return [-99], [-99], [-99], [-99], [-99], [-99], [-99]

    # general file
    blob, ext = os.path.splitext(file_gen)
    if ext == '.xcas':  # order matter as cas is in xcas. It loads xcas by default.
        [coord_r, nr] = river_coord_non_georef_from_xcas(file_gen, path_gen, abscisse, nb_pro_reach)
    elif ext == '.cas':
        [coord_r, nr] = river_coord_non_georef_from_cas(file_gen, path_gen, abscisse, nb_pro_reach)
    else:
        print('Error the general file should be of .xcas or .cas type.\n')
        return [-99], [-99], [-99], [-99], [-99], [-99], [-99]
    if nr == [-99]:
        print('Error: .xcas data not loaded. \n')
        return [-99], [-99], [-99], [-99], [-99], [-99], [-99]

    # profile info
    coord_xy = profil_coord_non_georef(coord_pro1, coord_r, nr, nb_pro_reach, bt)

    # update the form of coord_pro to be coherent with other hydrological models
    coord_pro = []
    r = 1
    for p in range(0, len(coord_pro1)):
        coord_pro_p = [coord_xy[p][0], coord_xy[p][1], coord_pro1[p][1], coord_pro1[p][0]]
        coord_pro.append(coord_pro_p)

    # result info
    blob, ext = os.path.splitext(file_res)
    if ext == '.rub':
        [xhzv_data, timestep] = open_rub_file(file_res, path_res)
    else:
        [xhzv_data, timestep] = open_res_file(file_res, path_res)
    if len(timestep) == 1 and timestep[0] == -99:
        print('Error: Data could not be loaded. \n')
        return -99, -99, -99, -99, -99, -99, -99
    on_profile = is_this_res_on_the_profile(abscisse, xhzv_data)
    if len(on_profile) == 1 and on_profile[0] == -99:
        print('Error: the profile number was not coherent.\n')
        return -99, -99, -99, -99, -99, -99, -99

    return coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach, timestep


def get_geo_name_from_xcas(file_gen, path_gen):
    """
    This function gets the name of the .geo file from the .xcas xml file. It is not used yet, but it could be useful
    in the GUI to simplify the loading of mascaret. The user would not need to give the name of the geo and the xcas
    files separetly. However, it is not written in yet.

    :param file_gen: the xcas file
    :param path_gen: the path to the xcas file
    :return: the name of the .geo file (no path indicated)
    """

    # load the xml file
    root = Hec_ras06.load_xml(file_gen, path_gen)
    if root == [-99]:  # if error arised
        print("Error: the .xcas file could not be read.\n")
        return
    # get the name of the geo file
    try:  # check that the data is not empty
        name_geo = root.findall(".//parametresGeometrieReseau/geometrie/fichier")
    except AttributeError:
        print("Error: The name of the .geo file cannot be read from the .xcas file.\n")
        return
    name_geo = name_geo[0].text
    return name_geo


def get_name_from_cas(file_gen, path_gen):
    """
    This function gets the name of the .geo file from the .cas text file. It is not used yet, but it could be useful
    in the GUI to simplify the loading of mascaret. The user would not need to give the name of the geo and the cas
    files separetly. However, it is not written in yet.

    :param file_gen: the name of .cas file (string)
    :param path_gen: the path to the cas file (string
    :return: the name of the .geo file (no path indicated)
    """

    # open the cas file
    try:
        with open(os.path.join(path_gen, file_gen), 'rt') as f:
            data_gen = f.read()
    except IOError:
        print("Error: the file " + file_gen + " does not exist.\n")
        return
    # find .geo name
    exp_geo = "FICHIER DE GEOMETRIE = '"
    ind = data_gen.find(exp_geo)
    if ind == -1:
        print('Error: The name of the .geo file was not found in the cas file.\n')
        return
    data_name = data_gen[ind:]
    ind_end = data_name.find('\n') # it finds the first occurence
    name_geo = data_name[len(exp_geo):ind_end-1]
    return name_geo


def open_geo_mascaret(file_geo, path_geo):
    """
    This function load the mascaret geo file. Generally, the profile are not geo-referenced when using this function.

    :param file_geo: the name of the geo file (string)
    :param path_geo: the path to the geo file (string)
    :return: the profile data (x,y), profile name (list of string),
             brief name (list of string), the number of profile in each reach and distance along the river/abcisse (list)
    """
    failload = [[-99]], ['-99'], ['-99'], [-99], [-99], [-99]
    send_warn = True

    # open file
    blob, ext = os.path.splitext(file_geo)
    if ext != '.geo':
        print('Warning: The mascaret file should be of .geo type. \n')
    filename = os.path.join(path_geo, file_geo)
    if not os.path.isfile(filename):
        print('Error: The .geo file is not found.\n')
        return failload
    try:
        with open(filename, 'rt') as f:
            data = f.read()
    except IOError:
        print('Error: The .geo file can not be open.\n')
        return failload

    # separe profile
    data = np.array(data.split('PROFIL '))
    data = list(filter(bool, data))  # erase empty lines
    if len(data) == 0:
        print('Error: No profile could be extracted from the .geo file.\n')
        return failload

    # get data by profile
    name_pro = []
    abscisse = []
    coord_pro = []
    bt = []
    name_reach = ['no_reach']
    nb_r = 0
    nb_pro_reach = []
    c = 0
    for p in range(0, len(data)):
        data_pro_all = data[p]
        data_pro = data_pro_all.split('\n')
        if len(data_pro) < 2:
            print('Error: the profile number ' + str(p) + ' was not in the right format.\n')
            return failload
        profile_info = data_pro[0].split()
        # name of reaches
        if name_reach[nb_r] != profile_info[0]:
            name_reach.append(profile_info[0])
            nb_pro_reach.append(p)
            nb_r += 1
        # name of profile
        name_pro.append(profile_info[1])
        # central coordinates (distance along the river)
        try:
            abscisse.append(float(profile_info[2]))
        except ValueError:
            print('Warning: the position of the profile could not be extracted from the .geo file.\n')

        # (x,y) data
        # find the type of (y,h) coordinate
        len_data_xh = len(data_pro[1].split())
        data_xh = data_pro_all.split()
        if len_data_xh < 2 or len_data_xh > 4:
            print('Error: the profile number ' + str(p) + ' was not in the right format. X or Y data were not found. \n')
            return failload
        else:
            xstr = data_xh[3::len_data_xh]
            ystr = data_xh[4::len_data_xh]
            try:
                x_pro = list(map(float, xstr))
            except ValueError:
                print('Error: Some x data in the .geo file were not float. \n')
                return failload
            try:
                h_pro = list(map(float, ystr))
            except ValueError:
                print('Error: Some y data in the .geo file were not float. \n')
                return failload
            # remove cases where the x is the same but the h is different, not good for 2D grid
            [x_pro, send_warn] = correct_duplicate(x_pro, send_warn)

            coord_pro.append(np.array([x_pro, h_pro]))

            # find if you have a bathymetry/topography difference
            bt_maybe_info = data_xh[len_data_xh-1::len_data_xh]
            if bt_maybe_info[1] == 'B' or bt_maybe_info[1] == 'T':
                bt.append(bt_maybe_info[1:])
                c += 1

    # check if all profiles have bathymetry/topography info
    if c != 0 and c != len(data):
        print('Warning: Only part of the profiles are separated between minor and major river beds.'
              ' Will introduce error if the data is not georeferenced. \n')

    # correct name_reach
    name_reach.pop(0)  # delete the first element of name_reach ('no_reach')
    nb_pro_reach.append(len(data))
    if not name_reach:
        print('Error: No name of reach could be extracted from the .geo file. \n')
        return failload

    return coord_pro, name_pro, name_reach, nb_pro_reach, abscisse, bt


def correct_duplicate(seq, send_warn, idfun=None):
    """
    It is possible to have a vertical line on a profile (different h, identical x). This is not possible for HABBY and
    the 2D grid. So this function correct duplicates along the profile.

    A similiar function exists in rubar, for the case where input is (x,y) coordinates and not distance along the profile.
    This function is inspired by https://www.peterbe.com/plog/uniqifiers-benchmark

    It should be tested more as manage_grid sometime still send warning about duplicate data in profile.

    :param seq: the list to be corrected (list)
    :param send_warn: a bool to avoid printing certains warning too many time
    :param idfun: support an optional transform function (not used)

    :return: the profile data without duplicate and the bollean which manages the warning.
    """

    # order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    c = 1
    le = len(seq)
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            if item > 0:
                result.append(item + 0.01 * c / le)  # moving the duplicate a bit further to correct for it
            elif item < 0:
                result.append(item - 0.01 * c / le)
            else:
                result.append(0.01 * c / le)
            if send_warn:
                 print('Warning: Vertical profile. One or more profiles were modified. \n')
                 send_warn = False
        else:
            seen[marker] = 1
            result.append(item)
        c+=1
    return result, send_warn


def river_coord_non_georef_from_xcas(file_gen, path_gen, abcisse, nb_pro_reach):
    """
    Get the coordinates of the river based on the xcas xml file. If there are only one river, this is an easy task as
    the river is straight. If there are more than one reach, the junctions and the angles between the reach sould be
    managed using the define_stream_network function and the information in the .xcas file.

    :param file_gen: the .xcas file with the information concerning the reach (string)
    :param path_gen: the path to the xcas file (string)
    :param abcisse: the distance along the river
    :param nb_pro_reach: the number of profile by reach
    :return: coord_r the coordinate of the river
    """
    failload = [-99], [-99]
    print("Warning: Data is not georeferenced. HYP: straight reaches.\n")

    # load .xcas file
    root = Hec_ras06.load_xml(file_gen, path_gen)
    if root == [-99]:  # if error arised
        print("Error: the .xcas file could not be read.\n")
        return failload

    # load the number of branch
    try:
        nb_reach_xml = root.findall(".//parametresGeometrieReseau/listeBranches/nb")
    except AttributeError:
        print("Error: The number of reach cannot be read from the .xcas file.\n")
        return failload
    if not nb_reach_xml:
        print("Error: The number of reach cannot be read from the .xcas file.\n")
        return failload
    try:
        nb_reach = int(nb_reach_xml[0].text)
    except ValueError:
        print("Error: The number of reach cannot be read from the .xcas file.\n")
        return failload
    if len(nb_pro_reach) != nb_reach + 1:
        print("Error: The number of reach in the .geo and .xcas file is not coherent .\n")
        return failload

    # if we only have on reach, easy case
    if nb_reach == 1:
        coord_r = [[]]
        coord_r[0] = np.array([abcisse, np.zeros((len(abcisse),)), ]).T
        nr = [[-1, 0]]  # HYP: straight reach

    else:
        # load data on the stream network

        try:
            start_node_xml = root.findall(".//parametresGeometrieReseau/listeBranches/numExtremDebut")
            end_node_xml = root.findall(".//parametresGeometrieReseau/listeBranches/numExtremFin")
            node_number_xml = root.findall(".//listeNoeuds/noeuds/noeud/num")
            angles_xml = root.findall(".//structureParametresConfluent/angles")
        except AttributeError:
            print("Error: The node info cannot be read from the .xcas file (1).\n")
            return failload
        if not start_node_xml or not end_node_xml or not angles_xml or not node_number_xml:
            print("Error: The node info cannot be read from the .xcas file (2) .\n")
            return failload
        start_node_xml = start_node_xml[0].text.split()
        end_node_xml = end_node_xml[0].text.split()
        angles_xml = [angles_xml[i].text.split() for i in range(0, len(angles_xml))]
        node_number_xml = [node_number_xml[i].text.split() for i in range(0, len(node_number_xml))]
        try:
            start_node = list(map(float, start_node_xml))  # cannot use int because 0.0 is not ok
            end_node = list(map(float, end_node_xml))
            angles = [list(map(float, angles_xml[i])) for i in range(0, len(angles_xml))]
            node_number = [list(map(float, node_number_xml[i])) for i in range(0, len(node_number_xml))]
        except ValueError:
            print("Error: The node info cannot be read from the .xcas file (3).\n")
            return failload

        # the actual calculation
        coord_r, nr = define_stream_network(node_number, start_node, end_node, angles, nb_pro_reach, nb_reach, abcisse)

    return coord_r, nr


def river_coord_non_georef_from_cas(file_gen, path_gen, abcisse, nb_pro_reach):
    """
    Get the coordinates of the river based on the cas text file. If there are only one river, this is an easy task as
    the river is straight. If there are more than one reach, the junctions and the angles between the reach sould be
    managed using the define_stream_network function and the information in the .cas file.

    :param file_gen: the .cas file whcih contains general info (string)
    :param path_gen: the path to this file (string)
    :param abcisse: ditance along the profiles
    :param nb_pro_reach: the number of reach by profile
    :return: the river coordinate and the unit vector indicating the river direction
    """
    failload = [-99], [-99]

    # open the cas file
    try:
        with open(os.path.join(path_gen, file_gen), 'rt') as f:
            data_gen = f.read()
    except IOError:
        print("Error: the file " + file_gen + " does not exist.\n")
        return failload

    # find the number of stream
    exp_nbreach = "NOMBRE DE BRANCHES = "
    ind = data_gen.find(exp_nbreach)
    if ind == -1:
        print('Error: The number of reach was not found in the cas file. (1)\n')
        return failload
    data_name = data_gen[ind:]
    ind_end = data_name.find('\n')  # it finds the first occurence
    nb_reach = data_name[len(exp_nbreach):ind_end]
    try:
        nb_reach = int(nb_reach)
    except ValueError:
        print('Error: The number of reach could not be extracted from the cas file. (2)\n')
        return failload
    if len(nb_pro_reach) != nb_reach + 1:
        print("Error: The number of reach in the .geo and .xcas file is not coherent .\n")
        return failload

    if nb_reach == 1:
        coord_r = [[]]
        coord_r[0] = np.array([abcisse, np.zeros((len(abcisse),)), ]).T
        nr = [[-1, 0]]  # HYP: straight reach

    else:
        # get the data reated to the nodes
        # start node
        exp_reg1 = "\nNUM DE L'EXTREMITE DE DEBUT\s*=\s*\n(.+)\n"
        start_node_str = re.findall(exp_reg1, data_gen)
        if not start_node_str:
            print('Error: The index of reaches start cannot be read from the .cas file. \n')
            return failload
        start_node_str = start_node_str[0].split(';')
        try:
            start_node = list(map(float, start_node_str))
        except ValueError:
            print("Error: The index of the reaches start cannot be converted to float. \n")
            return failload
        # end node
        exp_reg1 = "\nNUM DE L'EXTREMITE DE FIN\s*=\s*\n(.+)\n"
        end_node_str = re.findall(exp_reg1, data_gen)
        if not end_node_str:
            print('Error: The index of reaches end cannot be read from the .cas file. \n')
            return failload
        end_node_str = end_node_str[0].split(';')
        try:
            end_node = list(map(float, end_node_str))
        except ValueError:
            print("Error: The index of the reaches end cannot be converted to float. \n")
            return failload
        # node number
        exp_reg1 = '\nNOEUD\s*\d+\s*=\s*\n(.+)\n'
        node_number_str = re.findall(exp_reg1, data_gen)
        if not node_number_str:
            print('Error: the node info cannot be read from the .cas file. \n')
            return failload
        node_number = []
        for n in range(0, len(node_number_str)):
            node_n = node_number_str[n]
            node_n = node_n.split(';')
            try:
                node_n = list(map(float, node_n))
            except ValueError:
                print("Error: The node info cannot be extracted from the .cas file.\n")
                return failload
            node_number.append(node_n)
        # angles
        exp_reg1 = "\nANGLE DE L'AFFLUENT DU CONFLUENT\s*\d+\s*=\s*\n(.+)\n"
        angle_str = re.findall(exp_reg1, data_gen)
        if not angle_str:
            print('Error: the angles info cannot be read from the .cas file.\n')
            return failload
        angles = []
        for n in range(0, len(angle_str)):
            node_n = angle_str[n]
            node_n = node_n.split(';')
            try:
                node_n = list(map(float, node_n))
            except ValueError:
                print("Error: The angles info cannot be extracted from the .cas file. \n")
                return failload
            angles.append(node_n)

        # reconstruct the stream network
        [coord_r, nr] = define_stream_network(node_number, start_node, end_node, angles, nb_pro_reach, nb_reach, abcisse)

    return coord_r, nr


def define_stream_network(node_number, start_node, end_node, angles, nb_pro_reach, nb_reach, abcisse):
    """
    This function extracts the stream network from the node and angle data. This is used if we have more than one
    reach to define the geometry of the junction.

    :param node_number: the start/end number of the reaches for each nodes (list of list)
    :param start_node: the numbers indicating the start of each reach (list)
    :param end_node: the numbers indicating the end of each reach
    :param angles: for each node the angle between the reach
    :param nb_pro_reach: the number of profile by reach
    :param nb_reach: the number of reach
    :param abcisse: the distance along the river of each reach
    :return: the river coordinates and the unit vector indicating the river direction

    """
    failload = [-99], [-99]

    # initialization
    abcisse_r = abcisse[:nb_pro_reach[1]]  # first number is 0
    coord_r = [[]] * nb_reach
    n = [[]] * len(node_number)  # the unit vector defining the entering unit vector
    nr = [[]] * nb_reach  # the unit vector defining the river direction for each reach
    coord_n = [[]] * nb_reach  # the coordinate of each nodes
    coord_n[0] = [abcisse_r[-1], 0]

    # case without any angles defined (angle = [0.0 0.0 0,0])
    angle_chosen = [0., 90., 180., 225., 60., 75., 30, 80, 100, 55]
    for a in range(0, len(angles)):
        angle_a = angles[a]
        if len(angle_chosen) < len(angle_a):
            print('Error: too many reach for undefined angles. The file .xcas needs to be modfied.\n')
            return failload
        if all(x == 0.0 for x in angle_a):
            angles[a] = angle_chosen[:len(angle_a)]

    # coordinate of the first reach
    dist_r = - np.abs(np.array(abcisse_r[1:]) - abcisse_r[0])
    ne = find_node(node_number, end_node[0])
    pos_angle = node_number[ne].index(end_node[0])
    alpha = (angles[ne][pos_angle]) * (np.pi / 180.)
    n_new = [np.cos(alpha), np.sin(alpha)]  # we start from the end of the stream here
    coord_r_new = np.zeros((len(abcisse_r), 2))
    coord_r_new[0, :] = coord_n[0]  # the first point is the last point of the last reach
    coord_r_new[1:, 0] = n_new[0] * dist_r + coord_n[0][0]
    coord_r_new[1:, 1] = n_new[1] * dist_r + coord_n[0][1]
    coord_r[0] = coord_r_new
    nr[0] = n_new
    n[0] = n_new

    # get the coordinates of each reaches
    nb_reach_calc = 1
    catch_err = 0
    r_now = 1
    while nb_reach_calc < nb_reach:
        # avoid unknowns problems
        catch_err += 1
        if catch_err > 5000:
            print('Error: The stream network is not well defined or could not be reconstructed.\n')
            return failload
        # if coord_r of the reach already calculated, do nothing
        if len(coord_r[r_now]) == 0:
            # get distance between each river point
            abcisse_r = abcisse[nb_pro_reach[r_now]: nb_pro_reach[r_now + 1]]
            dist_r = np.abs(np.array(abcisse_r[1:]) - abcisse_r[0])
            # look at which node the stream starts and ends
            stream_start = start_node[r_now]
            stream_end = end_node[r_now]
            no = find_node(node_number, stream_start)
            ne = find_node(node_number, stream_end)
            pos_angle = node_number[no].index(stream_start)
            # if position of the starting node is known, calculate the reach, otherwise do nothing
            if n[no][0]:
                # calculate coord_r
                nx = n[no][0]
                ny = n[no][1]
                # angles[0][0] as the first stream gives the direction of the coordinates system
                alpha = (180 + angles[0][0] - angles[no][pos_angle]) * (np.pi / 180.)
                n_new = [np.cos(alpha) * nx + np.sin(alpha) * ny, -np.sin(alpha) * nx + np.cos(alpha) * ny]
                coord_r_new = np.zeros((len(abcisse_r), 2))
                coord_r_new[0, :] = coord_n[no]  # the first point is the last point of the last reach
                coord_r_new[1:, 0] = n_new[0] * dist_r + coord_n[no][0]
                coord_r_new[1:, 1] = n_new[1] * dist_r + coord_n[no][1]
                coord_r[r_now] = coord_r_new
                nr[r_now] = n_new

                # if not all stream ends there, keep the coordinates of the nodes
                if ne != [-99]:
                    coord_n[ne] = coord_r_new[-1, :]
                    n[ne] = n_new
                # we did this stream
                nb_reach_calc += 1

        # go to the next reach
        r_now += 1
        if r_now == nb_reach:
            r_now = 1

    return coord_r, nr


def find_node(node_number, reach_to_find):
    """
    This function finds which node is a stream end or a stream start. It is associated by the function
    define_stream_network()

    :param node_number: the list of list of the reaches linked with one node
    :param reach_to_find: the number indicating the start or end of the reach
    :return: the node number, ordered as in the xcas file
    """
    no = 0
    node_found = False
    while not node_found:
        if no == len(node_number):  # ending is not found, reach is not followed by another reach
            return [-99]
        if reach_to_find in node_number[no]:
            node_found = True
        else:
            no += 1
    return no


def profil_coord_non_georef(coord_pro, coord_r, nr, nb_pro_reach, bt=None):
    """
    This function gets the coordinates (x,y) of the profile as masacret outputs are not georeferenced.

    Hypothesis: The river and the profile are straight. The profile is perpendicular to the river.
    The river pass at the minimum elevation of the river bed. If there is a distinction between the main bed the
    secondary bed is given, we take the minimum elevation of the main bed

    The origin of the coordinate system is the start of the river.

    :param coord_pro: the coordinate of the profile. This variable is not in the general coordinate system,
            just distance along the profile and bed elevation (p, dist, h)
    :param coord_r: the river coordinates
    :param n: the vector indicating the river direction
    :param nb_pro_reach: the number of profile by reach (additive)
    :param bt: optional, it indicates which points in the profiles are in the minor/major bed
    :return: the velocity and height data, the timestep
    """
    #print("Warning: Data is not georeferenced. HYP: profiles perpendicular to the river \n")
    coord = []
    for r in range(0, len(coord_r)):
        coord_pro_r = coord_pro[nb_pro_reach[r]: nb_pro_reach[r+1]]
        bt_r = bt[nb_pro_reach[r]: nb_pro_reach[r+1]]
        for p in range(0, len(coord_pro_r)):
            coord_pro_p = coord_pro_r[p]
            xpro = coord_pro_p[0]
            hpro = coord_pro_p[1]
            # find where is the river positionned on the profile
            # HYP: it is to the minimum of altitude, either of the whole profile or of the minor bed if info available
            if not bt:
                hriv = np.min(hpro)
                a = int(len(xpro[hpro == hriv]) / 2)
                xriv = xpro[hpro == hriv][a]  # y-coord of the river
            else:
                btp = np.array(bt_r[p])
                hriv = np.min(hpro[btp == 'B'])
                a = int(len(xpro[hpro == hriv])/2)  # if two altitude idem, take the middle one
                xriv = xpro[hpro == hriv][a]
            dist_from_river = xpro - xriv
            # the profile start from the river and is perpendicular to it (-y,x) for the vector n
            xcoord = coord_r[r][p][0] + dist_from_river * (-1) * nr[r][1]
            ycoord = coord_r[r][p][1] + dist_from_river * nr[r][0]
            coord.append([xcoord, ycoord])

    return coord


def open_res_file(file_res, path_res):
    """
    The function to load the output from mascaret (.opt file). The format is Optyca.

    :param file_res: the name of the .opt file (string)
    :param path_res: the path to this file (string)
    :return:
    """
    failload = [-99], [-99]

    # open file
    blob, ext = os.path.splitext(file_res)
    if ext != '.opt':
        print('Warning: The mascaret file should be of .opt type. \n')
    filename = os.path.join(path_res, file_res)
    if not os.path.isfile(filename):
        print('Error: The output file is not found (mascaret).\n')
        return failload
    try:
        with open(filename, 'rt') as f:
            data = f.read()
    except IOError:
        print('Error: The output file can not be open (mascaret).\n')
        return failload

    # get variable names
    exp_reg1 = "variables](.+)[resultats]"
    data_name = re.findall(exp_reg1, data, re.DOTALL)
    if not data_name:
        print('Error: no variable name found in the output file (mascaret).\n')
        return failload
    data_name = data_name[0].split('\n')
    data_name = list(filter(bool, data_name))  # erase empty lines
    ind_h = -99
    ind_v = -99
    ind_z = -99
    nb_var = len(data_name)-1  # get rid of the lign "resultat"
    for i in range(0, nb_var):
        this_var = data_name[i].split(';')
        if this_var[1] == "\"Y\"":
            ind_h = i
        if this_var[1] == "\"VMIN\"":
            ind_v = i
        if this_var[1] == "\"ZREF\"":
            ind_z = i
    if ind_h == -99 or ind_v == -99 or ind_z == -99:
        print('Error: height, altitude or velocity data is not present in the output file.\n')
        return failload

    # get results
    exp_reg2 = 'resultats](.+)'
    data_var = re.findall(exp_reg2, data, re.DOTALL)
    if not data_var:
        print('Error: no data found in the output file (mascaret).\n')
        return failload
    # height and velocity data
    data_var = data_var[0].split('\n')
    data_var = list(filter(bool, data_var))  # erase empty lines
    t_data = np.zeros((len(data_var), ))
    xhzv_data = np.zeros((len(data_var), 4))
    timestep = []
    for i in range(0, len(data_var)):
        data_i = data_var[i].split(";")
        try:
            t_data_i = data_i[0]
            x_data_i = data_i[3]  # check if x is always on the 3rd column
            h_data_i = data_i[-(nb_var - ind_h)]
            v_data_i = data_i[-(nb_var - ind_v)]
            z_data_i = data_i[-(nb_var - ind_z)]
        except IndexError:
            print('Error: Missing columns in the outputs file. \n')
            return failload
        try:
            t_data[i] = float(t_data_i)
            xhzv_data[i, :] = [float(x_data_i), float(h_data_i), float(z_data_i), float(v_data_i)]
        except ValueError:
            print('Error: Output data could not be converted to float (mascaret .opt file) \n')
            return failload
        if i == 0:
            timestep.append(t_data[0])
        if t_data[i] != timestep[-1]:
            timestep.append(t_data[i])

    # update by time step
    xhzv_data_all = []
    for t in range(0, len(timestep)):
        xhzv_data_all.append(xhzv_data[t_data == timestep[t], :])

    return xhzv_data_all, timestep


def is_this_res_on_the_profile(abscisse, xhzv_data_all):
    """
    The output of mascaret can be given at points of the river where there is no profile.
    The function here says which results are on the profiles. All profiles are linked with an output, but some output
    are not linked with a profile.

    :param abscisse: the distance between each profile (list of float)
    :param xhzv_data_all: the outputs from mascaret by time step
    :return: a list of bool of the length of xhzv_data, True on profile, False not on profile

    **Technical comment**

    In the mascaret outputs, some rounding are suprising. For example, 0.49 can be transformed to 0.50 in an otehr file
    (not 0.5). To avoid this type of problem, we says that outputs with a distance smaller than 3cm of the profile are
    on the profile. If there are more than one output by profile, we takes the output which is the closest to the
    profile.
    """

    xhzv_data = xhzv_data_all[0]
    on_profile = [False] * len(xhzv_data)

    for p in range(0, len(abscisse)):
        # because 0.99 = 1 and 0.49 = 0.50 even if all number are given with 2 digits
        min_here = np.min(abs(xhzv_data[:, 0] - abscisse[p]))
        if min_here < 0.03:
            inds = np.where(abs(abscisse[p] - xhzv_data[:, 0]) < 0.03)   # more than one value so no argmin
            inds = inds[0]
            for j in range(0, len(inds)):
                on_profile[inds[j]] = True
        else:
            print('Error: a profile could not be found in the result files. \n')
            return [-99]
    on_profile = np.array(on_profile)

    return on_profile


def open_rub_file(file_res, path_res):
    """
    The function to open the binary output file from mascaret (.rub format).

    :param file_res: the name of the rub binary file (string)
    :param path_res: the path to this file (string)
    :return: xhzv_data, timestep

    **Technical comment**

    The binary output file was done using a program written in FORTRAN. So there are often suprising
    octet which are added to the binary file. Be careful before changing anything.
    """

    failload = [-99], [-99]
    xhzv_data = []
    timestep = []

    # open a binary file
    blob, ext = os.path.splitext(file_res)
    if ext != '.rub':
        print('Warning: The mascaret file should be of .rub type. \n')
    filename = os.path.join(path_res, file_res)
    if not os.path.isfile(filename):
        print('Error: The binary output file is not found (mascaret).\n')
        return failload
    try:
        with open(filename, 'rb') as f:
            in_fp = f.read()
    except IOError:
        print('Error: The binary output file can not be open (mascaret).\n')
        return failload

    # get the header (can be useful)
    c = 0
    for i in range(0, 3):
        c += 4        # fortran have addition octet giving the size
        try:
            title = unpack("72s", in_fp[c:c+72])[0]
        except errstruct:
            print('Error: header could not be extracted of the .rub file. \n')
            return failload
        c += 72
        c += 4
        title = title.decode()

    # go to the end of the title/header part of the file
    still_len = True
    try:
        check_end = unpack("3s", in_fp[:3])[0]
        check_end = check_end.decode()
    except errstruct:
        print('Error: Information from the .rub file could not be extracted.\n')
        return failload
    c += 4
    while check_end != 'FIN' and still_len:
        try:
            check_end = unpack("3s", in_fp[c:c + 3])[0]
            check_end = check_end.decode()
        except errstruct:
            print('Error: Information from the .rub file could not be extracted.\n')
            return failload
        c += 3
        if c >= len(in_fp) - 1:
            still_len = False
    if not still_len:
        print('Error: The format of the input file is not recognized. '
              'The end of the file was reached before the end of the header. \n')
        return failload
    c += 1  # the last bytes after "FIN"
    c += 8  # two free bytes

    # get number of reach
    try:
        nb_reach = unpack("1i", in_fp[c:c + 4])[0]
    except errstruct:
        print('Error: the number of reach could not be extracted from the .rub file. \n')
        return failload
    if nb_reach > 500:
        print('Warning: The number of reach looks unlikely. Number of reach: ' + str(nb_reach) + '.\n' )
    c += 8 + nb_reach * 4 + 8 + nb_reach*4 + 8   # 8 because of padding related to FORTRAN

    # get variable name which do not have a time dependance
    var_name = []
    sill_len = True
    try:
        check_end = unpack("3s", in_fp[:3])[0]
        check_end = check_end.decode()
    except errstruct:
        print('Error: Information from the .rub file could not be extracted.\n')
        return failload
    c += 8
    while check_end != 'FIN ' and still_len:
        try:
            check_end = unpack("4s", in_fp[c:c + 4])[0]
            check_end = check_end.decode()
        except errstruct:
            print('Error: Information from the .rub file could not be extracted.\n')
            return failload
        if check_end != 'FIN ' and 'x00' not in check_end:
            var_name.append(check_end)
        c += 4+8
        if c >= len(in_fp) - 1:
            still_len = False
    if not still_len:
        print('Error: The format fo the input file is not recognized. '
              'The end of the file was reached before the end of the header. \n')
        return failload
    nb_varnt = len(var_name)
    # time independant variable: data
    try:
        len_var = unpack("1i", in_fp[c:c + 4])[0]
    except errstruct:
        print('Error: length of the variable could not be extracted. \n')
        return failload
    c += 12
    x = []
    zref = []
    try:
        for v in range(0, nb_varnt):
            c += 4
            if var_name[v] == 'X   ':
                for i in range(0, len_var):
                    xi = unpack('1f', in_fp[c:c + 4])[0]
                    c += 4
                    x.append(xi)
                c += 4
            elif var_name[v] == 'ZREF':
                for i in range(0, len_var):
                    zrefi = unpack('1f', in_fp[c:c + 4])[0]
                    c += 4
                    zref.append(zrefi)
                c += 4
            else:
                c += 4*len_var +4
    except errstruct:
        print('Error: Variable X and ZREF could not be extracted')
    c += 4

    # block with the time dependant variable
    # get variable name with a time dependance
    var_namet = []
    sill_len = True
    check_end = unpack("3s", in_fp[:3])[0]
    check_end = check_end.decode()
    while check_end != 'FIN ' and still_len:
        check_end = unpack("4s", in_fp[c:c + 4])[0]
        check_end = check_end.decode()
        if check_end != 'FIN ' and 'x00' not in check_end:
            var_namet.append(check_end)
            c += 4+8
        if c >= len(in_fp) - 1:
            still_len = False
    if not still_len:
        print('Error: The format of the input file is not recognized. '
              'The end of the file was reached before the end of the header. \n')
        return failload
    nb_vart = len(var_namet)

    # time independant variable: data
    # get the number of time step
    c += 12
    try:
        nb_step = unpack("1i", in_fp[c:c + 4])[0]
    except errstruct:
        print('Error: the number of time step could not be extracted from the .rub file. \n')
        return failload
    if nb_step > 1000:
        print('Warning: More than 1000 time steps found. \n')
    c +=4
    nb_step = unpack("1i", in_fp[c:c + 4])[0]
    c += 12

    v = []
    z = []
    for t in range(0, nb_step):
        # get this time step
        try:
                t = unpack('1f', in_fp[c:c + 4])[0]
                timestep.append(t)
        except errstruct:
            print('Error: the time step could not be exteracted from the .rub file. \n')
        c += 8*2
        # get the length of the variable
        try:
            len_var = unpack("1i", in_fp[c:c + 4])[0]
        except errstruct:
            print('Error: length of the variable could not be extracted. \n')
            return failload
        c += 12
        # get the data for V and Z
        zt = []
        vt = []
        try:
            for var in range(0, nb_vart):
                c += 4
                if var_namet[var] == 'Z   ':
                    for i in range(0, len_var):
                        zi = unpack('1f', in_fp[c:c + 4])[0]
                        c += 4
                        zt.append(zi)
                    c += 4
                elif var_namet[var] == 'VMIN':
                    for i in range(0, len_var):
                        vi = unpack('1f', in_fp[c:c + 4])[0]
                        c += 4
                        vt.append(vi)
                    c += 4
                else:
                    c += 4 * len_var + 4
        except errstruct:
            print('Error: Variable V and Z could not be extracted')
        z.append(zt)
        v.append(vt)

    # create xhzv_data
    for t in range(0, nb_step):
        xhzv_data_t = np.array([x, np.array(z[t])- np.array(zref), np.array(zref), np.array(v[t])])
        xhzv_data.append(xhzv_data_t.T)

    return xhzv_data, timestep


def figure_mascaret(coord_pro, coord_r, xhzv_data, on_profile, nb_pro_reach, fig_opt, name_pro, name_reach, path_im, pro,
                    plot_timestep=[-1], reach_plot=[0]):
    """
    The function to plot the figures related to mascaret.

    :param coord_pro: the cordinates (x,y,h, dist along the river) of the profiles
    :param coord_r: the coordinate (x,y) of the river
    :param name_pro: the name of the profile
    :param name_reach: the name of the reach
    :param on_profile: which result are on the profile. Some output are not the profiles.
    :param nb_pro_reach: the number of profile by reach (careful this is the number of profile, not the number of output)
    :param fig_opt: the figure option
    :param xhzv_data: the height and velcoity (x,h,v) list by time step
    :param pro profile: which profile to be plotted (list of int)
    :param plot_timestep: which timestep to be plotted
    :param reach_plot: the reach to be plotted for the river view
    :param path_im: the path where to save the figure
    """
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42

    if not coord_pro:
        print('Error: No data available to plot.\n')
        return

    for t in plot_timestep:

        x_t_all = xhzv_data[t][:, 0]
        h_t_all = xhzv_data[t][:, 1]
        z_t_all = xhzv_data[t][:, 2]
        v_t_all = xhzv_data[t][:, 3]

        h_t_all_p = h_t_all[on_profile]
        z_t_all_p = z_t_all[on_profile]
        x_t_all_p = x_t_all[on_profile]
        v_t_all_p = v_t_all[on_profile]

        # "river" view
        for r in reach_plot:
            try:
                x_t = x_t_all_p[nb_pro_reach[r]: nb_pro_reach[r + 1]]
                z_t = z_t_all_p[nb_pro_reach[r]: nb_pro_reach[r + 1]]
                h_t = h_t_all_p[nb_pro_reach[r]: nb_pro_reach[r + 1]]
                v_t = v_t_all_p[nb_pro_reach[r]: nb_pro_reach[r + 1]]
            except IndexError:
                print('Error: The selected reach does not exist. It cannot be plotted. \n')
                return
            plt.figure()
            if fig_opt['language'] == 0:
                plt.suptitle("Mascaret - Reach " + name_reach[r] + " - Timestep " + str(t))
            elif fig_opt['language'] == 1:
                plt.suptitle("Mascaret - Troncon " + name_reach[r] + " - Pas de Temps " + str(t))
            ax1 = plt.subplot(211)
            plt.plot(x_t, h_t + z_t, 'b')
            plt.plot(x_t, z_t, 'k')
            plt.plot(x_t, z_t, 'xk', markersize=4)
            if fig_opt['language'] == 0:
                plt.xlabel('Distance along the river [m]')
                plt.ylabel('Height [m]')
                plt.legend(('water height', 'river slope', 'profile position'))
            elif fig_opt['language'] == 1:
                plt.xlabel('Distance le long de la rivière [m]')
                plt.ylabel('Hauteur [m]')
                plt.legend(("hauteur d'eau", 'pente de la rivière', 'position du profil'))
            ax1 = plt.subplot(212)
            plt.plot(x_t, v_t, 'r')
            if fig_opt['language'] == 0:
                plt.xlabel('Distance along the river [m]')
                plt.ylabel('Velocity [m/sec]')
            elif fig_opt['language'] ==1:
                plt.xlabel('Distance le long de la rivière [m]')
                plt.ylabel('Vitesse [m/sec]')
            if format == 1 or format == 0:
                plt.savefig(os.path.join(path_im, "mascaret_riv_" + name_reach[r] + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                                         + ".png"), dpi = fig_opt['resolution'])
            if format == 0 or format ==3:
                plt.savefig(os.path.join(path_im, "masacret_riv_" +
                                         name_reach[r] + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                                     + ".pdf"),dpi = fig_opt['resolution'])
            if format == 3:
                plt.savefig(
                    os.path.join(path_im, "masacret_riv_" + name_reach[r] + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                                 + ".jpg"), dpi=fig_opt['resolution'])

    # (x,y) coordinates view
    fig = plt.figure()
    for r in range(0, len(coord_r)):
        coord_r_reach = np.array(coord_r[r])
        plt.plot(coord_r_reach[:, 0], coord_r_reach[:, 1], label=name_reach[r])
    for p in range(0, len(coord_pro)):
        coord_p = coord_pro[p]
        plt.plot(coord_p[0], coord_p[1], 'k', linewidth=0.5)
        #plt.plot(coord_p[0], coord_p[1], 'k', markersize=1.5, label=txt_h)
        #if p % 30 == 0:
           #plt.text(coord_p[0][-1] * 1.1, coord_p[1][-1], name_pro[p])
        txt_pro = '_nolegend_'
        txt_h = "_nolegend_"
    if fig_opt['language'] == 0:
        plt.title('Profile (x,y)')
    elif fig_opt['language'] == 1:
        plt.title('Profil (x,y)')
    plt.xlabel('x coord. [m]')
    plt.ylabel('y coord. [m]')
    plt.axis('equal')
    plt.legend(bbox_to_anchor=(1.1, 1), prop={'size': 10})
    if format == 1 or format == 0:
        plt.savefig(os.path.join(path_im, "mascaret_xy_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                dpi=fig_opt['resolution'], transparent=True)
    if format == 0 or format == 3:
        plt.savefig(os.path.join(path_im, "masacret_xy_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                dpi=fig_opt['resolution'], transparent=True)
    if format == 2:
        plt.savefig(os.path.join(path_im, "masacret_xy_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                    dpi=fig_opt['resolution'], transparent=True)
    # profiles (h, x) with water levels
    for p in pro:
        plt.figure()
        try:
            coord_p = coord_pro[p]
        except IndexError:
            print('Error: The profile number exceed the total number of profiles. Cannot be plotted.\n')
            return
        h_here = h_t_all_p[p] + z_t_all_p[p]
        plt.fill_between(coord_p[3], coord_p[2], h_here, where=coord_p[2] < h_here,
                         facecolor='blue', alpha=0.5, interpolate=True)
        plt.plot(coord_p[3], coord_p[2], 'k')
        a = 0.95 * min(coord_p[3])
        if a == 0:
            plt.xlim(-0.05, 1.05 * max(coord_p[3]))
        else:
            plt.xlim(a, 1.05 * max(coord_p[3]))
        if fig_opt['language'] == 0:
            plt.xlabel('Distance along the profile [m]')
            plt.ylabel('Height of the river bed [m]')
            plt.title('Profile ' + name_pro[p] + ' at the time step ' + str(t))
        elif fig_opt['language'] ==1:
            plt.xlabel('Distance le long du profil [m]')
            plt.ylabel('Elevation du fond de la rivière [m]')
            plt.title('Profil ' + name_pro[p] + ' au temps t=' + str(t))
        if format == 1 or format == 0:
            plt.savefig(os.path.join(path_im, "mascaret_pro_" + str(p) + '_time' +
                        time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"), dpi=fig_opt['resolution'], transparent=True)
        if format == 0 or format == 3:
            plt.savefig(os.path.join(path_im, "masacret_pro_" + str(p) + '_time' +
                        time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"), dpi=fig_opt['resolution'], transparent=True)
        if format == 2:
            plt.savefig(os.path.join(path_im, "mascaret_pro_" + str(p) + '_time'+
                        time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"), dpi=fig_opt['resolution'], transparent=True)


def flat_coord_pro(coord_pro):
    """
    This function is not used anymroe.

    The variable coord_pro was a list of profile by reach. Finally, it was useful to have each profile one after the
    other with accounting for the reach. So we stop to use this function whose goal was to pass from one form of
    coord_pro to the other form 9with or wihtout reach information).

    :param coord_pro: the list of profile (x,y,h, dist along the river) by reach
    :return: coord_pro_f: a list of profile without the reach information. The list is flatten
    """

    coord_pro_f = []
    for r in range(0, len(coord_pro)):
        coord_pro_f.extend(coord_pro[r])
    return coord_pro_f


def main():
    """
    Used to test this module separately.
    """

    #path = r'D:\Diane_work\output_hydro\mascaret\Bort-les-Orgues'
    path = r'D:\Diane_work\output_hydro\mascaret\LecRub'
    file_geo = r'mascaret0.geo'
    #file_res = r'mascaret0_ecr.opt'
    file_res = r'mascaret0_full.rub'
    file_gen = 'mascaret0.xcas'
    #file_gen = r'failltext.xcas'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'


    [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach] =\
        load_mascaret(file_gen, file_geo, file_res, path, path, path)

    figure_mascaret(coord_pro, coord_r, xhzv_data, on_profile, nb_pro_reach, name_pro,
                    name_reach, path_im, [0, 1, 2], [-1], [0])


if __name__ == '__main__':
    main()