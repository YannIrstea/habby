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
import numpy.lib.recfunctions
import os.path
import time


def hydrosignature_calculation_alt(delta_mesh, progress_value, classhv, hyd_tin, hyd_xy_node, hyd_hv_node,
                                   hyd_data_node=None, hyd_data_mesh=None,
                                   i_whole_profile=None, return_cut_mesh=False):
    """
    Alternative version of hydrosignature_calculation, made to test variations to change function output and remove duplicates
    :param classhv: list containing 2 lists, one with h class limits and the other with v class limits
    :param hyd_tin: (m,3) int array containing the indices of each vertex in each mesh triangle
    :param hyd_xy_node: (n,2) array containing the position of each node
    :param hyd_hv_node: (n,2) array containing respectively depth and velocity in each node
    :param hyd_data_node: structured (n,) array, consisting of a list of np.record tuples, and a dtype attribute containing (fieldname,datatype) tuples for each variable
    :param hyd_data_mesh: structured (m,) array of np.record tuples and a dtype attribute containing (fieldname,datatype) for each variable
    :param return_cut_mesh: boolean indicating whether to return the new mesh created for HS calculation (if True, original data will be interpolated for the new nodes)

    """

    g = 9.80665  # value of gravitational acceleration on Earth [m**2/s] #
    uncertainty = 0.01  # a checking parameter for the algorithm
    translationxy = np.min(hyd_xy_node,
                           axis=0)  # offsets coordinates so that absolute values will be smaller, to reduce numerical errors
    hyd_xy_node -= translationxy

    # calculating the global hydraulic part of the hydrosignature
    # aire_totale	volume_total	hauteur_moyenne	vitesse_moyenne	Froude_moyen	hauteur_min	hauteur_max	vitesse_min	vitesse_max
    # calculating triangle area by vector product
    narea = 0.5 * (np.abs(
        (hyd_xy_node[hyd_tin[:, 1]][:, 0] - hyd_xy_node[hyd_tin[:, 0]][:, 0]) * (
                hyd_xy_node[hyd_tin[:, 2]][:, 1] - hyd_xy_node[hyd_tin[:, 0]][:, 1]) - (
                hyd_xy_node[hyd_tin[:, 2]][:, 0] - hyd_xy_node[hyd_tin[:, 0]][:, 0]) * (
                hyd_xy_node[hyd_tin[:, 1]][:, 1] - hyd_xy_node[hyd_tin[:, 0]][:, 1])))

    nhmean = (hyd_hv_node[hyd_tin[:, 0]][:, 0] + hyd_hv_node[hyd_tin[:, 1]][:, 0] + hyd_hv_node[hyd_tin[:, 2]][:,
                                                                                    0]) / 3
    nvolume = narea * nhmean
    nvmean = (hyd_hv_node[hyd_tin[:, 0]][:, 1] + hyd_hv_node[hyd_tin[:, 1]][:, 1] + hyd_hv_node[hyd_tin[:, 2]][:,
                                                                                    1]) / 3
    # nfroudemean=np.abs(nvmean)/np.sqrt(np.abs(nhmean)*g)
    with np.errstate(invalid='ignore'):
        f0 = np.abs(hyd_hv_node[hyd_tin[:, 0]][:, 1]) / np.sqrt(np.abs(hyd_hv_node[hyd_tin[:, 0]][:, 0]) * g)
        f1 = np.abs(hyd_hv_node[hyd_tin[:, 1]][:, 1]) / np.sqrt(np.abs(hyd_hv_node[hyd_tin[:, 1]][:, 0]) * g)
        f2 = np.abs(hyd_hv_node[hyd_tin[:, 2]][:, 1]) / np.sqrt(np.abs(hyd_hv_node[hyd_tin[:, 2]][:, 0]) * g)
    f0[np.isnan(f0)] = 0
    f1[np.isnan(f1)] = 0
    f2[np.isnan(f2)] = 0
    nfroudemean = np.mean((f0, f1, f2))

    total_area = np.sum(narea)
    total_volume = np.sum(nvolume)
    mean_depth = total_volume / total_area
    mean_velocity = np.sum(nvolume * np.abs(nvmean)) / total_volume
    mean_froude = np.sum(nvolume * np.abs(nfroudemean)) / total_volume
    nhused = np.hstack(
        (hyd_hv_node[hyd_tin[:, 0]][:, 0], hyd_hv_node[hyd_tin[:, 1]][:, 0], hyd_hv_node[hyd_tin[:, 2]][:, 0]))
    nvused = np.hstack(
        (hyd_hv_node[hyd_tin[:, 0]][:, 1], hyd_hv_node[hyd_tin[:, 1]][:, 1], hyd_hv_node[hyd_tin[:, 2]][:, 1]))
    min_depth = np.min(nhused)  # np.min(hyd_hv_node[:, 0]) not used because some node cannot be called by the tin
    max_depth = np.max(nhused)
    min_velocity = np.min(nvused)
    max_velocity = np.max(nvused)

    cl_h = classhv[0]
    cl_v = classhv[1]
    nb_cl_h = len(cl_h) - 1
    nb_cl_v = len(cl_v) - 1

    areameso = np.zeros((nb_cl_h, nb_cl_v), dtype=np.float64)
    volumemeso = np.zeros((nb_cl_h, nb_cl_v), dtype=np.float64)
    nb_mesh = 0

    ## storing node data and triangles of the newer mesh
    new_xy = []
    new_hv = []
    new_tin = []
    hydro_classes = []
    null_area_list = []
    original_triangle = []  # the index of the triangle each new node originally belonged to
    # original_node = [] #the index of each node in the original hyd_xy_node list. Is -1 if node is a new node
    enclosing_triangle = []  # the original index of the triangle which encloses each smaller triangle in the new mesh
    iscut = np.zeros(len(hyd_tin), dtype=bool)  # whether each original triangle has been cut by this function
    for i in range(hyd_tin.size // 3):  # even if one single triangle for hyd_tin
        # xyo, xya, xyb = hyd_xy_node[hyd_tin[i][0]], hyd_xy_node[hyd_tin[i][1]], hyd_xy_node[hyd_tin[i][2]]
        # axy, bxy = xya - xyo, xyb - xyo
        # deta = bxy[1] * axy[0] - bxy[0] * axy[1]

        if narea[i] == 0:
            null_area_list.append(str(i))
        else:
            nb_mesh += 1
            poly1 = {'x': [hyd_xy_node[hyd_tin[i][0]][0], hyd_xy_node[hyd_tin[i][1]][0], hyd_xy_node[hyd_tin[i][2]][0]],
                     'y': [hyd_xy_node[hyd_tin[i][0]][1], hyd_xy_node[hyd_tin[i][1]][1], hyd_xy_node[hyd_tin[i][2]][1]],
                     'h': [hyd_hv_node[hyd_tin[i][0]][0], hyd_hv_node[hyd_tin[i][1]][0], hyd_hv_node[hyd_tin[i][2]][0]],
                     'v': [hyd_hv_node[hyd_tin[i][0]][1], hyd_hv_node[hyd_tin[i][1]][1], hyd_hv_node[hyd_tin[i][2]][1]]}

            area1, volume1 = areavolumepoly(poly1, 0, 1, 2)
            area12, volume12 = 0, 0
            for j2 in range(nb_cl_h):
                if not (poly1['h'][0] == cl_h[j2 + 1] and poly1['h'][1] == cl_h[j2 + 1] and poly1['h'][2] == cl_h[
                    j2 + 1] and j2 + 1 != nb_cl_h):
                    poly2 = {'x': [], 'y': [], 'h': [], 'v': []}
                    ia, ib, nbeltpoly2 = 0, 1, 0
                    while ia <= 2:
                        if np.sign(poly1['h'][ia] - cl_h[j2]) * np.sign(poly1['h'][ia] - cl_h[j2 + 1]) != 1:
                            nbeltpoly2 += 1
                            poly2['x'].append(poly1['x'][ia])
                            poly2['y'].append(poly1['y'][ia])
                            poly2['h'].append(poly1['h'][ia])
                            poly2['v'].append(poly1['v'][ia])
                        if np.sign(cl_h[j2] - poly1['h'][ia]) * np.sign(cl_h[j2] - poly1['h'][ib]) == -1:
                            nbeltpoly2 += 1
                            iscut[i] = True
                            poly2['x'].append(
                                interpol0(cl_h[j2], poly1['h'][ia], poly1['x'][ia], poly1['h'][ib], poly1['x'][ib]))
                            poly2['y'].append(
                                interpol0(cl_h[j2], poly1['h'][ia], poly1['y'][ia], poly1['h'][ib], poly1['y'][ib]))
                            poly2['h'].append(cl_h[j2])
                            poly2['v'].append(
                                interpol0(cl_h[j2], poly1['h'][ia], poly1['v'][ia], poly1['h'][ib], poly1['v'][ib]))

                        if np.sign(cl_h[j2 + 1] - poly1['h'][ia]) * np.sign(cl_h[j2 + 1] - poly1['h'][ib]) == -1:
                            nbeltpoly2 += 1
                            iscut[i] = True
                            poly2['x'].append(
                                interpol0(cl_h[j2 + 1], poly1['h'][ia], poly1['x'][ia], poly1['h'][ib], poly1['x'][ib]))
                            poly2['y'].append(
                                interpol0(cl_h[j2 + 1], poly1['h'][ia], poly1['y'][ia], poly1['h'][ib], poly1['y'][ib]))
                            poly2['h'].append(cl_h[j2 + 1])
                            poly2['v'].append(
                                interpol0(cl_h[j2 + 1], poly1['h'][ia], poly1['v'][ia], poly1['h'][ib], poly1['v'][ib]))
                            if poly1['h'][ib] < poly1['h'][ia] and np.sign(cl_h[j2] - poly1['h'][ia]) * np.sign(
                                    cl_h[j2] - poly1['h'][ib]) == -1:
                                poly2['x'][nbeltpoly2 - 2], poly2['x'][nbeltpoly2 - 1] = poly2['x'][nbeltpoly2 - 1], \
                                                                                         poly2['x'][nbeltpoly2 - 2]
                                poly2['y'][nbeltpoly2 - 2], poly2['y'][nbeltpoly2 - 1] = poly2['y'][nbeltpoly2 - 1], \
                                                                                         poly2['y'][nbeltpoly2 - 2]
                                poly2['h'][nbeltpoly2 - 2], poly2['h'][nbeltpoly2 - 1] = poly2['h'][nbeltpoly2 - 1], \
                                                                                         poly2['h'][nbeltpoly2 - 2]
                                poly2['v'][nbeltpoly2 - 2], poly2['v'][nbeltpoly2 - 1] = poly2['v'][nbeltpoly2 - 1], \
                                                                                         poly2['v'][nbeltpoly2 - 2]
                        ia += 1;
                        ib += 1
                        if ib == 3:
                            ib = 0
                    if nbeltpoly2 > 5:
                        print(
                            "Warning: hydrosignature polygonation contrary to the YLC theory while in phase poly2 MAJOR BUG !!!")
                        return
                    elif nbeltpoly2 >= 3:

                        for k2 in range(1, nbeltpoly2 - 1):
                            area2, volume2 = areavolumepoly(poly2, 0, k2, k2 + 1)
                            area12 += area2
                            volume12 += volume2
                            area23, volume23 = 0, 0
                            for j3 in range(nb_cl_v):
                                if not (poly2['v'][0] == cl_v[j3 + 1] and poly2['v'][k2] == cl_v[j3 + 1] and poly2['v'][
                                    k2 + 1] == cl_v[j3 + 1] and j3 + 1 != nb_cl_v):
                                    poly3 = {'x': [], 'y': [], 'h': [], 'v': []}
                                    ic, id, nbeltpoly3 = 0, k2, 0
                                    while ic <= k2 + 1:
                                        if np.sign(poly2['v'][ic] - cl_v[j3]) * np.sign(
                                                poly2['v'][ic] - cl_v[j3 + 1]) != 1:
                                            nbeltpoly3 += 1
                                            poly3['x'].append(poly2['x'][ic]);
                                            poly3['y'].append(poly2['y'][ic])
                                            poly3['h'].append(poly2['h'][ic]);
                                            poly3['v'].append(poly2['v'][ic])
                                        if np.sign(cl_v[j3] - poly2['v'][ic]) * np.sign(
                                                cl_v[j3] - poly2['v'][id]) == -1:
                                            nbeltpoly3 += 1
                                            iscut[i] = True
                                            poly3['x'].append(
                                                interpol0(cl_v[j3], poly2['v'][ic], poly2['x'][ic], poly2['v'][id],
                                                          poly2['x'][id]))
                                            poly3['y'].append(
                                                interpol0(cl_v[j3], poly2['v'][ic], poly2['y'][ic], poly2['v'][id],
                                                          poly2['y'][id]))
                                            poly3['v'].append(cl_v[j3])
                                            poly3['h'].append(
                                                interpol0(cl_v[j3], poly2['v'][ic], poly2['h'][ic], poly2['v'][id],
                                                          poly2['h'][id]))
                                        if np.sign(cl_v[j3 + 1] - poly2['v'][ic]) * np.sign(
                                                cl_v[j3 + 1] - poly2['v'][id]) == -1:
                                            nbeltpoly3 += 1
                                            iscut[i] = True
                                            poly3['x'].append(
                                                interpol0(cl_v[j3 + 1], poly2['v'][ic], poly2['x'][ic], poly2['v'][id],
                                                          poly2['x'][id]))
                                            poly3['y'].append(
                                                interpol0(cl_v[j3 + 1], poly2['v'][ic], poly2['y'][ic], poly2['v'][id],
                                                          poly2['y'][id]))
                                            poly3['v'].append(cl_v[j3 + 1])
                                            poly3['h'].append(
                                                interpol0(cl_v[j3 + 1], poly2['v'][ic], poly2['h'][ic], poly2['v'][id],
                                                          poly2['h'][id]))
                                            if poly2['v'][id] < poly2['v'][ic] and np.sign(
                                                    cl_v[j3] - poly2['v'][ic]) * np.sign(
                                                cl_v[j3] - poly2['v'][id]) == -1:
                                                poly3['x'][nbeltpoly3 - 2], poly3['x'][nbeltpoly3 - 1] = poly3['x'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['x'][
                                                                                                             nbeltpoly3 - 2]
                                                poly3['y'][nbeltpoly3 - 2], poly3['y'][nbeltpoly3 - 1] = poly3['y'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['y'][
                                                                                                             nbeltpoly3 - 2]
                                                poly3['h'][nbeltpoly3 - 2], poly3['h'][nbeltpoly3 - 1] = poly3['h'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['h'][
                                                                                                             nbeltpoly3 - 2]
                                                poly3['v'][nbeltpoly3 - 2], poly3['v'][nbeltpoly3 - 1] = poly3['v'][
                                                                                                             nbeltpoly3 - 1], \
                                                                                                         poly3['v'][
                                                                                                             nbeltpoly3 - 2]
                                        if ic == 0:
                                            ic = k2
                                        else:
                                            ic += 1
                                        if id == k2:
                                            id = k2 + 1
                                        elif id == k2 + 1:
                                            id = 0
                                    if nbeltpoly3 > 5:
                                        print(
                                            "Warning: hydrosignature polygonation contrary to the YLC theory while in phase poly3 MAJOR BUG !!!")
                                        return
                                    elif nbeltpoly3 >= 3:
                                        node_indices = []  # the index each node in the present polygon has in the new list of nodes (hyd_xyhv)
                                        new_point_data = []  # x, y, h, v in each node of the present polygon
                                        # hyd_xyhv.append(poly3["x"][0], poly3)
                                        for index in range(0, nbeltpoly3):
                                            new_point_data.append(
                                                [poly3["x"][index], poly3["y"][index], poly3["h"][index],
                                                 poly3["v"][index]])

                                            # new_point_array=np.array([])

                                            if return_cut_mesh:
                                                if new_point_data[index][0:2] in new_xy:
                                                    node_indices.append(new_xy.index(new_point_data[index][0:2]))
                                                else:
                                                    new_xy.append(new_point_data[index][0:2])
                                                    new_hv.append(new_point_data[index][2:4])
                                                    original_triangle.append(i)
                                                    node_indices.append(len(new_xy) - 1)

                                        for k3 in range(1, nbeltpoly3 - 1):
                                            area3, volume3 = areavolumepoly(poly3, 0, k3, k3 + 1)
                                            areameso[j2][j3] += area3
                                            area23 += area3
                                            volumemeso[j2][j3] += volume3
                                            volume23 += volume3
                                            if return_cut_mesh:
                                                new_tin.append(
                                                    [node_indices[0], node_indices[k3], node_indices[k3 + 1]])
                                                hydro_classes.append(
                                                    index_to_class_number((nb_cl_h, nb_cl_v), (j2, j3)))
                                                enclosing_triangle.append(i)

                        # checking the partitioning poly3 checking area volume nothing lost by the algorithm

                        if area2 != 0:
                            if np.abs(area23 - area2) / area2 > uncertainty and area2 > uncertainty:
                                print(
                                    'Warning: Uncertainty allowed on the area calculation, exceeded while in phase poly3 BUG ???')
                        if volume2 != 0:
                            if np.abs(volume23 - volume2) / volume2 > uncertainty and volume2 > uncertainty:
                                print(
                                    'Warning: Uncertainty allowed on the volume calculation, exceeded while in phase poly3 BUG ???')
        # checking the partitioning poly2 checking area volume nothing lost by the algorithm
        if area1 != 0:
            if np.abs(area12 - area1) / area1 > uncertainty and area1 > uncertainty:
                print('Warning: Uncertainty allowed on the area calculation, exceeded while in phase poly2 BUG ???')
        if volume1 != 0:
            if np.abs(volume12 - volume1) / volume1 > uncertainty and volume1 > uncertainty:
                print('Warning: Uncertainty allowed on the volume calculation, exceeded while in phase poly2 BUG ???')

        # progress
        progress_value.value = progress_value.value + delta_mesh

    if null_area_list:
        print('Warning: Before hs hydraulic triangle have an null area : ' + ", ".join(null_area_list) + ".")

    # calculating percentages
    hsarea = 100 * areameso / np.sum(areameso)
    hsvolume = 100 * volumemeso / np.sum(volumemeso)



    if return_cut_mesh:
        new_xy = np.array(new_xy).astype(np.float64)
        new_hv = np.array(new_hv).astype(np.float64)
        original_triangle = np.array(original_triangle).astype(np.int64)
        enclosing_triangle = np.array(enclosing_triangle).astype(np.int64)
        new_tin = np.array(new_tin).astype(np.int64)
        hydro_classes = np.array(hydro_classes).astype(np.int64)

        ##making sure every point is unique, as numerical errors can make it not so
        new_xy_unique, indices, inverse_indices, counts = np.unique(new_xy, axis=0, return_index=True,
                                                                    return_inverse=True,
                                                                    return_counts=True)
        original_triangle_unique = original_triangle[indices]
        new_hv_unique = new_hv[indices]
        new_tin_unique, tin_indices, tin_reverse_indices, tin_counts = np.unique(inverse_indices[new_tin], axis=0,
                                                                                 return_index=True, return_inverse=True,
                                                                                 return_counts=True)
        tin_out = new_tin_unique
        hydro_classes_unique = hydro_classes[tin_indices]
        enclosing_triangle_unique = enclosing_triangle[tin_indices]
        iscut_newmesh = iscut[enclosing_triangle_unique]

        if not hyd_data_node is None:
            node_data_out = np.zeros(new_xy_unique.shape[0], dtype=hyd_data_node.dtype)
            for varname in hyd_data_node.dtype.names:
                original_values = hyd_data_node[varname]
                if varname=='h' or varname=='v':
                    k7=0 if varname=='h' else 1
                    node_data_out[varname]=new_hv_unique[:,k7]
                    node_data_out[varname][np.abs(node_data_out[varname]) < 1e-12] = 0 #(mainly for small négative value) <10e-12 will be corrected to 0
                else:
                    node_data_out[varname] = interpolate_from_triangle(new_xy_unique, hyd_xy_node, original_values, hyd_tin,
                                                                   original_triangle_unique)
        else:
            node_data_out = None

        if hyd_data_mesh is not None:
            mesh_data_out = np.zeros(new_tin_unique.shape[0], dtype=hyd_data_mesh.dtype)
            # varnames=hyd_data_mesh.dtypes.keys()
            for varname in hyd_data_mesh.dtype.names:
                if varname == "i_split":
                    original_i_split = hyd_data_mesh["i_split"]
                    mesh_data_out["i_split"] = original_i_split[enclosing_triangle_unique]
                    mesh_data_out["i_split"] += iscut_newmesh * 5
                else:
                    if varname != "area":
                        original_values = hyd_data_mesh[varname]
                        mesh_data_out[varname] = original_values[enclosing_triangle_unique]
            mesh_data_out = np.lib.recfunctions.append_fields(mesh_data_out, "hydraulic_class", hydro_classes_unique,
                                                              usemask=False)
        else:
            mesh_data_out = None

        i_whole_profile_out = i_whole_profile[enclosing_triangle_unique]


        # hyd_xy_node += translationxy
        ##making sure every point is unique, as numerical errors can make it not so
        node_xy_out, indices2,indices3 = np.unique(new_xy_unique, axis=0, return_inverse=True,return_index=True)
        tin_out2=indices2[tin_out]
        node_data_out3=node_data_out[indices3]
        if "area" in hyd_data_mesh.dtype.names:
            mesh_data_out["area" ]=0.5 * (np.abs((node_xy_out[tin_out2[:, 1]][:, 0] - node_xy_out[tin_out2[:, 0]][:, 0]) * (node_xy_out[tin_out2[:, 2]][:, 1] - node_xy_out[tin_out2[:, 0]][:, 1]) - (node_xy_out[tin_out2[:, 2]][:, 0] - node_xy_out[tin_out2[:, 0]][:, 0]) * (node_xy_out[tin_out2[:, 1]][:, 1] - node_xy_out[tin_out2[:, 0]][:, 1])))
        node_xy_out += translationxy

        return nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume, node_xy_out, node_data_out3, mesh_data_out, tin_out2, i_whole_profile_out
    else:
        return nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume


def hscomparison(classhv1, hs1, classhv2, hs2, k1=1, k2=1):
    # checking validity of the operation
    bok = False
    cl_h1, cl_v1 = classhv1[0], classhv1[1]
    cl_h2, cl_v2 = classhv2[0], classhv2[1]
    if len(cl_h1) != len(cl_h2) or len(cl_h1) != len(cl_h2):
        print("hydrosignatures comparison classes definitions must be identical to perform comparison")
        return
    if len([i for i, j in zip(cl_h2, cl_h1) if i != j]) != 0 or len([i for i, j in zip(cl_v2, cl_v1) if i != j]) != 0:
        print("hydrosignatures comparison classes definitions must be identical to perform comparison")
        return
    nb_cl_h, nb_cl_v = len(cl_h1) - 1, len(cl_v1) - 1
    if hs1.shape != (nb_cl_h, nb_cl_v) or hs2.shape != (nb_cl_h, nb_cl_v):
        print(
            "hydrosignatures comparison at least one of the two hydrosignature to compare is not coherent with the classes definitions impossible to perform comparison")
        return
    hsf10 = np.zeros((nb_cl_h + 2, nb_cl_v + 2), dtype=np.float64)
    hsf20 = np.zeros((nb_cl_h + 2, nb_cl_v + 2), dtype=np.float64)
    hsf1 = np.zeros((nb_cl_h + 2, nb_cl_v + 2), dtype=np.float64)
    hsf2 = np.zeros((nb_cl_h + 2, nb_cl_v + 2), dtype=np.float64)
    hsf10[1:nb_cl_h + 1, 1:nb_cl_v + 1] = hs1
    hsf20[1:nb_cl_h + 1, 1:nb_cl_v + 1] = hs2
    for ih in range(nb_cl_h + 2):
        for iv in range(nb_cl_v + 2):
            hsf1[ih][iv] = hsf10[ih][iv] * k1;
            hsf2[ih][iv] = hsf20[ih][iv] * k1
            if ih > 0 and iv > 0:
                hsf1[ih][iv] += hsf10[ih - 1][iv - 1] * k2
                hsf2[ih][iv] += hsf20[ih - 1][iv - 1] * k2
            if iv > 0:
                hsf1[ih][iv] += hsf10[ih][iv - 1] * k2
                hsf2[ih][iv] += hsf20[ih][iv - 1] * k2
            if ih < nb_cl_h + 1 and iv > 0:
                hsf1[ih][iv] += hsf10[ih + 1][iv - 1] * k2
                hsf2[ih][iv] += hsf20[ih + 1][iv - 1] * k2
            if ih < nb_cl_h + 1:
                hsf1[ih][iv] += hsf10[ih + 1][iv] * k2
                hsf2[ih][iv] += hsf20[ih + 1][iv] * k2
            if ih < nb_cl_h + 1 and iv < nb_cl_v + 1:
                hsf1[ih][iv] += hsf10[ih + 1][iv + 1] * k2
                hsf2[ih][iv] += hsf20[ih + 1][iv + 1] * k2
            if iv < nb_cl_v + 1:
                hsf1[ih][iv] += hsf10[ih][iv + 1] * k2
                hsf2[ih][iv] += hsf20[ih][iv + 1] * k2
            if ih > 0 and iv < nb_cl_v + 1:
                hsf1[ih][iv] += hsf10[ih - 1][iv + 1] * k2
                hsf2[ih][iv] += hsf20[ih - 1][iv + 1] * k2
            if ih > 0:
                hsf1[ih][iv] += hsf10[ih - 1][iv] * k2
                hsf2[ih][iv] += hsf20[ih - 1][iv] * k2
    hsf1 = hsf1 / (k1 + 8 * k2)
    hsf2 = hsf2 / (k1 + 8 * k2)
    hsc = np.sum(np.abs(hsf1 - hsf2)) / 2

    bok = True
    return bok, hsc


def hsexporttxt(pathexport, filename, classhv, unitname, nb_mesh, total_area, total_volume, mean_depth, mean_velocity,
                mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume, no_unit=1, factor=1,
                mean_width=0):
    ff = os.path.join(pathexport, filename)
    cl_h, cl_v = classhv[0], classhv[1]
    listhsglobal = ['N_Unit', 'Unit', 'Factor', 'mean_width', 'nbelt_unit', 'total_area', 'total_volume', 'height_mean',
                    'velocity_mean', 'mean_Froude', 'min_height', 'max_height', 'min_velocity', 'max_velocity']
    listclassarea = []
    listclassvolume = []
    for kh in range(len(cl_h) - 1):
        for kv in range(len(cl_v) - 1):
            listclassarea.append(
                'Area[' + str(cl_h[kh]) + '<=HW<' + str(cl_h[kh + 1]) + '|' + str(cl_v[kv]) + '<=V<' + str(
                    cl_v[kv + 1]) + ']')
            listclassvolume.append(
                'Volume[' + str(cl_h[kh]) + '<=HW<' + str(cl_h[kh + 1]) + '|' + str(cl_v[kv]) + '<=V<' + str(
                    cl_v[kv + 1]) + ']')
    if os.path.isfile(ff):
        f = open(ff, "r+")
        current_classes = '\t'.join(listhsglobal) + '\t' + '\t'.join(listclassarea) + '\t' + '\t'.join(
            listclassvolume) + '\n'
        file_classes = f.readlines()[7]
        if not current_classes == file_classes:
            print(
                "ERROR: The hydraulic classes in the text file are not the same as those requested. The same file cannot contain two different sets of ")
            return
    else:
        f = open(ff, 'w')

        f.write('hydrosignature built by HABBY' + '\n')

        f.write('hw(m)' + ' ' + ' '.join(str(elem) for elem in cl_h) + '\n')
        f.write('v(m/s)' + ' ' + ' '.join(str(elem) for elem in cl_v) + '\n')
        f.write('area_(m2)_volume_(m3)_mean_height_(m)_mean_velocity_(m/s)' + '\n')
        f.write('%_of_distribution_in_[height_HW|velocity_V]_combination_classes' + '\n')
        f.write('CAUTION_THE_PERCENTAGES_SUMS_DO_NOT_ALWAYS_EXACTLY_MATCH_100' + '\n')
        f.write('\n')

        f.write('\t'.join(listhsglobal) + '\t' + '\t'.join(listclassarea) + '\t' + '\t'.join(listclassvolume) + '\n')

    listhsglobalvalue = [no_unit, unitname, factor, mean_width, nb_mesh, total_area, total_volume, mean_depth,
                         mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity]
    listclassareavalue = []
    listclassvolumevalue = []
    for kh in range(len(cl_h) - 1):
        for kv in range(len(cl_v) - 1):
            listclassareavalue.append(str(hsarea[kh][kv]))
            listclassvolumevalue.append(str(hsvolume[kh][kv]))
    f.write(
        '\t'.join(str(elem) for elem in listhsglobalvalue) + '\t' + '\t'.join(listclassareavalue) + '\t' + '\t'.join(
            listclassvolumevalue) + '\n')
    f.close()
    return


def areavolumepoly(poly, ia, ib, ic):
    area = np.abs(
        (poly['x'][ib] - poly['x'][ia]) * (poly['y'][ic] - poly['y'][ia]) - (poly['x'][ic] - poly['x'][ia]) * (
                poly['y'][ib] - poly['y'][ia])) / 2
    volume = area * np.mean((poly['h'][ia], poly['h'][ib], poly['h'][ic]))
    return area, volume


def check_hs_class_validity(classhv):
    '''
    checking the validity of the definition of the two classes depth and velocity  defining the hydrosignature grid
    :param classhv: a list of two lists [[h0,h1,...,hn] , [v0,v1,...,vm]] defining the hydrosignature grid
    :return cl_h= [h0,h1,...,hn],cl_v=[v0,v1,...,vm] ,nb_cl_h= n,nb_cl_v=m
    '''
    bok = True
    if len(classhv) != 2:
        print("Error: hydrosignature : there is not 2 classes h,v found")
    if isinstance(classhv[0], list) == False or isinstance(classhv[1], list) == False:
        print("Error: hydrosignature : we have not 2 classes h,v found")

    cl_h, cl_v = classhv[0], classhv[1]
    nb_cl_h, nb_cl_v = len(cl_h) - 1, len(cl_v) - 1
    if nb_cl_h < 1 or nb_cl_v < 1:
        print("Error: hydrosignature : a classe h,v found have less than 2 elements")
        bok = False
    if len(set(cl_h)) - 1 != nb_cl_h or len(set(cl_v)) - 1 != nb_cl_v:
        print("Error: hydrosignature : there are duplicates in the classes  h,v")
        bok = False
    cl_h2, cl_v2 = list(cl_h), list(cl_v)
    cl_h2.sort()
    cl_v2.sort()
    if len([i for i, j in zip(cl_h2, cl_h) if i != j]) != 0 or len([i for i, j in zip(cl_v2, cl_v) if i != j]) != 0:
        print("Error: hydrosignature : the classes  h,v are not sorted")
        bok = False
    # checking wether an hydrosignature can be calculated
    if bok == False:
        print("Error: there is a problem in the class definition hydrosignature cannot be calculated")
        return
    return bok, cl_h, cl_v, nb_cl_h, nb_cl_v


def hydraulic_class_from_file(filename):
    ""
    # TODO: read headers and units to check validity and matching unit with data2d unit data
    warnings_list = []
    f = open(filename, "r")
    hvclass = [[], []]
    for i in [0, 1]:
        hvcstr = f.readline().rstrip("\n").split()

        for item in hvcstr[1:]:
            if item == "":
                #warnings_list.append("Warning: space character is present in hydrosignature input class file, it will be remove.")
                continue
            try:
                hvclass[i] += [float(item)]
            except ValueError:
                warnings_list.append("Error: can't convert" + str(item) + "to float.")
                return None, warnings_list

    # check_hs_class_validity
    valid = check_hs_class_validity(hvclass)

    if valid:
        return hvclass, warnings_list
    else:
        return None, warnings_list


def hydraulic_data_from_file(filename):
    pointsxy = []
    pointshv = []
    f = open(filename, "r")
    for line in f:
        data = line.rstrip("\n").split("\t")
        pointsxy += [data[:2]]
        pointshv += [data[2:4]]
    pointsxy = np.array(pointsxy).astype(float)
    pointshv = np.array(pointshv).astype(float)
    return pointsxy, pointshv


def interpol0(x, xa, ya, xb, yb):
    return (x - xa) * (yb - ya) / (xb - xa) + ya


def interpolate_from_triangle(new_xy, old_xy, old_values, old_tin, original_triangle):
    """
    Linearly interpolates the value of a variable z inside the mesh elements
    epsilonnul to avoid numerical problem with negative values calculated for h or v <1e-12
    :param new_xy: (m,2) array
    :param old_xy: (n,2) array
    :param old_values: (n,) array containing z-values in each node of original mesh
    :param old_tin: (l,3) array containing tin of old mesh (referring to old mesh indices)
    :param original_triangle: (m,) array containing the index of the triangle each new node is inside
    :return z: (m,) array of interpolated z-values in the positions of the new nodes
    """
    ordered_tin = old_tin[original_triangle]
    coordinates = old_xy[ordered_tin]
    x1, x2, x3 = coordinates[:, 0, 0], coordinates[:, 1, 0], coordinates[:, 2, 0]
    y1, y2, y3 = coordinates[:, 0, 1], coordinates[:, 1, 1], coordinates[:, 2, 1]
    values = old_values[ordered_tin]
    z1, z2, z3 = values[:, 0], values[:, 1], values[:, 2]
    x, y = new_xy[:, 0], new_xy[:, 1]
    z = z1 + (((x - x1) * ((y2 - y1) * (z2 - z3) - (y2 - y3) * (z2 - z1))) + (
            (y - y1) * ((x2 - x3) * (z2 - z1) - (x2 - x1) * (z2 - z3)))) / (
                (x2 - x3) * (y2 - y1) - (x2 - x1) * (y2 - y3))
    return z


def check_hs_class_match_hydraulic_values(classhv, h_min, h_max, v_min, v_max):
    error = ""
    cl_h, cl_v = classhv[0], classhv[1]

    if h_min < np.min(cl_h) or h_max > np.max(cl_h):
        return False, "Error: Some height values are off the class definition. hydrosignature cannot be calculated. " \
                      "Check min/max height values in the 'Data explorer'."
    if v_min < np.min(cl_v) or v_max > np.max(cl_v):
        return False, "Some velocity values are off the class definition. hydrosignature cannot be calculated. " \
                      "Check min/max velocity values in the 'Data explorer'."

    return True, error


def index_to_class_number(class_shape, indices):
    # takes a hydraulic class indicated by a (i,j) tuple of indices and returns the class number according to standard hydrosignature usage
    '''

    :param class_shape: (m,n) tuple, containing respectively the number of h classes and v classes
    :param indices: (i,j) tuple, containing respectively the position of a given hydraulic class in h and v
    :return class_number: the number that indicates the class according to hydrosignature standard, starting at 1 and going through velocity first, then depth
    '''
    i, j = indices
    m, n = class_shape
    number = i * m + j + 1
    if i >= m or j >= n:
        raise IndexError
    return number


# if __name__ == '__main__':
#     '''
#     testing the hydrosignature program
#     '''
#     t = 1  # regarding this value different tests can be launched
#     if t == 0:  # random nbpointhyd, nbpointsub are the number of nodes/points to be randomly generated respectively for hydraulic and substrate TIN
#         classhv = [[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 3], [0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 5]]
#         hyd_tin = np.array([[0, 1, 3], [0, 3, 4], [1, 2, 3], [3, 4, 6], [3, 6, 7], [4, 5, 6]])
#         hyd_xy_node = np.array([[821128.213280755, 1867852.71720679], [821128.302459342, 1867853.34262438],
#                                 [821128.314753232, 1867854.93690708], [821131.385434587, 1867854.6662084],
#                                 [821132.187889633, 1867852.67553172], [821136.547596803, 1867851.73984275],
#                                 [821136.717311027, 1867853.21858062], [821137.825096539, 1867853.68]])
#         hyd_hv_node = np.array(
#             [[1.076, 0.128], [0.889999985694885, 0.155], [0, 0], [0, 0], [0.829999983310699, 0.145], [1.127, 0.143],
#              [0.600000023841858, 0.182], [0, 0]])
#         nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume = hydrosignature_calculation_alt(
#             classhv, hyd_tin, hyd_xy_node, hyd_hv_node)
#         print(nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth,
#               min_velocity, max_velocity, hsarea, hsvolume)
#         bok, hsc = hscomparison(classhv, hsarea, classhv, hsvolume)
#         print(hsc)
#
#         # Test export file
#         pathexport = 'C:\\habby_dev\\files\\hydrosignature'
#         filename = "3HSexport.txt"
#         unitname = 'XXXXXXX'
#         hsexporttxt(pathexport, filename, classhv, unitname, nb_mesh, total_area, total_volume, mean_depth,
#                     mean_velocity,
#                     mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume)
#
#     if t == 1:
#         t0 = time.time()
#
#         classhv = [[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 3, 100], [0, 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 5, 100]]
#         path_prj = "C:\\habby_dev\\Hydrosignature\\project"
#         input_filename = "a1.hyd"
#         oldhdf5 = hdf5_mod.Hdf5Management(path_prj, input_filename, new=False, edit=False)
#         # oldhdf5.load_hdf5_hyd()
#         # oldhdf5.load_data_2d()
#         # oldhdf5.load_whole_profile()
#         # oldhdf5.load_data_2d_info()
#         # oldhdf5.add_hs(classhv)
#         newhdf5 = oldhdf5.hydrosignature_new_file(classhv)
#         t1 = time.time()
#         print("time: " + str(t1 - t0))
#         # newhdf5.load_hydrosignature()
#         newfile = hdf5_mod.Hdf5Management(path_prj, "a1_HS.hyd", new=True)
#         newfile.load_hdf5_hyd()
#         newfile.load_data_2d()
#         newfile.load_hydrosignature()
#         print(newhdf5.data_2d)
    # nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume = hydrosignature_calculation(
    #     classhv, hyd_tin, hyd_xy_node, hyd_hv_node)

    # Test HSC
