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
import time
import xml.etree.ElementTree as Etree
from copy import deepcopy
from io import StringIO

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QCoreApplication as qt_tr

from src import dist_vistess_mod
from src import hdf5_mod
from src import hec_ras2D_mod
from src import manage_grid_mod
from src.dev_tools import profileit
from src.project_manag_mod import load_project_preferences
from src_GUI import preferences_GUI
from src.user_preferences_mod import user_preferences


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

    project_preferences = load_project_preferences(path_prj, name_prj)
    [xhzv_data, coord_pro, lim_riv, timestep] = load_rubar1d(namefile[0], namefile[1], pathfile[0], pathfile[1],
                                                             path_im,
                                                             show_fig_1D, project_preferences)
    if show_fig_1D:
        plt.close()  # just save the figure do not show them

    if xhzv_data == [-99]:
        print(qt_tr.translate("rubar1d2d_mod", "Rubar data could not be loaded."))
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
                    print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The number of profile is not the same in the geo file and the data file. \n'))

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
        print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The fils does not seem to be of .rbe type.\n'))
    # load the XML file
    if not os.path.isfile(filename_path):
        print('Error: the .reb file does not exist.\n')
        return [-99], [-99], [-99], [-99]
    try:
        docxml = Etree.parse(filename_path)
        root = docxml.getroot()
    except IOError:
        print("Error: " + qt_tr.translate("rubar1d2d_mod", "the .rbe file cannot be open.\n"))
        return [-99], [-99], [-99], [-99]
    # read the section data
    try:  # check that the data is not empty
        jeusect = root.findall(".//Sections.JeuSection")
        sect = jeusect[0].findall(".//Sections.Section")
    except AttributeError:
        print("Error: " + qt_tr.translate("rubar1d2d_mod", "Sections data cannot be read from the .rbe file\n"))
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
            print("Error: " + qt_tr.translate("rubar1d2d_mod", "Point data cannot be read from the .rbe file\n"))
            return [], [], []
        try:
            name_profile.append(sect[i].attrib['nom'])
        except KeyError:
            print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The name of the profile could not be extracted from the .reb file.\n'))
        try:
            x = sect[i].attrib['Pk']  # nthis is hte distance along the river, not along the profile
            dist_riv.append(np.float(x))
        except KeyError:
            print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The name of the profile could not be extracted from the .reb file.\n'))
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
            print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The position of the river is not found in the .rbe file.\n'))
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
            print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'First indices is identical to another. Unlogical. \n'))
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
                print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'Vertical profile. One or more profiles were modified. \n'))
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
    if format == 0:
        plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.pdf'), dpi=project_preferences['resolution'], transparent=True)
    if format == 1:
        plt.savefig(os.path.join(path_im, "rubar1D_profile_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                 '.png'), dpi=project_preferences['resolution'], transparent=True)
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
            print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'Too many reaches to plot them all. Only the ten first reaches plotted. \n'))
            warn_reach = False

    # plt.show()


