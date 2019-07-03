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
import sys
import numpy as np
import matplotlib.pyplot as plt
import time
from src import hec_ras2D_mod
from io import StringIO
from src import hdf5_mod
from src import manage_grid_mod
import xml.etree.ElementTree as Etree
from src import dist_vistess_mod
from src_GUI import preferences_GUI
import matplotlib as mpl


def load_rubar1d_and_create_grid(name_hdf5, path_hdf5, name_prj, path_prj, model_type, namefile, pathfile,
                                 interpo_choice
                                 , manning_data, nb_point_vel, show_fig_1D, pro_add, q=[], path_im='.',
                                 print_cmd=False):
    """
    This function is used to load rubar 1d data by calling the load_rubar1d() function and to create the grid
    by calling the grid_and_interpo function in manage_grid_8. This function is called in a second thread by the class
    Rubar() in Hydro_grid_2(). It also distribute the velocity by calling dist_vitess2.

    :param name_hdf5: the name of the hdf5 to be created (string)
    :param path_hdf5: the path to the hdf5 to be created (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model (rubar in most case, but given as argument in case we change
           the form of the name)
    :param namefile: the name of the geo file and the data file, which contains respectively geographical data and
           the ouput data (see open_hec_ras() for more precision) -> list of string
    :param pathfile: the absolute path to the file chosen into namefile -> list of string
    :param interpo_choice: the interpolation type (int: 0,1,2 or 3). See grid_and_interpo() for mroe details.
    :param manning_data: Contains the manning data. It can be in an array form (variable) or as a float (constant)
    :param nb_point_vel: the number of velcoity point by whole profile
    :param show_fig_1D: A boolean. If True, image from the 1D data are created and savec
    :param q: used by the second thread.
    :param path_im: the path where to save the figure
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line. We make the switch here.
    """

    # load the rubar 1D
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    project_preferences = preferences_GUI.load_project_preferences(path_prj, name_prj)
    [xhzv_data, coord_pro, lim_riv, timestep] = load_rubar1d(namefile[0], namefile[1], pathfile[0], pathfile[1],
                                                             path_im,
                                                             show_fig_1D, project_preferences)
    if show_fig_1D:
        plt.close()  # just save the figure do not show them

    if xhzv_data == [-99]:
        print("Rubar data could not be loaded.")
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    nb_pro_reach = [0, len(coord_pro)]  # should be corrected? (only one reach for the moment)

    # distribute the velocity
    vh_pro = dist_vistess_mod.distribute_velocity(manning_data, nb_point_vel, coord_pro, xhzv_data)

    # create the grid
    [ikle_all_t, point_all_t, point_c_all_t, inter_vel_all_t, inter_h_all_t] \
        = manage_grid_mod.grid_and_interpo(vh_pro, coord_pro, nb_pro_reach, interpo_choice, pro_add)

    # save the hdf5 file
    timestep_str = list(map(str, timestep))
    hdf5_mod.save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, 1.5, path_hdf5, ikle_all_t,
                                     point_all_t,
                                     point_c_all_t, inter_vel_all_t, inter_h_all_t, [], coord_pro, vh_pro,
                                     nb_pro_reach,
                                     sim_name=timestep_str, hdf5_type="hydraulic")
    if print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def load_rubar1d(geofile, data_vh, pathgeo, pathdata, path_im, savefig, project_preferences=[]):
    """
    the function to load the RUBAR BE data (in 1D).

    :param geofile: the name of .rbe file which gives the coordinates of each profile (string)
    :param data_vh: the name of the profile.ETUDE file which contains the height and velocity data (string)
    :param pathgeo: the path to the geofile - string
    :param pathdata: the path to the data_vh file
    :param path_im: the file where to save the image
    :param savefig: a boolean. If True create and save the figure.
    :param project_preferences: A dictionarry with the figure option
    :return: coordinates of the profile (x,y,z dist along the profile) coordinates (x,y) of the river and the bed,
            data xhzv by time step where x is the distance along the river, h the water height, z the elevation of the bed
            and v the velocity
    """
    failload = [-99], [-99], [-99], [-99]

    # load the river coordinates 1d (not needed anymore, but can be useful)
    # [x, nb_mail] = load_mai_1d(mail, pathgeo)

    # load the profile coordinates
    blob, ext = os.path.splitext(geofile)
    if ext == ".rbe":
        [coord_pro, lim_riv, name_profile, x] = load_coord_1d(geofile, pathgeo)
        nb_pro_reach = [0, 10 ** 10]
    elif blob == "m":
        [coord_pro, name_profile, x, nb_pro_reach] = m_file_load_coord_1d(geofile, pathgeo)
        lim_riv = [0, 0, 0]
    else:
        print('Error: the geofile file should be a m.ETUDE file or a rbe file.')
        return failload

    # load the height and velocity 1d
    [timestep, data_xhzv] = load_data_1d(data_vh, pathdata, x)

    # plot the figure
    if savefig:
        if np.all(data_xhzv == [-99]) or np.all(coord_pro[0] == -99):
            print('Error: No data to produce the figure. \n')
            return failload
        else:
            if project_preferences['time_step'][0] == -99:
                tfig = range(0, len(coord_pro))
            else:
                tfig = project_preferences['time_step']
                tfig = list(map(int, tfig))
            figure_rubar1d(coord_pro, lim_riv, data_xhzv, name_profile, path_im, [0, 2], tfig, nb_pro_reach, project_preferences)

    return data_xhzv, coord_pro, lim_riv, timestep


