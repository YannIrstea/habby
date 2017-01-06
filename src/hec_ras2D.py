import h5py
import os
import numpy as np
import matplotlib.pyplot as plt
import time


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

    This function should be modified because currently it gets the data by cells. However, we should get the
    data by node. So this function should be changed.

    **Walk-through**

    The name and path of the file is given as input to the load_hec_ras_2D function. Usually this is done by the class
    HEC_RAS() in the GUI.  We load the file using the h5py module. This module opens and reads hdf5 file.

    Then we can read different part of the hdf5 file when we know the address of it (this is a bit like a file system).
    In hdf5 file of Hec-RAS, this first thing is to get the names of the flow area in “Geometry/2D Flow Area”. In
    general, this is the name of each reach, but it could be lake or pond also.

    Then, we go to “Geometry/2D Flow Area/<name>/FacePoint Coordinates” to get the points forming the grid.
    We can also get the connectivity table (or ikle) to the path “Geometry/2D Flow Area/<name>/Cells Face Point Indexes”
    We also get the elevations of the cells. Currently, this is just the minimum elevation of the cells, but it should
    be modified to get the elevation by node (in the vocabulary of HEC-RAS by “FacePoints”). We then get the water depth
    by cell. Somethings should be done to get it by node. I think that we did have the elevation by node somewhere in
    the hdf5 file. For there, water height can be found.
    The velocity is given by face of the cells. It should be averaged differently to get it on the point and
    not on the side.

    """
    filename_path = os.path.join(path, filename)

    # check extension
    blob, ext = os.path.splitext(filename)
    if ext == '.hdf' or ext == '.h5':
        pass
    else:
        print('Warning: The fils does not seem to be of hdf type.')

    # initialization
    coord_p_all = []
    coord_c_all = []
    elev_all = []
    ikle_all = []
    vel_c_all = []
    water_depth_all = []

    # open file
    if os.path.isfile(filename_path):
        try:
            file2D = h5py.File(filename_path, 'r')
        except OSError:
            print("Error: unable to open the hdf file.")
            return [-99], [-99], [-99], [-99], [-99], [-99]
    else:
        print('Error: The hdf5 file does not exist.')
        return [-99], [-99], [-99], [-99], [-99], [-99]

    # geometry and grid data
    try:
        geometry_base = file2D["Geometry/2D Flow Areas"]
        name_area = np.array(geometry_base["Names"])
    except KeyError:
        print('Error: Name of flow area could not be extracted. Check format of the hdf file.')
        return [-99], [-99], [-99], [-99], [-99], [-99]
        # print(list(geometry.items()))
    try:
        for i in range(0, len(name_area)):
            name_area_i = str(name_area[i].strip())
            path_h5_geo = "Geometry/2D Flow Areas" + '/' + name_area_i[2:-1]
            geometry = file2D[path_h5_geo]
            coord_p = np.array(geometry["FacePoints Coordinate"])
            coord_c = np.array(geometry["Cells Center Coordinate"])
            elev = np.array(geometry["Cells Minimum Elevation"])  # might introduce a bias NEED MODIFICATIONS
            ikle = np.array(geometry["Cells FacePoint Indexes"])
            coord_p_all.append(coord_p)
            coord_c_all.append(coord_c)
            elev_all.append(elev)
            ikle_all.append(ikle)
    except KeyError:
        print('Error: Geometry data could not be extracted. Check format of the hdf file.')
        return [-99],[-99], [-99], [-99], [-99], [-99]

    # water depth
    for i in range(0, len(name_area)):
        name_area_i = str(name_area[i].strip())
        path_h5_geo = '/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas'\
                      + '/' + name_area_i[2:-1]
        result = file2D[path_h5_geo]
        water_depth = np.array(result['Depth'])
        water_depth_all.append(water_depth)

    # velocity
    for i in range(0, len(name_area)):
        # velocity is given on the side of the cells.
        # It is to be averaged to find the norm of speed in the middle of the cells.
        cells_face_all = np.array(geometry["Cells Face and Orientation Values"])
        cells_face = cells_face_all[:, 0]
        where_is_cells_face = np.array(geometry["Cells Face and Orientation Info"])
        where_is_cells_face1 = where_is_cells_face[:,1]
        face_unit_vec = np.array(geometry["Faces NormalUnitVector and Length"])
        face_unit_vec = face_unit_vec[:, :2]
        velocity = np.array(result["Face Velocity"])
        new_vel = np.hstack((face_unit_vec, velocity.T))  # for optimization (looking for face is slow)
        lim_b = 0
        nbtstep = velocity.shape[0]
        vel_c = np.zeros((len(coord_c), nbtstep))
        for c in range(0, len(coord_c)):
            # find face
            nb_face = where_is_cells_face1[c]
            lim_a = lim_b
            lim_b = lim_a + nb_face
            face = cells_face[lim_a:lim_b]
            data_face = new_vel[face, :]
            data_face_t = data_face[:, 2:].T
            add_vec_x = np.sum(data_face_t*data_face[:, 0], axis=1)
            add_vec_y = np.sum(data_face_t*data_face[:, 1], axis=1)
            vel_c[c, :] = (1.0/nb_face) * np.sqrt(add_vec_x**2 + add_vec_y**2)
        vel_c_all.append(vel_c)

    return vel_c_all, water_depth_all, elev_all, coord_p_all, coord_c_all, ikle_all


def figure_hec_ras2d(v_all, h_all, elev_all, coord_p_all, coord_c_all, ikle_all, path_im,  time_step=[0], flow_area=[0], max_point=-99):
    """
    This is a function to plot figure of the output from hec-ras 2D.


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
    #plt.close()
    fig_size_inch = (8,6)
    #plt.rcParams['figure.figsize'] = 7, 3
    plt.rcParams['font.size'] = 10

    # for each chosen flow_area
    for f in flow_area:
        ikle = ikle_all[f]
        coord_p = coord_p_all[f]
        coord_c = coord_c_all[f]
        elev = elev_all[f]
        vel_c = v_all[f]
        water_depth = h_all[f]

        # plot grid
        [xlist, ylist] = prepare_grid(ikle, coord_p)
        fig = plt.figure()
        # sc2 = plt.scatter(coord_p[:, 0], coord_p[:, 1], s=0.07, color='r')
        # sc1 = plt.scatter(point_dam_levee[:, 0], point_dam_levee[:, 1], s=0.07, color='k')
        plt.plot(xlist, ylist, c='b', linewidth=0.2)
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Grid ')
        plt.savefig(os.path.join(path_im, "HEC2D_grid_"+ time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(os.path.join(path_im, "HEC2D_grid" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        #plt.close()

        # size of the marker (to avoid having to pale, unclear figure)
        # this is a rough estimation, no need for precise number here
        d1 = 0.5 * np.sqrt((coord_c[1,0] - coord_c[0,0])**2 + (coord_c[1,1] - coord_c[0, 1])**2)  # dist in coordinate
        dist_data = np.mean([np.max(coord_c[:,0]) - np.min(coord_c[:,0]), np.max(coord_c[:,1]) - np.min(coord_c[:,1])])
        f_len = fig_size_inch[0] * 72  # point is 1/72 inch
        transf = f_len/dist_data
        s1 = 3.1 * (d1* transf)**2 / 2  # markersize is given as an area
        s2 = s1/10

        # elevation
        fig = plt.figure()
        cm = plt.cm.get_cmap('terrain')
        sc = plt.scatter(coord_c[:, 0], coord_c[:, 1], c=elev, vmin=np.nanmin(elev), vmax=np.nanmax(elev), s=s1,cmap=cm, edgecolors='none')
        cbar = plt.colorbar(sc)
        cbar.ax.set_ylabel('Elev. [m]')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Elevation above sea level')
        plt.savefig(os.path.join(path_im, "HEC2D_elev_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(os.path.join(path_im, "HEC2D_elev_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        #plt.close()

        # for each chosen time step
        for t in time_step:
            # plot water depth
            water_deptht = np.squeeze(water_depth[t, :])
            scatter_plot(coord_c, water_deptht, 'Water Depth [m]', 'terrain', 8, t)
            plt.savefig(os.path.join(path_im, "HEC2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
            plt.savefig(os.path.join(path_im, "HEC2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
            #plt.close()

             # plot velocity
            vel_c0 = vel_c[:, t]
            scatter_plot(coord_c,vel_c0, 'Vel. [m3/sec]', 'gist_ncar', 8, t)
            plt.savefig(os.path.join(path_im, "HEC2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
            plt.savefig(os.path.join(path_im, "HEC2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
            #plt.close()

    #plt.show()


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
    if max_point < 0 or max_point > len(ikle[:, 0]):
        max_point = len(ikle[:, 0])

    # prepare grid
    xlist = []
    ylist = []
    col_ikle = ikle.shape[1]
    for i in range(0, max_point):
        pi = 0
        while pi < col_ikle - 1 and ikle[i, pi + 1] > 0:  # we have all sort of xells, max eight sides
            # The conditions should be tested in this order to avoid to go out of the array
            p = ikle[i, pi]  # we start at 0 in python, careful about -1 or not
            p2 = ikle[i, pi + 1]
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = ikle[i, pi]
        p2 = ikle[i, 0]
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
    s2 = s1/10
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
        plt.text(np.mean(coord[:,0]), np.mean(coord[:,1]), 'Data is null. No plotting possible')
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
    filename='Muncie.p04.hdf'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    a = time.clock()
    [v, h, elev, coord_p, coord_c, ikle] = load_hec_ras2d(filename, path)
    b = time.clock()
    print('Time to load data:' + str(b-a) + 'sec')
    figure_hec_ras2d(v, h, elev, coord_p, coord_c, ikle, path_im, [0], [0])


if __name__ == '__main__':
    main()