def load_rubar2d_and_create_grid(hydrau_description, progress_value, q=[], print_cmd=False, project_preferences={}):
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
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    file_path = hydrau_description["path_filename_source"]
    filename = hydrau_description["filename_source"]

    # minimum water height
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    minwh = project_preferences['min_height_hyd']

    # progress
    progress_value.value = 5

    # load data from txt file
    data_2d_from_rubar2d, description_from_rubar2d = load_rubar2d(filename, file_path, progress_value)
    if not data_2d_from_rubar2d and not description_from_rubar2d:
        q.put(mystdout)
        return

    # progress
    progress_value.value = 10

    # create copy
    data_2d_whole_profile = dict()
    data_2d_whole_profile["mesh"] = dict()
    data_2d_whole_profile["node"] = dict()
    data_2d_whole_profile["mesh"]["tin"] = [[data_2d_from_rubar2d["tin"]]]
    data_2d_whole_profile["node"]["xy"] = [[data_2d_from_rubar2d["xy"]]]
    data_2d_whole_profile["node"]["z"] = [[data_2d_from_rubar2d["z"]]]

    # create empty dict
    data_2d = dict()
    data_2d["mesh"] = dict()
    data_2d["node"] = dict()
    data_2d["mesh"]["tin"] = []
    data_2d["mesh"]["i_whole_profile"] = []
    data_2d["node"]["xy"] = []
    data_2d["node"]["h"] = []
    data_2d["node"]["v"] = []
    data_2d["node"]["z"] = []

    # progress from 10 to 90 : from 0 to len(units_index)
    delta = int(80 / int(description_from_rubar2d["unit_number"]))

    # for each reach
    for reach_num in range(int(description_from_rubar2d["reach_number"])):
        data_2d["mesh"]["tin"].append([])
        data_2d["mesh"]["i_whole_profile"].append([])
        data_2d["node"]["xy"].append([])
        data_2d["node"]["h"].append([])
        data_2d["node"]["v"].append([])
        data_2d["node"]["z"].append([])

        # index to remove (from user selection GUI)
        index_to_remove = []

        # for each units
        description_from_rubar2d["unit_list"] = [description_from_rubar2d["unit_list"].split(", ")]
        for unit_num in range(len(description_from_rubar2d["unit_list"][reach_num])):
            # get unit from according to user selection
            if hydrau_description["unit_list_tf"][reach_num][unit_num]:

                # conca xy with z value to facilitate the cutting of the grid (interpolation)
                xy = np.insert(data_2d_from_rubar2d["xy"],
                               2,
                               values=data_2d_from_rubar2d["z"],
                               axis=1)  # Insert values before column 2

                # remove mesh dry and cut partialy dry in option
                tin_data, xy_cuted, h_data, v_data, i_whole_profile = manage_grid_mod.cut_2d_grid(
                    data_2d_from_rubar2d["tin"],
                    xy,
                    data_2d_from_rubar2d["h"][reach_num][unit_num],
                    data_2d_from_rubar2d["v"][reach_num][unit_num],
                    progress_value,
                    delta,
                    project_preferences["CutMeshPartialyDry"],
                    minwh)

                if not isinstance(tin_data, np.ndarray):  # error or warning
                    if not tin_data:  # error
                        print("Error: " + qt_tr.translate("rubar1d2d_mod", "cut_2d_grid"))
                        q.put(mystdout)
                        return
                    elif tin_data:   # entierly dry
                        hydrau_description["unit_list_tf"][reach_num][unit_num] = False
                        print("Warning: " + qt_tr.translate("rubar1d2d_mod", "The mesh of timestep ") + description_from_rubar2d["unit_list"][reach_num][unit_num] + qt_tr.translate("rubar1d2d_mod", " is entirely dry."))
                        continue  # Continue to next iteration.
                else:
                    # get cuted grid
                    data_2d["mesh"]["tin"][reach_num].append(tin_data)
                    data_2d["mesh"]["i_whole_profile"][reach_num].append(i_whole_profile)
                    data_2d["node"]["xy"][reach_num].append(xy_cuted[:, :2])
                    data_2d["node"]["h"][reach_num].append(h_data)
                    data_2d["node"]["v"][reach_num].append(v_data)
                    data_2d["node"]["z"][reach_num].append(xy_cuted[:, 2])

            # erase unit
            else:
                index_to_remove.append(unit_num)

        # index to remove (from user selection GUI)
        for index in reversed(index_to_remove):
            data_2d_whole_profile["mesh"]["tin"][reach_num].pop(index)
            data_2d_whole_profile["node"]["xy"][reach_num].pop(index)
            data_2d_whole_profile["node"]["z"][reach_num].pop(index)

    # refresh unit (if unit mesh entirely dry)
    for reach_num in reversed(range(int(description_from_rubar2d["reach_number"]))):  # for each reach
        for unit_num in reversed(range(len(description_from_rubar2d["unit_list"][reach_num]))):
            if not hydrau_description["unit_list_tf"][reach_num][unit_num]:
                description_from_rubar2d["unit_list"][reach_num].pop(unit_num)
    description_from_rubar2d["unit_number"] = str(len(description_from_rubar2d["unit_list"][0]))

    # ALL CASE SAVE TO HDF5
    progress_value.value = 90  # progress

    # hyd description
    hyd_description = dict()
    hyd_description["hyd_filename_source"] = description_from_rubar2d["filename_source"]
    hyd_description["hyd_model_type"] = description_from_rubar2d["model_type"]
    hyd_description["hyd_model_dimension"] = description_from_rubar2d["model_dimension"]
    hyd_description["hyd_variables_list"] = "h, v, z"
    hyd_description["hyd_epsg_code"] = "unknown"
    hyd_description["hyd_reach_list"] = "unknown"
    hyd_description["hyd_reach_number"] = description_from_rubar2d["reach_number"]
    hyd_description["hyd_reach_type"] = "river"
    hyd_description["hyd_unit_list"] = description_from_rubar2d["unit_list"]
    hyd_description["hyd_unit_number"] = description_from_rubar2d["unit_number"]
    hyd_description["hyd_unit_type"] = description_from_rubar2d["unit_type"]
    hyd_description["hyd_cuted_mesh_partialy_dry"] = str(project_preferences["CutMeshPartialyDry"])

    hyd_description["hyd_varying_mesh"] = False
    if hyd_description["hyd_varying_mesh"]:
        hyd_description["hyd_unit_z_equal"] = False
    else:
        # TODO : check if all z values are equal between units
        hyd_description["hyd_unit_z_equal"] = True

    # create hdf5
    hdf5 = hdf5_mod.Hdf5Management(project_preferences["path_prj"],
                                   hydrau_description["hdf5_name"])
    hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description, project_preferences)

    # progress
    progress_value.value = 100
    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
    else:
        return


