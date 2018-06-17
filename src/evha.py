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
import os
import matplotlib.pyplot as plt
from copy import deepcopy


def load_evha_and_create_grid(path, name_evha=''):
    """
    This function loads the evha data, disitrbute the velocity,
    create a 2d grid from this data and save it all in
    an hdf5 format.  This function is called in a second thread by
    the class Evha() in Hydro_grid_2().

    THIS IS NOT FUNCTIONNING YET. IT SHOULD BE FINISHED BEFORE USE!!!!!!!

    :param path: the path to the folder with the evha data
    :param name_evha: the name of the project (if empty, this is assumed to be
     the name of the folder)
    """

    # load evha data
    if not name_evha:
        name_evha = os.path.basename(path)
    [xy, h, v] = load_evha(path, name_evha)
    if len(xy) == 1:
        if xy[0] == -99:
            return

    # disitrbute velocity

    # create 2d grid

    # save hdf5

    # create image if necessary


def load_evha(path, name_evha):
    """
    This function uses the different files to  load the evha data.

    :param path: the path to the folder with the evha project
    :param name_evha: The name of the evha project
    :return: the data to create the grids
    """
    failload = [-99], [-99], [-99]
    h = []
    v = []

    # load topography
    [xy, h, p_type] = load_top(path, name_evha)
    if len(xy) == 1:
        if xy[0] == -99:
            return failload

    # load hydraulic data (rcl file)

    return xy, h, v


def load_rcl(path, name_evha, section=[]):
    """
    This functions loads the rcl file created by evha. This functions contains
     the velocity and the adjusted water
    height. So it is the function which loads the hydraulic outputs.

    :param path: the path to the evha project
    :param name_evha: the name of the evha project
    :param section: the section number found in the top file (for verification)
    """
    pass
    # load the text

    # find the end of the text and the start of the data
    # the text end with the string 'iter  err'

    # separe the data by lines

    # modelled velcoity in on the fouth column and