def load_mai_1d(mailfile, path):
    """
    This function is not used anymore. It was used to load the coordinate of the 1D data. It might become useful again
    in the case where we found a Rubar model with more than one reach (which we do not have yet).

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
    if len(data_geo1d) != 2 * nb_mail - 1:
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
    This function loads the output data for Rubar BE (in 1D). The geometry data should be loaded before using this function.

    :param name_data_vh: the name of the profile.ETUDE file (string)
    :param path: the path to this file
    :param x: the distance along the river (from the .geo file)
    :return: data x, velocity height, cote for each time step (list of np.array), time step
    """
    failload = [-99], [-99]
    warn_num = True

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
    data_vh = data_vh.split('\n')

    # analyze each line
    timestep = []
    data_xhzv = []
    data = []
    c = 0
    for i in range(0, len(data_vh)):
        data_vh_i = data_vh[i].split()
        if len(data_vh_i) != 4 and len(data_vh_i) > 0:
            try:
                timestep.append(np.float(data_vh_i[0]))
            except ValueError:
                print('Error: the timesteps could not be extracted from the profile.ETUDE file.\n')
                return failload
            if i > 0:
                data_xhzv.append(np.array(data))
                data = []
                c = 0
        elif len(data_vh_i) > 0:
            try:
                h_i = np.float(data_vh_i[0])
            except ValueError:
                print('Error: Velocity could not be extracted from the profile.ETUDE file.\n')
                return failload
            try:
                vel_i = np.float(data_vh_i[1])
            except ValueError:
                print('Error: Water height could not be extracted from the profile.ETUDE file.\n')
                return failload
            try:
                cote_i = np.float(data_vh_i[3])
            except ValueError:
                print('Error: River bed altitude could not be extracted from the profile.ETUDE file.\n')
                return failload
            try:
                data.append([x[c], h_i, cote_i, vel_i])
            except IndexError:
                if warn_num:
                    print('Warning: The number of profile is not the same in the geo file and the data file. \n')
                    warn_num = False
                # return failload
            c += 1
    data_xhzv.append(np.array(data))

    if len(timestep) == 0:
        print('Error: No timestep could be extracted from the profil.ETUDE file.\n')
        return failload

    return timestep, data_xhzv


def m_file_load_coord_1d(geofile_name, pathgeo):
    """
        This function loads the m.ETUDE file which is based on .st format from cemagref. When we use the M.ETUDE file
        instead of the rbe file, more than one reach can be studied but the center and side of the river is not
        indicated anymore.

        :param geofile_name: The name to the m.ETUDE file (string)
        :param pathgeo: the path to this file (string)
        :return: the coordinates of the profiles (list of np.array with x,y,z coordinate), name of the profile
                (list of string), dist along the river (list of float), number of profile by reach
        """
    failload = [-99], [-99], [-99], [-99]

    # open the file
    filename_path = os.path.join(pathgeo, geofile_name)
    # check if the file exists
    if not os.path.isfile(filename_path):
        print('Error: The m.ETUDE file does not exist.\n')
        return failload
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_geo = f.read()
    except IOError:
        print('Error: The m.ETUDE file can not be open.\n')
        return failload

    # preparation
    data_geo = data_geo.split('\n')
    check_reach = 0
    coord_pro = []
    coord_x = []
    coord_y = []
    coord_z = []
    dist_pro = []
    dist_riv = []
    name_profile = []
    nb_pro_reach = [0]
    new_profile = True
    send_warn = True
    pro = 0

    # get the data line by line
    for i in range(0, len(data_geo)):
        data_i = data_geo[i]
        data_i = data_i.split()
        if len(data_i) > 1:
            if new_profile:
                # test for new bief
                try:
                    pro2 = np.float(data_i[0])
                except ValueError:
                    print('Error: the profile number could not be extracted from the m.ETUDE file. \n')
                    return failload
                if pro + 1 != pro2:
                    nb_pro_reach.append(nb_pro_reach[-1] + pro)
                    pro = 0
                pro += 1
                # get distance along the river
                if len(data_i) == 4:
                    try:
                        # there is some profiles with only 3+1 int (rare)
                        # this means that two number are stick together
                        num = data_i[3]
                        num = num[3:]
                        dist_riv_here = np.float(num)
                    except ValueError:
                        print('Error: the distance between profile could not be extracted from the m.ETUDE file. \n')
                        return failload
                else:
                    try:
                        dist_riv_here = np.float(data_i[4])
                    except ValueError:
                        print('Error: the distance between profile could not be extracted from the m.ETUDE file. \n')
                        return failload
                dist_riv.append(dist_riv_here)
                # get profile_name
                if len(data_i) > 5:
                    name_profile.append(data_i[5])
                else:
                    name_profile.append(' ')
                new_profile = False
                if i > 0:
                    # add to coord_pro
                    coord_sect = np.array([coord_x, coord_y, coord_z, dist_pro])
                    # For the 2D grid, it is not possible to have vertical profile, i.e. identical points
                    [coord_sect, send_warn] = correct_duplicate_xy(coord_sect, send_warn)
                    coord_pro.append(coord_sect)
                    coord_x = []
                    coord_y = []
                    coord_z = []
                    dist_pro = []
            else:
                try:
                    xhere = np.float(data_i[0])
                    yhere = np.float(data_i[1])
                    zhere = np.float(data_i[2])
                except ValueError:
                    print('Error: A coordinate could not be extracted from the m.ETUDE file. \n')
                    return failload
                # check if profile end
                if xhere == 999.9990 and yhere == 999.9990:
                    new_profile = True
                else:
                    # get x y z
                    coord_x.append(xhere)
                    coord_y.append(yhere)
                    coord_z.append(zhere)
                    if len(dist_pro) > 0:
                        dist_here = dist_pro[-1] + + np.sqrt((coord_x[-1] - coord_x[-2]) ** 2 +
                                                             (coord_y[-1] - coord_y[-1]) ** 2)
                    else:
                        dist_here = 0
                    dist_pro.append(dist_here)

    # add the last profil
    nb_pro_reach.append(nb_pro_reach[-1] + pro)
    coord_sect = np.array([coord_x, coord_y, coord_z, dist_pro])
    # For the 2D grid, it is not possible to have vertical profile, i.e. identical points
    [coord_sect, send_warn] = correct_duplicate_xy(coord_sect, send_warn)
    coord_pro.append(coord_sect)

    # geometry on cell border, hydraulique center of cell for the data (more intesting for us)
    x = []
    if len(nb_pro_reach) == 1:
        nb_pro_reach = [0, len(dist_riv) - 1]
    for r in range(0, len(nb_pro_reach) - 1):
        x_r = [(a + b) / 2 for a, b in
               zip(dist_riv[nb_pro_reach[r]:nb_pro_reach[r + 1]], dist_riv[nb_pro_reach[r] + 1:nb_pro_reach[r + 1]])]
        x_r = np.concatenate(([dist_riv[nb_pro_reach[r]]], x_r, [dist_riv[nb_pro_reach[r + 1] - 1]]))
        x.extend(x_r)

    return coord_pro, name_profile, x, nb_pro_reach


