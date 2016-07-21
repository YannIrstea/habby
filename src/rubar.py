
import os
import re
import numpy as np
import matplotlib.pyplot as plt
import time
from src import hec_ras2D
import xml.etree.ElementTree as Etree


def load_rubar1d(geofile, data_vh, pathgeo, pathdata, path_im, savefig):
    """
    the function to load the RUBAR data in 1D
    :param geofile: the name of .rbe file which gives the coordinates of each profile - string
    :param mailfile: the coordinate x of each mail (1D so only along the river length) mail.ETUDE file -string
    :param data_vh: the profile.ETUDE file which contains the height and velocity data
    :param pathgeo the path to the geofile - string
    :param pathmail idem
    :param pathdata the path to the data_vh file
    :param path_im the file where to save the image
    :param savefig: a boolean. If True create and save the figure.
    :return: coordinates of the profile (x,z,y, dist along the profile) coordinates (x,y) of the river and the bed,
    data xhzv by time step where x is the distance along the river, h the water height, z the elevation of the bed
    and v the velocity
    """

    # load the river coordinates 1d (not needed anymore, but can be useful)
    # [x, nb_mail] = load_mai_1d(mailfile, pathmail)
    # load the profile coordinates
    [coord_pro, lim_riv, name_profile, x] = load_coord_1d(geofile, pathgeo)
    # load the height and velocity 1d
    [timestep, data_xhzv]= load_data_1d(data_vh, pathdata, x)

    # plot the figure
    if savefig:
        figure_rubar1d(coord_pro, lim_riv, data_xhzv, name_profile, path_im, [0, 2], [-1])

    return data_xhzv, coord_pro, lim_riv


def load_mai_1d(mailfile, path):
    """
    :param mailfile: the name of the file which contain the (x,z) data
    :param path: the path to this file
    :return: x of the river, np.array and the number of mail
    """
    filename_path = os.path.join(path, mailfile)

    # check if the file exists
    if not os.path.isfile(filename_path):
        print('Error: The mail.ETUDE file does not exist.')
        return [-99], 99
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_geo1d = f.read()
    except IOError:
        print('Error: The mail.ETUDE file can not be open.')
        return [-99], 99

    data_geo1d = data_geo1d.split()
    # find the number of mailles
    try:
        nb_mail = np.int(data_geo1d[0])
    except ValueError:
        print('Error: Could not extract the number of cells from the mail.ETUDE file.')
        return [-99], 99
    data_geo1d = data_geo1d[1:]
    # get the coordinates
    if len(data_geo1d) != 2*nb_mail-1:
        print('Error: the number of cells is not the one expected in the mail.ETUDE file')
        return [-99], 99
    try:
        x = np.array(list(map(float, data_geo1d[:nb_mail])))
    except ValueError:
        print('Error: the cells coordinates could not be extracted from the mail.ETUDE file.')
        return [-99], 99
    return x, nb_mail


def load_data_1d(name_data_vh, path, x):
    """
    :param name_data_vh: the name of the profile.ETUDE file
    :param path: the path to this file
    :param x the distance along the river
    :return: data x, velocity height, cote for each time step (list of np.array), time step
    """
    failload = [-99], [-99]

    filename_path = os.path.join(path, name_data_vh)
    # check if the file exists
    if not os.path.isfile(filename_path):
        print('Error: The profil.ETUDE file does not exist.\n')
        return failload
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_vh = f.read()
    except IOError:
        print('Error: The profil.ETUDE file can not be open.\n')
        return failload
    data_vh = np.array(data_vh.split())
    # find timestep
    timestep_ind = np.squeeze(np.array(np.where(data_vh == 'tnprof'))) - 1  # why [[]] and not []?
    if len(timestep_ind) == 0:
        print('Error: No timestep could be extracted from the profil.ETUDE file.\n')
        return failload
    try:
        timestep = np.array(list(map(float, data_vh[timestep_ind])))
    except ValueError:
        print('Error: the timesteps could not be extracted from the profile.ETUDE file.\n')
        return failload

    # find velocity, height
    data_xhzv = []
    cote = []
    nb_mail = (len(data_vh) - timestep_ind[-1] - 2)/4
    for i in range(0, len(timestep_ind)):
        data_vh_t = data_vh[timestep_ind[i] + 2:int(timestep_ind[i] + 4*nb_mail + 4)]
        vel_t = data_vh_t[1:-1:4]
        h_t = data_vh_t[0:-2:4]
        try:
            vel_t = np.array(list(map(float, vel_t)))
        except ValueError:
            print('Error: Velocity could not be extracted from the profile.ETUDE file.\n')
            return failload
        try:
            h_t = np.array(list(map(float, h_t)))
        except ValueError:
            print('Error: Water height could not be extracted from the profile.ETUDE file.\n')
            return failload
            # find cote z (altitude of the river bed)
            # cote are the same for all time steps
        if i == 0:
            cote = data_vh_t[3:-1:4]
            try:
                cote = np.array(list(map(float, cote)))
            except ValueError:
                print('Error: River bed altitude could not be extracted from the profile.ETUDE file.\n')
                return failload

        data = np.column_stack((x,  h_t, cote, vel_t))

        data_xhzv.append(data)

    return timestep, data_xhzv


