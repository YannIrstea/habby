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
import sys
from io import StringIO
import shapefile
import os
import numpy as np
from scipy.spatial import Voronoi
from random import uniform
import triangle as tr
from random import randrange
from shapely.geometry import MultiPoint, Polygon, Point
from PyQt5.QtWidgets import QMessageBox
from src import hdf5_mod
from src.tools_mod import get_prj_from_epsg_web
from src import manage_grid_mod


def open_shp(filename, path):
    """
    This function open a ArcGIS shpaefile.

    :param filename: the name of the shapefile
    :param path: the path to this shapefile
    :return: a shapefile object as define in the model
    """

    # test extension and if the file exist
    blob, ext = os.path.splitext(filename)
    if ext != '.shp':
        print('Warning: the file does not have a .shp extension.')
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The shapefile " + filename + " does not exist.")
        return [-99], [-99], [-99]
    # read shp
    try:
        sf = shapefile.Reader(file)
    except shapefile.ShapefileException:
        print('Error: Cannot open the shapefile ' + filename + ', or one of the associated files (.shx, .dbf)')
        return [-99], [-99], [-99]

    return sf


def get_all_attribute(filename, path):
    """
    This function open a shapefile and get the list of all the attibute which is contains in it.

    :param filename: the name of the shpae file
    :param path: the path to this shapefile
    :return: a list with the name and information of all attribute. The form of each element of the list
             is [name(str), type (F,N), int, int]
    """

    sf = open_shp(filename, path)
    fields = sf.fields
    if len(fields) > 1:
        fields = fields[1:]
    else:
        print('Warning: No attibute found in the shapefile.')

    return fields


def get_useful_attribute(attributes):
    """
    This function find if the substrate was given in percentage or coarser/dominant/accesory and get the attribute
    or header name useful to load the substrate. If the subtrate is given by percentage, it is important to get
    attribute in order (S1, S2, S3) and not (S3, S1,S2) for this function and the next functions.

    :param attributes: The list of attribute from the shp file or the header list from the text file
    :return: The attribute type as int (percentage=1 and coarser/... = 0 and failed = -99) and the attribute names
                    If we are in the attribute type 0, attribute list is in the order of: coarser, dominant, and accessory

    """

    # all the different attribute names which can be accepted in the shape file
    pg = ['PG', 'PLUS_GROS', 'COARSER', 'SUB_COARSER', 'SUB_PG']
    pg = pg + list(map(lambda x: x.lower(), pg))
    dom = ['DM', 'DOMINANT', 'DOM', 'SUB_DOM']
    dom = dom + list(map(lambda x: x.lower(), dom))
    acc1 = ['ACC', 'ACCESSORY', 'ACCESSOIRE', 'SUB_ACC']
    acc1 = acc1 + list(map(lambda x: x.lower(), acc1))
    # create per_name
    per_all = []
    for m in range(0, 15):
        per_all.append('S' + str(m))
        per_all.append('s' + str(m))

    # stating
    found_per = False
    found_pg = False
    found_one_pg = 0  # if we found dominant and "plus gros", we get found_pg = True
    sub_classification_method = -99  # -99 indicates a failed load.
    attribute_name = ['-99', '-99', '-99']
    num_here = 0

    for f in attributes:

        if f[0] in pg:
            found_one_pg += 1
            attribute_name[0] = "coarser"
        if f[0] in dom:
            found_one_pg += 1
            attribute_name[1] = "dom"
        if f[0] in acc1:
            attribute_name[2] = "acc"

        if found_one_pg == 2:
            found_pg = True
            sub_classification_method = "coarser-dominant"

        if f[0] in per_all:
            num_here += 1
            found_per = True
            sub_classification_method = "percentage"
            if f[-1] == '1':
                attribute_name[0] = f[0]
            if f[-1] == '2':
                attribute_name[1] = f[0]
            if f[-1] == '3':
                attribute_name[2] = f[0]
            else:
                attribute_name.append(f[0])

        if found_per and found_pg:
            print('Error: The attributes of substrate shapefile cannot be understood: mixing betweeen percentage and'
                  'coarser/dominant attributes.\n')
            sub_classification_method = -99
            return

    if not found_pg and not found_per:
        print('Error: The attribute names of the substrate could not be recognized.\n')
        sub_classification_method = -99

    return sub_classification_method, attribute_name


