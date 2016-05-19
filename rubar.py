
import os
import warnings
import re
import numpy as np
import matplotlib.pyplot as plt
import time
import hec_ras2D


def load_rubar1d(geofile, mailfile, data_pro, path):
    """
    the function to load the RUBAR data in 1D
    :param geofile: the .m or .st file which gives the coordinates of each profile
    :param mailfile: the coordinate of each mail (1D so only alons the river length) mail.ETUDE file
    :param data_pro: the profile.ETUDE file which contains the height and velocity data
    :param pathgeo
    :return: (x,y,h)
    """
    pass


def load_rubar2d(geofile, tpsfile, pathgeo, pathtps, path_im):
    """
    the function to load the RUBA data in 2D
    :param geofile: the name of the .mai file which contain the connectivity table and the (x,y)
    :param tpsfile: the name of the .tps file
    :param pathgeo : path to the geo file
    :param pathtps : path to the tps file
    :param path_im: the path where to save the figure
    all strings input
    :return: (x,y), ikle velocity and height at the center of the cells, the coordinate of the point of the cells,
    the coordinates of the center of the cells and the connectivity table.
    """
    [ikle, xy, coord_c, nb_cell] = load_mai_2d(geofile, pathgeo)
    [timestep, h,v] = load_tps_2d(tpsfile, pathtps, nb_cell)
    figure_rubar2d(xy, coord_c, ikle, v, h, path_im, [0,1,-1])

    return v, h, xy, coord_c, ikle,


def load_mai_2d(geofile, path):
    """
    the function to load the geomtery info for the 2D case
    :param geofile: the .mai file which contain the connectivity table and the (x,y)
    :param path: the path to this file
    :return: connectivity table, point coordinates, coodinantes of the cell centers
    """
    filename_path = os.path.join(path, geofile)
    # check extension
    blob, ext = os.path.splitext(geofile)
    if ext != '.mai':
        warnings.warn('Warning: The fils does not seem to be of .mai type.')
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_geo2d = f.read()
    except IOError:
        print('Error: The .mai file does not exist.')
        return [-99], [-99], [-99], [-99], [-99], [-99]
    data_geo2d = data_geo2d.splitlines()
    # extract nb cells
    try:
        nb_cell = np.int(data_geo2d[0])
    except ValueError:
        print('Error: Could not extract the number of cells from the .mai file.')
        nb_cell = 0
    # extract connectivity table
    data_l = data_geo2d[1].split()
    m = 0
    ikle = []
    while len(data_l) > 1:
        m += 1
        if m == len(data_geo2d):
            print('Error: Could not extract the connectivity table from the .mai file.')
            return [-99], [-99], [-99], [-99], [-99], [-99]
        data_l = data_geo2d[m].split()
        ind_l = np.zeros(len(data_l)-1,)
        for i in range(0,len(data_l)-1):
            try:
                ind_l[i] = np.float(data_l[i+1]) -1
            except ValueError:
                print('Error: Could not extract the connectivity table from the .mai file.')
                return [-99], [-99], [-99], [-99], [-99], [-99]
        ikle.append(ind_l)

    if len(ikle) != nb_cell+1:
        warnings.warn('Warnings: some cells might be missing.')
    # nb coordinates
    try:
        nb_coord = np.int(data_geo2d[m])
    except ValueError:
        print('Error: Could not extract the number of coordinates from the .mai file.')
        nb_coord = 0
    # extract coordinates
    data_f= []
    m +=1
    for mi in range(m, len(data_geo2d)):
        data_str = data_geo2d[mi]
        l = 0
        while l < len(data_str):
            try:
                data_f.append(float(data_str[l:l + 8]))  # the length of number is eight.
                l += 8
            except ValueError:
                print('Error: Could not extract the coordinates from the .mai file.')
                return [-99], [-99], [-99], [-99], [-99], [-99]
    # separe x and z
    x = data_f[0:nb_coord]  # choose every 2 float
    y = data_f[nb_coord:]
    xy = np.column_stack((x, y))

    # find the center point of each cells
    coord_c = []
    for c in range(0,nb_cell):
        ikle_c = ikle[c]
        xy_c = [0,0]
        for i in range(0, len(ikle_c)):
            xy_c += xy[ikle_c[i]]
        coord_c.append(xy_c/len(ikle_c))


    return ikle, xy, coord_c, nb_cell