def load_rubar2d(filename, file_path, progress_value):
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

    pathgeo = file_path
    pathtps = file_path
    geofile = filename + ".dat"
    tpsfile = filename + ".tps"

    # DAT
    ikle, xyz, nb_cell = load_dat_2d(geofile, pathgeo)   # node
    progress_value.value = 6

    # TPS
    timestep, h, v = load_tps_2d(tpsfile, pathtps, nb_cell)   # cell
    progress_value.value = 7

    # QUADRANGLE TO TRIANGLE
    # ikle, coord_c, xy, h, v, z = get_triangular_grid(ikle, coord_c, xy, h, v, z)
    ikle, xyz, h, v = manage_grid_mod.finite_volume_to_finite_element_triangularxy(ikle, xyz, h, v)

    # description telemac data dict
    description_from_file = dict()
    description_from_file["filename_source"] = geofile + "; " + tpsfile
    description_from_file["model_type"] = "RUBAR2D"
    description_from_file["model_dimension"] = str(2)
    description_from_file["unit_list"] = ", ".join(list(map(str, timestep)))
    description_from_file["unit_number"] = str(len(list(map(str, timestep))))
    description_from_file["unit_type"] = "timestep [s]"
    description_from_file["unit_z_equal"] = True
    description_from_file["reach_number"] = "1"

    # reset to list and separate xy to z
    h_list = []
    v_list = []
    for timestep_index in range(len(timestep)):
        h_list.append(h[:, timestep_index])
        v_list.append(v[:, timestep_index])
    xy = xyz[:, (0, 1)]
    z = xyz[:, 2]

    # data 2d dict
    data_2d = dict()
    data_2d["h"] = [h_list]
    data_2d["v"] = [v_list]
    data_2d["z"] = z
    data_2d["xy"] = xy
    data_2d["tin"] = ikle

    return data_2d, description_from_file


