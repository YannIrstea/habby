import numpy as np
from src import mascaret
from src import dist_vistess2
import triangle
import matplotlib.pyplot as plt
import time
from src import rubar
from src import Hec_ras06
import scipy.interpolate
import copy
#np.set_printoptions(threshold=np.inf)
import os
import bisect


def create_grid(coord_pro, extra_pro, coord_sub, ikle_sub, nb_pro_reach=[0, 1e10], vh_pro_t=[], q=[], pnew_add=1):
    """
    It creates a grid from the coord_pro data using the triangle module.
    It creates the grid up to the end of the profile or up to the water limti uif vh_pro_t is present

    The function has the following form:
    if vh_pro_t:
         find cordinate under water -> update coord_pro
         see if there is islands, find the island limits and the holes indicating the inside/outside of the islands
    find the point which give the end/start of the segment defining the grid limit
    find all point which need to be added to the grid and add extra profile if needed
    based on the start/end points and the island limits, create the segments which gives the grid limit
    triangulate and so create the grid
    flag point which are overlapping in two grids
    :param q: used in the secondary process (like in hydro_gui2) when we do not call this function direclty, but we
    call it in a second process so that the GUI do not crash if something go wrong
    :param coord_pro: the profile coordinates (x,y, h, dist along) the profile
    :param extra_pro: the number of "extra" profiles to be added between profile to simplify the grid
    :param coord_sub: (not used anymore)
      the coordainte of the point forming the substrate layer (often created with substrate.load_sub)
    :param ikle_sub: (not used anymore)
      the connectivity table of the substrate grid (often created with substrate.load_sub)
    :param nb_pro_reach: the number of reach by profile starting with 0
    :param vh_pro_t: the velocity and height of the water (used to cut the limit of the river).
    :param pnew_add: (not used anymore)
     a parameter to cut the substrate side in smaller part (improve grid quality)
    in the form dist along profile, h , v for the analyzed time step
    If not given, gird is contructed on the whole profile.
    :return: connectivity table and grid point
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
        coord_pro_p0 = coord_pro[p - 1]
        coord_pro_p1 = coord_pro[p]
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
        #point_all2 = list(point_all)  # because you shall not use np.concatenate
        if np.all(p != np.array(nb_pro_reach)):
            if len(coord_pro_p1[0]) > 1 and len(coord_pro_p0[0]) > 1:
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
                        li = np.int(np.floor(l0 + i * (l1-l0) / len(new_p_a)))
                        if li < 2:
                            li = 2
                        point_all_i = newp(new_p_a[i], new_p_b[i], li)
                        point_all = np.concatenate((point_all, point_all_i), axis=0)
                        #point_all.extend(point_all_i)
                        ind_p.extend([len(point_all)])
                else:
                    [point_mid_x, point_mid_y] = find_profile_between(coord_pro_p0, coord_pro_p1, extra_pro)
                    for pr in range(0, extra_pro):
                        point_all_i = np.array([point_mid_x[pr], point_mid_y[pr]]).T
                        point_all = np.concatenate((point_all, point_all_i), axis=0)
                        ind_p.extend([len(point_all)])

        #point_all = np.array(point_all2)
        # add the last profile
        if p == len(coord_pro)-1:
            pro_orr = np.array([coord_pro_p1[0], coord_pro_p1[1]]).transpose()
            ind_s.extend([len(point_all)])  # start
            point_all = np.concatenate((point_all, pro_orr), axis=0)
            ind_e.extend([len(point_all) - 1])  # end
            ind_p.extend([len(point_all)])

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

        for p in range(0, len(coord_pro)-1):
            if np.all(p != np.array(nb_pro_reach)):
                # find on which extra profile to "finish" and "start" the island
                if np.any(p-1 == np.array(nb_pro_reach)):
                    if extra_pro2 % 2 == 0:
                        af = int(extra_pro2 / 2)
                        bef = -af-1
                    else:
                        af = int(np.floor(extra_pro2 / 2)+1)
                        bef = -af
                else:
                    if extra_pro2 % 2 == 0:
                        af = int(extra_pro2/2)
                        bef = -af - 1
                    else:
                        af = int(np.floor(extra_pro2 / 2)+1)
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
                    # ind_lim = np.delete(ind_lim, isl_del)
                    x = coord_pro[p][0]
                    y = coord_pro[p][1]
                    # find the end and start indices of the extra-profile before and after
                    p_here = p + p*extra_pro2 - r * extra_pro2 - 1
                    ind_bef_s = ind_p[p_here + bef]
                    ind_bef_e = ind_p[p_here + bef+1]
                    ind_af_s = ind_p[p_here + af]
                    ind_af_e = ind_p[p_here + af+1]

                    # calculate minimum distance for all island to get the six vertex
                    len_here = len(ind_lim)
                    for i in range(1, len_here - 1, 2):
                        point_bef = np.array(point_all[ind_bef_s:ind_bef_e])
                        dist_xy = np.sqrt((point_bef[:, 0] - x[ind_lim[i]]) ** 2 +
                                          (point_bef[:, 1] - y[ind_lim[i]]) ** 2)
                        ind1 = ind_bef_s + np.argmin(dist_xy)

                        dist_xy = np.sqrt((point_bef[:, 0] - x[ind_lim[i+1]]) ** 2 +
                                          (point_bef[:, 1] - y[ind_lim[i+1]]) ** 2)
                        ind2 = ind_bef_s + np.argmin(dist_xy)
                        point_af = np.array(point_all[ind_af_s:ind_af_e])
                        dist_xy = np.sqrt((point_af[:, 0] - x[ind_lim[i]]) ** 2 +
                                          (point_af[:, 1] - y[ind_lim[i]]) ** 2)
                        ind3 = ind_af_s + np.argmin(dist_xy)
                        dist_xy = np.sqrt((point_af[:, 0] - x[ind_lim[i+1]]) ** 2 +
                                          (point_af[:, 1] - y[ind_lim[i+1]]) ** 2)
                        ind4 = ind_af_s + np.argmin(dist_xy)
                        # add the six segments (start and end of each segment), so 12 points
                        beg_len = len(seg_island)
                        if ind2 != ind1:
                            seg_island.append([ind1, r, p_here+bef, isl2])
                            seg_island.append([ind2, r,p_here+bef, isl2])
                            seg_island.append([ind2, r, -99, isl2])
                            seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                        else:
                            #if ind1 < len(point_bef)-1+ind_bef_s:
                             #  seg_island.append([ind1, r, p_here+bef, isl2])
                              # seg_island.append([ind2+1, r, p_here+bef, isl2])
                              # seg_island.append([ind2+1, r, -99, isl2])
                              # seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                            #else:
                               seg_island.append([ind2, r, -99, isl2])
                               seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                        seg_island.append([ind1, r, -99, isl2])
                        seg_island.append([ind_p[p_here] + ind_lim[i], r, -99, isl2])

                        seg_island.append([ind_p[p_here] + ind_lim[i], r, -99, isl2])
                        seg_island.append([ind3, r, -99, isl2])
                        if ind3 != ind4:
                            seg_island.append([ind3, r, p_here+af, isl2])
                            seg_island.append([ind4, r, p_here+af, isl2])
                            seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                            seg_island.append([ind4, r, -99, isl2])
                        else:
                           # if ind3 < len(point_af) - 1 + ind_af_s:
                           #    seg_island.append([ind3, r, p_here + af, isl2])
                           #   seg_island.append([ind4+1, r, p_here + af, isl2])
                            #    seg_island.append([ind_p[p_here] + ind_lim[i + 1], r, -99, isl2])
                            #    seg_island.append([ind4+1, r, -99, isl2])
                            #else:
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
                            p2 = point_all[seg_island[polygon_ind[j+1]][0]]
                            seg_poly.append([p1, p2])
                        inside = inside_polygon(seg_poly, hole_here)
                        if inside:
                            hole_all_i.append(hole_here)
                            hole_isl.extend([isl2-1])
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

        # correct for colinear segments as triangle has difficulties with them
        colinear = True
        if len(seg_island) > 1 and colinear:
            for p in range(0, len(coord_pro)+len(coord_pro)*extra_pro):
                ind = np.where(seg_island[:, 2] == p)[0]  # not always 6 segments
                seg_island_pro = seg_island[ind, 0]
                seg_island_pro = np.sort(seg_island_pro)
                seg_island[ind, 0] = seg_island_pro

        # correct for point at the middle of one segment as triangle has difficulties with them (not used)
        test_middle = False
        if len(seg_island) > 1 and test_middle:
            for s in range(0, len(seg_island), 2):
                mpoint = 0.5 * point_all[seg_island[s, 0]] + 0.5 * point_all[seg_island[s+1, 0]]
                ind = np.where(abs(mpoint[0] - point_all[:, 0]) + abs(mpoint[1] -
                                                                      point_all[:, 1]) < point_all[0, 0] * 1e-7)[0]
                point_all[ind, :] = point_all[ind, :] * 0.99

        # correct for crossing segment (not used in all, just if check needed)
        check_cross = False
        hole_isl = np.array(hole_isl)
        if check_cross:
            new_seg_island = []
            if len(seg_island) > 1:
                for i in range(0, isl2):
                    inter = False
                    count = 0
                    ind_all = np.where(seg_island[:, 3] == i)[0]
                    for ind in ind_all[::2]:
                        for s2 in range(0, len(seg_island[:,0]), 2):
                            if np.all(s2 != ind_all) and np.all(s2+1 != ind_all) and np.all(s2 != ind_all + 1)  and np.all(s2+1 != ind_all + 1):
                                seg11 = point_all[seg_island[ind, 0]]
                                seg12 = point_all[seg_island[ind+1, 0]]
                                seg21 = point_all[seg_island[s2, 0]]
                                seg22 = point_all[seg_island[s2+1, 0]]
                                [inter_here, pc] = intersection_seg(seg11, seg12, seg21, seg22, False)
                                if inter_here:
                                    inter = True
                            if inter:
                                break
                    if not inter:
                        print(ind_all)
                        for indhere in ind_all:
                            new_seg_island.append(seg_island[indhere, :])
                    if inter:
                        print('Warning: An island was erased because it crossed with another island')
                        #ind2 = np.where(hole_isl == i)[0]
                        #if ind2:
                            #del hole_all_i[ind2]
                seg_island = np.array(new_seg_island)

    # check if they here identical points and send a warning if yes
    # using an idea from http://stackoverflow.com/questions/31097247/remove-duplicate-rows-of-a-numpy-array
    # should be reasonlaby quick
    # test: point_all2 = np.array([[1,1], [2,3], [1,2], [3,4], [1,2]])
    sorted_data = point_all[np.lexsort(point_all.T), :]
    row_mask = np.append([True], np.any(np.diff(sorted_data, axis=0), 1))
    test_unique = sorted_data[row_mask]
    if len(test_unique) != len(point_all):
        print('Warning: There is duplicate points. The triangulation might fail. \n')
        # this is very very slow, but it might solve problems
        # for p in range(0, len(point_all)):
        #    for p2 in range(0, len(point_all)):
        #      if p !=p2:
        #          if point_all[p,0] == point_all[p2,0] and point_all[p,1] == point_all[p2,1]:
        #             point_all[p] = point_all[p] * 0.99

    # put data in order and find the limits
    seg_to_be_added2 = []
    lim_by_reach_for_sub = []
    lim_isl_for_sub = []
    for r in range(0, len(nb_pro_reach)-1):
        lim_by_reach_r = []
        lim_isl_for_subr = []
        ind_r = nb_pro_reach[r]
        ind_r2 = nb_pro_reach[r+1]
        # side (for both list)
        for i in range(ind_r, nb_pro_reach[r+1]-1):
            lim_by_reach_r.append([ind_s[i], ind_s[i+1]])
            lim_by_reach_r.append([ind_e[i], ind_e[i+1]])
        # start and end of each reach
        lim_by_reach_r.append([ind_s[ind_r], ind_e[ind_r]])
        lim_by_reach_r.append([ind_s[ind_r2-1], ind_e[ind_r2-1]])
        blob = copy.deepcopy(lim_by_reach_r)  # classic, classic, but still annoying
        lim_by_reach_for_sub.append(blob)
        # add the segments realted to the island
        if vh_pro_t:
            if len(seg_island) > 1:
                ind_isl_re = np.where(seg_island[:, 1] == r)[0]
                for w in range(0, int(len(ind_isl_re)/2)):
                    seg_to_be_added = np.array([int(seg_island[ind_isl_re[2*w], 0]),
                                                int(seg_island[ind_isl_re[2*w+1], 0])])
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

    # add the segments and points related to the substrate (not used)
    add_sub = False
    if add_sub:
        lim_here_all = []
        lim_herei_all = []
        si = 0
        sub_analyzed = np.zeros((len(ikle_sub)*4, 4))
        for i in range(0, len(ikle_sub)):
            # it is probably a triangular grid but it might not be always true
            for j in range(0, len(ikle_sub[i])):
                # get the substrate segment
                if j < len(ikle_sub[i])-1:
                    p1sub = np.array(coord_sub[int(ikle_sub[i][j])])
                    p2sub = np.array(coord_sub[int(ikle_sub[i][j+1])])
                else:
                    p1sub = np.array(coord_sub[int(ikle_sub[i][j])])
                    p2sub = np.array(coord_sub[int(ikle_sub[i][0])])
                # there is segment more than one time in ikle, we do not want to do it more than once
                p12sub = np.array([p1sub[0], p1sub[1], p2sub[0], p2sub[1]])
                p21sub = np.array([p2sub[0], p2sub[1], p1sub[0], p1sub[1]])
                if np.any(np.sum(sub_analyzed - p12sub, axis=1) == 0) or np.any(np.sum(sub_analyzed - p21sub,axis=1) == 0):
                    break
                else:
                    sub_analyzed[si, :] = p12sub
                    si +=1

                # to get a better quality mesh it is often useful to use smaller segments
                # hence we cut the substrate segment in smaller entities
                p1sub0 = copy.deepcopy(p1sub)
                p2sub0 = copy.deepcopy(p2sub)
                for pnew in range(0, pnew_add):
                    # we redfine p1sub and p2sub here
                    if pnew > 0:
                        p1sub = copy.deepcopy(p2sub)
                    p2sub[0] = p1sub0[0] + (pnew+1) / pnew_add * (p2sub0[0] - p1sub0[0])
                    p2sub[1] = p1sub0[1] + (pnew+1) / pnew_add * (p2sub0[1] - p1sub0[1])
                    # find the new segments
                    for r in range(0, len(nb_pro_reach)-1):
                        sp1 = []
                        sp2 = []
                        sp3 = []
                        sp4 = []
                        if i == 0 and j == 0 and pnew == 0:
                            # create the limits of the reach with coordinates and not indices
                            lim_here = []
                            for w0 in range(0, len(lim_by_reach_for_sub[r])):
                                p1here = point_all[lim_by_reach_for_sub[r][w0][0]]
                                p2here = point_all[lim_by_reach_for_sub[r][w0][1]]
                                lim_here.append([p1here, p2here])
                            lim_here_all.append(lim_here)
                        else:
                            lim_here = lim_here_all[r]
                        # check if crossing with a segment of the reach
                        # add the substrate segment to lim_by_reach and point_all
                        ind_seg_sub_ini0 = len(lim_by_reach[r])
                        [point_all, lim_by_reach[r]] = \
                            get_crossing_segment_sub(p1sub, p2sub, lim_here, lim_by_reach[r], point_all, False)
                        ind_seg_sub_ini1 = len(lim_by_reach[r])
                        # create the limits of the island with coordinates and not indices
                        if i == 0 and j == 0 and pnew ==0 :
                            lim_here = []
                            for w0 in range(0, len(lim_isl_for_sub[r])):
                                p1here = point_all[lim_isl_for_sub[r][w0][0]]
                                p2here = point_all[lim_isl_for_sub[r][w0][1]]
                                lim_here.append([p1here, p2here])
                            lim_herei_all.append(lim_here)
                        else:
                            lim_here = lim_herei_all[r]
                        # check if crossing with a segment of the island
                        # add the substrate segment to lim_by_reach and point_all (if not already in)
                        # we need to correct
                        ind_seg_sub_ini = np.arange(ind_seg_sub_ini0, ind_seg_sub_ini1)
                        [point_all, lim_by_reach[r]] = get_crossing_segment_sub(p1sub, p2sub, lim_here, lim_by_reach[r],
                                                                                point_all, True, ind_seg_sub_ini)

    # triangulate. Overlaping elements are just flagged in the variable overlap
    ikle_all = []
    point_all_reach = []
    point_c_all = []
    overlap = []
    print('triangulation')
    for r in range(0, len(nb_pro_reach)-1):
        # do the triangulation
        # perfomance note: Obviously sending only the point_all from this reach would save time
        # however at the junction between the reach we would have different point on which the grid is constructed
        # which means that a "point in polygon" test would be needed to find the overlapping regions
        # if all point are tested, this is obviouly slower than the current version.
        # But overlapping points are often at the end/start of the reach.
        # Performance might depend on the criteria chosen to test the points.
        # the current version is actually the quickest one which I know. Might not be the quickest.

        if hole_all_i:
            dict_point = dict(vertices=point_all, segments=lim_by_reach[r], holes=hole_all_i)  #
        else:
            dict_point = dict(vertices=point_all, segments=lim_by_reach[r])
        grid_dict = triangle.triangulate(dict_point, 'p')  # 'p' allows for constraint V for verbose

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
        ikle_here = np.reshape(ikle_all[r], (len(ikle_all[r])*3, 1))
        p1s = point_here[ikle_here[::3]]
        p2s = point_here[ikle_here[1::3]]
        p3s = point_here[ikle_here[2::3]]
        point_c = (p1s + p2s + p3s) / 3
        point_c = np.squeeze(np.array(point_c))  # why squeeze?
        point_c_all.append(point_c)

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


def create_grid_only_1_profile(coord_pro, nb_pro_reach=[0, 1e10], vh_pro_t =[]):
    """
    It creates the grid from the coord_pro data using one additional profil in the middle. No triangulation.
    The data interpolation is done in this function also.
    :param coord_pro: the profile coordinates (x,y, h, dist along) the profile
    :param nb_pro_reach: the number of profile by reach
    :param vh_pro_t: the data with heigh and velocity, giving the river limits
    :return:
    """
    point_all_reach = []
    ikle_all = []
    point_c_all = []
    p_not_found_all = []
    warn_pro_short = True
    warn_pro_short2 = True

    # update coord_pro if we have data. Indeed, if velocity and water height is given, we only want wetted
    # perimeter and points where the velocity is given (might not be all profil points).
    inter_vel_all = []
    inter_height_all = []
    all_point_midx = []
    all_point_midy = []
    if vh_pro_t:
        coord_pro = update_coord_pro_with_vh_pro(coord_pro, vh_pro_t)

    a = 0
    # for each reach
    for r in range(0, len(nb_pro_reach) - 1):
        point_all = []
        ikle = []
        point_c = []
        inter_vel = []
        inter_height = []
        # get rid of island for the data
        if vh_pro_t:
            data_height_old = [val for val in vh_pro_t[nb_pro_reach[r]][1] for blob in (0, 1)]
            # was used for created the island, not needed
            # because the island information is contained in ikle
            # be caseful in case where it do not work
            # data_height_old = [val for val in data_height0 if val > 0]  # island
            data_vel_old = [val for val in vh_pro_t[nb_pro_reach[r]][2] for blob in (0, 1)]
            # data_vel_old = [j for (i, j) in zip(data_height0, data_vel) if i > 0]

        for p in range(nb_pro_reach[r]+1, nb_pro_reach[r+1]):
            coord_pro_p0 = coord_pro[p-1]
            coord_pro_p1 = coord_pro[p]

            # find the middle profile
            if len(coord_pro_p0[0]) > 0 and len(coord_pro_p1[0]) > 0:
                [point_mid_x, point_mid_y] = find_profile_between(coord_pro_p0, coord_pro_p1, 1, False)
                all_point_midx.extend([point_mid_x[0]])
                all_point_midy.extend([point_mid_y[0]])

            # create cells for the profile before the middle profile
            if len(coord_pro_p0[0]) > 0:
                # wet profile
                if vh_pro_t:
                    [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p0, vh_pro_t[p - 1], point_mid_x, point_mid_y, point_all, ikle, point_c, 1)
                # whole profile
                else:
                    [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p0, vh_pro_t, point_mid_x, point_mid_y,point_all, ikle, point_c, 1)
            if vh_pro_t:
                inter_vel += data_vel_old
                inter_height += data_height_old
            #  create cells for the profile after the middle profile
            if len(coord_pro_p1[0]) > 0:
                if vh_pro_t:
                    [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p1, vh_pro_t[p], point_mid_x,
                                                                                 point_mid_y, point_all, ikle, point_c, -1)
                else:
                    [point_all, ikle, point_c, p_not_found] = get_new_point_and_cell_1_profil(coord_pro_p1, vh_pro_t, point_mid_x,
                                                                                 point_mid_y, point_all, ikle, point_c, -1)
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
        point_all_reach.append(np.array(point_all))
        point_c_all.append(np.array(point_c))
        ikle_all.append(np.array(ikle))
        if vh_pro_t:
            inter_vel_all.append(np.array(inter_vel))
            inter_height_all.append(np.array(inter_height))

        # useful to control the middle profile 9added between two profiles)
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
        # #for p in range(0, len(p_not_found)):
        #    # plt.plot(p_not_found[p][0], p_not_found[p][1], '.r')
        # plt.show()


    return ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all


def get_new_point_and_cell_1_profil(coord_pro_p, vh_pro_t_p, point_mid_x, point_mid_y, point_all, ikle, point_c, dir):
    """
     create the grid for one profile (one "line")
    :param coord_pro_p: the coordinated of the profile
    :param vh_pro_t_p the height and velocity data of the profile analysed
    :param point_mid_x the x coodinate of the points forming the middle profile
    :param point_mid_y the y coordinate of the points forming the middle profile
    :param point_all the point of the grid
    :param ikle the connectivity table of the grif
    :param point_c the central point of each cell
    :param dir: in which direction are we going arounf the profile (upstream/downstram)
    :return: point_all, ikle. point_c
    """
    p_not_found = []
    inter = False
    point_mid_x = point_mid_x[0]
    point_mid_y = point_mid_y[0]
    far = 1e5

    # get a vector perpendicular to the profile
    diffx = coord_pro_p[0][0] - coord_pro_p[0][1]
    diffy = coord_pro_p[1][0] - coord_pro_p[1][1]
    norm = np.sqrt(diffx ** 2 + diffy ** 2)
    nx = diffy / norm
    ny = - diffx / norm
    if nx == 0:
        print('Warning: Found division by zero. \n')
        nx = ny = 1

    # add the cells and points to point_all and ikle
    for s0 in range(1, len(coord_pro_p[0])):

        # find which part of the middle profile to use
        xafter = coord_pro_p[0][s0] - far * nx * dir
        yafter = coord_pro_p[1][s0] - far * ny * dir
        xbefore = coord_pro_p[0][s0] + nx * dir
        ybefore = coord_pro_p[1][s0] + ny *dir
        p1hyd = [xbefore, ybefore]
        p2hyd = [xafter, yafter]
        for m in range(0, len(point_mid_x)-1):
            if max(point_mid_x[m], point_mid_x[m+1]) > min(p1hyd[0], p2hyd[0]) \
                    and max(point_mid_y[m], point_mid_y[m+1]) > min(p1hyd[1], p2hyd[1]):
                p1 = [point_mid_x[m], point_mid_y[m]]
                p2 = [point_mid_x[m+1], point_mid_y[m+1]]
                [inter, pc] = intersection_seg(p1hyd, p2hyd, p1, p2, False)
                if inter:
                    break
        # start/end of the line
        if not inter:
            if len(point_mid_x) > 4:
                p1 = [point_mid_x[-4], point_mid_y[-4]]
                p2 = [point_mid_x[-1], point_mid_y[-1]]
            else:
                p1 = [point_mid_x[-2], point_mid_y[-2]]
                p2 = [point_mid_x[-1], point_mid_y[-1]]
            norm = np.sqrt( (p2[0] - p1[0])**2 + (p2[1] - p1[0]) **2)
            p3x = p2[0] + far * (p2[0]-p1[0]) /norm
            p3y = p2[1] + far * (p2[1]-p1[1]) /norm
            p3 = [p3x, p3y]
            [inter, pc] = intersection_seg(p1hyd, p2hyd, p2, p3, False)
        if not inter:
            if len(point_mid_x) > 4:
                p1 = [point_mid_x[0], point_mid_y[0]]
                p2 = [point_mid_x[4], point_mid_y[4]]
            else:
                p1 = [point_mid_x[0], point_mid_y[0]]
                p2 = [point_mid_x[1], point_mid_y[1]]
            norm = np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[0]) ** 2)
            p3x = p1[0] + far * (p1[0] - p2[0]) / norm
            p3y = p1[1] + far * (p1[1] - p2[1]) / norm
            p3 = [p3x, p3y]
            [inter, pc] = intersection_seg(p1hyd, p2hyd, p1, p3, False)
        if not inter:
            print('Warning: no intersection found for a point. \n')
            # plt.figure()
            # plt.plot()
            # plt.plot(p1hyd[0], p1hyd[1], '.b')
            # plt.plot(p2hyd[0], p2hyd[1], '.b')
            # plt.plot(p2[0], p2[1], '.g')
            # plt.plot(p3[0], p3[1], '.g')
            # plt.plot(coord_pro_p[0], coord_pro_p[1], '-k')
            # plt.show()
            #pc = pc
            if not pc:
                pc = [[point_mid_x[0], point_mid_y[0]]]
            else:
                pc[0][0] = pc[0][0] + 0.0001
                pc[0][1] = pc[0][1] + 0.0001
            #p_not_found.append(pc)

        if s0 == 1:
            point_all.append([coord_pro_p[0][0], coord_pro_p[1][0]])
            point_all.append([coord_pro_p[0][0], coord_pro_p[1][0]])
        point_all.append([coord_pro_p[0][s0], coord_pro_p[1][s0]])
        point_all.append([pc[0][0], pc[0][1]])
        # add the two new cells to ikle and point_c
        if vh_pro_t_p:

            if vh_pro_t_p[1][s0] > 0:
                l = len(point_all) - 1
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
            ikle.append([l - 1, l - 3, l - 2])
            cx = (point_all[l - 1][0] + point_all[l - 3][0] + point_all[l - 2][0]) / 3
            cy = (point_all[l - 1][1] + point_all[l - 3][1] + point_all[l - 2][1]) / 3
            point_c.append([cx, cy])
            ikle.append([l - 1, l - 2, l])
            cx = (point_all[l - 1][0] + point_all[l - 2][0] + point_all[l][0]) / 3
            cy = (point_all[l - 1][1] + point_all[l - 2][1] + point_all[l][1]) / 3
            point_c.append([cx, cy])

    return point_all, ikle,  point_c, p_not_found


def update_coord_pro_with_vh_pro(coord_pro, vh_pro_t):
    """
    The points decribing the profile and the points where velocity is measured might not be the same. Additional,
    part of the profile might be dry and we have adde point giving the river limits which are not in the original
    profil. In this function coord_pro is recalculated to account for these modicfications. Only used if vh_pro_t exists.
    :param coord_pro: the original coord_pro
    :param vh_pro_t: the value and position of h and velcoity measurement with the river limits
    :return: updated coord_pro
    """
    coord_pro_new = []
    coord_change = []
    for p in range(0, len(coord_pro)):
        # prep
        coord_pro_p1 = coord_pro[p]
        dist_all = np.array(vh_pro_t[p][0] - coord_pro_p1[3][0])
        dist_coordorr = np.array(coord_pro_p1[3] - coord_pro_p1[3][0])
        h_all = np.array(vh_pro_t[p][1])
        x = np.zeros((len(dist_all),))
        y = np.zeros((len(dist_all),))
        # get coodinate change between meter and (x,y) coordinates
        norm2 = np.sqrt((coord_pro_p1[0][-1] - coord_pro_p1[0][0]) ** 2 +
                        (coord_pro_p1[1][-1] - coord_pro_p1[1][0]) ** 2)
        dist_in_m = coord_pro_p1[3][-1] - coord_pro_p1[3][0]
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
            if wold != w and w+1 < len(coord_pro_p1[0]):
                # find the direction between the two point of the original profile
                norm = np.sqrt((coord_pro_p1[0][w + 1] - coord_pro_p1[0][w]) ** 2 +
                               (coord_pro_p1[1][w + 1] - coord_pro_p1[1][w]) ** 2)
                if norm == 0:
                    print('Warning: Two identical point in profile. Profile will be modified.\n')
                    coord_pro_p1[0][w] += 0.0001  # add absolute value because Yann
                    coord_pro_p1[1][w] += 0.0001
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
    a small utility function to find start/end of extra profil.
    :param p0: the point at the profile p
    :param p1: the point at the profile p-1
    :param extra_pro the number of extra profile needed
    :return:
    """
    new_p = np.zeros((extra_pro+1, 2))  # why +1?????

    if p1[0] != p0[0]:
        a = (p1[1] - p0[1]) / (p1[0] - p0[0])
        b = p1[1] - a * p1[0]
        new_p[:, 0] = np.linspace(p0[0], p1[0],  num=extra_pro+1, endpoint=False)
        new_p[:, 1] = a * new_p[:, 0] + b
    else:
        new_p[:, 0] = p1[0]
        new_p[:, 1] = np.linspace(p0[1], p1[1], num=extra_pro+1, endpoint=False)

    # extract the first point (p0)
    new_p = new_p[1:, :]
    return new_p


