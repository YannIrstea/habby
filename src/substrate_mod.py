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
from io import StringIO
from glob import glob
from shutil import copy as sh_copy
from shutil import rmtree
import numpy as np
import triangle as tr
from PyQt5.QtCore import QCoreApplication as qt_tr
from osgeo import ogr
from osgeo import osr
from osgeo.ogr import GetDriverByName
from osgeo.osr import SpatialReference
from scipy.spatial import Voronoi
import pandas as pd

from src import hdf5_mod
from src.tools_mod import polygon_type_values, point_type_values
from src.data_2d_mod import Data2d
from src.variable_unit_mod import HydraulicVariableUnitManagement


def load_sub(sub_description, progress_value, q=[], print_cmd=False, project_preferences={}):
    """
    :param sub_description: substrate description dict
    :param progress_value: progress value from multiprocessing
    :param q: Queue from multiprocessing
    :param print_cmd: If True will print the error and warning to the cmd. If False, send it to the GUI.
    :param project_preferences: project_preferences dict
    :return:
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    data_2d = None
    # prog
    progress_value.value = 5

    # security if point case
    sub_path_source = sub_description["sub_path_source"]
    sub_filename_source = sub_description["sub_filename_source"]

    # create input project folder
    input_project_folder = os.path.join(sub_description["path_prj"], "input", os.path.splitext(sub_filename_source)[0])
    if os.path.exists(input_project_folder):
        try:
            rmtree(input_project_folder)
            while os.path.exists(input_project_folder):  # check if it exists
                pass
        except PermissionError:
            print("Error: Can't remove " + os.path.splitext(sub_filename_source)[0] +
                  " folder in 'input' project folder, as it file(s) opened in another program.")
            q.put(mystdout)
            return

    # create folder
    os.mkdir(input_project_folder)

    # set extension if not done
    if os.path.splitext(sub_description["name_hdf5"])[-1] != ".sub":
        sub_description["name_hdf5"] = sub_description["name_hdf5"] + ".sub"

    # load specific sub
    if sub_description["sub_mapping_method"] == "constant":
        data_2d = load_sub_cst(sub_description, progress_value)
    elif sub_description["sub_mapping_method"] == "polygon":
        data_2d = load_sub_sig(sub_description, progress_value)
    elif sub_description["sub_mapping_method"] == "point":
        data_2d = load_sub_txt(sub_description, progress_value)

    data_2d.hvum = HydraulicVariableUnitManagement()
    data_2d.hvum.detect_variable_from_sub_description(sub_description)
    data_2d.rename_substrate_column_data()
    if sub_description["sub_mapping_method"] != "constant":
        data_2d.get_dimension()

    # security if point case
    sub_description["sub_path_source"] = sub_path_source
    sub_description["sub_filename_source"] = sub_filename_source

    hdf5 = hdf5_mod.Hdf5Management(sub_description["path_prj"],
                                   sub_description["name_hdf5"])
    hdf5.create_hdf5_sub(sub_description, data_2d)

    # prog
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_sub_txt(sub_description, progress_value):
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
    filename = sub_description["sub_filename_source"]
    blob, ext = os.path.splitext(filename)
    path = sub_description["sub_path_source"]
    sub_classification_code = sub_description["sub_classification_code"]
    sub_classification_method = sub_description["sub_classification_method"]
    path_prj = sub_description["path_prj"]
    path_shp = os.path.join(path_prj, "input", blob)
    sub_epsg_code = sub_description["sub_epsg_code"]

    file = os.path.join(path, filename)
    if not os.path.isfile(file):
        print("Error: The txt file " + filename + " does not exist.")
        return False

    if sub_classification_method == 'coarser-dominant':
        sub_class_number = 2
    if sub_classification_method == 'percentage' and sub_classification_code == "Cemagref":
        sub_class_number = 8
    if sub_classification_method == 'percentage' and sub_classification_code == "Sandre":
        sub_class_number = 12

    name, ext = os.path.splitext(filename)

    # input txt
    if ext == ".txt":
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

        """ save substrate_point """
        name, ext = os.path.splitext(filename)
        filename2 = name + "_triangulated"
        sub_filename_voronoi = filename2 + '.gpkg'
        sub_filename_voronoi_path = os.path.join(path_shp, sub_filename_voronoi)
        driver = ogr.GetDriverByName('GPKG')
        ds = driver.CreateDataSource(sub_filename_voronoi_path)
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

        # close file
        layer = None
        ds = None

    # input shp
    if ext == ".shp" or ext == ".gpkg":
        if ext == ".shp":
            driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
            ds = driver.Open(file, 0)  # 0 means read-only. 1 means writeable.
        elif ext == ".gpkg":
            driver = ogr.GetDriverByName('GPKG')  # GPKG
            ds = driver.Open(file, 0)  # 0 means read-only. 1 means writeable.

        layer = ds.GetLayer(0)  # one layer in shapefile
        layer_defn = layer.GetLayerDefn()

        # get geom type
        if layer.GetGeomType() not in point_type_values:  # point type
            print("file is not point type : ", layer.GetGeomType())
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

    # prog (read done)
    progress_value.value = 10

    """ all input check """
    # check if duplicate tuple coord presence
    u, c = np.unique(point_in, return_counts=True, axis=0)
    dup = u[c > 1]
    if len(dup) > 0:
        print("Error: The substrate data has duplicates points coordinates :" + str(dup) + ". Please remove them and try again.")
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

    if not intersect_buffer:
        print('Error: Voronoi polygons buffer intersection failed')
        return False

    # find one sub data by polyg
    if len(list_polyg) == 0:
        print('Error: The substrate does not create a meangiful grid. Please add more substrate points.')
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

    """ voronoi export """
    # filename output
    sub_filename_voronoi = name + '_triangulated' + '.gpkg'
    sub_filename_voronoi_path = os.path.join(path_shp, sub_filename_voronoi)
    driver = ogr.GetDriverByName('GPKG')
    if os.path.exists(sub_filename_voronoi_path):
        ds = driver.Open(sub_filename_voronoi_path, 1)  # 0 means read-only. 1 means writeable.
    else:
        ds = driver.CreateDataSource(sub_filename_voronoi_path)
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
        feat = ogr.Feature(defn)
        for k in range(sub_class_number):
            sub_array2[k][i] = sub_array[k][i]
        data_here = [item[i] for item in sub_array2]
        for field_num, field in enumerate(field_names):
            feat.SetField(field, data_here[field_num])
        # set geometry
        feat.SetGeometry(polygon)
        # create
        layer.CreateFeature(feat)

    # Save and close everything
    layer.CommitTransaction()  # faster

    # close file
    ds.Destroy()

    # prog (read done)
    progress_value.value = 40

    # set temporary names with voronoi suffix
    sub_description["sub_filename_source"] = sub_filename_voronoi
    sub_description["sub_path_source"] = path_shp

    # triangulation on voronoi polygons
    data_2d = load_sub_sig(sub_description, progress_value)

    return data_2d


def load_sub_sig(sub_description, progress_value):
    # filename, path_file, path_prj, path_hdf5, name_prj, name_hdf5, sub_mapping_method,
    #                  sub_classification_code, sub_epsg_code, default_values, q=[]
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
    data_2d = None

    filename = sub_description["sub_filename_source"]
    path_file = sub_description["sub_path_source"]
    sub_mapping_method = sub_description["sub_mapping_method"]
    sub_classification_code = sub_description["sub_classification_code"]
    default_values = sub_description["sub_default_values"]
    path_prj = sub_description["path_prj"]
    sub_epsg_code = sub_description["sub_epsg_code"]
    blob, ext = os.path.splitext(filename)

    if ext == ".shp":
        # open shape file
        driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
        ds = driver.Open(os.path.join(path_file, filename), 0)  # 0 means read-only. 1 means writeable.
    elif ext == ".gpkg":
        driver = ogr.GetDriverByName('GPKG')  # GPKG
        ds = driver.Open(os.path.join(path_file, filename), 0)  # 0 means read-only. 1 means writeable.

    layer = ds.GetLayer(0)
    layer_defn = layer.GetLayerDefn()

    header_list = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]
    sub_array = np.empty(shape=(len(layer), len(header_list)), dtype=np.int)
    for feature_ind, feature in enumerate(layer):
        sub_array[feature_ind] = [feature.GetField(j) for j in header_list]

    # prog (read done)
    progress_value.value = 50

    # check data validity
    data_validity, sub_description_system = data_substrate_validity(header_list,
                                                                    sub_array,
                                                                    sub_mapping_method,
                                                                    sub_classification_code)

    # prog (read done)
    progress_value.value = 60

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
        if polygon_shp_to_triangle_shp(filename, path_file, path_prj, sub_description_system):
            # prog (triangulation done)
            progress_value.value = 90

            # initialization
            xy = []  # point
            tin = []  # connectivity table

            if sub_description_system['sub_mapping_method'] == 'point':
                # file name triangulated
                blob = blob.replace("_triangulated", "")

            # file name triangulated
            filename = blob + "_triangulated.gpkg"

            # open shape file (think about zero or one to start! )
            driver = ogr.GetDriverByName('GPKG')
            ds = driver.Open(os.path.join(path_prj, "input", blob, filename), 0)  # 0 means read-only. 1 means writeable.

            layer_num = 0
            if sub_description_system['sub_mapping_method'] == 'point':
                # get all name to found triangulated name
                for layer_num in range(ds.GetLayerCount()):
                    layer = ds.GetLayer(layer_num)
                    if "_triangulated" in layer.GetName():
                        break

            layer = ds.GetLayer(layer_num)

            # get point coordinates and connectivity table in two lists
            sub_array = np.empty(shape=(len(layer), len(header_list)),
                                 dtype=HydraulicVariableUnitManagement().sub_dom.dtype)
            for feature_ind, feature in enumerate(layer):
                sub_array[feature_ind] = [feature.GetField(j) for j in header_list]
                shape_geom = feature.geometry()
                shape_geom.SetCoordinateDimension(2)  # never z values
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

            # data_2d
            data_2d = Data2d(reach_num=1,
                             unit_num=1)
            data_2d[0][0]["node"] = dict(data=None,
                                     xy=np.array(xy))
            data_2d[0][0]["mesh"] = dict(data=None,
                                     tin=np.array(tin))
            data_2d[0][0]["mesh"]["data"] = pd.DataFrame()

            # TODO: be carefull of header order
            for header_num, header in enumerate(header_list):
                data_2d[0][0]["mesh"]["data"][header] = sub_array[:, header_num]

    return data_2d


def load_sub_cst(sub_description, progress_value):
    # sys.stdout = mystdout = StringIO()

    # prog
    progress_value.value = 10

    sub_constant_values = sub_description["sub_default_values"].split(",")

    # data_2d
    data_2d = Data2d()
    for i, value in enumerate(sub_constant_values):
        sub_constant_values[i] = int(value.strip())  # clean string and convert to int
    data_2d.sub_constant_values = np.array(sub_constant_values, dtype=np.int64)

    # prog
    progress_value.value = 90

    return data_2d


def polygon_shp_to_triangle_shp(filename, path_file, path_prj, sub_description_system):
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
    in_shp_abs_path = os.path.join(path_file, filename)
    blob, ext = os.path.splitext(filename)

    if ext == ".shp":
        driver = ogr.GetDriverByName('ESRI Shapefile')  # Shapefile
        ds_polygon = driver.Open(in_shp_abs_path, 0)  # 0 means read-only. 1 means writeable.
    elif ext == ".gpkg":
        driver = ogr.GetDriverByName('GPKG')  # GPKG
        ds_polygon = driver.Open(in_shp_abs_path, 0)  # 0 means read-only. 1 means writeable.

    layer_num = 0
    if sub_description_system['sub_mapping_method'] == 'point':
        # get all name to found triangulated name
        for layer_num in range(ds_polygon.GetLayerCount()):
            layer_polygon = ds_polygon.GetLayer(layer_num)
            if "_triangulated" in layer_polygon.GetName():
                break

    layer_polygon = ds_polygon.GetLayer(layer_num)
    layer_defn = layer_polygon.GetLayerDefn()

    # get geom type
    if layer_polygon.GetGeomType() not in polygon_type_values:
        print("file is not polygon type : ", layer_polygon.GetGeomType())
        return False

    # fields = sf.fields[1:]
    header_list = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]

    # get EPSG
    crs = layer_polygon.GetSpatialRef()

    # check if all polygon are triangle yet
    try:
        point_nb_list = []
        for feature_ind, feature in enumerate(layer_polygon):
            shape_geom = feature.geometry()
            new_points = shape_geom.GetGeometryRef(0).GetPoints()
            point_nb_list.append(len(new_points))
    except:
        print("Error: Input selected shapefile polygon geometry does not seems to be valid. "
              "Use a geometry validity checker in your GIS software.")
        return False

    # all_polygon_triangle_tf
    if list(set(point_nb_list)) == [4]:
        # copy input file to input files folder with suffix triangulated
        all_input_files_abspath_list = glob(os.path.join(path_file, blob) + "*")
        all_input_files_files_list = [os.path.basename(file_path) for file_path in all_input_files_abspath_list]
        for i in range(len(all_input_files_files_list)):
            sh_copy(all_input_files_abspath_list[i],
                    os.path.join(os.path.join(path_prj, "input"),
                                        os.path.splitext(all_input_files_files_list[i])[0] +
                                          "_triangulated" +
                                          os.path.splitext(all_input_files_files_list[i])[1]))
        print("Warning: Input selected shapefile polygon is already a triangle type.")

    # not all_polygon_triangle_tf
    else:
        # Extract list of points and segments from shp
        vertices_array = []  # point
        segments_array = []  # segment index or connectivity table
        holes_array = []
        inextpoint = 0
        regions_values = np.empty(shape=(len(layer_polygon), len(header_list)), dtype=np.int)
        regions_points = []
        layer_polygon.ResetReading()
        shape_geom = None
        for feature_ind, feature in enumerate(layer_polygon):
            regions_values[feature_ind] = [feature.GetField(j) for j in header_list]
            shape_geom = feature.geometry()
            regions_points.append([*shape_geom.PointOnSurface().GetPoint()[:2], feature_ind, 0])
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

        # triangulate on polygon
        if holes_array.size == 0:
            polygon_from_shp = dict(vertices=vertices_array2,
                                    segments=segments_array2,
                                    regions=regions_points)
        else:
            polygon_from_shp = dict(vertices=vertices_array2,
                                    segments=segments_array2,
                                    holes=holes_array,
                                    regions=regions_points)
        polygon_triangle = tr.triangulate(polygon_from_shp, "pA")  # 'pA' if we use regions key
        #tr.compare(plt, polygon_from_shp, polygon_triangle)

        # get geometry and attributes of triangles
        triangle_geom_list = polygon_triangle["vertices"][polygon_triangle["triangles"]]
        triangle_records_list = regions_values[polygon_triangle['triangle_attributes'].flatten().astype(np.int64)]

        # close file
        layer_polygon = None
        ds_polygon = None

        # geometry issue : polygons are not joined (little hole) ==> create invalid geom
        if triangle_records_list.min() < 0:
            # write triangulate shapefile
            out_error_shp_basename = os.path.splitext(filename)[0]
            out_error_shp_filename = out_error_shp_basename + "_invalid.gpkg"
            out_error_shp_path = os.path.join(path_prj, "input", out_error_shp_basename)
            out_error_shp_abs_path = os.path.join(out_error_shp_path, out_error_shp_filename)
            if os.path.exists(out_error_shp_abs_path):
                try:
                    os.remove(out_error_shp_abs_path)
                except PermissionError:
                    print('Error: ' + out_error_shp_filename + ' is currently open in an other program. Could not be re-written.')
                    return False

            driver = ogr.GetDriverByName('GPKG')  # GPKG
            ds_error = driver.CreateDataSource(out_error_shp_abs_path)
            if not crs:  # '' == crs unknown
                layer_error = ds_error.CreateLayer(name=out_error_shp_basename, geom_type=ogr.wkbPolygon)
            else:  # crs known
                layer_error = ds_error.CreateLayer(name=out_error_shp_basename, srs=crs, geom_type=ogr.wkbPolygon)

            defn = layer_error.GetLayerDefn()
            layer_error.StartTransaction()  # faster

            # triangle_invalid_index_list
            triangle_invalid_index_list = np.where(triangle_records_list[:, 0] == -1)[0]
            print("Warning: Maybe in reason of invalid geometry some generated substrate data triangles have been set to default values. You will find " + out_error_shp_filename +
                  " in 'input' project folder, these help you to find an invalid geometry. Correct it and try again.")
            for triangle_invalid_index in triangle_invalid_index_list:
                # set sub_default_values
                triangle_records_list[triangle_invalid_index, :] = np.array(sub_description_system["sub_default_values"].split(", ")).astype(np.int)

                # get geom
                p1 = polygon_triangle["vertices"][polygon_triangle["triangles"][triangle_invalid_index][0]]
                p2 = polygon_triangle["vertices"][polygon_triangle["triangles"][triangle_invalid_index][1]]
                p3 = polygon_triangle["vertices"][polygon_triangle["triangles"][triangle_invalid_index][2]]

                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(*p1)
                ring.AddPoint(*p2)
                ring.AddPoint(*p3)
                ring.AddPoint(*p1)
                # Create polygon
                poly = ogr.Geometry(ogr.wkbPolygon)
                poly.AddGeometry(ring)
                # Create a new feature
                feat = ogr.Feature(defn)
                # set geometry
                feat.SetGeometry(poly)
                # create
                layer_error.CreateFeature(feat)

            # Save and close everything
            layer_error.CommitTransaction()  # faster

            # close file
            layer_error = None
            ds_error = None

        # write triangulate
        out_shp_basename = os.path.splitext(filename)[0]
        if sub_description_system['sub_mapping_method'] == 'point':
            out_shp_filename = out_shp_basename + ".gpkg"
            folder_name = out_shp_basename.replace("_triangulated", "")
            out_shp_path = os.path.join(path_prj, "input", folder_name)
        else:
            out_shp_filename = out_shp_basename + "_triangulated.gpkg"
            folder_name = out_shp_basename.replace("_triangulated", "")
            out_shp_path = os.path.join(path_prj, "input", out_shp_basename)

        out_shp_abs_path = os.path.join(out_shp_path, out_shp_filename)
        if os.path.exists(out_shp_abs_path):
            driver = ogr.GetDriverByName('GPKG')
            ds_triangle = driver.Open(out_shp_abs_path, 1)  # 0 means read-only. 1 means writeable.
        else:
            driver = ogr.GetDriverByName('GPKG')
            ds_triangle = driver.CreateDataSource(out_shp_abs_path)

        # if os.path.exists(out_shp_abs_path):
        #     try:
        #         os.remove(out_shp_abs_path)
        #     except PermissionError:
        #         print(
        #             'Error: ' + out_shp_filename + ' is currently open in an other program. Could not be re-written.')
        #         return False

        if not crs:  # '' == crs unknown
            layer_triangle = ds_triangle.CreateLayer(name=folder_name + "_triangulated", geom_type=ogr.wkbPolygon)
        else:  # crs known
            layer_triangle = ds_triangle.CreateLayer(name=folder_name + "_triangulated", srs=crs, geom_type=ogr.wkbPolygon)

        for field in header_list:
            layer_triangle.CreateField(ogr.FieldDefn(field, ogr.OFTInteger))  # Add one attribute

        defn = layer_triangle.GetLayerDefn()
        layer_triangle.StartTransaction()  # faster
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
            layer_triangle.CreateFeature(feat)

        # Save and close everything
        layer_triangle.CommitTransaction()  # faster

        # close file
        layer_triangle = None
        #ds_triangle.Destroy()
        ds_triangle = None

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


def remove_duplicates_points_to_triangulate(vertices_array, segments_array, holes_array):
    """
    AIM: for using triangle in order to transform polygons into triangles it is necessary to avoid any duplicate point
    in the data set to be given to triangle
    Take great care of having only vertices defined in the x,y plane no Z or others coordinates !!!!!
    :param vertices_array:  list, coordinates of points duplicate may append
    :param segments_array: list, segment definition by a serial of couple of 2 index points defining a segment
    :param holes_array: list of coordinates of points inside holes (centroids)
    :return:
        vertices_array2 : a np-array of coordinates with no duplicate points,
         segments_array2 : segment definition by a serial of couple of 2 index points( referenced from vertices_array2)
            defining each segment
         holes_array  : a np-array of coordinates of points inside holes (centroids) (nothing changed),
    """
    vertices_array3, indices = np.unique(vertices_array, axis=0, return_inverse=True)
    segments_array3 = indices[segments_array]
    holes_array = np.array(holes_array)

    return vertices_array3, segments_array3, holes_array


def point_inside_polygon(x, y, poly):
    """
    http://www.ariel.com.au/a/python-point-int-poly.html
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