# def load_mai_2d(geofile, path):
#     """
#     The function to load the geomtery info for the 2D case when we use the .mai file. It would also be possible
#     to use the .dat file. In fact, it is advised to use the dat file when possible as there are more info in the .dat file.
#
#     :param geofile: the .mai file which contain the connectivity table and the (x,y)
#     :param path: the path to this file
#     :return: connectivity table, point coordinates, coordinates of the cell centers
#     """
#     filename_path = os.path.join(path, geofile)
#     # check extension
#     blob, ext = os.path.splitext(geofile)
#     if ext != '.mai':
#         print('Warning: The fils does not seem to be of .mai type.\n')
#     # check if the file exist
#     if not os.path.isfile(filename_path):
#         print('Error: The .mai file does not exist.')
#         return [-99], [-99], [-99], [-99]
#     # open file
#     try:
#         with open(filename_path, 'rt') as f:
#             data_geo2d = f.read()
#     except IOError:
#         print('Error: The .mai file can not be open.\n')
#         return [-99], [-99], [-99], [-99]
#     data_geo2d = data_geo2d.splitlines()
#     # extract nb cells
#     try:
#         nb_cell = np.int(data_geo2d[0])
#     except ValueError:
#         print('Error: Could not extract the number of cells from the .mai file.\n')
#         return [-99], [-99], [-99], [-99]
#         nb_cell = 0
#     # extract connectivity table, not always triangle
#     data_l = data_geo2d[1].split()
#     m = 0
#     ikle = []
#     while len(data_l) > 1:
#         m += 1
#         if m == len(data_geo2d):
#             print('Error: Could not extract the connectivity table from the .mai file.\n')
#             return [-99], [-99], [-99], [-99]
#         data_l = data_geo2d[m].split()
#         ind_l = np.zeros(len(data_l) - 1, dtype=np.int)
#         for i in range(0, len(data_l) - 1):
#             try:
#                 ind_l[i] = int(data_l[i + 1]) - 1
#             except ValueError:
#                 print('Error: Could not extract the connectivity table from the .mai file.\n')
#                 return [-99], [-99], [-99], [-99]
#         ikle.append(ind_l)
#
#     if len(ikle) != nb_cell + 1:
#         print('Warning: some cells might be missing.\n')
#     # nb coordinates
#     try:
#         nb_coord = np.int(data_geo2d[m])
#     except ValueError:
#         print('Error: Could not extract the number of coordinates from the .mai file.\n')
#         nb_coord = 0
#     # extract coordinates
#     data_f = []
#     m += 1
#     for mi in range(m, len(data_geo2d)):
#         data_str = data_geo2d[mi]
#         l = 0
#         while l < len(data_str):
#             try:
#                 data_f.append(float(data_str[l:l + 8]))  # the length of number is eight.
#                 l += 8
#             except ValueError:
#                 print('Error: Could not extract the coordinates from the .mai file.\n')
#                 return [-99], [-99], [-99], [-99]
#     # separe x and z
#     x = data_f[0:nb_coord]  # choose every 2 float
#     y = data_f[nb_coord:]
#     xy = np.column_stack((x, y))
#
#     # find the center point of each cell
#     # slow because number of point of a cell changes
#     coord_c = []
#     for c in range(0, nb_cell):
#         ikle_c = ikle[c]
#         xy_c = [0, 0]
#         for i in range(0, len(ikle_c)):
#             xy_c += xy[ikle_c[i]]
#         coord_c.append(xy_c / len(ikle_c))
#
#     return ikle, xy, coord_c, nb_cell


def wrap(s, w):
    """
    Divide a string in fixed length
    :param s: the string to divide
    :param w: the length
    :return: a list of substrings
    """
    return [s[i:i + w] for i in range(0, len(s), w)]


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
        print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The fils does not seem to be of .dat type.\n'))
    # check if the file exist
    if not os.path.isfile(filename_path):
        print('Error: The .dat file does not exist.')
        return [-99], [-99], [-99], [-99], [-99]
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_geo2d = f.read()
    except IOError:
        print('Error: The .dat file can not be open.\n')
        return [-99], [-99], [-99], [-99], [-99]
    data_geo2d = data_geo2d.splitlines()
    # extract nb cells
    try:
        nb_cell = np.int(data_geo2d[0])
    except ValueError:
        print('Error: Could not extract the number of cells from the .dat file.\n')
        return [-99], [-99], [-99], [-99], [-99]
        nb_cell = 0
    # extract connectivity table, not always triangle
    # in the .dat file we want only one line out for three
    data_l = data_geo2d[1].split()
    m2 = 2
    m = 1
    ikle = np.empty((nb_cell, 4), dtype=np.int)
    ikle_list = []
    while m < nb_cell * 3:
        if m >= len(data_geo2d):
            print('Error: Could not extract the connectivity table from the .dat file.\n')
            return [-99], [-99], [-99], [-99], [-99]
        # data_l = data_geo2d[m].split()
        # data_l = data_geo2d[m].split()
        data_l = wrap(data_geo2d[m], 6)
        if m2 == m:
            ind_l = np.array([-1] * 4, dtype=np.int)
            for i in range(0, len(data_l) - 1):
                try:
                    ind_l[i] = int(data_l[i + 1]) - 1
                except ValueError:
                    print('Error: Could not extract the connectivity table from the .dat file.\n')
                    return [-99], [-99], [-99], [-99], [-99]
            ikle_list.append(ind_l)
            ikle[int((m2 - 2) / 3)] = ind_l
            m2 += 3
        m += 1

    if len(ikle) != nb_cell:
        print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'Some cells might be missing.\n'))

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
    while c < 3 * nb_coord and c < 10 ** 8:
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
                return [-99], [-99], [-99], [-99], [-99]
        m += 1
    # merge x and y
    x = data_f[0:nb_coord]  # choose every 2 float
    y = data_f[nb_coord:2*nb_coord]
    z = data_f[2*nb_coord:]
    xyz = np.column_stack((x, y, z))
    ikle = np.asarray(ikle)
    return ikle, xyz, nb_cell


