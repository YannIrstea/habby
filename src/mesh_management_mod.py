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
from io import StringIO
import sys
import os
from src import hdf5_mod
import time
from copy import deepcopy
import numpy as np
import triangle
import matplotlib.pyplot as plt
import shapefile


def quadrangles_to_triangles(ikle4,xy,z,h,v):
    """
    this fucntion call the quadrangles hydraulic description and transforme it into a triangular description
    a new node is added in the center of each quadrangle, and we take care for the partially wet quadrangle
    for the calculation of the depth and the velocity of theses new points.


    :param ikle4: the connectivity table of the quadrangles
    :param xy: the coordinates of the nodes
    :param z: the bottom altitude of the nodes
    :param h: the height of water of the nodes
    :param v: the mean velocity of the nodes
    :return: ikle3 the connectivity table of the triangles, and the 'coordinates' of the additional nodes xy,z,h,v multilines numpy array
    """
    #TODO verifier que len(ikle4)!=0
    #TODO verifier que les elements des noeuds ont la même longueur len(xy)=len(v)=len(z)=len(h)
    nbnodes0=len(xy)
    nbnodes= nbnodes0
    ikle3=np.empty(shape=[0, 3], dtype=int)
    # transforming v<0 in abs(v) ; hw<0 in hw=0 and where hw=0 v=0
    v=np.abs(v)
    hwneg = np.where(h < 0)
    h[hwneg] = 0
    hwnul = np.where(h == 0)
    v[hwnul] = 0
    #essential for return value data in multiple lines
    if z.ndim==1:
        z = z.reshape(np.size(z),1)
    if h.ndim==1:
        h = h.reshape(np.size(h),1)
    if v.ndim==1:
        v = v.reshape(np.size(v),1)

    for i in range(len(ikle4)):
        nbnodes += 1
        q0,q1,q2,q3=ikle4[i][0], ikle4[i][1], ikle4[i][2], ikle4[i][3]
        ikle3 = np.append(ikle3, np.array([[q0, nbnodes - 1, q3], [q0, q1, nbnodes - 1],
                                         [q1, q2, nbnodes - 1], [nbnodes - 1, q2, q3]]),
                         axis=0)
        xyi = np.mean(xy[[q0, q1, q2, q3], :], axis=0)
        zi = np.mean(z[[q0, q1, q2, q3], :], axis=0)
        hi = np.mean(h[[q0, q1, q2, q3], :], axis=0)
        vi = np.mean(v[[q0, q1, q2, q3], :], axis=0)
        xy = np.append(xy, np.array([xyi]), axis=0)
        z = np.append(z, np.array([zi]), axis=0)
        h = np.append(h, np.array([hi]), axis=0)
        v = np.append(v, np.array([vi]), axis=0)
        # chek whether the quadrangle is partially wet
        h4 = h[[q0, q1, q2, q3]]
        bhw = (h4 > 0).astype(np.int)
        n4_type = np.sum(bhw)  # 0=dry 4=wet 1,2 or 3 = partially wet
        if n4_type != 0 and n4_type != 4:  # the quadrangle is partially wet
            hi, vi = 0, 0
            z4 = z[[q0, q1, q2, q3]]
            v4 = v[[q0, q1, q2, q3]]
            for j in range(2):  # working successively on the 2 diagonals/ edges
                za, ha, va = z4[j], h4[j], v4[j]
                zb, hb, vb = z4[j + 2], h4[j + 2], v4[j + 2]
                if ha != 0 and hb != 0:
                    hi += (ha + hb) / 2
                    vi += (va + vb) / 2
                elif ha == 0 and hb == 0:
                    pass
                else:
                    if ha == 0:  # swap A & B
                        za, ha, va, zb, hb, vb = zb, hb, vb, za, ha, va
                    # at this step hwB/hb=0
                    if za + ha >= zb or za >= zb:  # it is possible in that case that the hydraulic given is incorrect
                        hi += (ha + hb) / 2
                        vi += (va + vb) / 2
                    else:  # ha/(zb-za)<1
                        lama = ha / (zb - za)
                        if lama <= 0.5:  # the middle/center is dry
                            pass
                        else:
                            hi += ha - (zb - za) / 2
                            vi += hi * va / ha
            # affecting the mean result from the 2 diagonals/ edges
            h [nbnodes - 1]=hi/2
            v [nbnodes - 1]= vi/ 2
    return ikle3,xy[nbnodes0-nbnodes:,:],z[nbnodes0-nbnodes:],h[nbnodes0-nbnodes:],v[nbnodes0-nbnodes:]


