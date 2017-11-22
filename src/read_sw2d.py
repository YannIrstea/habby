import numpy as np
import sys
from io import StringIO
from src import manage_grid_8
from src_GUI import output_fig_GUI
from src import load_hdf5
from src import hec_ras2D


def load_swd_and_modify_grid(geom_sw2d_file, mesh_sw2d_file,name_prj, path_prj, model_type, nb_dim,name_hdf5, path_hdf5,
                             q=[], print_cmd=False, fig_opt={}):
    """
    This function loads the sw2d file, using the function below. Then, it changes the mesh which has triangle and
    quadrilater toward a triangle mesh and it passes the data from cell-centric data to node data using a linear
    interpolation. Finally it saves the data in one hdf5.

    TODO See if we could improve the interpolatin or study its effect in more details.
    :param geom_sw2d_file: the name of the .geo gile (string)
    :param mesh_sw2d_file: the name of the result file (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project (string)
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param name_hdf5: the base name of the hdf5 to be created (string)
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param q: used by the second thread to get the error back to the GUI at the end of the thread
    :param print_cmd: If True will print the error and warning to the cmd. If False, send it to the GUI.
    :param fig_opt: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    :return: none
    """

    # get minimum water height
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    minwh = fig_opt['min_height_hyd']

    # find where we should send the error (cmd or GUI)
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # load swd data
    [baryXY, times, heigth_cell, vel_cell] = read_result_sw2d(mesh_sw2d_file)
    if isinstance(baryXY[0], int):
        if baryXY == [-99]:
            print("Error: the SW2D result file could not be loaded.")
            if q:
                sys.stdout = sys.__stdout__
                q.put(mystdout)
                return
            else:
                return
    [noNodElem, listNoNodElem, nodesXYZ] = read_mesh_sw2d(geom_sw2d_file)
    if isinstance(noNodElem[0], int):
        if noNodElem == [-99]:
            print("Error: the SW2D geometry file could not be loaded.")
            if q:
                sys.stdout = sys.__stdout__
                q.put(mystdout)
                return
            else:
                return

    # get triangular nodes from quadrilater
    [ikle_all, coord_c_all, coord_p_all, vel_t_all2, water_depth_t_all2] = hec_ras2D.get_triangular_grid_hecras(
        ikle_all, coord_c_all, coord_p_all, vel_t_all, water_depth_t_all)

    # pass the data to node and cut the wet limit of the grid
    warn1 = True
    for t in range(0, len(vel_cell)):
        # cell to node data
        # using a different call for the first and the next time step allows to win time if you know that the grid
        # is not changing in this hydraulic models
        if t == 0:
            [v_node, h_node, vtx_all, wts_all] = manage_grid_8.pass_grid_cell_to_node_lin(point_all_t[0],
                                                                                          point_c_all_t[0], vel_cell[t],
                                                                                          height_cell[t], warn1)
        else:
            [v_node, h_node, vtx_all, wts_all] = manage_grid_8.pass_grid_cell_to_node_lin(point_all_t[0],
                                                                                          point_c_all_t[0], vel_cell[t],
                                                                                          height_cell[t], warn1,
                                                                                          vtx_all, wts_all)
            # to study the difference in average, do no forget to comment sys.stdout = mystdout = StringIO()
            # other wise you get zero for all.
        warn1 = False
        ikle_f = []
        point_f = []
        v_f = []
        h_f = []

        # cut the grid the wet limit
        for f in range(0, len(ikle_all_t[0])):  # by reach (or water area)
            # cut grid to wet area
            [ikle2, point_all, water_height, velocity] = manage_grid_8.cut_2d_grid(ikle_all_t[0][f],
                                                                                   point_all_t[0][f], h_node[f],
                                                                                   v_node[f], minwh)
            ikle_f.append(ikle2)
            point_f.append(point_all)
            h_f.append(water_height)
            v_f.append(velocity)
        inter_h_all_t.append(h_f)
        inter_vel_all_t.append(v_f)
        point_all_t.append(point_f)
        # we did not need the centroid aftwerwards and saving it would required a correction in cut_2d_grid
        # TO DO: correct this in cut_2d_grid
        point_c_all_t.append([[]])
        ikle_all_t.append(ikle_f)

    # save data
    load_hdf5.save_hdf5(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5, ikle_all_t, point_all_t,
                        point_c_all_t, inter_vel_all_t, inter_h_all_t, sim_name=timesteps)

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def read_mesh_sw2d(geom_sw2d_file):
    """
    Reads the binary file of SW2D mesh
    :param geom_sw2d_file: the name of the file (string)
    :return: - the number of nodes per element (3 or 4 --> triangle or quadrilateral)
             - the list of nodes for each element
             - x y and z-coordinates of nodes
    """
    failload = [-99], [-99], [-99]

    try:
        with open(geom_sw2d_file,'rb') as f:
            # reading dimensions with Fortran labels
            data = np.fromfile(f, dtype=np.int32, count=5)
            ncel = data[1]
            nint = data[2]
            nnod = data[3]
            # reading info on cells
            noNodElem = np.zeros((ncel, 1), dtype=np.int)
            nnCel = np.zeros((ncel,1), dtype=np.int)
            data = np.fromfile(f, dtype=np.int32, count=1) #label
            for i in range(ncel):
                data = np.fromfile(f, dtype=np.int32, count=3)
                noNodElem[i] = data[0]
                nnCel[i] = data[1]
                data = np.fromfile(f, dtype=np.float, count=4)
            data = np.fromfile(f, dtype=np.int32, count=1) #end label
            # reading connectivity
            listNoNodElem = np.zeros([ncel, np.max(noNodElem)], dtype=np.int)
            for i in range(int(ncel)):
                data = np.fromfile(f, dtype=np.int32, count=1) #label
                for j in range(int(noNodElem[i])):
                    listNoNodElem[i,j] = np.fromfile(f, dtype=np.int32, count=1)
                    data = np.fromfile(f, dtype=np.float, count=2)
                data = np.fromfile(f, dtype=np.int32, count=1) #end label
                data = np.fromfile(f, dtype=np.int32, count=1) #label
                data = np.fromfile(f, dtype=np.int32, count=int(noNodElem[i])) # cint
                data = np.fromfile(f, dtype=np.int32, count=1) #end label
                data = np.fromfile(f, dtype=np.int32, count=1) #label
                data = np.fromfile(f, dtype=np.int32, count=int(nnCel[i])) # ccel
                data = np.fromfile(f, dtype=np.int32, count=1) #end label
                data = np.fromfile(f, dtype=np.int32, count=1) #label
                data = np.fromfile(f, dtype=np.int32, count=int(noNodElem[i])) # cint
                data = np.fromfile(f, dtype=np.int32, count=1) #end label
            # reading info on edges
            data = np.fromfile(f, dtype=np.int32, count=1) #label
            for i in range(nint):
                data = np.fromfile(f, dtype=np.int32, count=4)
                data = np.fromfile(f, dtype=np.float, count=7)
            data = np.fromfile(f, dtype=np.int32, count=1) #end label
            # reading the coordinates of nodes
            nodesXYZ = np.zeros((nnod, 3))
            data = np.fromfile(f, dtype=np.int32, count=1) #label
            for i in range(nnod):
                nodesXYZ[i,] = np.fromfile(f, dtype=np.float, count=3)
                data = np.fromfile(f, dtype=np.int32, count=1)
            data = np.fromfile(f, dtype=np.int32, count=1) #end label
                
    except IOError:
        print('Error: The .geo file does not exist')
        return failload
    f.close()
    return noNodElem, listNoNodElem, nodesXYZ


