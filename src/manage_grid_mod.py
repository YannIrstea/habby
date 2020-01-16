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
import bisect
import copy
import os
import sys
import time
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import scipy.interpolate
import scipy.spatial.qhull as qhull
import triangle
from scipy.interpolate import griddata

from src.project_manag_mod import create_default_project_preferences_dict
from src_GUI import preferences_GUI
from src import tools_mod


def grid_and_interpo(vh_pro, coord_pro, nb_pro_reach, interpo_choice, pro_add=1):
    """
    This function forms the link between GUI and the various grid and interpolation functions. Is called by
    the "loading" function of hec-ras 1D, Mascaret and Rubar BE. It used to be a method in hydro_GUI2, but we have
    to move it as a function to create a second thread. Hence, the high amount of parameter.

    :param vh_pro: Velocity and height data
    :param coord_pro: the position of the profile
    :param nb_pro_reach: the number of profile by reach
    :param interpo_choice: an int which gives the choice of interpolatin (see below)
    :param pro_add: the number of profile for be added (for interpoation method 1 and 2)

    **Technical comments**

    Here are the list of the interpolation choice:

    * 0 Use the function create_grid_only_1_profile() from manage_grid_mod.py for all time steps.
    * 1 Use the function create_grid() from manage_grid_mod.py for all time steps followed by a linear interpolation
    * 2 Use the function create_grid() from manage_grid_mod.py for all time steps followed by a nearest neighbour interpolation
    * 3 Use create_grid() for the whole profile, make a linear inteporlation on this grid for all time step
        and use the cut_2d_grid to get a grid with only the wet profile for all time step (This part was only started.
        It was not finished.)

    For the interpolation case 1 and 2, it is possible that the triangle module crashes if the geometry of the
    river is too complicated. Generally, the interpolation method 1 and 2 gives smoother results with more control
    over the interpolation option and the size of the cells. However, these two interpolation methods are more sensitive
    to the inputs, especially if the river has a lot of "island" (strongly anastomotic). So the interpoliation method 0
    is more adequate in this case.

    """
    failload = [-99], [-99], [-99], [-99], [-99]
    # check input
    if not isinstance(interpo_choice, int):
        print('Error: Interpolation method is not recognized (Type).\n')
        return failload
    if len(vh_pro) == 0:
        print('Warning: Velocity and height data is empty (from grid_and_interpo).\n')
        return failload
    if len(vh_pro) == 1 and vh_pro == [-99]:
        print('Error: Velocity and height data were not created.\n')
        return failload
    if interpo_choice > 0 and not isinstance(pro_add, int):
        print('Error: Number of added profile is not recognized (Type).\n')
        return failload
    if interpo_choice > 0 and (pro_add < 1 or pro_add > 100):
        print('Error: a number of added profile between 1 and 100 must be given.\n')
        return failload

    # prepare outputs for all reaches and all time steps
    inter_vel_all_t = []
    inter_h_all_t = []
    ikle_all_t = []
    point_all_t = []
    point_c_all_t = []

    # each interpolations type
    if interpo_choice == 0:

        # first whole profile (no need for velcoity and height data)
        [ikle_all, point_all_reach, point_c_all, blob, blob] = \
            create_grid_only_1_profile(coord_pro, nb_pro_reach)
        inter_vel_all_t.append([])
        inter_h_all_t.append([])
        ikle_all_t.append(ikle_all)
        point_all_t.append(point_all_reach)
        point_c_all_t.append(point_c_all)

        # by time step
        for t in range(0, len(vh_pro)):
            if t % 10 == 0 and t > 2:
                print('time step :' + str(t))

            [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro[t])
            inter_vel_all_t.append(inter_vel_all)
            inter_h_all_t.append(inter_height_all)
            ikle_all_t.append(ikle_all)
            point_all_t.append(point_all_reach)
            point_c_all_t.append(point_c_all)

    elif interpo_choice == 1:
        # grid for the whole profile
        # it is in an extra thread because the triangle module might crash for too complicated cases
        [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = create_grid(
            coord_pro, pro_add, [], [], nb_pro_reach, [])

        inter_vel_all_t.append([])
        inter_h_all_t.append([])
        ikle_all_t.append(ikle_all)
        point_all_t.append(point_all_reach)
        point_c_all_t.append(point_c_all)

        # only the wet area, by time step
        for t in range(0, len(vh_pro)):
            [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = create_grid(
                coord_pro, pro_add, [], [], nb_pro_reach, vh_pro[t])
            [inter_vel_all, inter_height_all] = interpo_linear(point_all_reach, coord_pro2, vh_pro[t])

            inter_vel_all_t.append(inter_vel_all)
            inter_h_all_t.append(inter_height_all)
            ikle_all_t.append(ikle_all)
            point_all_t.append(point_all_reach)
            point_c_all_t.append(point_c_all)

    elif interpo_choice == 2:
        # grid for the whole profile
        [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = create_grid(
            coord_pro, pro_add, [], [], nb_pro_reach, [])
        inter_vel_all_t.append([])
        inter_h_all_t.append([])
        ikle_all_t.append(ikle_all)
        point_all_t.append(point_all_reach)
        point_c_all_t.append(point_c_all)

        # create grid for the wet area by time steps
        for t in range(0, len(vh_pro)):
            sys.stdout.flush()
            [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = create_grid(
                coord_pro, pro_add, [], [], nb_pro_reach, vh_pro[t])
            [inter_vel_all, inter_height_all] = interpo_nearest(point_all_reach, coord_pro2, vh_pro[t])
            inter_vel_all_t.append(inter_vel_all)
            inter_h_all_t.append(inter_height_all)
            ikle_all_t.append(ikle_all)
            point_all_t.append(point_all_reach)
            point_c_all_t.append(point_c_all)

    elif interpo_choice == 3:
        # NOT DONE (DEBUGGING NEEDED -> do not pass test_habby.py)
        # linear interpolatin again but using the function cut_grid instead of create_grid for all time step
        [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = create_grid(
            coord_pro, pro_add, [], [], nb_pro_reach, [])

        inter_vel_all_t.append([])
        inter_h_all_t.append([])
        ikle_all_t.append(ikle_all)
        point_all_t.append(point_all_reach)
        point_c_all_t.append(point_c_all)

        # update coord, interpolate on this grid for all time step linearly and cut the grid
        for t in range(0, len(vh_pro)):
            coord_pro2 = update_coord_pro_with_vh_pro(coord_pro, vh_pro[t])
            # interpolation on the whole grid
            [inter_vel_all, inter_height_all] = interpo_linear(point_all_t[0], coord_pro2, vh_pro[t])
            # cut grid for the wet area by time steps
            [ikle_all, point_all_reach, inter_height_all, inter_vel_all] = cut_2d_grid_all_reach(
                ikle_all_t[0], point_all_t[0], inter_height_all, inter_vel_all)
            inter_vel_all_t.append(inter_vel_all)
            inter_h_all_t.append(inter_height_all)
            ikle_all_t.append(ikle_all)
            point_all_t.append(point_all_reach)
            point_c_all_t.append(point_c_all)

    else:
        print('Error: Interpolation method is not recognized (Num).\n')

    return ikle_all_t, point_all_t, point_c_all_t, inter_vel_all_t, inter_h_all_t


def create_grid(coord_pro, extra_pro, coord_sub, ikle_sub, nb_pro_reach=[0, 1e10], vh_pro_t=[], q=[], pnew_add=1):
    """
    It creates a grid from the coord_pro data using the triangle module.
    It creates the grid up to the end of the profile if vh_pro_t is not present
    or up to the water limit if vh_pro_t is present

    :param q: used in the secondary process  when we do not call this function direclty, but we call it in a second
           process so that the GUI do not crash if something go wrong (not used anymore in this form)
    :param coord_pro: the profile coordinates (x,y, h, dist along) the profile
    :param extra_pro: the number of "extra" profiles to be added between profile to simplify the grid
    :param coord_sub: (not used anymore)
           the coordinate of the point forming the substrate layer (often created with substrate.load_sub)
    :param ikle_sub: (not used anymore)
           the connectivity table of the substrate grid (often created with substrate.load_sub)
    :param nb_pro_reach: the number of reach by profile starting with 0
    :param vh_pro_t: the velocity and height of the water (used to cut the limit of the river).
    :param pnew_add: (not used anymore) a parameter to cut the substrate side in smaller part (improve grid quality)
            in the form dist along profile, h , v for the analyzed time step. f not given, gird is contructed on the whole profile.
    :return: connectivity table and grid point

    **Form of the function in summary**

    *   if vh_pro_t:

        *   find cordinate under water and used this to update coord_pro
        *   see if there is islands, find the island limits and the holes indicating the inside/outside of the islands

    *   find the point which give the end/start of the segment defining the grid limit
    *   find all point which need to be added to the grid and add extra profile if needed
    *   based on the start/end points and the island limits, create the segments which gives the grid limit
    *   triangulate and so create the grid
    *   flag point which are overlapping in two grids

    For more info, see the document "More info on the grid".
    """

    all_straight = False
    point_all = []
    ind_s = []
    ind_e = []
    ind_p = []
    lim_by_reach = []
    warn_pro_short = True

    if extra_pro < 1:
        print('number of additional profil is too low. Add at least 1 profil. \n')
        return

    # if we create the grid only for the wetted area, update coord_pro to keep only the point which are under water
    seg_island = []
    if vh_pro_t:
        coord_pro = update_coord_pro_with_vh_pro(coord_pro, vh_pro_t)

        # get all the point for the grid
    for p in range(1, len(coord_pro)):  # len(coord_pro) nb_pro_reach[1]
        # because of the if afterwards, p = 0 is accounted for.
        coord_pro_p0 = np.array(coord_pro[p - 1])
        coord_pro_p1 = np.array(coord_pro[p])

        # add known point
        # manage segment and holes to give the constraint to Delauney
        pro_orr = np.array([coord_pro_p0[0], coord_pro_p0[1]]).transpose()

        if p == 1:
            point_all = pro_orr
            ind_s.extend([0])  # start
            ind_e.extend([len(point_all) - 1])  # end
            ind_p.extend([0])
        else:
            ind_s.extend([len(point_all)])  # start
            point_all = np.concatenate((point_all, pro_orr), axis=0)
            ind_e.extend([len(point_all) - 1])  # end
            ind_p.extend([len(point_all)])
        # do not add profile at a junction
        if np.all(p != np.array(nb_pro_reach)):
            if len(coord_pro_p1[0]) > 1 and len(coord_pro_p0[0]) > 1:
                # not used but quicker if we know that all profile are straight
                if all_straight:
                    # find the start/end of the original profile
                    x0all = coord_pro_p0[0]
                    y0all = coord_pro_p0[1]
                    x1all = coord_pro_p1[0]
                    y1all = coord_pro_p1[1]
                    l0 = min(len(x0all), len(x1all))
                    l1 = max(len(x0all), len(x1all))
                    p0a = np.array([x0all[0], y0all[0]])
                    p0b = np.array([x0all[-1], y0all[-1]])
                    p1a = np.array([x1all[0], y1all[0]])
                    p1b = np.array([x1all[-1], y1all[-1]])
                    if x1all[0] == x1all[-1] and warn_pro_short:
                        print('Warning: Profil is too short. Grid might be unlogical. \n')
                        warn_pro_short = False
                    # find start/end point at the end of the added profile
                    new_p_a = newp(p0a, p1a, extra_pro)
                    new_p_b = newp(p0b, p1b, extra_pro)
                    # add points to the extra profile
                    for i in range(0, len(new_p_a)):
                        li = np.int(np.floor(l0 + i * (l1 - l0) / len(new_p_a)))
                        if li < 2:
                            li = 2
                        point_all_i = newp(new_p_a[i], new_p_b[i], li)
                        point_all = np.concatenate((point_all, point_all_i), axis=0)
                        # point_all.extend(point_all_i)
                        ind_p.extend([len(point_all)])
                else:
                    [point_mid_x, point_mid_y] = find_profile_between(coord_pro_p0, coord_pro_p1, extra_pro, True)
                    for pr in range(0, extra_pro):
                        point_all_i = np.array([point_mid_x[pr], point_mid_y[pr]]).T
                        point_all = np.concatenate((point_all, point_all_i), axis=0)
                        ind_p.extend([len(point_all)])

        # add the last profile
        if p == len(coord_pro) - 1:
            pro_orr = np.array([coord_pro_p1[0], coord_pro_p1[1]]).transpose()
            ind_s.extend([len(point_all)])  # start
            point_all = np.concatenate((point_all, pro_orr), axis=0)
            ind_e.extend([len(point_all) - 1])  # end
            ind_p.extend([len(point_all)])

    # show the created profile, used to debug
    # plt.figure()
    # plt.plot(point_all[:, 0], point_all[:, 1], '.m')
    # # for p in range(0, len(coord_pro)):
    # #     plt.plot(coord_pro[p][0], coord_pro[p][1], '.b')
    # # plt.axis('equal')
    # plt.show()

    # manage islands
    hole_all_i = []
    isl2 = 0
    hole_isl = []
    # if one profile has a part out of water, we will create a polygon with six faces
    # one side along one of the extra profile situated before the profile and one side after
    # and four side to close the polygon. It is close to two perpendicular sides but it pass by the island limits
    # on the main profile, so it makes 4 sides when it is not all aligned
    # vertex are ind1, ind2, ind3, ind4, ind_lim[i], ind_lim[i+1]
    #  ind1, ind2,ind 3, ind4 are the poijt of the extra porfile which are the closest to ind_lim[i], ind_lim[i+1]
    # it is possible to have ind1 == ind2 ou ind3 == ind4. In this case, we put ind2(4) = ind2(4)+1
    # if we reach the end of the profile we have a triangle even if it is dangerous because of fine angle
    if vh_pro_t:
        warn_isl = True
        r = -1
        seg_island = []
        # find island profile by profile
        extra_pro2 = extra_pro
        if extra_pro == 0:
            extra_pro2 = 1

        for p in range(0, len(coord_pro) - 1):
            if np.all(p != np.array(nb_pro_reach)):
                # find on which extra profile to "finish" and "start" the island
                if np.any(p - 1 == np.array(nb_pro_reach)):
                    if extra_pro2 % 2 == 0:
                        af = int(extra_pro2 / 2)
                        bef = -af - 1
                    else:
                        af = int(np.floor(extra_pro2 / 2) + 1)
                        bef = -af
                else:
                    if extra_pro2 % 2 == 0:
                        af = int(extra_pro2 / 2)
                        bef = -af - 1
                    else:
                        af = int(np.floor(extra_pro2 / 2) + 1)
                        bef = -af
                # find if there is and island
                h_all = np.array(vh_pro_t[p][1])
                if len(h_all) > 0:
                    ind_lim = np.where(h_all == h_all[1])[0]
                else:
                    ind_lim = []
                # if yes find where it is
                if len(ind_lim) > 3:
                    isl_del = []
                    # if island over more than on consecutive indices, put them together (a bit quicker)
                    for isl in range(1, len(ind_lim) - 3):
                        if ind_lim[isl] + 1 == ind_lim[isl + 1] and ind_lim[isl + 2] == ind_lim[isl + 1] + 1:
                            isl_del.append(isl + 1)
                    ind_lim = np.delete(ind_lim, isl_del)
                    # if distance between two island is two small, eease the island
                    # isl_del = []
                    # for isl in range(0, len(ind_lim) - 1):
                    #     p1 = point_all[ind_lim[isl]]
                    #     p2 = point_all[ind_lim[isl+1]]
                    #     dist_here = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1]) **2)
                    #     if dist_here < 0.001:
                    #         isl_del.append(isl)
                    #         isl_del.append(isl + 1)
                    ind_lim = np.delete(ind_lim, isl_del)
                    x = coord_pro[p][0]
                    y = coord_pro[p][1]
                    # find the end and start indices of the extra-profile before and after
                    p_here = p + p * extra_pro2 - r * extra_pro2 - 1
                    ind_bef_s = ind_p[p_here + bef]
                    ind_bef_e = ind_p[p_here + bef + 1]
                    ind_af_s = ind_p[p_here + af]
                    ind_af_e = ind_p[p_here + af + 1]

                    # calculate minimum distance for all island to get the six vertex
                    len_here = len(ind_lim)
                    for i in range(1, len_here - 1, 2):
                        point_bef = np.array(point_all[ind_bef_s:ind_bef_e])
                        dist_xy = np.sqrt((point_bef[:, 0] - x[ind_lim[i]]) ** 2 +
                                          (point_bef[:, 1] - y[ind_lim[i]]) ** 2)
                        ind1 = ind_bef_s + np.argmin(dist_xy)

                        dist_xy = np.sqrt((point_bef[:, 0] - x[ind_lim[i + 1]]) ** 2 +
                                          (point_bef[:, 1] - y[ind_lim[i + 1]]) ** 2)
                        ind2 = ind_bef_s + np.argmin(dist_xy)
                        point_af = np.array(point_all[ind_af_s:ind_af_e])
                        dist_xy = np.sqrt((point_af[:, 0] - x[ind_lim[i]]) ** 2 +
                                          (point_af[:, 1] - y[ind_lim[i]]) ** 2)
                        ind3 = ind_af_s + np.argmin(dist_xy)
                        dist_xy = np.sqrt((point_af[:, 0] - x[ind_lim[i + 1]]) ** 2 +
                                          (point_af[:, 1] - y[ind_lim[i + 1]]) ** 2)
                        ind4 = ind_af_s + np.argmin(dist_xy)
                        # add the six segments (start and end of each segment), so 12 points
                        beg_len = len(seg_island)
                        if ind2 != ind1:
                            for mi in range(min(ind1, ind2), max(ind1, ind2)):
                                seg_island.append([mi, r, p_here + bef, isl2])
                                seg_island.append([mi + 1, r, p_here + bef, isl2])
                            seg_island.append([ind2, r, -99, isl2])
                            seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                        else:
                            seg_island.append([ind2, r, -99, isl2])
                            seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                        seg_island.append([ind1, r, -99, isl2])
                        seg_island.append([ind_p[p_here] + ind_lim[i], r, -99, isl2])

                        seg_island.append([ind_p[p_here] + ind_lim[i], r, -99, isl2])
                        seg_island.append([ind3, r, -99, isl2])
                        if ind3 != ind4:
                            for mi in range(min(ind3, ind4), max(ind3, ind4)):
                                seg_island.append([mi, r, p_here + af, isl2])
                                seg_island.append([mi + 1, r, p_here + af, isl2])
                            seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                            seg_island.append([ind4, r, -99, isl2])
                        else:
                            seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                            seg_island.append([ind4, r, -99, isl2])
                        isl2 += 1

                        # add the holes, so triangle know that this zone should be empty
                        oa = np.array([x[ind_lim[i]], y[ind_lim[i]]])
                        ob = np.array([x[ind_lim[i + 1]], y[ind_lim[i + 1]]])
                        # 0.5a + 0.5 b results in more island erased afterwards
                        hole_here = (0.95 * oa + 0.05 * ob).tolist()
                        # check if hole is in the triangle (might not be always true if geometry is complicated)
                        polygon_ind = range(beg_len, len(seg_island))
                        seg_poly = []
                        for j in range(0, len(polygon_ind), 2):
                            p1 = point_all[seg_island[polygon_ind[j]][0]]
                            p2 = point_all[seg_island[polygon_ind[j + 1]][0]]
                            seg_poly.append([p1, p2])
                        inside = inside_polygon(seg_poly, hole_here)
                        if inside:
                            hole_all_i.append(hole_here)
                            hole_isl.extend([isl2 - 1])
                        else:
                            seg_islandh = np.array(seg_island)
                            # ind_alls = np.where(seg_islandh[:, 3] == isl2-1)[0]
                            ind_alls = np.array(polygon_ind)
                            ind_alls = np.sort(ind_alls)
                            ind_alls = ind_alls[::-1]
                            for m in range(0, len(ind_alls)):
                                del seg_island[ind_alls[m]]
                            if warn_isl:
                                print('Warning: Some islands were neglected because the geometry was unclear. \n')
                                warn_isl = False

            else:
                r += 1
        seg_island = np.array(seg_island)

        # correct for crossing segment (not used, just if check needed)
        check_cross = False
        if check_cross:
            if len(seg_island) > 1:
                to_be_delete = []
                to_be_delete_hole = []
                for s1 in range(0, len(seg_island), 2):
                    seg11 = point_all[seg_island[s1, 0]]
                    seg12 = point_all[seg_island[s1 + 1, 0]]
                    for s2 in range(s1 + 2, len(seg_island), 2):
                        seg21 = point_all[seg_island[s2, 0]]
                        seg22 = point_all[seg_island[s2 + 1, 0]]
                        if np.sum(seg11 - seg21) != 0 and np.sum(seg11 - seg22) != 0 and np.sum(seg12 - seg21) != 0 \
                                and np.sum(seg12 - seg22) != 0:
                            [inter, pc] = intersection_seg(seg11, seg12, seg21, seg22, False)
                            if inter:
                                if seg_island[s2, 2] != seg_island[s1, 2]:  # pro
                                    if seg_island[s2, 3] != seg_island[s1, 3]:  # island
                                        # plt.figure()
                                        # plt.plot(seg11[0], seg11[1], '.b')
                                        # plt.plot(seg12[0], seg12[1], '.r')
                                        # plt.plot(seg21[0], seg21[1], '.m')
                                        # plt.plot(seg22[0], seg22[1], '.m')
                                        # plt.show()
                                        seg4 = [seg11, seg12, seg21, seg22]
                                        ind4 = [s1, s1 + 1, s2, s2 + 1]
                                        close = False
                                        for da in range(0, 4):
                                            dist = np.sqrt(
                                                (seg4[da][0] - pc[0][0]) ** 2 + (seg4[da][1] - pc[0][1]) ** 2)
                                            if dist < 10 ** -4:
                                                print('Warning: low distance found. \n')
                                                point_all[seg_island[ind4[da], 0]] = pc[0]
                                                close = True
                                        if not close:
                                            isl_here = seg_island[s1, 3]
                                            ind_all = np.where(seg_island[:, 3] == isl_here)[0]
                                            to_be_delete.extend(list(ind_all))
                                            to_be_delete_hole.append(isl_here)
                                            to_be_delete_hole.append(isl_here)
            to_be_delete = list(set(to_be_delete))
            seg_island = np.delete(seg_island, to_be_delete, axis=0)
            hole_all_i = list(np.delete(hole_all_i, to_be_delete_hole, axis=0))

        # correct for colinear segments as triangle has difficulties with them
        colinear = True
        if len(seg_island) > 1 and colinear:
            for p in range(0, len(coord_pro) + len(coord_pro) * extra_pro):
                ind = np.where(seg_island[:, 2] == p)[0]  # not always 6 segments
                seg_island_pro = seg_island[ind, 0]
                seg_island_pro = np.sort(seg_island_pro)
                seg_island[ind, 0] = seg_island_pro

        # correct for point at the middle of one segment as triangle has difficulties with them (not used)
        test_middle = False
        if len(seg_island) > 1 and test_middle:
            for s in range(0, len(seg_island), 2):
                mpoint = 0.5 * point_all[seg_island[s, 0]] + 0.5 * point_all[seg_island[s + 1, 0]]
                ind = np.where(abs(mpoint[0] - point_all[:, 0]) + abs(mpoint[1] -
                                                                      point_all[:, 1]) < point_all[0, 0] * 1e-7)[0]
                point_all[ind, :] = point_all[ind, :] * 0.99

    # check if they here identical points and make a corrrection if yes
    # using an idea from http://stackoverflow.com/questions/31097247/remove-duplicate-rows-of-a-numpy-array
    # should be reasonlaby quick
    # test: point_all2 = np.array([[1,1], [2,3], [1,2], [3,4], [1,2]])
    sorted_data = point_all[np.lexsort(point_all.T), :]
    row_mask = np.append([True], np.any(np.diff(sorted_data, axis=0), 1))
    test_unique = sorted_data[row_mask]
    if len(test_unique) != len(point_all):
        print('Warning: There is duplicate points. The triangulation will be modified.\n')
        # this is slow , but it might solve problems
        unique_find = []
        a = len(point_all)
        for ind, p in enumerate(point_all):
            p = list(p)
            if p not in unique_find:
                unique_find.append(p)
            else:
                point_all[ind] = [p[0] + p[0] * 0.001 * ind / a, p[1] + p[1] * 0.001 * ind / a]

    # put data in order and find the limits
    seg_to_be_added2 = []
    lim_by_reach_for_sub = []
    lim_isl_for_sub = []
    for r in range(0, len(nb_pro_reach) - 1):
        lim_by_reach_r = []
        lim_isl_for_subr = []
        ind_r = nb_pro_reach[r]
        ind_r2 = nb_pro_reach[r + 1]
        # side (for both list)
        for i in range(ind_r, nb_pro_reach[r + 1] - 1):
            lim_by_reach_r.append([ind_s[i], ind_s[i + 1]])
            lim_by_reach_r.append([ind_e[i], ind_e[i + 1]])
        # start and end of each reach
        for sta in range(ind_s[ind_r], ind_e[ind_r]):
            lim_by_reach_r.append([sta, sta + 1])
        for endr in range(ind_s[ind_r2 - 1], ind_e[ind_r2 - 1]):
            lim_by_reach_r.append([endr, endr + 1])
        # lim_by_reach_r.append([ind_s[ind_r], ind_e[ind_r]])
        # lim_by_reach_r.append([ind_s[ind_r2-1], ind_e[ind_r2-1]])
        blob = copy.deepcopy(lim_by_reach_r)  # classic, classic, but still annoying
        lim_by_reach_for_sub.append(blob)
        # add the segments realted to the island
        if vh_pro_t:
            if len(seg_island) > 1:
                ind_isl_re = np.where(seg_island[:, 1] == r)[0]
                for w in range(0, int(len(ind_isl_re) / 2)):
                    seg_to_be_added = np.array([int(seg_island[ind_isl_re[2 * w], 0]),
                                                int(seg_island[ind_isl_re[2 * w + 1], 0])])
                    # seg_to_be_added2.append(seg_to_be_added)
                    # needed because no identical segment possible
                    lim_by_reach_arr = np.array(lim_by_reach_r)
                    sum_reach = np.sum(abs(lim_by_reach_arr - seg_to_be_added), axis=1)
                    if (sum_reach != 0).all():
                        lim_by_reach_r.append(seg_to_be_added)
                        lim_isl_for_subr.append(seg_to_be_added)
        # add the limit of this reach
        lim_by_reach.append(lim_by_reach_r)
        lim_isl_for_sub.append(lim_isl_for_subr)

    # triangulate. Overlaping elements are just flagged in the variable overlap
    ikle_all = []
    point_all_reach = []
    point_c_all = []
    overlap = []

    # debug triangulation input (only point)
    # plt.figure()
    # plt.plot(point_all[:, 0], point_all[:, 1], '.m')
    # plt.axis('equal')
    # plt.show()

    # print('triangulation')
    for r in range(0, len(nb_pro_reach) - 1):
        # do the triangulation
        # perfomance note: Obviously sending only the point_all from this reach would save time
        # however at the junction between the reach we would have different point on which the grid is constructed
        # which means that a "point in polygon" test would be needed to find the overlapping regions
        # if all point are tested, this is obviouly slower than the current version.
        # But overlapping points are often at the end/start of the reach.
        # Performance might depend on the criteria chosen to test the points.
        if hole_all_i:
            dict_point = dict(vertices=point_all, segments=lim_by_reach[r], holes=hole_all_i)
        else:
            dict_point = dict(vertices=point_all, segments=lim_by_reach[r])
        try:
            grid_dict = triangle.triangulate(dict_point, 'p')  # 'p' allows for constraint
        except:
            print('Error: Triangulation failed')
        try:
            ikle_r = grid_dict['triangles']
            point_all_r = grid_dict['vertices']
        except KeyError:
            print('Warning: Reach with an empty grid.\n')
            ikle_r = None
            point_all_r = None
        ikle_all.append(ikle_r)
        point_all_reach.append(point_all_r)

        print('triangulation sucessful for reach ' + str(r))

        # find overlapping regions
        overlap_r = []
        ov = []
        for r2 in range(0, r):
            if ikle_all[r] is not None and ikle_all[r2] is not None:
                ind_ikle1 = ikle_all[r].flatten()
                ind_ikle2 = ikle_all[r2].flatten()
                ov = np.intersect1d(ind_ikle1, ind_ikle2)
                overlap_r.extend(ov)
        overlap.append(np.array(overlap_r))

        # get the centroid of the grid elements
        point_here = np.array(point_all_reach[r])
        # reshape allows for a quicker selection
        try:
            ikle_here = np.reshape(ikle_all[r], (len(ikle_all[r]) * 3, 1))
            p1s = point_here[ikle_here[::3]]
            p2s = point_here[ikle_here[1::3]]
            p3s = point_here[ikle_here[2::3]]
            point_c = (p1s + p2s + p3s) / 3
            point_c = np.squeeze(np.array(point_c))  # why squeeze?
            point_c_all.append(point_c)
        except TypeError:
            print('Warning: Could not calculate centroid on one reach.\n')
            point_c_all.append([])

    if q:
        q.put(point_all_reach)
        q.put(ikle_all)
        q.put(lim_by_reach)
        q.put(hole_all_i)
        q.put(overlap)
        q.put(coord_pro)
        q.put(point_c_all)
        return
    else:
        return point_all_reach, ikle_all, lim_by_reach, hole_all_i, overlap, coord_pro, point_c_all


def create_grid_only_1_profile(coord_pro, nb_pro_reach=[0, 1e10], vh_pro_t=[], sub_pg=[], sub_dom=[], sub_per=[],
                               virtual_startend=False, divgiv=[], h0ok=False):
    """
    This function creates the grid from the coord_pro data using one additional profil in the middle. No triangulation.
    The interpolation of the data is done in this function also, contrarily to create_grid().

    :param coord_pro: the profile coordinates (x,y, h, dist along) the profile
    :param nb_pro_reach: the number of profile by reach
    :param vh_pro_t: the data with heigh and velocity, giving the river limits
    :param sub_pg: the data from the coarser substrate, in case the hydraulic model already contains substrate data
    :param sub_dom: the data from the dominant substrate, in case the hydraulic model already contains substrate data
    :param sub_per: the data from the subtrate in a percentage form
    :param virtual_startend: this indicates that the first and the lst profile is doubled. This is used so that the
           grid around the last and the first profile extend after or before this profile, so that all porfile have
           the same weight. Useful for LAMMI moslty.
    :param divgiv: in case we do not want to middle profile to be at an equal distance of both profile(one value by profile)
    :param h0ok: if we want to keep in the grid the cell with an height or velocity of zero (False usually)
    :return: the connevtivity table, the coordinate of the grid, the centroid of the grid, the velocity data on this
             grid, the height data on this grid.

    For more info on this function, see the document "More info on the grid".
    """
    point_all_reach = []
    ikle_all = []
    point_c_all = []

    # update coord_pro if we have data. Indeed, if velocity and water height is given, we only want wetted
    # perimeter and points where the velocity is given (might not be all profil points).
    inter_vel_all = []
    inter_height_all = []
    inter_dom_all = []
    inter_pg_all = []
    inter_per_all = []
    all_point_midx = []
    all_point_midy = []
    coord_pro_old = coord_pro
    if vh_pro_t:
        coord_pro = update_coord_pro_with_vh_pro(coord_pro, vh_pro_t)
    # double the first and the last profile (useful to gind "midlle

    b = time.time()

    # for each reach
    for r in range(0, len(nb_pro_reach) - 1):
        point_all = []
        ikle = []
        point_c = []
        inter_vel = []
        inter_height = []
        inter_sub_pg = []
        inter_sub_per = []
        inter_sub_dom = []
        if vh_pro_t:
            data_height_old = [val for val in vh_pro_t[nb_pro_reach[r]][1] for blob in (0, 1)]
            data_vel_old = [val for val in vh_pro_t[nb_pro_reach[r]][2] for blob in (0, 1)]
            if sub_pg:
                data_pg_old = [val for val in sub_pg[nb_pro_reach[r]] for blob in (0, 1)]
                data_dom_old = [val for val in sub_dom[nb_pro_reach[r]] for blob in (0, 1)]
                data_per_old = [val for val in sub_per[nb_pro_reach[r]] for blob in (0, 1)]

        for p in range(nb_pro_reach[r] + 1, nb_pro_reach[r + 1]):
            coord_pro_p0 = coord_pro[p - 1]
            coord_pro_p1 = coord_pro[p]

            # find the middle profile
            if len(coord_pro_p0[0]) > 0 and len(coord_pro_p1[0]) > 0:
                if divgiv:
                    [point_mid_x, point_mid_y] = find_profile_between(coord_pro_p0, coord_pro_p1, 1, False,
                                                                      divgiv[p - 1])
                else:
                    [point_mid_x, point_mid_y] = find_profile_between(coord_pro_p0, coord_pro_p1, 1, False)
                all_point_midx.extend([point_mid_x[0]])
                all_point_midy.extend([point_mid_y[0]])

            # create cells for the profile before the middle profile
            if p == nb_pro_reach[r] + 1 and virtual_startend:
                # if we have double profile ignore the first triangle line
                # draw it to get it, the idea is that each profil would weight equally.
                pass
            else:
                if len(coord_pro_p0[0]) > 0:  # just to check
                    # wet profile
                    if vh_pro_t:
                        [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p0,
                                                                                                  vh_pro_t[p - 1],
                                                                                                  point_mid_x,
                                                                                                  point_mid_y,
                                                                                                  point_all, ikle,
                                                                                                  point_c, 1, h0ok)
                    # whole profile
                    else:
                        [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p0,
                                                                                                  vh_pro_t, point_mid_x,
                                                                                                  point_mid_y,
                                                                                                  point_all, ikle,
                                                                                                  point_c, 1)
                if vh_pro_t:
                    inter_vel += data_vel_old
                    inter_height += data_height_old
                    if sub_pg:
                        inter_sub_pg += data_pg_old
                        inter_sub_dom += data_dom_old
                        inter_sub_per += data_per_old
            #  create cells for the profile after the middle profile
            if p == nb_pro_reach[r + 1] - 1 and virtual_startend:
                # if we have double profile ignore the last triangle line
                pass
            else:
                if len(coord_pro_p1[0]) > 0:
                    if vh_pro_t:
                        [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p1,
                                                                                                  vh_pro_t[p],
                                                                                                  point_mid_x,
                                                                                                  point_mid_y,
                                                                                                  point_all, ikle,
                                                                                                  point_c, -1, h0ok)
                    else:
                        [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p1,
                                                                                                  vh_pro_t, point_mid_x,
                                                                                                  point_mid_y,
                                                                                                  point_all, ikle,
                                                                                                  point_c, -1)
                # get the data
                if vh_pro_t:
                    data_height = [val for val in vh_pro_t[p][1] for blob in (0, 1)]
                    # was used for created the island, not needed
                    # because the island information is contained in ikle
                    # be caseful in case where it do not work
                    # data_height = [val for val in data_height0 if val > 0]  # island
                    data_vel = [val for val in vh_pro_t[p][2] for blob in (0, 1)]
                    # data_vel = [j for (i, j) in zip(data_height0, data_vel) if i > 0]
                    inter_vel += data_vel
                    inter_height += data_height
                    data_vel_old = data_vel
                    data_height_old = data_height
                    if sub_pg:
                        data_pg = [val for val in sub_pg[p] for blob in (0, 1)]
                        data_dom = [val for val in sub_dom[p] for blob in (0, 1)]
                        data_per = [val for val in sub_per[p] for blob in (0, 1)]
                        inter_sub_pg += data_pg
                        inter_sub_dom += data_dom
                        inter_sub_per += data_per
                        data_pg_old = data_pg
                        data_dom_old = data_dom
                        data_per_old = data_per
        point_all_reach.append(np.array(point_all))
        point_c_all.append(np.array(point_c))
        # possible check which could be added:
        # take out triangle with an area hwich is smaller than a certain threshold
        if sub_pg:
            if len(ikle) != len(inter_sub_dom) or len(ikle) != len(inter_sub_pg):
                print('Warning: the length of the subtrate data and ikle is not coherent \n')
        ikle_all.append(np.array(ikle))
        if vh_pro_t:
            inter_vel_all.append(np.array(inter_vel))
            inter_height_all.append(np.array(inter_height))
            if sub_pg:
                inter_dom_all.append(np.array(inter_sub_dom))
                inter_pg_all.append(np.array(inter_sub_pg))
                inter_per_all.append(np.array(inter_sub_per))

        # useful to control the middle profile 9\(added between two profiles)
        # plt.figure()
        # for er in range(0, len(all_point_midy)):
        #     if er%3 == 0:
        #         plt.plot(all_point_midx[er], all_point_midy[er], '.m')
        #     if er % 3 == 1:
        #         plt.plot(all_point_midx[er], all_point_midy[er], '.g')
        #     if er % 3 == 2:
        #         plt.plot(all_point_midx[er], all_point_midy[er], '.y')
        # for p in range(0, len(coord_pro)):
        #     plt.plot(coord_pro[p][0], coord_pro[p][1], '.b')
        # for p in range(0, len(p_not_found)):
        # plt.plot(p_not_found[p][0], p_not_found[p][1], '.r')
        # plt.show()

    if sub_pg:
        return ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all, inter_dom_all, inter_pg_all, \
               inter_per_all
    else:
        return ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all


def get_new_point_and_cell_1_profil(coord_pro_p, vh_pro_t_p, point_mid_x, point_mid_y, point_all, ikle, point_c, dir,
                                    h0ok=False):
    """
    This function is use by create_grid_one_profile. It creates the grid for one profile (one "line" of triangle).
    To create the whole grod this function is called for each profile.

    :param coord_pro_p: the coordinates of the profile
    :param vh_pro_t_p: the height and velocity data of the profile analysed
    :param point_mid_x: the x coodinate of the points forming the middle profile
    :param point_mid_y: the y coordinate of the points forming the middle profile
    :param point_all: the point of the grid
    :param ikle: the connectivity table of the grid
    :param point_c: the central point of each cell
    :param dir: in which direction are we going around the profile (upstream/downstram)
    :param h0ok: if True, cell with a water height or a velocity of zero are kept
    :return: point_all, ikle, point_c (the centroid of the cell)

    For more info, see the document "More info on the grid".
    """

    p_not_found = []
    pc = []
    pc0 = []
    inter = False
    far = 1e4 * abs(coord_pro_p[0][-1] - coord_pro_p[0][0])
    if far == 0:
        far = 1e4
    warn_cell = True

    # elongate midlle profile
    dirmidx = point_mid_x[0][-1] - point_mid_x[0][0]
    dirmidy = point_mid_y[0][-1] - point_mid_y[0][0]
    norm = np.sqrt(dirmidx ** 2 + dirmidy ** 2)
    a1 = point_mid_x[0][0] - dirmidx * far / norm
    a2 = point_mid_y[0][0] - dirmidy * far / norm
    a3 = point_mid_x[0][-1] + dirmidx * far / norm
    a4 = point_mid_y[0][-1] + dirmidy * far / norm
    point_mid_x = np.hstack(([a1], point_mid_x[0], [a3]))
    point_mid_y = np.hstack(([a2], point_mid_y[0], [a4]))

    # get a vector perpendicular to the profile
    diffx = coord_pro_p[0][0] - coord_pro_p[0][-1]
    diffy = coord_pro_p[1][0] - coord_pro_p[1][-1]
    norm = np.sqrt(diffx ** 2 + diffy ** 2)
    if norm > 0:
        nx = diffy / norm
        ny = - diffx / norm
    elif norm == 0:
        print('Warning: Found division by zero. \n')
        nx = ny = 1

    # add the cells and points to point_all and ikle
    mi = 0
    for s0 in range(1, len(coord_pro_p[0])):

        # find which part of the middle profile to use
        xafter = coord_pro_p[0][s0] - far * nx * dir
        yafter = coord_pro_p[1][s0] - far * ny * dir
        xbefore = coord_pro_p[0][s0] + nx * dir * far
        ybefore = coord_pro_p[1][s0] + ny * dir * far
        p1hyd = [xbefore, ybefore]
        p2hyd = [xafter, yafter]
        if mi > 3:  # to optimize
            mi -= 2
        for m in range(0, len(point_mid_x) - 1):  # to be optimized
            if max(point_mid_x[mi], point_mid_x[mi + 1]) >= min(p1hyd[0], p2hyd[0]) \
                    and max(point_mid_y[mi], point_mid_y[mi + 1]) >= min(p1hyd[1], p2hyd[1]):
                p1 = [point_mid_x[mi], point_mid_y[mi]]
                p2 = [point_mid_x[mi + 1], point_mid_y[mi + 1]]
                [inter, pc] = intersection_seg(p1hyd, p2hyd, p1, p2, False)  # do not change this to True (or check)
                if inter:
                    break
            mi += 1
            if mi > len(point_mid_x) - 2:
                mi = 0

        if not inter:
            pass
            # print('Warning: Point not found')
            # plt.figure()
            # plt.plot()
            # plt.plot(p1hyd[0], p1hyd[1], 'xb')
            # plt.plot(p2hyd[0], p2hyd[1], 'xb')
            # plt.plot([p1hyd[0], p2hyd[0]],[p1hyd[1], p2hyd[1]])
            # plt.plot(point_mid_x, point_mid_y,'.r')
            # plt.plot(coord_pro_p[0], coord_pro_p[1], '-k')
            # plt.show()
            # return
        if s0 == 1:
            xafter = coord_pro_p[0][0] - far * nx * dir
            yafter = coord_pro_p[1][0] - far * ny * dir
            xbefore = coord_pro_p[0][0] + nx * dir * far
            ybefore = coord_pro_p[1][0] + ny * dir * far
            p1hyd = [xbefore, ybefore]
            p2hyd = [xafter, yafter]
            m0 = 0  # x coord
            for m in range(m0, len(point_mid_x) - 1):  # to be optimized
                if max(point_mid_x[m], point_mid_x[m + 1]) >= min(p1hyd[0], p2hyd[0]) \
                        and max(point_mid_y[m], point_mid_y[m + 1]) >= min(p1hyd[1], p2hyd[1]):
                    p1 = [point_mid_x[m], point_mid_y[m]]
                    p2 = [point_mid_x[m + 1], point_mid_y[m + 1]]
                    [inter, pc0] = intersection_seg(p1hyd, p2hyd, p1, p2,
                                                    False)  # do not change this to True (or check)
                    if inter:
                        break
            if not inter:
                pass
                # print('Warning: Point not found')
            try:
                point_all.append([pc0[0][0], pc0[0][1]])
            except IndexError:
                if warn_cell:
                    print('Warning: one cell or more is erased. (1) \n')
                    warn_cell = False
                point_all.append([coord_pro_p[0][0], coord_pro_p[1][0]])
            point_all.append([coord_pro_p[0][0], coord_pro_p[1][0]])
        point_all.append([coord_pro_p[0][s0], coord_pro_p[1][s0]])
        try:
            point_all.append([pc[0][0], pc[0][1]])
        except IndexError:
            if warn_cell:
                print('Warning: one cell or more is erased. (2) \n')
                warn_cell = False
            point_all.append([coord_pro_p[0][0], coord_pro_p[1][0]])
        # add the two new cells to ikle and point_c
        if vh_pro_t_p:
            if vh_pro_t_p[1][s0] >= 0:
                if (vh_pro_t_p[1][s0] > 0 and vh_pro_t_p[1][s0 - 1] > 0) or h0ok:  #
                    l = len(point_all) - 1
                    if s0 == 1:
                        ikle.append([l, l - 3, l - 2])
                        cx = (point_all[l][0] + point_all[l - 3][0] + point_all[l - 2][0]) / 3
                        cy = (point_all[l][1] + point_all[l - 3][1] + point_all[l - 2][1]) / 3
                        point_c.append([cx, cy])
                    else:
                        ikle.append([l - 1, l - 3, l - 2])
                        cx = (point_all[l - 1][0] + point_all[l - 3][0] + point_all[l - 2][0]) / 3
                        cy = (point_all[l - 1][1] + point_all[l - 3][1] + point_all[l - 2][1]) / 3
                        point_c.append([cx, cy])
                    ikle.append([l - 1, l - 2, l])
                    cx = (point_all[l - 1][0] + point_all[l - 2][0] + point_all[l][0]) / 3
                    cy = (point_all[l - 1][1] + point_all[l - 2][1] + point_all[l][1]) / 3
                    point_c.append([cx, cy])
        else:
            l = len(point_all) - 1
            if s0 == 1:
                ikle.append([l, l - 3, l - 2])
                cx = (point_all[l][0] + point_all[l - 3][0] + point_all[l - 2][0]) / 3
                cy = (point_all[l][1] + point_all[l - 3][1] + point_all[l - 2][1]) / 3
                point_c.append([cx, cy])
            else:
                ikle.append([l - 1, l - 3, l - 2])
                cx = (point_all[l - 1][0] + point_all[l - 3][0] + point_all[l - 2][0]) / 3
                cy = (point_all[l - 1][1] + point_all[l - 3][1] + point_all[l - 2][1]) / 3
                point_c.append([cx, cy])
            ikle.append([l - 1, l - 2, l])
            cx = (point_all[l - 1][0] + point_all[l - 2][0] + point_all[l][0]) / 3
            cy = (point_all[l - 1][1] + point_all[l - 2][1] + point_all[l][1]) / 3
            point_c.append([cx, cy])

    return point_all, ikle, point_c, p_not_found


def cut_2d_grid_all_reach(ikle_all, point_all, inter_height_all, inter_vel_all, min_height=0.001, get_ind_new=False):
    """
    This function si just use to call cut_2d-grid for all reach. So that if we have a river with more than reach, we
    do not need to add a for loops to call for all reach. Sometime it can save place. This can be only use for one
    time step.

    :param ikle_all: the connectivity table of the 2D grid for all reach
    :param point_all: the coordinate of the points for all reach
    :param inter_height_all: the water height data given on the nodes for all reach
    :param inter_vel_all: the velcoity given on the nodes for all reach
    :param min_height: the minimum water height which is kept inthe grid
    :param get_ind_new: If True, a list is returned which give the indices of the old cell in the order of the new cells
           One list by reach (so a list of np.array is returned)
    :return: the update connectivity table, the coodinate of the point, the height of the water and the
             velocity on the updated grid fro all reaches
    """

    ikle_all_new = []
    point_all_new = []
    inter_height_all_new = []
    inter_vel_all_new = []
    ind_new_all = []

    for r in range(0, len(ikle_all)):
        if not get_ind_new:
            [ikle, point_reach, inter_height, inter_vel] = cut_2d_grid(ikle_all[r], point_all[r], inter_height_all[r],
                                                                       inter_vel_all[r], min_height=min_height)
        else:
            [ikle, point_reach, inter_height, inter_vel, ind_new] = cut_2d_grid(ikle_all[r], point_all[r],
                                                                                inter_height_all[r], inter_vel_all[r],
                                                                                min_height=min_height, get_ind_new=True)
            ind_new_all.append(ind_new)
        ikle_all_new.append(ikle)
        point_all_new.append(point_reach)
        inter_height_all_new.append(inter_height)
        inter_vel_all_new.append(inter_vel)

    if get_ind_new:
        return ikle_all_new, point_all_new, inter_height_all_new, inter_vel_all_new, ind_new_all
    else:
        return ikle_all_new, point_all_new, inter_height_all_new, inter_vel_all_new


#@profileit
def cut_2d_grid(ikle, point_all, water_height, velocity, progress_value, delta, CutMeshPartialyDry, min_height=0.001):
    """
    This function cut the grid of the 2D model to have correct wet surface. If we have a node with h<0 and other node(s)
    with h>0, this function cut the cells to find the wetted part, assuming a constant water elevation in the mesh.
    All mesh entierly dry are always cuted. if CutMeshPartialyDry is True, partialy dry mesh are also cuted.
    This function works for one unit of a reach.

    :param ikle: the connectivity table of the 2D grid
    :param point_all: the coordinate of the points
    :param water_height: the water height data given on the nodes
    :param velocity: the velocity given on the nodes
    :param min_height: the minimum water height considered (as model sometime have cell with very low water height)
    :param CutMeshPartialyDry: If True partialy dry mesh are cuted
    :return: the update connectivity table, the coordinates of the point, the height of the water and the
             velocity on the updated grid and the indices of the old connectivity table in the new cell orders.
    """
    typeikle = ikle.dtype
    typepoint = point_all.dtype
    failload = False, False, False, False, False
    point_new = np.empty((0, 3), dtype=typepoint)
    jpn0 = len(point_all) - 1
    iklenew = np.empty((0, 3), dtype=typeikle)
    ind_whole = np.arange(len(ikle), dtype=typeikle)

    # progress
    prog = progress_value.value
    delta2 = delta / len(ikle)

    water_height[water_height < min_height] = 0  # correcting the height of water  hw<0 or hw <min_height=> hw=0
    bhw = (water_height > 0).astype(np.int)
    ikle_bit = bhw[ikle]
    ikle_type = np.sum(ikle_bit, axis=1)  # list of meshes characters 0=dry 3=wet 1 or 2 = partially wet
    mikle_keep = ikle_type ==3
    mikle_keep2 = ikle_type != 0
    ipt_all_ok_wetdry = []
    # all meshes are entirely wet
    if all(mikle_keep):
        print('Warning: All meshes are entirely wet on one of the timestep.')
        iklekeep=ikle
        point_all_ok=point_all
        water_height_ok=water_height
        velocity_ok=velocity
        ind_whole = ind_whole  # TODO: full whole profile
    # all meshes are entirely dry
    elif not True in mikle_keep2:
        #print('Error: all meshes are entirely dry')
        return True, True, True, True, True
    # only the dry meshes are cut (but not the partially ones)
    elif not CutMeshPartialyDry:
        mikle_keep = ikle_type != 0
        iklekeep = ikle[mikle_keep, ...]
        ind_whole = ind_whole[mikle_keep, ...]
    # we cut  the dry meshes and  the partially ones
    else:
        jpn = jpn0
        ind_whole2 = []
        for i, iklec in enumerate(ikle):
            # progress
            prog += delta2
            progress_value.value = int(prog)
            if ikle_type[i] == 1 or ikle_type[i] == 2:
                sumk, nboverdry, bkeep = 0, 0, True
                ia, ib, ic = ikle[i]
                pa = point_all[ia]
                pb = point_all[ib]
                pc = point_all[ic]
                ha = water_height[ia]
                hb = water_height[ib]
                hc = water_height[ic]
                p1, overdry, koverdry = linear_z_cross(pa, pb, ha, hb)
                if overdry > 0:
                    nboverdry = nboverdry + 1
                    if koverdry > 1: bkeep = False
                if len(p1) > 0:
                    sumk = sumk + 1
                p2, overdry, koverdry = linear_z_cross(pb, pc, hb, hc)
                if overdry > 0:
                    nboverdry = nboverdry + 1
                    if koverdry > 1: bkeep = False
                if len(p2) > 0:
                    sumk = sumk + 2
                p3, overdry, koverdry = linear_z_cross(pc, pa, hc, ha)
                if overdry > 0:
                    nboverdry = nboverdry + 1
                    if koverdry > 1: bkeep = False
                if len(p3) > 0:
                    sumk = sumk + 3
                if nboverdry > 0:
                    if bkeep: mikle_keep[i] = True  # keeping the mesh we can't split
                else:
                    if sumk == 5:
                        point_new = np.append(point_new, np.array([p2, p3]), axis=0)
                        if hc == 0:
                            iklenew = np.append(iklenew, np.array([[ia, jpn + 1, jpn + 2], [ia, ib, jpn + 1]]), axis=0)
                            ipt_all_ok_wetdry.extend([ia, ib])
                            ind_whole2.extend([i, i])
                        else:
                            iklenew = np.append(iklenew, np.array([[jpn + 2, jpn + 1, ic]]), axis=0)
                            ipt_all_ok_wetdry.append(ic)
                            ind_whole2.append(i)
                    elif sumk == 4:
                        point_new = np.append(point_new, np.array([p1, p3]), axis=0)
                        if ha == 0:
                            iklenew = np.append(iklenew, np.array([[jpn + 1, ib, jpn + 2], [ib, ic, jpn + 2]]), axis=0)
                            ipt_all_ok_wetdry.extend([ic, ib])
                            ind_whole2.extend([i, i])
                        else:
                            iklenew = np.append(iklenew, np.array([[ia, jpn + 1, jpn + 2]]), axis=0)
                            ipt_all_ok_wetdry.append(ia)
                            ind_whole2.append(i)
                    elif sumk == 3:
                        point_new = np.append(point_new, np.array([p1, p2]), axis=0)
                        if hb == 0:
                            iklenew = np.append(iklenew, np.array([[jpn + 1, jpn + 2, ia], [ia, jpn + 2, ic]]), axis=0)
                            ipt_all_ok_wetdry.extend([ia, ic])
                            ind_whole2.extend([i, i])
                        else:
                            iklenew = np.append(iklenew, np.array([[ib, jpn + 2, jpn + 1]]), axis=0)
                            ipt_all_ok_wetdry.append(ib)
                            ind_whole2.append(i)
                    else:
                        print("impossible case during cut_2d_grid")
                        return failload
                    jpn += 2

        iklekeep = ikle[mikle_keep, ...]  # only the original entirely wetted meshes and meshes we can't split( overwetted ones )
        ind_whole = ind_whole[mikle_keep, ...]
        ind_whole = np.append(ind_whole, np.asarray(ind_whole2, dtype=typeikle), axis=0)

    ipt_iklenew_unique = np.unique(iklekeep)

    if ipt_all_ok_wetdry:  # presence of partially wet/dry meshes cutted that we want
        ipt_iklenew_unique = np.append(ipt_iklenew_unique, np.asarray(ipt_all_ok_wetdry, dtype=typeikle), axis=0)
        ipt_iklenew_unique = np.unique(ipt_iklenew_unique)

    point_all_ok = point_all[ipt_iklenew_unique]  # select only the point of the selectionned meshes
    water_height_ok = water_height[ipt_iklenew_unique]
    velocity_ok = velocity[ipt_iklenew_unique]
    ipt_old_new = np.array([-1] * len(point_all))
    for i, point_index in enumerate(ipt_iklenew_unique):
        ipt_old_new[point_index] = i
    iklekeep2 = ipt_old_new[ikle]
    iklekeep = iklekeep2[mikle_keep, ...]  # only the meshes selected with the new point index
    if ipt_all_ok_wetdry:  # in case no partially wet/dry meshes
        # delete dupplicate of the new point set
        point_new_single, ipt_new_new2 = np.unique(point_new, axis=0, return_inverse=True)
        ipt_old_new = np.append(ipt_old_new, ipt_new_new2 + len(point_all_ok), axis=0)
        iklekeep = np.append(iklekeep, ipt_old_new[iklenew], axis=0)
        point_all_ok = np.append(point_all_ok, point_new_single, axis=0)
        u, c = np.unique(point_all_ok, return_counts=True, axis=0)
        dup = u[c > 1]
        if len(dup) != 0:
            # TODO: remove created duplicate with cut2d
            print("duplciate apres append", dup)
            print("u", u)
            print("c", c)
        water_height_ok = np.append(water_height_ok, np.zeros(len(point_new_single), dtype=water_height.dtype), axis=0)
        velocity_ok = np.append(velocity_ok, np.zeros(len(point_new_single), dtype=velocity.dtype), axis=0)

    return iklekeep, point_all_ok, water_height_ok, velocity_ok, ind_whole


def linear_z_cross(p1, p2, h1, h2):
    """
    This function is called by cut_2D_grid. It find the intersection point along a side of the triangle if part of a
    cells is 'dry'.

    :param p1: the coordinate (x,y,z) of the first point
    :param p2: the coordinate (x,y,z) of the second point
    :param h1: the water height at p1 (might be 0 or positive)
    :param h2: the water height at p2 (might be 0 or positive)
    :return: the intersection point and a overdry that characterize the 'hydraulic' validity of  the side
    ie the height of water measure above a 'dry' node when we assume that the water surface is plane
    """
    pm = []
    overdry = 0
    koverdry = 0
    if not ((h1 == 0 and h2 == 0) or (h1 > 0 and h2 > 0)):
        if (h1 == 0 and p2[2] + h2 > p1[2]) or (h2 == 0 and p1[2] + h1 > p2[2]) or (p1[2] == p2[2]):
            overdry = abs(p2[2] + h2 - p1[2] - h1)
            koverdry = overdry / (h2 + h1)
        else:
            if h2 == 0:
                zm = p1[2] + h1
                k = (zm - p1[2]) / (p2[2] - p1[2])
                pm = [(k * (p2[0] - p1[0]) + p1[0]), (k * (p2[1] - p1[1]) + p1[1]), zm]
            else:
                zm = p2[2] + h2
                k = (zm - p2[2]) / (p1[2] - p2[2])
                pm = [(k * (p1[0] - p2[0]) + p2[0]), (k * (p1[1] - p2[1]) + p2[1]), zm]
    return pm, overdry, koverdry


def update_coord_pro_with_vh_pro(coord_pro, vh_pro_t):
    """
    The points describing the profile elevation and the points where velocity is measured might not be the same.
    Additionally,part of the profile might be dry and we have added points giving the wetted limit in vh_pro_t. They were
    are not in the original profil (coord_pro). In this function,
    coord_pro is recalculated to account for these modicfications. It is used by create_grid() and
    create_grid_one_profile, but only if vh_pro_t exists.

    :param coord_pro: the original coord_pro
    :param vh_pro_t: the value and position of h and velcoity measurement with the river limits
    :return: updated coord_pro

    More information in the document "More info on the grid" (linked above)
    """
    coord_pro_new = []
    coord_change = []
    for p in range(0, len(coord_pro)):
        # prep
        try:
            coord_pro_p1 = coord_pro[p]
        except IndexError:
            print('Error: a profile is empty. Could not be managed')
            return [-99]
        dist_all = np.array(vh_pro_t[p][0] - coord_pro_p1[3][0])
        dist_coordorr = np.array(coord_pro_p1[3] - coord_pro_p1[3][0])
        h_all = np.array(vh_pro_t[p][1])
        x = np.zeros((len(dist_all),))
        y = np.zeros((len(dist_all),))
        # get coodinate change between meter and (x,y) coordinates
        norm2 = np.sqrt((coord_pro_p1[0][-1] - coord_pro_p1[0][0]) ** 2 +
                        (coord_pro_p1[1][-1] - coord_pro_p1[1][0]) ** 2)
        dist_in_m = coord_pro_p1[3][-1] - coord_pro_p1[3][0]
        if dist_in_m == 0:
            coord_change.extend([1])
        else:
            coord_change.extend([norm2 / dist_in_m])
        # for loop is needed because profile not always straight
        # so nx and ny should be calculated more than once
        w = -99
        nx = ny = 0
        for d in range(0, len(dist_all)):
            # closest point on the original profile to the studied point d
            wold = w
            w = bisect.bisect(dist_coordorr, dist_all[d]) - 1
            if w < 0:  # case with negative ditance after correction of identical point
                w = 0
            if wold != w and w + 1 < len(coord_pro_p1[0]):
                # find the direction between the two point of the original profile
                norm = np.sqrt((coord_pro_p1[0][w + 1] - coord_pro_p1[0][w]) ** 2 +
                               (coord_pro_p1[1][w + 1] - coord_pro_p1[1][w]) ** 2)
                if norm == 0:
                    print('Warning: Two identical point in profile. Profile will be modified.\n')
                    coord_pro_p1[0][w] += 0.000001
                    coord_pro_p1[1][w] += 0.000001
                    norm = np.sqrt((coord_pro_p1[0][w + 1] - coord_pro_p1[0][w]) ** 2 +
                                   (coord_pro_p1[1][w + 1] - coord_pro_p1[1][w]) ** 2)
                nx = (coord_pro_p1[0][w + 1] - coord_pro_p1[0][w]) * (1 / norm)
                ny = (coord_pro_p1[1][w + 1] - coord_pro_p1[1][w]) * (1 / norm)
            x[d] = coord_pro_p1[0][w] + (dist_all[d] - dist_coordorr[w]) * nx * coord_change[p]
            y[d] = coord_pro_p1[1][w] + (dist_all[d] - dist_coordorr[w]) * ny * coord_change[p]
        coord_pro_new.append([x, y, h_all, dist_all])

    return coord_pro_new


def newp(p0, p1, extra_pro):
    """
    This function find the start/end of the added profile. If only one profile is needed, it is just the
    point in the middle of the start/end of the profile. If mroe than one profile is needed, there are linearly
    distributed. This function only give the start and the end of the profile, the profile in full are constructed using
    find_profile_between()

    :param p0: the point at the profile p
    :param p1: the point at the profile p-1
    :param extra_pro: the number of extra profile needed
    :return: the start/end of the new profile
    """
    new_p = np.zeros((extra_pro + 1, 2))  # why +1?????

    if p1[0] != p0[0]:
        a = (p1[1] - p0[1]) / (p1[0] - p0[0])
        b = p1[1] - a * p1[0]
        new_p[:, 0] = np.linspace(p0[0], p1[0], num=extra_pro + 1, endpoint=False)
        new_p[:, 1] = a * new_p[:, 0] + b
    else:
        new_p[:, 0] = p1[0]
        new_p[:, 1] = np.linspace(p0[1], p1[1], num=extra_pro + 1, endpoint=False)

    # extract the first point (p0)
    new_p = new_p[1:, :]
    return new_p


def inside_polygon(seg_poly, point):
    """
    This function find if a point is inside a polygon, using a ray casting algorythm.

    :param seg_poly: the segmentS forming the polygon
    :param point: the point which is indide or outside the polygon
    :return: True is the point is inside the polygon, false otherwise
    """

    xhyd = point[0]
    yhyd = point[1]
    poly_i = seg_poly
    intersect = 0
    inside_poly = False

    for i2 in range(0, len(poly_i)):
        [x1sub, y1sub] = poly_i[i2][0]
        [x2sub, y2sub] = poly_i[i2][1]

        # send ray is along the x direction, positif y = const
        # check if it is possible to have an interesection using <>
        if xhyd <= max(x1sub, x2sub) and min(y1sub, y2sub) <= yhyd <= max(y1sub, y2sub):
            # find the possible intersection
            if x1sub != x2sub:
                # case where the side of the triangle is on the "wrong side"
                # of xhyd even if xhyd <= max(x1sub,x2sub)
                if y1sub != y2sub:
                    a = (y1sub - y2sub) / (x1sub - x2sub)
                    x_int = (yhyd - y1sub) / a + x1sub  # (yhyd - (y1sub - x1sub *a)) / a
                else:
                    x_int = xhyd + 1000  # crossing if horizontal
            else:
                x_int = xhyd  # x1sub

            # if we have interesection
            if xhyd <= x_int:
                intersect += 1

            # manage the case where the yhyd is at the same height than subtrate (we want one intersection
            # and not two)
            if yhyd == y1sub or yhyd == y2sub:
                # manage the case where the yhyd is at the same height than subtrate
                if yhyd == y1sub:
                    if y2sub < yhyd:
                        intersect += 1
                elif yhyd == y2sub:
                    if y1sub < yhyd:
                        intersect += 1

                    # seg = seg.append(i2)
    # if number of intersection is odd, then point inside
    if intersect % 2 == 1:
        inside_poly = True

    # to debug
    # plt.figure()
    # for p in range(0, len(seg_poly)):
    #     plt.plot(seg_poly[p][0][0], seg_poly[p][0][1], '*b')
    #     plt.plot(seg_poly[p][1][0], seg_poly[p][1][1], '*b')
    # plt.plot(xhyd, yhyd,'r*')
    # plt.title(inside_poly)
    # plt.show()

    return inside_poly

    # the direction of the ray does not matter
    # ray = [point, [point[0], 1e5*abs(point[0])]]
    # inter_count = 0
    # idem = False # in case we have two identical mpoint -> only one intersection is needed
    # for s in range(0, len(seg_poly)):
    #     [inter, blob] = intersection_seg(seg_poly[s][0], seg_poly[s][1], ray[0], ray[1], False, 0)
    #
    #     # case with two identical points
    #     if seg_poly[s][1][0] == point[0] or seg_poly[s][0][0] == point[0]:
    #         if idem:
    #             inter_count -= 1
    #             idem = False
    #         else:
    #             idem = True
    #
    #     if inter:
    #         inter_count +=1
    # if inter_count % 2 == 0:
    #     return False
    # else:
    #     return True


def intersection_seg(p1hyd, p2hyd, p1sub, p2sub, col=True, wig=10e-8):
    """
    This function finds if there is an intersection between two segment (AB and CD). Idea from :
    http://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect
    It is based on the caluclaion of the cross-product z= 0 for 2D

    Careful there is many function using this function, so change here should be thought about. There is a precision
    management, so everythion smaller than 10**-8 is ok

    :param p1hyd: point A
    :param p2hyd: point B
    :param p1sub: point C
    :param p2sub: point D
    :param col: if True, colinear segment crossed. If false, they do not cross
    :param wig: "wiggle room", how precise should the calculation be (careful, complicated!)
    :return: intersect (True or False) and the crossing point (if True, empty is False)
    """
    inter = False
    x1hyd = p1hyd[0]
    x2hyd = p2hyd[0]
    y1hyd = p1hyd[1]
    y2hyd = p2hyd[1]
    x1sub = p1sub[0]
    x2sub = p2sub[0]
    y1sub = p1sub[1]
    y2sub = p2sub[1]
    pc = []  # the crossing point
    # if the start or the end of segment are the same, crossing if col is True
    # if col = False not crossing
    # find r and s such as r = psub - p2sub  and s = qhyd - q2hyd
    [sx, sy] = [x2hyd - x1hyd, y2hyd - y1hyd]
    [rx, ry] = [x2sub - x1sub, y2sub - y1sub]
    # check if they intersect using cross product (v x w=vx wy - vy wx)
    rxs = rx * sy - ry * sx
    #  (psub - qhyd) x r
    term2 = (x1hyd - x1sub) * ry - rx * (y1hyd - y1sub)
    # are the segment collinear? if yes crossing at start point if col, if not col, not crossing
    if rxs == 0 and term2 == 0:
        if col:
            inter = True
            pc.append([x1sub, y1sub])
            return inter, pc
    # calculate possible crossing point
    if rxs != 0:
        t = ((x1hyd - x1sub) * sy - sx * (y1hyd - y1sub)) / rxs
        u = term2 / rxs
    else:
        t = u = 10 ** 10
    # in this case, crossing
    if rxs != 0 and 0 - wig <= t <= 1 + wig and 0 - wig <= u <= 1 + wig:
        inter = True
        xcross = x1hyd + u * sx
        ycross = y1hyd + u * sy
        pc.append([xcross, ycross])

    return inter, pc


def add_point(point_all, point):
    """
    To manage the substrate data, we modify the hydrological grid to avoid to have cells with two substrate type.
    This function add one coordinate point to the list of coordinates which compose the hydrological grid. This point
    is the intersection between one side of one triangluar cell of the hydrological grid and one side of the
    sibstrate layer (which is a shp). It only adds this intersection point if it is not already in point_all.

    :param point_all: the coordinates of the hydrological grid
    :param point: one intersection point between substrat and hydrological grids
    :return: the updated point_all (the coordinates of the hydrological grid)
    """

    sum_sub = np.sum(abs(point_all - point), axis=1)
    if (sum_sub != 0).all():
        point_all = np.vstack((point_all, point))
        return point_all, len(point_all) - 1
    else:
        ind = np.where(sum_sub == 0)[0]

        return point_all, ind[0]


def get_crossing_segment_sub(p1sub, p2sub, lim_here, lim_by_reachr, point_all, island, ind_seg_sub_ini=[0]):
    """
    This function looks at one substrate segment and find the crossing points of this semgent with the different
    segment which composed the hydrological grid. This function is useful to cut the grid as a function of the form
    of the substrate layer (to avoid having cells in the hydrological grid which have two substrate value).

    If island switch is True, lim_here is the limit of the island, so
    inside the polygon is outside the river. If island is false, lim_here is the limit of the reach under investigation

    :param p1sub: the start point of the substrate semgent
    :param p2sub: the end point of the substrate segment
    :param lim_here: the reach?island limit given in the coordinate system
    :param lim_by_reachr: the limits for reach r which will be given to triangle given by point_all indices.
    :param point_all: all the point (ccordinates) which will be given to triangle
    :param island: a boolean indicating if we are on an island or not
    :param ind_seg_sub_ini: the indices of the first segment add by p1sub et p2sub by the reach. Only used island = true
    :return: the updated point_all and lim_by_reach
    """

    for seg in ind_seg_sub_ini:

        if island:
            p1sub = point_all[lim_by_reachr[seg][0]]
            p2sub = point_all[lim_by_reachr[seg][1]]
            to_delete = []
        cross_poly = False

        sp1 = []
        sp2 = []
        sp3 = []
        sp4 = []

        # test all segments in lim_here
        for w in range(0, len(lim_here)):
            p1rea = lim_here[w][0]
            p2rea = lim_here[w][1]
            [inter, pc] = intersection_seg(p1rea, p2rea, p1sub, p2sub)
            # for each sub segment find the crossing point and if limit are outside or inside
            if inter:
                cross_poly = True
                # find which point is outside and should be moved
                inside1 = inside_polygon(lim_here, p1sub)
                inside2 = inside_polygon(lim_here, p2sub)
                pc[0][0] *= 0.99999  # having point exactly on the vertex is not good for triangle
                pc[0][1] *= 0.99999
                # if insland inside and outise are
                if island:
                    inside1 = not inside1
                    inside2 = not inside2
                if inside1 and not inside2:
                    sp3.append(pc)
                elif inside2 and not inside1:
                    sp4.append(pc)
                elif inside2 and inside1:
                    sp1.append(pc)
                elif not inside1 and not inside2:
                    sp2.append(pc)
        # if seg sub is crossing none of the reach segment
        # check if inside or outside. If outside ignore
        # if inside add to the lim_by-reach
        if not cross_poly and not island:
            inside = inside_polygon(lim_here, p1sub)
            if inside:
                [point_all, ind1] = add_point(point_all, p1sub)
                [point_all, ind2] = add_point(point_all, p2sub)
                lim_by_reachr.append([ind1, ind2])

        # if the sub segment does not cross with an island, the only important case
        # is if the segment is totally inside the island, i.e.  inside1 and inside2 are true
        # We need to re-calculate inside1 and inside2 as they were switched before
        if not cross_poly and island:
            inside1 = inside_polygon(lim_here, p1sub)
            inside2 = inside_polygon(lim_here, p2sub)
            if inside1 and inside2:
                to_delete.append(seg)
                # lim_by_reachr.remove([p1sub, p2sub])

        # if crossing, add to lim_by_reach, case by case
        # we could have more than crossing by substrate segment
        if len(sp1) > 0:  # both p1sub and p2sub inside
            # in this case we need to order the points
            dist_to_sort = []
            for wp in range(0, len(sp1)):
                dist = np.sqrt((p1sub[0] - sp1[wp][0][0]) ** 2 + (p1sub[1] - sp1[wp][0][1]) ** 2)
                dist_to_sort.append(dist)
            ind_sp = np.argmin(dist_to_sort)
            dist_to_sort[ind_sp] = np.inf
            [point_all, ind1] = add_point(point_all, p1sub)
            [point_all, ind2] = add_point(point_all, sp1[ind_sp])
            lim_by_reachr.append([ind1, ind2])
            if len(sp1) > 2:  # case with mulitple crossing
                for w1 in range(1, len(sp1), 2):
                    ind_sp = np.argmin(dist_to_sort)
                    dist_to_sort[ind_sp] = np.inf
                    [point_all, ind1] = add_point(point_all, sp1[ind_sp])
                    [point_all, ind2] = add_point(point_all, sp1[ind_sp + 1])
                    lim_by_reachr.append([ind1, ind2])
            ind_sp = np.argmin(dist_to_sort)
            dist_to_sort[ind_sp] = np.inf
            [point_all, ind1] = add_point(point_all, sp1[ind_sp])
            [point_all, ind2] = add_point(point_all, p2sub)
            lim_by_reachr.append([ind1, ind2])
            if island:
                to_delete.append(seg)
        if len(sp2) > 0:  # both p1sub and p2sub outside
            if len(sp2) > 1:
                for w2 in range(0, len(sp1) - 1, 2):
                    [point_all, ind1] = add_point(point_all, sp2[w2])
                    [point_all, ind2] = add_point(point_all, sp2[w2 + 1])
                    lim_by_reachr.append([ind1, ind2])
            if island:
                to_delete.append(seg)
        if len(sp3) > 0:  # p1 inside, p2 outside
            [point_all, ind1] = add_point(point_all, p1sub)
            [point_all, ind2] = add_point(point_all, sp3[0])
            lim_by_reachr.append([ind1, ind2])
            if len(sp3) > 2:
                for w1 in range(1, len(sp3), 2):
                    [point_all, ind1] = add_point(point_all, sp3[w1])
                    [point_all, ind2] = add_point(point_all, sp3[w1 + 1])
                    lim_by_reachr.append([ind1, ind2])
            if island:
                to_delete.append(seg)
        if len(sp4) > 0:  # both p1sub and p2sub outside
            if len(sp4) > 1:
                for w2 in range(0, len(sp4) - 1, 2):
                    [point_all, ind1] = add_point(point_all, sp4[w2])
                    [point_all, ind2] = add_point(point_all, sp4[w2 + 1])
                    lim_by_reachr.append([ind1, ind2])
            [point_all, ind1] = add_point(point_all, sp4[-1])
            [point_all, ind2] = add_point(point_all, p2sub)
            lim_by_reachr.append([ind1, ind2])
            if island:
                to_delete.append(seg)

    if island and len(ind_seg_sub_ini) > 0:
        for d in sorted(to_delete, reverse=True):
            del lim_by_reachr[d]

    return point_all, lim_by_reachr


def interpo_linear(point_all, coord_pro, vh_pro_t):
    """
    Using scipy.gridata, this function interpolates the 1.5 D velocity and height to the new grid
    It can be used for only one time step. The interpolation is linear.
    It is usually called after create_grid have been called.

    :param point_all: the coordinate of the grid point
    :param coord_pro: the coordinate of the profile. It should be coherent with the coordinate from vh_pro.
           To insure this, pass coord_pro through the function "create_grid" with the same vh_pro as input
    :param vh_pro_t: for each profile, dist along the profile, water height and velocity at a particular time step
    :return: the new interpolated data for velocity and water height
    """

    inter_vel_all = []
    inter_height_all = []
    for r in range(0, len(point_all)):  # reaches
        point_p = point_all[r]
        if point_p is not None:
            # velocity
            x = []
            y = []
            values = []
            for p in range(0, len(coord_pro)):
                coord_pro_p = coord_pro[p]
                x.extend(coord_pro_p[0])
                y.extend(coord_pro_p[1])
                values.extend(vh_pro_t[p][2])
            xy = np.array([x, y]).T
            values = np.array(values)
            inter_vel = scipy.interpolate.griddata(xy, values, point_p, method='linear')
            # sometime value like -1e17 is added because of the machine precision, we do no want this
            inter_vel[np.isnan(inter_vel)] = 0
            inter_vel[inter_vel < 0] = 0
        else:
            inter_vel = []
        inter_vel_all.append(inter_vel)

        # height
        if point_p is not None:
            x = []
            y = []
            values = []
            for p in range(0, len(coord_pro)):
                coord_pro_p = coord_pro[p]
                x.extend(coord_pro_p[0])
                y.extend(coord_pro_p[1])
                values.extend(vh_pro_t[p][1])  # height here
            xy = np.array([x, y]).T
            values = np.array(values)
            inter_height = scipy.interpolate.griddata(xy, values, point_p, method='linear')
            # sometime value like -1e17 is added because of the machine precision, we do no want this
            inter_height[np.isnan(inter_height)] = 0
            inter_height[inter_height < 0] = 0
        else:
            inter_height = []
        inter_height_all.append(inter_height)

    return inter_vel_all, inter_height_all


def interpo_nearest(point_all, coord_pro, vh_pro_t):
    """
    Using scipy.gridata, this function interpolates the 1.5 D velocity and height to the new grid
    It can be used for only one time step. The interpolation is nearest neighbours.
    It is usually called after create_grid have been called.

    :param point_all: the coordinate of the grid point
    :param coord_pro: the coordinate of the profile. It should be coherent with the coordinate from vh_pro.
           To insure this, pass coord_pro through the function "create_grid" with the same vh_pro as input
    :param vh_pro_t: for each profile, dist along the profile, water height and velocity at a particular time step
    :return: the new interpolated data for velocity and water height
    """

    inter_vel_all = []
    inter_height_all = []
    for r in range(0, len(point_all)):  # reaches
        point_p = point_all[r]
        if point_p is not None:
            # velocity
            x = []
            y = []
            values = []
            for p in range(0, len(coord_pro)):
                coord_pro_p = coord_pro[p]
                x.extend(coord_pro_p[0])
                y.extend(coord_pro_p[1])
                values.extend(vh_pro_t[p][2])  # velocity
            xy = np.array([x, y]).T
            values = np.array(values)
            inter_vel = scipy.interpolate.griddata(xy, values, point_p, method='nearest')
            # sometime value like -1e17 is added because of the maching precision, we do no want this
            inter_vel[np.isnan(inter_vel)] = 0
            inter_vel[inter_vel < 0] = 0
        else:
            inter_vel = []
        inter_vel_all.append(inter_vel)

        # height
        if point_p is not None:
            x = []
            y = []
            values = []
            for p in range(0, len(coord_pro)):
                coord_pro_p = coord_pro[p]
                x.extend(coord_pro_p[0])
                y.extend(coord_pro_p[1])
                values.extend(vh_pro_t[p][1])  # height here
            xy = np.array([x, y]).T
            values = np.array(values)
            inter_height = scipy.interpolate.griddata(xy, values, point_p, method='nearest')
            # sometime value like -1e17 is added because of the maching precision, we do no want this
            inter_height[np.isnan(inter_height)] = 0
            inter_height[inter_height < 0] = 0
        else:
            inter_height = []
        inter_height_all.append(inter_height)

    return inter_vel_all, inter_height_all


def habby_grid_data(grid_new, grid_ori, vel_ori, height_ori):
    """
    HABBY interpolates values from cell-centered volumes (Finite Volume) to nodal values (mesh) using SciPy griddata
    :param grid_new: xy-coordinates of nodes (mesh)
    :param grid_ori: xy-coordinates of centroids (volume: triangle)
    :param vel_ori: original values of the water velocity computed on the volumes
    :param height_ori: original values of the water depth computed on the volumes
    :return: new values for the velocity and water depth computes on nodes
    """
    # vel_ori = np.array(vel_ori[0])
    # height_ori = np.array(height_ori[0])
    # grid_ori = np.array(grid_ori[0])

    # Velocity interpolation (default method: linear)
    vel_new = griddata(grid_ori, vel_ori, grid_new, method='linear')
    # Get the NaN from outer nodes and replace with the nearest values
    vel_nan = np.argwhere(np.isnan(vel_new))
    vel_new_nan = griddata(grid_ori, vel_ori, grid_new[vel_nan], method='nearest')
    vel_new[vel_nan] = vel_new_nan

    # Water depth interpolation
    height_new = griddata(grid_ori, height_ori, grid_new, method='linear')
    # Get the NaN from outer nodes and replace with the nearest values
    height_nan = np.argwhere(np.isnan(height_new))
    height_new_nan = griddata(grid_ori, height_ori, grid_new[height_nan], method='nearest')
    height_new[height_nan] = height_new_nan

    return vel_new, height_new


def finite_volume_to_finite_element_triangularxy(ikle, nodes, hmesh, vmesh, sub=''):
    """
    all the following parameters are numpy arrays
    :param ikle: the connectivity table 4 columns for quadrangular or triangular (las column value=-1)  meshes
    :param nodes: the x , y , z of the nodes
    :param hmesh: the height of water at the mesh center each column is a unit (time or discharge)
    :param vmesh: the mean velocity at the mesh center each column is a unit (time or discharge)
    :param sub: the substrate description for all meshes
    :return: ikle2, new connectivity table for a triangular mesh(x,y) with associate x , y , z :nodes2
                and new values for the velocity and water depth computes on nodes at each unit and also
                the substrate description for all meshes that is repeated in four triangles if given in a quadrangle

    """
    if type(sub)==np.ndarray:
        bsub=True
    else:
        bsub=False
    nbnodes0 = nodes.shape[0]
    nbmesh = ikle.shape[0]
    nbunit= hmesh.shape[1]
    #Building the new ikle by spliting each quadrangle to 4 triangles adding the center of the quadrangle to the node list
    #transforming   a set of triangles and 4angles into only triangles
    ikle3 = ikle[np.where(ikle[:, [3]] == -1)[0]]
    ikle4 = ikle[np.where(ikle[:, [3]] != -1)[0]]
    ikle2 = np.copy(ikle3[:, 0:3])
    nodes2=np.copy(nodes)
    if len(ikle4):  # partitionning each 4angles in 4 triangles
        nbnodes = nodes.shape[0]
        if bsub:
            sub4 = sub[np.where(ikle[:, [3]] != -1)[0]]
            sub = sub[np.where(ikle[:, [3]] == -1)[0]]
        for i in range(len(ikle4)):
            nbnodes += 1
            q0, q1, q2, q3 = ikle4[i][0], ikle4[i][1], ikle4[i][2], ikle4[i][3]
            ikle2 = np.append(ikle2, np.array([[q0, nbnodes - 1, q3], [q0, q1, nbnodes - 1],
                                               [q1, q2, nbnodes - 1], [nbnodes - 1, q2, q3]]),
                              axis=0)
            nodes2=np.append(nodes2, [np.mean(nodes[[q0, q1, q2, q3], :], axis=0)], axis=0)
            if bsub:
                sub = np.append(sub, np.array([sub4[i, :], ] * 4), axis=0)

    #calculating the coordinates x,y,z of the mesh centers
    p1 = nodes[ikle[:, 0], :]
    p2 = nodes[ikle[:, 1], :]
    p3 = nodes[ikle[:, 2], :]
    t = ikle[:, [3]]
    t[t == -1] = 0
    t[t != 0] = 1
    p4 = nodes[ikle[:, 3], :] * t
    xyzmesh34 = np.sum(np.hstack((p1, p2, p3, p4)).reshape(nbmesh, 4, 3), axis=1) / (t + 3)

    hnodes2all,vnodes2all=np.empty((nodes2.shape[0],nbunit), dtype=np.float64),np.empty((nodes2.shape[0],nbunit), dtype=np.float64)
    hzmeshall = hmesh + xyzmesh34[:, 2].reshape(nbmesh, 1)
    vmesh=np.abs(vmesh) # as we are not interpolating in vectors (we have lose the directionnal information) TODO ?
    #hvmeshall =hmesh* vmesh
    nbnodes2 = nodes2.shape[0]
    for i in range(nbunit):
        #interpolates values from cell-centered volumes (Finite Volume) to nodal values (mesh) using SciPy griddata
        # for a given unit : considering the water surface (z+h) to  find  z+h for nodes in the fully wetted part
        if np.sum(hmesh[:,i]>0)>2: # at least we need one triangle for griddata
            hznodes2 = griddata(xyzmesh34[:,(0,1)][hmesh[:,i]>0], hzmeshall[:,i][hmesh[:,i]>0], nodes2[:,(0,1)], method='linear')
        else:
            hznodes2 =np.full(nbnodes2, np.nan)
        # Get the hw+z of the NaN edges from first closed wetted meshes
        wetikle=ikle[hmesh[:,i]>0] # the wet ikle
        iwetikle=np.where(hmesh[:,i]>0)[0]
        awetikle=hznodes2[wetikle]
        awetikle[:, 3][np.where(wetikle[:, [3]] == -1)[0]] = -1 # a matrix of the wet meshes(each line) and th information about the 3 (& -1)or four nodes wiht nan values if their z+hw have not been calculated
        aawetikle=np.sum(awetikle,axis=1)# a column of wet meshes with the information if there is or not (nan) at least one nan nodes defining the mesh
        for j in range(len(aawetikle)):
            if np.isnan(aawetikle[j]):
                for k,l in enumerate(awetikle[j,:]):
                    if np.isnan(l):
                        if np.isnan(hznodes2[wetikle[j][k]]) :# TODO the mean value can be better here we just take the first mesh on the river side
                            hznodes2[wetikle[j][k]]=hzmeshall[:,i][iwetikle[j]] #giving the h+z value of the mesh center to the contouring node that we imagine on the river side
        hnodes2 = hznodes2 - nodes2[:, 2]
        hnodes2[np.isnan(hznodes2)]=0
        hnodes2[hnodes2<=0] = 0


        #for a given unit : considering the  surface of the elementary flow (h*v) to  find  v for nodes is too risky in a mesh with a node having a very small value the velocity at this node can be calculated as infinite
        #so interpolating velocity values
        if vmesh[:,i].shape[0]>2: # at least we need one triangle for griddata
            vnodes2 = griddata(xyzmesh34[:,(0,1)], vmesh[:,i], nodes2[:,(0,1)], method='linear')
        else:
            vnodes2 =np.full(nbnodes2, np.nan)
        # Get the NaN from outer nodes and replace with the nearest values
        vnodes2_nan = np.isnan(vnodes2)
        nodes2nan = nodes2[:, (0, 1)][vnodes2_nan]
        vnodes2_new_nan = griddata(xyzmesh34[:,(0,1)], vmesh[:,i], nodes2nan, method='nearest')
        vnodes2[vnodes2_nan] = vnodes2_new_nan
        vnodes2[hnodes2==0]=0 # get realistic
        hnodes2all[:,i], vnodes2all[:,i]=hnodes2,vnodes2
    # giving the exact values of depth and velocity in the quadrangular mesh centers nodes
    #TODO not to do previously this job  above TAKE CARE that if you got just one quadrangle or similar situation
    # only the following part will give the correct result
    if len(ikle4):
        hnodes4all=hmesh[np.where(ikle[:, [3]] != -1)[0]]
        vnodes4all = vmesh[np.where(ikle[:, [3]] != -1)[0]]
        hnodes4all[hnodes4all <= 0] = 0
        vnodes4all[hnodes4all == 0] = 0
        hnodes2all[nbnodes0:nbnodes2, :]=hnodes4all
        vnodes2all[nbnodes0:nbnodes2, :] = vnodes4all
    if bsub:
        return ikle2, nodes2,hnodes2all,vnodes2all,sub
    else:
        return ikle2, nodes2,hnodes2all,vnodes2all


def pass_grid_cell_to_node_lin(point_all, coord_c, vel_in, height_in, warn1=True, vtx_all=[], wts_all=[]):
    """
    HABBY uses nodal information. Some hydraulic models have only ouput on the cells. This function pass
    from cells information to nodal information. The interpolation is linear and the cell centroid is used as the
    point where the cell information is carried. It can be used for one time step only.

    This function is also used by hydraulic_chronic to pass from one discharge to another because each discharge
    has it own grid. Hence, we need to interpolate

    :param point_all: the coordinates of grid points (new grid here)
    :param coord_c: the coordintes of the centroid of the cells (old grid here)
    :param vel_in: the velocity data by cell
    :param height_in: the height data by cell
    :param warn1: if True , show the warning (usually warn1 is True for t=0, False afterwards)
    :param vtx_all: if it exists it means than the same grid was interpolated before. This info can be reused to
           speed up the interpolation of mulitple time step. (optional, need wts)
    :param wts_all: if it exists it means than the same grid was interpolated before. This info can be reused to
           speed up the interpolation of mulitple time step. (optional, need vtx)
    :return: velocity and height data by node

    **Technical Comment**

    This function can be very slow when a lot of time step needs to be interpolated if done directlty with
    scipy.interpolate. It was optimized for this case:
    http://stackoverflow.com/questions/20915502/speedup-scipy-griddata-for-multiple-
    interpolations-between-two-irregular-grids

    """

    vel_node = []
    height_node = []
    vtx_new = []
    wts_new = []
    print(len(point_all))

    for r in range(0, len(point_all)):  # reaches

        # this part is copied from http://stackoverflow.com/questions/20915502/speedup-scipy-griddata
        # -for-multiple-interpolations-between-two-irregular-grids. No sure on how it works
        # if no interpolation info was sent, re-start the whole interpolatin on a new grid
        if vtx_all == [] and wts_all == []:
            vtx, wts = interp_weights(coord_c[r], point_all[r])
        else:
            vtx = vtx_all[r]
            wts = wts_all[r]
        vtx_new.append(vtx)
        wts_new.append(wts)

        # velocity
        max_vel = max(vel_in[r])
        inter_vel = interpolate_opti(vel_in[r], vtx, wts)
        # sometime value like -1e17 is added because of the machine precision, we do no want this
        inter_vel[np.isnan(inter_vel)] = 0
        inter_vel[inter_vel < 0] = 0
        inter_vel[inter_vel > max_vel] = max_vel
        vel_node.append(inter_vel)

        # height
        max_height = max(height_in[r])
        inter_height = interpolate_opti(height_in[r], vtx, wts)
        # sometime value like -1e17 is added because of the machine precision, we do no want this
        inter_height[np.isnan(inter_height)] = 0
        inter_height[inter_height < 0] = 0
        inter_height[inter_height > max_height] = max_height
        height_node.append(inter_height)

    if warn1:
        print('Warning: The outputs data from the model were passed from cells to node by linear interpolation.\n')

    return vel_node, height_node, vtx_new, wts_new


def interp_weights(xyz, uvw):
    """
    This fucntion is used by the function pass_grid_cell_to_node_lin(). To optimize the interpolation when more than one time step
    is done on the same grid, the first step of scipy.griddata.interolate are done here and are called only once for all
    time step. Hence, this function is the first part of a quicker "scipy.interpolate.griddata"

    :param xyz:
    :param uvw:
    """
    d = 2
    tri = qhull.Delaunay(xyz)
    simplex = tri.find_simplex(uvw)
    vertices = np.take(tri.simplices, simplex, axis=0)
    temp = np.take(tri.transform, simplex, axis=0)
    delta = uvw - temp[:, d]
    bary = np.einsum('njk,nk->nj', temp[:, :d, :], delta)
    return vertices, np.hstack((bary, 1 - bary.sum(axis=1, keepdims=True)))


def interpolate_opti(values, vtx, wts):
    """
    This fucntion is called by interp_weights(). It is used in the optimization of the function pass_grid_cell_to_node_lin().
    This idea of this optimization is to not re-do some calculation when many interpolation are done on the same grid.

    :param values:
    :param vtx:
    :param wts:
    :param fill_value: A new value for point where
    """
    # ret = np.einsum('nj,nj->n', np.take(values, vtx), wts)
    # ret[np.any(wts < 0, axis=1)] = fill_value
    # return ret
    return np.einsum('nj,nj->n', np.take(values, vtx), wts)  # summation based on einstein notation


def find_profile_between(coord_pro_p0, coord_pro_p1, nb_pro, trim=True, divgiv=[]):
    """
    Find n profile between two profiles which are not straight. This functions is useful to create the grid from 1D model
    as profile in 1D model are often far away from another.

    :param coord_pro_p0: the coord_pro (x,y,h, z) of the first profile
    :param coord_pro_p1: the coord_pro (x,y,h, z) of the second profile
    :param nb_pro: the number of profile to add
    :param trim: If True cut the end and start of profile to avoid to have part of the grid outside of the water limit
    :param divgiv: one value by profile, used to not put the middle profile at an euql distance of two profile
    :return: a list with the updated profiles
    """

    mid_point_x = []
    mid_point_y = []
    far = 1000 * (abs(coord_pro_p0[0][-1] - coord_pro_p0[0][0]) + abs(coord_pro_p0[1][-1] - coord_pro_p0[1][0]))
    # find point forming the middle profile
    x0all = coord_pro_p0[0]
    y0all = coord_pro_p0[1]
    x1all = coord_pro_p1[0]
    y1all = coord_pro_p1[1]

    # create a straight line betwen two point
    x1 = x0all[0]
    y1 = y0all[0]
    x2 = x0all[-1]
    y2 = y0all[-1]

    # careful the equation is ax + by + c = 0 and not y = ax + b as usual
    # easier for the porjection formula
    if x1 != x2:
        a = (y1 - y2) / (x1 - x2)
    else:
        a = 1
    b = -1
    c = y1 - a * x1
    norm = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    nx = (y2 - y1) / norm
    ny = -(x2 - x1) / norm

    # !!! test!!!
    # norm = np.sqrt((x1all[0]-x1)**2+(y1all[0]-y1)**2)
    # nx = (x1all[0] - x1)/norm
    # ny = (y1all[0] - y1) / norm

    # project points from both profil perpendiculary on the line
    # from https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
    if a ** 2 + b ** 2 > 0:
        xpro0 = (b * (b * x0all - a * y0all) - a * c) / (a ** 2 + b ** 2)
        # ypro0 = (a * (-1*b* x0all + a * y0all) - b*c) / (a**2 + b**2)
        xpro1 = (b * (b * x1all - a * y1all) - a * c) / (a ** 2 + b ** 2)
        # ypro1 = (a * (-1*b * x1all + a * y1all) - b*c) / (a**2 + b**2)
    else:
        xpro0 = xpro1 = 10e10

    # get a longer line (to have intersection in all cases)
    # to avoid case whew the vector nearly touch each other
    xstart0 = x0all + far * nx
    xend0 = x0all - far * nx
    xstart1 = x1all + far * nx
    xend1 = x1all - far * nx
    ystart0 = y0all + far * ny
    yend0 = y0all - far * ny
    ystart1 = y1all + far * ny
    yend1 = y1all - far * ny

    # find intersection with the other profile
    point_inter0 = np.zeros((len(x0all), 2))
    point_inter1 = np.zeros((len(x1all), 2))
    no_inter0 = np.zeros((len(x0all),))
    no_inter1 = np.zeros((len(x1all),))
    # first profile
    s = 0
    for i in range(0, len(x0all)):
        if len(x1all) > 0 and len(x0all) > 0:
            inter = False
            # p1 = [x0all[i], y0all[i]]
            # p2 = [xpro0[i], ypro0[i]]
            p1 = [xstart0[i], ystart0[i]]
            p2 = [xend0[i], yend0[i]]
            for i2 in range(0, len(x1all) - 1):
                if max(x1all[i2], x1all[i2 + 1]) > min(p1[0], p2[0]) and max(y1all[i2], y1all[i2 + 1]) > min(p1[1],
                                                                                                             p2[1]):
                    p3 = [x1all[i2], y1all[i2]]
                    p4 = [x1all[i2 + 1], y1all[i2 + 1]]
                    [inter, pc] = intersection_seg(p1, p2, p3, p4, False)
                if inter:
                    point_inter0[i] = pc[0]
                    break
            # start/end of line
            if not inter:
                if len(x1all) > 4:
                    p3 = [x1all[-4], y1all[-4]]
                    p4 = [x1all[-1], y1all[-1]]
                else:
                    p3 = [x1all[0], y1all[0]]
                    p4 = [x1all[-1], y1all[-1]]
                norm = np.sqrt((p4[0] - p3[0]) ** 2 + (p4[1] - p3[1]) ** 2)
                p3x = p3[0] + far * (p4[0] - p3[0]) / norm
                p3y = p3[1] + far * (p4[1] - p3[1]) / norm
                p3 = [p3x, p3y]
                [inter, pc] = intersection_seg(p1, p2, p3, p4, False)
                if inter:
                    point_inter0[i] = pc[0]
            if not inter:
                if len(x1all) > 4:
                    p30 = [x1all[0], y1all[0]]
                    p4 = [x1all[4], y1all[4]]
                else:
                    p30 = [x1all[0], y1all[0]]
                    p4 = [x1all[1], y1all[1]]
                norm = np.sqrt((p4[0] - p30[0]) ** 2 + (p4[1] - p30[1]) ** 2)
                p3x = p30[0] + far * (p4[0] - p30[0]) / norm
                p3y = p30[1] + far * (p4[1] - p30[1]) / norm
                p3 = [p3x, p3y]
                [inter, pc] = intersection_seg(p1, p2, p3, p30, False)
                if inter:
                    point_inter0[i] = pc[0]
            if not inter:
                no_inter0[i] = -99
        # if not inter:
        #    print('Warning: No intersection found when created new profile. (1)')
        #     point_inter0[i] = point_inter0[i-1] + 0.001

    # intersection second profile
    for j in range(0, len(x1all)):
        inter = False
        p1 = [xstart1[j], ystart1[j]]
        p2 = [xend1[j], yend1[j]]
        for j2 in range(0, len(x0all) - 1):
            if max(x0all[j2], x0all[j2 + 1]) > min(p1[0], p2[0]) and max(y0all[j2], y0all[j2 + 1]) > min(p1[1], p2[1]):
                p3 = [x0all[j2], y0all[j2]]
                p4 = [x0all[j2 + 1], y0all[j2 + 1]]
                [inter, pc] = intersection_seg(p1, p2, p3, p4, False)
            if inter:
                point_inter1[j] = pc[0]
                break
        # start/end of line
        if not inter:
            if len(x0all) > 4:
                p3 = [x0all[-4], y0all[-4]]
                p4 = [x0all[-1], y0all[-1]]
            else:
                p3 = [x0all[-2], y0all[-2]]
                p4 = [x0all[-1], y0all[-1]]
            norm = np.sqrt((p4[0] - p3[0]) ** 2 + (p4[1] - p3[1]) ** 2)
            p3x = p3[0] + far * (p4[0] - p3[0]) / norm
            p3y = p3[1] + far * (p4[1] - p3[1]) / norm
            p3 = [p3x, p3y]
            [inter, pc] = intersection_seg(p1, p2, p3, p4, False)
            if inter:
                point_inter1[j] = pc[0]
        if not inter:
            if len(x0all) > 4:
                p30 = [x0all[0], y0all[0]]
                p4 = [x0all[4], y0all[4]]
            else:
                p30 = [x0all[0], y0all[0]]
                p4 = [x0all[1], y0all[1]]
            norm = np.sqrt((p4[0] - p30[0]) ** 2 + (p4[1] - p30[1]) ** 2)
            p3x = p30[0] - far * (p4[0] - p30[0]) / norm
            p3y = p30[1] - far * (p4[1] - p30[1]) / norm
            p3 = [p3x, p3y]
            [inter, pc] = intersection_seg(p1, p2, p3, p30, False)
            if inter:
                point_inter1[j] = pc[0]
        if not inter:
            no_inter1[j] = -99
        # if not inter:
        #     print('Warning: No intersection found when created new profile (2).')
        #     # plt.figure()
        #     # plt.plot()
        #     # plt.plot(p1[0], p1[1], '.b')
        #     # plt.plot(p2[0], p2[1], '.b')
        #     # plt.plot(p3[0], p3[1], '.g')
        #     # plt.plot(p[0], p[1], '.r')
        #     # plt.plot(p30[0], p30[1], '.k')
        #     # plt.plot(x1all, y1all, '-r')
        #     # plt.plot(x0all, y0all, '-m')
        #     # print(far * (p[0] - p30[0]))
        #     # plt.show()
        #     point_inter1[j] = point_inter1[j - 1] + 0.001

    # find points between the profile
    len0 = len(x0all[no_inter0 == 0])
    len1 = len(x1all[no_inter1 == 0])
    for n in range(0, nb_pro):
        pm_all = np.zeros((len0 + len1, 2))  # x, y, dist to be ordered
        if divgiv:
            div = divgiv
        else:
            div = (n + 1) / (nb_pro + 1)
        div2 = 1 - div

        # point linked with the first profile
        pm_all[:len0, 0] = x0all[no_inter0 == 0] + (point_inter0[no_inter0 == 0, 0] - x0all[no_inter0 == 0]) * div
        pm_all[:len0, 1] = y0all[no_inter0 == 0] + (point_inter0[no_inter0 == 0, 1] - y0all[no_inter0 == 0]) * div

        # point related to second profile
        pm_all[len0:, 0] = x1all[no_inter1 == 0] + (point_inter1[no_inter1 == 0, 0] - x1all[no_inter1 == 0]) * div2
        pm_all[len0:, 1] = y1all[no_inter1 == 0] + (point_inter1[no_inter1 == 0, 1] - y1all[no_inter1 == 0]) * div2

        if len1 + len0 == 0:
            print('Warning: Middle profile empty \n')

        # if the profile should not be bigger than it is
        if trim:

            # sort so tha each point is one after the other
            xpro = np.concatenate((xpro0[no_inter0 == 0], xpro1[no_inter1 == 0]), axis=0)
            pm_all = pm_all[xpro.argsort()]

            # control limits (important to not get a river bigger than it is)
            p2seg = [x0all[-1], y0all[-1]]
            p1seg = [x1all[-1], y1all[-1]]
            inter = False
            for w2 in range(0, len(pm_all[:, 0]) - 1):
                p3 = pm_all[w2]
                p4 = pm_all[w2 + 1]
                [inter, pc] = intersection_seg(p1seg, p2seg, p3, p4, False)
                if inter:
                    if x1 > x2:
                        pm_all = pm_all[w2 + 1:, :]
                    if x1 < x2:
                        pm_all = pm_all[:w2 + 1, :]
                    break
            p1seg = [x0all[0], y0all[0]]
            p2seg = [x1all[0], y1all[0]]
            for w in range(0, len(pm_all[:, 0]) - 1):
                p3 = pm_all[w]
                p4 = pm_all[w + 1]
                [inter, pc] = intersection_seg(p1seg, p2seg, p3, p4, False)
                if inter:
                    if x1 > x2:
                        pm_all = pm_all[:w + 1, :]
                    if x1 < x2:
                        pm_all = pm_all[w + 1:, :]
                    break

        # sort the points
        x1m = pm_all[0, 0]
        x2m = pm_all[-1, 0]
        y1m = pm_all[0, 1]
        y2m = pm_all[-1, 1]
        if x1m != x2m:
            a = (y1m - y2m) / (x1m - x2m)
        else:
            a = 1
        b = -1
        c = y1m - a * x1m
        xprojmid = (b * (b * pm_all[:, 0] - a * pm_all[:, 1]) - a * c) / (a ** 2 + b ** 2)
        pm_all = pm_all[xprojmid.argsort()]

        # control for the risk of a crossing segments
        norma = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        normb = np.sqrt((x1all[-1] - x1all[0]) ** 2 + (y1all[-1] - y1all[0]) ** 2)
        # cos(theta) = a.b / (norm(a) * norm(b))
        dota = ((x2 - x1) * (x1all[-1] - x1all[0]) + (y2 - y1) * (y1all[-1] - y1all[0])) / (norma * normb)
        if dota > 1 or dota < -1:
            theta = 0.5
        else:
            theta = np.arccos(dota)
        inter1 = True
        inter2 = True
        warn_here = True
        while (inter1 or inter2) and len(pm_all[:, 1]) > 3 and abs(theta) > 0.4:
            p3a = [pm_all[0, 0], pm_all[0, 1]]
            p4a = [pm_all[-1, 0], pm_all[-1, 1]]
            for i in range(0, min(len(x0all), len(x1all)) - 1):
                p1a = [x0all[i], y0all[i]]
                p2a = [x0all[i + 1], y0all[i + 1]]
                [inter1, pc] = intersection_seg(p1a, p2a, p3a, p4a, False)
                p1a = [x1all[i], y1all[i]]
                p2a = [x1all[i + 1], y1all[i + 1]]
                [inter2, pc] = intersection_seg(p1a, p2a, p3a, p4a, False)
                if inter1 or inter2:
                    if warn_here:
                        print('Warning: Correction for crossing middle profile')
                        warn_here = False
                    pm_all = pm_all[1:-1, :]
                    break

        mid_point_x.append(pm_all[:, 0])
        mid_point_y.append(pm_all[:, 1])

    return mid_point_x, mid_point_y


def create_dummy_substrate(coord_pro, sqrtnp):
    """
    For testing purposes, it can be useful to create a substrate input even if one does not exist.
    This substrate is compose of n triangle situated on the rivers in the same coodinates system.

    :param coord_pro: the coordinate of each profile
    :param sqrtnp: the number of point which will compose one side of the new substrate grid (so the total number
            of point is sqrtnb squared).
    :return: dummy coord_sub, ikle_sub
    """

    ikle_sub = []
    coord_sub = []
    # find (x,y) limit of reach
    maxy = -np.inf
    maxx = - np.inf
    miny = np.inf
    minx = np.inf
    for p in range(0, len(coord_pro)):
        minx_here = np.min(coord_pro[p][0])
        maxx_here = np.max(coord_pro[p][0])
        miny_here = np.min(coord_pro[p][1])
        maxy_here = np.max(coord_pro[p][1])
        if minx_here < minx:
            minx = minx_here
        if miny_here < miny:
            miny = miny_here
        if maxx_here > maxx:
            maxx = maxx_here
        if maxy_here > maxy:
            maxy = maxy_here
    if maxx == minx or miny == maxy:
        print('Error: no dummy substrate created. \n')
    # create new point on a rectangular grid
    distx = (maxx - minx) / (sqrtnp - 1)
    disty = (maxy - miny) / (sqrtnp - 1)
    x = np.arange(minx, maxx + distx, distx)
    y = np.arange(miny, maxy + disty, disty)
    for i in range(0, sqrtnp):
        for j in range(0, sqrtnp):
            coord_sub.extend([x[i], y[j]])

    dict_point = dict(vertices=coord_sub)
    grid_dict = triangle.triangulate(dict_point)  # 'p' would allos for constraint V for verbose

    ikle_sub = grid_dict['triangles']
    coord_sub = grid_dict['vertices']

    return ikle_sub, coord_sub


def plot_grid_simple(point_all_reach, ikle_all, project_preferences, name_hdf5, mesh=True, velocity=True, height=True,
                     inter_vel_all=[], inter_h_all=[], path_im=[], merge_case=False,
                     time_step=0, sub_pg=[], sub_dom=[]):
    """
    This is the function to plot grid output for one time step. The data is one the node. A more complicated function
    exists to plot the grid and additional information (manage-grid_8.plot_grid()) in case there are needed to debug.
    The present function only plot the grid and output without more information.

    :param point_all_reach: the coordinate of the point for this time step. This is given by reaches.
    :param ikle_all:  the connectivity table for this time step. This is given by reaches.
    :param project_preferences: the dictionary with the different options to create the figures
    :param inter_vel_all: the velcoity data. This is given by reaches.
    :param inter_h_all: the height data. This is given by reaches.
    :param path_im: the path where the figure should be saved
    :param merge_case: If True, we plot data from grid with merged substrate and hydrological data
    :param time_step: time step to be added to the title
    :param sub_pg: coarser data from the subtrate
    :param sub_dom: doominat data from the subtrate
    """
    # print(mesh, velocity, height, time_step)
    if not project_preferences:
        project_preferences = create_default_project_preferences_dict()

    # plot the grid, the velcoity and the water height
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = project_preferences['erase_id']

    if mesh:
        plt.figure()
        # the grid
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        for r in range(0, len(ikle_all)):
            # get data for this reach
            ikle = ikle_all[r]
            coord_p = point_all_reach[r]

            # prepare the grid
            if ikle is not None:  # case empty grid
                xlist = []
                ylist = []
                for i in range(0, len(ikle)):
                    pi = 0
                    ikle_i = ikle[i]
                    if len(ikle_i) == 3:
                        while pi < 2:  # we have all sort of xells, max eight sides
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

                plt.plot(xlist, ylist, '-b', linewidth=0.1)
                plt.ticklabel_format(useOffset=False)
                plt.axis('equal')
                # to add water value on grid point (usualy to debug)
                # for idx, c in enumerate(coord_p):
                #     plt.annotate(str(inter_h_all[r][idx]),c)
        if project_preferences['language'] == 0:
            plt.title(name_hdf5[:-3] + " : " + 'Computational Grid - Time Step ' + str(time_step))
        elif project_preferences['language'] == 1:
            plt.title(name_hdf5[:-3] + " : " + 'Maillage - Pas de Temps: ' + str(time_step))
        else:
            plt.title(name_hdf5[:-3] + " : " + 'Computational Grid - Time Step ' + str(time_step))
        plt.tight_layout()  # remove margin out of plot

        # save figures
        if merge_case:
            suffix = 'Merge_grid_t' + str(time_step) + '_'
        else:
            suffix = 'Hydro_grid_t' + str(time_step) + '_'
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(suffix, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:  # [0,1,2,3,4,5] currently existing format
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".pdf"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".jpg"), dpi=project_preferences['resolution'],
                            transparent=True)
        if format1 == 123456:  # "display"
            plt.show()
        else:  # "export"
            plt.cla()
            plt.clf()
            plt.close('all')

    # plot the interpolated velocity
    bounds = []
    # if time_step == -1:
    #     if project_preferences['language'] == 0:
    #         plt.title('Hydraulic Data - Last Time Step')
    #     elif project_preferences['language'] == 1:
    #         plt.title('Données Hydrauliques - Dernier Pas de Temps')
    # else:
    #     if project_preferences['language'] == 0:
    #         plt.title('Hydraulic Data - Time Step ' + str(time_step))
    #     elif project_preferences['language'] == 1:
    #         plt.title('Données Hydrauliques - Pas de Temps: ' + str(time_step))
    if velocity:
        if len(inter_vel_all) > 0:  # 0
            plt.figure()
            plt.ticklabel_format(useOffset=False)
            # plt.subplot(2, 1, 1)
            # get colormap limit
            cm = plt.cm.get_cmap(project_preferences['color_map'])
            mvc = 0.001
            for r in range(0, len(inter_vel_all)):
                inter_vel = inter_vel_all[r]
                if len(inter_vel) > 0:
                    mv = max(inter_vel)
                    if mv > mvc:
                        mvc = mv
            bounds = np.linspace(0, mvc, 15)
            # do the figure for all reach
            for r in range(0, len(inter_vel_all)):
                point_here = np.array(point_all_reach[r])
                inter_vel = inter_vel_all[r]
                if len(point_here[:, 1]) == len(inter_vel) and len(ikle_all[r]) > 2:
                    sc = plt.tricontourf(point_here[:, 0], point_here[:, 1],
                                         ikle_all[r], inter_vel, cmap=cm,
                                         levels=bounds, extend='both')
                    if r == len(inter_vel_all) - 1:
                        # plt.clim(0, np.nanmax(inter_vel))
                        cbar = plt.colorbar(sc)
                        if project_preferences['language'] == 0:
                            cbar.ax.set_ylabel('Velocity [m/sec]')
                        elif project_preferences['language'] == 1:
                            cbar.ax.set_ylabel('Vitesse [m/sec]')
                        else:
                            cbar.ax.set_ylabel('Velocity [m/sec]')
                else:
                    print('Warning: The river is dry for one time step. The figure created will be empty.\n\n')
            plt.axis('equal')
            plt.xlabel('x coord []')
            plt.ylabel('y coord []')
            if project_preferences['language'] == 0:
                plt.title(name_hdf5[:-3] + " : " + 'Velocity - Time Step: ' + str(time_step))
            elif project_preferences['language'] == 1:
                plt.title(name_hdf5[:-3] + " : " + 'Vitesse - Pas de Temps: ' + str(time_step))
            else:
                plt.title(name_hdf5[:-3] + " : " + 'Velocity - Time Step: ' + str(time_step))

            # save figure
            plt.tight_layout()  # remove margin out of plot
            if merge_case:
                suffix = 'Merge_Velocity_t' + str(time_step) + '_'
            else:
                suffix = 'Velocity_t' + str(time_step) + '_'
            if not erase1:
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            else:
                test = tools_mod.remove_image(suffix, path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            if format1 == 123456:  # "display"
                plt.show()
            else:  # "export"
                plt.cla()
                plt.clf()
                plt.close('all')

    if height:
        print(erase1, format1)
        # plot the interpolated height
        if len(inter_h_all) > 0:  # 0
            # plt.subplot(2, 1, 2) # nb_fig, nb_fig, position
            plt.figure()
            plt.ticklabel_format(useOffset=False)
            # color map (the same for al reach)
            mvc = 0.001
            cm = plt.cm.get_cmap(project_preferences['color_map'])
            for r in range(0, len(inter_h_all)):
                inter_h = inter_h_all[r]
                if len(inter_h) > 0:
                    mv = max(inter_h)
                    # mv = np.mean(inter_h[inter_h >= 0]) * 2
                    if mv > mvc:
                        mvc = mv
            bounds = np.linspace(0, mvc, 15)
            for r in range(0, len(inter_h_all)):
                point_here = np.array(point_all_reach[r])
                inter_h = inter_h_all[r]
                if len(point_here) == len(inter_h) and len(ikle_all[r]) > 2:
                    inter_h[inter_h < 0] = 0
                    sc = plt.tricontourf(point_here[:, 0], point_here[:, 1], ikle_all[r], inter_h, cmap=cm,
                                         vmin=0, vmax=mvc, levels=bounds,
                                         extend='both')  # extent=(min(point_here[:, 0]), max(point_here[:, 0]), min(point_here[:, 1]), max(point_here[:, 1]))
                    if r == len(inter_h_all) - 1:  # end of loop
                        cbar = plt.colorbar(sc)
                        if project_preferences['language'] == 0:
                            cbar.ax.set_ylabel('Water depth [m]')
                        elif project_preferences['language'] == 1:
                            cbar.ax.set_ylabel("Hauteur d'eau [m]")
                        else:
                            cbar.ax.set_ylabel('Water depth [m]')
                else:
                    print('Warning: The river is dry for one time step. The figure created will be empty.\n\n')
            plt.axis('equal')
            plt.xlabel('x coord []')
            plt.ylabel('y coord []')
            if project_preferences['language'] == 0:
                plt.title(name_hdf5[:-3] + " : " + 'Water depth - Time Step: ' + str(time_step))
            elif project_preferences['language'] == 1:
                plt.title(name_hdf5[:-3] + " : " + "Hauteur d'eau - Pas de Temps: " + str(time_step))
            else:
                plt.title(name_hdf5[:-3] + " : " + "Hauteur d'eau - Pas de Temps: " + str(time_step))
            # save figure
            plt.tight_layout()  # remove margin out of plot
            if merge_case:
                suffix = 'Merge_Waterheight_t' + str(time_step) + '_'
            else:
                suffix = 'Water_height_t' + str(time_step) + '_'
            if not erase1:
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            else:
                test = tools_mod.remove_image(suffix, path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name_hdf5[:-3] + "_" + suffix + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            if format1 == 123456:  # "display"
                plt.show()
            else:  # "export"
                plt.cla()
                plt.clf()
                plt.close('all')

    # plot substrate for the whole hydrological grid for each reach
    # Not done anymore as it freezes the GUI for large models.
    # if sub_pg and sub_dom:
    #     for r in range(0, min(len(ikle_all), 2)):
    #         if len(ikle_all)>1:
    #             substrate.fig_substrate(point_all_reach[r], ikle_all[r], sub_pg[r], sub_dom[r], path_im, reach_num=r)
    #         else:
    #             substrate.fig_substrate(point_all_reach[r], ikle_all[r], sub_pg[r], sub_dom[r], path_im)
    #         if r==1:
    #             print('Warning: For the substrate data, only the two first reaches are plotted. \n')


def plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, point_c_all=[], inter_vel_all=[],
              inter_h_all=[], path_im=[]):
    """
    This is a function to plot a grid and the output. It is mosty used to debug the grid creation. Contrarily to the more
    simple function plot_grid_simple, it is posible to plot the position of the holes (which indicates the dry area),
    the limits of the reaches used by triangle, the overlap between two reaches, and so on.

    :param point_all_reach: the grid point by reach
    :param ikle_all: the connectivity table by reach
    :param lim_by_reach: the segment giving the limits of the grid
    :param hole_all: the coordinates of the holes
    :param overlap: the point of each reach which are also on an other reach
    :param point_c_all: the centroid of each element
    :param inter_vel_all: the interpolated velocity for each reach
    :param inter_h_all: the interpolated height
    :param path_im: the path where to save the image
    """

    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['pdf.fonttype'] = 42

    # plot only the grid
    plt.figure()
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    for r in range(0, len(ikle_all)):
        # get data for this reach
        ikle = ikle_all[r]
        coord_p = point_all_reach[r]
        if lim_by_reach:
            seg_reach = lim_by_reach[r]
        h = hole_all

        # prepare the grid
        if ikle is not None:  # case empty grid
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

            # plt.plot(xlist, ylist, '-b', linewidth=0.1)
            if lim_by_reach:
                for hh in range(0, len(h)):
                    plt.plot(h[hh][0], h[hh][1], "g*", markersize=3)
                for i in range(0, len(seg_reach)):
                    seg = seg_reach[i]
                    if i % 3 == 0:
                        m = 'r'
                    elif i % 3 == 1:
                        m = 'g'
                    else:
                        m = 'y'
                    plt.plot([coord_p[seg[0], 0], coord_p[seg[1], 0]], [coord_p[seg[0], 1], coord_p[seg[1], 1]], m,
                             linewidth=1)
                overlap_r = overlap[r]
                # if len(overlap_r) > 0:
                # for i in range(0, len(overlap_r)):
                # plt.plot(coord_p[overlap_r[i], 0],coord_p[overlap_r[i], 1], 'k.')
    # plt.plot(xlist, ylist, 'g.', markersize=1)
    # if coord_pro2:
    #   for p in range(0, len(coord_pro2)):
    #        plt.plot(coord_pro2[p][0], coord_pro2[p][1], 'b.', markersize=2)
    # plt.axis('equal')
    plt.title('Computational Grid')
    plt.savefig(os.path.join(path_im, "Grid_new_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"), transparent=True)
    plt.savefig(os.path.join(path_im, "Grid_new_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"), transparent=True)
    # plt.close()
    plt.show()

    # plot the interpolated velocity
    if len(inter_vel_all) > 0:  # 0
        cm = plt.cm.get_cmap('coolwarm')
        plt.figure()
        for r in range(0, len(inter_vel_all)):
            point_here = np.array(point_all_reach[r])
            inter_vel = inter_vel_all[r]
            if len(point_here[:, 0]) == len(inter_vel):
                sc = plt.tricontourf(point_here[:, 0], point_here[:, 1], ikle_all[r], inter_vel
                                     , min=-1e-5, max=np.nanmax(inter_vel), cmap=cm)
                if r == len(inter_vel_all) - 1:
                    # plt.clim(0, np.nanmax(inter_vel))
                    cbar = plt.colorbar(sc)
                    cbar.ax.set_ylabel('Velocity [m/sec]')
            else:
                print('Warning: One reach could not be drawn. \n')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Interpolated velocity')
        # plt.savefig(os.path.join(path_im, "Vel_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
        # plt.savefig(os.path.join(path_im, "Vel_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
        # plt.close()

    # plot the interpolated height
    if len(inter_h_all) > 0:  # 0
        cm = plt.cm.get_cmap('jet')
        plt.figure()
        for r in range(0, len(inter_h_all)):
            point_here = np.array(point_all_reach[r])
            inter_h = inter_h_all[r]
            if len(point_here) == len(inter_h):
                inter_h[inter_h < 0] = 0
                sc = plt.tricontourf(point_here[:, 0], point_here[:, 1], ikle_all[r],
                                     inter_h, min=0, max=np.nanmax(inter_h), cmap=cm)
                if r == len(inter_h_all) - 1:
                    cbar = plt.colorbar(sc)
                    cbar.ax.set_ylabel('Water height [m]')
            else:
                print('Warning: One reach could not be drawn. \n')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Interpolated water height')
        # plt.savefig(os.path.join(path_im, "Water_height_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
        # plt.savefig(os.path.join(path_im, "Water_height_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
        # plt.close()
        # plt.show()

    # plt.show()


def main():
    """
    Used to test this module
    """

    # #create grid mascaret
    # path = r'D:\Diane_work\output_hydro\mascaret'
    # path = r'D:\Diane_work\output_hydro\mascaret\Bort-les-Orgues'
    # #path = r'D:\Diane_work\output_hydro\mascaret\large_fichier'
    # file_geo = r'mascaret0.geo'
    # file_res = r'mascaret0_ecr.opt'
    # file_gen = 'mascaret0.xcas'
    # [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach] = \
    #                     mascaret.load_mascaret(file_gen, file_geo, file_res, path, path, path)
    # #mascaret.figure_mascaret(coord_pro, coord_r, xhzv_data, on_profile, nb_pro_reach, name_pro, name_reach,'.', [0, 1, 2], [-1], [0])
    # manning_value = 0.025
    # manning = []
    # nb_point = 20
    # for p in range(0, len(coord_pro)):
    #     manning.append([manning_value] * nb_point)
    #
    # vh_pro = dist_vistess2.dist_velocity_hecras(coord_pro, xhzv_data, manning, nb_point, 1.0, on_profile)
    # inter_vel_all = []
    # inter_height_all = []
    # for t in range(0, len(vh_pro)):
    #     [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all]\
    #         = create_grid(coord_pro, 2, [], [], nb_pro_reach, vh_pro[t])
    #     #[ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all]= \
    #     #create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro[t])
    # #plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, [], [], [], path)
    # plot_grid(point_all_reach, ikle_all, [], [], [], point_c_all, inter_vel_all, inter_height_all, path)
    #
    # #create grid RUBAR
    # a = time.time()
    # path = r'D:\Diane_work\output_hydro\RUBAR_MAGE\Gregoire\1D\LE2013\LE2013\LE13'
    # mail = 'mail.LE13'
    # geofile = 'LE13.rbe'
    # data = 'profil.LE13'
    # [xhzv_data_all, coord_pro, lim_riv] = rubar.load_rubar1d(geofile, data, path, path, path, True)
    # coord_sub = [[0.0,0.0], [2.0,2.0],[1.5,1.5]]
    # ikle_sub = [[0, 1, 2]]
    #
    # manning_value_center = 0.025
    # manning_value_border = 0.06
    # manning = []
    # nb_point = len(coord_pro)
    # # write this function better
    # for p in range(0, len(coord_pro)):
    #     x_manning = coord_pro[p][0]
    #     manning_p = [manning_value_border] * nb_point
    #     lim1 = lim_riv[p][0]
    #     lim2 = lim_riv[p][2]
    #     ind = np.where((coord_pro[p][0] < lim2[0]) & (coord_pro[p][1] < lim2[1]) &\
    #               (coord_pro[p][0] > lim1[0]) & (coord_pro[p][1] > lim1[1]))
    #     ind = ind[0]
    #
    #     for i in range(0, len(ind)):
    #         manning_p[ind[i]] = manning_value_center
    #     manning.append(manning_p)
    # manning = []
    # nb_point = 100
    # manning = dist_vistess2.get_manning(manning_value_center, nb_point, len(coord_pro))
    #
    # vh_pro = dist_vistess2.dist_velocity_hecras(coord_pro, xhzv_data_all, manning, nb_point, 1)
    # #dist_vistess2.plot_dist_vit(vh_pro, coord_pro, xhzv_data_all, [0],[0,1])
    # [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] \
    #     = create_grid(coord_pro, 10, [], [], [0, len(coord_pro)], vh_pro[1])
    # #[ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = create_grid_only_1_profile(coord_pro, [0, len(coord_pro)], vh_pro[0])
    # plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, [], [], [], path, coord_pro2)
    # #plot_grid(point_all_reach, ikle_all, [], [], [], [], [], [], path, [])

    # #plt.figure()
    # #for p in range(0, len(coord_pro2)):
    #   #  plt.plot(coord_pro[p][0], coord_pro[p][1], 'r.', markersize=4)
    #   # plt.plot(coord_pro2[p][0], coord_pro2[p][1], 'b.', markersize=4)
    # #plt.show()
    # b = time.time()
    # print(b-a)
    #
    # #test hec-ras
    # CAREFUL SOME DATA CAN BE IN IMPERIAL UNIT (no impact on the code, but result can look unlogical)
    path_test = r'D:\Diane_work\version\file_test\hecrasv4'
    name = 'CHANMOD'  # CRITCREK (22), LOOP (12)
    name_xml = name + '.O02.xml'
    # name_xml = 'BaldEagle.RASexport.sdf'
    name_geo = name + '.g01'
    path_im = r'D:\Diane_work\version\file_test\fig_test'
    # coord_sub = [[0.5, 0.2], [0.6, 0.6], [0.0, 0.6]]
    # ikle_sub = [[0, 1, 2]]
    from src import hec_ras1D_mod

    [coord_pro, vh_pro, nb_pro_reach] = hec_ras1D_mod.open_hecras(name_geo, name_xml, path_test, path_test, path_im, False)
    print(len(vh_pro))

    [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] = create_grid(
        coord_pro, 5, [], [], nb_pro_reach, [])
    # plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, point_c_all, [], [], path_im)
    # plt.show()

    for t in range(0, len(vh_pro)):
        which_pro = vh_pro[t]
        [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] \
            = create_grid(coord_pro, 5, [], [], nb_pro_reach, which_pro)  # [], [] -> coord_sub, ikle_sub,
        # [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
        # create_grid_only_1_profile(coord_pro, nb_pro_reach, [])
        if which_pro:
            [inter_vel_all, inter_h_all] = interpo_linear(point_all_reach, coord_pro2, vh_pro[t])
            plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, point_c_all, inter_vel_all,
                      inter_h_all, path_im)
            # plot_grid(point_all_reach, ikle_all, [], [], [], point_c_all, inter_vel_all, inter_height_all, path_im)
        else:
            pass
            # plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, seg_island)
        plt.show()

    # cut 2D grid
    # namefile = r'mersey.res'
    # pathfile = r'C:\Users\diane.von-gunten\HABBY\test_data'
    # path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    # [v, h, coord_p, ikle, coord_c] = selafin_habby1.load_telemac(namefile, pathfile)
    # h = np.array(h)
    # h[-1][1:50] = -10
    # [ikle, point_all, water_height, velocity] = cut_2d_grid(ikle, coord_p, h[-1], v[-1])
    # print(ikle)
    # plot_grid([point_all], [ikle], [], [], [], [], [],[], path_im)


if __name__ == '__main__':
    main()
