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
from PyQt5.QtCore import QLocale
import numpy as np
from osgeo import ogr
from osgeo import osr


def setup(t, l):
    global progress_value, lock
    progress_value = t
    lock = l


""" txt """


def export_point_txt(name, hvum, unit_data):
    # name, hvum, unit_data = args
    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:
        # header 1
        text_to_write_str = "x\ty\t"
        text_to_write_str += "\t".join(hvum.all_final_variable_list.nodes().names())
        text_to_write_str += '\n'
        f.write(text_to_write_str)

        # header 2 2
        text_to_write_str = '[m]\t[m]\t['
        text_to_write_str += "]\t[".join(hvum.all_final_variable_list.nodes().units())
        text_to_write_str += "]"
        f.write(text_to_write_str)

        # data
        text_to_write_str = ""
        # for each point
        for point_num in range(0, len(unit_data["node"][hvum.xy.name])):
            text_to_write_str += '\n'
            # data geom (get the triangle coordinates)
            x = str(unit_data["node"][hvum.xy.name][point_num][0])
            y = str(unit_data["node"][hvum.xy.name][point_num][1])
            text_to_write_str += f"{x}\t{y}"
            for node_variable_name in hvum.all_final_variable_list.nodes().names():
                text_to_write_str += "\t" + str(
                    unit_data["node"]["data"][node_variable_name][point_num])

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            text_to_write_str = text_to_write_str.replace('.', ',')

        # write file
        f.write(text_to_write_str)


def export_mesh_txt(name, hvum, unit_data):
    # name, hvum, unit_data = args
    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:
        # header 1
        text_to_write_str_list = ["node1", "node2", "node3"]
        text_to_write_str_list.extend(hvum.all_final_variable_list.meshs().names())
        text_to_write_str = "\t".join(text_to_write_str_list)
        text_to_write_str += '\n'
        f.write(text_to_write_str)

        # header 2
        text_to_write_str = "[]\t[]\t[]\t["
        text_to_write_str += ']\t['.join(hvum.all_final_variable_list.meshs().units())
        f.write(text_to_write_str)

        # data
        text_to_write_str = ""
        # for each mesh
        for mesh_num in range(0, len(unit_data["mesh"][hvum.tin.name])):
            node1 = unit_data["mesh"][hvum.tin.name][mesh_num][
                0]  # node num
            node2 = unit_data["mesh"][hvum.tin.name][mesh_num][1]
            node3 = unit_data["mesh"][hvum.tin.name][mesh_num][2]
            text_to_write_str += '\n'
            text_to_write_str += f"{str(node1)}\t{str(node2)}\t{str(node3)}\t"
            data_list = []
            for mesh_variable_name in hvum.all_final_variable_list.meshs().names():
                data_list.append(str(
                    unit_data["mesh"]["data"][mesh_variable_name][mesh_num]))
            text_to_write_str += "\t".join(data_list)

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            text_to_write_str = text_to_write_str.replace('.', ',')

        # write file
        f.write(text_to_write_str)


""" gpkg """


def export_mesh_layer_to_gpkg(filename_path, layer_name, epsg_code, unit_data, whole_profile, delta_mesh):  #
    # Mapping between OGR and Python data types
    OGRTypes_dict = {np.int64: ogr.OFTInteger64,
                     np.float64: ogr.OFTReal}

    # CRS
    crs = osr.SpatialReference()
    if epsg_code != "unknown":
        try:
            crs.ImportFromEPSG(int(epsg_code))
        except:
            print("Warning: " + "hdf5_mod", "Can't write .prj from EPSG code : " + epsg_code)

    driver = ogr.GetDriverByName('GPKG')  # GPKG
    ds = driver.CreateDataSource(filename_path + "_" + layer_name + ".gpkg")

    # create new layer
    if not crs.ExportToWkt():  # '' == crs unknown
        layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPolygon, options=['OVERWRITE=YES'])
    else:  # crs known
        layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPolygon, options=['OVERWRITE=YES'])

    # create fields (no width no precision to be specified with GPKG)
    layer.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))  # Add one attribute

    if not whole_profile:
        # create fields (no width no precision to be specified with GPKG)
        for mesh_variable in unit_data.hvum.all_final_variable_list.meshs():
            layer.CreateField(ogr.FieldDefn(mesh_variable.name_gui, OGRTypes_dict[mesh_variable.dtype]))

    defn = layer.GetLayerDefn()
    layer.StartTransaction()  # faster

    # for each mesh
    for mesh_num in range(0, len(unit_data["mesh"][unit_data.hvum.tin.name])):
        node1 = unit_data["mesh"][unit_data.hvum.tin.name][mesh_num][
            0]  # node num
        node2 = unit_data["mesh"][unit_data.hvum.tin.name][mesh_num][1]
        node3 = unit_data["mesh"][unit_data.hvum.tin.name][mesh_num][2]
        # data geom (get the triangle coordinates)
        if whole_profile:
            z_source = unit_data["node"][unit_data.hvum.z.name]
        else:
            z_source = unit_data["node"]["data"][unit_data.hvum.z.name]
        p1 = list(unit_data["node"][unit_data.hvum.xy.name][node1].tolist() + [z_source[node1]])
        p2 = list(unit_data["node"][unit_data.hvum.xy.name][node2].tolist() + [z_source[node2]])
        p3 = list(unit_data["node"][unit_data.hvum.xy.name][node3].tolist() + [z_source[node3]])
        # Create triangle
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
        feat.SetField('ID', mesh_num)
        if not whole_profile:
            # variables
            for mesh_variable in unit_data.hvum.all_final_variable_list.meshs():
                # convert NumPy values to a native Python type
                data_field = unit_data[mesh_variable.position]["data"][mesh_variable.name][mesh_num].item()
                feat.SetField(mesh_variable.name_gui, data_field)
        # set geometry
        feat.SetGeometry(poly)
        # create
        layer.CreateFeature(feat)
        # progress
        with lock:
            progress_value.value = progress_value.value + delta_mesh

    # Save and close everything
    layer.CommitTransaction()  # faster

    # close file
    ds.Destroy()


