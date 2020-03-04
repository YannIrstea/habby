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
import h5py
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtCore import QCoreApplication as qt_tr
from PyQt5.QtCore import QLocale
from osgeo import ogr
from osgeo import osr
from stl import mesh
from multiprocessing import Value

from src import bio_info_mod
from src import substrate_mod
from src import plot_mod
from src import hl_mod
from src import paraview_mod
from src.project_manag_mod import load_project_preferences, save_project_preferences
from src.tools_mod import txt_file_convert_dot_to_comma, c_mesh_mean_from_node_values, copy_hydrau_input_files,\
    c_mesh_max_slope_bottom, c_mesh_max_slope_energy, c_mesh_shear_stress, c_mesh_froude, c_mesh_hydraulic_head, \
    c_mesh_conveyance, c_node_conveyance, c_node_froude, c_node_hydraulic_head, c_node_water_level, c_mesh_water_level,\
    c_mesh_area, create_empty_data_2d_dict, copy_shapefiles, create_empty_data_2d_whole_profile_dict,\
    check_data_2d_dict_size, check_data_2d_dict_validity

from habby import HABBY_VERSION


class Hdf5Management:
    def __init__(self, path_prj, hdf5_filename):
        self.gravity_acc = 9.80665
        # hdf5 version attributes
        self.h5py_version = h5py.version.version
        self.hdf5_version = h5py.version.hdf5_version
        # project attributes
        self.path_prj = path_prj  # relative path to project
        self.path_shp = os.path.join(self.path_prj, "output", "GIS")
        self.path_visualisation = os.path.join(self.path_prj, "output", "3D")
        self.name_prj = os.path.basename(path_prj)  # name of project
        self.absolute_path_prj_xml = os.path.join(self.path_prj, self.name_prj + '.habby')
        # hdf5 attributes fix
        self.extensions = ('.hyd', '.sub', '.hab')  # all available extensions
        self.export_source = "auto"  # or "manual" if export launched from data explorer
        # variables
        self.hyd_variables = ["elevation", "water_height", "water_velocity", "water_level",
                               "froude_number", "hydraulic_head", "conveyance",
                              "max_slope_bottom", "max_slope_energy", "shear_stress"]
        self.hyd_variables_computed_mesh = ["area", "h", "v", "water_level",
                               "froude_number", "hydraulic_head", "conveyance",
                              "max_slope_bottom", "max_slope_energy", "shear_stress"]
        self.hyd_variables_computed_node = ["water_level", "froude_number", "hydraulic_head", "conveyance"]
        self.sub_variables = ["substrate_coarser", "substrate_dominant"]
        # dict
        self.data_2d = None
        self.data_2d_whole = None
        self.data_description = None
        # export available list
        self.available_export_list = ["mesh_whole_profile",  # GPKG
                                      "point_whole_profile",  # GPKG
                                      "mesh_units",  # GPKG
                                      "point_units",  # GPKG
                                      "elevation_whole_profile",  # stl
                                      "variables_units",  # PVD
                                      "detailled_text",  # txt
                                      "fish_information"]  # pdf
        # hdf5 file attributes
        self.path = os.path.join(path_prj, "hdf5")  # relative path
        self.filename = hdf5_filename  # filename with extension
        self.absolute_path_file = os.path.join(self.path, self.filename)  # absolute path of filename with extension
        self.basename = hdf5_filename[:-4]  # filename without extension
        self.extension = hdf5_filename[-4:]  # extension of filename
        self.file_object = None  # file object
        if self.extension == ".hyd":
            self.hdf5_type = "hydraulic"
            self.variables = ["mesh"] + self.hyd_variables
            self.variables_computed_mesh = self.hyd_variables_computed_mesh
            self.variables_computed_node = self.hyd_variables_computed_node
        if self.extension == ".sub":
            self.hdf5_type = "substrate"
            self.variables = ["mesh"] + self.sub_variables
        if self.extension == ".hab":
            self.hdf5_type = "habitat"
            self.variables = ["mesh"] + self.sub_variables + self.hyd_variables
            self.variables_computed_mesh = self.hyd_variables_computed_mesh
            self.variables_computed_node = self.hyd_variables_computed_node
            if "ESTIMHAB" in self.filename:
                self.hdf5_type = "ESTIMHAB"

    def open_hdf5_file(self, new=False):
        # get mode
        if not new:
            mode_file = 'r+'  # Readonly, file must exist
        if new:
            mode_file = 'w'  # Read/write, file must exist

        # extension check
        if self.extension not in self.extensions:
            print(f"Warning: the extension file should be : {self.extensions}.")

        # file presence check
        try:
            # write or open hdf5 file
            self.file_object = h5py.File(name=self.absolute_path_file,
                                         mode=mode_file)
            if new:  # write + write attributes
                self.file_object.attrs['hdf5_version'] = self.hdf5_version
                self.file_object.attrs['h5py_version'] = self.h5py_version
                self.file_object.attrs['software'] = 'HABBY'
                self.file_object.attrs['software_version'] = str(HABBY_VERSION)
                self.file_object.attrs['path_project'] = self.path_prj
                self.file_object.attrs['name_project'] = self.name_prj
                self.file_object.attrs[self.extension[1:] + '_filename'] = self.filename
            if not new:
                if self.hdf5_type != "ESTIMHAB":
                    self.project_preferences = load_project_preferences(self.path_prj)

                    self.get_hdf5_attributes()

                    # create basename_output_reach_unit for output files
                    if self.extension != ".sub":
                        self.basename_output_reach_unit = []
                        for reach_num, reach_name in enumerate(self.reach_name):
                            self.basename_output_reach_unit.append([])
                            for unit_num, unit_name in enumerate(self.units_name[reach_num]):
                                self.basename_output_reach_unit[reach_num].append(
                                    self.basename + "_" + reach_name + "_" + unit_name.replace(".", "_"))
                        self.units_name_output = []
                        for reach_num, reach_name in enumerate(self.reach_name):
                            self.units_name_output.append([])
                            for unit_num, unit_name in enumerate(self.units_name[reach_num]):
                                if self.file_object.attrs["hyd_unit_type"] != 'unknown':
                                    unit_name2 = unit_name.replace(".", "_") + "_" + \
                                                 self.file_object.attrs["hyd_unit_type"].split("[")[1][:-1].replace("/",
                                                                                                                    "")  # ["/", ".", "," and " "] are forbidden for gpkg in ArcMap
                                else:
                                    unit_name2 = unit_name.replace(".", "_") + "_" + \
                                                 self.file_object.attrs["hyd_unit_type"]
                                self.units_name_output[reach_num].append(unit_name2)

        except OSError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'the hdf5 file could not be loaded.'))
            self.file_object = None

    def save_xml(self, model_type, input_file_path):
        """
        Save in project file : path (replace existing) and hdf5 name (append list)
        :param model_type: TELEMAC, HECRAS2D, ..., SUBSTRATE, HABITAT
        :param input_file_path: input file path
        """
        if not os.path.isfile(self.absolute_path_prj_xml):
            print('Error: ' + qt_tr.translate("hdf5_mod",
                                              'No project saved. Please create a project first in the General tab.'))
            return
        else:
            # load_project_preferences
            project_preferences = load_project_preferences(self.path_prj)

            # change values
            if self.filename in project_preferences[model_type]["hdf5"]:
                project_preferences[model_type]["hdf5"].remove(self.filename)
            project_preferences[model_type]["hdf5"].append(self.filename)
            project_preferences[model_type]["path"] = input_file_path

            # save_project_preferences
            save_project_preferences(self.path_prj, project_preferences)

    # SET HDF5 INFORMATIONS
    def set_hdf5_attributes(self, attribute_name, attribute_value):
        # create existing hdf5
        self.open_hdf5_file(new=False)

        # set attributes
        for attrib_ind in range(len(attribute_name)):
            self.file_object.attrs[attribute_name[attrib_ind]] = str(attribute_value[attrib_ind])
        self.file_object.close()

    # GET HDF5 INFORMATIONS
    def get_hdf5_attributes(self):
        # get attributes
        hdf5_attributes_dict = dict(self.file_object.attrs.items())

        # sort
        hdf5_attributes_dict_keys = sorted(hdf5_attributes_dict.keys())
        attributes_to_the_end = ['name_project', 'path_project', 'software', 'software_version', 'h5py_version',
                                 'hdf5_version']
        hdf5_attributes_name_text = []
        hdf5_attributes_info_text = []
        # format attributes
        for attribute_name in hdf5_attributes_dict_keys:
            if attribute_name in attributes_to_the_end:
                pass
            else:
                hdf5_attributes_name_text.append(attribute_name.replace("_", " "))
                hdf5_attributes_info_text.append(str(hdf5_attributes_dict[attribute_name]))

        # set general attributes to the end
        for attribute_name in attributes_to_the_end:
            hdf5_attributes_name_text.extend([attribute_name.replace("_", " ")])
            hdf5_attributes_info_text.extend([hdf5_attributes_dict[attribute_name]])

        # to attributes
        self.hdf5_attributes_name_text = hdf5_attributes_name_text
        self.hdf5_attributes_info_text = hdf5_attributes_info_text

        if self.hdf5_type != "estimhab":
            """ get_2D_variables """
            # hydraulic
            if self.hdf5_type == "hydraulic":
                pass
            # substrate constant ==> nothing to plot
            elif self.hdf5_type == "substrate" and self.file_object.attrs["sub_mapping_method"] == "constant":
                self.variables = []

            # substrate polygon/point
            elif self.hdf5_type == "substrate" and self.file_object.attrs["sub_mapping_method"] != "constant":
                pass

            # habitat
            else:
                # get fish list
                self.fish_list = hdf5_attributes_dict["hab_fish_list"].split(", ")
                if self.fish_list == [""]:
                    self.fish_list = []
                # estithic sort for GUI (classic variables + fish variables (alphanumeric))
                self.fish_list.sort(key=str.lower)  # sort alphanumeric

                # merge
                if self.fish_list:
                    self.variables = self.variables + self.fish_list

            """ get_hdf5_reach_name """
            # units name
            reach_name = []
            hdf5_attributes = list(self.file_object.attrs.items())
            for attribute_name, attribute_data in hdf5_attributes:
                if "reach_list" in attribute_name:
                    if self.hdf5_type == "hydraulic" or self.hdf5_type == "habitat":
                        if attribute_name[:3] == "hyd":
                            reach_name = attribute_data.split(", ")
                    else:
                        if attribute_name[:3] == "sub":
                            reach_name = attribute_data.split(", ")

            # to attributes
            self.reach_name = reach_name

            """ get xml parent element name """
            if self.hdf5_type == "hydraulic":
                self.input_type = hdf5_attributes_dict["hyd_model_type"].upper()
            elif self.hdf5_type == "substrate":
                self.input_type = "SUBSTRATE"
            else:
                self.input_type = "HABITAT"

            """ get_hdf5_units_name """
            # to attributes
            if self.hdf5_type == "substrate":
                self.units_name = [["unit_0"]]
                self.nb_unit = 1
            else:
                self.units_name = self.file_object["unit_by_reach"][:].transpose().astype(np.str).tolist()
                self.nb_unit = len(self.units_name)
                self.unit_type = self.file_object.attrs["hyd_unit_type"]

    # HYDRAULIC 2D
    def create_hdf5_hyd(self, data_2d, data_2d_whole_profile, hyd_description, project_preferences):
        """
        :param data_2d: data 2d dict with keys :
        'mesh':
            'tin' : list by reach, sub list by units and sub list of numpy array type int
            (three values by mesh : triangle nodes indexes)
            'i_whole_profile', : list by reach, sub list by units and sub list of numpy array type int
            (one value by mesh : whole profile mesh indexes)
            'data':
                unknown : list by reach, sub list by units and sub list of numpy array type float
                (one value by mesh : unknown)
        'node'
            'xy' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y coordinates)
            'z' : list by reach, sub list by units and sub list of numpy array type float
            (one value by node : bottom elevation)
            'data':
                'h' : list by reach, sub list by units and sub list of numpy array type float
                (one value by node : water height)
                'v' : list by reach, sub list by units and sub list of numpy array type float
                (one value by node : water velocity)
                unknown : list by reach, sub list by units and sub list of numpy array type float
                (one value by node : unknown)
        :param data_2d_whole_profile: data 2d whole profile dict with keys :
        'mesh':
            'tin' : list by reach, sub list by units and sub list of numpy array type int
            (three values by mesh : triangle nodes indexes)
            'xy_center' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y center coordinates of triangle)
        'node'
            'xy' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y coordinates)
            'z' : list by reach, sub list by units and sub list of numpy array type float
            (one value by node : bottom elevation)
        :param hyd_description: description dict with keys :
        'hyd_filename_source' : str of input filename(s) (sep: ', ')
        'hyd_model_type' : str of hydraulic model type
        'hyd_model_dimension' : str of dimension number
        'hyd_mesh_variables_list' : str of mesh variable list (sep: ', ')
        'hyd_node_variables_list' : str of node variable list (sep: ', ')
        'hyd_epsg_code' : str of EPSG number
        'hyd_reach_list' : str of reach name(s) (sep: ', ')
        'hyd_reach_number' : str of reach total number
        'hyd_reach_type' : str of type of reach
        'hyd_unit_list' : str of list of units (sep: ', ')
        'hyd_unit_number' : str of units total number
        'hyd_unit_type' : str of units type (discharge or time) with between brackets, the unit symbol ([m3/s], [s], ..)
        ex : 'discharge [m3/s]', 'time [s]'
        'hyd_varying_mesh' : boolean
        'hyd_unit_z_equal' : boolean if all z are egual between units, 'False' if the bottom values vary
        """
        #check_data_2d_dict_size(data_2d)
        validity, error = check_data_2d_dict_validity(data_2d,
                                    int(hyd_description["hyd_reach_number"]),
                                    int(hyd_description["hyd_unit_number"]))
        if not validity:
            print(error)
            return

        # create a new hdf5
        self.open_hdf5_file(new=True)

        # save dict to attribute
        self.project_preferences = project_preferences

        # hyd_varying_mesh ?
        if len(set(hyd_description["unit_correspondence"][0])) == 1:
            hyd_description["hyd_varying_mesh"] = False
        else:
            hyd_description["hyd_varying_mesh"] = True

        if hyd_description["hyd_varying_mesh"]:
            hyd_description["hyd_unit_z_equal"] = False
        else:
            # TODO : check if all z values are equal between units
            hyd_description["hyd_unit_z_equal"] = True

        # create hyd attributes
        for attribute_name, attribute_value in list(hyd_description.items()):
            if attribute_name in ("hyd_unit_list", "hyd_unit_list_full"):
                # check if duplicate name present in unit_list
                for reach_num in range(int(hyd_description["hyd_reach_number"])):
                    if len(set(hyd_description[attribute_name][reach_num])) != len(hyd_description[attribute_name][reach_num]):
                        a = hyd_description[attribute_name][reach_num]
                        duplicates = list(set([x for x in a if a.count(x) > 1]))
                        for unit_num, unit_element in enumerate(hyd_description[attribute_name][reach_num]):
                            for duplicate in duplicates:
                                if unit_element == duplicate:
                                    hyd_description[attribute_name][reach_num][unit_num] = duplicate + "_" + str(unit_num)
                self.file_object.attrs[attribute_name] = str(attribute_value)
            else:
                if type(attribute_value) == bool:
                    self.file_object.attrs[attribute_name] = str(attribute_value)
                else:
                    if type(attribute_value) == str:
                        if "m<sup>3</sup>/s" in attribute_value:
                            attribute_value = attribute_value.replace("m<sup>3</sup>/s", "m3/s")
                        self.file_object.attrs[attribute_name] = attribute_value
                    if attribute_name == "unit_correspondence":
                        pass
                    else:
                        self.file_object.attrs[attribute_name] = attribute_value

        # data by type of model (2D)
        if int(hyd_description["hyd_model_dimension"]) <= 2:
            # dataset for unit_list
            self.file_object.create_dataset(name="unit_by_reach",
                                            shape=[len(hyd_description["hyd_unit_list"][0]),
                                                   len(hyd_description["hyd_unit_list"])],
                                            data=np.array(hyd_description["hyd_unit_list"],
                                                          dtype=h5py.string_dtype(encoding='utf-8')).transpose())
            # data = np.array(hyd_description["hyd_unit_list"]).astype(
            #     np.float).transpose())
            # dataset for unit_list
            self.file_object.create_dataset(name="unit_correspondence",
                                            shape=[len(hyd_description["unit_correspondence"][0]),
                                                   len(hyd_description["unit_correspondence"])],
                                            data=np.array(hyd_description["unit_correspondence"]).astype(
                                                np.int).transpose())

            # whole_profile
            data_whole_profile_group = self.file_object.create_group('data_2d_whole_profile')
            whole_profile_unit_corresp = []
            for reach_num in range(int(hyd_description["hyd_reach_number"])):
                whole_profile_unit_corresp.append([])
                reach_group = data_whole_profile_group.create_group('reach_' + str(reach_num))

                unit_list = list(set(hyd_description["unit_correspondence"][reach_num]))
                unit_list.sort()
                # UNIT GROUP
                for unit_index, unit_num in enumerate(unit_list):
                    # hyd_varying_mesh==False
                    if unit_list == [0]:  # one whole profile for all units
                        group_name = 'unit_all'
                    # hyd_varying_mesh==True
                    else:
                        if unit_index == len(unit_list) - 1:  # last
                            group_name = 'unit_' + str(unit_list[unit_index]) + "-" + str(int(hyd_description["hyd_unit_number"]) - 1)
                        else:  # all case
                            group_name = 'unit_' + str(unit_list[unit_index]) + "-" + str(unit_list[unit_index + 1] - 1)

                    unit_group = reach_group.create_group(group_name)
                    whole_profile_unit_corresp[reach_num].extend([group_name] * hyd_description["unit_correspondence"][reach_num].count(unit_num))

                    # MESH GROUP
                    mesh_group = unit_group.create_group('mesh')
                    mesh_group.create_dataset(name="tin",
                                              shape=data_2d_whole_profile["mesh"]["tin"][reach_num][unit_num].shape,
                                              data=data_2d_whole_profile["mesh"]["tin"][reach_num][unit_num])
                    # NODE GROUP
                    node_group = unit_group.create_group('node')
                    node_group.create_dataset(name="xy",
                                              shape=data_2d_whole_profile["node"]["xy"][reach_num][unit_num].shape,
                                              data=data_2d_whole_profile["node"]["xy"][reach_num][unit_num])
                    if hyd_description["hyd_unit_z_equal"]:
                        node_group.create_dataset(name="z",
                                                  shape=data_2d_whole_profile["node"]["z"][reach_num][0].shape,
                                                  data=data_2d_whole_profile["node"]["z"][reach_num][0])
                    else:
                        if not hyd_description["hyd_varying_mesh"]:
                            for unit_num2 in range(int(hyd_description["hyd_unit_number"])):
                                unit_group = reach_group.create_group('unit_' + str(unit_num2))
                                node_group = unit_group.create_group('node')
                                node_group.create_dataset(name="z",
                                                          shape=data_2d_whole_profile["node"]["z"][reach_num][unit_num2].shape,
                                                          data=data_2d_whole_profile["node"]["z"][reach_num][unit_num2])
                        else:
                            node_group.create_dataset(name="z",
                                                      shape=data_2d_whole_profile["node"]["z"][reach_num][unit_num].shape,
                                                      data=data_2d_whole_profile["node"]["z"][reach_num][unit_num])

            # get extent
            xMin = []
            xMax = []
            yMin = []
            yMax = []

            # data_2d
            data_group = self.file_object.create_group('data_2d')
            # REACH GROUP
            for reach_num in range(int(hyd_description["hyd_reach_number"])):
                reach_group = data_group.create_group('reach_' + str(reach_num))
                # UNIT GROUP
                for unit_num in range(int(hyd_description["hyd_unit_number"])):
                    # extent
                    xMin.append(min(data_2d["node"]["xy"][reach_num][unit_num][:, 0]))
                    xMax.append(max(data_2d["node"]["xy"][reach_num][unit_num][:, 0]))
                    yMin.append(min(data_2d["node"]["xy"][reach_num][unit_num][:, 1]))
                    yMax.append(max(data_2d["node"]["xy"][reach_num][unit_num][:, 1]))

                    unit_group = reach_group.create_group('unit_' + str(unit_num))
                    unit_group.attrs["whole_profile_corresp"] = whole_profile_unit_corresp[reach_num][unit_num]

                    # MESH GROUP
                    mesh_group = unit_group.create_group('mesh')
                    mesh_data_group = mesh_group.create_group('data')
                    mesh_group.create_dataset(name="tin",
                                              shape=data_2d["mesh"]["tin"][reach_num][unit_num].shape,
                                              data=data_2d["mesh"]["tin"][reach_num][unit_num])
                    mesh_group.create_dataset(name="i_whole_profile",
                                              shape=data_2d["mesh"]["i_whole_profile"][reach_num][unit_num].shape,
                                              data=data_2d["mesh"]["i_whole_profile"][reach_num][unit_num])
                    for mesh_variable in data_2d["mesh"]["data"].keys():
                        mesh_data_group.create_dataset(name=mesh_variable,
                                                       shape=data_2d["mesh"]["data"][mesh_variable][reach_num][unit_num].shape,
                                                       data=data_2d["mesh"]["data"][mesh_variable][reach_num][unit_num])
                    # NODE GROUP
                    node_group = unit_group.create_group('node')
                    node_data_group = node_group.create_group('data')
                    node_group.create_dataset(name="xy",
                                              shape=data_2d["node"]["xy"][reach_num][unit_num].shape,
                                              data=data_2d["node"]["xy"][reach_num][unit_num])
                    node_group.create_dataset(name="z",
                                              shape=data_2d["node"]["z"][reach_num][unit_num].shape,
                                              data=data_2d["node"]["z"][reach_num][unit_num])
                    for node_variable in data_2d["node"]["data"].keys():
                        node_data_group.create_dataset(name=node_variable,
                                                       shape=data_2d["node"]["data"][node_variable][reach_num][unit_num].shape,
                                                       data=data_2d["node"]["data"][node_variable][reach_num][unit_num])

        # get extent
        xMin = min(xMin)
        xMax = max(xMax)
        yMin = min(yMin)
        yMax = max(yMax)
        self.file_object.attrs["data_extent"] = str(xMin) + ", " + str(yMin) + ", " + str(xMax) + ", " + str(yMax)
        self.file_object.attrs["data_height"] = xMax - xMin
        self.file_object.attrs["data_width"] = yMax - yMin

        # close file
        self.file_object.close()

        # copy input files to input project folder
        copy_hydrau_input_files(hyd_description["hyd_path_filename_source"],
                                hyd_description["hyd_filename_source"],
                                self.filename,
                                os.path.join(project_preferences["path_prj"], "input"))
        # save XML
        self.save_xml(hyd_description["hyd_model_type"], hyd_description["hyd_path_filename_source"])

        # reload to export data or not
        for key in self.available_export_list:
            if True in project_preferences[key]:
                # load
                self.load_hdf5_hyd(whole_profil=True)
                # get_variables_to_compute_from_project_pref
                self.get_variables_from_dict_and_compute()
                # exports
                self.export_gpkg()
                self.export_stl()
                self.export_paraview()
                self.export_detailled_mesh_txt()
                self.export_detailled_point_txt()
                break

    def load_hdf5_hyd(self, units_index="all", whole_profil=False):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # save unit_index for computing variables
        self.units_index = units_index

        # attributes
        if self.units_index == "all":
            # load the number of time steps
            nb_t = int(self.file_object.attrs['hyd_unit_number'])
            self.units_index = list(range(nb_t))

        # get attributes
        hyd_description = dict()
        for attribute_name, attribute_value in list(self.file_object.attrs.items()):
            if type(attribute_value) == str:
                if attribute_value == "True" or attribute_value == "False":
                    hyd_description[attribute_name] = eval(attribute_value)
                else:
                    hyd_description[attribute_name] = attribute_value
            else:
                hyd_description[attribute_name] = attribute_value

        # dataset for unit_list
        hyd_description["hyd_unit_list"] = self.file_object["unit_by_reach"][:].transpose().tolist()
        hyd_description["unit_correspondence"] = self.file_object["unit_correspondence"][:].transpose().tolist()

        # WHOLE PROFIL
        if whole_profil:
            # create dict
            data_2d_whole_profile = create_empty_data_2d_whole_profile_dict(int(hyd_description['hyd_reach_number']))
            data_2d_whole_profile_group = 'data_2d_whole_profile'
            hyd_description["unit_name_whole_profile"] = []

            # for each reach
            reach_list = list(self.file_object[data_2d_whole_profile_group].keys())
            for reach_num, reach_group_name in enumerate(reach_list):
                hyd_description["unit_name_whole_profile"].append([])
                reach_group = data_2d_whole_profile_group + "/" + reach_group_name

                # for each unit
                unit_list = list(self.file_object[reach_group].keys())
                for unit_group_name in unit_list:
                    hyd_description["unit_name_whole_profile"][reach_num].append(unit_group_name)
                    unit_group = reach_group + "/" + unit_group_name

                    # for each variable_type (mesh or node or another in the future ?)
                    variable_type_list = list(self.file_object[unit_group].keys())
                    for variable_type_name in variable_type_list:
                        variable_type_group = unit_group + "/" + variable_type_name

                        # for each variable
                        variable_list = list(self.file_object[variable_type_group].keys())
                        for variable_mesh_name in variable_list:
                            variable_dataset = self.file_object[variable_type_group + "/" + variable_mesh_name][:]
                            data_2d_whole_profile[variable_type_name][variable_mesh_name][reach_num].append(variable_dataset)

        # DATA 2D
        hyd_mesh_variables_list = hyd_description["hyd_mesh_variables_list"].split(", ")
        if hyd_mesh_variables_list == ['']:
            hyd_mesh_variables_list = []
        hyd_node_variables_list = hyd_description["hyd_node_variables_list"].split(", ")
        if hyd_node_variables_list == ['']:
            hyd_node_variables_list = []

        # create dict
        data_2d = create_empty_data_2d_dict(int(hyd_description['hyd_reach_number']),
                                            mesh_variables=hyd_mesh_variables_list,
                                            node_variables=hyd_node_variables_list)
        data_2d_group = 'data_2d'
        # for each reach
        reach_list = list(self.file_object[data_2d_group].keys())
        for reach_num, reach_group_name in enumerate(reach_list):
            # group name
            reach_group = data_2d_group + "/" + reach_group_name

            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            desired_units_list = [available_unit_list[unit_index] for unit_index in self.units_index]  # get only desired_units
            for unit_group_name in desired_units_list:
                # group name
                unit_group = reach_group + "/" + unit_group_name

                # for each variable_type (mesh or node or another in the future ?)
                struct_type_list = list(self.file_object[unit_group].keys())
                for struct_type_name in struct_type_list:
                    # group name
                    struct_type_group = unit_group + "/" + struct_type_name

                    # for each struct_variable (data, i_whole_profile, tin, xy, z)
                    struct_variable = list(self.file_object[struct_type_group].keys())
                    for struct_variable_name in struct_variable:
                        if struct_variable_name == "data":
                            # group name
                            data_group = struct_type_group + "/" + struct_variable_name

                            # for each hyd_variable (h, v, ...)
                            hyd_variable_list = list(self.file_object[data_group].keys())
                            for hyd_variable_name in hyd_variable_list:
                                variable_dataset = self.file_object[data_group + "/" + hyd_variable_name][:]
                                data_2d[struct_type_name][struct_variable_name][hyd_variable_name][reach_num].append(variable_dataset)
                        else:
                            struct_dataset = self.file_object[struct_type_group + "/" + struct_variable_name][:]
                            data_2d[struct_type_name][struct_variable_name][reach_num].append(struct_dataset)

        # close file
        self.file_object.close()
        self.file_object = None

        # to attributes
        if whole_profil:
            self.data_2d = data_2d
            self.data_2d_whole = data_2d_whole_profile
            self.data_description = hyd_description
        if not whole_profil:
            self.data_2d = data_2d
            self.data_description = hyd_description

    # SUBSTRATE
    def create_hdf5_sub(self, sub_description_system, data_2d):
        # create a new hdf5
        self.open_hdf5_file(new=True)

        # create sub attributes
        for attribute_name, attribute_value in list(sub_description_system.items()):
            self.file_object.attrs[attribute_name] = attribute_value

        # POLYGON or POINT
        if sub_description_system["sub_mapping_method"] in ("polygon", "point"):
            # create specific attributes
            self.file_object.attrs['sub_default_values'] = sub_description_system["sub_default_values"]
            self.file_object.attrs['sub_epsg_code'] = sub_description_system["sub_epsg_code"]

            # get extent
            xMin = []
            xMax = []
            yMin = []
            yMax = []

            # data_2d
            data_group = self.file_object.create_group('data_2d')
            # REACH GROUP
            for reach_num in range(data_2d["nb_reach"]):
                reach_group = data_group.create_group('reach_' + str(reach_num))
                # UNIT GROUP
                for unit_num in range(data_2d["nb_unit"]):
                    unit_group = reach_group.create_group('unit_' + str(unit_num))
                    # MESH GROUP
                    mesh_group = unit_group.create_group('mesh')
                    mesh_data_group = mesh_group.create_group('data')
                    mesh_group.create_dataset(name="tin",
                                              shape=[len(data_2d["mesh"]["tin"][reach_num][unit_num]), 3],
                                              data=data_2d["mesh"]["tin"][reach_num][unit_num])
                    # mesh_data_group.create_dataset(name="sub",
                    #                           shape=[data_2d["sub"][unit_num].shape[0],
                    #                                  data_2d["sub"][unit_num].shape[1]],
                    #                           data=data_2d["sub"][unit_num])
                    for mesh_variable in data_2d["mesh"]["data"].keys():
                        mesh_data_group.create_dataset(name=mesh_variable,
                                                       shape=data_2d["mesh"]["data"][mesh_variable][reach_num][
                                                           unit_num].shape,
                                                       data=data_2d["mesh"]["data"][mesh_variable][reach_num][unit_num])

                    # NODE GROUP
                    xMin.append(min(data_2d["node"]["xy"][reach_num][unit_num][:, 0]))
                    xMax.append(max(data_2d["node"]["xy"][reach_num][unit_num][:, 0]))
                    yMin.append(min(data_2d["node"]["xy"][reach_num][unit_num][:, 1]))
                    yMax.append(max(data_2d["node"]["xy"][reach_num][unit_num][:, 1]))
                    node_group = unit_group.create_group('node')
                    node_group.create_dataset(name="xy",
                                              shape=[len(data_2d["node"]["xy"][reach_num][unit_num]), 2],
                                              data=data_2d["node"]["xy"][reach_num][unit_num])

            # get extent
            xMin = min(xMin)
            xMax = max(xMax)
            yMin = min(yMin)
            yMax = max(yMax)
            self.file_object.attrs["data_extent"] = str(xMin) + ", " + str(yMin) + ", " + str(xMax) + ", " + str(yMax)
            self.file_object.attrs["data_height"] = xMax - xMin
            self.file_object.attrs["data_width"] = yMax - yMin

        # CONSTANT
        if sub_description_system["sub_mapping_method"] == "constant":
            # create attributes
            self.file_object.attrs['sub_constant_values'] = sub_description_system["sub_default_values"]

            # add the constant value of substrate
            if sub_description_system["sub_classification_method"] == 'coarser-dominant':
                sub_class_number = 2
            if sub_description_system["sub_classification_method"] == 'percentage' and sub_description_system["sub_classification_code"] == "Cemagref":
                sub_class_number = 8
            if sub_description_system["sub_classification_method"] == 'percentage' and sub_description_system["sub_classification_code"] == "Sandre":
                sub_class_number = 12
            self.file_object.create_dataset(name="sub",
                                            shape=[1, sub_class_number],
                                            data=data_2d["sub"][0])

        # close file
        self.file_object.close()

        # copy input files to input project folder
        copy_shapefiles(os.path.join(sub_description_system["sub_path_source"], sub_description_system["sub_filename_source"]),
                        sub_description_system["name_hdf5"],
                        os.path.join(sub_description_system["path_prj"], "input"),
                        remove=False)

        # save XML
        self.save_xml("SUBSTRATE", sub_description_system["sub_path_source"])

    def load_hdf5_sub(self, convert_to_coarser_dom=False):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # get attributes
        sub_description_system = dict()
        for attribute_name, attribute_value in list(self.file_object.attrs.items()):
            sub_description_system[attribute_name] = attribute_value

        # DATA 2D
        sub_mesh_variables_list = ["sub"]
        data_2d = create_empty_data_2d_dict(1,
                                            mesh_variables=sub_mesh_variables_list)

        if sub_description_system["sub_mapping_method"] == "constant":
            data_2d["mesh"]["data"]["sub"] = self.file_object["sub"][:].tolist()[0]

        if sub_description_system["sub_mapping_method"] != "constant":
            data_2d["nb_unit"] = int(self.file_object.attrs['sub_unit_number'])
            data_2d["nb_reach"] = int(self.file_object.attrs['sub_reach_number'])
            data_group = 'data_2d'
            # for all reach
            for reach_num in range(0, data_2d["nb_reach"]):
                reach_group = data_group + "/reach_" + str(reach_num)
                # for all unit
                for t in range(0, data_2d["nb_unit"]):
                    unit_group = reach_group + "/unit_" + str(t)
                    mesh_group = unit_group + "/mesh"
                    mesh_data_group = mesh_group + "/data"
                    node_group = unit_group + "/node"
                    try:
                        # mesh
                        data_2d["mesh"]["tin"][reach_num].append(self.file_object[mesh_group + "/tin"][:])

                        # mesh data
                        for mesh_variable in sub_mesh_variables_list:
                            if mesh_variable == "sub":
                                if convert_to_coarser_dom and sub_description_system["sub_classification_method"] != "coarser-dominant":
                                    sub_array = self.file_object[mesh_data_group + "/sub"][:]
                                    sub_dominant, sub_coarser = substrate_mod.percentage_to_domcoarse(sub_array, dominant_case=1)
                                    data_2d["mesh"]["data"]["sub"][reach_num].append(np.array(list(zip(sub_coarser, sub_dominant))))

                                else:
                                    data_2d["mesh"]["data"]["sub"][reach_num].append(self.file_object[mesh_data_group + "/sub"][:])
                            else:
                                data_2d["mesh"]["data"][mesh_variable][reach_num].append(self.file_object[mesh_data_group + "/" + mesh_variable][:])

                        # node
                        data_2d["node"]["xy"][reach_num].append(self.file_object[node_group + "/xy"][:])
                    except Exception as e:
                        print('Error: ' + qt_tr.translate("hdf5_mod", 'load_hdf5_sub : ') + str(e) + "\n")
                        self.file_object.close()
                        return

        self.file_object.close()
        self.file_object = None

        # to attributes
        self.data_2d = data_2d
        self.data_description = sub_description_system

    # HABITAT 2D
    def create_hdf5_hab(self, data_2d, data_2d_whole_profile, merge_description, project_preferences):
        """
        :param data_2d: data 2d dict with keys :
        'mesh':
            'tin' : list by reach, sub list by units and sub list of numpy array type int
            (three values by mesh : triangle nodes indexes)
            'i_whole_profile', : list by reach, sub list by units and sub list of numpy array type int
            (one value by mesh : whole profile mesh indexes)
            'data':
                'sub' : list by reach, sub list by units and sub list of numpy array type float
                (one value by mesh : sub)
                unknown : list by reach, sub list by units and sub list of numpy array type float
                (one value by mesh : unknown)
        'node'
            'xy' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y coordinates)
            'z' : list by reach, sub list by units and sub list of numpy array type float
            (one value by node : bottom elevation)
            'data':
                'h' : list by reach, sub list by units and sub list of numpy array type float
                (one value by node : water height)
                'v' : list by reach, sub list by units and sub list of numpy array type float
                (one value by node : water velocity)
                unknown : list by reach, sub list by units and sub list of numpy array type float
                (one value by node : unknown)
        :param data_2d_whole_profile: data 2d whole profile dict with keys :
        'mesh':
            'tin' : list by reach, sub list by units and sub list of numpy array type int
            (three values by mesh : triangle nodes indexes)
            'xy_center' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y center coordinates of triangle)
        'node'
            'xy' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y coordinates)
            'z' : list by reach, sub list by units and sub list of numpy array type float
            (one value by node : bottom elevation)
        """

        # validity, error = check_data_2d_dict_validity(data_2d,
        #                             int(merge_description["hyd_reach_number"]),
        #                             int(merge_description["hyd_unit_number"]))
        # if not validity:
        #     print(error)
        #     return

        attributes_to_remove = (
        "hyd_unit_list", "hyd_unit_list_full", "sub_unit_list", "sub_unit_number", "sub_reach_number", "sub_unit_type",
        "hdf5_type")

        # create a new hdf5
        self.open_hdf5_file(new=True)

        # save dict to attribute
        self.project_preferences = project_preferences

        # create hab attributes
        for attribute_name, attribute_value in list(merge_description.items()):
            if attribute_name not in attributes_to_remove:
                if type(attribute_value) == bool:
                    self.file_object.attrs[attribute_name] = str(attribute_value)
                else:
                    if type(attribute_value) == str:
                        if "m<sup>3</sup>/s" in attribute_value:
                            attribute_value = attribute_value.replace("m<sup>3</sup>/s", "m3/s")
                        self.file_object.attrs[attribute_name] = attribute_value

        self.file_object.attrs["hab_fish_list"] = ", ".join([])
        self.file_object.attrs["hab_fish_number"] = str(0)
        self.file_object.attrs["hab_fish_pref_list"] = ", ".join([])
        self.file_object.attrs["hab_fish_stage_list"] = ", ".join([])

        # dataset for unit_list
        self.file_object.create_dataset(name="unit_by_reach",
                                        shape=[len(merge_description["hyd_unit_list"][0]),
                                               len(merge_description["hyd_unit_list"])],
                                        data=np.array(merge_description["hyd_unit_list"],
                                                      dtype=h5py.string_dtype(encoding='utf-8')).transpose())
                                        # data=np.array(merge_description["hyd_unit_list"]).astype(
                                        #     np.str).transpose())
        # dataset for unit_list
        self.file_object.create_dataset(name="unit_correspondence",
                                        shape=[len(merge_description["unit_correspondence"][0]),
                                               len(merge_description["unit_correspondence"])],
                                        data=np.array(merge_description["unit_correspondence"]).astype(
                                            np.int).transpose())

        # whole_profile
        data_whole_profile_group = self.file_object.create_group('data_2d_whole_profile')
        whole_profile_unit_corresp = []
        # REACH GROUP
        for reach_num in range(int(merge_description["hyd_reach_number"])):
            whole_profile_unit_corresp.append([])
            reach_group = data_whole_profile_group.create_group('reach_' + str(reach_num))

            unit_list = list(set(merge_description["unit_correspondence"][reach_num]))
            unit_list.sort()
            for unit_index, unit_num in enumerate(unit_list):
                # hyd_varying_mesh==False
                if unit_list == [0]:  # one whole profile for all units
                    group_name = 'unit_all'
                # hyd_varying_mesh==True
                else:
                    if unit_index == len(unit_list) - 1:  # last
                        group_name = 'unit_' + str(unit_list[unit_index]) + "-" + str(
                            int(merge_description["hyd_unit_number"]) - 1)
                    else:  # all case
                        group_name = 'unit_' + str(unit_list[unit_index]) + "-" + str(unit_list[unit_index + 1] - 1)

                unit_group = reach_group.create_group(group_name)
                whole_profile_unit_corresp[reach_num].extend(
                    [group_name] * merge_description["unit_correspondence"][reach_num].count(unit_num))

                # MESH GROUP
                mesh_group = unit_group.create_group('mesh')
                mesh_group.create_dataset(name="tin",
                                          shape=data_2d_whole_profile["mesh"]["tin"][reach_num][unit_num].shape,
                                          data=data_2d_whole_profile["mesh"]["tin"][reach_num][unit_num])
                # NODE GROUP
                node_group = unit_group.create_group('node')
                node_group.create_dataset(name="xy",
                                          shape=data_2d_whole_profile["node"]["xy"][reach_num][unit_num].shape,
                                          data=data_2d_whole_profile["node"]["xy"][reach_num][unit_num])
                if merge_description["hyd_unit_z_equal"]:
                    node_group.create_dataset(name="z",
                                              shape=data_2d_whole_profile["node"]["z"][reach_num][0].shape,
                                              data=data_2d_whole_profile["node"]["z"][reach_num][0])
                else:
                    if not merge_description["hyd_varying_mesh"]:
                        for unit_num2 in range(int(merge_description["hyd_unit_number"])):
                            unit_group = reach_group.create_group('unit_' + str(unit_num2))
                            node_group = unit_group.create_group('node')
                            node_group.create_dataset(name="z",
                                                      shape=data_2d_whole_profile["node"]["z"][reach_num][
                                                          unit_num2].shape,
                                                      data=data_2d_whole_profile["node"]["z"][reach_num][unit_num2])
                    else:
                        node_group.create_dataset(name="z",
                                                  shape=data_2d_whole_profile["node"]["z"][reach_num][unit_num].shape,
                                                  data=data_2d_whole_profile["node"]["z"][reach_num][unit_num])

        # get extent
        xMin = []
        xMax = []
        yMin = []
        yMax = []

        # data_2d
        data_group = self.file_object.create_group('data_2d')
        # REACH GROUP
        for reach_num in range(int(merge_description["hyd_reach_number"])):
            reach_group = data_group.create_group('reach_' + str(reach_num))
            # UNIT GROUP
            for unit_num in range(int(merge_description["hyd_unit_number"])):
                # extent
                xMin.append(min(data_2d["node"]["xy"][reach_num][unit_num][:, 0]))
                xMax.append(max(data_2d["node"]["xy"][reach_num][unit_num][:, 0]))
                yMin.append(min(data_2d["node"]["xy"][reach_num][unit_num][:, 1]))
                yMax.append(max(data_2d["node"]["xy"][reach_num][unit_num][:, 1]))

                unit_group = reach_group.create_group('unit_' + str(unit_num))
                unit_group.attrs["whole_profile_corresp"] = whole_profile_unit_corresp[reach_num][unit_num]
                unit_group.attrs['total_wet_area'] = data_2d["total_wet_area"][reach_num][unit_num]

                # MESH GROUP
                mesh_group = unit_group.create_group('mesh')
                mesh_data_group = mesh_group.create_group('data')
                _ = mesh_group.create_group('hv_data')  # used when add_fish
                mesh_group.create_dataset(name="tin",
                                          shape=data_2d["mesh"]["tin"][reach_num][unit_num].shape,
                                          data=data_2d["mesh"]["tin"][reach_num][unit_num])
                mesh_group.create_dataset(name="i_whole_profile",
                                          shape=data_2d["mesh"]["i_whole_profile"][reach_num][unit_num].shape,
                                          data=data_2d["mesh"]["i_whole_profile"][reach_num][unit_num])
                for mesh_variable in data_2d["mesh"]["data"].keys():
                    mesh_data_group.create_dataset(name=mesh_variable,
                                                   shape=data_2d["mesh"]["data"][mesh_variable][reach_num][unit_num].shape,
                                                   data=data_2d["mesh"]["data"][mesh_variable][reach_num][unit_num])
                # NODE GROUP
                node_group = unit_group.create_group('node')
                node_data_group = node_group.create_group('data')
                node_group.create_dataset(name="xy",
                                          shape=data_2d["node"]["xy"][reach_num][unit_num].shape,
                                          data=data_2d["node"]["xy"][reach_num][unit_num])
                node_group.create_dataset(name="z",
                                          shape=data_2d["node"]["z"][reach_num][unit_num].shape,
                                          data=data_2d["node"]["z"][reach_num][unit_num])
                for node_variable in data_2d["node"]["data"].keys():
                    node_data_group.create_dataset(name=node_variable,
                                                   shape=data_2d["node"]["data"][node_variable][reach_num][unit_num].shape,
                                                   data=data_2d["node"]["data"][node_variable][reach_num][unit_num])

        # get extent
        xMin = min(xMin)
        xMax = max(xMax)
        yMin = min(yMin)
        yMax = max(yMax)
        self.file_object.attrs["data_extent"] = str(xMin) + ", " + str(yMin) + ", " + str(xMax) + ", " + str(yMax)
        self.file_object.attrs["data_height"] = xMax - xMin
        self.file_object.attrs["data_width"] = yMax - yMin

        # close file
        self.file_object.close()

        # copy input files to input project folder (only not merged, .hab directly from a input file as ASCII)
        if merge_description["hyd_filename_source"] == merge_description["sub_filename_source"]:
            copy_hydrau_input_files(merge_description["hyd_path_filename_source"],
                                    merge_description["hyd_filename_source"],
                                    self.filename,
                                    os.path.join(project_preferences["path_prj"], "input"))

        # save XML
        self.save_xml("HABITAT", "")  # uppercase for xml

        # reload to export data or not
        for key in self.available_export_list:
            if True in project_preferences[key]:
                # load
                self.load_hdf5_hab(whole_profil=True)
                self.get_variables_from_dict_and_compute()

                # exports
                self.export_gpkg()
                self.export_paraview()
                self.export_detailled_mesh_txt()
                self.export_detailled_point_txt()
                break

    def load_hdf5_hab(self, units_index="all", fish_names="all", whole_profil=False, convert_to_coarser_dom=False):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # attributes
        if units_index == "all":
            # load the number of time steps
            nb_t = int(self.file_object.attrs['hyd_unit_number'])
            units_index = list(range(nb_t))

        # get hab attributes
        data_description = dict()
        for attribute_name, attribute_value in list(self.file_object.attrs.items()):
            if attribute_value == "True" or attribute_value == "False":
                data_description[attribute_name] = eval(attribute_value)
            else:
                data_description[attribute_name] = attribute_value

        if fish_names != "all":
            fish_names_existing = data_description["hab_fish_list"].split(", ")
            all_fish_exist = True
            for fish_name in fish_names:
                if fish_name not in fish_names_existing:
                    print("Error: ", fish_name, qt_tr.translate("hdf5_mod", "habitat don't exist in "), self.filename)
                    return
            if not all_fish_exist:
                return

        # dataset for unit_list
        data_description["hyd_unit_list"] = self.file_object["unit_by_reach"][:].transpose().tolist()
        data_description["unit_correspondence"] = self.file_object["unit_correspondence"][:].transpose().tolist()

        # DATA 2D WHOLE PROFIL
        if whole_profil:
            # create dict
            data_2d_whole_profile = create_empty_data_2d_whole_profile_dict(int(data_description['hyd_reach_number']))
            data_2d_whole_profile_group = 'data_2d_whole_profile'
            data_description["unit_name_whole_profile"] = []

            # for each reach
            reach_list = list(self.file_object[data_2d_whole_profile_group].keys())
            for reach_num, reach_group_name in enumerate(reach_list):
                data_description["unit_name_whole_profile"].append([])
                reach_group = data_2d_whole_profile_group + "/" + reach_group_name

                # for each unit
                unit_list = list(self.file_object[reach_group].keys())
                for unit_group_name in unit_list:
                    data_description["unit_name_whole_profile"][reach_num].append(unit_group_name)
                    unit_group = reach_group + "/" + unit_group_name

                    # for each variable_type (mesh or node or another in the future ?)
                    variable_type_list = list(self.file_object[unit_group].keys())
                    for variable_type_name in variable_type_list:
                        variable_type_group = unit_group + "/" + variable_type_name

                        # for each variable
                        variable_list = list(self.file_object[variable_type_group].keys())
                        for variable_mesh_name in variable_list:
                            variable_dataset = self.file_object[variable_type_group + "/" + variable_mesh_name][:]
                            data_2d_whole_profile[variable_type_name][variable_mesh_name][reach_num].append(variable_dataset)

        # DATA 2D
        hyd_mesh_variables_list = data_description["hyd_mesh_variables_list"].split(", ")
        if hyd_mesh_variables_list == ['']:
            hyd_mesh_variables_list = ["sub"]  # always sub in .hab
        hyd_node_variables_list = data_description["hyd_node_variables_list"].split(", ")
        if hyd_node_variables_list == ['']:
            hyd_node_variables_list = []
        data_2d = create_empty_data_2d_dict(int(data_description['hyd_reach_number']),
                                            mesh_variables=hyd_mesh_variables_list,
                                            node_variables=hyd_node_variables_list)
        data_2d["total_wet_area"] = [[] for _ in range(int(data_description['hyd_reach_number']))]
        data_description["total_wet_area"] = [[] for _ in range(int(data_description['hyd_reach_number']))]

        # fish dict
        if fish_names == "all":  # "all"
            fish_names_total_list = self.file_object.attrs["hab_fish_list"].split(", ")
            if fish_names_total_list == ['']:
                fish_names_total_list = []
        elif not fish_names:  # list of fish
            fish_names_total_list = []
        else:  # fish presence
            fish_names_total_list = fish_names
        if fish_names_total_list:
            data_2d["mesh"]["hv_data"] = dict()
            data_description["total_HV_area"] = dict()
            data_description["total_WUA_area"] = dict()
            data_description["percent_area_unknown"] = dict()
            data_description["total_wet_area"] = [[] for _ in range(int(data_description['hyd_reach_number']))]
            for fish_name in fish_names_total_list:
                data_2d["mesh"]["hv_data"][fish_name] = [[] for _ in range(int(data_description['hyd_reach_number']))]
                data_description["total_HV_area"][fish_name] = [[] for _ in range(int(data_description['hyd_reach_number']))]
                data_description["total_WUA_area"][fish_name] = [[] for _ in range(int(data_description['hyd_reach_number']))]
                data_description["percent_area_unknown"][fish_name] = [[] for _ in range(int(data_description['hyd_reach_number']))]

        data_group = 'data_2d'
        # for all reach
        for reach_num in range(0, int(data_description['hyd_reach_number'])):
            reach_group = data_group + "/reach_" + str(reach_num)
            # for all unit
            for unit_index, unit_num in enumerate(units_index):
                unit_group = reach_group + "/unit_" + str(unit_num)
                mesh_group = unit_group + "/mesh"
                mesh_data_group = mesh_group + "/data"
                mesh_hv_data_group = mesh_group + "/hv_data"
                node_group = unit_group + "/node"
                node_data_group = node_group + "/data"

                try:
                    # unit
                    data_2d["total_wet_area"][reach_num].append(self.file_object[unit_group].attrs['total_wet_area'])
                    data_description["total_wet_area"][reach_num].append(self.file_object[unit_group].attrs['total_wet_area'])
                    # mesh
                    data_2d["mesh"]["tin"][reach_num].append(self.file_object[mesh_group + "/tin"][:])
                    data_2d["mesh"]["i_whole_profile"][reach_num].append(self.file_object[mesh_group + "/i_whole_profile"][:])
                    # mesh data
                    for mesh_variable in hyd_mesh_variables_list:
                        if mesh_variable == "sub":
                            if convert_to_coarser_dom and data_description["sub_classification_method"] != "coarser-dominant":
                                sub_array = self.file_object[mesh_data_group + "/sub"][:]
                                sub_dominant, sub_coarser = substrate_mod.percentage_to_domcoarse(sub_array, dominant_case=1)
                                data_2d["mesh"]["data"]["sub"][reach_num].append(np.array(list(zip(sub_coarser, sub_dominant))))

                            else:
                                data_2d["mesh"]["data"]["sub"][reach_num].append(self.file_object[mesh_data_group + "/sub"][:])
                        else:
                            data_2d["mesh"]["data"][mesh_variable][reach_num].append(self.file_object[mesh_data_group + "/" + mesh_variable][:])

                    if fish_names_total_list:
                        for fish_name in fish_names_total_list:
                            data_2d["mesh"]["hv_data"][fish_name][reach_num].append(self.file_object[mesh_hv_data_group + "/" + fish_name][:])
                            data_description["total_HV_area"][fish_name][reach_num].append(float(self.file_object[mesh_hv_data_group + "/" + fish_name].attrs["HV"]))
                            data_description["total_WUA_area"][fish_name][reach_num].append(self.file_object[mesh_hv_data_group + "/" + fish_name].attrs["WUA"])
                            data_description["percent_area_unknown"][fish_name][reach_num].append(float(self.file_object[mesh_hv_data_group + "/" + fish_name].attrs["percent_area_unknown [%m2]"]))
                    # node
                    data_2d["node"]["xy"][reach_num].append(self.file_object[node_group + "/xy"][:])
                    data_2d["node"]["z"][reach_num].append(self.file_object[node_group + "/z"][:])
                    # node data
                    for node_variable in hyd_node_variables_list:
                        data_2d["node"]["data"][node_variable][reach_num].append(self.file_object[node_data_group + "/" + node_variable][:])
                except KeyError:
                    print('Warning: ' + qt_tr.translate("hdf5_mod", "Can't read hdf5 dataset for one or more units."))
                    self.file_object.close()
                    return

        # close file
        self.file_object.close()
        self.file_object = None

        # set to attributes
        if whole_profil:
            self.data_2d = data_2d
            self.data_2d_whole = data_2d_whole_profile
            self.data_description = data_description
        if not whole_profil:
            self.data_2d = data_2d
            self.data_description = data_description

    def add_fish_hab(self, vh_cell, area_c_all, spu_all, code_alternative_list, pref_file_list, stage_list, aquatic_animal_type_list, project_preferences):
        """
        This function takes a merge file and add habitat data to it. The habitat data is given by cell. It also save the
        velocity and the water height by cell (and not by node)

        :param hdf5_name: the name of the merge file
        :param path_hdf5: the path to this file
        :param vh_cell: the habitat value by cell
        :param area_all: total wet area by reach
        :param spu_all: total SPU by reach
        :param fish_name: the name of the fish (with the stage in it)
        """
        # open an hdf5
        self.open_hdf5_file(new=False)

        # save dict to attribute
        self.project_preferences = project_preferences

        # create name_fish_sh
        name_fish_sh = [code_alternative_list[fish_num] + "_" + stage_list[fish_num] for fish_num in range(len(code_alternative_list))]

        fish_replaced = []

        # load the number of reach
        try:
            nb_r = int(self.file_object.attrs["hyd_reach_number"])
        except KeyError:
            print(
                'Error: the number of time step is missing from :' + self.filename)
            self.file_object.close()
            return

        # load the number of time steps
        try:
            nb_t = int(self.file_object.attrs["hyd_unit_number"])
        except KeyError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'The number of time step is missing from : ') + self.filename)
            self.file_object.close()
            return

        # data_2d
        data_group = self.file_object['data_2d']
        # REACH GROUP
        for reach_num in range(nb_r):
            reach_group = data_group["reach_" + str(reach_num)]
            # UNIT GROUP
            for unit_num in range(nb_t):
                unit_group = reach_group["unit_" + str(unit_num)]
                total_wet_area = unit_group.attrs["total_wet_area"]
                # MESH GROUP
                mesh_group = unit_group["mesh"]
                mesh_hv_data_group = mesh_group["hv_data"]
                # HV by celle for each fish
                for fish_num, fish_name in enumerate(code_alternative_list):
                    if fish_name in mesh_hv_data_group:  # if exist erase it
                        del mesh_hv_data_group[fish_name]
                        fish_data_set = mesh_hv_data_group.create_dataset(name=fish_name,
                                                                  shape=vh_cell[fish_num][reach_num][unit_num].shape,
                                                                  data=vh_cell[fish_num][reach_num][unit_num])
                        fish_replaced.append(fish_name)
                    else:  # if not exist create it
                        fish_data_set = mesh_hv_data_group.create_dataset(name=fish_name,
                                                                  shape=vh_cell[fish_num][reach_num][unit_num].shape,
                                                                  data=vh_cell[fish_num][reach_num][unit_num])
                    fish_data_set.attrs['pref_file'] = pref_file_list[fish_num]
                    fish_data_set.attrs['stage'] = stage_list[fish_num]
                    fish_data_set.attrs['short_name'] = name_fish_sh[fish_num]
                    fish_data_set.attrs['WUA'] = str(spu_all[fish_num][reach_num][unit_num])
                    fish_data_set.attrs['aquatic_animal_type_list'] = aquatic_animal_type_list[fish_num]

                    if any(np.isnan(vh_cell[fish_num][reach_num][unit_num])):
                        area = np.sum(area_c_all[reach_num][unit_num][
                                          np.argwhere(~np.isnan(vh_cell[fish_num][reach_num][unit_num]))])
                        HV = spu_all[fish_num][reach_num][unit_num] / area
                        percent_area_unknown = (1 - (
                                    area / total_wet_area)) * 100  # next to 1 in top quality, next to 0 is bad or EVIL !
                    else:
                        HV = spu_all[fish_num][reach_num][unit_num] / total_wet_area
                        percent_area_unknown = 0.0

                    fish_data_set.attrs['HV'] = str(HV)
                    fish_data_set.attrs['percent_area_unknown [%m2]'] = str(percent_area_unknown)

        # get all fish names and total number
        fish_names_total_list = list(mesh_hv_data_group.keys())
        if "i_whole_profile" in fish_names_total_list:
            fish_names_total_list.remove("i_whole_profile")
        if "tin" in fish_names_total_list:
            fish_names_total_list.remove("tin")
        if "sub" in fish_names_total_list:
            fish_names_total_list.remove("sub")
        if "area" in fish_names_total_list:
            fish_names_total_list.remove("area")

        # get xml and stage fish
        xml_names = []
        stage_names = []
        names_short = []
        aquatic_animal_type_list = []
        for fish_ind, fish_name in enumerate(fish_names_total_list):
            xml_names.append(mesh_hv_data_group[fish_name].attrs['pref_file'])
            stage_names.append(mesh_hv_data_group[fish_name].attrs['stage'])
            names_short.append(mesh_hv_data_group[fish_name].attrs['short_name'])
            aquatic_animal_type_list.append(mesh_hv_data_group[fish_name].attrs['aquatic_animal_type_list'])

        # set to attributes
        self.file_object.attrs["hab_fish_list"] = ", ".join(fish_names_total_list)
        self.file_object.attrs["hab_fish_number"] = str(len(fish_names_total_list))
        self.file_object.attrs["hab_fish_pref_list"] = ", ".join(xml_names)
        self.file_object.attrs["hab_fish_stage_list"] = ", ".join(stage_names)
        self.file_object.attrs["hab_fish_shortname_list"] = ", ".join(names_short)
        self.file_object.attrs["hab_aquatic_animal_type_list"] = ", ".join(aquatic_animal_type_list)

        if fish_replaced:
            fish_replaced = set(fish_replaced)
            fish_replaced = "; ".join(fish_replaced)
            print(f'Warning: fish(s) information replaced in hdf5 file ({fish_replaced}).\n')

        # close file
        self.file_object.close()

        # reload to add new data to attributes
        self.load_hdf5_hab(convert_to_coarser_dom=False, whole_profil=True)
        self.get_variables_from_dict_and_compute()
        self.export_gpkg()
        self.export_paraview()
        self.export_spu_txt()
        self.export_detailled_mesh_txt()
        self.export_export()

    def remove_fish_hab(self, fish_names_to_remove):
        """
        Method to remove all data of specific aquatic animal.
        Data to remove : attributes general and datasets.
        """
        # get actual attributes (hab_fish_list, hab_fish_number, hab_fish_pref_list, hab_fish_shortname_list, hab_fish_stage_list)
        hab_fish_list_before = self.file_object.attrs["hab_fish_list"].split(", ")
        hab_fish_pref_list_before = self.file_object.attrs["hab_fish_pref_list"].split(", ")
        hab_fish_shortname_list_before = self.file_object.attrs["hab_fish_shortname_list"].split(", ")
        hab_fish_stage_list_before = self.file_object.attrs["hab_fish_stage_list"].split(", ")
        hab_aquatic_animal_type_list = self.file_object.attrs["hab_aquatic_animal_type_list"].split(", ")

        # get index
        fish_index_to_remove_list = []
        for fish_name_to_remove in fish_names_to_remove:
            if fish_name_to_remove in hab_fish_list_before:
                fish_index_to_remove_list.append(hab_fish_list_before.index(fish_name_to_remove))
        fish_index_to_remove_list.sort()

        # change lists
        for index in reversed(fish_index_to_remove_list):
            hab_fish_list_before.pop(index)
            hab_fish_pref_list_before.pop(index)
            hab_fish_shortname_list_before.pop(index)
            hab_fish_stage_list_before.pop(index)
            hab_aquatic_animal_type_list.pop(index)

        # change attributes
        self.file_object.attrs["hab_fish_number"] = str(len(hab_fish_list_before))
        self.file_object.attrs["hab_fish_list"] = ", ".join(hab_fish_list_before)
        self.file_object.attrs["hab_fish_pref_list"] = ", ".join(hab_fish_pref_list_before)
        self.file_object.attrs["hab_fish_shortname_list"] = ", ".join(hab_fish_shortname_list_before)
        self.file_object.attrs["hab_fish_stage_list"] = ", ".join(hab_fish_stage_list_before)
        self.file_object.attrs["hab_aquatic_animal_type_list"] = ", ".join(hab_aquatic_animal_type_list)

        # remove data
        # load the number of reach
        try:
            nb_r = int(self.file_object.attrs["hyd_reach_number"])
        except KeyError:
            print(
                'Error: the number of time step is missing from :' + self.filename)
            return

        # load the number of time steps
        try:
            nb_t = int(self.file_object.attrs["hyd_unit_number"])
        except KeyError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'The number of time step is missing from : ') + self.filename)
            return

        # data_2d
        data_group = self.file_object['data_2d']
        # REACH GROUP
        for reach_num in range(nb_r):
            reach_group = data_group["reach_" + str(reach_num)]
            # UNIT GROUP
            for unit_num in range(nb_t):
                unit_group = reach_group["unit_" + str(unit_num)]
                mesh_group = unit_group["mesh"]
                mesh_hv_data_group = mesh_group["hv_data"]
                for fish_name_to_remove in fish_names_to_remove:
                    del mesh_hv_data_group[fish_name_to_remove]

    # COMPUTATION
    def get_variables_from_dict_and_compute(self):
        """
        Get all variables to compute from dict (project_preferences) for exports.
        :return:
        """
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1

        variables_node = []
        variables_mesh = []
        # get_variables_from_dict
        if self.project_preferences["mesh_units"][index]:
            variables_mesh = self.hyd_variables_computed_mesh
        if self.project_preferences["point_units"][index]:
            variables_node = self.hyd_variables_computed_node
        if self.project_preferences["detailled_text"][index]:
            variables_node = self.hyd_variables_computed_node
            variables_mesh = self.hyd_variables_computed_mesh
        if self.project_preferences["variables_units"][index]:
            variables_mesh = self.hyd_variables_computed_mesh
            if variables_node == self.variables_computed_node:
                pass
            else:
                variables_node = [self.project_preferences["pvd_variable_z"]]

        # compute_variables
        self.compute_variables(variables_node=variables_node, variables_mesh=variables_mesh)

    def compute_variables(self, variables_node=[], variables_mesh=[]):
        """
        Compute all necessary variables.
        :param variables_node:
        :param variables_mesh:
        :return:
        """
        if variables_mesh:
            #print("compute_variables_mesh", variables_mesh)
            # replace height by h, same for velocity
            if "water_height" in variables_mesh:
                variables_mesh[variables_mesh.index("water_height")] = "h"
            if "water_velocity" in variables_mesh:
                variables_mesh[variables_mesh.index("water_velocity")] = "v"

            # create keys and empty list
            for variable in variables_mesh:
                self.data_2d["mesh"]["data"][variable] = []

            # for all reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):

                # append empty list
                for variable in variables_mesh:
                    self.data_2d["mesh"]["data"][variable].append([])

                # for all units
                for unit_num in range(len(self.data_2d["mesh"]["tin"][reach_num])):
                    for variable in variables_mesh:
                        # compute area mean
                        if variable == "area":
                            area = c_mesh_area(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                            self.data_2d["node"]["xy"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(area)

                        # compute height mean
                        elif variable == "h":
                            h = c_mesh_mean_from_node_values(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                             self.data_2d["node"]["data"]["h"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(h)

                        # compute velocity mean
                        elif variable == "v":
                            v = c_mesh_mean_from_node_values(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                             self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(v)

                        # compute water_level
                        elif variable == "water_level":
                            water_level = c_mesh_water_level(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                           self.data_2d["node"]["z"][reach_num][unit_num],
                                                           self.data_2d["node"]["data"]["h"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(water_level)

                        # compute froude
                        elif variable == "froude_number":
                            froude = c_mesh_froude(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                   self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                   self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(froude)

                        # compute hydraulic_head
                        elif variable == "hydraulic_head":
                            hydraulic_head = c_mesh_hydraulic_head(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                                   self.data_2d["node"]["z"][reach_num][unit_num],
                                                                   self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                                   self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(hydraulic_head)

                        # compute conveyance
                        elif variable == "conveyance":
                            conveyance = c_mesh_conveyance(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                           self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                           self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(conveyance)

                        # compute max_slope_bottom
                        elif variable == "max_slope_bottom":
                            max_slope_bottom = c_mesh_max_slope_bottom(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                                       self.data_2d["node"]["xy"][reach_num][unit_num],
                                                                       self.data_2d["node"]["z"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(max_slope_bottom)

                        # compute max_slope_energy
                        elif variable == "max_slope_energy":
                            max_slope_bottom = c_mesh_max_slope_energy(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                                       self.data_2d["node"]["xy"][reach_num][unit_num],
                                                                       self.data_2d["node"]["z"][reach_num][unit_num],
                                                                       self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                                       self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(max_slope_bottom)

                        # compute shear_stress
                        elif variable == "shear_stress":
                            shear_stress = c_mesh_shear_stress(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                                               self.data_2d["node"]["xy"][reach_num][unit_num],
                                                               self.data_2d["node"]["z"][reach_num][unit_num],
                                                               self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                               self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["mesh"]["data"][variable][reach_num].append(shear_stress)

        if variables_node:
            #print("compute_variables_node", variables_node)
            # replace height by h, same for velocity
            if "water_height" in variables_node:
                variables_node[variables_node.index("water_height")] = "h"
            if "water_velocity" in variables_node:
                variables_node[variables_node.index("water_velocity")] = "v"

            # create keys and empty list
            for variable in variables_node:
                self.data_2d["node"]["data"][variable] = []

            # for all reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):

                # append empty list
                for variable in variables_node:
                    self.data_2d["node"]["data"][variable].append([])

                # for all units
                for unit_num in range(len(self.data_2d["mesh"]["tin"][reach_num])):
                    for variable in variables_node:
                        # compute water_level
                        if variable == "water_level":
                            water_level = c_node_water_level(self.data_2d["node"]["z"][reach_num][unit_num],
                                                             self.data_2d["node"]["data"]["h"][reach_num][unit_num])
                            self.data_2d["node"]["data"][variable][reach_num].append(water_level)

                        # compute froude
                        if variable == "froude_number":
                            froude_number = c_node_froude(self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                   self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["node"]["data"][variable][reach_num].append(froude_number)

                        # compute hydraulic_head
                        if variable == "hydraulic_head":
                            hydraulic_head = c_node_hydraulic_head(self.data_2d["node"]["z"][reach_num][unit_num],
                                                                   self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                                   self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["node"]["data"][variable][reach_num].append(hydraulic_head)

                        # compute conveyance
                        if variable == "conveyance":
                            conveyance = c_node_conveyance(self.data_2d["node"]["data"]["h"][reach_num][unit_num],
                                                             self.data_2d["node"]["data"]["v"][reach_num][unit_num])
                            self.data_2d["node"]["data"][variable][reach_num].append(conveyance)

    # HABITAT ESTIMHAB
    def create_hdf5_estimhab(self, estimhab_dict, project_preferences):
        # create a new hdf5
        self.open_hdf5_file(new=True)

        # hdf5_type
        self.hdf5_type = "ESTIMHAB"

        # save dict to attribute
        self.project_preferences = project_preferences

        # intput data
        self.file_object.attrs["path_bio_estimhab"] = estimhab_dict["path_bio"]
        self.file_object.create_dataset('qmes', [2, 1], data=estimhab_dict["q"])
        self.file_object.create_dataset("wmes", [2, 1], data=estimhab_dict["w"])
        self.file_object.create_dataset("hmes", [2, 1], data=estimhab_dict["h"])
        self.file_object.create_dataset("q50", [1, 1], data=estimhab_dict["q50"])
        self.file_object.create_dataset("qrange", [2, 1], data=estimhab_dict["qrange"])
        self.file_object.create_dataset("substrate", [1, 1], data=estimhab_dict["substrate"])
        xml_list = [n.encode("ascii", "ignore") for n in estimhab_dict["xml_list"]]  # unicode is not ok with hdf5
        fish_list = [n.encode("ascii", "ignore") for n in estimhab_dict["fish_list"]]  # unicode is not ok with hdf5
        self.file_object.create_dataset("xml_list", (len(xml_list), 1), data=xml_list)
        self.file_object.create_dataset("fish_list", (len(fish_list), 1), data=fish_list)

        # output data
        self.file_object.create_dataset("q_all", estimhab_dict["q_all"].shape, data=estimhab_dict["q_all"])
        self.file_object.create_dataset("h_all", estimhab_dict["h_all"].shape, data=estimhab_dict["h_all"])
        self.file_object.create_dataset("w_all", estimhab_dict["w_all"].shape, data=estimhab_dict["w_all"])
        self.file_object.create_dataset("vel_all", estimhab_dict["vel_all"].shape, data=estimhab_dict["vel_all"])
        self.file_object.create_dataset("VH", estimhab_dict["VH"].shape, data=estimhab_dict["VH"])
        self.file_object.create_dataset("SPU", estimhab_dict["SPU"].shape, data=estimhab_dict["SPU"])

        # targ
        for k, v in estimhab_dict["qtarg_dict"].items():
            self.file_object.create_dataset("targ_" + k, data=v)

        # close
        self.file_object.close()

        # load
        self.load_hdf5_estimhab()

    def load_hdf5_estimhab(self):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # load dataset
        estimhab_dict = dict(q=self.file_object["qmes"][:].flatten().tolist(),
                             w=self.file_object["wmes"][:].flatten().tolist(),
                             h=self.file_object["hmes"][:].flatten().tolist(),
                             q50=self.file_object["q50"][:].flatten().tolist()[0],
                             qrange=self.file_object["qrange"][:].flatten().tolist(),
                             substrate=self.file_object["substrate"][:].flatten().tolist()[0],
                             path_bio=self.file_object.attrs["path_bio_estimhab"],
                             xml_list=self.file_object["xml_list"][:].flatten().astype(np.str).tolist(),
                             fish_list=self.file_object["fish_list"][:].flatten().astype(np.str).tolist(),
                             q_all=self.file_object["q_all"][:],
                             h_all=self.file_object["h_all"][:],
                             w_all=self.file_object["w_all"][:],
                             vel_all=self.file_object["vel_all"][:],
                             VH=self.file_object["VH"][:],
                             SPU=self.file_object["SPU"][:])

        # targ
        for k in ["q_all", "h_all", "w_all", "vel_all", "VH", "SPU"]:
            estimhab_dict["targ_" + k] = self.file_object["targ_" + k][:]

        # close file
        self.file_object.close()
        self.file_object = None

        # save attrivbute
        self.estimhab_dict = estimhab_dict

    # EXPORT GPKG
    def export_gpkg(self, state=None):
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1

        # activated exports ?
        mesh_whole_profile_tf = self.project_preferences['mesh_whole_profile'][index]
        mesh_units_tf = self.project_preferences['mesh_units'][index]
        point_whole_profile_tf = self.project_preferences['point_whole_profile'][index]
        point_units_tf = self.project_preferences['point_units'][index]

        if not mesh_whole_profile_tf and not mesh_units_tf and not point_whole_profile_tf and not point_units_tf:
            return

        # get fish name
        fish_names = []  # init
        if self.hdf5_type == "habitat":
            fish_names = self.data_description["hab_fish_list"].split(", ")
            if fish_names == ['']:
                fish_names = []

        # CRS
        crs = osr.SpatialReference()
        if self.hdf5_type == "hydraulic":
            if self.data_description["hyd_epsg_code"] != "unknown":
                try:
                    crs.ImportFromEPSG(int(self.data_description["hyd_epsg_code"]))
                except:
                    print("Warning: " + qt_tr.translate("hdf5_mod", "Can't write .prj from EPSG code : "), self.data_description["hyd_epsg_code"])
        if self.hdf5_type == "habitat":
            if self.data_description["hab_epsg_code"] != "unknown":
                try:
                    crs.ImportFromEPSG(int(self.data_description["hab_epsg_code"]))
                except:
                    print("Warning: " + qt_tr.translate("hdf5_mod", "Can't write .prj from EPSG code : "), self.data_description["hab_epsg_code"])

        # for each reach : one gpkg
        for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
            # name
            filename = self.basename + "_" + self.reach_name[reach_num] + ".gpkg"
            driver = ogr.GetDriverByName('GPKG')  # GPKG

            # file not exist : create it
            if not os.path.isfile(os.path.join(self.path_shp, filename)):
                # gpkg file creation
                ds = driver.CreateDataSource(os.path.join(self.path_shp, filename))
                layer_names = []

            # file exist
            else:
                # if .hyd
                if self.hdf5_type == "hydraulic":
                    # if erase_id == True : remove and create
                    if self.project_preferences['erase_id']:
                        try:
                            os.remove(os.path.join(self.path_shp, filename))
                        except PermissionError:
                            print(
                                'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                            return
                    # if erase_id == False : create with new name
                    else:
                        filename = self.basename + "_" + self.reach_name[reach_num] + "_allunits_" + time.strftime(
                            "%d_%m_%Y_at_%H_%M_%S") + '.gpkg'

                    # gpkg file creation
                    ds = driver.CreateDataSource(os.path.join(self.path_shp, filename))
                    layer_names = []

                # if .hab
                if self.hdf5_type == "habitat":
                    # no fish
                    if not fish_names:
                        # if erase_id == True
                        if self.project_preferences['erase_id']:
                            try:
                                os.remove(os.path.join(self.path_shp, filename))
                            except PermissionError:
                                print(
                                    'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                                return
                        # if erase_id == False
                        else:
                            filename = self.basename + "_" + self.reach_name[reach_num] + "_allunits_" + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S") + '.gpkg'

                        # gpkg file creation
                        ds = driver.CreateDataSource(os.path.join(self.path_shp, filename))
                        layer_names = []

                    # fish
                    else:
                        # if erase_id == True
                        if self.project_preferences['erase_id']:
                            # gpkg file update
                            ds = driver.Open(os.path.join(self.path_shp, filename), 1)
                            layer_names = [ds.GetLayer(i).GetName() for i in range(ds.GetLayerCount())]
                        # if erase_id == False
                        else:
                            filename = self.basename + "_" + self.reach_name[reach_num] + "_allunits_" + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S") + '.gpkg'
                            # gpkg file creation
                            ds = driver.CreateDataSource(os.path.join(self.path_shp, filename))
                            layer_names = []

            # DATA 2D WHOLE PROFILE mesh
            if mesh_whole_profile_tf:  # only on .hyd creation
                # for all units (selected or all)
                for unit_num in range(0, len(self.data_2d_whole["mesh"]["tin"][reach_num])):
                    # layer_name
                    if not self.data_description['hyd_varying_mesh']:
                        layer_name = "mesh_wholeprofile_allunits"
                    else:
                        layer_name = "mesh_wholeprofile_" + self.data_description["unit_name_whole_profile"][reach_num][unit_num]

                    # create layer
                    if not crs.ExportToWkt():  # '' == crs unknown
                        layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPolygon)
                    else:  # crs known
                        layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPolygon)
                    # create fields (no width no precision to be specified with GPKG)
                    layer.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))  # Add one attribute
                    defn = layer.GetLayerDefn()
                    layer.StartTransaction()  # faster

                    # for each mesh
                    for mesh_num in range(0, len(self.data_2d_whole["mesh"]["tin"][reach_num][unit_num])):
                        node1 = self.data_2d_whole["mesh"]["tin"][reach_num][unit_num][mesh_num][0]  # node num
                        node2 = self.data_2d_whole["mesh"]["tin"][reach_num][unit_num][mesh_num][1]
                        node3 = self.data_2d_whole["mesh"]["tin"][reach_num][unit_num][mesh_num][2]
                        # data geom (get the triangle coordinates)
                        p1 = list(self.data_2d_whole["node"]["xy"][reach_num][unit_num][node1].tolist() + [
                            self.data_2d_whole["node"]["z"][reach_num][unit_num][node1]])
                        p2 = list(self.data_2d_whole["node"]["xy"][reach_num][unit_num][node2].tolist() + [
                            self.data_2d_whole["node"]["z"][reach_num][unit_num][node2]])
                        p3 = list(self.data_2d_whole["node"]["xy"][reach_num][unit_num][node3].tolist() + [
                            self.data_2d_whole["node"]["z"][reach_num][unit_num][node3]])
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
                        # set geometry
                        feat.SetGeometry(poly)
                        # create
                        layer.CreateFeature(feat)

                    # Save and close everything
                    layer.CommitTransaction()  # faster

                    # # stop loop in this case (if one unit in whole profile)
                    # if not self.data_description['hyd_varying_mesh']:
                    #     break

            # DATA 2D mesh
            if mesh_units_tf:
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    # name
                    layer_name = "mesh_" + self.units_name_output[reach_num][unit_num]
                    layer_exist = False

                    # if layer exist
                    if layer_name in layer_names:
                        layer_exist = True
                        if fish_names:
                            layer = ds.GetLayer(unit_num)
                            layer_defn = layer.GetLayerDefn()
                            field_names = [layer_defn.GetFieldDefn(i).GetName() for i in
                                           range(layer_defn.GetFieldCount())]
                            # erase all fish field
                            for fish_num, fish_name in enumerate(fish_names):
                                if fish_name in field_names:
                                    field_index = field_names.index(fish_name)
                                    layer.DeleteField(field_index)  # delete all features attribute of specified field
                                    field_names = [layer_defn.GetFieldDefn(i).GetName() for i in
                                                   range(layer_defn.GetFieldCount())]  # refresh list
                            # create all fish field
                            for fish_num, fish_name in enumerate(fish_names):
                                new_field = ogr.FieldDefn(fish_name, ogr.OFTReal)
                                layer.CreateField(new_field)
                            # add fish data for each mesh
                            layer.StartTransaction()  # faster
                            for mesh_num in range(0, len(self.data_2d["mesh"]["tin"][reach_num][unit_num])):
                                feature = layer.GetFeature(mesh_num + 1)  # 1 because gpkg start at 1
                                for fish_num, fish_name in enumerate(fish_names):
                                    data = self.data_2d["mesh"]["hv_data"][fish_name][reach_num][unit_num][mesh_num]
                                    feature.SetField(fish_name, data)
                                layer.SetFeature(feature)
                            layer.CommitTransaction()  # faster

                    # if layer not exist
                    if not layer_exist or not fish_names:  # not exist or merge case
                        # create layer
                        if not crs.ExportToWkt():  # '' == crs unknown
                            layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPolygon)
                        else:  # crs known
                            layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPolygon)

                        # create fields (no width no precision to be specified with GPKG)
                        layer.CreateField(ogr.FieldDefn('water_velocity', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('water_height', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('water_level', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('froude_number', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('hydraulic_head', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('conveyance', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('max_slope_bottom', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('max_slope_energy', ogr.OFTReal))
                        layer.CreateField(ogr.FieldDefn('shear_stress', ogr.OFTReal))
                        defn = layer.GetLayerDefn()
                        if self.hdf5_type == "habitat":
                            layer.CreateField(ogr.FieldDefn('area', ogr.OFTReal))
                            # sub
                            if self.data_description["sub_classification_method"] == 'coarser-dominant':
                                layer.CreateField(ogr.FieldDefn('coarser', ogr.OFTInteger))
                                layer.CreateField(ogr.FieldDefn('dominant', ogr.OFTInteger))
                            if self.data_description["sub_classification_method"] == 'percentage':
                                if self.data_description["sub_classification_code"] == "Cemagref":
                                    sub_class_number = 8
                                if self.data_description["sub_classification_code"] == "Sandre":
                                    sub_class_number = 12
                                for i in range(sub_class_number):
                                    layer.CreateField(ogr.FieldDefn('S' + str(i + 1), ogr.OFTInteger))
                            # fish
                            if fish_names:
                                for fish_num, fish_name in enumerate(fish_names):
                                    layer.CreateField(ogr.FieldDefn(fish_name, ogr.OFTReal))
                        layer.StartTransaction()  # faster

                        # for each mesh
                        for mesh_num in range(0, len(self.data_2d["mesh"]["tin"][reach_num][unit_num])):
                            node1 = self.data_2d["mesh"]["tin"][reach_num][unit_num][mesh_num][0]  # node num
                            node2 = self.data_2d["mesh"]["tin"][reach_num][unit_num][mesh_num][1]
                            node3 = self.data_2d["mesh"]["tin"][reach_num][unit_num][mesh_num][2]
                            # data geom (get the triangle coordinates)
                            p1 = list(self.data_2d["node"]["xy"][reach_num][unit_num][node1].tolist() + [
                                self.data_2d["node"]["z"][reach_num][unit_num][node1]])
                            p2 = list(self.data_2d["node"]["xy"][reach_num][unit_num][node2].tolist() + [
                                self.data_2d["node"]["z"][reach_num][unit_num][node2]])
                            p3 = list(self.data_2d["node"]["xy"][reach_num][unit_num][node3].tolist() + [
                                self.data_2d["node"]["z"][reach_num][unit_num][node3]])
                            # data attrbiutes
                            if self.hdf5_type == "habitat":
                                area = self.data_2d["mesh"]["data"]["area"][reach_num][unit_num][mesh_num]
                                sub = self.data_2d["mesh"]["data"]["sub"][reach_num][unit_num][mesh_num].tolist()
                                if fish_names:
                                    fish_data = []
                                    for fish_name in fish_names:
                                        fish_data.append(self.data_2d["mesh"]["hv_data"][fish_name][reach_num][unit_num][mesh_num])
                            # variables
                            height = self.data_2d["mesh"]["data"]["h"][reach_num][unit_num][mesh_num]
                            velocity = self.data_2d["mesh"]["data"]["v"][reach_num][unit_num][mesh_num]
                            water_level = self.data_2d["mesh"]["data"]["water_level"][reach_num][unit_num][mesh_num]
                            froude_number = self.data_2d["mesh"]["data"]["froude_number"][reach_num][unit_num][mesh_num]
                            hydraulic_head = self.data_2d["mesh"]["data"]["hydraulic_head"][reach_num][unit_num][mesh_num]
                            conveyance = self.data_2d["mesh"]["data"]["conveyance"][reach_num][unit_num][mesh_num]
                            max_slope_bottom = self.data_2d["mesh"]["data"]["max_slope_bottom"][reach_num][unit_num][mesh_num]
                            max_slope_energy = self.data_2d["mesh"]["data"]["max_slope_energy"][reach_num][unit_num][mesh_num]
                            shear_stress = self.data_2d["mesh"]["data"]["shear_stress"][reach_num][unit_num][mesh_num]

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
                            feat.SetField('water_height', height)
                            feat.SetField('water_velocity', velocity)
                            feat.SetField('water_level', water_level)
                            feat.SetField('froude_number', froude_number)
                            feat.SetField('hydraulic_head', hydraulic_head)
                            feat.SetField('conveyance', conveyance)
                            feat.SetField('max_slope_bottom', max_slope_bottom)
                            feat.SetField('max_slope_energy', max_slope_energy)
                            feat.SetField('shear_stress', shear_stress)
                            if self.hdf5_type == "habitat":
                                # area
                                feat.SetField("area", area)
                                # sub
                                if self.data_description["sub_classification_method"] == 'coarser-dominant':
                                    feat.SetField('coarser', sub[0])
                                    feat.SetField('dominant', sub[1])
                                if self.data_description["sub_classification_method"] == 'percentage':
                                    for i in range(sub_class_number):
                                        feat.SetField('S' + str(i + 1), sub[i])
                                # fish
                                if fish_names:
                                    for fish_num, fish_name in enumerate(fish_names):
                                        feat.SetField(fish_name, fish_data[fish_num])
                            # set geometry
                            feat.SetGeometry(poly)
                            # create
                            layer.CreateFeature(feat)

                        # close layer
                        layer.CommitTransaction()  # faster

            # DATA 2D WHOLE PROFILE point
            if point_whole_profile_tf:  # only on .hyd creation
                # for all units (selected or all)
                for unit_num in range(0, len(self.data_2d_whole["mesh"]["tin"][reach_num])):
                    # layer_name
                    if not self.data_description['hyd_varying_mesh']:
                        layer_name = "point_wholeprofile_allunits"
                    else:
                        layer_name = "point_wholeprofile_" + self.data_description["unit_name_whole_profile"][reach_num][unit_num]

                    # create layer
                    if not crs.ExportToWkt():  # '' == crs unknown
                        layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPoint)
                    else:  # crs known
                        layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPoint,
                                               options=['DESCRIPTION=testaaaaa'])
                    # create fields (no width no precision to be specified with GPKG)
                    layer.CreateField(ogr.FieldDefn('elevation', ogr.OFTReal))  # Add one attribute
                    defn = layer.GetLayerDefn()
                    layer.StartTransaction()  # faster

                    # for each point
                    for point_num in range(0, len(self.data_2d_whole["node"]["xy"][reach_num][unit_num])):
                        # data geom (get the triangle coordinates)
                        x = self.data_2d_whole["node"]["xy"][reach_num][unit_num][point_num][0]
                        y = self.data_2d_whole["node"]["xy"][reach_num][unit_num][point_num][1]
                        z = self.data_2d_whole["node"]["z"][reach_num][unit_num][point_num]
                        # Create a point
                        point = ogr.Geometry(ogr.wkbPoint)
                        point.AddPoint(x, y, z)
                        # Create a new feature
                        feat = ogr.Feature(defn)
                        feat.SetField('elevation', z)
                        # set geometry
                        feat.SetGeometry(point)
                        # create
                        layer.CreateFeature(feat)

                    # Save and close everything
                    layer.CommitTransaction()  # faster

                    # stop loop in this case (if one unit in whole profile)
                    if not self.data_description['hyd_varying_mesh']:
                        break

            # DATA 2D point
            if point_units_tf:
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    # name
                    layer_name = "point_" + self.units_name_output[reach_num][unit_num]
                    layer_exist = False

                    # if layer exist
                    if layer_name in layer_names:
                        layer_exist = True

                    # if layer not exist
                    if not layer_exist or not fish_names:  # not exist or merge case
                        # create layer
                        if not crs.ExportToWkt():  # '' == crs unknown
                            layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPoint)
                        else:  # crs known
                            layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPoint)

                        # create fields (no width no precision to be specified with GPKG)
                        layer.CreateField(ogr.FieldDefn('elevation', ogr.OFTReal))  # Add one attribute
                        layer.CreateField(ogr.FieldDefn('water_height', ogr.OFTReal))  # Add one attribute
                        layer.CreateField(ogr.FieldDefn('water_velocity', ogr.OFTReal))  # Add one attribute
                        layer.CreateField(ogr.FieldDefn('water_level', ogr.OFTReal))  # Add one attribute
                        layer.CreateField(ogr.FieldDefn('froude_number', ogr.OFTReal))  # Add one attribute
                        layer.CreateField(ogr.FieldDefn('hydraulic_head', ogr.OFTReal))  # Add one attribute
                        layer.CreateField(ogr.FieldDefn('conveyance', ogr.OFTReal))  # Add one attribute

                        defn = layer.GetLayerDefn()
                        layer.StartTransaction()  # faster

                        # for each point
                        for point_num in range(0, len(self.data_2d["node"]["xy"][reach_num][unit_num])):
                            # data geom (get the triangle coordinates)
                            x = self.data_2d["node"]["xy"][reach_num][unit_num][point_num][0]
                            y = self.data_2d["node"]["xy"][reach_num][unit_num][point_num][1]
                            z = self.data_2d["node"]["z"][reach_num][unit_num][point_num]
                            h = self.data_2d["node"]["data"]["h"][reach_num][unit_num][point_num]
                            v = self.data_2d["node"]["data"]["v"][reach_num][unit_num][point_num]
                            water_level = self.data_2d["node"]["data"]["water_level"][reach_num][unit_num][point_num]
                            froude_number = self.data_2d["node"]["data"]["froude_number"][reach_num][unit_num][point_num]
                            hydraulic_head = self.data_2d["node"]["data"]["hydraulic_head"][reach_num][unit_num][point_num]
                            conveyance = self.data_2d["node"]["data"]["conveyance"][reach_num][unit_num][point_num]

                            # Create a point
                            point = ogr.Geometry(ogr.wkbPoint)
                            point.AddPoint(x, y, z)
                            # Create a new feature
                            feat = ogr.Feature(defn)
                            feat.SetField('water_height', h)
                            feat.SetField('water_velocity', v)
                            feat.SetField('elevation', z)
                            feat.SetField('water_level', water_level)
                            feat.SetField('froude_number', froude_number)
                            feat.SetField('hydraulic_head', hydraulic_head)
                            feat.SetField('conveyance', conveyance)
                            # set geometry
                            feat.SetGeometry(point)
                            # create
                            layer.CreateFeature(feat)

                        # Save and close everything
                        layer.CommitTransaction()  # faster

            # close file
            ds.Destroy()

        if state:
            state.value = 1  # process finished

    # EXPORT 3D
    def export_stl(self, state=None):
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['elevation_whole_profile'][index]:
            """ create stl whole profile (to see topography) """
            # for all reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for all units (selected or all)
                for unit_num in range(0, len(self.data_2d_whole["node"]["xy"][reach_num])):
                    # get data
                    xy = self.data_2d_whole["node"]["xy"][reach_num][unit_num]
                    z = self.data_2d_whole["node"]["z"][reach_num][unit_num] * self.project_preferences["vertical_exaggeration"]
                    tin = self.data_2d_whole["mesh"]["tin"][reach_num][unit_num]
                    xyz = np.column_stack([xy, z])
                    # Create the mesh
                    stl_file = mesh.Mesh(np.zeros(tin.shape[0], dtype=mesh.Mesh.dtype))
                    for i, f in enumerate(tin):
                        for j in range(3):
                            stl_file.vectors[i][j] = xyz[f[j], :]
                    # filename
                    name_file = self.basename + "_" + self.reach_name[reach_num] + "_" + self.data_description["unit_name_whole_profile"][reach_num][unit_num] + "_wholeprofile_mesh.stl"

                    if self.project_preferences['erase_id']:  # erase file if exist ?
                        if os.path.isfile(os.path.join(self.path_visualisation, name_file)):
                            try:
                                os.remove(os.path.join(self.path_visualisation, name_file))
                            except PermissionError:
                                print(
                                    'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                                return
                    else:
                        if os.path.isfile(os.path.join(self.path_visualisation, name_file)):
                            name_file = self.basename + "_whole_profile_point_r0_t0_" + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S") + '.shp'
                    # Write the mesh to file "cube.stl"
                    stl_file.save(os.path.join(self.path_visualisation,
                                               name_file))
            if state:
                state.value = 1  # process finished

    def export_paraview(self, state=None):
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['variables_units'][index]:
            if self.extension == ".hab":
                # format the name of species and stage
                name_fish = self.data_description["hab_fish_list"].split(", ")
                if name_fish == [""]:
                    name_fish = []
                for id, n in enumerate(name_fish):
                    name_fish[id] = n.replace('_', ' ')

            file_names_all = []
            part_timestep_indice = []

            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    part_timestep_indice.append((reach_num, unit_num))
                    # create one vtu file by time step
                    x = np.ascontiguousarray(self.data_2d["node"]["xy"][reach_num][unit_num][:, 0])
                    y = np.ascontiguousarray(self.data_2d["node"]["xy"][reach_num][unit_num][:, 1])
                    try:
                        if self.project_preferences['pvd_variable_z'] == "point_elevation":
                            z = np.ascontiguousarray(self.data_2d["node"]["z"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                        elif self.project_preferences['pvd_variable_z'] == "water_height":
                            z = np.ascontiguousarray(self.data_2d["node"]["data"]["h"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                        elif self.project_preferences['pvd_variable_z'] == "water_velocity":
                            z = np.ascontiguousarray(self.data_2d["node"]["data"]["v"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                        elif self.project_preferences['pvd_variable_z'] == "water_level":
                            z = np.ascontiguousarray(self.data_2d["node"]["data"]["water_level"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                        elif self.project_preferences['pvd_variable_z'] == "hydraulic_head":
                            z = np.ascontiguousarray(self.data_2d["node"]["data"]["hydraulic_head"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                        elif self.project_preferences['pvd_variable_z'] == "conveyance":
                            z = np.ascontiguousarray(self.data_2d["node"]["data"]["conveyance"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                        elif self.project_preferences['pvd_variable_z'] == "froude_number":
                            z = np.ascontiguousarray(self.data_2d["node"]["data"]["froude_number"][reach_num][unit_num] *
                                                     self.project_preferences["vertical_exaggeration"])

                    except Warning:
                        print('Error: ' + qt_tr.translate("hdf5_mod", 'oh no!'))

                    connectivity = np.reshape(self.data_2d["mesh"]["tin"][reach_num][unit_num],
                                              (len(self.data_2d["mesh"]["tin"][reach_num][unit_num]) * 3,))
                    offsets = np.arange(3, len(self.data_2d["mesh"]["tin"][reach_num][unit_num]) * 3 + 3, 3)
                    offsets = np.array(list(map(int, offsets)), dtype=np.int64)
                    cell_types = np.zeros(len(self.data_2d["mesh"]["tin"][reach_num][unit_num]), ) + 5  # triangle
                    cell_types = np.array(list((map(int, cell_types))), dtype=np.int64)

                    cellData = {}

                    # fish
                    if self.extension == ".hab":
                        if name_fish:
                            for fish_name in self.data_description["hab_fish_list"].split(", "):
                                newkey = "HV " + fish_name
                                cellData[newkey] = self.data_2d["mesh"]["hv_data"][fish_name][reach_num][unit_num]
                        # sub
                        if self.data_description["sub_classification_method"] == 'coarser-dominant':
                            cellData["substrate_coarser"] = np.ascontiguousarray(
                                self.data_2d["mesh"]["data"]["sub"][reach_num][unit_num][:, 0])
                            cellData["substrate_dominant"] = np.ascontiguousarray(
                                self.data_2d["mesh"]["data"]["sub"][reach_num][unit_num][:, 1])

                        if self.data_description["sub_classification_method"] == 'percentage':
                            if self.data_description["sub_classification_code"] == "Cemagref":
                                sub_class_number = 8
                            if self.data_description["sub_classification_code"] == "Sandre":
                                sub_class_number = 12
                            for i in range(sub_class_number):
                                cellData['S' + str(i + 1)] = np.ascontiguousarray(
                                    self.data_2d["mesh"]["data"]["sub"][reach_num][unit_num][:, i])

                    # mesh variables
                    cellData['water_height'] = self.data_2d["mesh"]["data"]["h"][reach_num][unit_num]
                    cellData['water_velocity'] = self.data_2d["mesh"]["data"]["v"][reach_num][unit_num]
                    cellData['water_level'] = self.data_2d["mesh"]["data"]["water_level"][reach_num][unit_num]
                    cellData['froude_number'] = self.data_2d["mesh"]["data"]["froude_number"][reach_num][unit_num]
                    cellData['hydraulic_head'] = self.data_2d["mesh"]["data"]["hydraulic_head"][reach_num][unit_num]
                    cellData['conveyance'] = self.data_2d["mesh"]["data"]["conveyance"][reach_num][unit_num]
                    cellData['max_slope_bottom'] = self.data_2d["mesh"]["data"]["max_slope_bottom"][reach_num][unit_num]
                    cellData['max_slope_energy'] = self.data_2d["mesh"]["data"]["max_slope_energy"][reach_num][unit_num]
                    cellData['shear_stress'] = self.data_2d["mesh"]["data"]["shear_stress"][reach_num][unit_num]

                    # create the grid and the vtu files
                    name_file = os.path.join(self.path_visualisation,
                                             self.basename_output_reach_unit[reach_num][unit_num] + "_" + self.project_preferences['pvd_variable_z'])
                    if self.project_preferences['erase_id']:  # erase file if exist ?
                        if os.path.isfile(os.path.join(self.path_visualisation, name_file)):
                            try:
                                os.remove(os.path.join(self.path_visualisation, name_file))
                            except PermissionError:
                                print(
                                    'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                                return
                    else:
                        if os.path.isfile(os.path.join(self.path_visualisation, name_file)):
                            name_file = os.path.join(self.path_visualisation,
                                             self.basename_output_reach_unit[reach_num][unit_num] + "_" + self.project_preferences['pvd_variable_z']) + "_" + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S")
                    file_names_all.append(name_file + ".vtu")
                    hl_mod.unstructuredGridToVTK(name_file, x, y, z, connectivity, offsets, cell_types,
                                                 cellData)

            # create the "grouping" file to read all time step together
            name_here = self.basename + "_" + self.reach_name[reach_num] + "_" + self.project_preferences['pvd_variable_z'] + ".pvd"
            file_names_all = list(map(os.path.basename, file_names_all))
            if self.project_preferences['erase_id']:  # erase file if exist ?
                if os.path.isfile(os.path.join(self.path_visualisation, name_here)):
                    try:
                        os.remove(os.path.join(self.path_visualisation, name_here))
                    except PermissionError:
                        print(
                            'Error: The file .pvd is currently open in an other program. Could not be re-written \n')
                        return
            else:
                if os.path.isfile(os.path.join(self.path_visualisation, name_here)):
                    name_here = self.basename + "_" + self.reach_name[reach_num] + "_" + self.project_preferences['pvd_variable_z'] + "_" + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + '.pvd'
            paraview_mod.writePVD(os.path.join(self.path_visualisation, name_here), file_names_all,
                                  part_timestep_indice)

            if state:
                state.value = 1  # process finished

    # EXPORT TXT
    def export_spu_txt(self, state=None):
        path_txt = os.path.join(self.data_description["path_project"], "output", "text")
        if not os.path.exists(path_txt):
            print('Error: ' + qt_tr.translate("hdf5_mod", 'The path to the text file is not found. Text files not created \n'))
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['habitat_text'][index]:
            sim_name = self.units_name
            fish_names = self.data_description["hab_fish_list"].split(", ")
            if fish_names == ['']:
                fish_names = []

            unit_type = self.data_description["hyd_unit_type"][
                        self.data_description["hyd_unit_type"].find('[') + 1:self.data_description[
                            "hyd_unit_type"].find(']')]

            if self.project_preferences['language'] == 0:
                name = self.basename + '_wua.txt'
            else:
                name = self.basename + '_spu.txt'
            if os.path.isfile(os.path.join(path_txt, name)):
                if not self.project_preferences['erase_id']:
                    if self.project_preferences['language'] == 0:
                        name = self.basename + '_wua_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    else:
                        name = self.basename + '_spu_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                else:
                    try:
                        os.remove(os.path.join(path_txt, name))
                    except PermissionError:
                        print('Error: ' + qt_tr.translate("hdf5_mod", 'Could not modify text file as it is open in another program. \n'))
                        return

            name = os.path.join(path_txt, name)

            # open text to write
            with open(name, 'wt', encoding='utf-8') as f:

                # header 1
                if self.project_preferences['language'] == 0:
                    header = 'reach\tunit\treach_area'
                else:
                    header = 'troncon\tunit\taire_troncon'
                if self.project_preferences['language'] == 0:
                    header += "".join(['\tHV' + str(i) for i in range(len(fish_names))])
                    header += "".join(['\tWUA' + str(i) for i in range(len(fish_names))])
                    header += "".join(['\t%unknown' + str(i) for i in range(len(fish_names))])
                else:
                    header += "".join(['\tVH' + str(i) for i in range(len(fish_names))])
                    header += "".join(['\tSPU' + str(i) for i in range(len(fish_names))])
                    header += "".join(['\t%inconnu' + str(i) for i in range(len(fish_names))])
                header += '\n'
                f.write(header)
                # header 2
                header = '[]\t[' + unit_type + ']\t[m2]'
                header += "".join(['\t[]' for _ in range(len(fish_names))])
                header += "".join(['\t[m2]' for _ in range(len(fish_names))])
                header += "".join(['\t[%m2]' for _ in range(len(fish_names))])
                header += '\n'
                f.write(header)
                # header 3
                header = 'all\tall\tall '
                for fish_name in fish_names * 3:
                    header += '\t' + fish_name.replace(' ', '_')
                header += '\n'
                f.write(header)

                for reach_num in range(0, len(self.data_2d["total_wet_area"])):
                    for unit_num in range(0, len(self.data_2d["total_wet_area"][reach_num])):
                        area_reach = self.data_2d["total_wet_area"][reach_num][unit_num]
                        if not sim_name:
                            data_here = str(reach_num) + '\t' + str(unit_num) + '\t' + str(area_reach)
                        else:
                            data_here = str(reach_num) + '\t' + str(sim_name[reach_num][unit_num]) + '\t' + str(
                                area_reach)
                        # HV
                        for fish_name in fish_names:
                            try:
                                wua_fish = self.data_description["total_WUA_area"][fish_name][reach_num][unit_num]
                                data_here += '\t' + str(float(wua_fish) / float(area_reach))
                            except TypeError:
                                data_here += '\t' + 'NaN'
                        # WUA
                        for fish_name in fish_names:
                            wua_fish = self.data_description["total_WUA_area"][fish_name][reach_num][unit_num]
                            data_here += '\t' + str(wua_fish)
                        # %unknwon
                        for fish_name in fish_names:
                            wua_fish = self.data_description["percent_area_unknown"][fish_name][reach_num][unit_num]
                            data_here += '\t' + str(wua_fish)

                        data_here += '\n'

                        # change decimal point
                        locale = QLocale()
                        if locale.decimalPoint() == ",":
                            data_here = data_here.replace('.', ',')

                        # write file
                        f.write(data_here)

            if state:
                state.value = 1  # process finished

    def export_detailled_txt(self, state=None):
        self.export_detailled_mesh_txt()
        self.export_detailled_point_txt()
        if state:
            state.value = 1  # process finished

    def export_detailled_mesh_txt(self, state=None):
        """
        detailled mesh
        """
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['detailled_text'][index]:
            path_txt = os.path.join(self.data_description["path_project"], "output", "text")
            if not os.path.exists(path_txt):
                print('Error: ' + qt_tr.translate("hdf5_mod", 'The path to the text file is not found. Text files not created \n'))

            if self.hdf5_type == "habitat":
                fish_names = self.data_description["hab_fish_list"].split(", ")
                if fish_names != ['']:
                    fish_names = self.data_description["hab_fish_list"].split(", ")
                else:
                    fish_names = []

            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    name = self.basename_output_reach_unit[reach_num][unit_num] + "_" + qt_tr.translate("hdf5_mod", "detailled_mesh") + ".txt"
                    if os.path.isfile(os.path.join(path_txt, name)):
                        if not self.project_preferences['erase_id']:
                            name = self.basename_output_reach_unit[reach_num][unit_num] + "_" + qt_tr.translate(
                                "hdf5_mod", "detailled_mesh") + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                        else:
                            try:
                                os.remove(os.path.join(path_txt, name))
                            except PermissionError:
                                print('Error: ' + qt_tr.translate("hdf5_mod", 'Could not modify text file as it is open in another program. \n'))
                                return
                    name = os.path.join(path_txt, name)

                    # open text to write
                    with open(name, 'wt', encoding='utf-8') as f:
                        # header 1
                        text_to_write_str_list = [qt_tr.translate("hdf5_mod", "area"),
                                       qt_tr.translate("hdf5_mod", "water_height"),
                                       qt_tr.translate("hdf5_mod", "water_velocity"),
                                       qt_tr.translate("hdf5_mod", "water_level"),
                                       qt_tr.translate("hdf5_mod", "froude_number"),
                                       qt_tr.translate("hdf5_mod", "hydraulic_head"),
                                       qt_tr.translate("hdf5_mod", "conveyance"),
                                       qt_tr.translate("hdf5_mod", "max_slope_bottom"),
                                       qt_tr.translate("hdf5_mod", "max_slope_energy"),
                                       qt_tr.translate("hdf5_mod", "shear_stress"),
                                       qt_tr.translate("hdf5_mod", "node1"),
                                       qt_tr.translate("hdf5_mod", "node2"),
                                       qt_tr.translate("hdf5_mod", "node3")]
                        text_to_write_str = "\t".join(text_to_write_str_list)

                        if self.hdf5_type == "habitat":
                            # sub
                            if self.data_description["sub_classification_method"] == 'coarser-dominant':
                                text_to_write_str += '\tsubstrate_coarser\tsubstrate_dominant'
                                sub_class_number = 2
                            if self.data_description["sub_classification_method"] == 'percentage':
                                if self.data_description["sub_classification_code"] == "Cemagref":
                                    sub_class_number = 8
                                if self.data_description["sub_classification_code"] == "Sandre":
                                    sub_class_number = 12
                                for i in range(sub_class_number):
                                    text_to_write_str += '\tsub_S' + str(i + 1)

                            if self.project_preferences['language'] == 0:
                                text_to_write_str += "".join(['\tHV' + str(i) for i in range(len(fish_names))])
                            else:
                                text_to_write_str += "".join(['\tVH' + str(i) for i in range(len(fish_names))])
                        text_to_write_str += '\n'
                        f.write(text_to_write_str)

                        # header 2
                        text_to_write_str = '[m2]\t[m]\t[m/s]\t[m]\t[]\t[m]\t[m²/s]\t[m/m]\t[m/m]\t[]\t[]\t[]\t[]'
                        if self.hdf5_type == "habitat" and fish_names:
                            text_to_write_str += "".join("\t[" + self.data_description["sub_classification_code"] + "]" for _ in
                                              range(sub_class_number))
                            text_to_write_str += "".join(['\t[' + fish + ']' for fish in fish_names])
                        f.write(text_to_write_str)

                        # data
                        text_to_write_str = ""
                        # for each mesh
                        for mesh_num in range(0, len(self.data_2d["mesh"]["tin"][reach_num][unit_num])):
                            node1 = self.data_2d["mesh"]["tin"][reach_num][unit_num][mesh_num][0]  # node num
                            node2 = self.data_2d["mesh"]["tin"][reach_num][unit_num][mesh_num][1]
                            node3 = self.data_2d["mesh"]["tin"][reach_num][unit_num][mesh_num][2]
                            area_str = str(self.data_2d["mesh"]["data"]["area"][reach_num][unit_num][mesh_num])
                            height_str = str(self.data_2d["mesh"]["data"]["h"][reach_num][unit_num][mesh_num])
                            velocity_str = str(self.data_2d["mesh"]["data"]["v"][reach_num][unit_num][mesh_num])
                            water_level_str = str(self.data_2d["mesh"]["data"]["water_level"][reach_num][unit_num][mesh_num])
                            froude_number_str = str(self.data_2d["mesh"]["data"]["froude_number"][reach_num][unit_num][mesh_num])
                            hydraulic_head_str = str(self.data_2d["mesh"]["data"]["hydraulic_head"][reach_num][unit_num][mesh_num])
                            conveyance_str = str(self.data_2d["mesh"]["data"]["conveyance"][reach_num][unit_num][mesh_num])
                            max_slope_bottom_str = str(self.data_2d["mesh"]["data"]["max_slope_bottom"][reach_num][unit_num][mesh_num])
                            max_slope_energy_str = str(self.data_2d["mesh"]["data"]["max_slope_energy"][reach_num][unit_num][mesh_num])
                            shear_stress_str = str(self.data_2d["mesh"]["data"]["shear_stress"][reach_num][unit_num][mesh_num])

                            text_to_write_str += '\n'
                            text_to_write_str += f"{area_str}\t{height_str}\t{velocity_str}\t{water_level_str}\t{froude_number_str}\t{hydraulic_head_str}\t{conveyance_str}\t{max_slope_bottom_str}\t{max_slope_energy_str}\t{shear_stress_str}\t{str(node1)}\t{str(node2)}\t{str(node3)}"

                            if self.hdf5_type == "habitat":
                                sub = self.data_2d["mesh"]["data"]["sub"][reach_num][unit_num][mesh_num]
                                text_to_write_str += "\t" + "\t".join(str(e) for e in sub.tolist())
                                if fish_names:
                                    for fish_name in fish_names:
                                        text_to_write_str += f"\t{str(self.data_2d['mesh']['hv_data'][fish_name][reach_num][unit_num][mesh_num])}"

                        # change decimal point
                        locale = QLocale()
                        if locale.decimalPoint() == ",":
                            text_to_write_str = text_to_write_str.replace('.', ',')

                        # write file
                        f.write(text_to_write_str)

            if state:
                state.value = 1  # process finished

    def export_detailled_point_txt(self, state=None):
        """
         detailled mesh
         """
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['detailled_text'][index]:
            path_txt = os.path.join(self.data_description["path_project"], "output", "text")
            if not os.path.exists(path_txt):
                print('Error: ' + qt_tr.translate("hdf5_mod", 'The path to the text file is not found. Text files not created \n'))

            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    name = self.basename_output_reach_unit[reach_num][unit_num] + "_" + qt_tr.translate("hdf5_mod",
                                                                                                        "detailled_point") + ".txt"
                    if os.path.isfile(os.path.join(path_txt, name)):
                        if not self.project_preferences['erase_id']:
                            name = self.basename_output_reach_unit[reach_num][unit_num] + "_" + qt_tr.translate(
                                "hdf5_mod", "detailled_point") + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                        else:
                            try:
                                os.remove(os.path.join(path_txt, name))
                            except PermissionError:
                                print('Error: ' + qt_tr.translate("hdf5_mod", 'Could not modify text file as it is open in another program. \n'))
                                return
                    name = os.path.join(path_txt, name)

                    # open text to write
                    with open(name, 'wt', encoding='utf-8') as f:
                        # header 1
                        text_to_write_str_list = [qt_tr.translate("hdf5_mod", "x"),
                                       qt_tr.translate("hdf5_mod", "y"),
                                       qt_tr.translate("hdf5_mod", "z"),
                                       qt_tr.translate("hdf5_mod", "water_height"),
                                       qt_tr.translate("hdf5_mod", "water_velocity"),
                                       qt_tr.translate("hdf5_mod", "water_level"),
                                       qt_tr.translate("hdf5_mod", "froude_number"),
                                       qt_tr.translate("hdf5_mod", "hydraulic_head"),
                                       qt_tr.translate("hdf5_mod", "conveyance")]
                        text_to_write_str = "\t".join(text_to_write_str_list)
                        text_to_write_str += '\n'
                        f.write(text_to_write_str)

                        # header 2 2
                        text_to_write_str = '[m]\t[m]\t[m]\t[m]\t[m/s]\t[m]\t[]\t[m]\t[m²/s]'
                        f.write(text_to_write_str)

                        # data
                        text_to_write_str = ""
                        # for each point
                        for point_num in range(0, len(self.data_2d["node"]["xy"][reach_num][unit_num])):
                            # data geom (get the triangle coordinates)
                            x = str(self.data_2d["node"]["xy"][reach_num][unit_num][point_num][0])
                            y = str(self.data_2d["node"]["xy"][reach_num][unit_num][point_num][1])
                            z = str(self.data_2d["node"]["z"][reach_num][unit_num][point_num])
                            h = str(self.data_2d["node"]["data"]["h"][reach_num][unit_num][point_num])
                            v = str(self.data_2d["node"]["data"]["v"][reach_num][unit_num][point_num])
                            water_level = str(self.data_2d["node"]["data"]["water_level"][reach_num][unit_num][point_num])
                            froude_number = str(self.data_2d["node"]["data"]["froude_number"][reach_num][unit_num][point_num])
                            hydraulic_head = str(self.data_2d["node"]["data"]["hydraulic_head"][reach_num][unit_num][point_num])
                            conveyance = str(self.data_2d["node"]["data"]["conveyance"][reach_num][unit_num][point_num])

                            text_to_write_str += '\n'
                            text_to_write_str += f"{x}\t{y}\t{z}\t{h}\t{v}\t{water_level}\t{froude_number}\t{hydraulic_head}\t{conveyance}"

                        # change decimal point
                        locale = QLocale()
                        if locale.decimalPoint() == ",":
                            text_to_write_str = text_to_write_str.replace('.', ',')

                        # write file
                        f.write(text_to_write_str)

            if state:
                state.value = 1  # process finished

    def export_export(self, state=None):
        """
        # xmlfiles, stages_chosen, path_bio, path_im_bio, path_out, self.project_preferences
        This functionc create a pdf with information about the fish.
        It tries to follow the chosen language, but
        the stage name are not translated and the decription are usually
        only given in French.

        :param xmlfiles: the name of the xmlfile (without the path!)
        :param stages_chosen: the stage chosen (might not be all stages)
        :param path_bio: the path with the biological xml file
        :param path_im_bio: the path with the images of the fish
        :param path_out: the path where to save the .pdf file
            (usually other_outputs)
        """
        # INDEX IF HYD OR HAB
        if self.extension == ".hyd":
            index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['fish_information'][index]:
            # get data
            xmlfiles = self.data_description["hab_fish_pref_list"].split(", ")
            #stages_chosen = self.data_description["hab_fish_stage_list"].split(", ")
            hab_aquatic_animal_type_list = self.data_description["hab_aquatic_animal_type_list"].split(", ")
            # remove duplicates xml
            prov_list = list(set(list(zip(xmlfiles, hab_aquatic_animal_type_list))))
            xmlfiles, hab_aquatic_animal_type_list = ([a for a, b in prov_list], [b for a, b in prov_list])

            # path_im_bio = path_bio
            path_out = os.path.join(self.path_prj, "output", "figures")

            plt.close()
            plt.rcParams['figure.figsize'] = 21, 29.7  # a4
            plt.rcParams['font.size'] = 24

            # create the pdf
            for idx, xmlfile in enumerate(xmlfiles):
                information_model_dict = bio_info_mod.get_biomodels_informations_for_database(xmlfile)

                # read additionnal info
                attributes = ['Description', 'Image', 'French_common_name',
                              'English_common_name', ]
                # careful: description is last data returned
                path_bio = os.path.dirname(xmlfile)
                path_im_bio = path_bio
                xmlfile = os.path.basename(xmlfile)
                data = bio_info_mod.load_xml_name(path_bio, attributes, [xmlfile])

                # create figure
                fake_value = Value("i", 0)

                if information_model_dict["ModelType"] != "bivariate suitability index models":
                    # read pref
                    if hab_aquatic_animal_type_list[idx] == "fish":
                        h_all, vel_all, sub_all, sub_code, code_fish, name_fish, stages = \
                            bio_info_mod.read_pref(xmlfile, hab_aquatic_animal_type_list[idx])
                    if hab_aquatic_animal_type_list[idx] == "invertebrate":
                        # open the pref
                        shear_stress_all, hem_all, hv_all, _, code_fish, name_fish, stages = \
                            bio_info_mod.read_pref(xmlfile, hab_aquatic_animal_type_list[idx])

                    # plot pref
                    if hab_aquatic_animal_type_list[idx] == "fish":
                        plot_mod.plot_suitability_curve(fake_value,
                                                                     h_all,
                                                                     vel_all,
                                                                     sub_all,
                                                                     information_model_dict["CdBiologicalModel"],
                                                                     name_fish,
                                                                     stages,
                                                                     information_model_dict["substrate_type"],
                                                                     sub_code,
                                                                     self.project_preferences, True)
                    if hab_aquatic_animal_type_list[idx] == "invertebrate":
                        plot_mod.plot_suitability_curve_invertebrate(fake_value,
                                                                                  shear_stress_all, hem_all, hv_all,
                                                                                  code_fish, name_fish,
                                                                                  stages, self.project_preferences, True)
                else:
                    # open the pref
                    [h_all, vel_all, pref_values_all, _, code_fish, name_fish, stages] = bio_info_mod.read_pref(xmlfile,
                                                                                                             hab_aquatic_animal_type_list[idx])
                    state_fake = Value("i", 0)
                    plot_mod.plot_suitability_curve_bivariate(state_fake,
                                                  h_all,
                                                  vel_all,
                                                  pref_values_all,
                                                  code_fish,
                                                  name_fish,
                                                  stages,
                                                  self.project_preferences,
                                                  True)
                # get axe and fig
                fig = plt.gcf()
                #axe_curve = plt.gca()

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
                text_all = name_fish + '\n\n' + data[0][2] + '\n\n' + information_model_dict["CdBiologicalModel"] + '\n\n' + code_fish + '\n\n'
                for idx, s in enumerate(stages):
                    text_all += s + ', '
                text_all = text_all[:-2] + '\n\n'
                plt.figtext(0.4, 0.7, text_all, fontsize=32)

                # description
                newax = fig.add_axes([0.4, 0.55, 0.56, 0.16], anchor='C',
                                   zorder=-1,
                                   frameon=True)
                newax.name = "description"
                newax.xaxis.set_ticks([])  # remove ticks
                newax.yaxis.set_ticks([])  # remove ticks
                if len(data[0][-1]) > 350:
                    decription_str = data[0][-1][:350] + '...'
                else:
                    decription_str = data[0][-1]
                newax.text(0.0, 1.0, decription_str,  # 0.4, 0.71,
                            wrap=True,
                            fontsize=32,
                            # bbox={'facecolor': 'grey', 'alpha': 0.15},
                            va='top',
                           ha="left")

                # add a fish image
                if path_im_bio:
                    fish_im_name = os.path.join(os.getcwd(), path_im_bio, data[0][0])
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
                filename = os.path.join(path_out, 'report_' + information_model_dict["CdBiologicalModel"] + self.project_preferences["format"])

                # save
                try:
                    plt.savefig(filename)
                except PermissionError:
                    print('Warning: ' + qt_tr.translate("hdf5_mod", 'Close ' + filename + ' to update fish information'))

            if state:
                state.value = 1  # process finished

    def export_estimhab(self):
        # text files output
        txt_header = 'Discharge\tHeight\tWidth\tVelocity'
        q_all = self.estimhab_dict["q_all"]
        h_all = self.estimhab_dict["h_all"]
        w_all = self.estimhab_dict["w_all"]
        vel_all = self.estimhab_dict["vel_all"]
        fish_name = self.estimhab_dict["fish_list"]
        qmes = self.estimhab_dict["q"]
        width = self.estimhab_dict["w"]
        height = self.estimhab_dict["h"]
        q50 = self.estimhab_dict["q50"]
        substrat = self.estimhab_dict["substrate"]
        qrange = self.estimhab_dict["qrange"]
        VH = self.estimhab_dict["VH"]
        SPU = self.estimhab_dict["SPU"]
        path_txt = os.path.join(self.path_prj, "output", "text")
        output_filename = "Estimhab"
        intput_filename = "Estimhab_input"

        # check if exist and erase
        if os.path.exists(os.path.join(path_txt, output_filename + '.txt')):
            if not self.project_preferences["erase_id"]:
                output_filename = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")

        # prep data
        all_data = np.vstack((q_all, h_all, w_all, vel_all))
        for f in range(0, len(fish_name)):
            txt_header += '\tVH_' + fish_name[f] + '\tSPU_' + fish_name[f]
            all_data = np.vstack((all_data, VH[f]))
            all_data = np.vstack((all_data, SPU[f]))
        if len(self.estimhab_dict["targ_q_all"]) != 0:
            all_data_targ = np.vstack((self.estimhab_dict["targ_q_all"],
                                       self.estimhab_dict["targ_h_all"],
                                       self.estimhab_dict["targ_w_all"],
                                       self.estimhab_dict["targ_vel_all"]))
            for f in range(0, len(fish_name)):
                all_data_targ = np.vstack((all_data_targ, np.expand_dims(self.estimhab_dict["targ_VH"], axis=1)[f]))
                all_data_targ = np.vstack((all_data_targ, np.expand_dims(self.estimhab_dict["targ_SPU"], axis=1)[f]))

        txt_header += '\n[m3/sec]\t[m]\t[m]\t[m/s]'
        for f in range(0, len(fish_name)):
            txt_header += '\t[-]\t[m2/100m]'

        # export estimhab output
        try:
            np.savetxt(os.path.join(path_txt, output_filename + '.txt'),
                       all_data.T,
                       header=txt_header,
                       fmt='%f',
                       delimiter='\t')  # , newline=os.linesep
        except PermissionError:
            output_filename = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            np.savetxt(os.path.join(path_txt, output_filename + '.txt'),
                       all_data.T,
                       header=txt_header,
                       fmt='%f',
                       delimiter='\t')  # , newline=os.linesep
        if len(self.estimhab_dict["targ_q_all"]) != 0:
            f = open(os.path.join(path_txt, output_filename + '.txt'), "a+")
            np.savetxt(f,
                       all_data_targ.T,
                       header="target(s) discharge(s)",
                       fmt='%f',
                       delimiter='\t')
            f.close()

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            txt_file_convert_dot_to_comma(os.path.join(path_txt, output_filename + '.txt'))

        # export estimhab input
        txtin = 'Discharge [m3/sec]:\t' + str(qmes[0]) + '\t' + str(qmes[1]) + '\n'
        txtin += 'Width [m]:\t' + str(width[0]) + '\t' + str(width[1]) + '\n'
        txtin += 'Height [m]:\t' + str(height[0]) + '\t' + str(height[1]) + '\n'
        txtin += 'Median discharge [m3/sec]:\t' + str(q50) + '\n'
        txtin += 'Mean substrate size [m]:\t' + str(substrat) + '\n'
        txtin += 'Minimum and maximum discharge [m3/sec]:\t' + str(qrange[0]) + '\t' + str(qrange[1]) + '\n'
        txtin += 'Discharge target  [m3/sec]:\t'
        if len(self.estimhab_dict["targ_q_all"]) != 0:
            for q_tar in self.estimhab_dict["targ_q_all"]:
                txtin += str(q_tar) + "\t"
            txtin += "\n"
        txtin += 'Fish chosen:\t'
        for n in fish_name:
            txtin += n + '\t'
        txtin = txtin[:-1]
        txtin += '\n'
        txtin += 'Output file:\t' + output_filename + '.txt\n'
        try:
            with open(os.path.join(path_txt, intput_filename + '.txt'), 'wt') as f:
                f.write(txtin)
        except PermissionError:
            intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            with open(os.path.join(path_txt, intput_filename + '.txt'), 'wt') as f:
                f.write(txtin)
        locale = QLocale()
        if locale.decimalPoint() == ",":
            txt_file_convert_dot_to_comma(os.path.join(path_txt, intput_filename + '.txt'))


#################################################################


def open_hdf5(hdf5_name, mode="read"):
    """
    This is a function which opens an hdf5 file and check that it exists. It does not load the data. It only opens the
    files.
    :param hdf5_name: the path and name of the hdf5 file (string)
    :param mode: read or write
    """
    # get mode
    if mode == "read":
        mode_hdf5 = 'r'
    if mode == "write":
        mode_hdf5 = 'r+'

    blob, ext = os.path.splitext(hdf5_name)
    if ext not in ('.hyd', '.sub', '.hab'):
        print("Warning: " + qt_tr.translate("hdf5_mod", "The file should be of hdf5 type ('.hyd', '.sub', '.hab')."))
    if os.path.isfile(hdf5_name):
        try:
            file = h5py.File(hdf5_name, mode_hdf5)
        except OSError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'The hdf5 file could not be loaded.\n'))
            return None
    else:
        print("Error: " + qt_tr.translate("hdf5_mod", "The hdf5 file is not found. " + hdf5_name + "\n"))
        return None

    return file


def open_hdf5_(hdf5_name, path_hdf5, mode):
    """
    A function to load hdf5 file. If hdf5_name is an absolute path, the path_hdf5 is not used. If it is a relative path,
    the path is composed of the path to the 'hdf5' folder (path_hdf5/hdf5_name) composed with hdf5_name.
    return file object open, false or '', true if error occured

    :param hdf5_name: path and file name to the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :param mode: read or write
    """
    # open the file
    if os.path.isabs(hdf5_name):
        file_ = open_hdf5(hdf5_name, mode)
    else:
        if path_hdf5:
            file_ = open_hdf5(os.path.join(path_hdf5, hdf5_name), mode)
        else:
            print('Error ' + qt_tr.translate("hdf5_mod", 'No path to the project given although a relative path was provided'))
            return "", True
    if file_ is None:
        print('Error: ' + qt_tr.translate("hdf5_mod", 'hdf5 file could not be open. \n'))
        return "", True
    return file_, False


def get_all_filename(dirname, ext):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    filenames = []
    for file in os.listdir(dirname):
        if file.endswith(ext):
            filenames.append(file)
    return filenames


def get_filename_by_type_stat(type, path):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    filenames = []
    for file in os.listdir(path):
        if file.endswith(".hab"):
            # check if not statistic
            if type in file:  # physic
                filenames.append(file)
    filenames.sort()
    return filenames


def get_filename_by_type_physic(type, path):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    type_and_extension = dict(hydraulic=".hyd",
                              substrate=".sub",
                              habitat=".hab")
    filenames = []
    for file in os.listdir(path):
        if file.endswith(type_and_extension[type]):
            # check if not statistic
            if file.endswith(".hab"):
                if not "ESTIMHAB" in file:  # physic
                    filenames.append(file)
            else:
                filenames.append(file)
    filenames.sort()
    return filenames


def get_hdf5_name(model_name, name_prj, path_prj):
    """
    This function get the name of the hdf5 file containg the hydrological data for an hydrological model of type
    model_name. If there is more than one hdf5 file, it choose the last one. The path is the path from the
    project folder. Hence, it is not the absolute path.

    :param model_name: the name of the hydrological model as written in the attribute of the xml project file
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :return: the name of the hdf5 file
    """
    # open the xml project file
    filename_path_pro = os.path.join(path_prj, name_prj + '.habby')
    if os.path.isfile(filename_path_pro):
        project_preferences = load_project_preferences(path_prj)
        name_hdf5_list = project_preferences[model_name]["hdf5"]
        return name_hdf5_list
    else:
        print('Error: ' + qt_tr.translate("hdf5_mod", 'No project found by load_hdf5'))
        return ''


def get_initial_files(path_hdf5, hdf5_name):
    """
    This function looks into a merge file to find the hydraulic and subtrate file which
    were used to create this file.
    :param path_hdf5: the path to the hdf5 file
    :param hdf5_name: the name fo this hdf5 file
    :return: the name of the substrate and hydraulic file used to create the merge file
    """

    file, bfailload = open_hdf5_(hdf5_name, path_hdf5, "read")
    if bfailload:
        return '', ''

    # get the name
    try:
        sub_ini = file.attrs['sub_filename']
    except KeyError:
        sub_ini = ''
    try:
        hydro_ini = file.attrs['hyd_filename']
    except KeyError:
        hydro_ini = ''
    file.close()
    return sub_ini, hydro_ini

