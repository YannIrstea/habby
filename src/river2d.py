import os
import re
import numpy as np
import matplotlib.pyplot as plt
from src import hec_ras2D
import time


def load_river2d_cdg(file_cdg, path):
    """
    The file to load the output data from River2D. Cerful the input data has the same ending and nearly the same format.
    Do not mix the files.
    :param file_cdg:
    :param path:
    :return:
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
                print('Error: Some values are not float. Check the node '+ str(n+1) + ' in the .cdg file.\n')
                return failload
        elif 3 + nb_par + nb_var == len(data_node_n):   # there is one coulmn which is not always there
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
    xyzhv[:, 4] = np.sqrt((qxqy[:, 0]/xyzhv[:, 3])**2 + (qxqy[:, 0]/xyzhv[:, 3])**2)

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
    coord_c_x = 1.0/3.0 * (p1[:, 0] + p2[:, 0] + p3[:, 0])
    coord_c_y = 1.0/3.0 * (p1[:, 1] + p2[:, 1] + p3[:, 1])
    coord_c = np.array([coord_c_x, coord_c_y]).T

    return xyzhv, ikle, coord_c


def get_rid_of_lines(datahere, nb_data):
    """
    There are lines which are useless. used to correct ikle and data_node
    :param datahere: the data with the empty lines
    :param nb_data: nb_node or nb_el
    :return:
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
    A function to plot the output from river 2d. Need hec-ras2d as import because it re-used most of the plot from there
    Plot only one time step because river 2d output have one file by time step
    :param xyzhv: the x,y, coordinates of the node (h,v are nodal output in river 2d), the river bed, the water height
    and the velocity (one data by column, row are node)
    :param ikle: connectivity table
    :param path_im the path where to save the figure
    :param t: the time step
    :return: grid figure, h and v
    """
    plt.rcParams['font.size'] = 10
    # grid
    [xlist, ylist] = hec_ras2D.prepare_grid(ikle, xyzhv[:, :2])
    fig = plt.figure()
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.plot(xyzhv[:, 0], xyzhv[:, 1], '.', markersize=3)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Grid ')
    plt.savefig(os.path.join(path_im, "river2D_grid_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "river2D_grid_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    plt.close()

    hec_ras2D.scatter_plot(xyzhv[:, :2], xyzhv[:, 3], 'Water Depth [m]', 'terrain', 8, 0)
    plt.savefig(
        os.path.join(path_im, "river2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(
        os.path.join(path_im, "river2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    plt.close()

    hec_ras2D.scatter_plot(xyzhv[:, :2], xyzhv[:, 4], 'Vel. [m3/sec]', 'gist_ncar', 8, 0)
    plt.savefig(os.path.join(path_im, "river2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "river2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    plt.close()
    # plt.show()


def main():
    path = r'D:\Diane_work\output_hydro\river2d\output_time'
    name = 'test83.00.cdg'

    [xyzhv, ikle, coord_c] = load_river2d_cdg(name, path)
    figure_river2d(xyzhv, ikle, '.')

if __name__ == '__main__':
    main()