def read_result_sw2d(mesh_sw2d_file):
    """
    Reads the binary file of SW2D results
    
    :param mesh_sw2d_file: the name of the file (string)
    :return: - barycentric coordinates of each elements
             - time values
             - water depth and velocity values for each time step and element
    """
    failload = [-99], [-99], [-99], [-99]

    try:
        with open(mesh_sw2d_file,'rb') as f:
            # reading storage info with Fortran labels
            data = np.fromfile(f, dtype=np.int32, count=18)
            # reading dimensions with Fortran labels
            data = np.fromfile(f, dtype=np.int32, count=4)
            ncel = data[1]
            nint = data[2]
            # reading barycentric coordinates
            baryXY = np.zeros((ncel, 2))
            data = np.fromfile(f, dtype=np.int32, count=1) #label
            for i in range(ncel):
                baryXY[i,] = np.fromfile(f, dtype=np.float, count=2)
            data = np.fromfile(f, dtype=np.int32, count=1) #end label
            # reading info on edges
            data = np.fromfile(f, dtype=np.int32, count=1) #label
            for i in range(nint):
                data = np.fromfile(f, dtype=np.int32, count=2)
                data = np.fromfile(f, dtype=np.float, count=6)
            data = np.fromfile(f, dtype=np.int32, count=1) #end label
            # reading results
            times = np.array([]).reshape(0, 1)
            h = np.array([]).reshape(0, ncel)
            v = np.array([]).reshape(0, ncel)
            while True:
                data = np.fromfile(f, dtype=np.int32, count=1) #label
                if data.size < 1:
                    break
                timeval = np.fromfile(f, dtype=np.float, count=1)
                nvar = np.fromfile(f, dtype=np.int32, count=1)
                data = np.fromfile(f, dtype=np.int32, count=1) #end label
                times = np.vstack([times, timeval])
                data = np.fromfile(f, dtype=np.int32, count=1) #label
                result = np.fromfile(f, dtype=np.float, count=ncel)
                data = np.fromfile(f, dtype=np.int32, count=1) #end label
                if nvar == 1:
                    h = np.vstack([h, result])
                elif nvar == 8:
                    v = np.vstack([v, result])
    except IOError:
        print('Error: The .res file does not exist')
        return failload
    f.close()
    return baryXY, np.unique(times), h, v

if __name__ == '__main__':
    # read the mesh of sw2d
    mesh_sw2d_file = 'a.geo'
    mesh_sw2d = read_mesh_sw2d(mesh_sw2d_file)
    # read results on the water depth and velocity for all time steps
    result_sw2d_file = 'alex23.res'
    result_sw2d = read_result_sw2d(result_sw2d_file)

    print(result_sw2d)
    