def export_node_layer_to_gpkg(filename_path, layer_name, epsg_code, unit_data, whole_profile, delta_node):  #
    # Mapping between OGR and Python data types
    OGRTypes_dict = {np.int64: ogr.OFTInteger64,
                     np.float64: ogr.OFTReal}

    # CRS
    crs = osr.SpatialReference()
    if epsg_code != "unknown":
        try:
            crs.ImportFromEPSG(int(epsg_code))
        except:
            print("Warning: " + "hdf5_mod", "Can't write .prj from EPSG code : " + epsg_code)

    driver = ogr.GetDriverByName('GPKG')  # GPKG
    ds = driver.CreateDataSource(filename_path + "_" + layer_name + ".gpkg")

    # create new layer
    if not crs.ExportToWkt():  # '' == crs unknown
        layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPoint, options=['OVERWRITE=YES'])
    else:  # crs known
        layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPoint, options=['OVERWRITE=YES'])

    # create fields (no width no precision to be specified with GPKG)
    layer.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))  # Add one attribute

    if not whole_profile:
        # create fields (no width no precision to be specified with GPKG)
        for node_variable in unit_data.hvum.all_final_variable_list.nodes():
            layer.CreateField(ogr.FieldDefn(node_variable.name_gui, OGRTypes_dict[node_variable.dtype]))
    else:
        layer.CreateField(ogr.FieldDefn('elevation', ogr.OFTReal))  # Add one attribute

    defn = layer.GetLayerDefn()
    layer.StartTransaction()  # faster

    # for each point
    for node_num in range(0, len(unit_data["node"][unit_data.hvum.xy.name])):
        # data geom (get the triangle coordinates)
        x = unit_data["node"][unit_data.hvum.xy.name][node_num][0]
        y = unit_data["node"][unit_data.hvum.xy.name][node_num][1]
        if whole_profile:
            z = unit_data["node"][unit_data.hvum.z.name][node_num]
        else:
            z = unit_data["node"]["data"][unit_data.hvum.z.name][node_num]
        # Create a point
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y, z)
        # Create a new feature
        feat = ogr.Feature(defn)
        feat.SetField('ID', node_num)
        if not whole_profile:
            # variables
            for node_variable in unit_data.hvum.all_final_variable_list.nodes():
                # convert NumPy values to a native Python type
                data_field = unit_data[node_variable.position]["data"][node_variable.name][node_num].item()
                feat.SetField(node_variable.name_gui, data_field)
        else:
            feat.SetField('elevation', z)
        # set geometry
        feat.SetGeometry(point)
        # create
        layer.CreateFeature(feat)
        # progress
        with lock:
            progress_value.value = progress_value.value + delta_node

    # Save and close everything
    layer.CommitTransaction()  # faster

    # close file
    ds.Destroy()


def merge_gpkg_to_one(filename_path_list, layer_name_list, output_filename_path):
    # merge gpkg to one
    driver = ogr.GetDriverByName('GPKG')  # GPKG
    if os.path.isfile(output_filename_path):
        # os.remove(output_filename_path)
        ds = driver.Open(output_filename_path, 1)
    else:
        ds = driver.CreateDataSource(output_filename_path)

    # loop on inputfile
    for filename_path, layer_name in zip(filename_path_list, layer_name_list):
        # print("copy " + layer_name + " to " + output_filename_path)
        # current file
        current_file = filename_path + "_" + layer_name + ".gpkg"
        # read file
        ds_current = driver.Open(current_file, 0)
        # copy current to general
        ds.CopyLayer(ds_current.GetLayer(0), layer_name, options=['OVERWRITE=YES'])
        # close file
        ds_current.Destroy()
        # remove file
        os.remove(current_file)

    # close file
    ds.Destroy()


if __name__ == '__main__':
    # input
    filename_path = r"C:\Users\Quentin\Documents\HABBY_projects\DefaultProj\output\GIS\a1_a2_unknown.gpkg"
    path_prj = r"C:\Users\Quentin\Documents\HABBY_projects\DefaultProj"
    import hdf5_mod
    from src.project_properties_mod import load_project_properties

    hdf5_hydro = hdf5_mod.Hdf5Management(path_prj,
                                         "a1_a2.hyd",
                                         new=False,
                                         edit=False)
    hdf5_hydro.load_hdf5_hyd(whole_profil=True,
                             user_target_list=load_project_properties(path_prj))
    hdf5_hydro.export_gpkg_mesh_whole_profile()
    # hdf5_hydro.export_gpkg_mesh_units()