def polygon_shp_to_triangle_shp(filename, path_file, path_prj):
    """
    Convert a polygon shapefile to a polygon triangle shapefile
    with a constrained Delaunay triangulation
    of a Planar Straight Line Graph (PSLG)
    :param in_shp_path: path where the input shapefile is present.
    :param in_shp_filename: input filename (with extension)
    :param out_shp_path: path where the output shapefile will be produced.
    :param out_shp_filename: output filename (with extension)
    :return: True (triangle shapefile produced) False (error)
    """
    # init
    shapefile_type = 5  # polygon
    prj = False  # presence of the .prj accompanying the shapefile

    # read source shapefile
    in_shp_abs_path = os.path.join(path_file, filename)
    in_shp_basename_abs_path = os.path.splitext(in_shp_abs_path)[0]
    sf = shapefile.Reader(in_shp_abs_path)
    if sf.shapeType != shapefile_type:
        print("file is not polygon type")
        return False
    shapes = sf.shapes()
    records = sf.records()
    fields = sf.fields[1:]
    if os.path.isfile(in_shp_basename_abs_path + ".prj"):
        prj = open(in_shp_basename_abs_path + ".prj", "r").read()

    # Extract list of points and segments from shp
    vertices_array = []  # point
    segments_array = []  # segment index or connectivity table
    holes_array = []
    inextpoint = 0
    for i in range(len(shapes)):  # for each polygon
        if len(shapes[i].parts) > 1:  # polygon a trous
            index_hole = list(shapes[i].parts) + [len(shapes[i].points)]
            new_points = []
            lnbptspolys = []
            for j in range(len(index_hole) - 1):
                new_points.extend(shapes[i].points[index_hole[j]:index_hole[j + 1] - 1])
                lnbptspolys.append(index_hole[j + 1] - 1 - index_hole[j])
                if j > 0:  # hole presence : creating a single point inside the hole using triangulation
                    vertices_hole = np.array(shapes[i].points[index_hole[j]:index_hole[j + 1] - 1])
                    segments_hole = []
                    for k in range(lnbptspolys[-1]):
                        segments_hole.append([k % lnbptspolys[-1], (k + 1) % lnbptspolys[-1]])
                    segments_hole = np.array(segments_hole)
                    polygon_hole = dict(vertices=vertices_hole, segments=segments_hole)
                    polygon_hole_triangle = tr.triangulate(polygon_hole, "p")
                    p1 = polygon_hole_triangle["vertices"][polygon_hole_triangle["triangles"][0][0]].tolist()
                    p2 = polygon_hole_triangle["vertices"][polygon_hole_triangle["triangles"][0][1]].tolist()
                    p3 = polygon_hole_triangle["vertices"][polygon_hole_triangle["triangles"][0][2]].tolist()
                    holes_array.append([(p1[0] + p2[0] + p3[0]) / 3, (p1[1] + p2[1] + p3[1]) / 3])
        else:
            new_points = list((shapes[i].points[:-1]))  # taking off the first redundant description point
            lnbptspolys = [len(new_points)]
        # add
        vertices_array.extend(new_points)  # add the points to list
        for j in range(len(lnbptspolys)):  # add the segments to list
            for k in range(lnbptspolys[j]):
                segments_array.append([k % lnbptspolys[j] + inextpoint, (k + 1) % lnbptspolys[j] + inextpoint])
            inextpoint += lnbptspolys[j]

    # Taking off the doublons
    # AIM: for using triangle to transform polygons into triangles it is necessary to avoid any point doublon
    vertices_array = np.array(vertices_array)
    n0 = np.array([[i] for i in range(inextpoint)])
    t = np.hstack([vertices_array, n0])
    t = t[t[:, 1].argsort()]  # sort in y secondary key
    t = t[t[:, 0].argsort()]  # sort in x primary key
    vertices_array2 = []
    corresp = []
    j = -1
    for i in range(inextpoint):
        if i == 0 or not (x0 == t[i][0] and y0 == t[i][1]):
            x0, y0 = t[i][0], t[i][1]
            vertices_array2.append([x0, y0])
            j += 1
        corresp.append([int(t[i][2]), j])
    corresp = np.array(corresp)
    corresp = corresp[corresp[:, 0].argsort()]  # sort in n0 primary key
    segments_array2 = []
    for elem in segments_array:
        segments_array2.append([corresp[elem[0]][1], corresp[elem[1]][1]])
    segments_array2 = np.array(segments_array2)
    vertices_array2 = np.array(vertices_array2)
    holes_array = np.array(holes_array)

    # triangulate on polygon (if we use regions
    if holes_array.size == 0:
        polygon_from_shp = dict(vertices=vertices_array2,
                                segments=segments_array2)
    else:
        polygon_from_shp = dict(vertices=vertices_array2,
                                segments=segments_array2,
                                holes=holes_array)
    polygon_triangle = tr.triangulate(polygon_from_shp, "p")  # , opts="p")
    #tr.compare(plt, polygon_from_shp, polygon_triangle)

    # get geometry and attributes of triangles
    triangle_geom_list = []
    triangle_records_list = []
    for i in range(len(polygon_triangle["triangles"])):
        # triangle coords
        p1 = polygon_triangle["vertices"][polygon_triangle["triangles"][i][0]].tolist()
        p2 = polygon_triangle["vertices"][polygon_triangle["triangles"][i][1]].tolist()
        p3 = polygon_triangle["vertices"][polygon_triangle["triangles"][i][2]].tolist()
        triangle_geom_list.append([p1, p2, p3])
        # triangle centroid
        xmean = (p1[0] + p2[0] + p3[0]) / 3
        ymean = (p1[1] + p2[1] + p3[1]) / 3
        polyg_center = (xmean, ymean)
        # if center in polygon: get attributes
        for j in range(len(shapes)):  # for each polygon
            if len(shapes[j].parts) > 1:  # hole presence
                point_list = shapes[j].points[:shapes[j].parts[1]-2]
            else:
                point_list = shapes[j].points[:-1]
            if point_inside_polygon(polyg_center[0], polyg_center[1], point_list):
                triangle_records_list.append(records[j])

    # write triangulate shapefile
    out_shp_basename = os.path.splitext(filename)[0]
    out_shp_filename = out_shp_basename + "_triangulated.shp"
    out_shp_path = os.path.join(path_prj, "input")
    out_shp_abs_path = os.path.join(out_shp_path, out_shp_filename)
    out_shp_basename_abs_path = os.path.splitext(out_shp_abs_path)[0]
    w = shapefile.Writer(shapefile_type)
    for field in fields:
        w.field(*field)
    for i in range(len(triangle_geom_list)):
        w.poly(parts=[triangle_geom_list[i]])
        w.record(*triangle_records_list[i])
    w.save(out_shp_abs_path)
    if prj:
        open(out_shp_basename_abs_path + ".prj", "w").write(prj)
    return True


