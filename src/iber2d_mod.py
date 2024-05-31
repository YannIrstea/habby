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
import sys
import os
from io import StringIO

import src.manage_grid_mod
from src import manage_grid_mod
from src.project_properties_mod import create_default_project_properties_dict
from src import hdf5_mod
from src import rubar1d2d_mod


def load_iber2d_and_modify_grid(name_hdf5, geom_iber2d_file,
                                result_iber2d_file1, result_iber2d_file2,
                                result_iber2d_file3, result_iber2d_file4,
                                path_geo, path_res, path_im, name_prj,
                                path_prj, model_type, nb_dim, path_hdf5,
                                q=[], print_cmd=False, project_properties={}):
    """
    This function loads the iber2d file, using the function below.
    Then, it changes the mesh which has triangle and
    quadrilater toward a triangle mesh and it passes the data from cell-centric
    data to node data using a linear interpolation.
    Finally it saves the data in one hdf5.

    TODO See if we could improve the interpolation or study its effect
    in more details.
    :param name_hdf5: the base name of the created hdf5 (string)
    :param geom_iber2d_file: the name of the .geo gile (string)
    :param result_iber2d_file: the name of the result file (string)
    :param path_geo: path to the geo file (string)
    :param path_res: path to the result file which contains the outputs
                    (string)
    :param path_im: the path where to save the figure (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project (string)
    :param model_type: the name of the model such as Rubar, hec-ras, etc.
                        (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which
                    to save the hdf5
    :param q: used by the second thread to get the error back to the GUI
                at the end of the thread
    :param print_cmd: If True will print the error and warning to the cmd.
                        If False, send it to the GUI.
    :param project_properties: the figure option, used here to get the minimum water
                    height to have a wet node (can be > 0)
    :return: none
    """
    # get minimum water height
    if not project_properties:
        project_properties = create_default_project_properties_dict()
    minwh = project_properties['min_height_hyd']

    # find where we should send the error (cmd or GUI)
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # create the empy output
    inter_vel_all_t = []
    inter_h_all_t = []
    ikle_all_t = []
    point_all_t = []
    point_c_all_t = []

    # load iber data
    [baryXY, timesteps, height_cell, vel_cell] = \
        read_result_iber2d(result_iber2d_file1, result_iber2d_file2,
                           result_iber2d_file3, result_iber2d_file4,
                           path_res)
    if isinstance(baryXY[0], int):
        if baryXY == [-99]:
            print("Error: the IBER2D result file could not be loaded.")
            if q:
                sys.stdout = sys.__stdout__
                q.put(mystdout)
                return
            else:
                return
    [noNodElem, listNoNodElem, nodesXYZ] = \
        read_mesh_iber2d(geom_iber2d_file, path_geo)
    if isinstance(noNodElem[0], int):
        if noNodElem == [-99]:
            print("Error: the IBER2D geometry file could not be loaded.")
            if q:
                sys.stdout = sys.__stdout__
                q.put(mystdout)
                return
            else:
                return

    # get triangular nodes from quadrilateral
    [ikle_base, coord_c, coord_p, height_cell, vel_cell] = \
        src.manage_grid_mod.get_triangular_grid(listNoNodElem, baryXY,
                                  nodesXYZ[:, :2], height_cell, vel_cell)

    # remove non connected nodes
    triangles = np.asarray(ikle_base)
    nodes = coord_p
    nbnode = nodes.shape[0]
    nbtriangle = triangles.shape[0]
    connect = np.zeros(nbnode, dtype=int)
    connect[np.ravel(triangles)] = 1
    pointer = np.zeros(nbnode, dtype=int)
    k = 0
    for i in range(nbnode):
        if connect[i]:
            pointer[i] = k
            k = k + 1
    nds = [nodes[i,] for i in range(nbnode) if connect[i]]
    coord_p = np.asarray(nds)

    tria1 = np.ravel(triangles[:, 0])
    tria2 = np.ravel(triangles[:, 1])
    tria3 = np.ravel(triangles[:, 2])
    trs1 = [pointer[tria1[i]] for i in range(nbtriangle)]
    trs2 = [pointer[tria2[i]] for i in range(nbtriangle)]
    trs3 = [pointer[tria3[i]] for i in range(nbtriangle)]
    trs = trs1 + trs2 + trs3
    trs = np.asarray(trs)
    trs = trs.reshape(3, nbtriangle)
    ikle_base = np.transpose(trs)
    ikle_base = ikle_base.tolist()

    # create grid
    # first, the grid for the whole profile (no velocity or height data)
    # because we have a "whole" grid for 1D model before the actual time step
    inter_h_all_t.append([[]])
    inter_vel_all_t.append([[]])
    point_all_t.append([coord_p])
    point_c_all_t.append([coord_c])
    ikle_all_t.append([ikle_base])

    # the grid data for each time step
    warn1 = False
    for t in range(0, len(vel_cell)):
        # get data no the node (and not on the cells) by linear interpolation
        if t == 0:
            [vel_node, height_node, vtx_all, wts_all] = \
                manage_grid_mod.pass_grid_cell_to_node_lin([coord_p],
                                                           [coord_c],
                                                           vel_cell[t],
                                                           height_cell[t], warn1)
        else:
            [vel_node, height_node, vtx_all, wts_all] = \
                manage_grid_mod.pass_grid_cell_to_node_lin([coord_p], [coord_c],
                                                           vel_cell[t],
                                                           height_cell[t], warn1,
                                                           vtx_all, wts_all)
        # cut the grid to the water limit
        [ikle, point_all, water_height, velocity] = \
            manage_grid_mod.cut_2d_grid(ikle_base, coord_p, height_node[0],
                                        vel_node[0], minwh)

        inter_h_all_t.append([water_height])
        inter_vel_all_t.append([velocity])
        point_all_t.append([point_all])
        point_c_all_t.append([[]])
        ikle_all_t.append([ikle])
        warn1 = False

    # save data
    timestep_str = list(map(str, timesteps))
    hdf5_mod.save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, nb_dim,
                                     path_hdf5, ikle_all_t, point_all_t,
                                     point_c_all_t,
                                     inter_vel_all_t, inter_h_all_t, sim_name=timestep_str, hdf5_type="hydraulic")

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
    else:
        return


