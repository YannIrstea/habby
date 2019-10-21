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
import os
import numpy as np
from scipy.spatial import Voronoi
import triangle as tr
from json import loads as jsonload
from PyQt5.QtWidgets import QMessageBox
from osgeo import osr
from osgeo import ogr

from src import hdf5_mod
from src import manage_grid_mod
from src.dev_tools import profileit


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
    warnings_list = []
    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        warnings_list.append("Error: The txt file " + filename + " does not exist.")
        queue.put(warnings_list)
        return False

    if sub_classification_method == 'coarser-dominant':
        sub_class_number = 2
    if sub_classification_method == 'percentage' and sub_classification_code == "Cemagref":
        sub_class_number = 8
    if sub_classification_method == 'percentage' and sub_classification_code == "Sandre":
        sub_class_number = 12

    # input txt
    if os.path.splitext(filename)[1] == ".txt":
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
        [attribute_type, _] = get_useful_attribute(header)

        data = data.split("\n")[sub_header_index:]

        if attribute_type == -99:
            print('Error: The substrate data not recognized.\n')
            return

        if not attribute_type == sub_classification_method:
            print("Error: The sub classification code don't match headers.\n")
            return

        x = []
        y = []
        sub_array = [[] for _ in range(sub_class_number)]

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

        """ save substrate_point_shp """
        name, ext = os.path.splitext(filename)
        name = name + "_from_txt"
        sub_filename_voronoi_shp = name + '.shp'
        sub_filename_voronoi_shp_path = os.path.join(path_shp, sub_filename_voronoi_shp)
        driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
        ds = driver.CreateDataSource(sub_filename_voronoi_shp_path)
        crs = osr.SpatialReference()
        if sub_epsg_code != "unknown":
            try:
                crs.ImportFromEPSG(int(sub_epsg_code))
            except:
                print("Warning : Can't write .prj from EPSG code :", sub_epsg_code)

        if not crs.ExportToWkt():  # '' == crs unknown
            layer = ds.CreateLayer(name=name, geom_type=ogr.wkbPoint)
        else:  # crs known
            layer = ds.CreateLayer(name=name, srs=crs, geom_type=ogr.wkbPoint)

        if sub_classification_method == 'coarser-dominant':
            layer.CreateField(ogr.FieldDefn('coarser', ogr.OFTInteger))  # Add one attribute
            layer.CreateField(ogr.FieldDefn('dominant', ogr.OFTInteger))  # Add one attribute
        if sub_classification_method == 'percentage':
            for i in range(sub_class_number):
                layer.CreateField(ogr.FieldDefn('S' + str(i + 1), ogr.OFTInteger))  # Add one attribute

        defn = layer.GetLayerDefn()
        field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]

        layer.StartTransaction()  # faster
        for i in range(point_in.shape[0]):
            # create geom
            point_geom = ogr.Geometry(ogr.wkbPoint)  # Create ring
            point_geom.AddPoint(*point_in[i])

            # Create a new feature
            feat = ogr.Feature(defn)
            for field_num, field in enumerate(field_names):
                feat.SetField(field, sub_array[field_num][i])
            # set geometry
            feat.SetGeometry(point_geom)
            # create
            layer.CreateFeature(feat)

        # Save and close everything
        layer.CommitTransaction()  # faster

        # close file
        ds.Destroy()

    # input shp
    if os.path.splitext(filename)[1] == ".shp":
        name, ext = os.path.splitext(filename)
        # read source shapefile
        driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
        ds = driver.Open(file, 0)  # 0 means read-only. 1 means writeable.
        layer = ds.GetLayer(0)  # one layer in shapefile
        layer_defn = layer.GetLayerDefn()

        # get geom type
        if layer.GetGeomType() != 1:  # point type
            # print("file is not point type")
            return False

        # fields = sf.fields[1:]
        header_list = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]

        # Extract list of points and sub values from shp
        point_in = np.empty(shape=(len(layer), 2), dtype=np.float)
        x = []
        y = []
        sub_array = [[] for _ in range(sub_class_number)]
        for feature_ind, feature in enumerate(layer):
            for j, sub_type in enumerate(header_list):
                sub_array[j].append(feature.GetField(j))
            shape_geom = feature.geometry()
            XY = shape_geom.GetPoints()[0]
            point_in[feature_ind] = XY
            x.append(XY[0])
            y.append(XY[1])

    """ all input check """
    # check if duplicate tuple coord presence
    u, c = np.unique(point_in, return_counts=True, axis=0)
    dup = u[c > 1]
    if len(dup) > 0:
        warnings_list.append("Error: The substrate data has duplicates points coordinates :" + str(dup) + ". Please remove them and try again.")
        queue.put(warnings_list)
        return False

    """ voronoi """
    # translation ovtherwise numerical problems some voronoi cells may content several points
    translation_value = np.array([point_in[:, 0].min(), point_in[:, 1].min()])
    point_voronoi = point_in - translation_value

    # voronoi
    vor = Voronoi(point_voronoi, qhull_options="Qt")

    # remove translation
    vor.vertices = vor.vertices + translation_value
    for point_element_num in range(len(vor.points)):
        vor.points[point_element_num] = vor.points[point_element_num] + translation_value

    # voronoi_finite_polygons_2d (all points)
    regions, vertices = voronoi_finite_polygons_2d(vor, 200)

    """ voronoi intersection with buffer """
    # convex_hull buffer to cut polygons (ogr)
    multipoint_geom = ogr.Geometry(ogr.wkbMultiPoint)
    for point_coord in point_in:
        point_geom = ogr.Geometry(ogr.wkbPoint)
        point_geom.AddPoint(*point_coord)
        multipoint_geom.AddGeometry(point_geom)
    convex_hull = multipoint_geom.ConvexHull().Buffer(200)

    # for each polyg voronoi
    list_polyg = []
    intersect_buffer = False
    for region in regions:
        polygon = vertices[region]
        shape = list(polygon.shape)
        shape[0] += 1
        # ogr
        ring = ogr.Geometry(ogr.wkbLinearRing)  # Create ring
        for polyg_point_ind in list(range(len(polygon))) + [0]:
            ring.AddPoint(*polygon[polyg_point_ind])
        poly = ogr.Geometry(ogr.wkbPolygon)  # Create polygon
        poly.AddGeometry(ring)
        if poly.Intersect(convex_hull):
            list_polyg.append(poly.Intersection(convex_hull))
            intersect_buffer = True
        else:
            list_polyg.append(poly)

    # if not intersect_buffer:
    #     warnings_list.append('Error: Voronoi polygons buffer intersection failed')
    #     queue.put(warnings_list)
    #     return False

    # find one sub data by polyg
    if len(list_polyg) == 0:
        warnings_list.append('Error: The substrate does not create a meangiful grid. Please add more substrate points.')
        queue.put(warnings_list)
        return False

    sub_array2 = [np.zeros(len(list_polyg), ) for _ in range(sub_class_number)]

    for e in range(0, len(list_polyg)):
        polygon = list_polyg[e]
        centerx = np.float64(polygon.Centroid().GetX())
        centery = np.float64(polygon.Centroid().GetY())
        nearest_ind = np.argmin(np.sqrt((x - centerx) ** 2 + (y - centery) ** 2))
        for k in range(sub_class_number):
            sub_array2[k][e] = sub_array[k][nearest_ind]

    sub_array2 = [np.zeros(len(regions), ) for i in range(sub_class_number)]

    """ voronoi shapefile export """
    # filename output
    sub_filename_voronoi_shp = name + '_voronoi' + '.shp'
    sub_filename_voronoi_shp_path = os.path.join(path_shp, sub_filename_voronoi_shp)
    driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
    ds = driver.CreateDataSource(sub_filename_voronoi_shp_path)
    crs = osr.SpatialReference()
    if sub_epsg_code != "unknown":
        crs.ImportFromEPSG(int(sub_epsg_code))

    if not crs.ExportToWkt():  # '' == crs unknown
        layer = ds.CreateLayer(name=name + '_voronoi', geom_type=ogr.wkbPolygon)
    else:  # crs known
        layer = ds.CreateLayer(name=name + '_voronoi', srs=crs, geom_type=ogr.wkbPolygon)

    if sub_classification_method == 'coarser-dominant':
        layer.CreateField(ogr.FieldDefn('coarser', ogr.OFTInteger))  # Add one attribute
        layer.CreateField(ogr.FieldDefn('dominant', ogr.OFTInteger))  # Add one attribute
    if sub_classification_method == 'percentage':
        for i in range(sub_class_number):
            layer.CreateField(ogr.FieldDefn('S' + str(i + 1), ogr.OFTInteger))  # Add one attribute

    defn = layer.GetLayerDefn()
    field_names = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]

    layer.StartTransaction()  # faster
    for i, polygon in enumerate(list_polyg):  # for each polygon with buffer
        polygon.SetCoordinateDimension(2)
        # coord_list = polygon.GetGeometryRef(0).GetPoints()
        # ring = ogr.Geometry(ogr.wkbLinearRing)
        # for point in coord_list:
        #     ring.AddPoint(*point)
        # # Create polygon
        # poly = ogr.Geometry(ogr.wkbPolygon)
        # poly.AddGeometry(ring)
        # Create a new feature
        feat = ogr.Feature(defn)
        for k in range(sub_class_number):
            sub_array2[k][i] = sub_array[k][i]
        data_here = [item[i] for item in sub_array2]
        for field_num, field in enumerate(field_names):
            feat.SetField(field, data_here[field_num])
        # set geometry
        #feat.SetGeometry(poly)
        feat.SetGeometry(polygon)
        # create
        layer.CreateFeature(feat)

    # Save and close everything
    layer.CommitTransaction()  # faster

    # close file
    ds.Destroy()

    queue.put(sub_filename_voronoi_shp)


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
    driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
    ds = driver.Open(os.path.join(path_file, filename), 0)  # 0 means read-only. 1 means writeable.
    layer = ds.GetLayer(0)  # one layer in shapefile
    layer_defn = layer.GetLayerDefn()

    header_list = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
    sub_array = np.empty(shape=(len(layer), len(header_list)), dtype=np.int)
    for feature_ind, feature in enumerate(layer):
        sub_array[feature_ind] = [feature.GetField(j) for j in header_list]

    # check data validity
    data_validity, sub_description_system = data_substrate_validity(header_list,
                                                                    sub_array,
                                                                    sub_mapping_method,
                                                                    sub_classification_code)

    sub_description_system["sub_filename_source"] = filename
    sub_description_system["sub_class_number"] = str(len(sub_array[0]))
    sub_description_system["sub_default_values"] = default_values
    sub_description_system["sub_reach_number"] = "1"
    sub_description_system["sub_reach_list"] = "unknown"
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
            #sf = open_shp(filename, os.path.join(path_prj, "input"))
            driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
            ds = driver.Open(os.path.join(path_prj, "input", filename), 0)  # 0 means read-only. 1 means writeable.
            layer = ds.GetLayer(0)  # one layer in shapefile
            layer_defn = layer.GetLayerDefn()

            # get point coordinates and connectivity table in two lists
            sub_array = np.empty(shape=(len(layer), len(header_list)), dtype=np.int)
            for feature_ind, feature in enumerate(layer):
                sub_array[feature_ind] = [feature.GetField(j) for j in header_list]
                shape_geom = feature.geometry()
                geom_part = shape_geom.GetGeometryRef(0)  # only one if triangular mesh
                p_all = geom_part.GetPoints()
                tin_i = []
                for j in range(0, len(p_all) - 1):  # last point of shapefile is the first point
                    try:
                        tin_i.append(int(xy.index(p_all[j])))
                    except ValueError:
                        tin_i.append(int(len(xy)))
                        xy.append(p_all[j])
                tin.append(tin_i)

            # get data
            data_2d = dict()
            data_2d["tin"] = [np.array(tin)]
            data_2d["xy"] = [np.array(xy)]
            data_2d["sub"] = [sub_array]
            data_2d["nb_unit"] = 1
            data_2d["nb_reach"] = 1

            # save hdf5
            hdf5 = hdf5_mod.Hdf5Management(path_prj, name_hdf5)
            hdf5.create_hdf5_sub(sub_description_system, data_2d)

    queue.put(mystdout)


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
    shapefile_type = 3  # polygon in ogr

    in_shp_abs_path = os.path.join(path_file, filename)

    # read source shapefile
    driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
    ds = driver.Open(in_shp_abs_path, 0)  # 0 means read-only. 1 means writeable.
    layer = ds.GetLayer(0)  # one layer in shapefile
    layer_defn = layer.GetLayerDefn()

    # get geom type
    if layer.GetGeomType() != shapefile_type:
        print("file is not polygon type")
        return False

    # fields = sf.fields[1:]
    header_list = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]

    # get EPSG
    crs = layer.GetSpatialRef()

    # Extract list of points and segments from shp
    vertices_array = []  # point
    segments_array = []  # segment index or connectivity table
    holes_array = []
    inextpoint = 0
    records = np.empty(shape=(len(layer), len(header_list)), dtype=np.int)
    for feature_ind, feature in enumerate(layer):
        records[feature_ind] = [feature.GetField(j) for j in header_list]
        shape_geom = feature.geometry()
        shape_geom.SetCoordinateDimension(2)  # never z values
        if shape_geom.GetGeometryCount() > 1:  # polygon a trous
            # index_hole = list(shapes[i].parts) + [len(shapes[i].points)]
            index_hole = [0]
            all_coord = []
            for part_num, part in enumerate(range(shape_geom.GetGeometryCount())):
                geom_part = shape_geom.GetGeometryRef(part_num)
                coord_part = geom_part.GetPoints()
                all_coord.extend(coord_part)
                if part_num == shape_geom.GetGeometryCount() - 1:  # last
                    index_hole.append(index_hole[-1] + len(coord_part))
                else:
                    index_hole.append(len(coord_part))

            new_points = []
            lnbptspolys = []
            for j in range(len(index_hole) - 1):
                new_points.extend(all_coord[index_hole[j]:index_hole[j + 1] - 1])
                lnbptspolys.append(index_hole[j + 1] - 1 - index_hole[j])
                if j > 0:  # hole presence : creating a single point inside the hole using triangulation
                    vertices_hole = np.array(all_coord[index_hole[j]:index_hole[j + 1] - 1])
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
            new_points = shape_geom.GetGeometryRef(0).GetPoints()
            lnbptspolys = [len(new_points)]
        # add
        vertices_array.extend(new_points)  # add the points to list
        for j in range(len(lnbptspolys)):  # add the segments to list
            for k in range(lnbptspolys[j]):
                segments_array.append([k % lnbptspolys[j] + inextpoint, (k + 1) % lnbptspolys[j] + inextpoint])
            inextpoint += lnbptspolys[j]

    # Remove duplicates
    vertices_array2, segments_array2, holes_array = remove_duplicates_points_to_triangulate(vertices_array,
                                                                                 segments_array,
                                                                                 holes_array)

    # check if duplicates
    if len(np.unique(vertices_array2, axis=0)) != len(vertices_array2):
        print("Error: Duplicates points presence before triangulation. Please remove them.")
        return False

    # triangulate on polygon (if we use regions)
    if holes_array.size == 0:
        polygon_from_shp = dict(vertices=vertices_array2,
                                segments=segments_array2)
    else:
        polygon_from_shp = dict(vertices=vertices_array2,
                                segments=segments_array2,
                                holes=holes_array)
    polygon_triangle = tr.triangulate(polygon_from_shp, "p")  # triangulation
    #tr.compare(plt, polygon_from_shp, polygon_triangle)

    # get geometry and attributes of triangles
    triangle_geom_list = []
    triangle_records_list = np.empty(shape=(len(polygon_triangle["triangles"]), len(header_list)), dtype=np.int)
    for i in range(len(polygon_triangle["triangles"])):
        # triangle coords
        p1 = polygon_triangle["vertices"][polygon_triangle["triangles"][i][0]]
        p2 = polygon_triangle["vertices"][polygon_triangle["triangles"][i][1]]
        p3 = polygon_triangle["vertices"][polygon_triangle["triangles"][i][2]]
        triangle_geom_list.append([p1, p2, p3])
        # triangle centroid
        xmean = (p1[0] + p2[0] + p3[0]) / 3
        ymean = (p1[1] + p2[1] + p3[1]) / 3
        polyg_center = (xmean, ymean)
        layer.ResetReading()  # reset the read position to the start
        # if center in polygon: get attributes
        for j, feature in enumerate(layer):
            shape_geom = feature.geometry()
            geom_part = shape_geom.GetGeometryRef(0)  # 0 == outline
            point_list = geom_part.GetPoints()[:-1]
            if point_inside_polygon(polyg_center[0], polyg_center[1], point_list):
                triangle_records_list[i] = records[j]

    # close file
    ds.Destroy()

    # write triangulate shapefile
    out_shp_basename = os.path.splitext(filename)[0]
    out_shp_filename = out_shp_basename + "_triangulated.shp"
    out_shp_path = os.path.join(path_prj, "input")
    out_shp_abs_path = os.path.join(out_shp_path, out_shp_filename)
    ds = driver.CreateDataSource(out_shp_abs_path)
    if not crs:  # '' == crs unknown
        layer = ds.CreateLayer(name=out_shp_basename + "_triangulated", geom_type=ogr.wkbPolygon)
    else:  # crs known
        layer = ds.CreateLayer(name=out_shp_basename + "_triangulated", srs=crs, geom_type=ogr.wkbPolygon)

    for field in header_list:
        layer.CreateField(ogr.FieldDefn(field, ogr.OFTInteger))  # Add one attribute

    defn = layer.GetLayerDefn()
    layer.StartTransaction()  # faster
    for i in range(len(triangle_geom_list)):
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for point_ind in [0, 1, 2, 0]:
            ring.AddPoint(triangle_geom_list[i][point_ind][0], triangle_geom_list[i][point_ind][1])
        # Create polygon
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        # Create a new feature
        feat = ogr.Feature(defn)
        for field_num, field in enumerate(header_list):
            feat.SetField(field, int(triangle_records_list[i][field_num]))
        # set geometry
        feat.SetGeometry(poly)
        # create
        layer.CreateFeature(feat)

    # Save and close everything
    layer.CommitTransaction()  # faster

    # close file
    ds.Destroy()

    return True


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
            attribute_name[1] = "dominant"
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