def load_coord_1d(name_rbe, path):
    """
    the function to load the rbe file, which is an xml file. The gives the geometry of the river system.

    :param name_rbe: The name fo the rbe file (string)
    :param path: the path to this file (string)
    :return: the coordinates of the profiles and the coordinates of the right bank, center of the river, left bank
            (list of np.array with x,y,z coordinate), name of the profile (list of string), dist along the river (list of float)
            number of cells (int)
    """
    warn_riv = True
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
    send_warn = True
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
            x = sect[i].attrib['Pk']  # nthis is hte distance along the river, not along the profile
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
                    coord_sect[j, 3] = coord_sect[j - 1, 3] + np.sqrt((coord_sect[j, 0] - coord_sect[j - 1, 0]) ** 2 +
                                                                      (coord_sect[j, 1] - coord_sect[j - 1, 1]) ** 2)
            except ValueError:
                print('Error: Some coordinates of the .rbe file are not float. Section number: ' + str(i + 1) + '.\n')
                return [-99], [-99], [-99], [-99]
            try:
                name_here = attrib_p['nom']
            except KeyError:
                print('Error: the position of the river can not be extracted from the .rbe file.\n')
                return [-99], [-99], [-99], [-99]
            if name_here == 'rg':
                lim_riv_sect[0, :] = coord_sect[j, :3]
            if name_here == 'axe':
                lim_riv_sect[1, :] = coord_sect[j, :3]
            if name_here == 'rd':
                lim_riv_sect[2, :] = coord_sect[j, :3]
        coord_sect = coord_sect.T
        # sometime there is no river found
        if np.sum(lim_riv_sect[:, 1]) == 0 and warn_riv:
            print('Warning: the position of the river is not found in the .rbe file.\n')
            warn_riv = False
        # For the 2D grid, it is not possible to have vertical profile, i.e. identical points
        [coord_sect, send_warn] = correct_duplicate_xy(coord_sect, send_warn)
        # find right bank, left bank and river center.
        coord.append(coord_sect)
        lim_riv.append(lim_riv_sect)

    # geometry on cell border, hydraulique center of cell for the data (more intesting for us)
    x = [(a + b) / 2 for a, b in zip(dist_riv[:], dist_riv[1:])]
    x = np.concatenate(([dist_riv[0]], x, [dist_riv[-1]]))

    for c in range(0, len(coord)):
        if coord[c][0][-1] == coord[c][0][-2]:
            print(c)
            print(coord[c])

    return coord, lim_riv, name_profile, x