def point_inside_polygon(x, y, poly):
    """
    To know if point is inside or outsite of a polygon (without holes)
    :param x: coordinate x in float
    :param y: coordinate y in float
    :param poly: list of coordinates [[x1, y1], ..., [xn, yn]]
    :return: True (inside), False (not inseide)
    """
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def data_substrate_validity(header_list, sub_array, sub_mapping_method, sub_classification_code):
    """
    This function check if substrate data (from txt or shp) is coherent with code type.

    :param header_list: List of headers
    :param sub_array: List of data by columns (index in list correspond with header)
    :param code_type: Code type of substrate
    :return: True/False: if data is or not valid
             sub_classification_name : type of substrate
    """
    # sub_description_system
    sub_description_system = dict(sub_mapping_method=sub_mapping_method,
                                  sub_classification_code=sub_classification_code,
                                  sub_classification_method=-99)

    # header
    fake_field = [None] * len(header_list)  # fake fields like shapefile
    header2 = list(zip(header_list, fake_field))

    # percent or coarserdom ?
    [sub_classification_method, attribute_name] = get_useful_attribute(header2)
    sub_description_system["sub_classification_method"] = sub_classification_method

    # get sub_classification_name
    if sub_classification_method == -99:
        return False, sub_description_system

    # coarserdom
    if sub_classification_method == "coarser-dominant":
        # coarser dom
        sub_pg = sub_array[header_list.index("coarser")]
        sub_dom = sub_array[header_list.index("dom")]
        # check min max if match code_type
        if sub_classification_code == 'Cemagref':  # All value 1 < x < 8
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The Cemagref code should be formed by an int between 1 and 8. (2)\n')
                return False, sub_description_system
            elif max(sub_dom) > 8 or max(sub_pg) > 8:
                print('Error: The Cemagref code should be formed by an int between 1 and 8. (3)\n')
                return False, sub_description_system
            else:
                return True, sub_description_system
        elif sub_classification_code == 'Sandre':  # All value 1 < x < 12
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The Sandre code should be formed by an int between 1 and 12. (2)\n')
                return False, sub_description_system
            elif max(sub_dom) > 12 or max(sub_pg) > 12:
                print('Error: The Sandre code should be formed by an int between 1 and 12. (3)\n')
                return False, sub_description_system
            else:
                return True, sub_description_system
        else:
            print('Error: The substrate code is not recognized.\n')
            return False, sub_description_system

    # if percentage type
    if sub_classification_method == "percentage":
        # all case : sum == 100 % ?
        sub_array2 = list(zip(*sub_array))  # retransforme data by features
        for e in range(0, len(sub_array2)):  # for all features
            if sum(sub_array2[e]) != 100:
                print('Warning: Substrate data is given in percentage. However, it does not sum to 100% \n')
                return False, sub_description_system
        # code type Cemagref S1 ==> S8
        if sub_classification_code == 'Cemagref':
            if not "S8" in attribute_name:
                print('Error: The Cemagref percentages should contain 8 classes of percent.\n')
                return False, sub_description_system
            else:
                return True, sub_description_system
        # code type sandre  S1 ==> S12
        elif sub_classification_code == 'Sandre':
            if not "S12" in attribute_name:
                print('Error: The Sandre percentages should contain 12 classes of percent.\n')
                return False, sub_description_system
            else:
                return True, sub_description_system
        else:
            print('Error: The substrate code is not recognized.\n')
            return False, sub_description_system


def shp_validity(filename, path_prj, code_type, dominant_case=1):
    ind = 0

    # open shape file (think about zero or one to start! )
    sf = open_shp(filename, path_prj)

    fields = sf.fields

    # find where the info is and how was given the substrate (percentage or coarser/dominant/accessory)
    [attribute_type, attribute_name] = get_useful_attribute(fields)
    if attribute_type == -99:
        print('Error: The substate data not recognized.\n')
        return False, dominant_case

    # if percentage type
    if attribute_type == 1:
        record_all = []
        # get the data and pass it int
        for f in fields:
            if f[0] in attribute_name:
                record_here = sf.records()
                record_here = np.array(record_here)
                record_here = record_here[:, ind]
                try:
                    record_here = list(map(int, record_here))
                except ValueError:
                    print('Error: The substate code should be formed by an int.\n')
                    return False, dominant_case
                record_all.append(record_here)
                ind += 1
        record_all = np.array(record_all).T

        # get the dominant and coarser from the percentage
        [sub_dom, sub_pg] = percentage_to_domcoarse(record_all, dominant_case)

        # dominant case unknown
        if len(sub_dom) == 1:
            if sub_dom[0] == -99:
                # in this case ask the user
                msg2 = QMessageBox()
                msg2.setWindowTitle('Dominant substrate')
                msg2.setText('Our analysis found that the dominant substrate of certain substrate'
                                          ' cells cannot be determined. Indeed, the maximum percentage of two or '
                                          'more classes are equal. In these cases, should we take the larger or the'
                                          ' smaller substrate class?')
                b1 = msg2.addButton('Larger', QMessageBox.NoRole)
                b2 = msg2.addButton('Smaller', QMessageBox.YesRole)
                msg2.exec()
                if msg2.clickedButton() == b1:
                    dominant_case = 1
                elif msg2.clickedButton() == b2:
                    dominant_case = -1

                # recompute
                [sub_dom, sub_pg] = percentage_to_domcoarse(record_all, dominant_case)

        # transform to cemagref substrate form
        if code_type == 'Cemagref':
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The Cemagref code should be formed by an int between 1 and 8. (2)\n')
                return False, dominant_case
            elif max(sub_dom) > 8 or max(sub_pg) > 8:
                print('Error: The Cemagref code should be formed by an int between 1 and 8. (3)\n')
                return False, dominant_case
            else:
                return True, dominant_case
        # # code type edf - checked and transform
        # elif code_type == 'EDF':
        #     if min(sub_dom) < 1 or min(sub_pg) < 1:
        #         print('Error: The edf code should be formed by an int between 1 and 8. (2)\n')
        #         return False, dominant_case
        #     elif max(sub_dom) > 8 or max(sub_pg) > 8:
        #         print('Error: The edf code should be formed by an int between 1 and 8. (3)\n')
        #         return False, dominant_case
        #     else:
        #         sub_dom = edf_to_cemagref(sub_dom)
        #         sub_pg = edf_to_cemagref(sub_pg)
        #         return True, dominant_case
        # code type sandre
        elif code_type == 'Sandre':
            if min(sub_dom) < 1 or min(sub_pg) < 1:
                print('Error: The sandre code should be formed by an int between 1 and 12. (2)\n')
                return False, dominant_case
            elif max(sub_dom) > 12 or max(sub_pg) > 12:
                print('Error: The sandre code should be formed by an int between 1 and 12. (3)\n')
                return False, dominant_case
            else:
                sub_dom = sandre_to_cemagref(sub_dom)
                sub_pg = sandre_to_cemagref(sub_pg)
                return True, dominant_case
        else:
            print('Error: The substrate code is not recognized.\n')
            return False, dominant_case

    # pg/coarser/accessory type
    elif attribute_type == 0:
        for f in fields:
            if f[0] == attribute_name[0] or f[0] == attribute_name[1]:  # [0] coarser and [1] pg
                # read for all code type
                a = int('2')
                record_here = sf.records()
                record_here = np.array(record_here)
                record_here = record_here[:, ind - 1]
                try:
                    record_here = list(map(float, record_here))  # int('2.000' ) throw an error
                    record_here = list(map(int, record_here))
                except ValueError:
                    print('Error: The substrate code should be formed by an int.\n')
                    return False, dominant_case

                # code type cemagref - checked
                if code_type == 'Cemagref':
                    if min(record_here) < 1:
                        print('Error: The Cemagref code should be formed by an int between 1 and 8. (2)\n')
                        return False, dominant_case
                    elif max(record_here) > 8:
                        print('Error: The Cemagref code should be formed by an int between 1 and 8. (3)\n')
                        return False, dominant_case
                # code type edf - checked and transform
                elif code_type == 'EDF':
                    if min(record_here) < 1:
                        print('Error: The edf code should be formed by an int between 1 and 8. (2)')
                        return False, dominant_case
                    elif max(record_here) > 8:
                        print('Error: The edf code should be formed by an int between 1 and 8. (3)')
                        return False, dominant_case
                    else:
                        record_here = edf_to_cemagref(record_here)
                # code type sandre
                elif code_type == 'Sandre':
                    if min(record_here) < 1:
                        print('Error: The sandre code should be formed by an int between 1 and 12. (2)\n')
                        return False, dominant_case
                    elif max(record_here) > 12:
                        print('Error: The sandre code should be formed by an int between 1 and 12. (3)\n')
                        return False, dominant_case
                    else:
                        record_here = sandre_to_cemagref(record_here)
                else:
                    print('Error: The substrate code is not recognized.\n')
                    return False, dominant_case

                # now that we have checked and transform, give the data
                if f[0] == attribute_name[0]:
                    sub_pg = record_here
                if f[0] == attribute_name[1]:
                    sub_dom = record_here
            ind += 1
        return True, dominant_case
    else:
        print('Error: Attribute type not recognized.\n')
        return False, dominant_case