def read_mesh_iber2d(geofile, pathfile):
    """
    Reads the binary file of IBER2D mesh
    :param geofile: the name of the geometry file (string)
    :param pathfile: the path of the geometry file (string)
    :return: - the number of nodes per element
                (3 or 4 --> triangle or quadrilateral)
             - the list of nodes for each element
             - x y and z-coordinates of nodes
    """
    failload = [-99], [-99], [-99]
    filename_path = os.path.join(pathfile, geofile)
    try:
        with open(filename_path, 'r') as f:
            line = ''
            while line != 'MATRIU':
                line = f.readline()
                line = line.strip()
            line = f.readline()
            line = line.strip()
            nbelem = np.fromstring(line, dtype=int, sep=' ')
            listNoNodElem = []
            noNodElem = []
            for i in range(nbelem[0]):
                line = f.readline()
                line = line.strip()
                elem = np.fromstring(line, dtype=int, sep=' ')
                if elem[0] == elem[3]:
                    noNodElem.append(3)
                    elem = elem[:-2]
                else:
                    noNodElem.append(4)
                    elem = elem[:-1]
                elem = elem - 1
                listNoNodElem.append(elem)
            f.seek(0)
            line = ''
            while line != 'VERTEXS':
                line = f.readline()
                line = line.strip()
            line = f.readline()
            line = line.strip()
            nnodes = np.fromstring(line, dtype=int, sep=' ')
            nodesXYZ = np.array([]).reshape(0, 3)  # Only XYZ for now
            for i in range(nnodes[0]):
                line = f.readline()
                line = line.strip()
                node = np.fromstring(line, dtype=float, sep=' ')
                node = node[:-1]
                nodesXYZ = np.vstack([nodesXYZ, node])
    except IOError:
        print('Error: The .geo file does not exist')
        return failload
    f.close()

    return noNodElem, listNoNodElem, nodesXYZ


def read_result_iber2d(resfile_h, resfile_u, resfile_v, resfile_xyz, pathfile):
    """
    Reads the ascii files of IBER2D results

    :param resfile: the name of the result files (string)
    :param pathfile: path of the result file (string)
    :return: - barycentric XY-coordinates of each elements
             - time values
             - water depth and velocity values for each time step and element
    """
    failload = [-99], [-99], [-99], [-99]
    # Water depths
    filename_path = os.path.join(pathfile, resfile_h)
    tval = np.array(())
    hval = np.array(())
    nsteps = 0
    try:
        with open(filename_path, 'r') as f:
            for line in f:
                line = line.strip()
                val = np.fromstring(line, sep=' ')
                if val.size == 1:
                    tval = np.hstack((tval, val))
                    nnodes = 0
                    nsteps += 1
                else:
                    nnodes += val.size
                    hval = np.hstack((hval, val))
    except IOError:
        print('Error: The .res file does not exist')
        return failload
    f.close()
    hval = hval.reshape(nsteps, nnodes)

    # Velocity x-component
    filename_path = os.path.join(pathfile, resfile_u)
    uval = np.array(())
    try:
        with open(filename_path, 'r') as f:
            for line in f:
                line = line.strip()
                val = np.fromstring(line, sep=' ')
                if val.size != 1:
                    uval = np.hstack((uval, val))
    except IOError:
        print('Error: The .res file does not exist')
        return failload
    f.close()
    # Velocity y-component
    filename_path = os.path.join(pathfile, resfile_v)
    vval = np.array(())
    try:
        with open(filename_path, 'r') as f:
            for line in f:
                line = line.strip()
                val = np.fromstring(line, sep=' ')
                if val.size != 1:
                    vval = np.hstack((vval, val))
    except IOError:
        print('Error: The .res file does not exist')
        return failload
    f.close()
    # Velocity magnitude
    vnorm = np.sqrt(uval * uval + vval * vval)
    vnorm = vnorm.reshape(nsteps, nnodes)
    # Barycentric XY-coordinates
    filename_path = os.path.join(pathfile, resfile_xyz)
    xyval = []
    try:
        with open(filename_path, 'r') as f:
            for line in f:
                line = line.strip()
                val = np.fromstring(line, dtype=float, sep=' ')
                val = val[1:3]
                xyval.append(val)
    except IOError:
        print('Error: The .res file does not exist')
        return failload
    f.close()

    return xyval, tval, hval, vnorm


if __name__ == '__main__':
    # read the mesh of iber2d
    result_iber2d_file = 'Iber2D.dat'
    mesh_iber2d = read_mesh_iber2d(result_iber2d_file)
    # read results on the water depth and velocity for all time steps
    result_iber2d_file1 = 'h.rep'
    result_iber2d_file2 = 'u.rep'
    result_iber2d_file3 = 'v.rep'
    result_iber2d_file4 = 'xyz.rep'
    result_iber2d = read_result_iber2d(result_iber2d_file1,
                                       result_iber2d_file2,
                                       result_iber2d_file3,
                                       result_iber2d_file4)
    print(result_iber2d)