# @profileit
# def load_tps_2d(tpsfile, path, nb_cell):
#     """
#     The function to load the output data in the 2D rubar case. The geometry file (.mai or .dat) should be loaded before.
#
#     :param tpsfile: the name of the file with the data for the 2d case
#     :param path: the path to the tps file.
#     :param nb_cell: the number of cell extracted from the .mai file
#     :return: v, h, timestep (all in list of np.array)
#     """
#     filename_path = os.path.join(path, tpsfile)
#     # check extension
#     blob, ext = os.path.splitext(tpsfile)
#     if ext != '.tps':
#         print('Warning: The fils does not seem to be of .tps type.\n')
#     # open file
#     try:
#         with open(filename_path, 'rt') as f:
#             data_tps = f.read()
#     except IOError:
#         print('Error: The .tps file does not exist.\n')
#         return [-99], [-99], [-99]
#     data_tps = data_tps.split()
#     # get data and transform into float
#     i = 0
#     t = []
#     h = []
#     v = []
#     while i < len(data_tps):
#         try:
#             # time
#             ti = np.float(data_tps[i])
#             t.append(ti)
#             i += 1
#             hi = np.array(list(map(float, data_tps[i:i + nb_cell])))
#             h.append(hi)
#             i += nb_cell
#             qve = np.array(list(map(float, data_tps[i:i + nb_cell])))
#             i += nb_cell
#             que = np.array(list(map(float, data_tps[i:i + nb_cell])))
#             i += nb_cell
#             # velocity
#             hiv = np.copy(hi)
#             hiv[hiv == 0] = -99  # avoid division by zeros
#             if len(que) != len(qve):
#                 np.set_printoptions(threshold=np.inf)
#             vi = np.sqrt((que / hiv) ** 2 + (qve / hiv) ** 2)
#             vi[hi == 0] = 0  # get realistic again
#             v.append(vi)
#         except ValueError:
#             print('Error: the data could not be extracted from the .tps file. Error at number ' + str(i) + '.\n')
#             return [-99], [-99], [-99]
#
#     return t, h, v