def load_sub_shp(filename, path_file, path_prj, path_hdf5, name_prj, name_hdf5, sub_mapping_method,
                 sub_classification_code, sub_epsg_code, default_values, queue=[]):
    """
    A function to load the substrate in form of shapefile.

    :param filename: the name of the shapefile
    :param path_prj: the path where the shapefile is
    :param sub_classification_code: the type of code used to define the substrate (string)
    :param dominant_case: an int to manage the case where the transfomation form percentage to dominnat is unclear (two
           maxinimum percentage are equal from one element). if -1 take the smallest, if 1 take the biggest,
           if 0, we do not know.
    :return: grid in form of list of coordinate and connectivity table (two list)
            and an array with substrate type and a boolean which allows to get the case where we have tow dominant case

    """
    sys.stdout = mystdout = StringIO()

    # open shape file
    sf = open_shp(filename, path_file)

    # get sub data in the shape file
    fields = sf.fields
    header_list = []
    for i, field in enumerate(fields):
        if i > 0:
            header_list.append(field[0])
    records = sf.records()
    sub_array = list(zip(*records))

    # check data validity
    data_validity, sub_description_system = data_substrate_validity(header_list,
                                                                    sub_array,
                                                                    sub_mapping_method,
                                                                    sub_classification_code)

    sub_description_system["sub_filename_source"] = filename
    sub_description_system["sub_class_number"] = str(len(sub_array))
    sub_description_system["sub_default_values"] = default_values
    sub_description_system["sub_reach_number"] = "1"
    sub_description_system["sub_unit_number"] = "1"
    sub_description_system["sub_unit_list"] = "0.0"
    sub_description_system["sub_unit_type"] = "unknown"
    sub_description_system["sub_epsg_code"] = sub_epsg_code

    if data_validity:
        # before loading substrate shapefile data : create shapefile triangulated mesh from shapefile polygon
        if polygon_shp_to_triangle_shp(filename, path_file, path_prj):
            # file name triangulated
            filename = filename[:-4] + "_triangulated.shp"

            # initialization
            xy = []  # point
            tin = []  # connectivity table
            ind = 0

            # open shape file (think about zero or one to start! )
            sf = open_shp(filename, os.path.join(path_prj, "input"))

            # get point coordinates and connectivity table in two lists
            shapes = sf.shapes()
            for i in range(0, len(shapes)):
                p_all = shapes[i].points
                tin_i = []
                for j in range(0, len(p_all) - 1):  # last point of shapefile is the first point
                    try:
                        tin_i.append(int(xy.index(p_all[j])))
                    except ValueError:
                        tin_i.append(int(len(xy)))
                        xy.append(p_all[j])
                tin.append(tin_i)

            # get data
            records = sf.records()
            sub_array = list(zip(*records))

            data_2d = dict()
            data_2d["tin"] = [np.array(tin)]
            data_2d["xy"] = [np.array(xy)]
            data_2d["sub"] = [np.array(sub_array)]
            data_2d["nb_unit"] = 1
            data_2d["nb_reach"] = 1

            # save hdf5
            hdf5 = hdf5_mod.Hdf5Management(path_prj, name_hdf5)
            hdf5.create_hdf5_sub(sub_description_system, data_2d)

    queue.put(mystdout)


def edf_to_cemagref(records):
    """
    This function passes the substrate data from the code type 'EDF" to the code type "Cemagref". As the code 1 from EDF
    can be the code 2 or code 1 in Cemagref, a code 1 in EDF is code 1 in Cemagref half of the time and code 2 the
    other half of the time. This function is not optimized yet. For the definiction of the code, see the tabular at the 14
    of the LAMMI manual. THIS IS NOT RIGHT AS CLASS ARE NOT SPEAREATED IDENTICALLY,  TO BE CORRECTED !!!

    :param records: the substrate data in code edf
    :return: the substrate data in code cemagref

    """
    new_record = []
    one_give_one = False
    for r in records:
        if r == 1:
            new_record.append(2)
        elif r == 2:
            new_record.append(3)
        elif r == 3:
            new_record.append(4)
        elif r == 4:
            new_record.append(5)
        elif r == 5:
            new_record.append(6)
        elif r == 6:
            if one_give_one:
                new_record.append(6)
                one_give_one = False
            else:
                new_record.append(7)
                one_give_one = True
            # new_record.append(6)
        elif r == 7:
            new_record.append(7)
        elif r == 8:  # slabs? -> check this
            new_record.append(8)

    return new_record