def remove_duplicates_points_to_triangulate(vertices_array, segments_array, holes_array):
    inextpoint = len(vertices_array)
    # AIM: for using triangle to transform polygons into triangles it is necessary to avoid any duplicate point
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
    return vertices_array2, segments_array2, holes_array


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
        sub_dom = sub_array[header_list.index("dominant")]
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
        for e in range(0, len(sub_array)):  # for all features
            if sum(sub_array[e]) != 100:
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


def sandre_to_cemagref_array(records_sandre_array):
    """
    This function change the subtrate value array from sandre code to cemagref code
    :param records_sandre_array: all records sandre
    :return: records_cemagref_array: all records cemagref
    """
    sandre_cemagref = np.array([1,2,3,3,4,4,5,5,6,6,7,8])
    records_cemagref_array=sandre_cemagref[records_sandre_array-1]
    return records_cemagref_array


def sandre_to_cemagref_by_percentage_array(records_sandre_array):
    """
    This function change the subtrate data array in a percentage form from sandre code to cemagref code
    :param records_sandre_array: all records sandre
    :return: records_cemagref_array: all records cemagref
    """
    records_cemagref_array=np.empty((records_sandre_array.shape[0], 8), np.int)
    records_cemagref_array[:, (0, 1)] = records_sandre_array[:, (0, 1)]
    records_cemagref_array[:, 2] = records_sandre_array[:, 2]+records_sandre_array[:, 3]
    records_cemagref_array[:, 3] = records_sandre_array[:, 4] + records_sandre_array[:, 5]
    records_cemagref_array[:, 4] = records_sandre_array[:, 6] + records_sandre_array[:, 7]
    records_cemagref_array[:, 5] = records_sandre_array[:, 8] + records_sandre_array[:, 9]
    records_cemagref_array[:, (6, 7)] = records_sandre_array[:, (10, 11)]
    return records_cemagref_array


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


