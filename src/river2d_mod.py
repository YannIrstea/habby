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
import re
import numpy as np
import sys
import matplotlib.pyplot as plt
import matplotlib as mpl
from src import hec_ras2D_mod
import time
from src import manage_grid_mod
from src import hdf5_mod
from io import StringIO
from src.project_manag_mod import create_default_project_preferences_dict


def load_river2d_and_cut_grid(name_hdf5, namefiles, paths, name_prj, path_prj, model_type, nb_dim, path_hdf5, q=[],
                              print_cmd=False, project_preferences={}):
    """
    This function loads the river2d data and cut the grid to the wet area. Originally, this function was in the class
    River2D() in hydro_GUI_2. This function was added as it was practical to have a second thread to avoid freezing
    the GUI.

    :param name_hdf5: the base name of the created hdf5 (string)
    :param namefiles: the names of all the cdg file (list of string)
    :param paths: the path to the files (list of string).
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param q: used to send the error back from the second thread (can be used to send other variable too)
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param project_preferences: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    """

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_preferences_dict()
    minwh = project_preferences['min_height_hyd']

    # creation of array
    xyzhv = []
    ikle_all_t = []
    point_c_all_t = []
    point_all_t = []
    inter_h_all_t = []
    inter_vel_all_t = []

    # for all time step
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    for i in range(0, len(namefiles)):
        # load river 2d data
        [xyzhv_i, ikle_i, coord_c] = load_river2d_cdg(namefiles[i], paths[i])
        if isinstance(xyzhv_i[0], int):
            if xyzhv_i[0] == -99:
                print('Error: River2D data could not be loaded')
                if q:
                    sys.stdout = sys.__stdout__
                    q.put(mystdout)
                    return
                else:
                    return

        # cut grid to wet area
        [ikle_i, point_all, water_height, velocity] = manage_grid_mod.cut_2d_grid(ikle_i, xyzhv_i[:, :2], xyzhv_i[:, 3],
                                                                                xyzhv_i[:, 4], minwh)

        # mimic empty grid for t = 0 for 1 D model
        if i == 0:
            point_all_t.append([point_all])
            ikle_all_t.append([ikle_i])
            point_c_all_t.append([coord_c])
            inter_h_all_t.append([])
            inter_vel_all_t.append([])
        point_all_t.append([point_all])
        ikle_all_t.append([ikle_i])
        point_c_all_t.append([[]])
        inter_h_all_t.append([water_height])
        inter_vel_all_t.append([velocity])

    # save data
    namefiles2 = [x[:-4] for x in namefiles]  # no need of the .cdg to name the time step

    hdf5_mod.save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5, ikle_all_t,
                                     point_all_t, point_c_all_t,
                                     inter_vel_all_t, inter_h_all_t, sim_name=namefiles2, hdf5_type="hydraulic")
    if not print_cmd:
        sys.stdout = sys.__stdout__

    if q:
        q.put(mystdout)
        return
    else:
        return