def edf_to_cemagref_by_percentage(records):
    """
    This function change the subtrate in a percetage form from edf code to cemagref code
    :param records: the subtrate data (in 8x len tabular)
    :return:
    """
    new_record = []
    for r in records:
        r2 = [0, 0, 0, 0, 0, 0, 0, 0]
        r2[0] = 0
        r2[1] = r[0]
        r2[2] = r[1]
        r2[3] = r[2]
        r2[4] = r[3]
        r2[5] = r[4] + r[5] * 0.5
        r2[6] = r[6] + r[5] * 0.5
        r2[7] = r[7]
        new_record.append(r2)

    return new_record


def sandre_to_cemagref(records):
    """
    This function passes the substrate data from the code type "Sandre" to the code type "Cemagref". This function is
    not optimized yet. For the definition of the code, see the tabular at the 14 of the LAMMI manual.

    :param records: the substrate data in code samdre
    :return: the substrate data in code cemagref

    """

    new_record = []
    for r in records:
        if r == 1:
            new_record.append(1)
        elif r == 2:
            new_record.append(2)
        elif r == 3:
            new_record.append(3)
        elif r == 4:
            new_record.append(3)
        elif r == 5:
            new_record.append(4)
        elif r == 6:
            new_record.append(4)
        elif r == 7:
            new_record.append(5)
        elif r == 8:
            new_record.append(5)
        elif r == 9:
            new_record.append(6)
        elif r == 10:
            new_record.append(6)
        elif r == 11:
            new_record.append(7)
        elif r == 12:
            new_record.append(8)

    return new_record


def percentage_to_domcoarse(sub_data, dominant_case):
    """
    This function is used to pass from percentage data to dominant/coarse. As the code 8 from the subtrate in
    Cemagref code is slab, we do not the 8 code as the coarser substrate.

    :param sub_data: the subtrate data in percentage from Lammi
    :param dominant_case: an int to manage the case where the transfomation form percentage to dominnat is unclear (two
           maxinimum percentage are equal from one element). if -1 take the smallest, if 1 take the biggest,
           if 0, we do not know.
    :return:
    """
    sub_data = np.array(sub_data)

    len_sub = len(sub_data)
    sub_dom = [0] * len_sub
    sub_pg = [0] * len_sub
    warn = True

    for e in range(0, len_sub):
        record_all_i = sub_data[e]
        if sum(record_all_i) != 100 and warn:
            print('Warning: Substrate data is given in percentage. However, it does not sum to 100% \n')
            warn = False
        # let find the dominant
        # we cannot use argmax as we need all maximum value, not only the first
        inds = list(np.argwhere(record_all_i == np.max(record_all_i)).flatten())
        if len(inds) > 1:
            # if we have the same percentage for two dominant we send back the function to the GUI to ask the
            # user. It is called again with the arg dominant_case
            if dominant_case == 0:
                return [-99], [-99]
            elif dominant_case == 1:
                sub_dom[e] = inds[-1] + 1
            elif dominant_case == -1:
                # sub_dom[e] = int(attribute_name_all[inds[0]][0][1])
                sub_dom[e] = inds[0] + 1
        else:
            sub_dom[e] = inds[0] + 1
        # let find the coarser (the last one not equal to zero)
        ind = np.where(record_all_i[record_all_i != 0])[0]
        if len(ind) > 1:
            sub_pg[e] = ind[-1] + 1
        elif ind:  # just a float
            sub_pg[e] = ind + 1
        else:  # no zeros
            sub_pg[e] = len(record_all_i)
        # cas des dalles
        if sub_pg[e] == 8:
            sub_pg[e] = sub_dom[e]

    return sub_dom, sub_pg