def correct_duplicate_xy(seq3D, send_warn, idfun=None):
    """
    It is possible to have a vertical line on a profile (different h, identical x). This is not possible for HABBY and
    the 2D grid. So this function correct duplicates along the profile.

    A similiar function exists in mascaret, for the case where the input is the distance along the profile and not
    (x,y) coordinates. This function is inspired by https://www.peterbe.com/plog/uniqifiers-benchmark.

    It should be tested more as manage_grid sometime still send warning about duplicate data in profile.

    :param seq3D: the list to be corrected in this case (x,y,z,dist along the profile)
    :param send_warn: a bool to avoid printing the warning too many time
    :param idfun: support an optional transform function (not tested)
    :return: the list wihtout duplicate and the boolean which helps manage the warnings
    """

    def find_point(seqf, result2, c2, add_l):
        """
        A sub function to find the update (x,y) coordinate bsed on the modification the disntance along the porfile
        :param seqf: the orginal data
        :param result2: the updated distance
        :param c2: where we are
        :param add_l: the added distance from the last point
        :return:
        """

        if c == 0:  # should not happen
            xf = seqf[0, c2] * 1.01
            yf = seqf[1, c2] * 1.01
            print('Warning: First indices is identical to another. Unlogical. \n')
        else:
            if result2[c2] > 0:
                # as a direction for the new point use the general direction of the profil
                # stright line from beginnning of the profil to point c2
                nx = (seqf[0, c2] - seqf[0, 0]) / (result2[c2] - result2[0])
                ny = (seqf[1, c2] - seqf[1, 0]) / (result2[c2] - result2[0])
            else:
                # special case, chosen arbitrarily
                nx = ny = 1
            if nx == 0 or (result2[c2] - result2[c2 - 1]) == 0:
                xf = seqf[0, c2] + 0.01 * c / 10
                yf = seqf[1, c2] + 0.01 * c / 10
            else:
                xf = seqf[0, c2] + nx * add_l
                yf = seqf[1, c2] + ny * add_l

        return xf, yf

    # main function of correct_duplicate!

    seq = seq3D[3, :]

    # order preserving
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    resultx = []
    resulty = []
    c = 0
    le = len(seq)
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            add_l = 0.01 * c / le
            if item > 0:
                result.append(item + add_l)  # moving the duplicate a bit further to correct for it
                [x, y] = find_point(seq3D, result, c, add_l)
                resultx.append(x)
                resulty.append(y)
            elif item < 0:
                result.append(item - add_l)
                [x, y] = find_point(seq3D, result, c, add_l)
                resultx.append(x)
                resulty.append(y)
            else:
                result.append(add_l)
                [x, y] = find_point(seq3D, result, c, add_l)
                resultx.append(x)
                resulty.append(y)

            if send_warn:
                print('Warning: Vertical profile. One or more profiles were modified. \n')
                send_warn = False
        else:
            seen[marker] = 1
            result.append(item)
            resultx.append(seq3D[0, c])
            resulty.append(seq3D[1, c])
        c += 1

    seq3D[0, :] = resultx
    seq3D[1, :] = resulty  # z-= seq[:,2] is not changing
    seq3D[3, :] = result

    return seq3D, send_warn


