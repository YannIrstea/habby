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
import time
import matplotlib as mpl
from PyQt5.QtCore import QLocale #, QCoreApplication as qt_tr
import numpy as np
from osgeo import ogr
from osgeo import osr
from pandas import DataFrame
from matplotlib import pyplot as plt

from src.bio_info_mod import get_biomodels_informations_for_database, read_pref
from src.plot_mod import plot_suitability_curve, plot_suitability_curve_hem, plot_suitability_curve_bivariate

locale = QLocale()


def setup(t, l):
    global progress_value, lock
    progress_value = t
    lock = l


""" animal report """


def export_report(xmlfile, project_properties, qt_tr, progress_value, delta_animal):
    # qt_tr = get_translator(project_properties['path_prj'])

    plt.close()
    plt.rcParams['figure.figsize'] = 21, 29.7  # a4
    plt.rcParams['font.size'] = 24

    information_model_dict = read_pref(xmlfile)

    if information_model_dict["model_type"] != "bivariate suitability index models":
        if "HV" in information_model_dict["hydraulic_type_available"][0]:
            # plot
            fig, axe_curve = plot_suitability_curve(None,
                                   information_model_dict,
                                   None,
                                    project_properties,
                                   True,
                                   qt_tr)
        else:
            # plot
            fig, axe_curve = plot_suitability_curve_hem(None,
                                                        information_model_dict,
                                                        None,
                                                        project_properties,
                                                        True,
                                                        qt_tr)
    else:
        fig, axe_curve = plot_suitability_curve_bivariate(None,
                                                          information_model_dict,
                                                          None,
                                         project_properties,
                                         True,
                                   qt_tr)

    # get axe and fig
    # fig = plt.gcf()
    # axe_curve = plt.gca()

    # modification of the orginal preference fig
    # (0,0) is bottom left - 1 is the end of the page in x and y direction
    # plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.53])
    plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.53])
    # position for the image

    # HABBY and date
    plt.figtext(0.8, 0.97, 'HABBY - ' + time.strftime("%d %b %Y"))

    # REPORT title
    plt.figtext(0.1, 0.92, "REPORT - " + information_model_dict["code_biological_model"],
                fontsize=55,
                weight='bold',
                bbox={'facecolor': 'grey', 'alpha': 0.15, 'pad': 50})

    # Informations title
    list_of_title = [qt_tr.translate("export_manager_mod", "Latin name:"),
                     qt_tr.translate("export_manager_mod", "Common Name:"),
                     qt_tr.translate("export_manager_mod", "Code biological model:"),
                     qt_tr.translate("export_manager_mod", "ONEMA fish code:"),
                     qt_tr.translate("export_manager_mod", "Stage chosen:"),
                     qt_tr.translate("export_manager_mod", "Description:")]
    list_of_title_str = "\n\n".join(list_of_title)
    plt.figtext(0.1, 0.7,
                list_of_title_str,
                weight='bold',
                fontsize=32)

    # Informations text
    try:
        text_all = information_model_dict["latin_name"] + '\n\n' + information_model_dict["common_name_dict"][0] + '\n\n' + information_model_dict[
            "code_biological_model"] + '\n\n' + information_model_dict["code_alternative"][0] + '\n\n'
    except TypeError:
        aa=1
    for idx, s in enumerate(information_model_dict["stage_and_size"]):
        text_all += s + ', '
    text_all = text_all[:-2] + '\n\n'
    plt.figtext(0.4, 0.7, text_all, fontsize=32)

    # description
    newax = fig.add_axes([0.4, 0.55, 0.30, 0.16], anchor='C',
                         zorder=-1, frameon=False)
    newax.name = "description"
    newax.xaxis.set_ticks([])  # remove ticks
    newax.yaxis.set_ticks([])  # remove ticks
    if len(information_model_dict["description"]) > 350:
        decription_str = information_model_dict["description"][:350] + '...'
    else:
        decription_str = information_model_dict["description"]
    newax.text(0.0, 1.0, decription_str,  # 0.4, 0.71,
               wrap=True,
               fontsize=32,
               # bbox={'facecolor': 'grey',
               #       'alpha': 0.15},
               va='top',
               ha="left")  # , transform=newax.transAxes

    if information_model_dict["path_img"]:
        fish_im_name = os.path.join(os.getcwd(), information_model_dict["path_img"])
        if os.path.isfile(fish_im_name):
            im = plt.imread(mpl.cbook.get_sample_data(fish_im_name))
            newax = fig.add_axes([0.078, 0.55, 0.25, 0.13], anchor='C',
                                 zorder=-1)
            newax.imshow(im)
            newax.axis('off')

    # move suptitle
    fig.suptitle(qt_tr.translate("export_manager_mod", 'Habitat Suitability Index'),
                 x=0.5, y=0.54,
                 fontsize=32,
                 weight='bold')

    # filename
    filename = os.path.join(project_properties['path_figure'],
                            'report_' + information_model_dict["code_biological_model"] +
                            project_properties["format"])

    # save
    try:
        plt.savefig(filename)
        plt.close(fig)
        # plt.clf()
    except PermissionError:
        print(
            'Warning: Close ' + filename + ' to update fish information')

    # plt.clf()
    # plt.cla()

    # progress
    # with lock:
    progress_value.value = progress_value.value + delta_animal