def load_top(path, name_evha):
    """
    This function loads the topographical data from evha.

    :param path: the path to the folder with the evha project
    :param name_evha: The name of the evha project
    :return: the coordinates of the points, the water height, the type of point
    """
    failload = [-99], [-99], [-99]
    xy = []
    p_type = []
    h = []

    # get the name
    topnamepath = os.path.join(path, name_evha+'.top')
    if not os.path.isfile(topnamepath):
        print('Error: no topographical file found for the evha project. \n')
        return failload

    # get the string with the topographical data
    try:
        with open(topnamepath, 'rt') as f:
            data = f.read()
    except IOError:
        print('Error: Could not read the topographical file for evha. \n')
        return
    data = data.split('\n')

    # check if there is an extra angle
    first_line = data[0]
    first_line = first_line.strip()
    first_line = first_line.split()
    try:
        angleall = float(first_line[0])
    except ValueError:
        print('Error: Could not extract the angle from the topographical file.\
            Is it an evha input file? \n')
        return

    # check if evha was run to completion, send a warning otherwise
    if len(first_line) < 3:
        print('Warning: Evha does not seem to have run completely (1). \n')
    else:
        if first_line[2] != str(1):
            print('Warning: Evha does not seem to have run completely (2). \n')

    # find the lines with the pivot points
    # we know the first one (0,0).
    # it is possible than we have no other
    pli = []  # lines of the file with a pivot point
    pnum = []  # the number of this pivot point
    pref = []  # the reference of the pivot point
    for ind, d in enumerate(data):
        d = d.strip()
        # end of file with comments afterwards
        if len(d) == 1 and d[0] == '0':
            break
        if d[0] != '!' and ind != 0:  # comment
                if d[1] == 'P':
                    pli.append(ind)
                    try:
                        pnum.append(float(d[2:4].strip()))
                        ref_here = float(d[0])
                        if ref_here > 11 or ref_here < 0:
                            print('Warning: Pivot point\
                             should be between 1 and 10 \n')
                        pref.append(ref_here)
                    except ValueError:
                        print('Error: Could not read the pivot point on\
                            the topographical files (1) \n')
                        return failload

    # check if we have a double of each point
    sing_pnum = list(set(pnum))  # all pnum one times
    if len(pnum) != len(sing_pnum)*2:
        print('Error: Each pivot point should be doubled')
        return failload

    # calculate the coordinate of each reference point
    all_ref = list(set(pref))
    ref_known = [1]
    pivot_known = []
    secure = 0
    coord_pivot = []
    coord_ref = [[0, 0, 0]]  # in ref known order, each point only once
    while len(all_ref) > len(ref_known) and secure < 500:
        secure += 1
        # see if it is possible to calculate any pivot point
        for ind, p in enumerate(pnum):
            if p not in pivot_known and pref[ind] in ref_known:
                # if yes, find coordinates
                iref = [i for i, r in enumerate(ref_known)
                        if r == pref[ind]][0]
                coord_pp_here = get_point_from_angle(coord_ref[iref],
                                                     data[pli[ind]],
                                                     addan=angleall)
                if not coord_pp_here:
                    print('Error: The loading of the topographical file\
                            failed at line ' + str(pli[ind]) + '\n')
                    return failload
                coord_pivot.append(coord_pp_here)
                pivot_known.append(p)

        # see if it possible to calculate any reference
        for ind, p in enumerate(pref):
            if p not in ref_known and pnum[ind] in pivot_known:
                # if yes, find coordinates
                ipiv = [i for i, piv in enumerate(pivot_known)
                        if piv == pnum[ind]][0]
                coord_ref_here = get_point_from_angle(coord_pivot[ipiv],
                                                      data[pli[ind]], True,
                                                      addan=angleall)
                if not coord_ref_here:
                    print('Error: The loading of the topographical\
                     file failed at line ' + str(pli[ind]) + '\n')
                    return failload
                # check that we have a new reference point
                already_known = False
                for p2 in coord_ref:
                    if abs(p2[0] - coord_ref_here[0])\
                           + abs(p2[1] + coord_ref_here[1]) < 1e-5:
                        already_known = True
                if not already_known:
                    coord_ref.append(coord_ref_here)
                    ref_known.append(p)

    # get the points at the side of the river
    coord_left = []
    coord_right = []
    sec_right = []
    sec_left = []
    deca_left = []
    deca_right = []
    for ind, d in enumerate(data):
        d = d.strip()
        # end of file with comments afterwards
        if len(d) == 1 and d[0] == '0':
            break
        if d[0] != '!' and ind != 0:  # comment
            if d[1] == 'G' or d[1] == 'D':

                # find the reference point
                try:
                    ref_here = float(d[0])
                except ValueError:
                    print('Error: The loading of the topographical\
                     file failed at line ' + str(ind+1) + '\n')
                    return failload
                if ref_here > 11 or ref_here < 0:
                    print('Warning: Pivot point should be between 1 and 10 \n')

                # calculate coordinate of the point on the left or right
                iref = [i for i, r in enumerate(ref_known) if r == ref_here][0]
                coord_bank = get_point_from_angle(coord_ref[iref],
                                                  data[ind], addan=angleall)
                if not coord_bank:
                    print('Error: The loading of the topographical file failed\
                                at line ' + str(ind+1) + '\n')
                    return failload

                # find the section num
                try:
                    num_sec = float(d[4:6])
                except ValueError:
                    print('Error: The loading of the topographical\
                        file failed at line ' + str(ind) + '\n')
                    return failload

                if d[1] == 'G':   # Left
                    coord_left.append(coord_bank)
                    sec_left.append(num_sec)
                    try:
                        deca = float(d[34:40])
                    except ValueError:
                        print('Error: The loading of the topographical file\
                         failed at line ' + str(ind + 1) + '\n')
                        return failload
                    deca_left.append(deca)

                if d[1] == 'D':  # right
                    coord_right.append(coord_bank)
                    sec_right.append(num_sec)
                    try:
                        deca = float(d[34:40])
                    except ValueError:
                        print('Error: The loading of the topographical file\
                            failed at line ' + str(ind + 1) + '\n')
                        return failload
                    deca_right.append(deca)

    # for all the transect, get the direction of the transect
    dir_t = []  # the direction of the transect in sec_left order,
    # from left to right, norm of 1
    if len(sec_right) != len(sec_left):
        print('Error: the number of point on the left bank are not equal\
            to the number of point on the left bank \n')
    for indl, n in enumerate(sec_left):
            indr = [i2 for i2, n2 in enumerate(sec_right) if n == n2]
            if len(indr) == 0:
                print('Error: One of the pint which descibed the right bank\
                    is not known \n')
                return
            elif len(indr) > 1:
                print('Warning: More than one right point is found')
            else:
                indr = indr[0]
            distx = coord_right[indr][0] - coord_left[indl][0]
            disty = coord_right[indr][1] - coord_left[indl][1]
            # norm = np.sqrt(distx**2 + disty**2)
            dir_here = [distx, disty]
            dir_t.append(dir_here)

    # get the coordinates of the points on the transect
    # either with decameter or angle
    coord_trans = []
    for ind, d in enumerate(data):
        d = d.strip()
        # end of file with comments afterwards
        if len(d) == 1 and d[0] == '0':
            break
        if d[0] != '!' and ind != 0:  # comment
            if d[1] == ' ':

                # get section number
                try:
                    num_sec = float(d[4:6])
                except ValueError:
                    print('Error: Section number of transect\
                        could not be read \n')
                    print('Error: The loading of the topographical file\
                        failed at line ' + str(ind) + '\n')
                    return failload
                # find the direction of the transect
                indt = [i for i, n in enumerate(sec_right) if n == num_sec][0]
                dir_here = dir_t[indt]
                coord_left_here = coord_left[indt]
                deca_left_here = deca_left[indt]
                deca_right_here = deca_right[indt]

                # check if point done with angle oder decameter
                try:
                    type_transect = d[40:41]
                except ValueError:
                    print('Error: One transect point could not be read. \n')
                    print('Error: The loading of the topographical file\
                        failed at line ' + str(ind) + '\n')
                    return failload

                # find the reference point
                try:
                    ref_here = float(d[0])
                except ValueError:
                    print('Error: Could not read the reference point \n')
                    print('Error: The loading of the topographical file\
                        failed at line ' + str(ind + 1) + '\n')
                    return failload
                if ref_here > 11 or ref_here < 0:
                    print('Warning: Reference point should be between\
                        1 and 10 \n')
                indref = \
                    [i for i, r in enumerate(ref_known) if r == ref_here][0]
                coord_ref_here = coord_ref[indref]

                # get height difference
                try:
                    cote_mid = float(d[17:23])
                except ValueError:
                    print('Error: The loading of the topographical file failed\
                        at line ' + str(ind + 1) + '\n')
                    return failload

                # calculate coord with angle
                if type_transect == 'V':
                    try:
                        angle = float(d[29:35])
                    except ValueError:
                        print('Error: The loading of the topographical file\
                            failed at line ' + str(ind + 1) + '\n')
                        return failload
                    coord_t = get_point_on_transect(angle, dir_here,
                                                    coord_ref_here,
                                                    coord_left_here, cote_mid)
                    coord_trans.append(coord_t)

                # calculate coord with decameter
                else:
                    try:
                        deca = float(d[34:40])
                    except ValueError:
                        print('Error: The loading of the topographical file\
                         failed at line ' + str(ind + 1) + '\n')
                        return failload
                    if (deca_left_here-deca_right_here) > 0:
                        dist = deca/(deca_left_here-deca_right_here)
                    else:
                        dist = 0
                    xt = coord_left_here[0] + dir_here[0] * dist
                    yt = coord_left_here[1] + dir_here[1] * dist
                    zt = coord_ref_here[2] + cote_mid/100
                    coord_trans.append([xt, yt, zt])

    plt.figure()
    for p in coord_ref:
        plt.plot(p[0], p[1], '*b')
    for p in coord_pivot:
        plt.plot(p[0], p[1], '^k')
    coord_righta = np.array(coord_right)
    plt.plot(coord_righta[:, 0], coord_righta[:, 1], '-xg')
    coord_lefta = np.array(coord_left)
    plt.plot(coord_lefta[:, 0], coord_lefta[:, 1], '-xr')
    for p in coord_trans:
        plt.plot(p[0], p[1], '^k')
    plt.xlabel('x coordinates []')
    plt.ylabel(' y label []')
    plt.show()

    return xy, h, p_type