def load_coord_1d(name_rbe, path):
    """
    the function to load the rbe file, which is an xml file.
    :param name_rbe: The name fo the rbe files
    :param path: the path to this file
    :return: the coordinates of the profiles and the coordinates of the right bank, center of the river, left bank
    (list of np.array with x,y,z coordinate), name of the profile (list of string), dist along the river (list of float)
    number of cells (int)
    """
    filename_path = os.path.join(path, name_rbe)
    # check extension
    blob, ext = os.path.splitext(name_rbe)
    if ext != '.rbe':
        print('Warning: The fils does not seem to be of .rbe type.\n')
    # load the XML file
    if not os.path.isfile(filename_path):
        print('Error: the .reb file does not exist.\n')
        return [-99], [-99], [-99], [-99]
    try:
        docxml = Etree.parse(filename_path)
        root = docxml.getroot()
    except IOError:
        print("Error: the .rbe file cannot be open.\n")
        return [-99], [-99], [-99], [-99]
    # read the section data
    try:  # check that the data is not empty
        jeusect = root.findall(".//Sections.JeuSection")
        sect = jeusect[0].findall(".//Sections.Section")
    except AttributeError:
        print("Error: Sections data cannot be read from the .rbe file\n")
        return [-99], [-99], [-99], [-99]
    # read each point of the section
    coord = []
    lim_riv = []  # for each section, the right lim of the bed, the position of the 1D river, the left lim of the bed
    name_profile = []
    dist_riv = []
    for i in range(0, len(sect)):
        try:
            point = sect[i].findall(".//Sections.PointXYZ")
        except AttributeError:
            print("Error: Point data cannot be read from the .rbe file\n")
            return [], [], []
        try:
            name_profile.append(sect[i].attrib['nom'])
        except KeyError:
            print('Warning: The name of the profile could not be extracted from the .reb file.\n')
        try:
            x = sect[i].attrib['Pk']
            dist_riv.append(np.float(x))
        except KeyError:
            print('Warning: The name of the profile could not be extracted from the .reb file.\n')
        coord_sect = np.zeros((len(point), 4))
        lim_riv_sect = np.zeros((3, 3))
        name_sect = []
        for j in range(0, len(point)):
            attrib_p = point[j].attrib
            try:
                coord_sect[j, 0] = np.float(attrib_p['x'])
                coord_sect[j, 1] = np.float(attrib_p['y'])
                coord_sect[j, 2] = np.float(attrib_p['z'])
                if j > 0:
                    coord_sect[j, 3] = coord_sect[j-1,3] + np.sqrt((coord_sect[j, 0] - coord_sect[j-1, 0])**2 +
                                               (coord_sect[j, 1] - coord_sect[j-1, 1])**2)
            except ValueError:
                print('Error: Some coordinates of the .rbe file are not float. Section number: ' + str(i+1)+'.\n')
                return [-99], [-99], [-99], [-99]
            # find right bank, left bank and river center.
            try:
                name_here = attrib_p['nom']
            except KeyError:
                print('Error: the position of the river can not be extracted fromt he .rbe file.\n')
                return [-99], [-99], [-99], [-99]
            if name_here == 'rg':
                lim_riv_sect[0, :] = coord_sect[j, :3]
            if name_here == 'axe':
                lim_riv_sect[1, :] = coord_sect[j, :3]
            if name_here == 'rd':
                lim_riv_sect[2, :] = coord_sect[j, :3]
        coord_sect = coord_sect.T
        coord.append(coord_sect)
        lim_riv.append(lim_riv_sect)

    # geometry on cell border, hydraulique center of cell for the data (more intesting for us)
    x = [(a + b) / 2 for a, b in zip(dist_riv[:], dist_riv[1:])]
    x = np.concatenate(([dist_riv[0]], x, [dist_riv[-1]]))

    return coord, lim_riv, name_profile, x


