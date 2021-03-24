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
from multiprocessing import Value
import matplotlib as mpl
from PyQt5.QtCore import QLocale, QCoreApplication as qt_tr
import numpy as np
from matplotlib import pyplot as plt
from osgeo import ogr
from osgeo import osr

from src.bio_info_mod import get_biomodels_informations_for_database, read_pref
from src.plot_mod import plot_suitability_curve, plot_suitability_curve_invertebrate, plot_suitability_curve_bivariate


def setup(t, l):
    global progress_value, lock
    progress_value = t
    lock = l


""" animal report """


def export_report(xmlfile, hab_animal_type, project_preferences, delta_animal):
    # plt.close()
    plt.rcParams['figure.figsize'] = 21, 29.7  # a4
    plt.rcParams['font.size'] = 24

    information_model_dict = get_biomodels_informations_for_database(xmlfile)

    # read additionnal info
    attributes = ['Description', 'Image', 'French_common_name',
                  'English_common_name', ]
    # careful: description is last data returned
    path_bio = os.path.dirname(xmlfile)
    path_im_bio = path_bio
    xmlfile = os.path.basename(xmlfile)
    # data = load_xml_name(path_bio, attributes, [xmlfile])

    # create figure
    fake_value = Value("d", 0)

    if information_model_dict["ModelType"] != "bivariate suitability index models":
        # fish
        if hab_animal_type == "fish":
            # read pref
            h_all, vel_all, sub_all, sub_code, code_fish, name_fish, stages = \
                read_pref(xmlfile, hab_animal_type)
            # plot
            fig, axe_curve = plot_suitability_curve(fake_value,
                                                    h_all,
                                                    vel_all,
                                                    sub_all,
                                                    information_model_dict["CdBiologicalModel"],
                                                    name_fish,
                                                    stages,
                                                    information_model_dict["substrate_type"],
                                                    sub_code,
                                                    project_preferences,
                                                    True)
        # invertebrate
        else:
            # open the pref
            shear_stress_all, hem_all, hv_all, _, code_fish, name_fish, stages = \
                read_pref(xmlfile, hab_animal_type)
            # plot
            fig, axe_curve = plot_suitability_curve_invertebrate(fake_value,
                                                                 shear_stress_all, hem_all, hv_all,
                                                                 code_fish, name_fish,
                                                                 stages, project_preferences, True)
    else:
        # open the pref
        [h_all, vel_all, pref_values_all, _, code_fish, name_fish, stages] = read_pref(xmlfile,
                                                                                       hab_animal_type)
        state_fake = Value("d", 0)
        fig, axe_curve = plot_suitability_curve_bivariate(state_fake,
                                                          h_all,
                                                          vel_all,
                                                          pref_values_all,
                                                          code_fish,
                                                          name_fish,
                                                          stages,
                                                          project_preferences,
                                                          True)
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
    plt.figtext(0.1, 0.92, "REPORT - " + name_fish,
                fontsize=55,
                weight='bold',
                bbox={'facecolor': 'grey', 'alpha': 0.15, 'pad': 50})

    # Informations title
    list_of_title = [qt_tr.translate("hdf5_mod", "Latin name:"),
                     qt_tr.translate("hdf5_mod", "Common Name:"),
                     qt_tr.translate("hdf5_mod", "Code biological model:"),
                     qt_tr.translate("hdf5_mod", "ONEMA fish code:"),
                     qt_tr.translate("hdf5_mod", "Stage chosen:"),
                     qt_tr.translate("hdf5_mod", "Description:")]
    list_of_title_str = "\n\n".join(list_of_title)
    plt.figtext(0.1, 0.7,
                list_of_title_str,
                weight='bold',
                fontsize=32)

    # Informations text
    text_all = name_fish + '\n\n' + information_model_dict["common_name_dict"][1] + '\n\n' + information_model_dict[
        "CdBiologicalModel"] + '\n\n' + code_fish + '\n\n'
    for idx, s in enumerate(stages):
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
               ha="left")  #, transform=newax.transAxes

    # add a fish image
    if path_im_bio:
        fish_im_name = os.path.join(os.getcwd(), information_model_dict["path_img"])
        if os.path.isfile(fish_im_name):
            im = plt.imread(mpl.cbook.get_sample_data(fish_im_name))
            newax = fig.add_axes([0.078, 0.55, 0.25, 0.13], anchor='C',
                                 zorder=-1)
            newax.imshow(im)
            newax.axis('off')

    # move suptitle
    fig.suptitle(qt_tr.translate("hdf5_mod", 'Habitat Suitability Index'),
                 x=0.5, y=0.54,
                 fontsize=32,
                 weight='bold')

    # filename
    filename = os.path.join(project_preferences['path_figure'], 'report_' + information_model_dict["CdBiologicalModel"] +
                            project_preferences["format"])

    # save
    try:
        plt.savefig(filename)
        plt.close(fig)
        plt.clf()
    except PermissionError:
        print(
            'Warning: ' + qt_tr.translate("hdf5_mod", 'Close ' + filename + ' to update fish information'))

    # progress
    with lock:
        progress_value.value = progress_value.value + delta_animal


""" txt """


def export_point_txt(name, hvum, unit_data_node, delta_node):
    # name, hvum, unit_data = args

    # convert all pandas data to str
    unit_data_node["data"] = unit_data_node["data"].astype(np.str)

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
        for point_num in range(0, len(unit_data_node[hvum.xy.name])):
            text_to_write_str += '\n'
            # data geom (get the triangle coordinates)
            x = str(unit_data_node[hvum.xy.name][point_num][0])
            y = str(unit_data_node[hvum.xy.name][point_num][1])
            text_to_write_str += f"{x}\t{y}"
            for node_variable_name in hvum.all_final_variable_list.nodes().names():
                text_to_write_str += "\t" + unit_data_node["data"][node_variable_name][point_num]

            # progress
            with lock:
                progress_value.value = progress_value.value + delta_node

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            text_to_write_str = text_to_write_str.replace('.', ',')

        # write file
        f.write(text_to_write_str)


def export_mesh_txt(name, hvum, unit_data_mesh, delta_mesh):
    # name, hvum, unit_data_mesh = args
    # open text to write
    # convert all pandas data to str
    unit_data_mesh["data"] = unit_data_mesh["data"].astype(np.str)

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
        for mesh_num in range(0, len(unit_data_mesh[hvum.tin.name])):
            node1 = unit_data_mesh[hvum.tin.name][mesh_num][0]  # node num
            node2 = unit_data_mesh[hvum.tin.name][mesh_num][1]
            node3 = unit_data_mesh[hvum.tin.name][mesh_num][2]
            text_to_write_str += '\n'
            text_to_write_str += f"{node1.__str__()}\t{node2.__str__()}\t{node3.__str__()}\t"
            for mesh_variable_name in hvum.all_final_variable_list.meshs().names():
                text_to_write_str += "\t" + unit_data_mesh["data"][mesh_variable_name][mesh_num]

            # progress
            with lock:
                progress_value.value = progress_value.value + delta_mesh

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