def add_angle(xy, angle):
    """
    This function add an angle to a list of point.
    The angle is always taken around the point (0,0). We use
    radial coordinates (r, theta) for this calculation.
    NOT USED ANYMORE. MIGHT BE WRONG AS WE NEED TO BE MORE CAREFUL
    WHEN CALCULATING ARCCOS

    :param xy: the coordinate without the added angle -
        list of two floats (x,y)
    :param angle: the angle to add (in grad)
    :return: the corrected list of point
    """
    xy_old = deepcopy(xy)
    xy_new = []
    angle2 = angle * np.pi/200  # to radian

    for p in xy_old:
        r = np.sqrt(p[0]**2 + p[1]**2)
        new_angle = np.arccos(p[0]/r)

        new_angle += angle2  # radian
        if new_angle > 2*np.pi:  # we might go over the circle
            new_angle -= 2*np.pi
        pnew = [r*np.cos(new_angle), r*np.sin(new_angle), p[2]]
        xy_new.append(pnew)

    return xy_new


def get_point_from_angle(coord0, d, inv=False, addan=0):
    """
    This function find a point from a given reference.
    This is points is based on one angle from the reference and
    three cotes (min, middle, max).
    The difference between the minimum and maximum cotes gives
     the distance between
     the points and the middle one gives the height difference (in cm).
    It is possible to find (x,y,z) from the new points
    from these information and the reference points. We gives a line of
     string as entry which is in the format of evha
     topographical file

    :param coord0: the coordinate of the reference point
    :param d: one line of the topographical file (one line)
    :param inv: If inv True, the point was not shoot from the reference point
     but "to" the reference point
    :param addan: an angle to add if the river to moved by an angle (in grad)
    :return xy (coordinates of all point), point_lr updated
    """
    p = []

    # get double from string
    try:
        cote_min = float(d[11:17])
        cote_mid = float(d[17:23])
        cote_max = float(d[23:29])
    except ValueError:
        print('Error: Could not read one angle in the topographical file\
         from evha (1) \n')
        return p
    if cote_max < cote_min or cote_mid < cote_min or cote_mid > cote_max:
        print('Error: One of the three "cotes" was not coherent')
        return p
    try:
        angle = float(d[29:35])
    except ValueError:
        print('Error: Could not read one angle in the topographical file\
         from evha (2) \n')
        return p
    angle = angle * np.pi/200 + addan * np.pi/200

    # calculate point
    dist = (cote_max - cote_min)
    # diff en cm is distance in meter becaause fo measurement device
    if not inv:
        x = coord0[0] + np.cos(angle) * dist
        y = coord0[1] + np.sin(angle) * dist
        z = coord0[2] + cote_mid / 100
    else:
        x = coord0[0] - np.cos(angle) * dist
        y = coord0[1] - np.sin(angle) * dist
        z = coord0[2] - cote_mid / 100

    p = [x, y, z]
    return p