def inside_polygon(seg_poly, point):
    """
    a function to find if a piont is inside a polygon, using ray casting
    :param seg_poly: the segment forming the polygon
    :param point: the point which is indide or outside the polygon
    :return: True is the point is inside the polygon, false otherwise
    """

    # the direction of the ray does not matter
    ray = [point, [point[0], 1e5]]
    inter_count = 0
    for s in range(0, len(seg_poly)):
        [inter, blob] = intersection_seg(seg_poly[s][0], seg_poly[s][1], ray[0], ray[1])
        if inter:
            inter_count +=1
    if inter_count%2 ==0:
        return False
    else:
        return True


def intersection_seg(p1hyd, p2hyd, p1sub, p2sub, col=True):
    """
    find if there is an intersection between two segment (AB and CD). Idea from :
    http://stackoverflow.com/questions/563198/how-do-you-detect-where-two-line-segments-intersect
    based on the caluclaion of the cross-product z= 0 for 2D
    return the crossing point if true
    :param p1hyd: point A
    :param p2hyd: point B
    :param p1sub: point C
    :param p2sub: point D
    :param col: if True, colinear segment crossed. If false they do not
    :return: intersect and the crossing point
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
    if np.all(p1hyd == p1sub) or np.all(p2hyd == p1sub):
        if col:
            inter = True
            pc.append([x1sub, y1sub])
        else:
            inter = False
        return inter, pc
    if np.all(p1hyd == p2sub) or np.all(p2hyd == p2sub):
        if col:
            inter = True
            pc.append([x2sub, y2sub])
        else:
            inter = False
        return inter, pc
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
        t = u = 10**10
    # in this case, crossing
    if col:
        if rxs != 0 and 0 <= t <= 1 and 0 <= u <= 1:
            inter = True
            xcross = x1hyd + u * sx
            ycross = y1hyd + u * sy
            pc.append([xcross, ycross])
    else:
        if rxs != 0 and 0 < t < 1 and 0 < u < 1:
            inter = True
            xcross = x1hyd + u * sx
            ycross = y1hyd + u * sy
            pc.append([xcross, ycross])

    return inter, pc


def add_point(point_all, point):
    """
    add one point to point all in the part concerned with the substrate
    :param point_all: all the point
    :param point:
    :return: point_all, position of the new point
    """

    sum_sub = np.sum(abs(point_all - point), axis=1)
    if (sum_sub != 0).all():
        point_all = np.vstack((point_all, point))
        return point_all, len(point_all)-1
    else:
        ind = np.where(sum_sub == 0)[0]
        return point_all, ind[0]


def get_crossing_segment_sub(p1sub, p2sub, lim_here, lim_by_reachr, point_all, island, ind_seg_sub_ini=[0]):
    """
    This function looks at one substrate segment and find the crossing points of this semgnet with the different
     river segment. If island switch is True, lim_here is the limit of the island, so inside the polygon is outside the river
     If island is false, lim_here is the limiy of the reach under investigation
    :param p1sub: the start point of the substrate semgent
    :param p2sub: the end point of the substrate segment
    :param lim_here: the reach?island limit given in the coordinate system
    :param lim_by_reachr: the limits for reach r which will be given to triangle given by point_all indices.
    :param point_all: all the point (ccordinates) which will be given to triangle
    :param island a boolena indicating if we are on an island or not
    :param ind_seg_sub_ini: the indices of the first segment add by p1sub et p2sub by the reach. Only used island = true
    :return: the update point_all and lim_by_reach
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
                #lim_by_reachr.remove([p1sub, p2sub])

        # if crossing, add to lim_by_reach, case by case
        # we could have more than crossing by substrate segment
        if len(sp1) > 0:  # both p1sub and p2sub inside
            # in this case we need to order the points
            dist_to_sort = []
            for wp in range(0, len(sp1)):
                dist = np.sqrt((p1sub[0]-sp1[wp][0][0])**2 + (p1sub[1]-sp1[wp][0][1])**2)
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
                for w2 in range(0, len(sp1)-1, 2):
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
                for w2 in range(0, len(sp4)-1, 2):
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
    can be used for only one time step - linear
    :param point_all: the coordinate of the grid point
    :param coord_pro: the coordinate of the profile (should be coherent with the coordinate from vh_pro).
    To insure this pass coord_pro through the function "create_grid" with the same vh_pro as input
    :param vh_pro_t: for each profile, dist along the profile, water height and velocity at a particular time step
    :return: the new interpolated data for velocity and water height
    """

    inter_vel_all = []
    inter_height_all = []
    for r in range(0, len(point_all)):  # reaches
        point_p = point_all[r]
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
        # sometime value like -1e17 is added because of the maching precision, we do no want this
        inter_vel[inter_vel < 0] = 0
        inter_vel_all.append(inter_vel)

        # height
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
        # sometime value like -1e17 is added because of the maching precision, we do no want this
        inter_height[inter_height < 0] = 0
        inter_height_all.append(inter_height)

    return inter_vel_all, inter_height_all


def interpo_nearest(point_all, coord_pro, vh_pro_t):
    """
    Using scipy.gridata, this function interpolates the 1.5 D velocity and height to the new grid
    can be used for only one time step - nearest neighbors
    :param point_all: the coordinate of the grid point
    :param coord_pro: the coordinate of the profile (should be coherent with the coordinate from vh_pro).
    To insure this pass coord_pro through the function "create_grid" with the same vh_pro as input
    :param vh_pro_t: for each profile, dist along the profile, water height and velocity at a particular time step
    :return: the new interpolated data for velocity and water height
    """

    inter_vel_all = []
    inter_height_all = []
    for r in range(0, len(point_all)):  # reaches
        point_p = point_all[r]
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
        inter_vel[inter_vel < 0] = 0
        inter_vel_all.append(inter_vel)

        # height
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
        inter_height[inter_height < 0] = 0
        inter_height_all.append(inter_height)

    return inter_vel_all, inter_height_all


def find_profile_between(coord_pro_p0, coord_pro_p1, nb_pro, trim= True):
    """
    Find n profile between two profiles which are not straight
    :param coord_pro_p0: the coord_pro (x,y,h, z) of the first profile
    :param coord_pro_p1: the coord_pro (x,y,h, z) of the second profile
    :param nb_pro the number of profile to add
    :param Trim cut the end and start of profile to avoid to have part of the grid outside of limit
    :return: a list with the updated profile
    """

    mid_point_x = []
    mid_point_y = []
    far = 1e5

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
    a = (y1 - y2)/(x1-x2)
    b = -1
    c = y1 - a * x1
    norm = np.sqrt((x2-x1)**2+(y2-y1)**2)
    nx = (y2-y1) / norm
    ny = -(x2-x1) / norm

    # project points from both profil perpendiculary on the line
    # from https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
    xpro0 = (b * (b * x0all - a * y0all) - a*c) / (a**2 + b**2)
    # ypro0 = (a * (-1*b* x0all + a * y0all) - b*c) / (a**2 + b**2)
    xpro1 = (b * (b * x1all - a * y1all) - a*c) / (a**2 + b**2)
    # ypro1 = (a * (-1*b * x1all + a * y1all) - b*c) / (a**2 + b**2)

    # get a longer line (to have intersection in all cases)
    # to avoid case whew the vector nearly touch each other
    xstart0 = x0all + far * nx
    xend0 = x0all - far * nx
    xstart1 = x1all + far*nx
    xend1 = x1all - far*nx
    ystart0 = y0all + far * ny
    yend0 = y0all - far * ny
    ystart1 = y1all + far * ny
    yend1 = y1all - far * ny

    # find intersection with the other profile
    point_inter0 = np.zeros((len(x0all), 2))
    point_inter1 = np.zeros((len(x1all), 2))
    no_inter0 = np.zeros((len(x0all), ))
    no_inter1 = np.zeros((len(x1all), ))
    # first profile
    s = 0
    for i in range(0, len(x0all)):
        if len(x1all) > 0 and len(x0all) > 0:
            inter = False
            #p1 = [x0all[i], y0all[i]]
            #p2 = [xpro0[i], ypro0[i]]
            p1 = [xstart0[i], ystart0[i]]
            p2 = [xend0[i], yend0[i]]
            for i2 in range(0, len(x1all)-1):
                if max(x1all[i2], x1all[i2+1]) > min(p1[0], p2[0]) and max(y1all[i2], y1all[i2+1]) > min(p1[1], p2[1]):
                    p3 = [x1all[i2], y1all[i2]]
                    p4 = [x1all[i2+1], y1all[i2+1]]
                    [inter, pc] = intersection_seg(p1, p2, p3, p4, False)
                if inter:
                    point_inter0[i] = pc[0]
                    break
            #start/end of line
            if not inter:
                if len(x1all) > 4:
                    p3 = [x1all[-4], y1all[-4]]
                    p4 = [x1all[-1], y1all[-1]]
                else:
                    p3 = [x1all[0], y1all[0]]
                    p4 = [x1all[-1], y1all[-1]]
                norm = np.sqrt((p4[0] - p3[0])**2 + (p4[1] - p3[1])**2)
                p3x = p3[0] + far * (p4[0] - p3[0]) / norm
                p3y = p3[1] + far * (p4[1] - p3[1]) /norm
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
                p3x = p30[0] - far * (p4[0] - p30[0])/norm
                p3y = p30[1] - far * (p4[1] - p30[1]) /norm
                p3 = [p3x, p3y]
                [inter, pc] = intersection_seg(p1, p2, p3, p30, False)
                if inter:
                    point_inter0[i] = pc[0]
            if not inter:
                    no_inter0[i] = -99
        # if not inter:
        #     print('Warning: No intersection found when created new profile. (1)')
        #     point_inter0[i] = point_inter0[i-1] + 0.001

    # intersection second profile
    for j in range(0, len(x1all)):
        inter = False
        #p1 = [x1all[j], y1all[j]]
        #p2 = [xpro1[j], ypro1[j]]
        p1 = [xstart1[j], ystart1[j]]
        p2 = [xend1[j], yend1[j]]
        for j2 in range(0, len(x0all)-1):
            if max(x0all[j2], x0all[j2 + 1]) > min(p1[0], p2[0]) and max(y0all[j2], y0all[j2 + 1]) > min(p1[1], p2[1]):
                p3 = [x0all[j2], y0all[j2]]
                p4 = [x0all[j2+1], y0all[j2+1]]
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
            p3x = p3[0] + far * (p4[0] - p3[0])/norm
            p3y = p3[1] + far * (p4[1] - p3[1])/norm
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
            p3x = p30[0] - far * (p4[0] - p30[0])/norm
            p3y = p30[1] - far * (p4[1] - p30[1])/norm
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
        #     # plt.plot(p4[0], p4[1], '.r')
        #     # plt.plot(p30[0], p30[1], '.k')
        #     # plt.plot(x1all, y1all, '-r')
        #     # plt.plot(x0all, y0all, '-m')
        #     # print(far * (p4[0] - p30[0]))
        #     # plt.show()
        #     point_inter1[j] = point_inter1[j - 1] + 0.001

    # find points between the profile
    len0 = len(x0all[no_inter0 ==0])
    len1 = len(x1all[no_inter1 ==0])
    for n in range(0, nb_pro):
        pm_all = np.zeros((len0 + len1, 2))  # x, y, dist to be ordered
        div = (n+1) / (nb_pro + 1)
        div2 = 1 - div

        # point linked with the first profile
        pm_all[:len0, 0] = x0all[no_inter0 ==0] + (point_inter0[no_inter0 == 0, 0] - x0all[no_inter0 ==0]) * div
        pm_all[:len0, 1] = y0all[no_inter0 ==0] + (point_inter0[no_inter0 ==0, 1] - y0all[no_inter0 ==0]) * div

        # point related to second profile
        pm_all[len0:, 0] = x1all[no_inter1 ==0] + (point_inter1[no_inter1 ==0, 0] - x1all[no_inter1 ==0]) * div2
        pm_all[len0:, 1] = y1all[no_inter1 ==0] + (point_inter1[no_inter1 ==0, 1] - y1all[no_inter1 ==0]) * div2

        if len1 + len0 == 0:
            print('Warning: Middle profile empty \n')


        # sort so tha each point is one after the other
        if trim:
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
                    pm_all = pm_all[w2 + 1:, :]
                    break
            p1seg = [x0all[0], y0all[0]]
            p2seg = [x1all[0], y1all[0]]
            for w in range(0, len(pm_all[:, 0])-1):
                p3 = pm_all[w]
                p4 = pm_all[w+1]
                [inter, pc] = intersection_seg(p1seg, p2seg, p3, p4, False)
                if inter:
                    pm_all = pm_all[:w+1, :]
                    break

        mid_point_x.append(pm_all[:, 0])
        mid_point_y.append(pm_all[:, 1])

    return mid_point_x, mid_point_y


def create_dummy_substrate(coord_pro, sqrtnp):
    """
    For testing purposes, it can be useful to create a substrate input even if one does not exist.
    This substrate is compose of n triangle situated on the rivers in the same coodinates system
    :param coord_pro: the coordinate of each profile
    :param: sqrtnp the number of point which will compose one side of the new substrate grid
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
    distx = (maxx-minx)/(sqrtnp-1)
    disty = (maxy - miny) / (sqrtnp-1)
    x = np.arange(minx, maxx + distx, distx)
    y = np.arange(miny, maxy+disty, disty)
    for i in range(0, sqrtnp):
        for j in range(0, sqrtnp):
            coord_sub.extend([x[i],y[j]])

    dict_point = dict(vertices= coord_sub)
    grid_dict = triangle.triangulate(dict_point)  # 'p' would allos for constraint V for verbose

    ikle_sub = grid_dict['triangles']
    coord_sub = grid_dict['vertices']

    return ikle_sub, coord_sub


def plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, point_c_all=[], inter_vel_all=[], inter_h_all=[], path_im = [], coord_pro2 = []):
    """
    Function to plot a grid, copied from hec-ras2D
    :param point_all_reach: the grid point by reach
    :param ikle_all: the connectivity table by reach
    :param lim_by_reach the segment giving the limits of the grid
    :param hole_all: the coordinates of the holes
    :param overlap: the point of each reach which are also on an other reach
    :param point_c_all: the centroid of each element
    :param inter_vel_all: the interpolated velocity for each reach
    :param inter_h_all: the interpolated height
    :param path_im the path where to save the image
    :return:
    """
    plt.close()

    # plot only the grid
    fig = plt.figure()
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

            plt.plot(xlist, ylist, linewidth=0.1)
            if lim_by_reach:
                for hh in range(0, len(h)):
                     plt.plot(h[hh][0], h[hh][1], "g*", markersize=3)
                for i in range(0, len(seg_reach)):
                    seg = seg_reach[i]
                    if i % 3 == 0:
                        m = 'r'
                    elif i% 3 == 1:
                        m = 'g'
                    else:
                        m = 'y'
                    plt.plot([coord_p[seg[0], 0], coord_p[seg[1], 0]], [coord_p[seg[0], 1], coord_p[seg[1], 1]], m, linewidth=1)
                overlap_r = overlap[r]
                #if len(overlap_r) > 0:
                    #for i in range(0, len(overlap_r)):
                       # plt.plot(coord_p[overlap_r[i], 0],coord_p[overlap_r[i], 1], 'k.')
            #for i in range(0, int(len(seg_island)/2)):
             #seg = [int(seg_island[2*i, 2]), int(seg_island[2*i+1, 2])]
             # plt.plot([coord_p[seg[0], 0], coord_p[seg[1], 0]], [coord_p[seg[0], 1], coord_p[seg[1], 1]], 'g', linewidth=1)
    #plt.plot(xlist, ylist, 'g.', markersize=1)
    #if coord_pro2:
    #   for p in range(0, len(coord_pro2)):
    #        plt.plot(coord_pro2[p][0], coord_pro2[p][1], 'b.', markersize=2)
    #plt.axis('equal')
    plt.title('Computational Grid')
    plt.savefig(os.path.join(path_im, "Grid_new_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
    plt.savefig(os.path.join(path_im, "Grid_new_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
    plt.close()
    #plt.show()

    # plot the interpolated velocity
    if len(inter_vel_all) >0: #0
        cm = plt.cm.get_cmap('coolwarm')
        plt.figure()
        for r in range(0, len(inter_vel_all)):
            point_here = np.array(point_all_reach[r])
            inter_vel = inter_vel_all[r]
            print(len(point_here))
            print(len(inter_vel))
            if len(point_here[:, 0]) == len(inter_vel):
                sc = plt.tricontourf(point_here[:, 0],point_here[:, 1], ikle_all[r], inter_vel
                                     , min=0, max=np.nanmax(inter_vel), cmap=cm)
                if r == len(inter_vel_all) -1:
                    cbar = plt.colorbar(sc)
                    cbar.ax.set_ylabel('Velocity [m/sec]')
            else:
                print('Warning: One reach could not be drawn. \n')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Interpolated velocity')
        plt.savefig(os.path.join(path_im, "Vel_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
        plt.savefig(os.path.join(path_im, "Vel_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
        plt.close()

    if len(inter_h_all) > 0:  # 0
        cm = plt.cm.get_cmap('jet')
        plt.figure()
        for r in range(0, len(inter_h_all)):
            point_here = np.array(point_all_reach[r])
            inter_h = inter_h_all[r]
            if len(point_here) == len(inter_h):
                sc = plt.tricontourf(point_here[:, 0], point_here[:, 1], ikle_all[r], inter_h
                                     , min=0, max=np.nanmax(inter_h), cmap=cm)
                if r == len(inter_h_all) - 1:
                    cbar = plt.colorbar(sc)
                    cbar.ax.set_ylabel('Water height [m]')
            else:
                print('Warning: One reach could not be drawn. \n')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Interpolated water height')
        plt.savefig(os.path.join(path_im, "Water_height_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"))
        plt.savefig(os.path.join(path_im, "Water_height_inter_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"))
        plt.close()

    #plt.show()


def main():

        #distrbution vitesse mascaret
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


        # #test hec-ras
        #CAREFUL SOME DATA CAN BE IN IMPERIAL UNIT (no impact on the code, but result can look unlogical)
        path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
        path_test = r'C:\Users\diane.von-gunten\Documents\HEC Data\HEC-RAS\Steady Examples'
        name = 'CRITCREK'  # CRITCREK, LOOP
        name_xml = name + '.O03.xml'
        name_geo = name + '.g01'
        path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
        #coord_sub = [[0.5, 0.2], [0.6, 0.6], [0.0, 0.6]]
        #ikle_sub = [[0, 1, 2]]

        [coord_pro, vh_pro, nb_pro_reach] = Hec_ras06.open_hecras(name_geo, name_xml, path_test, path_test, path_im, False)
        # whole profile
        #[point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, seg_island,
         #coord_pro, point_c_all] = create_grid(coord_pro, 10, nb_pro_reach)
        #plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, seg_island)

        [ikle_sub, coord_sub] = create_dummy_substrate(coord_pro, 5)

        for t in range(0, len(vh_pro)):
            which_pro = vh_pro[t]
            [point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, coord_pro2, point_c_all] \
               = create_grid(coord_pro, 13,[], [], nb_pro_reach, which_pro)  # [], [] -> coord_sub, ikle_sub,
            #[ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
              #  create_grid_only_1_profile(coord_pro, nb_pro_reach, which_pro)
            if which_pro:
                [inter_vel_all, inter_h_all] = interpo_linear(point_all_reach, coord_pro2, vh_pro[t])
                plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, point_c_all, inter_vel_all, inter_h_all, path_im)
                #plot_grid(point_all_reach, ikle_all, [], [], [], point_c_all, inter_vel_all, inter_height_all, path_im)
            else:
                pass
                #plot_grid(point_all_reach, ikle_all, lim_by_reach, hole_all, overlap, seg_island)


if __name__ == '__main__':
    main()