def get_sub_description_from_source(filename_path, substrate_mapping_method, path_prj):
    warning_list = []  # text warning output
    name_prj = os.path.splitext(os.path.basename(path_prj))[0]
    substrate_classification_code = None
    substrate_classification_method = None
    substrate_default_values = None
    epsg_code = None
    substrate_classification_codes = ['Cemagref', 'Sandre']
    substrate_classification_methods = ['coarser-dominant', 'percentage']

    dirname = os.path.dirname(filename_path)
    filename = os.path.basename(filename_path)
    blob, ext = os.path.splitext(filename)

    # POLYGON
    if substrate_mapping_method == "polygon":
        # check classification code in .txt (polygon or point shp)
        if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
            warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                            "The selected shapefile is not accompanied by its habby .txt file."))
            return False, warning_list

        if ext == ".shp":
            # get type shapefile
            driver = GetDriverByName('ESRI Shapefile')  # Shapefile
            ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.
        elif ext == ".gpkg":
            # get type shapefile
            driver = GetDriverByName('GPKG')  # GPKG
            ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.

        # get layer
        layer = ds.GetLayer(0)  # one layer in shapefile but can be multiple in gpkg..

        # get geom type
        if layer.GetGeomType() not in polygon_type_values:
            # get the first feature
            feature = layer.GetNextFeature()
            geom_type = feature.GetGeometryRef().GetGeometryName()
            warning_list.append(
                "Error : " + qt_tr.translate("hydro_input_file_mod",
                                             "Selected shapefile is not polygon type. Type : " + geom_type))
            return False, warning_list

        if os.path.isfile(os.path.join(dirname, blob + ".txt")):
            with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                dataraw = f.read()
            substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                "\n")
            if "substrate_classification_code=" in substrate_classification_code_raw:
                substrate_classification_code = \
                    substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                if substrate_classification_code not in substrate_classification_codes:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification code in .txt file is not recognized : ")
                                        + substrate_classification_code)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_code=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "substrate_classification_method=" in substrate_classification_method_raw:
                substrate_classification_method = \
                    substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                if substrate_classification_method not in substrate_classification_methods:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification method in .txt file is not recognized : ")
                                        + substrate_classification_method)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_method=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "default_values=" in substrate_default_values_raw:
                substrate_default_values = substrate_default_values_raw.split("default_values=")[1].strip()
                constant_values_list = substrate_default_values.split(",")
                for value in constant_values_list:
                    try:
                        int(value.strip())
                    except:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "Default values can't be converted to integer : ")
                                            + substrate_default_values)
                        return False, warning_list
            else:
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'default_values=' is not found in"
                                                                        " .txt file."))
                return False, warning_list

        # check EPSG code in .prj
        if not os.path.isfile(os.path.join(dirname, blob + ".prj")) and ext == ".shp":
            warning_list.append(
                "Warning: The selected shapefile is not accompanied by its .prj file. EPSG code is unknwon.")
            epsg_code = "unknown"
        else:
            inSpatialRef = layer.GetSpatialRef()
            sr = SpatialReference(str(inSpatialRef))
            res = sr.AutoIdentifyEPSG()
            epsg_code_str = sr.GetAuthorityCode(None)
            if epsg_code_str:
                epsg_code = epsg_code_str
            else:
                epsg_code = "unknown"

    # POINT
    if substrate_mapping_method == "point":
        # txt case
        if ext == ".txt":
            if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The selected file don't exist."))
                return False, warning_list
            with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                dataraw = f.read()
            if len(dataraw.split("\n")[:4]) < 4:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "This text file is not a valid point substrate."))
                return False, warning_list
            epsg_raw, substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                "\n")[:4]
            # check EPSG in .txt (polygon or point shp)
            if "EPSG=" in epsg_raw:
                epsg_code = epsg_raw.split("EPSG=")[1].strip()
            else:
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'EPSG=' is not found in .txt file."))
                return False, warning_list
            # check classification code in .txt ()
            if "substrate_classification_code=" in substrate_classification_code_raw:
                substrate_classification_code = \
                    substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                if substrate_classification_code not in substrate_classification_codes:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification code in .txt file is not recognized : ")
                                        + substrate_classification_code)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_code=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "substrate_classification_method=" in substrate_classification_method_raw:
                substrate_classification_method = \
                    substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                if substrate_classification_method not in substrate_classification_methods:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The classification method in .txt file is not recognized : ")
                        + substrate_classification_method)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_method=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "default_values=" in substrate_default_values_raw:
                substrate_default_values = substrate_default_values_raw.split("default_values=")[1].strip()
                constant_values_list = substrate_default_values.split(",")
                for value in constant_values_list:
                    try:
                        int(value.strip())
                    except:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "Default values can't be converted to integer : ")
                                            + substrate_default_values)
                        return False, warning_list
            else:
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'default_values=' is not found in"
                                                                        " .txt file."))
                return False, warning_list

        if ext == ".shp" or ext == ".gpkg":
            # check classification code in .txt (polygon or point shp)
            if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The selected shapefile is not accompanied by its habby .txt file."))
                return False, warning_list

            if ext == ".shp":
                # get type shapefile
                driver = GetDriverByName('ESRI Shapefile')  # Shapefile
                ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.
            elif ext == ".gpkg":
                # get type shapefile
                driver = GetDriverByName('GPKG')  # GPKG
                ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.

            layer = ds.GetLayer(0)  # one layer in shapefile but can be multiple in gpkg..

            # get geom type
            if layer.GetGeomType() not in point_type_values:  # point type
                # get the first feature
                feature = layer.GetNextFeature()
                geom_type = feature.GetGeometryRef().GetGeometryName()
                warning_list.append(
                    "Error : " + qt_tr.translate("hydro_input_file_mod",
                                                 "Selected shapefile is not point type. Type : " + geom_type))
                return False, warning_list

            else:
                with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                    dataraw = f.read()
                substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                    "\n")
                if "substrate_classification_code=" in substrate_classification_code_raw:
                    substrate_classification_code = \
                        substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                    if substrate_classification_code not in substrate_classification_codes:
                        warning_list.append(
                            "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                        "The classification code in .txt file is not recognized : ")
                            + substrate_classification_code)
                        return False, warning_list
                else:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The name 'substrate_classification_code=' is not found in"
                                                    " .txt file."))
                    return False, warning_list
                if "substrate_classification_method=" in substrate_classification_method_raw:
                    substrate_classification_method = \
                        substrate_classification_method_raw.split("substrate_classification_method=")[
                            1].strip()
                    if substrate_classification_method not in substrate_classification_methods:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "The classification method in .txt file is not recognized : ")
                                            + substrate_classification_method)
                        return
                else:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The name 'substrate_classification_method=' is not found in"
                                                    " .txt file."))
                    return False, warning_list
                if "default_values=" in substrate_default_values_raw:
                    substrate_default_values = substrate_default_values_raw.split("default_values=")[
                        1].strip()
                    constant_values_list = substrate_default_values.split(",")
                    for value in constant_values_list:
                        try:
                            int(value.strip())
                        except:
                            warning_list.append(
                                "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                            "Default values can't be converted to integer : ")
                                + substrate_default_values)
                            return False, warning_list
                else:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'default_values=' is not found in"
                                                                            " .txt file."))
                    return False, warning_list

            # check EPSG code in .prj
            if not os.path.isfile(os.path.join(dirname, blob + ".prj")) and ext == ".shp":
                warning_list.append(
                    "Warning: The selected shapefile is not accompanied by its .prj file. EPSG code is unknwon.")
                epsg_code = "unknown"
            else:
                inSpatialRef = layer.GetSpatialRef()
                sr = SpatialReference(str(inSpatialRef))
                res = sr.AutoIdentifyEPSG()
                epsg_code_str = sr.GetAuthorityCode(None)
                if epsg_code_str:
                    epsg_code = epsg_code_str
                else:
                    epsg_code = "unknown"

    # CONSTANT
    if substrate_mapping_method == "constant":
        epsg_code = "unknown"
        # txt
        if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
            warning_list.append(
                "Error: " + qt_tr.translate("hydro_input_file_mod", "The selected text file don't exist."))
            return False, warning_list
        if os.path.isfile(os.path.join(dirname, blob + ".txt")):
            with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                dataraw = f.read()
            substrate_classification_code_raw, substrate_classification_method_raw, constant_values_raw = dataraw.split(
                "\n")
            # classification code
            if "substrate_classification_code=" in substrate_classification_code_raw:
                substrate_classification_code = \
                    substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                if substrate_classification_code not in substrate_classification_codes:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification code in .txt file is not recognized : ")
                                        + substrate_classification_code)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_code=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "substrate_classification_method=" in substrate_classification_method_raw:
                substrate_classification_method = \
                    substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                if substrate_classification_method not in substrate_classification_methods:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The classification method in .txt file is not recognized : ")
                        + substrate_classification_method)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_method=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            # constant values
            if "constant_values=" in constant_values_raw:
                substrate_default_values = constant_values_raw.split("constant_values=")[1].strip()
                substrate_default_values_list = substrate_default_values.split(",")
                for value in substrate_default_values_list:
                    try:
                        int(value.strip())
                    except:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "Constant values can't be converted to integer : ")
                                            + substrate_default_values)
                        return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'constant_values=' is not found in .txt file."))
                return False, warning_list

    # create dict
    sub_description = dict(sub_mapping_method=substrate_mapping_method,
                           sub_classification_code=substrate_classification_code,
                           sub_classification_method=substrate_classification_method,
                           sub_default_values=substrate_default_values,
                           sub_epsg_code=epsg_code,
                           sub_filename_source=filename,
                           sub_path_source=dirname,
                           sub_reach_number="1",
                           sub_reach_list="unknown",
                           sub_unit_number="1",
                           sub_unit_list="0.0",
                           sub_unit_type="unknown",
                           name_prj=name_prj,
                           path_prj=path_prj
                           )

    return sub_description, warning_list