def load_tps_2d(tpsfile, path, nb_cell):
    """
    the function to load the data in the 2D rubar case
    :param tpsfile: the name of the file with the data for the 2d case
    :param path:
    :param nb_cell the number of cell extracted from the .mai file
    :return: v, h, timestep (all in list of np.array)
    """
    filename_path = os.path.join(path, tpsfile)
    # check extension
    blob, ext = os.path.splitext(tpsfile)
    if ext != '.tps':
        warnings.warn('Warning: The fils does not seem to be of .tps type.')
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_tps = f.read()
    except IOError:
        print('Error: The .tps file does not exist.')
        return [-99], [-99], [-99], [-99], [-99], [-99]
    data_tps = data_tps.split()
    # get data and transform into float
    i = 0
    t = []
    h = []
    v = []
    while i < len(data_tps):
        try:
            # time
            ti = np.float(data_tps[i])
            t.append(ti)
            i += 1
            hi = np.array(list(map(float, data_tps[i:i+nb_cell])))
            h.append(hi)
            i += nb_cell
            qve = np.array(list(map(float, data_tps[i:i+nb_cell])))
            i += nb_cell
            que = np.array(list(map(float, data_tps[i:i + nb_cell])))
            i += nb_cell
            # velocity
            hiv = np.copy(hi)
            hiv[hiv == 0] = -99  #avoid division by zeros
            vi = np.sqrt((que/hiv)**2 + (qve/hiv)**2)
            vi[hi == 0] = 0  # get realistic again
            v.append(vi)
        except ValueError:
            print('Error: the data could not be extracted from the .tps file. Error at number ' + str(i) + '.')
            return [-99], [-99], [-99], [-99], [-99], [-99]

    return t, h,v


def figure_rubar2d(xy, coord_c, ikle, v, h, path_im, time_step=[-1]):
    """
    the function to plot the rubar 2d data
    :param xy: coordinates of the points
    :param coord_c: the center of the point
    :param ikle: connectivity table
    :param v: speed
    :param h: height
    :param path_im where to save the figure
    ;param time_step which will be plotted
    :return:
    """
    coord_p = np.array(xy)
    coord_c = np.array(coord_c)
    plt.close()

    # ikle cannot be an np.array
    xlist = []
    ylist = []
    for i in range(0, len(ikle)-1):
        pi = 0
        ikle_i = ikle[i]
        while pi < len(ikle_i) - 1:  # we have all sort of xells, max eight sides
            # The conditions should be tested in this order to avoid to go out of the array
            p = ikle_i[pi]  # we start at 0 in python, careful about -1 or not
            p2 = ikle_i[pi + 1]
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = ikle_i[pi]
        p2 = ikle_i[0]
        xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
        xlist.append(None)
        ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
        ylist.append(None)

    fig = plt.figure()
    plt.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title('Grid ')
    plt.savefig(os.path.join(path_im, "RUBAR_grid_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "RUBAR_grid" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    plt.close()  # do not forget to close or the program crash

    for t in time_step:
        # plot water depth
        h_t = np.array(h[t])
        hec_ras2D.scatter_plot(coord_c, h_t, 'Water Depth [m]', 'terrain', 8, t)
        plt.savefig(
            os.path.join(path_im, "rubar2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(
            os.path.join(path_im, "rubar2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        plt.close()

        # plot velocity
        vel_c0 = v[t]
        hec_ras2D.scatter_plot(coord_c, h_t, 'Vel. [m3/sec]', 'gist_ncar', 8, t)
        plt.savefig(
                os.path.join(path_im, "rubar2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(
                os.path.join(path_im, "rubar2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        plt.close()

    # plt.show()


def main():

    path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\2D\120_K35_K25_K20\120_K35_K25_K20'
    geofile2d='BS15a6.mai'
    tpsfile = 'BS15a6.tps'
    load_rubar2d(geofile2d,tpsfile, path, path, path)

if __name__ == '__main__':
    main()