def pref_substrate_dominant_from_percentage_description(prefsub, c1):
    """
    aiming the calculation for each mesh of the substrate preferences for the dominant substrate (there can be several)

    :param prefsub: substrate preferences for each substrate class
    :param c1: np.array each line is for a given mesh the area percentage description for each substrate class
    :return: preferences for each mesh number of preferences equal to the number of meshes
    """
    b = np.amax(c1, axis=1).reshape(c1.shape[0], 1)
    e = (c1 == b) * 1
    return np.sum(e * prefsub, axis=1) / np.sum(e, axis=1)


def pref_substrate_coarser_from_percentage_description(prefsub, c1):
    """
    aiming the calculation for each mesh of the substrate preferences for the coarser substrate
    :param prefsub: substrate preferences for each substrate class
    :param c1: np.array each line is for a given mesh the area percentage description for each substrate class
    :return: preferences for each mesh number of preferences equal to the number of meshes
    """
    codsub = list(range(1, len(prefsub) + 1))
    return prefsub[np.amax((c1 != 0) * codsub, axis=1) - 1]

# prefsub=np.array([0.1,0.2,0.25,0.5,1,0.3,0.7,0.6])
# #la description du substrat par maille est sous forme de % pour ici les 8 classes substrat Cemagref
# c1=np.array([[ 8, 15,  12, 20, 11, 20,  0,  14],
#        [ 1, 10,  2, 11,  6, 34,  2, 34],
#        [15, 15,  15,  10, 10, 11, 12,  12],
#        [27,  4,  8,  8,  0,  2, 34, 17],
#        [34,  6,  4, 27,  2,  9, 14,  4],
#        [ 1, 16, 10, 11, 20, 29, 11,  2],
#        [26,  46,  5, 20,  3, 0,  0,  0],
#        [22,  19,  2, 19, 32,  6, 0,  0],
#        [ 8,  1, 24,  3, 22, 13, 25,  4],
#        [17,  7,  6, 11, 36,  7,  9,  7],
#        [ 9, 11, 26, 32,  3,  0,  0, 19]])
#


#vhdom=pref_substrate_dominant_from_percentage_description(prefsub,c1)
##>>> vhdom
##array([0.4       , 0.45      , 0.18333333, 0.7       , 0.1       ,
##       0.3       , 0.2       , 1.        , 0.7       , 1.        ,
##       0.5       ])
#vhcoarser=pref_substrate_coarser_from_percentage_description(prefsub,c1)
#array([0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 1. , 0.3, 0.6, 0.6, 0.6])

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