# @profileit
# def load_tps_2d(tpsfile, path, nb_cell):
#     """
#     The function to load the output data in the 2D rubar case. The geometry file (.mai or .dat) should be loaded before.
#
#     :param tpsfile: the name of the file with the data for the 2d case
#     :param path: the path to the tps file.
#     :param nb_cell: the number of cell extracted from the .mai file
#     :return: v, h, timestep (all in list of np.array)
#     """
#     filename_path = os.path.join(path, tpsfile)
#     # check extension
#     blob, ext = os.path.splitext(tpsfile)
#     if ext != '.tps':
#         print('Warning: The fils does not seem to be of .tps type.\n')
#     # open file
#     try:
#         with open(filename_path, 'rt') as f:
#             data_tps = f.read()
#     except IOError:
#         print('Error: The .tps file does not exist.\n')
#         return [-99], [-99], [-99]
#     data_tps_splited = data_tps.split()
#
#     # get data and transform into float
#     total_element = len(data_tps_splited)
#     i = 0
#     t = []
#     h = []
#     qve = []
#     que = []
#     v = []
#     while i < total_element:
#         try:
#             # time
#             ti = data_tps_splited[i]
#             t.append(ti)
#             i += 1
#             hi = data_tps_splited[i:i + nb_cell]
#             h.append(hi)
#             i += nb_cell
#             qvei = data_tps_splited[i:i + nb_cell]
#             qve.append(qvei)
#             i += nb_cell
#             quei = data_tps_splited[i:i + nb_cell]
#             que.append(quei)
#             i += nb_cell
#         except ValueError:
#             print('Error: the data could not be extracted from the .tps file. Error at number ' + str(i) + '.\n')
#             return [-99], [-99], [-99]
#
#     h = np.asarray(h, dtype=np.float)
#     qve = np.asarray(qve, dtype=np.float)
#     que = np.asarray(que, dtype=np.float)
#     # compute velocity
#     hiv = np.copy(h)
#     hiv[hiv == 0] = -99  # avoid division by zeros
#     if len(que) != len(qve):
#         np.set_printoptions(threshold=np.inf)
#     vi = np.sqrt((que / hiv) ** 2 + (qve / hiv) ** 2)
#     vi[hi == 0] = 0  # get realistic again
#
#     return t, h, v


# @profileit
# def load_tps_2d(tpsfile, path, nb_cell):
#     """
#     The function to load the output data in the 2D rubar case. The geometry file (.mai or .dat) should be loaded before.
#
#     :param tpsfile: the name of the file with the data for the 2d case
#     :param path: the path to the tps file.
#     :param nb_cell: the number of cell extracted from the .mai file
#     :return: v, h, timestep (all in list of np.array)
#     """
#     filename_path = os.path.join(path, tpsfile)
#     # check extension
#     blob, ext = os.path.splitext(tpsfile)
#     if ext != '.tps':
#         print('Warning: The fils does not seem to be of .tps type.\n')
#     # open file
#     try:
#         with open(filename_path, 'rt') as f:
#             data_tps = f.read()
#     except IOError:
#         print('Error: The .tps file does not exist.\n')
#         return [-99], [-99], [-99]
#     data_tps_splited = data_tps.strip().split("\n")
#
#     # get timestep
#     timestep_list = []
#     timestep_index_list = []
#     for line_index, line_str in enumerate(data_tps_splited):
#         if len(line_str) < 30 and line_str != "":  # get timestep
#             timestep_list.append(line_str.strip())
#             timestep_index_list.append(line_index)  # remove timestep to list
#
#     # remove timestep lines
#     for timestep_index in reversed(timestep_index_list):
#         data_tps_splited.pop(timestep_index)
#
#     line_block_len = int(len(data_tps_splited) / len(timestep_list))
#     line_block_variable_len = int(line_block_len / 3)
#
#     # get raw data
#     hi = []
#     qve = []
#     que = []
#     start = -line_block_len
#     for _ in timestep_list:  # for each timestep
#         start += line_block_len
#         end = start + line_block_len
#         block_timestep = data_tps_splited[start:end]
#         hi_timestep = []
#         qve_timestep = []
#         que_timestep = []
#         for line_index in range(line_block_variable_len):  # for each block_variable
#             hi_timestep.extend([block_timestep[0:line_block_variable_len * 2][line_index][i:i+10] for i in range(0, len(block_timestep[0:line_block_variable_len * 2][line_index]), 10)])  # split all 10 character (because they can be stuck together)
#             qve_timestep.extend([block_timestep[line_block_variable_len:line_block_variable_len * 2][line_index][i:i+10] for i in range(0, len(block_timestep[line_block_variable_len:line_block_variable_len * 2][line_index]), 10)])
#             que_timestep.extend([block_timestep[line_block_variable_len:line_block_variable_len * 3][line_index][i:i+10] for i in range(0, len(block_timestep[line_block_variable_len:line_block_variable_len * 3][line_index]), 10)])
#         hi.append(hi_timestep)
#         qve.append(qve_timestep)
#         que.append(que_timestep)
#
#     # convert to numpy
#     hi = np.asarray(hi, dtype=np.float)
#     qve = np.asarray(qve, dtype=np.float)
#     que = np.asarray(que, dtype=np.float)
#
#     # compute velocity
#     hiv = np.copy(hi)
#     hiv[hiv == 0] = -99  # avoid division by zeros
#     if len(que) != len(qve):
#         np.set_printoptions(threshold=np.inf)
#     #vi = np.sqrt((que / hiv) ** 2 + (qve / hiv) ** 2)
#     vi = np.sqrt(que ** 2 + qve ** 2) / hiv
#     vi[hi == 0] = 0  # get realistic again
#
#     # convert to list
#     h = []
#     v = []
#     for timestep_index, _ in enumerate(timestep_list):  # for each timestep
#         h.append(hi[timestep_index])
#         v.append(vi[timestep_index])
#
#     return timestep_list, h, v