def load_river2d_cdg(file_cdg, path):
    """
    The file to load the output data from River2D. Careful the input data of River2D has the same ending and nearly
    the same format as the output. However, it is nessary to have the output here. River2D gives one cdg. file by timestep.
    Hence, this function read only one timeste. HABBY read all time step by calling this function once for each time step.

    :param file_cdg: the name of the cdg file (string)
    :param path: the path to this file (string).
    :return: the velocity and height data, the coordinate and the connectivity table.
    """

    failload = [-99], [-99], [-99]
    # open file
    blob, ext = os.path.splitext(file_cdg)
    if ext != '.cdg':
        print('Warning: The River2D file should be of .cdg type. \n')
    filename = os.path.join(path, file_cdg)
    if not os.path.isfile(filename):
        print('Error: The .cdg file is not found.\n')
        return failload
    try:
        with open(filename, 'rt') as f:
            data = f.read()
    except IOError:
        print('Error: The .cdg file can not be open.\n')
        return failload

    # number of variable
    exp_reg1 = 'Number of Variables\s*=\s*(\d+)'
    nb_var = re.findall(exp_reg1, data)
    if not nb_var:
        print('Error: The number of variable was not found. Check .cdf file format.\n')
        return failload
    nb_var = int(nb_var[0])
    # number of parameter
    exp_reg1 = 'Number of Parameters\s*=\s*(\d+)'
    nb_par = re.findall(exp_reg1, data)
    if not nb_par:
        print('Error: The number of parameter was not found. Check .cdf file format.\n')
        return failload
    nb_par = int(nb_par[0])
    # number of nodes
    exp_reg1 = 'Number of Nodes\s*=\s*(\d+)'
    nb_node = re.findall(exp_reg1, data)
    if not nb_node:
        print('Error: The number of nodes was not found. Check .cdf file format.\n')
        return failload
    nb_node = int(nb_node[0])
    # number of elements
    exp_reg1 = 'Number of Elements\s*=\s*(\d+)'
    nb_el = re.findall(exp_reg1, data)
    if not nb_el:
        print('Error: The number of parameter was not found. Check .cdf file format.\n')
        return failload
    nb_el = int(nb_el[0])

    # get data by node
    exp_reg2 = 'Node Information(.+)Element Information'
    node_data = re.findall(exp_reg2, data, re.DOTALL)
    if not node_data:
        print('Error: The output das was not in the right format. Check the .cdg file.\n')
        return failload
    node_data = node_data[0].split('\n')
    node_data = get_rid_of_lines(node_data, nb_node)
    if node_data == -99:
        return
    # analyze and pass to float; data by node
    xyzhv = np.zeros((nb_node, 5))
    qxqy = np.zeros((nb_node, 2))
    for n in range(0, nb_node):
        data_node_n = node_data[n]
        data_node_n = data_node_n.split()

        if len(data_node_n) == 4 + nb_par + nb_var:
            try:
                xyzhv[n, 0] = float(data_node_n[2])  # x
                xyzhv[n, 1] = float(data_node_n[3])  # y
                xyzhv[n, 2] = float(data_node_n[4])  # z
                xyzhv[n, 3] = float(data_node_n[4 + nb_par])  # h
                qxqy[n, 0] = float(data_node_n[5 + nb_par])
                qxqy[n, 1] = float(data_node_n[6 + nb_par])
            except ValueError:
                print('Error: Some values are not float. Check the node ' + str(n + 1) + ' in the .cdg file.\n')
                return failload
        elif 3 + nb_par + nb_var == len(data_node_n):  # there is one coulmn which is not always there
            try:
                xyzhv[n, 0] = float(data_node_n[1])
                xyzhv[n, 1] = float(data_node_n[2])
                xyzhv[n, 2] = float(data_node_n[3])
                xyzhv[n, 3] = float(data_node_n[3 + nb_par])
                qxqy[n, 0] = float(data_node_n[4 + nb_par])
                qxqy[n, 1] = float(data_node_n[5 + nb_par])
            except ValueError:
                print('Error: Some values are not float. Check the node ' + str(n + 1) + ' in the .cdg file.\n')
                return failload
        else:
            print('Error: Some column are missing. Check the node ' + str(n + 1) + ' in the .cdg file.\n')
            return failload

    # get the velocity data
    xyzhv[:, 4] = np.sqrt((qxqy[:, 0] / xyzhv[:, 3]) ** 2 + (qxqy[:, 0] / xyzhv[:, 3]) ** 2)

    # if height negative (normal in river 2d) -> h and v = 0
    xyzhv[xyzhv[:, 3] < 0, 2:] = 0

    # mesh connectivity table
    exp_reg3 = 'Element Information(.+)Boundary Element'
    ikle_data = re.findall(exp_reg3, data, re.DOTALL)
    ikle_data = ikle_data[0].split('\n')
    if not ikle_data:
        print('Error: No connectivity table was found in the .cdg file \n.')
        return failload
    ikle_data = get_rid_of_lines(ikle_data, nb_el)
    if ikle_data == -99:
        return
    ikle = np.zeros((nb_el, 3), dtype=np.int32)  # triangular mesh only
    for e in range(0, nb_el):
        ikle_data_e = ikle_data[e]
        ikle_data_e = ikle_data_e.split()
        if len(ikle_data_e) == 9:
            try:
                ikle[e, 0] = int(ikle_data_e[3]) - 1  # n1
                ikle[e, 1] = int(ikle_data_e[4]) - 1  # n2
                ikle[e, 2] = int(ikle_data_e[5]) - 1  # n3
            except ValueError:
                print('Error: Some values are not integer. Check the element ' + str(e + 1) + ' in the .cdg file.\n')
                return failload
        else:
            print('Error: Some column are missing. Check the element ' + str(e + 1) + ' in the .cdg file.\n')
            return failload

    # center of element
    coord = xyzhv[:, :2]
    p1 = coord[ikle[:, 0], :]
    p2 = coord[ikle[:, 1], :]
    p3 = coord[ikle[:, 2], :]
    coord_c_x = 1.0 / 3.0 * (p1[:, 0] + p2[:, 0] + p3[:, 0])
    coord_c_y = 1.0 / 3.0 * (p1[:, 1] + p2[:, 1] + p3[:, 1])
    coord_c = np.array([coord_c_x, coord_c_y]).T

    return xyzhv, ikle, coord_c