def load_sub_txt(filename, path, sub_mapping_method, sub_classification_code, sub_classification_method, sub_epsg_code,
                 path_shp='.', queue=[], dominant_case=0):
    """
    A function to load the substrate in form of a text file. The text file must have 4 columns x,y coordinate and
    coarser substrate type, dominant substrate type. It is transform to a grid using a voronoi
    transformation. There is one line of header (free texte).

    The voronoi transformation might look strange as it is often bigger than the original point. However, this is
    just the mathematical result.

    At the end of this fnuction, the resulting grid is exported in a shapefile form.

    :param filename: the name of the shapefile
    :param path: the path where the shapefile is
    :param sub_classification_code: the type of code used to define the substrate (string)
    :param path_shp: the path where to save the shapefile (usually the input folder)
    :return: grid in form of list of coordinate and connectivity table (two list)
             and an array with substrate type and (x,y,sub) of the orginal data
    """

    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The txt file " + filename + " does not exist.\n")
        return False
    # read
    with open(file, 'rt') as f:
        data = f.read()

    # neglect the first line as it is the header
    ind1 = data.find('\n')
    if ind1 == -1:
        print('Error: Could not find more than one line in the substrate input file. Check format \n')

    sub_end_info_habby_index = 4
    sub_header_index = 5

    # header
    header = data.split("\n")[sub_end_info_habby_index].split("\t")[2:]
    fake_field = [None] * len(header)  # fake fields like shapefile
    header = list(zip(header, fake_field))
    [attribute_type, attribute_name] = get_useful_attribute(header)

    data = data.split("\n")[sub_header_index:]

    if attribute_type == -99:
        print('Error: The substate data not recognized.\n')
        return

    if not attribute_type == sub_classification_method:
        print("Error: The sub classification code don't match headers.\n")
        return

    if sub_classification_method == 'coarser-dominant':
        sub_class_number = 2
    if sub_classification_method == 'percentage' and sub_classification_code == "Cemagref":
        sub_class_number = 8
    if sub_classification_method == 'percentage' and sub_classification_code == "Sandre":
        sub_class_number = 12

    x = []
    y = []
    sub_array = [[] for i in range(sub_class_number)]

    for line in data:
        try:
            line_list = line.split()
            x.append(float(line_list[0]))
            y.append(float(line_list[1]))
        except TypeError:
            print("Error: Coordinates (x,y) could not be read as float. Check format of the file " + filename + '.\n')
            return False
        for i in range(sub_class_number):
            index = i + 2
            try:
                sub_array[i].append(int(line_list[index]))
            except TypeError:
                print("Error: Substrate data could not be read as integer. Check format of the file " + filename + '.\n')
                return False

    # Coord
    point_in = np.vstack((np.array(x), np.array(y))).T

    # translation ovtherwise numerical problems some voronoi cells may content several points
    min_x = min([pt[0] for pt in point_in])
    min_y = min([pt[1] for pt in point_in])
    for dataelement in point_in:
        dataelement[0] = dataelement[0] - min_x
        dataelement[1] = dataelement[1] - min_y

    # voronoi
    vor = Voronoi(point_in, qhull_options="Qt")  #

    # remove translation
    for dataelement in vor.vertices:
        dataelement[0] = dataelement[0] + min_x
        dataelement[1] = dataelement[1] + min_y
    for dataelement in vor.points:
        dataelement[0] = dataelement[0] + min_x
        dataelement[1] = dataelement[1] + min_y
    for dataelement in point_in:
        dataelement[0] = dataelement[0] + min_x
        dataelement[1] = dataelement[1] + min_y

    # voronoi_finite_polygons_2d (all points)
    regions, vertices = voronoi_finite_polygons_2d(vor, 200)

    # create extent from points
    rect_extent = point_in[:, 0].min(), point_in[:, 1].min(), point_in[:, 0].max(), point_in[:, 1].max()

    # clip from point extent + 200m
    regions, vertices = clip_polygons_from_rect(regions, vertices, rect_extent)

    # convex_hull buffer to cut polygons
    # list_points = [Point(i) for i in point_in]
    # convex_hull = MultiPoint(list_points).convex_hull.buffer(200)
    #
    # # for each polyg voronoi
    # list_polyg = []
    # for region in regions:
    #     polygon = vertices[region]
    #     shape = list(polygon.shape)
    #     shape[0] += 1
    #     list_polyg.append(Polygon(np.append(polygon, polygon[0]).reshape(*shape)).intersection(convex_hull))
    #
    # # find one sub data by polyg
    # if len(list_polyg) == 0:
    #     print('Error the substrate does not create a meangiful grid. Please add more substrate points. \n')
    #     return False
    #
    # sub_array2 = [np.zeros(len(list_polyg), ) for i in range(sub_class_number)]
    #
    # for e in range(0, len(list_polyg)):
    #     polygon = list_polyg[e]
    #     centerx = np.float64(polygon.centroid.x)
    #     centery = np.float64(polygon.centroid.y)
    #     nearest_ind = np.argmin(np.sqrt((x - centerx) ** 2 + (y - centery) ** 2))
    #     for k in range(sub_class_number):
    #         sub_array2[k][e] = sub_array[k][nearest_ind]

    sub_array2 = [np.zeros(len(regions), ) for i in range(sub_class_number)]


    # export sub initial voronoi in a shapefile
    w = shapefile.Writer(shapefile.POLYGON)
    w.autoBalance = 1

    if sub_classification_method == 'coarser-dominant':
        w.field('coarser', 'N', 10, 0)
        w.field('dom', 'N', 10, 0)
    if sub_classification_method == 'percentage':
        for i in range(sub_class_number):
            w.field('S' + str(i + 1), 'N', 10, 0)

    #for i, polygon in enumerate(list_polyg):  # for each polygon
    for i, region in enumerate(regions):  # for each polygon
        #coord_list = list(polygon.exterior.coords)
        coord_list = vertices[region].tolist()
        w.poly(parts=[coord_list])  # the double [[]] is important or it bugs, but why?
        for k in range(sub_class_number):
            sub_array2[k][i] = sub_array[k][i]
        data_here = [item[i] for item in sub_array2]
        w.record(*data_here)

    # filename output
    name, ext = os.path.splitext(filename)
    sub_filename_voronoi_shp = name + '_voronoi' + '.shp'
    sub_filename_voronoi_shp_path = os.path.join(path_shp, sub_filename_voronoi_shp)
    w.save(sub_filename_voronoi_shp_path)
    # write .prj
    if sub_epsg_code != "unknown":
        try:
            string_prj = get_prj_from_epsg_web(int(sub_epsg_code))
            open(os.path.join(path_shp, os.path.splitext(sub_filename_voronoi_shp)[0]) + ".prj", "w").write(string_prj)
        except:
            print("Warning : Can't write .prj from EPSG code :", sub_epsg_code)
    return sub_filename_voronoi_shp  # xy, ikle, sub_dom2, sub_pg2, x, y, sub_dom, sub_pg