#@profileit
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
        print('Warning: ' + qt_tr.translate("rubar1d2d_mod", 'The fils does not seem to be of .tps type.\n'))
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_tps = f.read()
    except IOError:
        print('Error: The .tps file does not exist.\n')
        return [-99], [-99], [-99]
    data_tps_splited = data_tps.split("\n")

    # write temp file and get timestep
    path_stat = user_preferences.user_preferences_temp_path
    file_temp = open(os.path.join(path_stat, tpsfile), "w")
    timestep_list = []
    for line_index, line_str in enumerate(data_tps_splited):
        if len(line_str) == 80:  # write normal lines
            file_temp.write(line_str + "\n")
        elif len(line_str) == 15:
            timestep_list.append(line_str.strip())
        else:  # write ajusted lines
            char_missing = 80 - len(line_str)
            line_str = line_str + char_missing * "*" + "\n"
            file_temp.write(line_str)
    file_temp.close()

    # read temp file
    data_tps_array = np.genfromtxt(os.path.join(path_stat, tpsfile),
                       delimiter=10,
                       missing_values="*" * 10,
                       filling_values=np.nan)

    # remove nan and flatten
    data_tps_array = data_tps_array[~np.isnan(data_tps_array)]

    # create array and compute velocity
    h_array = np.empty((int(data_tps_array.shape[0] / nb_cell / 3), nb_cell), dtype=np.float)
    qve_array = np.empty((int(data_tps_array.shape[0] / nb_cell / 3), nb_cell), dtype=np.float)
    que_array = np.empty((int(data_tps_array.shape[0] / nb_cell / 3), nb_cell), dtype=np.float)

    start = 0
    end = nb_cell
    for timestep_index, timestep in enumerate(timestep_list):
        h_array[timestep_index] = data_tps_array[start:end]
        start += nb_cell
        end += nb_cell
        qve_array[timestep_index] = data_tps_array[start:end]
        start += nb_cell
        end += nb_cell
        que_array[timestep_index] = data_tps_array[start:end]
        start += nb_cell
        end += nb_cell

    # compute velocity
    hiv = np.copy(h_array)
    hiv[hiv == 0] = -99  # avoid division by zeros
    if len(que_array) != len(qve_array):
        np.set_printoptions(threshold=np.inf)
    v_array = np.sqrt(que_array ** 2 + qve_array ** 2) / hiv
    v_array[h_array == 0] = 0  # get realistic again

    h_array = h_array.transpose()
    v_array = v_array.transpose()

    return timestep_list, h_array, v_array