def get_point_on_transect(angle, dir, refc, lefc, cod_mid):
    """
    This function calculates the coordinate of the point on transect if
     this point is given by one angle from the
     reference and the direction of the transect.

    To get this we solve a system of equation:
    rx + r*cos(a) = lx + dist * dir[0] et ry + r*sin(a) = ly + dist*dir[1].
    dir should have a unit length. When r is found,
     we can calculate the coordinate (x = rx + r*cos(a) and y=ry + r*sin(a))

    :param angle: the angle from the reference point
    :param dir: the direction of the transect
    :param refc: the coordinate of the reference
    :param lefc: the coordinate of the left bank point
    :param cod_mid: the different in height compared to
        the reference station in cm
    :return: the new point coordinate
    """

    # insure unit vector
    norm = np.sqrt(dir[0]**2 + dir[1]**2)
    dir = [dir[0]/norm, dir[1]/norm]

    # radian angle from grad
    a = angle * np.pi / 200

    # find r using uncertain formula
    r1 = dir[1] * (lefc[0] - refc[0]) + dir[0] * (refc[1]-lefc[1])
    r2 = dir[1] * np.cos(a) - dir[0] * np.sin(a)
    r = r1/r2

    # find coord
    x = refc[0] + r * np.cos(a)
    y = refc[1] + r * np.sin(a)
    z = refc[1] + cod_mid/100
    coord = [x, y, z]

    return coord


def main():
    """
    This is used to test evha.
    """

    path = r'D:\Diane_work\output_hydro\EVHA\Projet\arc'
    load_evha_and_create_grid(path, 'arc15-8')
    # path = r'D:\Diane_work\output_hydro\EVHA\Projet\adouin'
    # load_evha_and_create_grid(path)
    # path = r'D:\Diane_work\output_hydro\EVHA\Projet\andrable\ands3a'
    # load_evha_and_create_grid(path)


if __name__ == '__main__':
    main()