""" txt """


def export_mesh_txt(name, hvum, unit_data_mesh, delta_unit):
    # conca to one dataframe
    unit_data_mesh["data"]["node1"] = unit_data_mesh["tin"][:, 0]
    unit_data_mesh["data"]["node2"] = unit_data_mesh["tin"][:, 1]
    unit_data_mesh["data"]["node3"] = unit_data_mesh["tin"][:, 2]

    # conca and write header and units
    unit_list_str = "[" + ']\t['.join(hvum.all_final_variable_list.meshs().units()) + "]\t[]\t[]\t[]"
    unit_list = unit_list_str.split("\t")
    DataFrame(unit_list).T.to_csv(name,
                                  mode="w",
                                  sep="\t",
                                  decimal=locale.decimalPoint(),
                                  header=unit_data_mesh["data"].columns.to_list(),
                                  index=False)

    # write data
    unit_data_mesh["data"].to_csv(name,
                                  mode="a",
                                  sep="\t",
                                  decimal=locale.decimalPoint(),
                                  header=False,
                                  index=False)

    # progress
    with lock:
        progress_value.value = progress_value.value + delta_unit


def export_point_txt(name, hvum, unit_data_node, delta_unit):
    # conca to one dataframe
    unit_data_node["data"]["x"] = unit_data_node["xy"][:, 0]
    unit_data_node["data"]["y"] = unit_data_node["xy"][:, 1]

    # conca and write header and units
    unit_list_str = "[" + ']\t['.join(hvum.all_final_variable_list.nodes().units()) + "]\t[m]\t[m]"
    unit_list = unit_list_str.split("\t")
    DataFrame(unit_list).T.to_csv(name,
                                  mode="w",
                                  sep="\t",
                                  decimal=locale.decimalPoint(),
                                  header=unit_data_node["data"].columns.to_list(),
                                  index=False)

    # write data
    unit_data_node["data"].to_csv(name,
                                  mode="a",
                                  sep="\t",
                                  decimal=locale.decimalPoint(),
                                  header=False,
                                  index=False)

    # progress
    with lock:
        progress_value.value = progress_value.value + delta_unit


""" gpkg """


def export_mesh_layer_to_gpkg(filename_path, layer_name, epsg_code, unit_data, whole_profile, delta_mesh):
    # Mapping between OGR and Python data types
    OGRTypes_dict = {np.int64: ogr.OFTInteger64,
                     np.float64: ogr.OFTReal}

    # CRS
    crs = osr.SpatialReference()
    if epsg_code != "unknown":
        try:
            crs.ImportFromEPSG(int(epsg_code))
        except:
            print("Warning: Can't write .prj from EPSG code : " + epsg_code)

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

    mesh_variable_list = unit_data.hvum.all_final_variable_list.meshs()

    # for each mesh
    for mesh_num in range(0, len(unit_data["mesh"][unit_data.hvum.tin.name])):
        node1 = unit_data["mesh"][unit_data.hvum.tin.name][mesh_num][0]
        node2 = unit_data["mesh"][unit_data.hvum.tin.name][mesh_num][1]
        node3 = unit_data["mesh"][unit_data.hvum.tin.name][mesh_num][2]
        # data geom (get the triangle coordinates)
        if whole_profile:
            z_source = unit_data["node"][unit_data.hvum.z.name]
        else:
            z_source = unit_data["node"]["data"][unit_data.hvum.z.name]
        p1 = unit_data["node"][unit_data.hvum.xy.name][node1].tolist() + [z_source[node1]]
        p2 = unit_data["node"][unit_data.hvum.xy.name][node2].tolist() + [z_source[node2]]
        p3 = unit_data["node"][unit_data.hvum.xy.name][node3].tolist() + [z_source[node3]]
        # Create triangle line
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
            for mesh_variable in mesh_variable_list:
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
            print("Warning: Can't write .prj from EPSG code : " + epsg_code)

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

    node_variable_list = unit_data.hvum.all_final_variable_list.nodes()

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
            for node_variable in node_variable_list:
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
    hdf5_hydro.export_gpkg_mesh_whole_profile()
    # hdf5_hydro.export_gpkg_mesh_units()