def get_time_step(filename_without_extension, path):
    """
    The function to load the output data in the 2D rubar case. The geometry file (.mai or .dat) should be loaded before.

    :param tpsfile: the name of the file with the data for the 2d case
    :param path: the path to the tps file.
    :param nb_cell: the number of cell extracted from the .mai file
    :return: v, h, timestep (all in list of np.array)
    """
    # warning_list
    warning_list = []
    # get time step
    tpsfile = os.path.splitext(filename_without_extension)[0] + ".tps"
    filename_path = os.path.join(path, tpsfile)
    # open file
    try:
        with open(filename_path, 'rt') as f:
            data_tps = f.read()
    except IOError:
        warning_list.append('Error: The .tps file does not exist.\n')
        return [-99], [-99], [-99]
    data_tps_splited = data_tps.split("\n")

    # get timestep and timestep_index
    timestep_list = []
    timestep_index_list = []
    last_line_timestep_len = []
    for line_index, line_str in enumerate(data_tps_splited):
        if len(line_str) == 15:  # timestep
            timestep_list.append(line_str.strip())
            timestep_index_list.append(line_index)
            if len(timestep_list) > 1:
                last_line_timestep_len.append(len(data_tps_splited[line_index - 1]))

    if len(timestep_list) > 1:
        # get timestep_index_step
        timestep_index_step = timestep_index_list[1] - timestep_index_list[0]

        # get last line len (if crash : line(s) are missing)
        try:
            last_line_timestep_len.append(len(data_tps_splited[timestep_index_list[-1] + timestep_index_step - 1]))
        except IndexError:
            del timestep_list[-1]
            warning_list.append("Warning: " + qt_tr.translate("rubar1d2d_mod", "The last time step is corrupted : one line data or more are missing. The last timestep is removed."))

        # check if lines are missing in other timestep
        timestep_index_to_remove_list = []
        for index in range(len(timestep_index_list)):
            if index > 0:
                # check if timestep index are constant
                # print(timestep_index_list[index] - timestep_index_list[index -1])
                if timestep_index_list[index] - timestep_index_list[index -1] != timestep_index_step:
                    timestep_index_to_remove_list.append(timestep_index_list[index])

        # check if last_line_timestep_len are equal
        if len(set(last_line_timestep_len)) > 1:  # not equal
            # index of corrupted timestep
            timestep_index_to_remove_list.extend([timestep_index_list[last_line_timestep_len.index(elem)] for elem in last_line_timestep_len if elem != last_line_timestep_len[0]])

        # raise warning and remove corrupted timestep
        if timestep_index_to_remove_list:
            timestep_to_remove = []
            for timestep_index_to_remove in timestep_index_to_remove_list:
                timestep_to_remove.append(timestep_list[timestep_index_list.index(timestep_index_to_remove)])
                # remove timestep
                timestep_list.pop(timestep_list.index(timestep_list[timestep_index_list.index(timestep_index_to_remove)]))
            warning_list.append("Warning: " + qt_tr.translate("rubar1d2d_mod", "Block data of timestep(s) corrumpted : ") + ", ".join(timestep_to_remove) +
                                qt_tr.translate("rubar1d2d_mod", ". They will be removed."))

    nb_t = len(timestep_list)

    return nb_t, timestep_list, warning_list


def get_triangular_grid(ikle, coord_c, xy, h, v, z):
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
    :param z: data on bottom levels
    :return: the updated ikle, coord_c (the center of the cell , must be updated ) and xy (the grid coordinate)
    """

    # this is important for speed. np.array are slow to append value
    xy = xy.tolist()
    h2 = []
    v2 = []
    z2 = z
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
            # add new value for the bottom level
            z2.append(np.mean(np.array(z2)[ikle[c]]))
            # first triangular cell
            ikle[c] = [ikle_c[0], ikle_c[1], len(xy) - 1]
            p1 = xy[len(xy) - 1]
            coord_c[c] = (np.array(xy[ikle_c[0]]) + np.array(xy[ikle_c[1]]) + p1) / 3
            # next triangular cell
            for s in range(1, len(ikle_c) - 1):
                ikle.append([ikle_c[s], ikle_c[s + 1], len(xy) - 1])
                coord_c.append((np.array(xy[ikle_c[s]]) + np.array(xy[ikle_c[s + 1]]) + p1) / 3)
                for t in range(0, nbtime):
                    v2[t].append(v[t][c])
                    h2[t].append(h[t][c])
            # last triangular cells
            ikle.append([ikle_c[-1], ikle_c[0], len(xy) - 1])
            coord_c.append((np.array(xy[ikle_c[-1]]) + np.array(xy[ikle_c[0]]) + p1) / 3)
            for t in range(0, nbtime):
                v2[t].append(v[t][c])
                h2[t].append(h[t][c])
    xy = np.array(xy)
    v = []
    h = []

    for t in range(0, nbtime):
        # there is an extra [] for the case where we more than one reach
        # to be corrected if we get multi-reach RUBAR simulation
        h.append(np.array(h2[t]))
        v.append(np.array(v2[t]))

    return ikle, coord_c, xy, v, h, z2


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