def modify_grid_if_concave(ikle, point_all, sub_pg, sub_dom):
    """
    This function check if the grid in entry is composed of convex cell. Indeed, it is possible to have concave
    cells in the substrate grid. However, this is unpractical when the hydrological grid is merged with the subtrate
    grid. Hence, we find here the concave cells. These cells are then modified using the triangle module.

    The algotithm is based on the idea that when you have a convex polygon you turn always in the same direction.
    When you have a concave polygon sometime you will turn left, sometime you will turn right. To check this,
    we can take the determinant betwen each vector which compose the cells and check if they have the same sign.
    Triangle are always convex.

    :param ikle: the connectivity table of the grid (one reach, one time step as substrate grid is constant)
    :param point_all: the point of the grid
    :param sub_pg: the coarser substrate, one data by cell
    :param sub_dom: the dominant subtrate, one data by cell
    :return: ikle, point_all with only convexe cells
    """

    point_alla = np.array(point_all)

    to_delete = []
    for ic, c in enumerate(ikle):
        concave = False
        lenc = len(c)
        sign_old = 0
        if lenc > 3:  # triangle are convex
            v00 = point_alla[c[1]] - point_alla[c[0]]
            v0 = v00
            for ind in range(0, lenc):
                # find vector
                if ind < lenc - 2:
                    v1 = point_alla[c[ind + 2]] - point_alla[c[ind + 1]]
                elif ind == lenc - 2:
                    v1 = point_alla[c[0]] - point_alla[c[ind + 1]]
                elif ind == lenc - 1:
                    v1 = v00
                # calulate deteminant (x0y1 - x1y0)
                det = v0[0] * v1[1] - v1[0] * v0[1]
                # check sign
                if ind == 0:
                    sign_old = np.sign(det)
                else:
                    sign = np.sign(det)
                    if sign != sign_old:
                        concave = True
                    break
                v0 = v1

        # if concave, correct the substrate grid
        if concave:
            to_delete.append(ic)
            # create triangle intput
            point_cell = np.zeros((lenc, 2))
            seg_cell = np.zeros((lenc, 2))
            for ind in range(0, lenc):
                point_cell[ind] = point_all[c[ind]]
                if ind < lenc - 1:
                    seg_cell[ind] = [ind, ind + 1]
                else:
                    seg_cell[ind] = [ind, 0]
            # triangulate
            try:
                dict_point = dict(vertices=point_cell, segments=seg_cell)
                grid_dict = tr.triangulate(dict_point, 'p')
            except:
                # to be done: create a second threat so that the error management will function
                print('Triangulation failed')
                return

            try:
                ikle_new = grid_dict['triangles']
                point_new = grid_dict['vertices']
                # add this triagulation to the ikle
                ikle.extend(list(np.array(ikle_new) + len(point_all)))
                point_all.extend(point_new)
                for m in range(0, len(ikle_new)):
                    sub_pg.append(sub_pg[ic])
                    sub_dom.append(sub_dom[ic])
            except KeyError:
                # in case triangulation was not ok
                print('Warning: A concave element of the substrate grid could not be corrected \n')

    # remove element
    if len(to_delete) > 0:
        for d in reversed(to_delete):  # to_delete is ordered
            del ikle[d]
        sub_pg = np.delete(sub_pg, to_delete)
        sub_dom = np.delete(sub_dom, to_delete)

    return ikle, point_all, sub_pg, sub_dom


def create_dummy_substrate_from_hydro(h5name, path, new_name, code_type, attribute_type, nb_point=200, path_out='.'):
    """
    This function takes an hydrological hdf5 as inputs and create a shapefile of substrate and a text file of substrate
    which can be used as input for habby. The substrate data is random. So it is mainly useful to test an hydrological
    input.

    The created shape file is rectangular with a size based on min/max of the hydrological coordinates. The substrate
    grid is not the same as the hydrological grids (which is good to test the programm). In addition, one side of the shp
    is smaller than the hydrological grid to test the 'default substrate' option (which is used if the substrate
    shapefile is not big enough).

    :param h5name: the name of the hydrological hdf5 file
    :param path: the path to this file
    :param new_name: the name of the create shape file wihtout the shp (string)
    :param code_type: the code type for the substrate (Sandre, Cemagref, Const_cemagref, or EDF). All subtrate value
           to 4 for Const_cemagref.
    :param attribute_type: if the substrate is given in the type coarser/dominant/..(0) or in percenctage (1)
    :param nb_point: the number of point needed (more points results in smaller substrate form)
    :param path_out: the path where to save the new substrate shape
    """

    # load hydro hdf5
    [ikle_all_t, point_all, inter_vel_all, inter_height_all] = hdf5_mod.load_hdf5_hyd_and_merge(h5name, path)

    # get min max of coord
    minx = 1e40
    maxx = -1e40
    miny = 1e40
    maxy = -1e40
    point_all = np.array(point_all[0])  # full profile
    for r in range(0, len(point_all)):
        maxx_here = max(point_all[r][:, 0])
        minx_here = min(point_all[r][:, 0])
        maxy_here = max(point_all[r][:, 1])
        miny_here = min(point_all[r][:, 1])
        if maxx_here > maxx:
            maxx = maxx_here
        if minx_here < minx:
            minx = minx_here
        if maxy_here > maxy:
            maxy = maxy_here
        if miny_here < miny:
            miny = miny_here

    # to test the case where substrate shp does not cover the whole reach
    # miny *= 0.90

    # get random coordinate
    point_new = []
    for p in range(0, nb_point):
        x = uniform(minx, maxx)
        y = uniform(miny, maxy)
        point_new.append([x, y])

    # get a new substrate grid
    dict_point = dict(vertices=point_new)
    grid_sub = tr.triangulate(dict_point)
    try:
        ikle_r = list(grid_sub['triangles'])
        point_all_r = list(grid_sub['vertices'])
    except KeyError:
        print('Warning: Reach with an empty grid.\n')
        return

    # gett random substrate data for shapefile
    data_sub = []
    data_sub_txt = []
    for i in range(0, len(ikle_r)):
        if attribute_type == 0:
            if code_type == 'EDF' or code_type == 'Cemagref':
                s1 = randrange(1, 8)
                s2 = randrange(1, 8)
            elif code_type == 'Sandre':
                s1 = randrange(1, 12)
                s2 = randrange(1, 12)
            elif code_type == 'Const_cemagref':
                s1 = 4
                s2 = 4
            else:
                print('code not recognized')
                return
            data_sub.append([s1, s2])  # coarser, dominant
            if i < len(point_new):
                data_sub_txt.append([s1, s2])
        elif attribute_type == 1:
            data_sub_here = []
            if code_type == 'EDF' or code_type == 'Cemagref':
                for j in range(0, 8):
                    sx = randrange(1, 100)
                    data_sub_here.append(sx)
            elif code_type == 'Sandre':
                for j in range(0, 12):
                    sx = randrange(1, 100)
                    data_sub_here.append(sx)
            else:
                print('code not recognized')
                return
            data_sub.append(data_sub_here)
        else:
            print('Error: the attribute type should 1 or 0')
            return

    # pass the substrate data to shapefile
    w = shapefile.Writer(shapefile.POLYGON)
    if attribute_type == 0:
        w.field('PG', 'F', 10, 8)
        w.field('DM', 'F', 10, 8)
    elif attribute_type == 1:
        if code_type == 'EDF' or code_type == 'Cemagref':
            for j in range(1, 9):  # we want to start with S1 to get the corresponding class
                w.field('S' + str(j), 'F', 10, 8)
        elif code_type == 'Sandre':
            for j in range(1, 13):
                w.field('S' + str(j), 'F', 10, 8)

    for i in range(0, len(ikle_r)):
        p1 = list(point_all_r[ikle_r[i][0]])
        p2 = list(point_all_r[ikle_r[i][1]])
        p3 = list(point_all_r[ikle_r[i][2]])
        w.poly(parts=[[p1, p2, p3, p1]])  # the double [[]] is important or it bugs, but why?
    for i in range(0, len(ikle_r)):
        if attribute_type == 0:
            w.record(data_sub[i][0], data_sub[i][1])  # data_sub[i] does not work
        elif attribute_type == 1:
            if code_type == 'EDF' or code_type == 'Cemagref':
                w.record(data_sub[i][0], data_sub[i][1], data_sub[i][2], data_sub[i][3], data_sub[i][4], data_sub[i][5],
                         data_sub[i][6], data_sub[i][7])
            elif code_type == 'Sandre':
                w.record(data_sub[i][0], data_sub[i][1], data_sub[i][2], data_sub[i][3], data_sub[i][4], data_sub[i][5],
                         data_sub[i][6], data_sub[i][7], data_sub[i][8], data_sub[i][9], data_sub[i][10],
                         data_sub[i][11])
    w.autoBalance = 1
    w.save(os.path.join(path_out, new_name + '.shp'))

    # pass to text file
    if attribute_type == 0:
        data = np.hstack((np.array(point_new), np.array(data_sub_txt)))
        np.savetxt(os.path.join(path_out, new_name + '.txt'), data)