def merge_grid_and_save(name_hdf5merge, hdf5_name_hyd, hdf5_name_sub, path_hdf5, name_prj, path_prj,
                        model_type, progress_value,
                        q=[], print_cmd=False, project_preferences=[]):
    """
    This function call the merging of the grid between the grid from the hydrological data and the substrate data.
    It then save the merged data and the substrate data in a common hdf5 file. This function is called in a second
    thread to avoid freezin gthe GUI. This is why we have this extra-function just to call save_hdf5() and
    merge_grid_hydro_sub().


    :param name_hdf5merge: the name of the hdf5 merge output
    :param hdf5_name_hyd: the name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the name of the hdf5 with the substrate data
    :param path_hdf5: the path to the hdf5 data
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: the type of the "model". In this case, it is just 'SUBSTRATE'
    :param q: used to share info with the GUI when this thread have finsihed (print_cmd = False)
    :param print_cmd: If False, print to the GUI (usually False)
    :param path_shp: the path where to save the shp file with hydro and subtrate. If empty, the shp file is not saved.
    :param: erase_id should we erase old shapefile from the same model or not.
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # progress
    progress_value.value = 10

    # merge the grid
    data_2d_merge, data_2d_whole_profile, data_description = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub,
                                                                                  path_prj, progress_value)

    if not any([data_2d_merge, data_2d_whole_profile, data_description]) and not print_cmd:
        sys.stdout = sys.__stdout__
        if q:
            q.put(mystdout)
            return

    # progress
    progress_value.value = 90

    # create hdf5 hab
    hdf5 = hdf5_mod.Hdf5Management(path_prj, name_hdf5merge)
    hdf5.create_hdf5_hab(data_2d_merge, data_2d_whole_profile, data_description, project_preferences)

    # progress
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, path_prj, progress_value):
    """
    After the data for the substrate and the hydrological data are loaded, they are still in different grids.
    This functions will merge both grid together. This is done for all time step and all reaches. If a
    constant substrate is there, the hydrological hdf5 is just copied.

    :param hdf5_name_hyd: the name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the name of the hdf5 with the substrate data
    :param path_hdf5: the path to the hdf5 data
    :param path_prj: the path to the project
    :return: the connectivity table, the coordinates, the substrated data, the velocity and height data all in a merge form.

    """
    failload = [False, False, False]

    # load hdf5 hydro
    hdf5_hydro = hdf5_mod.Hdf5Management(path_prj, hdf5_name_hyd)
    hdf5_hydro.load_hdf5_hyd(units_index="all", whole_profil=True)

    # load hdf5 sub
    hdf5_sub = hdf5_mod.Hdf5Management(path_prj, hdf5_name_sub)
    hdf5_sub.load_hdf5_sub(convert_to_coarser_dom=False)

    # merge_description
    merge_description = dict()
    # copy attributes hydraulic
    for attribute_name, attribute_value in list(hdf5_hydro.data_description.items()):
        merge_description[attribute_name] = attribute_value
    # copy attributes substrate
    for attribute_name, attribute_value in list(hdf5_sub.data_description.items()):
        merge_description[attribute_name] = attribute_value

    # data_2d_merge and data_2d_whole_merge
    data_2d_merge = dict(hdf5_hydro.data_2d)
    data_2d_whole_merge = dict(hdf5_hydro.data_2d_whole)

    # CONSTANT CASE
    if hdf5_sub.data_description["sub_mapping_method"] == "constant":  # set default value to all mesh
        merge_description["hab_epsg_code"] = merge_description["hyd_epsg_code"]
        data_2d_merge, data_2d_whole_merge = set_constant_values_to_merge_data(hdf5_hydro,
                                                                               hdf5_sub,
                                                                               data_2d_merge,
                                                                               data_2d_whole_merge)
        if not any([data_2d_merge, data_2d_whole_merge]):
            return failload

    # POLYGON AND POINTS CASES
    if hdf5_sub.data_description["sub_mapping_method"] != "constant":
        # check if EPSG are integer and if TRUE they must be equal
        epsg_hyd = hdf5_hydro.data_description["hyd_epsg_code"]
        epsg_sub = hdf5_sub.data_description["sub_epsg_code"]
        if RepresentsInt(epsg_hyd) and RepresentsInt(epsg_sub):
            if epsg_hyd == epsg_sub:
                merge_description["hab_epsg_code"] = epsg_hyd
            if epsg_hyd != epsg_sub:
                print("Error : Merging failed. EPSG codes are different between hydraulic and substrate data : " + epsg_hyd + ", " + epsg_sub)
                return failload
        if not RepresentsInt(epsg_hyd) and RepresentsInt(epsg_sub):
            print(
                "Warning : EPSG code of hydraulic data is unknown (" + epsg_hyd + ") "
                "and EPSG code of substrate data is known (" + epsg_sub + "). " +
                "The merging data will still be calculated.")
            merge_description["hab_epsg_code"] = epsg_sub
        if RepresentsInt(epsg_hyd) and not RepresentsInt(epsg_sub):
            print(
                "Warning : EPSG code of hydraulic data is known (" + epsg_hyd + ") "
                "and EPSG code of substrate data is unknown (" + epsg_sub + "). " +
                "The merging data will still be calculated.")
            merge_description["hab_epsg_code"] = epsg_hyd
        if not RepresentsInt(epsg_hyd) and not RepresentsInt(epsg_sub):
            print(
                "Warning : EPSG codes of hydraulic and substrate data are unknown : " + epsg_hyd + " ; "
               + epsg_sub + ". The merging data will still be calculated.")
            merge_description["hab_epsg_code"] = epsg_hyd

        # check if extent match
        extent_hyd = list(map(float, hdf5_hydro.data_description["hyd_extent"].split(", ")))
        extent_sub = list(map(float, hdf5_sub.data_description["sub_extent"].split(", ")))
        if (extent_hyd[2] < extent_sub[0] or extent_hyd[0] > extent_sub[2] or
                extent_hyd[3] < extent_sub[1] or extent_hyd[1] > extent_sub[3]):
            print("Warning : No intersection found between hydraulic and substrate data (from extent intersection).")
            extent_intersect = False
        else:
            extent_intersect = True

        # check if whole profile is equal for all timestep
        if not hdf5_hydro.data_description["hyd_varying_mesh"]:
            # have to check intersection for only one timestep
            pass
        else:
            # TODO : merge for all time step
            pass

        if not extent_intersect:  # set default value to all mesh
            data_2d_merge, data_2d_whole_merge = set_constant_values_to_merge_data(hdf5_hydro,
                                                                                   hdf5_sub,
                                                                                   data_2d_merge,
                                                                                   data_2d_whole_merge)
            if not any([data_2d_merge, data_2d_whole_merge]):
                return failload

        if extent_intersect:
            # defaut data
            default_data = np.array(list(map(int, hdf5_sub.data_description["sub_default_values"].split(", "))))
            """ data_2d_whole """
            data_2d_whole_merge = hdf5_hydro.data_2d_whole
            """ data_2d """
            # prog
            delta = 80 / int(hdf5_hydro.data_description["hyd_unit_number"])
            prog = progress_value.value
            warn_inter = True
            ikle_both = []
            point_all_both = []
            vel_all_both = []
            height_all_both = []
            z_all_both = []
            sub_data_all_t = []
            # for each reach
            for reach_num in range(0, int(hdf5_hydro.data_description["hyd_reach_number"])):
                sub_array_by_unit = []
                vel_by_unit = []
                height_by_unit = []
                ikle_all_by_unit = []
                point_all_by_unit = []
                point_z_all_by_unit = []
                # for each unit
                for unit_num in range(0, int(hdf5_hydro.data_description["hyd_unit_number"])):
                    first_time = False
                    point_before = np.array(hdf5_hydro.data_2d["xy"][reach_num][unit_num])
                    point_z_before = np.array(hdf5_hydro.data_2d["z"][reach_num][unit_num])
                    ikle_before = np.array(hdf5_hydro.data_2d["tin"][reach_num][unit_num])
                    vel_before = hdf5_hydro.data_2d["v"][reach_num][unit_num]
                    height_before = hdf5_hydro.data_2d["h"][reach_num][unit_num]

                    # find intersection betweeen hydrology and substrate
                    [ikle_sub, point_all_sub, data_sub, data_crossing, sub_cell] = \
                        find_sub_and_cross(hdf5_sub.data_2d["tin"][reach_num][0],
                                           hdf5_sub.data_2d["xy"][reach_num][0],
                                           hdf5_sub.data_2d["sub"][reach_num][0],
                                           hdf5_hydro.data_2d["tin"][reach_num][unit_num],
                                           hdf5_hydro.data_2d["xy"][reach_num][unit_num],
                                           progress_value, delta,
                                           first_time)

                    # if no intersection found at t==0
                    if len(data_crossing[0]) < 1:
                        if warn_inter:
                            print('Warning: No intersection between the grid and the substrate for one reach for'
                                  ' one or more time steps.\n')
                            warn_inter = False
                        try:
                            # sub_data_here = np.zeros(len(ikle_all[t][r]), ) + float(default_data)
                            sub_data_here = default_data
                        except ValueError:
                            print('Error: no float in substrate. (only float accepted for now).\n')
                            return failload
                        sub_array_by_unit.append(sub_data_here)
                        vel_by_unit.append(vel_before)
                        height_by_unit.append(height_before)
                        ikle_all_by_unit.append(ikle_before)
                        point_all_by_unit.append(point_before)
                        point_z_all_by_unit.append(point_z_before)

                    else:

                        # create the new grid based on intersection found
                        [ikle_here, point_all_here, new_data_sub, vel_new, height_new, z_values_new] = \
                            create_merge_grid(ikle_before,
                                              point_before,
                                              data_sub,
                                              vel_before,
                                              height_before,
                                              point_z_before,
                                              ikle_sub,
                                              default_data,
                                              data_crossing,
                                              sub_cell)

                        # check that each triangle of the grid is clock-wise (useful for shapefile)
                        ikle_here = check_clockwise(ikle_here, point_all_here)

                        # print('TIME NEW GRID')
                        # print(c - b)
                        sub_array_by_unit.append(new_data_sub)
                        vel_by_unit.append(vel_new)
                        height_by_unit.append(height_new)
                        point_z_all_by_unit.append(z_values_new)
                        ikle_all_by_unit.append(np.array(ikle_here))
                        point_all_by_unit.append(np.array(point_all_here))

                ikle_both.append(ikle_all_by_unit)
                point_all_both.append(point_all_by_unit)
                sub_data_all_t.append(sub_array_by_unit)
                vel_all_both.append(vel_by_unit)
                height_all_both.append(height_by_unit)
                z_all_both.append(point_z_all_by_unit)
                # progress
                prog += delta
                progress_value.value = int(prog)

            # add sub data to dict
            data_2d_merge["tin"] = ikle_both
            data_2d_merge["xy"] = point_all_both
            data_2d_merge["sub"] = sub_data_all_t
            data_2d_merge["v"] = vel_all_both
            data_2d_merge["h"] = height_all_both
            data_2d_merge["z"] = z_all_both

    return data_2d_merge, data_2d_whole_merge, merge_description


def find_sub_and_cross(ikle_sub, coord_p_sub, data_sub, ikle, coord_p, progress_value, delta, first_time=False):
    """
    A function which find where the crossing points are. Crossing points are the points on the triangular side of the
    hydrological grid which cross with a side of the substrate grid. The algo based on finding if points of one elements
    are in the same polygon using a ray casting method. We assume that the polygon forming the subtrate grid are convex.
    Otherwise it would not work in all cases.
    We also neglect the case where a substrate cell at the border of the subtrate grid is fully in a hydrological cell.

    IMPORTANT: polygon should be convex.

    :param ikle_sub: the connectivity table for the substrate
    :param coord_p_sub: the coordinates of the poitn forming the subtrate
    :param data_sub: the subtrate data by subtrate cell
    :param ikle: the connectivity table for the hydrology
    :param coord_p: the coordinate of the hydrology
    :param first_time: If True, we preapre the subtrate data
    :return: the new substrate grid (ikle_sub, coord_p_sub, data_sub, sub_cell), the data for
             the crossing point (hydrological element with a crossing, crossing point, substrate element linked with
             the crossing point, point of substrate inside, substrate element linked with the substrate point,
             side of the crossing points, substrate leemnt link with hydro_point).

    """

    # preparation
    ikle_sub = np.array(ikle_sub)
    ikle = np.array(ikle)
    sub_cell = np.zeros((len(ikle),)) - 99  # the link between substrate cell and hydro cell
    el_cross = []
    hydro_el = []
    sub_point_in_cross = []
    sub_point_in_el = []
    point_cross = []
    side_point_cross = []
    point_cross_el = []

    if first_time:

        # get triangle substrate grid substrate grid (finally it is easier, even if part of merge grid function with
        # a polygon convex substrate)
        xy_new = list(coord_p_sub)
        ikle_new = []
        data_sub_new = []
        for idc, c in enumerate(ikle_sub):
            ikle_new.append(c)
            data_sub_new.append(data_sub[idc])

        coord_p_sub = np.array(xy_new)
        ikle_sub = ikle_new
        data_sub = list(data_sub_new)

        # erase substrate cell which are outside of the hydrological grid (to optimize)
        # the full time is the bigger grid
        data_sub2 = []
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
                data_sub2.append(data_sub[i])
            i += 1
        ikle_sub = np.array(ikle_sub2)
        if len(ikle_sub) < 1:
            return ikle_sub, coord_p_sub, data_sub, [[]], sub_cell

        data_sub = np.copy(data_sub2)

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
    data_sub = data_sub[indmin]

    # progress
    prog = progress_value.value
    delta2 = delta / nb_tri
    if nb_tri == 1:
        delta2 = delta / 2

    # for each hydrological cell
    for e in range(0, nb_tri):
        # progress
        prog += delta2
        progress_value.value = int(prog)
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
                if i < nb_poly - 4:
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
                if j == nb_poly + 3:
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
                w2 = w + 1
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
                        for seg in range(0, len(a1)):  # test all substrate side
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
                                # break

                    # check if intersection identical
                    if len(point_cross_here) >= 2:
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

                # in case there is a substrate cell in the hydro cells (slow)
                # we might miss case where a border substrate cell is in an hydro cell
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
    return ikle_sub, coord_p_sub, data_sub, data_crossing, sub_cell


def set_constant_values_to_merge_data(hdf5_hydro, hdf5_sub, data_2d_merge, data_2d_whole_merge):
    # for each reach
    sub_array_by_reach = []
    for reach_num in range(0, int(hdf5_hydro.data_description["hyd_reach_number"])):
        # for each unit
        sub_array_by_unit = []
        for unit_num in range(0, int(hdf5_hydro.data_description["hyd_unit_number"])):
            try:
                default_data = np.array(list(map(int, hdf5_sub.data_description["sub_default_values"].split(", "))))
                sub_array = np.repeat([default_data], len(data_2d_merge["tin"][reach_num][unit_num]), 0)
            except ValueError or TypeError:
                print('Error: Merging failed. No numerical data in substrate. (only float or int accepted for now). \n')
                return False, False
            sub_array_by_unit.append(sub_array)
        sub_array_by_reach.append(sub_array_by_unit)
    # add sub data to dict
    data_2d_merge["sub"] = sub_array_by_reach
    data_2d_whole_merge["sub"] = sub_array_by_reach
    return data_2d_merge, data_2d_whole_merge


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

    area = 0.5 * (-p1y * p2x + p0y * (-p1x + p2x) + p0x * (p1y - p2y) + p1x * p2y)
    if area != 0:
        s = 1 / (2 * area) * (p0y * p2x - p0x * p2y + (p2y - p0y) * pt[0] + (p0x - p2x) * pt[1])
        t = 1 / (2 * area) * (p0x * p1y - p0y * p1x + (p0y - p1y) * pt[0] + (p1x - p0x) * pt[1])
    else:
        return False

    if s >= 0 and t >= 0 and 1 - s - t >= 0:
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

    [sx, sy] = [hyd2[0] - hyd1[0], hyd2[1] - hyd1[1]]
    [rx, ry] = [sub2[0] - sub1[0], sub2[1] - sub1[1]]
    rxs = rx * sy - ry * sx
    term2 = (hyd1[0] - sub1[0]) * ry - rx * (hyd1[1] - sub1[1])
    xcross = None
    ycross = None

    if rxs == 0 and term2 == 0:
        print('collinear points')
    if rxs != 0:
        u = term2 / rxs
        t = ((hyd1[0] - sub1[0]) * sy - sx * (hyd1[1] - sub1[1])) / rxs
        if 0.0 - wig <= t <= 1.0 + wig and 0.0 - wig <= u <= 1.0 + wig:
            xcross = hyd1[0] + u * sx
            ycross = hyd1[1] + u * sy
    else:
        pass
        #print('rxs == 0')
    return [xcross, ycross]


def create_merge_grid(ikle, coord_p, data_sub, vel, height, point_z, ikle_sub,
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
    z_values = list(point_z)
    el_cross = data_crossing[0]
    point_cross_el = data_crossing[1]
    point_cross = np.array(data_crossing[2])
    side_point_cross = data_crossing[3]
    sub_point_in_cross = data_crossing[4]
    sub_point_in_el = data_crossing[5]
    hydro_el = data_crossing[6]
    to_delete = []
    empty_one = True
    empty_two = True

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

            # new intersection point (we have two identical point)
            pc1 = [pc_here[0][0], pc_here[0][1]]
            pc2 = [pc_here[2][0], pc_here[2][1]]
            coord_p.append(pc2)  # order matters
            coord_p.append(pc1)

            # get the new height and velocity data
            if len(vel) > 0:  # not used by t=0, for the grid representing the whole profile
                point_old = [coord_p[ikle[e][0]], coord_p[ikle[e][1]], coord_p[ikle[e][2]]]

                vel_here = [vel[ikle[e][0]], vel[ikle[e][1]], vel[ikle[e][2]]]
                h_here = [height[ikle[e][0]], height[ikle[e][1]], height[ikle[e][2]]]
                z_here = [z_values[ikle[e][0]], z_values[ikle[e][1]], z_values[ikle[e][2]]]

                vel_new1 = finit_element_interpolation(pc1, point_old, vel_here)
                vel_new2 = finit_element_interpolation(pc2, point_old, vel_here)
                vel.append(vel_new2)
                vel.append(vel_new1)

                h_new1 = finit_element_interpolation(pc1, point_old, h_here)
                h_new2 = finit_element_interpolation(pc2, point_old, h_here)
                height.append(h_new2)
                height.append(h_new1)

                z_new1 = finit_element_interpolation(pc1, point_old, z_here)
                z_new2 = finit_element_interpolation(pc2, point_old, z_here)
                z_values.append(z_new2)
                z_values.append(z_new1)

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
                    if len(point_new) > 2:
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
                                h_here = [height[ikle[e][0]], height[ikle[e][1]], height[ikle[e][2]]]
                                z_here = [z_values[ikle[e][0]], z_values[ikle[e][1]], z_values[ikle[e][2]]]
                                for i in point_new:
                                    vel_new1 = finit_element_interpolation(i, point_old, vel_here)
                                    vel.append(vel_new1)
                                    h_new1 = finit_element_interpolation(i, point_old, h_here)
                                    height.append(h_new1)
                                    z_new1 = finit_element_interpolation(i, point_old, z_here)
                                    z_values.append(z_new1)

                        except KeyError:
                            # in case triangulation was not ok
                            if empty_one:
                                print('Warning: one or more empty triangle was found by merge grid (1) \n')
                                empty_one = False
                            # print(point_new)
                            # print(hydroe)
                            # print(hyd_all)
                            # print(pce)
                            # print(pc_here)

                    else:
                        if empty_two:
                            print('Warning: one or more empty triangle was found by merge grid (2) \n')
                            empty_two = False

    # create the new substrate data
    #print('create the new substrate data')
    data_sub_ok = np.zeros((len(sub_cell), len(default_data)))
    for i, s in enumerate(sub_cell):
        #print(i, s)
        if s == -99 or s == -1:
            data_sub_ok[i] = default_data

        else:
            data_sub_ok[i] = data_sub[int(s)]

    # remove element from ikle and new_data_sub
    for d in reversed(to_delete):  # to_delete is ordered
        del ikle[d]

    data_sub_ok = np.delete(data_sub_ok, to_delete, axis=0)

    return ikle, coord_p, data_sub_ok, vel, height, z_values


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


def finit_element_interpolation(newp, point_old, data_old):
    """
    This function gets the height and velcoity data for a new point in or on the side of an element. It does an
    average of the data (velocity or height) given at the node of the original (old) elements. This average is weighted
    as a function of the distance of the point.

    :param newp: the coordinates of the new points
    :param point_old: the coordinates of thre three old points (would work with more than three)
    :param data_old: the data for the point in point_old
    :return: the new data
    """
    # point known
    x1 = point_old[0][0]
    x2 = point_old[1][0]
    x3 = point_old[2][0]

    y1 = point_old[0][1]
    y2 = point_old[1][1]
    y3 = point_old[2][1]

    va1 = data_old[0]
    va2 = data_old[1]
    va3 = data_old[2]

    # point new
    xm = newp[0]
    ym = newp[1]
    valm = va1  # force to have coherent value (if divide by 0)

    if ((x2 - x3) * (y2 - y1)) - ((x2 - x1) * (y2 - y3)) == 0:
        print("divide by zero, not a triangle ?")
        #export_one_mesh_and_new_point(x1, y1, va1, x2, y2, va2, x3, y3, va3, xm, ym, valm)
    else:
        # formula Yann Lecoarer
        valm = va1 + ((xm - x1) * ((y2 - y1) * (va2 - va3) - (y2 - y3) * (va2 - va1)) + (ym - y1) * (
                    (x2 - x3) * (va2 - va1) - (x2 - x1) * (va2 - va3))) / (
                           (x2 - x3) * (y2 - y1) - (x2 - x1) * (y2 - y3))

    return valm


def export_one_mesh_and_new_point(x1, y1, val1, x2, y2, val2, x3, y3, val3, xm, ym, valm):
    # export triangle
    fileOUT = os.path.join(r"C:\Users\quentin.royer\Documents\TAF\PROJETS_HABBY\Test_QR\DefaultProj", "test.shp")
    w = shapefile.Writer(shapefile.POINTZ)
    w.field('x', 'F', 10, 10)
    w.field('y', 'F', 10, 10)
    w.field('z', 'F', 10, 10)
    w.point(x1, y1, val1, shapeType=11)
    w.point(x2, y2, val2, shapeType=11)
    w.point(x3, y3, val3, shapeType=11)
    w.point(xm, ym, valm)
    w.record(*[x1, y1, val1])
    w.record(*[x2, y2, val2])
    w.record(*[x3, y3, val3])
    w.record(*[xm, ym, valm])
    w.save(fileOUT)


def check_clockwise(ikle, point):
    """
    This function check that each grid cell is given in a clockwise order. This is useful because we might create
    shapefile afterward. ArcMap beleives that we have hole if a grid cell is in counter-clockwise order.

    To check the clockwise order, we sum (x2-x1)*(y2+y1) over the three edges.
    Here is a more information on the algo: http://blog.element84.com/polygon-winding.html

    :param ikle: the connectivity table
    :param point: the grid point
    :return: the connectivity table with the point in clockewise order
    """

    ikle = np.array(ikle)
    point = np.array(point)

    point1 = point[ikle[:, 0]]
    point2 = point[ikle[:, 1]]
    point3 = point[ikle[:, 2]]

    sum_edge = (point2[:, 0] - point1[:, 0]) * (point2[:, 1] + point1[:, 1])
    sum_edge += (point3[:, 0] - point2[:, 0]) * (point3[:, 1] + point2[:, 1])
    sum_edge += (point1[:, 0] - point3[:, 0]) * (point1[:, 1] + point3[:, 1])
    ikle_old0 = deepcopy(ikle[:, 0])

    ikle[sum_edge < 0, 0] = ikle[sum_edge < 0, 2]
    ikle[sum_edge < 0, 2] = ikle_old0[sum_edge < 0]

    return ikle


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
        # plt.plot(coord_p[:, 0], coord_p[:, 1], '*r')
    # for test, remove otherwise
    # point_all_sub = np.array([[0.4, 0.45], [0.48, 0.45], [0.32, 0.35]])
    # plt.plot(point_all_sub[:, 0], point_all_sub[:, 1], '*r')
    plt.title('Computational grid, updated for substrate data')
    plt.xlabel('x coordinate')
    plt.ylabel('y coordinate')
    # plt.show()
    plt.savefig(os.path.join(path_im, "Grid_merge_" + name_add + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                dpi=1000)
    plt.savefig(os.path.join(path_im, "Grid_merge_" + name_add + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                dpi=1000)


def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def main():
    """
    Used to test this module.
    """

    path = r'D:\Diane_work\output_hydro\substrate'

    # test create shape
    # filename = 'mytest.shp'
    # filetxt = 'sub_txt2.txt'
    # # load shp file
    # [coord_p, ikle_sub, sub_info] = load_sub_shp(filename, path, 'VELOCITY')
    # fig_substrate(coord_p, ikle_sub, sub_info, path)
    # # load txt file
    # [coord_pt, ikle_subt, sub_infot,  x, y, sub] = load_sub_txt(filetxt, path,)
    # fig_substrate(coord_pt, ikle_subt, sub_infot, path, x, y, sub)

    # test merge grid
    path1 = r'D:\Diane_work\dummy_folder\DefaultProj'
    hdf5_name_hyd = os.path.join(path1, r'Hydro_RUBAR2D_BS15a607_02_2017_at_15_52_59.hab')
    hdf5_name_sub = os.path.join(path1, r'Substrate_dummy_hyd_shp06_03_2017_at_11_27_59.hab')
    [ikle_both, point_all_both, sub_data1, subdata2, vel, height] = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub,
                                                                                         -1)
    fig_merge_grid(point_all_both[0], ikle_both[0], path1)
    plt.show()

    # test create dummy substrate
    # path = r'D:\Diane_work\dummy_folder\DefaultProj'
    # fileh5 = 'Hydro_RUBAR2D_BS15a607_02_2017_at_15_50_13.hab'
    # create_dummy_substrate_from_hydro(fileh5, path, 'dummy_hydro_substrate2', 'Sandre', 0)


if __name__ == '__main__':
    main()