def figure_rubar1d(coord_pro, lim_riv, data_xhzv, name_profile, path_im, pro, plot_timestep, nb_pro_reach=[0, 10 ** 10]
                   , project_preferences={}):
    """
    The function to plot the loaded RUBAR 1D data (Rubar BE).

    :param coord_pro: the coordinate of the profile (x, y, z, dist along the river)
    :param lim_riv: the right bank, river center, left bank
    :param data_xhzv: the data by time step with x the distance along the river, h the water height and v the vlocity
    :param cote: the altitude of the river center
    :param name_profile: the name of the profile
    :param path_im: the path where to save the image
    :param pro: the profile number which should be plotted
    :param plot_timestep: which timestep should be plotted
    :param nb_pro_reach: the number of profile by reach
    :param project_preferences: the dictionnary with the figure option
    :return: none
    """

    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if project_preferences['font_size'] > 7:
        plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'

    # profiles in xy view
    riv_mid = np.zeros((len(coord_pro), 3))
    fig2 = plt.figure()
    for p in range(0, len(coord_pro)):
        coord_p = coord_pro[p]
        plt.plot(coord_p[0], coord_p[1], '-b')
        # plt.plot(coord_p[0], coord_p[1], 'xk',markersize=1)
        # if p % 5 == 0:
        #  plt.text(coord_p[0, 0] + 0.03, coord_p[0, 1] + 0.03, name_profile[p])
    # river
    # if np.sum(lim_riv[1]) != -99 and np.sum(lim_riv[1]) != 0:
    # riv_sect = lim_riv[p]
    # riv_mid[p, :] = riv_sect[1]
    # plt.plot(riv_mid[:, 0], riv_mid[:, 1], '-r')

    if project_preferences['language'] == 0:
        plt.xlabel("x coordinate []")
        plt.ylabel("y coordinate []")
        plt.title("Position of the profiles")
    elif project_preferences['language'] == 1:
        plt.xlabel("x coordonnées []")
        plt.ylabel("y coordonnées []")
        plt.title("Position des profils")
    # plt.axis('equal') # if right angle are needed
    if format == 0 or format == 1:
        plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'), dpi=project_preferences['resolution'], transparent=True)
    if format == 0 or format == 3:
        plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'), dpi=project_preferences['resolution'], transparent=True)
    if format == 2:
        plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.jpg'), dpi=project_preferences['resolution'], transparent=True)

    # plot speeed and height
    warn_reach = True
    for r in range(0, len(nb_pro_reach) - 1):
        if r < 10:
            x = data_xhzv[0][nb_pro_reach[r]:nb_pro_reach[r + 1], 0]
            cote = data_xhzv[0][nb_pro_reach[r]:nb_pro_reach[r + 1], 2]
            for t in plot_timestep:
                fig1 = plt.figure()
                h_t = data_xhzv[t][nb_pro_reach[r]:nb_pro_reach[r + 1], 1]
                v_t = data_xhzv[t][nb_pro_reach[r]:nb_pro_reach[r + 1], 3]
                if t == -1:
                    if project_preferences['language'] == 0:
                        plt.suptitle("RUBAR1D - Last timestep ")
                    elif project_preferences['language'] == 1:
                        plt.suptitle("RUBAR1D - Dernier Pas de temps")
                else:
                    if project_preferences['language'] == 0:
                        plt.suptitle("RUBAR1D - Timestep " + str(t))
                    if project_preferences['language'] == 1:
                        plt.suptitle("RUBAR1D - Pas de Temps " + str(t))
                ax1 = plt.subplot(211)
                plt.plot(x, h_t + cote, '-b')
                plt.plot(x, cote, '-k')
                if project_preferences['language'] == 0:
                    plt.xlabel('Distance along the river [m]')
                    plt.ylabel('Elevation [m]')
                    plt.legend(('water surface', 'river bottom'), fancybox=True, framealpha=0.5)
                elif project_preferences['language'] == 1:
                    plt.xlabel('Distance le long de la rivière [m]')
                    plt.ylabel('Elevation [m]')
                    plt.legend(("surface de l'eau", 'fond de la rivière'), fancybox=True, framealpha=0.5)
                ax1 = plt.subplot(212)
                plt.plot(x, v_t, '-r')
                if project_preferences['language'] == 0:
                    plt.xlabel('Distance along the river [m]')
                    plt.ylabel('Velocity [m/sec]')
                elif project_preferences['language'] == 1:
                    plt.xlabel('Distance le long de la rivière [m]')
                    plt.ylabel('Vitesse [m/sec]')
                if format == 0 or format == 1:
                    plt.savefig(os.path.join(path_im, "rubar1D_vh_t" + str(t) + '_' + str(r) + '_' +
                                             time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'), dpi=project_preferences['resolution'],
                                transparent=True)
                if format == 0 or format == 3:
                    plt.savefig(os.path.join(path_im, "rubar1D_vh_t" + str(t) + '_' + str(r) + '_' +
                                             time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'), dpi=project_preferences['resolution'],
                                transparent=True)
                if format == 2:
                    plt.savefig(os.path.join(path_im, "rubar1D_vh_t" + str(t) + '_' + str(r) + '_' + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + '.jpg'), dpi=project_preferences['resolution'], transparent=True)
        elif warn_reach:
            print('Warning: Too many reaches to plot them all. Only the ten first reaches plotted. \n')
            warn_reach = False

    # plt.show()


def load_rubar2d_and_create_grid(name_hdf5, geofile, tpsfile, pathgeo, pathtps, path_im, name_prj, path_prj, model_type,
                                 nb_dim, progress_value, path_hdf5, q=[], print_cmd=False, project_preferences={}):
    """
    This is the function used to load the RUBAR data in 2D, to pass the data from the cell to the node using
    interpolation and to save the whole in an hdf5 format

    :param name_hdf5: the base name of the created hdf5 (string)
    :param geofile: the name of the .mai or .dat file which contains the connectivity table and the coordinates (string)
    :param tpsfile: the name of the .tps file (string)
    :param pathgeo: path to the geo file (string)
    :param pathtps: path to the tps file which contains the outputs (string)
    :param path_im: the path where to save the figure (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param q: used by the second thread to get the error back to the GUI at the end of the thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param project_preferences: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    """

    # minimum water height
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    minwh = project_preferences['min_height_hyd']

    # progress
    progress_value.value = 10

    # create the empy output
    inter_vel_all_t = []
    inter_h_all_t = []
    ikle_all_t = []
    point_all_t = []
    point_c_all_t = []

    # load data
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    [vel_cell, height_cell, coord_p, coord_c, ikle_base, timestep] \
        = load_rubar2d(geofile, tpsfile, pathgeo, pathtps, path_im, False)  # True to get figure

    if vel_cell == [-99]:
        print('Error: Rubar data not loaded.')
        sys.stdout = sys.__stdout__
        if q:
            q.put(mystdout)
            return
        else:
            return

    # create grid
    # first, the grid for the whole profile (no velcoity or height data)
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
            [vel_node, height_node, vtx_all, wts_all] = manage_grid_mod.pass_grid_cell_to_node_lin([coord_p],
                                                                                                   [coord_c], vel_cell[t],
                                                                                                   height_cell[t], warn1)
        else:
            [vel_node, height_node, vtx_all, wts_all] = manage_grid_mod.pass_grid_cell_to_node_lin([coord_p], [coord_c],
                                                                                                   vel_cell[t],
                                                                                                   height_cell[t], warn1,
                                                                                                   vtx_all, wts_all)
        # cut the grid to the water limit
        # [ikle, point_all, water_height, velocity] = manage_grid_mod.cut_2d_grid(ikle_base, coord_p, height_node[0],
        #                                                                         vel_node[0], minwh)
        #
        # inter_h_all_t.append([water_height])
        # inter_vel_all_t.append([velocity])
        # point_all_t.append([point_all])
        # point_c_all_t.append([[]])
        # ikle_all_t.append([ikle])
        inter_h_all_t.append([height_node[0]])
        inter_vel_all_t.append([vel_node[0]])
        point_all_t.append([coord_p])
        point_c_all_t.append([[]])
        ikle_all_t.append([ikle_base])
        warn1 = False

    # save data
    # timestep_str = list(map(str, timestep))
    # hdf5_mod.save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5, ikle_all_t,
    #                                  point_all_t, point_c_all_t,
    #                                  inter_vel_all_t, inter_h_all_t, sim_name=timestep_str, hdf5_type="hydraulic")

        # hyd description
        hyd_description = dict()
        hyd_description["hyd_filename_source"] = geofile
        hyd_description["hyd_model_type"] = "RUBAR2D"
        hyd_description["hyd_model_dimension"] = 2
        hyd_description["hyd_variables_list"] = "h, v, z"
        hyd_description["hyd_epsg_code"] = description_from_indextelemac_file[hyd_file]["epsg_code"]
        hyd_description["hyd_reach_list"] = description_from_indextelemac_file[hyd_file]["reach_list"]
        hyd_description["hyd_reach_number"] = description_from_indextelemac_file[hyd_file]["reach_number"]
        hyd_description["hyd_reach_type"] = description_from_indextelemac_file[hyd_file]["reach_type"]
        hyd_description["hyd_unit_list"] = description_from_indextelemac_file[hyd_file]["unit_list"]
        hyd_description["hyd_unit_number"] = description_from_indextelemac_file[hyd_file]["unit_number"]
        hyd_description["hyd_unit_type"] = description_from_indextelemac_file[hyd_file]["unit_type"]
        hyd_description["hyd_varying_mesh"] = str(data_2d_whole_profile["unit_correspondence"])
        hyd_description["hyd_unit_z_equal"] = description_from_telemac_file["hyd_unit_z_equal"]

        # create hdf5
        hdf5 = hdf5_mod.Hdf5Management(description_from_indextelemac_file[hyd_file]["path_prj"],
                                       description_from_indextelemac_file[hyd_file]["hdf5_name"])
        hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description)

    # progress
    progress_value.value = 90
    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
    else:
        return


def load_rubar2d(geofile, tpsfile, pathgeo, pathtps, path_im, save_fig):
    """
    This is the function used to load the RUBAR data in 2D.

    :param geofile: the name of the .mai or .dat file which contains the connectivity table and the coordinates (string)
    :param tpsfile: the name of the .tps file (string)
    :param pathgeo: path to the geo file (string)
    :param pathtps: path to the tps file which contains the outputs (string)
    :param path_im: the path where to save the figure (string)
    :param save_fig: a boolean indicating if the figures should be created or not
    :return: velocity and height at the center of the cells, the coordinate of the point of the cells,
             the coordinates of the center of the cells and the connectivity table.
    """

    blob, ext = os.path.splitext(geofile)
    if ext == '.mai':
        [ikle, xy, coord_c, nb_cell] = load_mai_2d(geofile, pathgeo)
    elif ext == '.dat':
        [ikle, xy, coord_c, nb_cell] = load_dat_2d(geofile, pathgeo)
    else:
        return [-99], [-99], [-99], [-99], [-99], [-99]
    [timestep, h, v] = load_tps_2d(tpsfile, pathtps, nb_cell)
    [ikle, coord_c, xy, h, v] = get_triangular_grid(ikle, coord_c, xy, h, v)
    if save_fig:
        figure_rubar2d(xy, coord_c, ikle, v, h, path_im, [-1])

    return v, h, xy, coord_c, ikle, timestep


def load_mai_2d(geofile, path):
    """
    The function to load the geomtery info for the 2D case when we use the .mai file. It would also be possible
    to use the .dat file. In fact, it is advised to use the dat file when possible as there are more info in the .dat file.

    :param geofile: the .mai file which contain the connectivity table and the (x,y)
    :param path: the path to this file
    :return: connectivity table, point coordinates, coordinates of the cell centers
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
        ind_l = np.zeros(len(data_l) - 1, dtype=np.int)
        for i in range(0, len(data_l) - 1):
            try:
                ind_l[i] = int(data_l[i + 1]) - 1
            except ValueError:
                print('Error: Could not extract the connectivity table from the .mai file.\n')
                return [-99], [-99], [-99], [-99]
        ikle.append(ind_l)

    if len(ikle) != nb_cell + 1:
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
        coord_c.append(xy_c / len(ikle_c))

    return ikle, xy, coord_c, nb_cell


def load_dat_2d(geofile, path):
    """
    This  function is used to load the geomtery info for the 2D case, using the .dat file
    The .dat file has the same role than the .mai file but with more information (number of side and more
    complicated connectivity table).

    :param geofile: the .dat file which contain the connectivity table and the (x,y)
    :param path: the path to this file
    :return: connectivity table, point coordinates, coordinates of the cell centers
    """
    filename_path = os.path.join(path, geofile)
    # check extension
    blob, ext = os.path.splitext(geofile)
    if ext != '.dat':
        print('Warning: The fils does not seem to be of .dat type.\n')
    # check if the file exist
    if not os.path.isfile(filename_path):
        print('Error: The .dat file does not exist.')
        return [-99], [-99], [-99], [-99]
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_geo2d = f.read()
    except IOError:
        print('Error: The .dat file can not be open.\n')
        return [-99], [-99], [-99], [-99]
    data_geo2d = data_geo2d.splitlines()
    # extract nb cells
    try:
        nb_cell = np.int(data_geo2d[0])
    except ValueError:
        print('Error: Could not extract the number of cells from the .dat file.\n')
        return [-99], [-99], [-99], [-99]
        nb_cell = 0
    # extract connectivity table, not always triangle
    # in the .dat file we want only one line out for three
    data_l = data_geo2d[1].split()
    m2 = 2
    m = 1
    ikle = []
    while m < nb_cell * 3:
        if m >= len(data_geo2d):
            print('Error: Could not extract the connectivity table from the .dat file.\n')
            return [-99], [-99], [-99], [-99]
        data_l = data_geo2d[m].split()
        if m2 == m:
            ind_l = np.zeros(len(data_l) - 1, dtype=np.int)
            for i in range(0, len(data_l) - 1):
                try:
                    ind_l[i] = int(data_l[i + 1]) - 1
                except ValueError:
                    print('Error: Could not extract the connectivity table from the .dat file.\n')
                    return [-99], [-99], [-99], [-99]
            ikle.append(ind_l)
            m2 += 3
        m += 1

    if len(ikle) != nb_cell:
        print('Warning: some cells might be missing.\n')

    # extract the number of side (not needed)
    m += 1
    nb_side = int(data_geo2d[m])
    # and directly go to coordinate
    m += nb_side * 2 + 1

    # nb coordinates
    try:
        nb_coord = np.int(data_geo2d[m])
    except ValueError:
        print('Error: Could not extract the number of coordinates from the .dat file.\n')
        nb_coord = 0
    # extract coordinates
    data_f = []
    m += 1
    c = 0
    while c < 2 * nb_coord and c < 10 ** 8:
        data_str = data_geo2d[m]
        l = 0
        while l < len(data_str):
            try:
                data_f.append(float(data_str[l:l + 8]))  # the length of number is eight.
                l += 8
                c += 1
            except ValueError:
                print('Error: Could not extract the coordinates from the .dat file.\n')
                print(data_geo2d[mi])
                return [-99], [-99], [-99], [-99]
        m += 1
    # separe x and y
    x = data_f[0:nb_coord]  # choose every 2 float
    y = data_f[nb_coord:]
    xy = np.column_stack((x, y))

    # get z
    z_position_line = [data_geo2d[index] for index, value in enumerate(data_geo2d) if len(value) == 80]

    # find the center point of each cellss
    # slow because number of point of a cell changes
    coord_c = []

    for c in range(0, nb_cell):
        ikle_c = ikle[c]
        xy_c = [0, 0]
        for i in range(0, len(ikle_c)):
            xy_c += xy[ikle_c[i]]
        coord_c.append(xy_c / len(ikle_c))

    return ikle, xy, coord_c, nb_cell


def load_tps_2d(tpsfile, path, nb_cell):
    """
    The function to load the output data in the 2D rubar case. The geometry file (.mai or .dat) should be loaded before.

    :param tpsfile: the name of the file with the data for the 2d case
    :param path: the path to the tps file.
    :param nb_cell: the number of cell extracted from the .mai file
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
            hi = np.array(list(map(float, data_tps[i:i + nb_cell])))
            h.append(hi)
            i += nb_cell
            qve = np.array(list(map(float, data_tps[i:i + nb_cell])))
            i += nb_cell
            que = np.array(list(map(float, data_tps[i:i + nb_cell])))
            i += nb_cell
            # velocity
            hiv = np.copy(hi)
            hiv[hiv == 0] = -99  # avoid division by zeros
            if len(que) != len(qve):
                np.set_printoptions(threshold=np.inf)
            vi = np.sqrt((que / hiv) ** 2 + (qve / hiv) ** 2)
            vi[hi == 0] = 0  # get realistic again
            v.append(vi)
        except ValueError:
            print('Error: the data could not be extracted from the .tps file. Error at number ' + str(i) + '.\n')
            return [-99], [-99], [-99]

    return t, h, v


def get_triangular_grid(ikle, coord_c, xy, h, v):
    """
    In Rubar, it is possible to have non-triangular cells. It is possible to have a grid composed of a mix
    of pentagonal, 4-sided and triangualr cells. This function transform the "mixed" grid to a triangular grid. For this,
    it uses the centroid of each cell with more than three side and it create a triangle by side (linked with the
    center of the cell). A similar function exists in hec-ras2D.py, but, as there is only one reach in rubar
    and because ikle is different in hec-ras, it was hard to marge both functions together.

    :param ikle: the connectivity table (list)
    :param coord_c: the coordinate of the centroid of the cell (list)
    :param xy: the points of the grid (np.array)
    :param h: data on water height
    :param v: data on velocity
    :return: the updated ikle, coord_c (the center of the cell , must be updated ) and xy (the grid coordinate)
    """

    # this is important for speed. np.array are slow to append value
    xy = list(xy)
    h2 = []
    v2 = []
    nbtime = len(v)
    for t in range(0, nbtime):
        h2.append(list(h[t]))
        v2.append(list(v[t]))

    # now create the triangular grid
    likle = len(ikle)
    for c in range(0, likle):
        ikle_c = ikle[c]
        if len(ikle_c) == 0:
            del ikle[c]
        elif len(ikle_c) < 3:
            print('Error: A cell with an area of 0 is found.\n')
            print(ikle_c)
            return [-99], [-99], [-99], [-99], [-99]

        elif len(ikle_c) > 3:
            # the new cell is compose of triangle where one point is the centroid and two points are side of
            # the polygon which composed the cells before. The first new triangular cell take the place of the old one
            # (to avoid changing the order of ikle), the other are added at the end
            # no change to v and h for the first triangular data, change afterwards
            xy.append(coord_c[c])
            # first triangular cell
            ikle[c] = [ikle_c[0], ikle_c[1], len(xy) - 1]
            p1 = xy[len(xy) - 1]
            coord_c[c] = (xy[ikle_c[0]] + xy[ikle_c[1]] + p1) / 3
            # next triangular cell
            for s in range(1, len(ikle_c) - 1):
                ikle.append([ikle_c[s], ikle_c[s + 1], len(xy) - 1])
                coord_c.append((xy[ikle_c[s]] + xy[ikle_c[s + 1]] + p1) / 3)
                for t in range(0, nbtime):
                    v2[t].append(v[t][c])
                    h2[t].append(h[t][c])
            # last triangular cells
            ikle.append([ikle_c[-1], ikle_c[0], len(xy) - 1])
            coord_c.append((xy[ikle_c[-1]] + xy[ikle_c[0]] + p1) / 3)
            for t in range(0, nbtime):
                v2[t].append(v[t][c])
                h2[t].append(h[t][c])

    xy = np.array(xy)
    v = []
    h = []
    for t in range(0, nbtime):
        # there is an extra [] for the case where we more than one reach
        # to be corrected if we get multi-reach RUBAR simulation
        h.append([np.array(h2[t])])
        v.append([np.array(v2[t])])

    return ikle, coord_c, xy, v, h


def figure_rubar2d(xy, coord_c, ikle, v, h, path_im, time_step=[-1]):
    """
    This functions plots the rubar 2d data. This function is only used to debug. It is not used direclty by Habby.

    :param xy: coordinates of the points
    :param coord_c: the center of the point
    :param ikle: connectivity table
    :param v: speed
    :param h: height
    :param path_im: the path where to save the figure
    :param time_step: The time step which will be plotted
    """
    coord_p = np.array(xy)
    coord_c = np.array(coord_c)
    # plt.close()

    # ikle cannot be an np.array
    xlist = []
    ylist = []
    for i in range(0, len(ikle) - 1):
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
    # plt.close()  # do not forget to close or the program crash

    for t in time_step:
        # plot water depth
        h_t = np.array(h[t][0])  # 0 in case we have more than one reach
        hec_ras2D_mod.scatter_plot(coord_c, h_t, 'Water Depth [m]', 'terrain', 8, t)
        plt.savefig(
            os.path.join(path_im,
                         "rubar2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(
            os.path.join(path_im,
                         "rubar2D_waterdepth_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        # plt.close()

        # plot velocity
        vel_c0 = np.array(v[t][0])
        hec_ras2D_mod.scatter_plot(coord_c, vel_c0, 'Vel. [m/sec]', 'gist_ncar', 8, t)
        plt.savefig(
            os.path.join(path_im, "rubar2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(
            os.path.join(path_im, "rubar2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        # plt.close()

    # plt.show()


def main():
    """
    Used to test this module
    """

    # path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\2D\120_K35_K25_K20\120_K35_K25_K20'
    # geofile2d='BS15a6.mai'
    # tpsfile = 'BS15a6.tps'
    # #path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\trubarbe\aval07'
    # #geofile2d = 'aval07.dat'
    # #tpsfile = 'aval07.tps'
    # #path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\belcastel201106\sect2b14'
    # #geofile2d = 'sect2b.dat'
    # #tpsfile = 'sect2b.tps'
    # load_rubar2d(geofile2d,tpsfile, path, pat    #mail = 'mail.LE13'h, path, True)
    #
    path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\1D\LE2013\LE2013\LE13'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'

    geofile = 'LE13.rbe'
    data = 'profil.LE13'

    # path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\trubarbe\1D\RubarBE_four_0'
    # geofile = r'four.rbe'
    # geofile = 'm.four'
    # data = r'profil.four'

    # path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\trubarbe\b120'
    # geofile = 'm.b120'
    # data = 'profil.b120'
    # mail = 'mail.b120'
    load_rubar1d(geofile, data, path, path, path_im, True)


if __name__ == '__main__':
    main()