def clip_polygons_from_rect(polygon_regions, polygon_vertices, rect):
    # create rect_sides (clockwise)
    xMin = rect[0] - 200
    yMin = rect[1] - 200
    xMax = rect[2] + 200
    yMax = rect[3] + 200
    left_side = [[xMin, yMin], [xMin, yMax]]
    top_side = [[xMin, yMax], [xMax, yMax]]
    right_side = [[xMax, yMax], [xMax, yMin]]
    bottom_side = [[xMax, yMin], [xMin, yMin]]
    extent = [xMin, yMin, xMax, yMax]
    rect_sides = np.stack([left_side, top_side, right_side, bottom_side])

    # # init
    # shapefile_type = 5  # polygon
    # # write shapefile
    # out_shp_abs_path = os.path.join(r"C:\temp_out", "create_polygon_shp_from_data.shp")
    # w = shapefile.Writer(shapefile_type)
    # w.autoBalance = 1
    # w.fields = [('empty', 'N', 10, 0)]
    # w.poly(parts=rect_sides.tolist())
    # aa = list([0.0])
    # w.record(*aa)
    # w.save(out_shp_abs_path)

    # for each polygon
    for i, region in enumerate(polygon_regions):  # for each polygon
        # coord_list = list(polygon.exterior.coords)
        coord_array = polygon_vertices[region]
        first_done = False
        # for each segment
        for j in range(len(coord_array)):
            segment = np.stack([coord_array[j], coord_array[j - 1]])
            # segment outside of extent
            if not rectContains(extent, segment[0]) and not rectContains(extent, segment[1]):
                print("segment outside of extent")
                polygon_vertices[region[j]] = polygon_vertices[region[j - 1]]
            # segment inside extent
            else:
                if not first_done:
                    # for each side of rectangle
                    for rect_side in rect_sides:
                        intersect, point = manage_grid_mod.intersection_seg(rect_side[0], rect_side[1], segment[0], segment[1])
                        if intersect:
                            print("intersect")
                            polygon_vertices[region[j]] = np.array(point[0])
                            first_done = True


    return polygon_regions, polygon_vertices


def rectContains(rect, pt):
    logic = rect[0] < pt[0] < rect[0]+rect[2] and rect[1] < pt[1] < rect[1]+rect[3]
    return logic


def voronoi_finite_polygons_2d(vor, radius=None):
    """
    Reconstruct infinite voronoi regions in a 2D diagram to finite
    regions.
    source : https://stackoverflow.com/questions/20515554/colorize-voronoi-diagram/20678647#20678647
    Parameters
    ----------
    vor : Voronoi
        Input diagram
    radius : float, optional
        Distance to 'points at infinity'.

    Returns
    -------
    regions : list of tuples
        Indices of vertices in each revised Voronoi regions.
    vertices : list of tuples
        Coordinates for revised Voronoi vertices. Same as coordinates
        of input vertices, with 'points at infinity' appended to the
        end.

    """

    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = vor.points.ptp().max()

    # Construct a map containing all ridges for a given point
    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    # Reconstruct infinite regions
    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]

        if all(v >= 0 for v in vertices):
            # finite region
            new_regions.append(vertices)
            continue

        # reconstruct a non-finite region
        ridges = all_ridges[p1]
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                # finite ridge: already in the region
                continue

            # Compute the missing endpoint of an infinite ridge

            t = vor.points[p2] - vor.points[p1]  # tangent
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])  # normal

            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius

            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        # sort region counterclockwise
        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:,1] - c[1], vs[:,0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]

        # finish
        new_regions.append(new_region.tolist())

    return new_regions, np.asarray(new_vertices)


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
    # [ikle_both, point_all_both, sub_data1, subdata2,  vel, height] = merge_grid_hydro_sub(hdf5_name_hyd, hdf5_name_sub, -1)
    # fig_merge_grid(point_all_both[0], ikle_both[0], path1)
    # plt.show()

    # test create dummy substrate
    # path = r'D:\Diane_work\dummy_folder\DefaultProj'
    # fileh5 = 'Hydro_RUBAR2D_BS15a607_02_2017_at_15_50_13.hab'
    # create_dummy_substrate_from_hydro(fileh5, path, 'dummy_hydro_substrate2', 'Sandre', 0)


if __name__ == '__main__':
    main()