def get_rid_of_lines(datahere, nb_data):
    """
    There are lines which are useless in the cdg file. This function is used to correct ikle and data_node

    :param datahere: the data with the empty lines
    :param nb_data: nb_node or nb_el
    :return: datahere wihtout the useless lines
    """
    # there are 3 useless lines are the start and one at the end. Hopefully, it is always the same number.
    for l in range(0, 3):
        datahere.pop(0)
    datahere.pop(-1)
    # also erase empty lines which arrives from nowhere.
    datahere = list(filter(bool, datahere))
    # check that we did not erase too much or too little
    if len(datahere) != nb_data:
        print('Error: The number of nodes or element is not consistent with the header in the .cdg file.')
        return -99
    return datahere


def figure_river2d(xyzhv, ikle, path_im, t=0):
    """
    A function to plot the output from river 2d. Need hec-ras2d as import because it re-used most of the plot from this
    script. It is only used to debug. It is not used directly by HABBY.

    Plot only one time step because river 2d output have one file by time step.

    :param xyzhv: the x,y, coordinates of the node (h,v are nodal output in river 2d), the river bed, the water height
           and the velocity (one data by column, row are node)
    :param ikle: connectivity table
    :param path_im: the path where to save the figure
    :param t: the time step which is being plotted
    :return:
    """
    plt.rcParams['font.size'] = 10
    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['pdf.fonttype'] = 42

    # grid
    [xlist, ylist] = hec_ras2D_mod.prepare_grid(ikle, xyzhv[:, :2])
    fig = plt.figure()
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.plot(xyzhv[:, 0], xyzhv[:, 1], '.', markersize=3)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Grid ')
    plt.savefig(os.path.join(path_im, "river2D_grid_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "river2D_grid_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    plt.close()

    hec_ras2D_mod.scatter_plot(xyzhv[:, :2], xyzhv[:, 3], 'Water Depth [m]', 'terrain', 8, 0)
    # plt.savefig(
    #  os.path.join(path_im, "river2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    # plt.savefig(
    #  os.path.join(path_im, "river2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    # plt.close()

    hec_ras2D_mod.scatter_plot(xyzhv[:, :2], xyzhv[:, 4], 'Vel. [m3/sec]', 'gist_ncar', 8, 0)
    plt.savefig(os.path.join(path_im, "river2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "river2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))


def main():
    """
    Used to test this module.
    """
    path = r'D:\Diane_work\output_hydro\river2d\output_time'
    name = 'test83.00.cdg'

    [xyzhv, ikle, coord_c] = load_river2d_cdg(name, path)
    figure_river2d(xyzhv, ikle, '.')


if __name__ == '__main__':
    main()
