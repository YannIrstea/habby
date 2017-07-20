from io import StringIO
import sys
import os
from src import load_hdf5
import time
from copy import deepcopy
import numpy as np
import triangle
import matplotlib.pyplot as plt


def merge_grid_and_save(hdf5_name_hyd, hdf5_name_sub, path_hdf5, default_data, name_prj, path_prj, model_type,
                        q=[], print_cmd=False):
    """
    This function call the merging of the grid between the grid from the hydrological data and the substrate data.
    It then save the merged data and the substrate data in a common hdf5 file. This function is called in a second
    thread to avoid freezin gthe GUI. This is why we have this extra-function just to call save_hdf5() and
    merge_grid_hydro_sub().

    :param hdf5_name_hyd: the name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the name of the hdf5 with the substrate data
    :param path_hdf5: the path to the hdf5 data
    :param default_data: The substrate data given in the region of the hydrological grid where no substrate is given
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: the type of the "model". In this case, it is just 'SUBSTRATE'
    :param q: used to share info with the GUI when this thread have finsihed (print_cmd = False)
    :param print_cmd: If False, print to the GUI (usually False)
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # merge the grid
    [ikle_both, point_all_both, sub_pg_all_t, sub_dom_all_t, inter_vel_all_both, inter_h_all_both] = \
        merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, path_hdf5, default_data)
    if ikle_both == [-99]:
        print('Error: data not merged.\n')
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # get time step name if they exists
    sim_name = load_hdf5.load_timestep_name(hdf5_name_hyd, path_hdf5)

    # save hdf5
    if len(os.path.basename(hdf5_name_hyd)) > 25:
        name_hdf5merge = 'MERGE_' + os.path.basename(hdf5_name_hyd)[:-25]  # take out the date in most case
    else:
        name_hdf5merge = 'MERGE_' + os.path.basename(hdf5_name_hyd)
    load_hdf5.save_hdf5(name_hdf5merge, name_prj, path_prj, model_type, 2, path_hdf5, ikle_both,
                        point_all_both, [], inter_vel_all_both, inter_h_all_both, [], [], [], [], True,
                        sub_pg_all_t, sub_dom_all_t, sim_name=sim_name)

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, path_hdf5, default_data=1, path_prj=''):
    """
    After the data for the substrate and the hydrological data are loaded, they are still in different grids.
    This functions will merge both grid together. This is done for all time step and all reaches. If a
    constant substrate is there, the hydrological hdf5 is just copied.

    :param hdf5_name_hyd: the name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the name of the hdf5 with the substrate data
    :param path_hdf5: the path to the hdf5 data
    :param default_data: The substrate data given in the region of the hydrological grid where no substrate is given
    :param path_prj: the path to the project
    :return: the connectivity table, the coordinates, the substrated data, the velocity and height data all in a merge form.

    """
    failload = [-99], [-99], [-99], [-99], [-99], [-99]
    sub_dom_all_t = []
    sub_pg_all_t = []
    ikle_both = []
    point_all_both = []
    point_c_all_both = []
    vel_all_both = []
    height_all_both = []

    try:
        default_data = float(default_data)
    except ValueError:
        print('Error: Default data should be a float. (1)\n')
        return failload

    m = time.time()
    # load hdf5 hydro
    [ikle_all, point_all, inter_vel_all, inter_height_all] = load_hdf5.load_hdf5_hyd(hdf5_name_hyd, path_hdf5)

    # load hdf5 sub
    [ikle_sub, point_all_sub, data_sub_pg, data_sub_dom] = load_hdf5.load_hdf5_sub(hdf5_name_sub, path_hdf5)

    print('Load done')

    # simple test case to debug( two triangle separated by an horizontal line)
    # point_all = [[np.array([[0.5, 0.55], [0.3, 0.55], [0.5, 0.3], [0.3, 0.3]])]]
    # ikle_all = [[np.array([[0, 1, 3], [0, 2, 3]])]]
    # ikle_sub = np.array([[0, 1, 2]])
    # point_all_sub = np.array([[0.4, 0.45], [0.48, 0.45], [0.32, 0.35], [1, 1]])

    # special cases and checks
    if len(ikle_all) == 1 and ikle_all[0] == [-99]:
        print('Error: hydrological data could not be loaded.')
        return failload
    elif len(ikle_sub) == 1 and ikle_sub[0][0] == -99:
        print('Error: Substrate data could not be loaded.')
        return failload
    elif len(point_all_sub) == 0 and ikle_sub == []:
        # if constant substrate, the hydrological grid is used
        # the default value is not really used
        print('Warning: Constant substrate.')
        for t in range(0, len(ikle_all)):
            sub_data_all_pg = []
            sub_data_all_dom = []
            if len(ikle_all[t]) > 0:
                for r in range(0, len(ikle_all[t])):
                    try:
                        sub_data_pg = np.zeros(len(ikle_all[t][r]), ) + float(data_sub_dom[0])
                        sub_data_dom = np.zeros(len(ikle_all[t][r]), ) + float(data_sub_pg[0])
                    except ValueError or TypeError:
                        print('Error: no int in substrate. (only float or int accepted for now). \n')
                        return failload
                    sub_data_all_pg.append(sub_data_dom)
                    sub_data_all_dom.append(sub_data_pg)
            elif t > 0:
                for r in range(0, len(ikle_all[t])):
                    sub_data_all_pg.append([-99])
                    sub_data_all_dom.append([-99])

            sub_dom_all_t.append(sub_data_all_dom)
            sub_pg_all_t.append(sub_data_all_pg)

        return ikle_all, point_all, sub_pg_all_t, sub_dom_all_t, inter_vel_all, inter_height_all
    elif ikle_sub == [] and len(point_all_sub) != 0:
        print('no connectivity table found for the substrate. Check the format of the hdf5 file. \n')
        return failload
    elif ikle_all == []:
        print('no connectivity table found for the hydrology. Check the format of the hdf5 file. \n')
        return failload
    elif len(ikle_sub[0]) < 3:
        print('Error: the connectivity table of the substrate is badly formed.')
        return failload

    # m1 = time.time()
    # print('Time to load:')
    # print(m1 - m)

    # merge the grid for each time step (the time step 0 is the full profile)
    for t in range(0, len(ikle_all)): # len(ikle_all)

        ikle_all2 = []
        point_all2 = []
        data_sub2_pg = []
        data_sub2_dom = []
        vel2 = []
        height2 = []

        if len(ikle_all[t]) > 0:
            # print('Timestep: ' + str(t))
            for r in range(0, len(ikle_all[t])):
                point_before = np.array(point_all[t][r])
                ikle_before = np.array(ikle_all[t][r])
                if t > 0:
                    vel_before = inter_vel_all[t][r]
                    height_before = inter_height_all[t][r]
                else:
                    vel_before = []
                    height_before = []
                a = time.time()
                if len(ikle_before) < 1:
                    print('Warning: One time steps without grids found. \n')
                    data_sub2_pg.append([-99])
                    data_sub2_dom.append([-99])
                    vel2.append([-99])
                    height2.append([-99])
                    ikle_all2.append([[-99, -99]])
                    point_all2.append([[[-99, -99]]])
                    break

                # find intersection betweeen hydrology and substrate
                # a = time.time()
                [ikle_sub, coord_p_sub, data_sub_pg,  data_sub_dom, data_crossing, sub_cell] = \
                    find_sub_and_cross(ikle_sub, point_all_sub, ikle_before, point_before, data_sub_pg, data_sub_dom)

                # b = time.time()
                # print('time crossing')
                # print(b - a)

                # print('found all crossing')

                # if no intersection found
                if len(data_crossing[0]) < 1:
                    print('Warning: No intersection between the grid and the substrate for one reach.\n')
                    try:
                        sub_data_here = np.zeros(len(ikle_all[t][r]), ) + float(default_data)
                    except ValueError:
                        print('Error: no float in substrate. (only float accepted for now).\n')
                        return failload
                    data_sub2_pg.append(sub_data_here)
                    data_sub2_dom.append(sub_data_here)
                    vel2.append(vel_before)
                    height2.append(height_before)
                    ikle_all2.append(ikle_before)
                    point_all2.append(point_before)
                else:

                    # create the new grid based on intersection found
                    b = time.time()
                    [ikle_here, point_all_here, new_data_sub_pg, new_data_sub_dom, vel_new, height_new] = \
                        create_merge_grid(ikle_before, point_before, data_sub_pg, data_sub_dom, vel_before, height_before,
                                          ikle_sub, default_data, data_crossing, sub_cell)
                    c = time.time()

                    # print('TIME NEW GRID')
                    # print(c - b)
                    ikle_all2.append(np.array(ikle_here))
                    point_all2.append(np.array(point_all_here))
                    data_sub2_pg.append(new_data_sub_pg)
                    data_sub2_dom.append(new_data_sub_dom)
                    vel2.append(vel_new)
                    height2.append(height_new)

                    # print('Time to find the intersection point')
                    # print(b-a)
                    # print('Time to find the merge grid')
                    # print(c-b)

        ikle_both.append(ikle_all2)
        point_all_both.append(point_all2)
        sub_pg_all_t.append(data_sub2_pg)
        sub_dom_all_t.append(data_sub2_dom)
        vel_all_both.append(vel2)
        height_all_both.append(height2)

    return ikle_both, point_all_both, sub_pg_all_t, sub_dom_all_t, vel_all_both, height_all_both


def find_sub_and_cross(ikle_sub, coord_p_sub, ikle, coord_p, data_sub_pg, data_sub_dom):
    """
    A function which find where the crossing points are. Crossing points are the points on the triangular side of the
    hydrological grid which cross with a side of the substrate grid. The algo based on finding if points of one elements
    are in the same polygon using a ray casting method. We assume that the polygon forming the subtrate grid are convex.
    Otherwise it would not work in all cases. We could do a small function to test or correct this.
    We also neglect the case where a substrate cell at the border of the subtrate grid is fully in a hydrological cell.

    IMPORTANT: polygon should be convex.

    :param ikle_sub: the connectivity table for the substrate
    :param coord_p_sub: the coordinates of the poitn forming the subtrate
    :param ikle: the connectivity table for the hydrology
    :param coord_p: the coordinate of the hydrology
    :param data_sub_dom: the subtrate data by subtrate cell (dominant)
    :param data_sub_pg: the substrate data by substrate cell (coarser)
    :return: the new substrate grid (ikle_sub, coord_p_sub, data_sub_pg, data_sub_dom, sub_cell), the data for
             the crossing point (hydrological element with a crossing, crossing point, substrate element linked with
             the crossing point, point of substrate inside, substrate element linked with the substrate point,
             side of the crossing points, substrate leemnt link with hydro_point).

    """

    # preparation
    ikle_sub = np.array(ikle_sub)
    ikle = np.array(ikle)
    sub_cell = np.zeros((len(ikle),)) -99  # the link between substrate cell and hydro cell
    el_cross = []
    hydro_el = []
    sub_point_in_cross = []
    sub_point_in_el = []
    point_cross = []
    side_point_cross = []
    point_cross_el = []

    # check that the subtrate grid is convex and transform if necesary
    # check all angle < 180 degree
    # not done yet

    # erase substrate cell which are outside of the hydrological grid (to optimize)
    data_sub_pg2 = []
    data_sub_dom2 = []
    ikle_sub2 = []
    xhydmax = max(coord_p[:, 0])
    yhydmax = max(coord_p[:, 1])
    xhydmin = min(coord_p[:, 0])
    yhydmin = min(coord_p[:, 1])
    i = 0
    for k in ikle_sub:
        coord_x_sub = np.array([coord_p_sub[int(k[0]), 0], coord_p_sub[int(k[1]), 0], coord_p_sub[int(k[2]), 0]])
        coord_y_sub = np.array([coord_p_sub[int(k[0]), 1], coord_p_sub[int(k[1]), 1], coord_p_sub[int(k[2]), 1]])
        if xhydmax >= min(coord_x_sub) and xhydmin <= max(coord_x_sub) and \
                        yhydmax >= min(coord_y_sub) and yhydmin <= max(coord_y_sub):
            ikle_sub2.append(k)
            data_sub_pg2.append(data_sub_pg[i])
            data_sub_dom2.append(data_sub_dom[i])
        i += 1
    ikle_sub = np.array(ikle_sub2)
    if len(ikle_sub) < 1:
        return ikle_sub, coord_p_sub, data_sub_pg,  data_sub_dom, [[]], sub_cell
    data_sub_pg = np.copy(data_sub_pg2)
    data_sub_dom = np.copy(data_sub_dom2)

    # preparation 2
    nb_poly = len(ikle_sub)
    nb_tri = len(ikle)
    coord_p_subx = coord_p_sub[:, 0]
    coord_p_suby = coord_p_sub[:, 1]
    coord_hyd_x = coord_p[:, 0]
    coord_hyd_y = coord_p[:, 1]

    # for each substrate element get xmin, xmax
    px = np.array([coord_p_subx[ikle_sub[:, 0]], coord_p_subx[ikle_sub[:, 1]], coord_p_subx[ikle_sub[:, 2]]])
    py = np.array([coord_p_suby[ikle_sub[:, 0]], coord_p_suby[ikle_sub[:, 1]], coord_p_suby[ikle_sub[:, 2]]])
    max_px = np.max(px, 0)
    min_px = np.min(px, 0)
    max_py = np.max(py, 0)
    min_py = np.min(py, 0)
    # order it along xmin
    indmin = np.argsort(min_px)
    max_px = max_px[indmin]
    min_px = min_px[indmin]
    max_py = max_py[indmin]
    min_py = min_py[indmin]
    ikle_sub = ikle_sub[indmin, :]
    data_sub_pg = data_sub_pg[indmin]
    data_sub_dom = data_sub_dom[indmin]

    # for each hydrological cell
    for e in range(0, nb_tri):

        # find the first substrate cell with x > xmin (quick because ordered)
        xhyd = coord_hyd_x[ikle[e, 0]]
        yhyd = coord_hyd_y[ikle[e, 0]]
        sub_num = [-999, -999, -999]  # where are the polygon

        i = np.searchsorted(min_px, xhyd, side='right') + 2
        if i > len(ikle_sub) - 1:
            i = len(ikle_sub) - 1
        while i > 1 and (max_px[i] < xhyd or min_py[i] > yhyd or max_py[i] < yhyd):
            i -= 1

        # for each points in this triangle
        for p in range(0, 3):

            # go to the next triangle
            if p > 0:
                xhyd = coord_hyd_x[ikle[e, p]]
                yhyd = coord_hyd_y[ikle[e, p]]
                if i < nb_poly-4:
                    i += 4
            find_sub = False
            j = 0
            # i = 0 debug

            while not find_sub:

                # find if this point is in a polygon
                # using to send a ray outside of the polygon
                # idea from http://geomalgorithms.com/a03-_inclusion.html
                # the number of time a particular point intersect with a segments
                intersect = 0.0
                # find the "substrate" point of this polygon
                poly_i = ikle_sub[i]
                # for each side of the substrate polygon
                xsub0 = coord_p_subx[poly_i[0]]
                ysub0 = coord_p_suby[poly_i[0]]
                coord_old0 = [xsub0, ysub0]
                coord_old = coord_old0
                lenpoly = len(poly_i)
                for i2 in range(0, lenpoly):
                    if i2 == lenpoly - 1:
                        [x1sub, y1sub] = coord_old  # coord_p_sub[int(poly_i[i2])]
                        [x2sub, y2sub] = coord_old0  # coord_p_sub[int(poly_i[0])]
                    else:
                        [x1sub, y1sub] = coord_old
                        x2sub = coord_p_subx[poly_i[i2 + 1]]  # quicker when coord_p_sub is in x and y
                        y2sub = coord_p_suby[poly_i[i2 + 1]]
                        coord_old = [x2sub, y2sub]
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
                            # manage the case where the yhyd is at the same height than subtrate
                            if yhyd == y1sub:
                                if y2sub < yhyd:
                                    intersect += 1
                            elif yhyd == y2sub:
                                if y1sub < yhyd:
                                    intersect += 1
                            # normal case
                            else:
                                intersect += 1
                # if number of intersection is odd, then point inside
                if intersect % 2 == 1:
                    find_sub = True
                    sub_num[p] = i
                    # if p == 0:
                    #     print('new')
                    # print(j)

                # get to the next polygon
                i -= 1
                j += 1
                if i < 0:
                    i = nb_poly - 1
                if j == nb_poly+3:
                    find_sub = True
                    sub_num[p] = -1

        # if no intersection was found
        # the hypothesis that substrate in convex is imporant here, it would not work otherwise
        if sub_num[0] == sub_num[1] and sub_num[1] == sub_num[2]:
            sub_cell[e] = sub_num[0]

        # if intersection
        else:
            el_cross.append(e)
            sub_point_in_cross_here = []
            sub_point_in_el_here = []
            point_cross_here = []
            side_point_cross_here = []
            point_cross_el_here = []

            for w in range(0, 3):  # look to the 3 hydro point

                w1 = w
                w2 = w+1
                if w == 2:
                    w2 = 0

                if sub_num[w1] != sub_num[w2]:  # if intersection on this side
                    hyd1 = [coord_hyd_x[ikle[e, w1]], coord_hyd_y[ikle[e, w1]]]
                    hyd2 = [coord_hyd_x[ikle[e, w2]], coord_hyd_y[ikle[e, w2]]]
                    side_point_cross_here.append(w)
                    # intersection with the first subtrate point
                    if sub_num[w1] != -1:
                        a1 = ikle_sub[sub_num[w1]]
                        for seg in range(0, len(a1)):
                            if seg < len(a1) - 1:
                                sub1 = coord_p_sub[int(a1[seg])]
                                sub2 = coord_p_sub[int(a1[seg + 1])]
                            else:
                                sub1 = coord_p_sub[int(a1[seg])]
                                sub2 = coord_p_sub[int(a1[0])]
                            p_cross = intersec_cross(hyd1, hyd2, sub1, sub2)
                            if p_cross[1] is not None:
                                # add the point cross
                                point_cross_here.append(p_cross)
                                point_cross_el_here.append(sub_num[w1])
                                if sub_num[w2] == -1:
                                    point_cross_here.append(p_cross)
                                    point_cross_el_here.append(sub_num[w2])
                                # test if there is substate point in the element
                                p1 = coord_p[ikle[e, 0]]
                                p2 = coord_p[ikle[e, 1]]
                                p3 = coord_p[ikle[e, 2]]
                                inside1 = inside_trigon(sub1, p1, p2, p3)
                                inside2 = inside_trigon(sub2, p1, p2, p3)
                                if inside1:
                                    sub_point_in_cross_here.append(sub1)
                                    sub_point_in_el_here.append(sub_num[w1])
                                if inside2:
                                    sub_point_in_cross_here.append(sub2)
                                    sub_point_in_el_here.append(sub_num[w1])

                    # find intersection with the second subtrate cell  (if not outside of substrate grid)
                    if sub_num[w2] != -1:
                        a1 = ikle_sub[sub_num[w2]]
                        for seg in range(0, len(a1)): # test all substrate side
                            if seg < len(a1) - 1:
                                sub1 = coord_p_sub[int(a1[seg])]
                                sub2 = coord_p_sub[int(a1[seg + 1])]
                            else:
                                sub1 = coord_p_sub[int(a1[seg])]
                                sub2 = coord_p_sub[int(a1[0])]
                            p_cross = intersec_cross(hyd1, hyd2, sub1, sub2)
                            if p_cross[1] is not None:
                                # add the point cross
                                point_cross_here.append(p_cross)
                                point_cross_el_here.append(sub_num[w2])
                                if sub_num[w1] == -1:
                                    point_cross_here.append(p_cross)
                                    point_cross_el_here.append(sub_num[w1])
                                # test if there is substate point in the element
                                p1 = coord_p[ikle[e, 0]]
                                p2 = coord_p[ikle[e, 1]]
                                p3 = coord_p[ikle[e, 2]]
                                inside1 = inside_trigon(sub1, p1, p2, p3)
                                inside2 = inside_trigon(sub2, p1, p2, p3)
                                if inside1:
                                    sub_point_in_cross_here.append(sub1)
                                    sub_point_in_el_here.append(sub_num[w2])
                                if inside2:
                                    sub_point_in_cross_here.append(sub2)
                                    sub_point_in_el_here.append(sub_num[w2])
                                #break

                    # check if intersection identical
                    if len(point_cross_here) >=2:
                        dist = abs(point_cross_here[-1][0] - point_cross_here[-2][0]) \
                               + abs(point_cross_here[-1][1] - point_cross_here[-2][1])
                        # if no, test all possible intersections (slow)
                        if dist > 1e-7 or -1 in sub_num:
                            # in this case we will find again the old intersection
                            del point_cross_here[-1]
                            del point_cross_here[-1]
                            del point_cross_el_here[-1]
                            del point_cross_el_here[-1]
                            lenp = len(point_cross_here)

                            elhere = 0
                            for a1 in ikle_sub:
                                len_k = len(a1)
                                for seg in range(0, len_k):
                                    if seg < len_k - 1:
                                        sub1 = coord_p_sub[int(a1[seg])]
                                        sub2 = coord_p_sub[int(a1[seg + 1])]
                                    else:
                                        sub1 = coord_p_sub[int(a1[seg])]
                                        sub2 = coord_p_sub[int(a1[0])]
                                    p_cross = intersec_cross(hyd1, hyd2, sub1, sub2)
                                    if p_cross[1] is not None:
                                        # add the point cross
                                        point_cross_here.append(p_cross)
                                        point_cross_el_here.append(elhere)
                                        # test if there is substate point in the element
                                        p1 = coord_p[ikle[e, 0]]
                                        p2 = coord_p[ikle[e, 1]]
                                        p3 = coord_p[ikle[e, 2]]
                                        inside1 = inside_trigon(sub1, p1, p2, p3)
                                        inside2 = inside_trigon(sub2, p1, p2, p3)
                                        if inside1:
                                            sub_point_in_cross_here.append(sub1)
                                            sub_point_in_el_here.append(elhere)
                                        if inside2:
                                            sub_point_in_cross_here.append(sub2)
                                            sub_point_in_el_here.append(elhere)
                                elhere += 1

                            if len(point_cross_here) > 0:
                                point_cross_here_this_s = point_cross_here[lenp:]
                                if sub_num[w1] == -1:  # in this case we would have find only one intersection
                                    min_dist = 1e10
                                    idx2 = 0
                                    for id2, m in enumerate(point_cross_here_this_s):
                                        dist = abs(m[0] - hyd1[0]) + abs(m[1] - hyd1[1])
                                        if dist < min_dist:
                                            idx2 = id2
                                            min_dist = dist
                                    point_cross_el_here.append(-1)
                                    point_cross_here.append(point_cross_here_this_s[idx2])
                                if sub_num[w2] == - 1:
                                    min_dist = 1e10
                                    idx2 = 0
                                    for id2, m in enumerate(point_cross_here_this_s):
                                        dist = abs(m[0] - hyd2[0]) + abs(m[1] - hyd2[1])
                                        if dist < min_dist:
                                            idx2 = id2
                                            min_dist = dist
                                    point_cross_el_here.append(-1)
                                    point_cross_here.append(point_cross_here_this_s[idx2])


                #in case there is a substrate cell in the hydro cells (slow)
                #we might miss case where a border substrate cell is in an hydro cell
                # if len(sub_point_in_cross_here) > 2:
                #     # test if more substrate point inside
                #     seg_tri = []
                #     seg_tri.append([coord_p[ikle[e, 0]], coord_p[ikle[e, 1]]])
                #     seg_tri.append([coord_p[ikle[e, 1]], coord_p[ikle[e, 2]]])
                #     seg_tri.append([coord_p[ikle[e, 2]], coord_p[ikle[e, 0]]])
                #     for s0 in coord_p_sub:
                #         inside1 = manage_grid_8.inside_polygon(seg_tri, s0)
                #         if inside1:
                #             sub_point_in_cross_here.append(s0)
                #     for s1 in sub_point_in_cross_here:
                #         # find to which substrate cell, this substrate point are part of
                #         # very slow but very rare
                #         ind = np.where((coord_hyd_x == s1[0]) & (coord_hyd_y == s1[1]))[0]
                #         # if one cell not there yet, add it on to these points
                #         for indi in ind:
                #             if indi not in sub_point_in_el:
                #                 sub_point_in_el_here.append(indi)

            # add all the info for this crossing element
            sub_point_in_cross.append(sub_point_in_cross_here)
            sub_point_in_el.append(sub_point_in_el_here)
            point_cross.append(point_cross_here)
            side_point_cross.append(side_point_cross_here)
            point_cross_el.append(point_cross_el_here)
            hydro_el.append(sub_num)

    data_crossing = [el_cross, point_cross_el, point_cross, side_point_cross, sub_point_in_cross, sub_point_in_el,
                     hydro_el]
    return ikle_sub, coord_p_sub, data_sub_pg,  data_sub_dom, data_crossing, sub_cell


def inside_trigon(pt, p0, p1, p2):
    """
    This function check if a point is in a triangle using the barycentric coordinates.

    :param pt: the point to determine if it is in or not
    :param p0: the first point of triangle
    :param p1: the second point of triangle
    :param p2: the third point of triangle
    :return: A boolean (Ture if pt inside of triangle)
    """
    p0x = p0[0]
    p0y = p0[1]
    p1x = p1[0]
    p1y = p1[1]
    p2x = p2[0]
    p2y = p2[1]

    area = 0.5 * (-p1y*p2x + p0y*(-p1x + p2x) + p0x*(p1y - p2y) + p1x*p2y)
    if area < 1e-15:
        s = 1 / (2 * area) * (p0y * p2x - p0x * p2y + (p2y - p0y) * pt[0] + (p0x - p2x) * pt[1])
        t = 1 / (2 * area) * (p0x * p1y - p0y * p1x + (p0y - p1y) * pt[0] + (p1x - p0x) * pt[1])
    else:
        return False

    if s >= 0 and t >= 0 and 1-s-t >= 0:
        return True
    else:
        return False


def intersec_cross(hyd1, hyd2, sub1, sub2):
    """
    A function function to calculate the intersection, segment are not parrallel,
    used in case where we know that the intersection exists

    :param hyd1: the first hydrological point
    :param hyd2: the second
    :param sub1: the first substrate point
    :param sub2: the second
    :return: intersection
    """

    sub1 = np.array(sub1)
    sub2 = np.array(sub2)
    wig = 1e-5

    [sx,sy] = [hyd2[0] - hyd1[0], hyd2[1] - hyd1[1]]
    [rx,ry] = [sub2[0] - sub1[0], sub2[1] - sub1[1]]
    rxs = rx * sy - ry * sx
    term2 = (hyd1[0] - sub1[0]) * ry - rx * (hyd1[1]- sub1[1])
    xcross = None
    ycross = None

    if rxs ==0 and term2 ==0:
        print('collinear points')
    if rxs != 0:
        u = term2 / rxs
        t = ((hyd1[0] - sub1[0]) * sy - sx * (hyd1[1] - sub1[1])) / rxs
        if 0.0 -wig <=t<= 1.0+wig and 0.0 - wig <=u<= 1.0+wig:
            xcross = hyd1[0] + u * sx
            ycross = hyd1[1] + u * sy
    else:
        print('rxs == 0')
    return [xcross, ycross]


def create_merge_grid(ikle, coord_p, data_sub_pg, data_sub_dom, vel, height,ikle_sub,
                      default_data, data_crossing, sub_cell):
    """
    A function to update the grid after finding the crossing points. It also get the substrate_data for each cell
    of the new grid.

    :param ikle:  the hydrological grid to be merge with the substrate grid
    :param coord_p: the coordinate of the point of the hydrological grid
    :param data_sub_pg: the coarser substrate data by hydrological cell (3 information by cells realted to
           the three points)
    :param data_sub_dom: the dominant substrate data by hydrological cell (3 information by cells realted to
           the three points)
    :param vel: the velocity (one time step, one reach) for each point in coord_p
    :param height: the water height (one time step, one reach) for each point in coord_p
    :param ikle_sub: the connectivity table for the substrate
    :param default_data: the default substrate data
    :param data_crossing: the hydrological elment with a crossing and the info for this crossing (a list of list)
    :return: the new grid

    **Technical comments**

    This function corrects all element of the grids where a crossing point have been found by the
    function find_sub_and_cross()

    There are three cases:

    a) one crossing point -> no change
    b) two crossing points and subtrate point inside -> done manually. We take the two crossing point and the side on
       which the crossing is done. Based on this, we correct the grid.
    c) more than two crossing point on the elements -> We call the extrenal module
       triangle to re-do some triagulations into the element. This last cases covers many possible case, but it is slow.
       To optimize, we can think about writing more individual cases. To follow the border of each subtrate cell in
       the "special cell", we do one triangulation by subtrate element, so we can have two or three triangulation.
       It is also important there that the substrate is convex as the triangulation is not constrained.

    """

    # preparation
    sub_cell = list(sub_cell)
    ikle = list(ikle)
    coord_p = list(coord_p)
    vel = list(vel)
    height = list(height)
    el_cross = data_crossing[0]
    point_cross_el = data_crossing[1]
    point_cross = np.array(data_crossing[2])
    side_point_cross = data_crossing[3]
    sub_point_in_cross = data_crossing[4]
    sub_point_in_el = data_crossing[5]
    hydro_el = data_crossing[6]
    to_delete = []

    for idx, e in enumerate(el_cross):

        pc_here = point_cross[idx]
        which_side = side_point_cross[idx]
        hydroe = hydro_el[idx]
        sube = sub_point_in_el[idx]
        pce = point_cross_el[idx]
        psub_in = sub_point_in_cross[idx]

        # if we have one crossing point, let's ignore it as the grid is already ok
        if len(pc_here) < 3 and len(psub_in) < 3:
            pass


        # if simple crossing do it 'by hand"(i.e. witbout the triangle module)
        # this is the case used most often so it must be quick
        # calling triangle is slow, so we used it only for rare case
        # analyze if other case should be handled separately
        elif len(pc_here) == 4 and len(psub_in) == 0:  # not on the same side if len(psub_in) == 0

            # will delete the old element at the end(ikle and substrate)
            to_delete.append(e)

            a1 = time.time()
            # new intersection point (we have two identical point)
            pc1 = [pc_here[0][0], pc_here[0][1]]
            pc2 = [pc_here[2][0], pc_here[2][1]]
            coord_p.append(pc2) # order matters
            coord_p.append(pc1)

            # get the new height and velocity data
            if len(vel) > 0:  # not used by t=0, for the grid representing the whole profile
                point_old = [coord_p[ikle[e][0]], coord_p[ikle[e][1]], coord_p[ikle[e][2]]]
                vel_here = [vel[ikle[e][0]], vel[ikle[e][1]], vel[ikle[e][2]]]
                h_here = [height[ikle[e][0]], height[ikle[e][1]], height[ikle[e][2]]]
                vel_new1 = get_new_vel_height_data(pc1, point_old, vel_here)
                vel_new2 = get_new_vel_height_data(pc2, point_old, vel_here)
                vel.append(vel_new1)
                vel.append(vel_new2)
                h_new1 = get_new_vel_height_data(pc1, point_old, h_here)
                h_new2 = get_new_vel_height_data(pc2, point_old, h_here)
                height.append(h_new1)
                height.append(h_new2)

            # update ikle
            # seg1 = [0,1] and seg2 = [1,2] in ikle order
            if sum(which_side) == 1:
                ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][1]])
                sub_cell.append(hydroe[1])
                if which_side[1] == 1:  # seg = [1, 2]
                    ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][0]])
                    sub_cell.append(hydroe[0])
                    ikle.append([len(coord_p) - 2, ikle[e][2], ikle[e][0]])
                    sub_cell.append(hydroe[0])
                else:
                    ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][2]])
                    sub_cell.append(hydroe[2])
                    ikle.append([len(coord_p) - 2, ikle[e][2], ikle[e][0]])
                    sub_cell.append(hydroe[0])
                    # seg1 = [0,1] and seg2 = [0,2]
            if sum(which_side) == 2:
                ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][0]])
                sub_cell.append(hydroe[0])
                if which_side[1] == 0:  # seg = [1, 0]
                    ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][2]])
                    sub_cell.append(hydroe[2])
                    ikle.append([len(coord_p) - 2, ikle[e][1], ikle[e][2]])
                    # new_data_sub[e][1] and new_data_sub[e][2] should be identical
                    sub_cell.append(hydroe[2])
                else:
                    ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][1]])
                    sub_cell.append(hydroe[1])
                    ikle.append([len(coord_p) - 2, ikle[e][1], ikle[e][2]])
                    sub_cell.append(hydroe[2])
            # seg1 = [2,1] and seg2 = [0,2]
            if sum(which_side) == 3:
                ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][2]])
                sub_cell.append(hydroe[2])
                if which_side[1] == 2:  # seg = [2, 0]
                    ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][1]])
                    sub_cell.append(hydroe[1])
                    ikle.append([len(coord_p) - 2, ikle[e][1], ikle[e][0]])
                    sub_cell.append(hydroe[0])
                else:
                    ikle.append([len(coord_p) - 1, len(coord_p) - 2, ikle[e][0]])
                    sub_cell.append(hydroe[0])
                    ikle.append([len(coord_p) - 2, ikle[e][1], ikle[e][0]])
                    sub_cell.append(hydroe[0])

        # complicated case with triangulation
        else:

            # will delete the old element at the end(ikle and substrate)
            to_delete.append(e)

            # get the points from the hydrological grid
            hyd1 = list(coord_p[ikle[e][0]])
            hyd2 = list(coord_p[ikle[e][1]])
            hyd3 = list(coord_p[ikle[e][2]])
            hyd_all = [[hyd1], [hyd2], [hyd3]]

            # if we have element with a area of zero (should not happend but did), let's erase this element
            if hyd1 == hyd2 or hyd2 == hyd3 or hyd1 == hyd3:
                pass
            else:
                # get all substrate element
                all_sub2 = deepcopy(hydroe)
                all_sub2.extend(pce)
                all_sub2.extend(sube)
                all_sub = list(set(all_sub2))  # only unique element
                for es in all_sub:

                    # get the point for this triangulation
                    point_new = [a[0] for idx, a in enumerate(hyd_all) if hydroe[idx] == es]
                    if len(pc_here) > 0:
                        point_new.extend([a for idx, a in enumerate(pc_here) if pce[idx] == es])
                    if len(psub_in) > 0:
                        point_new.extend([a for idx, a in enumerate(psub_in) if sube[idx] == es])

                    # for each substrate element, get a new triangulation
                    if len(point_new)> 2:
                        dict_point = dict(vertices=point_new)
                        grid_dict = triangle.triangulate(dict_point)  # 'p'

                        try:
                            ikle_new = grid_dict['triangles']
                            point_new = grid_dict['vertices']
                            # add this triagulation to the ikle
                            ikle.extend(list(np.array(ikle_new) + len(coord_p)))
                            coord_p.extend(point_new)

                            # add the elelement to sub_cell
                            sub_new = [es] * len(ikle_new)
                            sub_cell.extend(sub_new)

                            # add new velcoity and height data
                            if len(vel) > 0:
                                point_old = [coord_p[ikle[e][0]], coord_p[ikle[e][1]], coord_p[ikle[e][2]]]
                                vel_here = [vel[ikle[e][0]], vel[ikle[e][1]], vel[ikle[e][2]]]
                                for i in point_new:
                                    h_here = [height[ikle[e][0]], height[ikle[e][1]], height[ikle[e][2]]]
                                    vel_new1 = get_new_vel_height_data(i, point_old, vel_here)
                                    vel.append(vel_new1)
                                    h_new1 = get_new_vel_height_data(i, point_old, h_here)
                                    height.append(h_new1)
                        except KeyError:
                            # in case triangulation was not ok
                            print('Warning: an empty triangle was found by merge grid (1) \n')
                            # print(point_new)
                            # print(hydroe)
                            # print(hyd_all)
                            # print(pce)
                            # print(pc_here)

                    else:
                        print('Warning: an empty triangle was found by merge grid (2) \n')

    # create the new substrate data
    print('create the new substrate data')
    data_sub_dom_ok = np.zeros((len(sub_cell),))
    data_sub_pg_ok = np.zeros((len(sub_cell),))
    for i,s in enumerate(sub_cell):
        if s == -99 or s == -1:
            data_sub_dom_ok[i] = default_data
            data_sub_pg_ok[i] = default_data
        else:
            data_sub_dom_ok[i] = data_sub_dom[int(s)]
            data_sub_pg_ok[i] = data_sub_pg[int(s)]

    # remove element from ikle and new_data_sub
    # ikle = [i for j, i in enumerate(ikle) if j not in to_delete]  # slow
    for d in reversed(to_delete):  # to_delete is ordered
        del ikle[d]
    data_sub_pg_ok = np.delete(data_sub_pg_ok, to_delete)
    data_sub_dom_ok = np.delete(data_sub_dom_ok, to_delete)

    return ikle, coord_p, data_sub_pg_ok, data_sub_dom_ok, vel, height


def get_new_vel_height_data(newp, point_old, data_old):
    """
    This function gets the height and velcoity data for a new point in or on the side of an element. It does an
    average of the data (velocity or height) given at the node of the original (old) elements. This average is weighted
    as a function of the distance of the point.

    :param newp: the coordinates of the new points
    :param point_old: the coordinates of thre three old points (would work with more than three)
    :param data_old: the data for the point in point_old
    :return: the new data
    """
    point_old = np.array(point_old)
    d_all = np.sqrt((point_old[:,0] - newp[0])**2 + (point_old[:,1]-newp[1])**2)
    data_new = 0
    for i in range(0, len(point_old)):
        data_new += d_all[i] * data_old[i]
    sum_d_all = np.sum(d_all)
    data_new = data_new/sum_d_all
    return data_new


def fig_merge_grid(point_all_both_t, ikle_both_t, path_im, name_add='', ikle_orr=[], point_all_orr=[]):
    """
    A function to plot the grid after it was merged with the substrate data.
    It plots one time step at the time. This function is not used anymore by Habby. Indded, mesh_grid2 uses the
    function provided in manage_grid8.py to plot the grid and data after it is merged with the substrate. However,
    this function could be useful to debug if one wants to only plots teh grid and not the height/velocity data

    :param point_all_both_t: the coordinate of the points of the updated grid
    :param ikle_both_t: the connectivity table
    :param path_im: the path where the image should be saved
    :param name_add: the anem to be added to the figure name
    :param ikle_orr: the orginial ikle
    :param point_all_orr: the orginal point_all
    """
    if not os.path.isdir(path_im):
        print('Error: No directory found to save the figures \n')
        return

    # prepare grid
    xlist = []
    ylist = []
    fig = plt.figure()
    for r in range(0, len(ikle_both_t)):
        ikle = np.array(ikle_both_t[r])
        if len(ikle) > 1:
            coord_p = point_all_both_t[r]
            col_ikle = len(ikle[0])
            for i in range(0, len(ikle)):
                pi = 0
                while pi < col_ikle - 1:  # we have all sort of xells, max eight sides
                    p = int(ikle[i, pi])  # we start at 0 in python, careful about -1 or not
                    p2 = int(ikle[i, pi + 1])
                    xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
                    xlist.append(None)
                    ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
                    ylist.append(None)
                    pi += 1

                p = int(ikle[i, pi])
                p2 = int(ikle[i, 0])
                xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
                xlist.append(None)
                ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
                ylist.append(None)
        plt.plot(xlist, ylist, linewidth=0.1)
        #plt.plot(coord_p[:, 0], coord_p[:, 1], '*r')
    # for test, remove otherwise
    # point_all_sub = np.array([[0.4, 0.45], [0.48, 0.45], [0.32, 0.35]])
    # plt.plot(point_all_sub[:, 0], point_all_sub[:, 1], '*r')
    plt.title('Computational grid, updated for substrate data')
    plt.xlabel('x coordinate')
    plt.ylabel('y coordinate')
    #plt.show()
    plt.savefig(os.path.join(path_im, "Grid_merge_" + name_add + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                dpi=1000)
    plt.savefig(os.path.join(path_im, "Grid_merge_" + name_add + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                dpi=1000)


def main():
    """
    Used to test this module.
    """

    path = r'D:\Diane_work\output_hydro\substrate'


    # test create shape
    #filename = 'mytest.shp'
    #filetxt = 'sub_txt2.txt'
    # # load shp file
    # [coord_p, ikle_sub, sub_info] = load_sub_shp(filename, path, 'VELOCITY')
    # fig_substrate(coord_p, ikle_sub, sub_info, path)
    # # load txt file
    #[coord_pt, ikle_subt, sub_infot,  x, y, sub] = load_sub_txt(filetxt, path,)
    #fig_substrate(coord_pt, ikle_subt, sub_infot, path, x, y, sub)


    # test merge grid
    path1 = r'D:\Diane_work\dummy_folder\DefaultProj'
    hdf5_name_hyd = os.path.join(path1, r'Hydro_RUBAR2D_BS15a607_02_2017_at_15_52_59.h5' )
    hdf5_name_sub = os.path.join(path1, r'Substrate_dummy_hyd_shp06_03_2017_at_11_27_59.h5')
    [ikle_both, point_all_both, sub_data1, subdata2,  vel, height] = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, -1)
    fig_merge_grid(point_all_both[0], ikle_both[0], path1)
    plt.show()

    # test create dummy substrate
    # path = r'D:\Diane_work\dummy_folder\DefaultProj'
    # fileh5 = 'Hydro_RUBAR2D_BS15a607_02_2017_at_15_50_13.h5'
    # create_dummy_substrate_from_hydro(fileh5, path, 'dummy_hydro_substrate2', 'Sandre', 0)


if __name__ == '__main__':
    main()