def figure_rubar1d(coord_pro, lim_riv, data_xhzv,  name_profile, path_im, pro, plot_timestep):
    """
    The function to plot the loaded RUBAR 1D data
    :param coord_pro: the cooedinate of the profile (x, y, z, dist along the river)
    :param lim_riv: the right bank, river center, left bank
    :param data_xhzv the data by time step with x the distance along the river, h the water height and v the vlocity
    :param cote: the altitude of the river center
    :param name_profile the name of the profile
    :param path_im: the path where to save the image
    :param pro: the profile number which should be plotted
    :param plot_timestep: which timestep should be plotted
    :return: none
    """
    plt.close()
    #plt.rcParams.update({'font.size': 9})

    # profiles in xy view
    riv_mid = np.zeros((len(coord_pro), 3))
    fig2 = plt.figure()
    for p in range(0, len(coord_pro)):
        coord_p = coord_pro[p]
        plt.plot(coord_p[0], coord_p[1], '-b')
        plt.plot(coord_p[0], coord_p[1], 'xk',markersize=1)
        riv_sect = lim_riv[p]
        riv_mid[p, :] = riv_sect[1]
        if p % 5 == 0:
            plt.text(coord_p[0, 0] + 0.03, coord_p[0, 1] + 0.03, name_profile[p])
    # river
    plt.plot(riv_mid[:, 0], riv_mid[:, 1], '-r')
    plt.xlabel("x coordinate []")
    plt.ylabel("y coordinate []")
    plt.title("Position of the profiles")
    # plt.axis('equal') # if right angle are needed
    plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
    plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))

    # plot speeed and height
    x = data_xhzv[0][:, 0]
    cote = data_xhzv[0][:, 2]
    for t in plot_timestep:
        fig1 = plt.figure()
        h_t = data_xhzv[t][:, 1]
        v_t = data_xhzv[t][:, 3]
        if t == -1:
            plt.suptitle("RUBAR1D - Last timestep ")
        else:
            plt.suptitle("RUBAR1D - Timestep " + str(t))
        ax1 = plt.subplot(211)
        plt.plot(x, h_t + cote, '-b')
        plt.plot(x, cote, '-k')
        plt.xlabel('Distance along the river [m]')
        plt.ylabel('Height [m]')
        plt.legend(('water height', 'river slope'))
        ax1 = plt.subplot(212)
        plt.plot(x, v_t, '-r')
        plt.xlabel('Distance along the river [m]')
        plt.ylabel('Velocity [m/sec]')
        plt.savefig(
            os.path.join(path_im, "rubar1D_vh_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(
            os.path.join(path_im, "rubar1D_vh_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
    # plt.close()
    # plt.show()


def load_rubar2d(geofile, tpsfile, pathgeo, pathtps, path_im, save_fig):
    """
    the function to load the RUBAR data in 2D
    :param geofile: the name of the .mai file which contains the connectivity table and the (x,y)
    :param tpsfile: the name of the .tps file
    :param pathgeo : path to the geo file
    :param pathtps : path to the tps file
    :param path_im: the path where to save the figure
    :param save_fig: boolean indicated if the figures should be created or not
    all strings input
    :return: (x,y), ikle velocity and height at the center of the cells, the coordinate of the point of the cells,
    the coordinates of the center of the cells and the connectivity table.
    """
    [ikle, xy, coord_c, nb_cell] = load_mai_2d(geofile, pathgeo)
    [timestep, h,v] = load_tps_2d(tpsfile, pathtps, nb_cell)
    if save_fig:
        figure_rubar2d(xy, coord_c, ikle, v, h, path_im, [-1])

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
        print('Warning: The fils does not seem to be of .mai type.\n')
    # check if the file exist
    if not os.path.isfile(filename_path):
        print('Error: The .mai file does not exist.')
        return [-99], [-99], [-99], [-99]
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_geo2d = f.read()
    except IOError:
        print('Error: The .mai file can not be open.\n')
        return [-99], [-99], [-99], [-99]
    data_geo2d = data_geo2d.splitlines()
    # extract nb cells
    try:
        nb_cell = np.int(data_geo2d[0])
    except ValueError:
        print('Error: Could not extract the number of cells from the .mai file.\n')
        return [-99], [-99], [-99], [-99]
        nb_cell = 0
    # extract connectivity table, not always triangle
    data_l = data_geo2d[1].split()
    m = 0
    ikle = []
    while len(data_l) > 1:
        m += 1
        if m == len(data_geo2d):
            print('Error: Could not extract the connectivity table from the .mai file.\n')
            return [-99], [-99], [-99], [-99]
        data_l = data_geo2d[m].split()
        ind_l = np.zeros(len(data_l)-1, dtype=np.int)
        for i in range(0, len(data_l)-1):
            try:
                ind_l[i] = int(data_l[i+1]) - 1
            except ValueError:
                print('Error: Could not extract the connectivity table from the .mai file.\n')
                return [-99], [-99], [-99], [-99]
        ikle.append(ind_l)

    if len(ikle) != nb_cell+1:
        print('Warning: some cells might be missing.\n')
    # nb coordinates
    try:
        nb_coord = np.int(data_geo2d[m])
    except ValueError:
        print('Error: Could not extract the number of coordinates from the .mai file.\n')
        nb_coord = 0
    # extract coordinates
    data_f = []
    m += 1
    for mi in range(m, len(data_geo2d)):
        data_str = data_geo2d[mi]
        l = 0
        while l < len(data_str):
            try:
                data_f.append(float(data_str[l:l + 8]))  # the length of number is eight.
                l += 8
            except ValueError:
                print('Error: Could not extract the coordinates from the .mai file.\n')
                return [-99], [-99], [-99], [-99]
    # separe x and z
    x = data_f[0:nb_coord]  # choose every 2 float
    y = data_f[nb_coord:]
    xy = np.column_stack((x, y))

    # find the center point of each cellss
    # slow because number of point of a cell changes
    coord_c = []
    for c in range(0, nb_cell):
        ikle_c = ikle[c]
        xy_c = [0, 0]
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
        print('Warning: The fils does not seem to be of .tps type.\n')
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_tps = f.read()
    except IOError:
        print('Error: The .tps file does not exist.\n')
        return [-99], [-99], [-99]
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
            print('Error: the data could not be extracted from the .tps file. Error at number ' + str(i) + '.\n')
            return [-99], [-99], [-99]

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
        hec_ras2D.scatter_plot(coord_c, h_t, 'Vel. [m/sec]', 'gist_ncar', 8, t)
        plt.savefig(
                os.path.join(path_im, "rubar2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(
                os.path.join(path_im, "rubar2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        plt.close()

    # plt.show()


def main():

    #path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\2D\120_K35_K25_K20\120_K35_K25_K20'
    #geofile2d='BS15a6.mai'
    #tpsfile = 'BS15a6.tps'
    #load_rubar2d(geofile2d,tpsfile, path, path, path, True)

    path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\1D\LE2013\LE2013\LE13'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    mail = 'mail.LE13'
    geofile = 'LE13.rbe'
    data = 'profil.LE13'
    load_rubar1d(geofile, data, path, path, path_im, True)


if __name__ == '__main__':
    main()