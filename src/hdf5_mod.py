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
import shutil
import sys
from pandas import DataFrame
from copy import deepcopy

from src import bio_info_mod
from src import plot_mod
from src import hl_mod
from src import paraview_mod
from src.project_properties_mod import load_project_properties, save_project_properties
from src.tools_mod import txt_file_convert_dot_to_comma, copy_hydrau_input_files, copy_shapefiles
from src.data_2d_mod import Data2d
from src.hydrosignature import hydrosignature_calculation_alt, hsexporttxt, check_hs_class_match_hydraulic_values
from src.dev_tools import profileit

from habby import HABBY_VERSION_STR


class Hdf5Management:
    def __init__(self, path_prj, hdf5_filename, new=False):
        self.gravity_acc = 9.80665
        # hdf5 version attributes
        self.h5py_version = h5py.version.version
        self.hdf5_version = h5py.version.hdf5_version
        # project attributes
        self.path_prj = path_prj  # relative path to project
        self.path_shp = os.path.join(self.path_prj, "output", "GIS")
        self.path_txt = os.path.join(self.path_prj, "output", "text")
        self.path_visualisation = os.path.join(self.path_prj, "output", "3D")
        self.path_figure = os.path.join(self.path_prj, "output", "figures")
        self.name_prj = os.path.basename(path_prj)  # name of project
        self.absolute_path_prj_xml = os.path.join(self.path_prj, self.name_prj + '.habby')
        # hdf5 attributes fix
        self.extensions = ('.hyd', '.sub', '.hab')  # all available extensions
        self.export_source = "auto"  # or "manual" if export launched from data explorer
        self.project_preferences = load_project_properties(self.path_prj)
        # dict
        self.data_2d = None
        self.data_2d_whole = None
        self.whole_profile_unit_corresp = []
        # gui
        self.hdf5_attributes_name_text = []
        self.hdf5_attributes_info_text = []
        # export available list
        self.available_export_list = ["mesh_whole_profile",  # GPKG
                                      "point_whole_profile",  # GPKG
                                      "mesh_units",  # GPKG
                                      "point_units",  # GPKG
                                      "elevation_whole_profile",  # stl
                                      "variables_units",  # PVD
                                      "detailled_text",  # txt
                                      "fish_information"]  # pdf
        # export filenames
        self.basename_output_reach_unit = []
        self.units_name_output = []
        # hdf5 file attributes
        self.path = os.path.join(path_prj, "hdf5")  # relative path
        self.filename = hdf5_filename  # filename with extension
        self.absolute_path_file = os.path.join(self.path, self.filename)  # absolute path of filename with extension
        self.basename = hdf5_filename[:-4]  # filename without extension
        self.extension = hdf5_filename[-4:]  # extension of filename
        self.file_object = None  # file object
        self.hdf5_type = None
        if self.extension == ".hyd":
            self.hdf5_type = "hydraulic"
        if self.extension == ".sub":
            self.hdf5_type = "substrate"
        if self.extension == ".hab":
            self.hdf5_type = "habitat"
            if "ESTIMHAB" in self.filename:
                self.hdf5_type = "ESTIMHAB"
        # hdf5 data attrbutes
        self.hs_calculated = False
        # create_or_open_file
        self.create_or_open_file(new)

    def create_or_open_file(self, new=False):
        # get mode
        if not new:
            mode_file = 'r+'  # Readonly, file must exist
        else:
            mode_file = 'w'  # Read/write, file must exist

        # extension check
        if self.extension not in self.extensions:
            print("Warning: extension : " + self.extension + f" is unknown. The extension file should be : {self.extensions}.")

        # file presence check
        try:
            # write or open hdf5 file
            self.file_object = h5py.File(name=self.absolute_path_file,
                                         mode=mode_file)
        except OSError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'the hdf5 file could not be loaded.'))
            self.file_object = None
            return

        if new:  # write + write attributes
            self.file_object.attrs['hdf5_version'] = self.hdf5_version
            self.file_object.attrs['h5py_version'] = self.h5py_version
            self.file_object.attrs['software'] = 'HABBY'
            self.file_object.attrs['software_version'] = str(HABBY_VERSION_STR)
            self.file_object.attrs['path_project'] = self.path_prj
            self.file_object.attrs['name_project'] = self.name_prj
            self.file_object.attrs['filename'] = self.filename
        elif not new:
            if self.hdf5_type != "ESTIMHAB":
                self.project_preferences = load_project_properties(self.path_prj)
                """ get xml parent element name """
                if self.hdf5_type == "hydraulic":
                    self.input_type = self.file_object.attrs['hyd_model_type']
                elif self.hdf5_type == "substrate":
                    self.input_type = "SUBSTRATE"
                else:
                    self.input_type = "HABITAT"

                # hs
                if self.hdf5_type == "hydraulic" or self.hdf5_type == "habitat":
                    self.hs_calculated = self.file_object.attrs["hs_calculated"]
                    if self.hs_calculated:
                        self.hs_input_class = self.file_object.attrs["hs_input_class"]

    def close_file(self):
        self.file_object.close()
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
            # load_project_properties
            project_preferences = load_project_properties(self.path_prj)

            # change values
            if self.filename in project_preferences[model_type]["hdf5"]:
                project_preferences[model_type]["hdf5"].remove(self.filename)
            project_preferences[model_type]["hdf5"].append(self.filename)
            project_preferences[model_type]["path"] = input_file_path

            # save_project_properties
            save_project_properties(self.path_prj, project_preferences)

    # HDF5 INFORMATIONS
    def set_hdf5_attributes(self, attribute_name_list=[], attribute_value_list=[]):
        # open file if not done
        if self.file_object is None:
            self.create_or_open_file(new=False)

        # specific attributes
        if attribute_name_list and attribute_value_list:
            for attribute_name, attribute_value in zip(attribute_name_list, attribute_value_list):
                self.file_object.attrs[attribute_name] = attribute_value
        # all data_2d attributes
        else:
            # global
            self.file_object.attrs["data_extent"] = self.data_2d.data_extent
            self.file_object.attrs["data_height"] = self.data_2d.data_height
            self.file_object.attrs["data_width"] = self.data_2d.data_width

            for attribute_name in self.data_2d.__dict__.keys():
                attribute_value = getattr(self.data_2d, attribute_name)
                if attribute_name in ("unit_list", "unit_list_full"):
                    # check if duplicate name present in unit_list
                    for reach_number in range(self.data_2d.reach_number):
                        if len(set(attribute_value[reach_number])) != len(attribute_value[reach_number]):
                            a = attribute_value[reach_number]
                            duplicates = list(set([x for x in a if a.count(x) > 1]))
                            for unit_number, unit_element in enumerate(attribute_value[reach_number]):
                                for duplicate in duplicates:
                                    if unit_element == duplicate:
                                        attribute_value[reach_number][unit_number] = duplicate + "_" + str(
                                            unit_number)
                    self.file_object.attrs[attribute_name] = attribute_value
                elif attribute_name == "reach_list":
                    self.file_object.attrs[attribute_name] = attribute_value
                elif attribute_name in {"hs_summary_data", "hvum", "units_index"}:  # don't save to attr
                    pass
                else:
                    if type(attribute_value) == bool:
                        self.file_object.attrs[attribute_name] = attribute_value
                    else:
                        if type(attribute_value) == str:
                            if "m<sup>3</sup>/s" in attribute_value:
                                attribute_value = attribute_value.replace("m<sup>3</sup>/s", "m3/s")
                            self.file_object.attrs[attribute_name] = attribute_value
                        else:
                            self.file_object.attrs[attribute_name] = attribute_value

            # variable_list
            if self.data_2d.hvum.hdf5_and_computable_list:
                # variables attrs
                self.data_2d.hvum.hdf5_and_computable_list.sort_by_names_gui()
                self.file_object.attrs[
                    "mesh_variable_original_name_list"] = self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().meshs().names()
                self.file_object.attrs[
                    "node_variable_original_name_list"] = self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().nodes().names()
                self.file_object.attrs[
                    "mesh_variable_original_unit_list"] = self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().meshs().units()
                self.file_object.attrs[
                    "node_variable_original_unit_list"] = self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().nodes().units()
                self.file_object.attrs[
                    "mesh_variable_original_min_list"] = ["{0:.1f}".format(min) for min in
                                                          self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().meshs().min()]
                self.file_object.attrs[
                    "node_variable_original_min_list"] = ["{0:.1f}".format(min) for min in
                                                          self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().nodes().min()]
                self.file_object.attrs[
                    "mesh_variable_original_max_list"] = ["{0:.1f}".format(max) for max in
                                                          self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().meshs().max()]
                self.file_object.attrs[
                    "node_variable_original_max_list"] = ["{0:.1f}".format(max) for max in
                                                          self.data_2d.hvum.hdf5_and_computable_list.hdf5s().no_habs().nodes().max()]

            # hab variables
            self.file_object.attrs["hab_animal_list"] = ", ".join(
                self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().names())
            self.file_object.attrs["hab_animal_number"] = str(
                len(self.data_2d.hvum.hdf5_and_computable_list.meshs().habs()))
            self.file_object.attrs["hab_animal_pref_list"] = ", ".join(
                self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().pref_files())
            self.file_object.attrs["hab_animal_stage_list"] = ", ".join(
                self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().stages())
            self.file_object.attrs["hab_animal_type_list"] = ", ".join(
                self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().aquatic_animal_types())

    def get_hdf5_attributes(self, close_file=False):
        # print("get_hdf5_attributes")
        # get attributes
        hdf5_attributes_dict = dict(self.file_object.attrs.items())

        # format and sort attributes to gui
        hdf5_attributes_dict_keys = sorted(hdf5_attributes_dict.keys())
        attributes_to_the_end = ['name_project', 'path_project', 'software', 'software_version', 'h5py_version',
                                 'hdf5_version']
        attributes_to_not_show_gui = ["hs_input_class", "hyd_unit_correspondence"]
        hdf5_attributes_name_text = []
        hdf5_attributes_info_text = []
        for attribute_name in hdf5_attributes_dict_keys:
            if attribute_name in attributes_to_the_end or attribute_name in attributes_to_not_show_gui:
                pass
            else:
                hdf5_attributes_name_text.append(attribute_name.replace("_", " "))
                attribute_value = hdf5_attributes_dict[attribute_name]
                # height, width,
                if type(attribute_value) == np.float64:
                    attribute_value = "{0:.2f}".format(attribute_value)
                # np array
                elif type(attribute_value) in {np.array, np.ndarray}:
                    if attribute_value.dtype == 'O':
                        if len(attribute_value.shape) == 1:
                            attribute_value = ", ".join(attribute_value.tolist())
                        else:
                            attribute_value = str(attribute_value.tolist())
                    else:
                        attribute_value = ", ".join(np.round(attribute_value, decimals=2).astype('str').tolist())
                else:
                    attribute_value = str(attribute_value)
                # append
                hdf5_attributes_info_text.append(attribute_value)

        # set general attributes to the end
        for attribute_name in attributes_to_the_end:
            hdf5_attributes_name_text.extend([attribute_name.replace("_", " ")])
            hdf5_attributes_info_text.extend([hdf5_attributes_dict[attribute_name]])

        # to attributes (GUI)
        self.hdf5_attributes_name_text = hdf5_attributes_name_text
        self.hdf5_attributes_info_text = hdf5_attributes_info_text

        # .hyd, .sub and .hab
        if self.hdf5_type != "estimhab":
            """ get_hdf5_reach_name """
            reach_list = self.file_object.attrs["reach_list"].tolist()
            reach_number = self.file_object.attrs["reach_number"]

            """ get_hdf5_units_name """
            unit_list = self.file_object.attrs["unit_list"].tolist()
            unit_number = len(unit_list[0])
            unit_type = self.file_object.attrs["unit_type"]

            """ light_data_2d """
            self.data_2d = Data2d(reach_number=reach_number,
                                  unit_number=unit_number)  # with no array data
            self.data_2d.set_unit_names(unit_list)
            self.data_2d.set_reach_names(reach_list)
            self.data_2d.filename = self.filename
            self.data_2d.unit_type = unit_type
            self.data_2d.data_extent = self.file_object.attrs["data_extent"]
            self.data_2d.data_height = self.file_object.attrs["data_height"]
            self.data_2d.data_width = self.file_object.attrs["data_width"]

            """ get_2D_variables """
            # hydraulic
            if self.hdf5_type == "hydraulic" or self.hdf5_type == "habitat":
                self.data_2d.hvum.get_original_computable_mesh_and_node_from_hyd(
                    hdf5_attributes_dict["mesh_variable_original_name_list"].tolist(),
                    hdf5_attributes_dict["mesh_variable_original_min_list"].tolist(),
                    hdf5_attributes_dict["mesh_variable_original_max_list"].tolist(),
                    hdf5_attributes_dict["node_variable_original_name_list"].tolist(),
                    hdf5_attributes_dict["node_variable_original_min_list"].tolist(),
                    hdf5_attributes_dict["node_variable_original_max_list"].tolist())
            # substrate
            if self.hdf5_type == "substrate" or self.hdf5_type == "habitat":
                sub_description = dict(sub_mapping_method=hdf5_attributes_dict["sub_mapping_method"],
                                       sub_classification_code=hdf5_attributes_dict["sub_classification_code"],
                                       sub_classification_method=hdf5_attributes_dict["sub_classification_method"])
                self.data_2d.hvum.detect_variable_from_sub_description(sub_description)
            # habitat
            if self.hdf5_type == "habitat":
                hab_variable_list = hdf5_attributes_dict["hab_animal_list"].split(", ")
                if hab_variable_list == ['']:
                    hab_variable_list = []
                self.data_2d.hvum.detect_variable_habitat(hab_variable_list)

            self.data_2d.hvum.hdf5_and_computable_list.sort_by_names_gui()

            # all attr
            for attribute_name in hdf5_attributes_dict_keys:
                if attribute_name[:4] not in {"mesh", "node"}:
                    attribute_value = hdf5_attributes_dict[attribute_name]
                    if type(attribute_value) in {np.array, np.ndarray}:
                        attribute_value = attribute_value.tolist()
                    setattr(self.data_2d, attribute_name, attribute_value)

            # load_data_2d_info
            if self.hdf5_type == "substrate":
                if self.data_2d.sub_mapping_method != "constant":
                    self.load_data_2d_info()
            else:
                self.load_data_2d_info()

            # output filenames
            for reach_number in range(self.data_2d.reach_number):
                self.basename_output_reach_unit.append([])
                self.units_name_output.append([])
                for unit_number in range(self.data_2d.unit_number):
                    reach_name = self.data_2d[reach_number][unit_number].reach_name
                    unit_name = self.data_2d[reach_number][unit_number].unit_name
                    self.basename_output_reach_unit[reach_number].append(self.basename + "_" + reach_name + "_" + unit_name.replace(".", "_"))
                    if unit_type != 'unknown':
                        # ["/", ".", "," and " "] are forbidden for gpkg in ArcMap
                        unit_name2 = unit_name.replace(".", "_") + "_" + unit_type.split("[")[1][:-1].replace("/", "")
                    else:
                        unit_name2 = unit_name.replace(".", "_") + "_" + unit_type
                    self.units_name_output[reach_number].append(unit_name2)

        if close_file:
            self.close_file()

    # HYDRAU 2D
    def write_whole_profile(self):
        data_whole_profile_group = self.file_object.create_group('data_2d_whole_profile')
        self.whole_profile_unit_corresp = []
        for reach_number in range(self.data_2d_whole.reach_number):
            self.whole_profile_unit_corresp.append([])
            reach_group = data_whole_profile_group.create_group('reach_' + str(reach_number))
            unit_list = list(set(self.data_2d.hyd_unit_correspondence[reach_number]))
            unit_list.sort()
            # UNIT GROUP
            for unit_index, unit_number in enumerate(unit_list):
                # hyd_varying_mesh==False
                if unit_list == [0]:  # one whole profile for all units
                    group_name = 'unit_all'
                # hyd_varying_mesh==True
                else:
                    if unit_index == len(unit_list) - 1:  # last
                        group_name = 'unit_' + str(unit_list[unit_index]) + "-" + str(self.data_2d.unit_number - 1)
                    else:  # all case
                        group_name = 'unit_' + str(unit_list[unit_index]) + "-" + str(unit_list[unit_index + 1] - 1)

                unit_group = reach_group.create_group(group_name)
                self.whole_profile_unit_corresp[reach_number].extend(
                    [group_name] * self.data_2d.hyd_unit_correspondence[reach_number].count(unit_number))

                # MESH GROUP
                mesh_group = unit_group.create_group('mesh')
                mesh_group.create_dataset(name=self.data_2d.hvum.tin.name,
                                          shape=self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name].shape,
                                          data=self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name])
                # NODE GROUP
                node_group = unit_group.create_group('node')
                node_group.create_dataset(name=self.data_2d.hvum.xy.name,
                                          shape=self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name].shape,
                                          data=self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name])
                if self.data_2d.hyd_unit_z_equal:
                    node_group.create_dataset(name=self.data_2d.hvum.z.name,
                                              shape=self.data_2d_whole[reach_number][0]["node"][self.data_2d.hvum.z.name].shape,
                                              data=self.data_2d_whole[reach_number][0]["node"][self.data_2d.hvum.z.name])
                else:
                    if not self.data_2d.hyd_varying_mesh:
                        for unit_num2 in range(self.data_2d.unit_number):
                            unit_group = reach_group.create_group('unit_' + str(unit_num2))
                            node_group = unit_group.create_group('node')
                            node_group.create_dataset(name=self.data_2d.hvum.z.name,
                                                      shape=self.data_2d_whole[reach_number][unit_num2]["node"][
                                                          self.data_2d.hvum.z.name].shape,
                                                      data=self.data_2d_whole[reach_number][unit_num2]["node"][
                                                          self.data_2d.hvum.z.name])
                    else:
                        node_group.create_dataset(name=self.data_2d.hvum.z.name,
                                                  shape=self.data_2d_whole[reach_number][unit_number]["node"][
                                                      self.data_2d.hvum.z.name].shape,
                                                  data=self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name])

    def write_data_2d(self):
        # data_2d
        data_group = self.file_object.create_group('data_2d')
        # for each reach
        for reach_number in range(self.data_2d.reach_number):
            reach_group = data_group.create_group('reach_' + str(reach_number))
            # for each unit
            for unit_number in range(self.data_2d.unit_number):
                unit_group = reach_group.create_group('unit_' + str(unit_number))

                """ mesh """
                mesh_group = unit_group.create_group('mesh')
                if self.extension == ".hab":
                    mesh_group.create_group("hv_data")  # always an empty group for futur calc hab
                # tin
                tin_dataset = mesh_group.create_dataset(name=self.data_2d.hvum.tin.name,
                                                        shape=self.data_2d[reach_number][unit_number]["mesh"][
                                                            self.data_2d.hvum.tin.name].shape,
                                                        data=self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name])
                tin_dataset.attrs[self.data_2d.hvum.tin.name] = self.data_2d.hvum.tin.descr
                # i_whole_profile
                if self.extension == ".hyd" or self.extension == ".hab":
                    i_whole_profile_dataset = mesh_group.create_dataset(name=self.data_2d.hvum.i_whole_profile.name,
                                                                        shape=self.data_2d[reach_number][unit_number]["mesh"][
                                                                            self.data_2d.hvum.i_whole_profile.name].shape,
                                                                        data=self.data_2d[reach_number][unit_number]["mesh"][
                                                                            self.data_2d.hvum.i_whole_profile.name])
                    i_whole_profile_dataset.attrs[self.data_2d.hvum.i_whole_profile.name] = self.data_2d.hvum.i_whole_profile.descr

                # data
                if self.data_2d.hvum.hdf5_and_computable_list.meshs():
                    rec_array = self.data_2d[reach_number][unit_number]["mesh"]["data"].to_records(index=False)
                    mesh_group.create_dataset(name="data",
                                              shape=rec_array.shape,
                                              data=rec_array,
                                              dtype=rec_array.dtype)

                """ node """
                node_group = unit_group.create_group('node')
                # xy
                xy_dataset = node_group.create_dataset(name=self.data_2d.hvum.xy.name,
                                                       shape=self.data_2d[reach_number][unit_number]["node"][
                                                           self.data_2d.hvum.xy.name].shape,
                                                       data=self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name])
                xy_dataset.attrs[self.data_2d.hvum.xy.name] = self.data_2d.hvum.xy.descr
                # data
                if self.data_2d.hvum.hdf5_and_computable_list.nodes():
                    rec_array = self.data_2d[reach_number][unit_number]["node"]["data"].to_records(index=False)
                    node_group.create_dataset(name="data",
                                              shape=rec_array.shape,
                                              data=rec_array,
                                              dtype=rec_array.dtype)

    def write_data_2d_info(self):
        # for each reach
        for reach_number in range(self.data_2d.reach_number):
            # for each unit
            for unit_number in range(self.data_2d.unit_number):
                """ unit info """
                unit_group = self.file_object["data_2d/reach_" + str(reach_number) + "/unit_" + str(unit_number)]
                if self.extension == ".hyd" or self.extension == ".hab":
                    unit_group.attrs["whole_profile_corresp"] = self.whole_profile_unit_corresp[reach_number][unit_number]
                    unit_group.attrs['total_wet_area'] = self.data_2d[reach_number][unit_number].total_wet_area

    def load_whole_profile(self):
        # create dict
        data_2d_whole_profile_group = 'data_2d_whole_profile'
        reach_list = list(self.file_object[data_2d_whole_profile_group].keys())

        self.data_2d_whole = Data2d(reach_number=len(reach_list),
                                    unit_number=len(self.file_object[
                                                     data_2d_whole_profile_group + "/" + reach_list[0]].keys()))  # new
        self.data_2d_whole.unit_list = []

        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            self.data_2d_whole.unit_list.append([])
            reach_group = data_2d_whole_profile_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            for unit_number, unit_group_name in enumerate(available_unit_list):
                self.data_2d_whole.unit_list[reach_number].append(unit_group_name)
                unit_group = reach_group + "/" + unit_group_name
                mesh_group = unit_group + "/mesh"
                node_group = unit_group + "/node"
                # data_2d_whole_profile
                self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name] = self.file_object[
                                                                                          mesh_group + "/tin"][:]
                self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name] = self.file_object[
                                                                                         node_group + "/xy"][:]
                self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name] = self.file_object[node_group + "/z"][
                                                                                    :]

    def load_data_2d(self):
        data_2d_group = 'data_2d'
        reach_list = list(self.file_object[data_2d_group].keys())
        removed_units_list = []
        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            # group name
            reach_group = data_2d_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            removed_units_list = list(set(list(range(len(available_unit_list)))) - set(self.units_index))
            for unit_number, unit_group_name in enumerate(available_unit_list):
                if unit_number in self.units_index:
                    # group name
                    unit_group = reach_group + "/" + unit_group_name

                    """ mesh """
                    # group
                    mesh_group = unit_group + "/mesh"
                    # i_whole_profile
                    if self.extension == ".hyd" or self.extension == ".hab":
                        self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.i_whole_profile.name] = self.file_object[
                                                                                                        mesh_group + "/i_whole_profile"][
                                                                                                    :]
                    # tin
                    self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name] = self.file_object[mesh_group + "/tin"][:]
                    # data (always ?)
                    mesh_dataframe = DataFrame()
                    if mesh_group + "/data" in self.file_object:
                        if self.user_target_list != "defaut":
                            for mesh_variable in self.data_2d.hvum.all_final_variable_list.no_habs().hdf5s().meshs():
                                mesh_dataframe[mesh_variable.name] = self.file_object[mesh_group + "/data"][
                                    mesh_variable.name]
                        else:
                            mesh_dataframe = DataFrame.from_records(self.file_object[mesh_group + "/data"][:])
                    self.data_2d[reach_number][unit_number]["mesh"]["data"] = mesh_dataframe

                    # HV by celle for each fish
                    if self.extension == ".hab":
                        mesh_hv_data_group = self.file_object[mesh_group + "/hv_data"]
                        for animal_num, animal in enumerate(self.data_2d.hvum.all_final_variable_list.habs().hdf5s().meshs()):
                            # get dataset
                            fish_data_set = mesh_hv_data_group[animal.name]
                            # get data
                            self.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name] = fish_data_set[:]

                    """ node """
                    # group
                    node_group = unit_group + "/node"
                    # xy
                    self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name] = self.file_object[node_group + "/xy"][:]
                    # data (always ?)
                    node_dataframe = DataFrame()
                    if node_group + "/data" in self.file_object:
                        if self.user_target_list != "defaut":
                            for node_variable in self.data_2d.hvum.all_final_variable_list.no_habs().hdf5s().nodes():
                                node_dataframe[node_variable.name] = self.file_object[node_group + "/data"][
                                    node_variable.name]
                        else:
                            node_dataframe = DataFrame.from_records(self.file_object[node_group + "/data"][:])
                    self.data_2d[reach_number][unit_number]["node"]["data"] = node_dataframe

        self.load_data_2d_info()

        if removed_units_list:
            self.data_2d.remove_unit_from_unit_index_list(removed_units_list)

    def load_data_2d_info(self):
        data_2d_group = 'data_2d'
        reach_list = list(self.file_object[data_2d_group].keys())
        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            # group name
            reach_group = data_2d_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            desired_units_list = [available_unit_list[unit_index] for unit_index in self.data_2d.units_index]  # get only desired_units
            for unit_number, unit_group_name in enumerate(desired_units_list):
                # group name
                unit_group = reach_group + "/" + unit_group_name

                if self.extension == ".hyd" or self.extension == ".hab":
                    self.data_2d[reach_number][unit_number].total_wet_area = self.file_object[unit_group].attrs[
                        'total_wet_area']

                if self.extension == ".hab":
                    # group
                    mesh_group = unit_group + "/mesh"
                    mesh_hv_data_group = self.file_object[mesh_group + "/hv_data"]
                    for animal in self.data_2d.hvum.hdf5_and_computable_list.hdf5s().meshs().habs():
                        # dataset
                        fish_data_set = mesh_hv_data_group[animal.name]

                        # get summary data
                        animal.wua[reach_number].append(float(fish_data_set.attrs['wua']))
                        animal.hv[reach_number].append(float(fish_data_set.attrs['hv']))
                        animal.percent_area_unknown[reach_number].append(
                            float(fish_data_set.attrs['percent_area_unknown [%m2]']))

                        # add dataset attributes
                        animal.pref_file = fish_data_set.attrs['pref_file']
                        animal.stage = fish_data_set.attrs['stage']
                        animal.name = fish_data_set.attrs['short_name']
                        animal.aquatic_animal_type = fish_data_set.attrs['aquatic_animal_type_list']

                        # replace_variable
                        self.data_2d.hvum.hdf5_and_computable_list.replace_variable(animal)

    # HYDRAULIC
    def create_hdf5_hyd(self, data_2d, data_2d_whole, project_preferences):
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
        :param data_2d_whole: data 2d whole profile dict with keys :
        'mesh':
            'tin' : list by reach, sub list by units and sub list of numpy array type int
            (three values by mesh : triangle nodes indexes)
        'node'
            'xy' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y coordinates)
            'z' : list by reach, sub list by units and sub list of numpy array type float
            (one value by node : bottom elevation)
        :param data_2d attributes: description attributes with name :
        'filename_source' : str of input filename(s) (sep: ', ')
        'hyd_model_type' : str of hydraulic model type
        'hyd_model_dimension' : str of dimension number
        'hyd_mesh_variables_list' : str of mesh variable list (sep: ', ')
        'hyd_node_variables_list' : str of node variable list (sep: ', ')
        'epsg_code' : str of EPSG number
        'reach_list' : str of reach name(s) (sep: ', ')
        'reach_number' : str of reach total number
        'reach_type' : str of type of reach
        'unit_list' : str of list of units (sep: ', ')
        'unit_number' : str of units total number
        'unit_type' : str of units type (discharge or time) with between brackets, the unit symbol ([m3/s], [s], ..)
        ex : 'discharge [m3/s]', 'time [s]'
        'hyd_varying_mesh' : boolean
        'hyd_unit_z_equal' : boolean if all z are egual between units, 'False' if the bottom values vary
        """
        # save temporary to attribute
        self.data_2d = data_2d
        self.data_2d_whole = data_2d_whole
        self.project_preferences = project_preferences

        # save hyd attributes to hdf5 file
        self.set_hdf5_attributes()

        # create_whole_profile to hdf5 file
        self.write_whole_profile()

        # create_data_2d to hdf5 file
        self.write_data_2d()

        # create_data_2d_info
        self.write_data_2d_info()

        # copy input files to input project folder
        copy_hydrau_input_files(self.data_2d.path_filename_source,
                                self.data_2d.filename_source,
                                self.filename,
                                os.path.join(project_preferences["path_prj"], "input"))

        # save XML
        self.save_xml(self.data_2d.hyd_model_type,
                      self.data_2d.path_filename_source)

        # close file
        self.close_file()

    def load_hdf5_hyd(self, units_index="all", user_target_list="defaut", whole_profil=False):
        # open an hdf5
        self.create_or_open_file(new=False)

        # get_hdf5_attributes
        self.get_hdf5_attributes(close_file=False)

        # save unit_index for computing variables
        self.units_index = units_index
        if self.units_index == "all":
            # load the number of time steps
            self.units_index = list(range(int(self.file_object.attrs['unit_number'])))

        # variables
        self.user_target_list = user_target_list
        if self.user_target_list == "defaut":  # when hdf5 is created (by project preferences)
            self.data_2d.hvum.get_final_variable_list_from_project_preferences(self.project_preferences,
                                                                       hdf5_type=self.hdf5_type)
        elif type(self.user_target_list) == dict:  # project_preferences
            self.project_preferences = self.user_target_list
            self.data_2d.hvum.get_final_variable_list_from_project_preferences(self.project_preferences,
                                                                       hdf5_type=self.hdf5_type)
        else:
            self.data_2d.hvum.get_final_variable_list_from_wish(self.user_target_list)

        # load_whole_profile
        if whole_profil:
            self.load_whole_profile()

        # load_data_2d
        self.load_data_2d()

        # close file
        self.close_file()

        # compute ?
        if self.data_2d.hvum.all_final_variable_list.to_compute():
            self.data_2d.compute_variables(self.data_2d.hvum.all_final_variable_list.to_compute())

    # SUBSTRATE
    def create_hdf5_sub(self, data_2d):
        self.data_2d = data_2d

        # save hyd attributes to hdf5 file
        self.set_hdf5_attributes()

        # POLYGON or POINT
        if self.data_2d.sub_mapping_method in ("polygon", "point"):
            # data_2d
            self.write_data_2d()

        # close file
        self.close_file()

        # copy input files to input project folder
        copy_shapefiles(
            os.path.join(self.data_2d.path_filename_source, self.data_2d.filename_source),
            self.filename,
            os.path.join(self.path_prj, "input"),
            remove=False)

        # save XML
        self.save_xml("SUBSTRATE", self.data_2d.path_filename_source)

    def load_hdf5_sub(self, user_target_list="defaut"):
        # open an hdf5
        self.create_or_open_file(new=False)

        # get_hdf5_attributes
        self.get_hdf5_attributes(close_file=False)

        # units_index
        self.units_index = list(range(int(self.file_object.attrs['unit_number'])))

        # variables
        self.user_target_list = user_target_list
        if self.user_target_list == "defaut":  # when hdf5 is created (by project preferences)
            self.data_2d.hvum.get_final_variable_list_from_project_preferences(self.project_preferences,
                                                                       hdf5_type=self.hdf5_type)
        elif type(self.user_target_list) == dict:  # project_preferences
            self.project_preferences = self.user_target_list
            self.data_2d.hvum.get_final_variable_list_from_project_preferences(self.project_preferences,
                                                                       hdf5_type=self.hdf5_type)
        else:
            self.data_2d.hvum.get_final_variable_list_from_wish(self.user_target_list)

        # load_data_2d
        if self.data_2d.sub_mapping_method != "constant":
            # load_data_2d
            self.load_data_2d()

        # close
        self.close_file()

        # compute ?
        if self.data_2d.hvum.all_final_variable_list.to_compute():
            self.data_2d.compute_variables(self.data_2d.hvum.all_final_variable_list.to_compute())

    # HABITAT
    def create_hdf5_hab(self, data_2d, data_2d_whole, project_preferences):
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
        'node'
            'xy' : list by reach, sub list by units and sub list of numpy array type float
            (two values by node : x and y coordinates)
            'z' : list by reach, sub list by units and sub list of numpy array type float
            (one value by node : bottom elevation)
        """
        # save temporary to attribute
        self.data_2d = data_2d
        self.data_2d_whole = data_2d_whole
        self.project_preferences = project_preferences

        # save hyd attributes to hdf5 file
        self.set_hdf5_attributes()

        # create_whole_profile to hdf5 file
        self.write_whole_profile()

        # create_data_2d to hdf5 file
        self.write_data_2d()

        # create_data_2d_info
        self.write_data_2d_info()

        # copy input files to input project folder (only not merged, .hab directly from a input file as ASCII)
        if not hasattr(self.data_2d, "sub_filename_source"):
            copy_hydrau_input_files(self.data_2d.path_filename_source,
                                    self.data_2d.filename_source,
                                    self.filename,
                                    os.path.join(project_preferences["path_prj"], "input"))

        # save XML
        self.save_xml("HABITAT", "")

        # close file
        self.close_file()

    def load_hdf5_hab(self, units_index="all", user_target_list="defaut", whole_profil=False):
        # open an hdf5
        self.create_or_open_file(new=False)

        # get_hdf5_attributes
        self.get_hdf5_attributes(close_file=False)

        # save unit_index for computing variables
        self.units_index = units_index
        if self.units_index == "all":
            # load the number of time steps
            self.units_index = list(range(int(self.file_object.attrs['unit_number'])))

        # variables
        self.user_target_list = user_target_list
        if self.user_target_list == "defaut":  # when hdf5 is created (by project preferences)
            self.data_2d.hvum.get_final_variable_list_from_project_preferences(self.project_preferences,
                                                                       hdf5_type=self.hdf5_type)
        elif type(self.user_target_list) == dict:  # project_preferences
            self.project_preferences = self.user_target_list
            self.data_2d.hvum.get_final_variable_list_from_project_preferences(self.project_preferences,
                                                                       hdf5_type=self.hdf5_type)
        else:
            self.data_2d.hvum.get_final_variable_list_from_wish(self.user_target_list)

        # load_whole_profile
        if whole_profil:
            self.load_whole_profile()

        # load_data_2d
        self.load_data_2d()

        # close file
        self.close_file()

        # compute ?
        if self.data_2d.hvum.all_final_variable_list.to_compute():
            self.data_2d.compute_variables(self.data_2d.hvum.all_final_variable_list.to_compute())

    def add_fish_hab(self, animal_variable_list):
        """
        This function takes a merge file and add habitat data to it. The habitat data is given by cell. It also save the
        velocity and the water height by cell (and not by node)

        :param hdf5_name: the name of the merge file
        :param path_hdf5: the path to this file
        :param vh_cell: the habitat value by cell
        :param area_all: total wet area by reach
        :param spu_all: total SPU by reach
        :param animal: the name of the fish (with the stage in it)
        """
        # open an hdf5
        self.create_or_open_file(new=False)

        # add variables
        self.data_2d.hvum.hdf5_and_computable_list.extend(animal_variable_list)

        # data_2d
        data_group = self.file_object['data_2d']
        # REACH GROUP
        for reach_number in range(self.data_2d.reach_number):
            reach_group = data_group["reach_" + str(reach_number)]
            # UNIT GROUP
            for unit_number in range(self.data_2d.unit_number):
                unit_group = reach_group["unit_" + str(unit_number)]
                # MESH GROUP
                mesh_group = unit_group["mesh"]
                mesh_hv_data_group = mesh_group["hv_data"]

                # HV by celle for each fish
                for animal_num, animal in enumerate(self.data_2d.hvum.hdf5_and_computable_list.meshs().to_compute().habs()):
                    # create
                    if animal.name in mesh_hv_data_group:
                        del mesh_hv_data_group[animal.name]
                    fish_data_set = mesh_hv_data_group.create_dataset(name=animal.name,
                                                                      shape=
                                                                      self.data_2d[reach_number][unit_number]["mesh"]["data"][
                                                                          animal.name].shape,
                                                                      data=
                                                                      self.data_2d[reach_number][unit_number]["mesh"]["data"][
                                                                          animal.name].to_numpy(),
                                                                      dtype=self.data_2d[reach_number][unit_number]["mesh"]["data"][
                                                                          animal.name].dtype)
                    # add dataset attributes
                    fish_data_set.attrs['pref_file'] = animal.pref_file
                    fish_data_set.attrs['stage'] = animal.stage
                    fish_data_set.attrs['short_name'] = animal.name
                    fish_data_set.attrs['aquatic_animal_type_list'] = animal.aquatic_animal_type
                    fish_data_set.attrs['wua'] = str(animal.wua[reach_number][unit_number])
                    fish_data_set.attrs['hv'] = str(animal.hv[reach_number][unit_number])
                    fish_data_set.attrs['percent_area_unknown [%m2]'] = str(
                        animal.percent_area_unknown[reach_number][unit_number])

        # set to attributes
        self.file_object.attrs["hab_animal_list"] = ", ".join(self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().names())
        self.file_object.attrs["hab_animal_number"] = str(len(self.data_2d.hvum.hdf5_and_computable_list.meshs().habs()))
        self.file_object.attrs["hab_animal_pref_list"] = ", ".join(
            self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().pref_files())
        self.file_object.attrs["hab_animal_stage_list"] = ", ".join(
            self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().stages())
        self.file_object.attrs["hab_animal_type_list"] = ", ".join(
            self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().aquatic_animal_types())

        # close file
        self.close_file()

    def remove_fish_hab(self, fish_names_to_remove):
        """
        Method to remove all data of specific aquatic animal.
        Data to remove : attributes general and datasets.
        """
        # open file if not done
        if self.file_object is None:
            self.create_or_open_file(new=False)

        # get actual attributes (hab_fish_list, hab_animal_number, hab_fish_pref_list, hab_fish_shortname_list, hab_animal_stage_list)
        hab_animal_list_before = self.file_object.attrs["hab_animal_list"].split(", ")
        hab_animal_pref_list_before = self.file_object.attrs["hab_animal_pref_list"].split(", ")
        hab_animal_stage_list_before = self.file_object.attrs["hab_animal_stage_list"].split(", ")
        hab_animal_type_list = self.file_object.attrs["hab_animal_type_list"].split(", ")

        # get index
        fish_index_to_remove_list = []
        for fish_name_to_remove in fish_names_to_remove:
            if fish_name_to_remove in hab_animal_list_before:
                fish_index_to_remove_list.append(hab_animal_list_before.index(fish_name_to_remove))
        fish_index_to_remove_list.sort()

        # change lists
        for index in reversed(fish_index_to_remove_list):
            hab_animal_list_before.pop(index)
            hab_animal_pref_list_before.pop(index)
            hab_animal_stage_list_before.pop(index)
            hab_animal_type_list.pop(index)

        # change attributes
        self.file_object.attrs["hab_animal_number"] = str(len(hab_animal_list_before))
        self.file_object.attrs["hab_animal_list"] = ", ".join(hab_animal_list_before)
        self.file_object.attrs["hab_animal_pref_list"] = ", ".join(hab_animal_pref_list_before)
        self.file_object.attrs["hab_animal_stage_list"] = ", ".join(hab_animal_stage_list_before)
        self.file_object.attrs["hab_animal_type_list"] = ", ".join(hab_animal_type_list)

        # remove data
        # load the number of reach
        try:
            nb_r = int(self.file_object.attrs["reach_number"])
        except KeyError:
            print(
                'Error: the number of time step is missing from :' + self.filename)
            return

        # load the number of time steps
        try:
            nb_t = int(self.file_object.attrs["unit_number"])
        except KeyError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'The number of time step is missing from : ') + self.filename)
            return

        # data_2d
        data_group = self.file_object['data_2d']
        # REACH GROUP
        for reach_number in range(nb_r):
            reach_group = data_group["reach_" + str(reach_number)]
            # UNIT GROUP
            for unit_number in range(nb_t):
                unit_group = reach_group["unit_" + str(unit_number)]
                mesh_group = unit_group["mesh"]
                mesh_hv_data_group = mesh_group["hv_data"]
                for fish_name_to_remove in fish_names_to_remove:
                    del mesh_hv_data_group[fish_name_to_remove]

    # HYDROSIGNATURE
    def hydrosignature_new_file(self, progress_value, classhv, export_txt=False):
        newfilename = self.filename[:-4] + "_HS" + self.extension
        shutil.copy(self.absolute_path_file, os.path.join(self.path, newfilename))
        newhdf5 = Hdf5Management(self.path_prj, newfilename)
        newhdf5.create_or_open_file(False)
        newhdf5.add_hs(progress_value,
                       classhv,
                       export_mesh=True,
                       export_txt=export_txt)
        return newhdf5

    def add_hs(self, progress_value, classhv, export_mesh=False, export_txt=False):
        self.get_hdf5_attributes(close_file=False)
        self.units_index = list(range(self.data_2d.unit_number))
        self.user_target_list = "defaut"
        self.load_data_2d()

        mathing = check_hs_class_match_hydraulic_values(classhv,
                                              h_min=self.data_2d.hvum.h.min,
                                              h_max=self.data_2d.hvum.h.max,
                                              v_min=self.data_2d.hvum.v.min,
                                              v_max=self.data_2d.hvum.v.max)
        if mathing:
            # progress
            delta_reach = 90 / self.data_2d.reach_number

            # for each reach
            for reach_number in range(self.data_2d.reach_number):

                # progress
                delta_unit = delta_reach / self.data_2d.unit_number

                # for each unit
                for unit_number in range(self.data_2d.unit_number):
                    hyd_data_mesh = self.data_2d[reach_number][unit_number]["mesh"]["data"].to_records(index=False)
                    hyd_tin = self.data_2d[reach_number][unit_number]["mesh"]["tin"]
                    i_whole_profile = self.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"]
                    hyd_data_node = self.data_2d[reach_number][unit_number]["node"]["data"].to_records(index=False)
                    hyd_xy_node = self.data_2d[reach_number][unit_number]["node"]["xy"]
                    hyd_hv_node = np.array([hyd_data_node["h"], hyd_data_node["v"]]).T

                    # progress
                    delta_mesh = delta_unit / len(hyd_tin)

                    if export_mesh:
                        nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume, node_xy_out, node_data_out, mesh_data_out, tin_out, i_whole_profile_out = hydrosignature_calculation_alt(
                            delta_mesh, progress_value, classhv, hyd_tin, hyd_xy_node, hyd_hv_node, hyd_data_node, hyd_data_mesh, i_whole_profile,
                            return_cut_mesh=True)
                    else:
                        nb_mesh, total_area, total_volume, mean_depth, mean_velocity, mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume = hydrosignature_calculation_alt(
                            delta_mesh, progress_value, classhv, hyd_tin, hyd_xy_node, hyd_hv_node, hyd_data_node, hyd_data_mesh, i_whole_profile,
                            return_cut_mesh=False)

                    # hsexporttxt
                    if export_txt:
                        hsexporttxt(os.path.join(self.path_prj, "output", "text"),
                                os.path.splitext(self.filename)[0] + "_HSresult.txt",
                                classhv, self.data_2d[reach_number][unit_number].unit_name,
                                nb_mesh, total_area, total_volume, mean_depth, mean_velocity,
                                mean_froude, min_depth, max_depth, min_velocity, max_velocity, hsarea, hsvolume)

                    # attr
                    hs_dict = {"nb_mesh": nb_mesh,
                               "total_area": total_area,
                               "total_volume": total_volume,
                               "mean_depth": mean_depth,
                               "mean_velocity": mean_velocity,
                               "mean_froude": mean_froude,
                               "min_depth": min_depth,
                               "max_depth": max_depth,
                               "min_velocity": min_velocity,
                               "max_velocity": max_velocity,
                               "classhv": classhv}
                    unitpath = "data_2d/reach_" + str(reach_number) + "/unit_" + str(unit_number)
                    for key in hs_dict.keys():
                        self.data_2d[reach_number][unit_number].hydrosignature[key] = hs_dict[key]
                    self.data_2d[reach_number][unit_number].hydrosignature["hsarea"] = hsarea
                    self.data_2d[reach_number][unit_number].hydrosignature["hsvolume"] = hsvolume

                    if export_mesh:
                        self.replace_dataset_in_file(unitpath + "/mesh/data", mesh_data_out)
                        self.replace_dataset_in_file(unitpath + "/mesh/tin", tin_out)
                        self.replace_dataset_in_file(unitpath + "/mesh/i_whole_profile", i_whole_profile_out)
                        self.replace_dataset_in_file(unitpath + "/node/data", node_data_out)
                        self.replace_dataset_in_file(unitpath + "/node/xy", node_xy_out)

            self.write_hydrosignature()

    def write_hydrosignature(self):
        # for each reach
        for reach_number in range(self.data_2d.reach_number):
            # for each unit
            for unit_number in range(self.data_2d.unit_number):
                # attr
                hs_dict = {"nb_mesh": self.data_2d[reach_number][unit_number].hydrosignature["nb_mesh"],
                           "total_area": self.data_2d[reach_number][unit_number].hydrosignature["total_area"],
                           "total_volume": self.data_2d[reach_number][unit_number].hydrosignature["total_volume"],
                           "mean_depth": self.data_2d[reach_number][unit_number].hydrosignature["mean_depth"],
                           "mean_velocity": self.data_2d[reach_number][unit_number].hydrosignature["mean_velocity"],
                           "mean_froude": self.data_2d[reach_number][unit_number].hydrosignature["mean_froude"],
                           "min_depth": self.data_2d[reach_number][unit_number].hydrosignature["min_depth"],
                           "max_depth": self.data_2d[reach_number][unit_number].hydrosignature["max_depth"],
                           "min_velocity": self.data_2d[reach_number][unit_number].hydrosignature["min_velocity"],
                           "max_velocity": self.data_2d[reach_number][unit_number].hydrosignature["max_velocity"],
                           "classhv": self.data_2d[reach_number][unit_number].hydrosignature["classhv"]}

                unitpath = "data_2d/reach_" + str(reach_number) + "/unit_" + str(unit_number)
                for key in hs_dict.keys():
                    self.file_object[unitpath].attrs.create(key, hs_dict[key])
                # hsarea
                hsarea = self.data_2d[reach_number][unit_number].hydrosignature["hsarea"]
                if "hsarea" in self.file_object[unitpath]:
                    del self.file_object[unitpath]["hsarea"]
                self.file_object[unitpath].create_dataset("hsarea",
                                                          shape=hsarea.shape,
                                                          dtype=hsarea.dtype,
                                                          data=hsarea)
                # hsvolume
                hsvolume = self.data_2d[reach_number][unit_number].hydrosignature["hsvolume"]
                if "hsvolume" in self.file_object[unitpath]:
                    del self.file_object[unitpath]["hsvolume"]
                self.file_object[unitpath].create_dataset("hsvolume",
                                                          shape=hsvolume.shape,
                                                          dtype=hsvolume.dtype,
                                                          data=hsvolume)

        self.file_object.attrs.create("hs_calculated", True)
        self.file_object.attrs.create("hs_input_class", self.data_2d[0][0].hydrosignature["classhv"])

    def load_hydrosignature(self):
        self.get_hdf5_attributes(close_file=False)
        for reach_index in range(self.data_2d.reach_number):
            for unit_index in range(self.data_2d.unit_number):
                unitpath = "data_2d/reach_" + str(reach_index) + "/unit_" + str(unit_index)
                keylist = ["nb_mesh",
                           "total_area",
                           "total_volume",
                           "mean_depth",
                           "mean_velocity",
                           "mean_froude",
                           "min_depth",
                           "max_depth",
                           "min_velocity",
                           "max_velocity",
                           "classhv"]
                self.data_2d[reach_index][unit_index].hydrosignature = {}
                for key in keylist:
                    self.data_2d[reach_index][unit_index].hydrosignature[key] = self.file_object[unitpath].attrs[key]
                self.data_2d[reach_index][unit_index].hydrosignature["hsarea"] = self.file_object[unitpath + "/hsarea"][:]
                self.data_2d[reach_index][unit_index].hydrosignature["hsvolume"] = self.file_object[unitpath + "/hsvolume"][:]

    def replace_dataset_in_file(self, dataset_name, new_dataset):
        attrs = self.file_object[dataset_name].attrs.items()
        del self.file_object[dataset_name]
        self.file_object.create_dataset(dataset_name, new_dataset.shape, new_dataset.dtype, data=new_dataset)
        for attribute in attrs:
            self.file_object[dataset_name].attrs.create(attribute[0], attribute[1])

    # ESTIMHAB²
    def create_hdf5_estimhab(self, estimhab_dict, project_preferences):
        # create a new hdf5
        self.create_or_open_file(new=True)

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
        self.close_file()

        # load
        self.load_hdf5_estimhab()

    def load_hdf5_estimhab(self):
        # open an hdf5
        self.create_or_open_file(new=False)

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
        self.close_file()

        # save attrivbute
        self.estimhab_dict = estimhab_dict

    # EXPORT GPKG
    def export_gpkg(self, state=None):
        # INDEX IF HYD OR HAB
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

        # Mapping between OGR and Python data types
        OGRTypes_dict = {np.int64: ogr.OFTInteger64,
                         np.float64: ogr.OFTReal}

        # CRS
        crs = osr.SpatialReference()
        if self.hdf5_type == "hydraulic":
            if self.data_2d.epsg_code != "unknown":
                try:
                    crs.ImportFromEPSG(int(self.data_2d.epsg_code))
                except:
                    print("Warning: " + qt_tr.translate("hdf5_mod", "Can't write .prj from EPSG code : "),
                          self.data_2d.epsg_code)
        if self.hdf5_type == "habitat":
            if self.data_2d.epsg_code != "unknown":
                try:
                    crs.ImportFromEPSG(int(self.data_2d.epsg_code))
                except:
                    print("Warning: " + qt_tr.translate("hdf5_mod", "Can't write .prj from EPSG code : "),
                          self.data_2d.epsg_code)

        # for each reach : one gpkg
        for reach_number in range(0, self.data_2d.reach_number):
            # name
            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + ".gpkg"
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
                        filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + "_allunits_" + time.strftime(
                            "%d_%m_%Y_at_%H_%M_%S") + '.gpkg'

                    # gpkg file creation
                    ds = driver.CreateDataSource(os.path.join(self.path_shp, filename))
                    layer_names = []

                # if .hab
                if self.hdf5_type == "habitat":
                    # no fish
                    if not self.data_2d.hvum.all_final_variable_list.habs():
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
                            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + "_allunits_" + time.strftime(
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
                            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + "_allunits_" + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S") + '.gpkg'
                            # gpkg file creation
                            ds = driver.CreateDataSource(os.path.join(self.path_shp, filename))
                            layer_names = []

            # DATA 2D WHOLE PROFILE mesh
            if mesh_whole_profile_tf:  # only on .hyd creation
                # for all units
                for unit_number in range(0, self.data_2d_whole.unit_number):
                    # layer_name
                    if not self.data_2d.hyd_varying_mesh:
                        layer_name = "mesh_wholeprofile_allunits"
                    else:
                        layer_name = "mesh_wholeprofile_" + self.data_2d_whole.unit_list[reach_number][
                            unit_number]

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
                    for mesh_num in range(0, len(self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name])):
                        node1 = self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][
                            0]  # node num
                        node2 = self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][1]
                        node3 = self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][2]
                        # data geom (get the triangle coordinates)
                        p1 = list(self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][node1].tolist() + [
                            self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name][node1]])
                        p2 = list(self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][node2].tolist() + [
                            self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name][node2]])
                        p3 = list(self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][node3].tolist() + [
                            self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name][node3]])
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

                    # stop loop in this case (if one unit in whole profile)
                    if not self.data_2d.hyd_varying_mesh:
                        break

            # DATA 2D mesh
            if mesh_units_tf:
                # for each unit
                for unit_number in range(0, self.data_2d.unit_number):
                    # name
                    layer_name = "mesh_" + self.units_name_output[reach_number][unit_number]
                    layer_exist = False

                    # if layer exist
                    if layer_name in layer_names:
                        layer_exist = True
                        if self.data_2d.hvum.all_final_variable_list.habs():
                            layer = ds.GetLayer(layer_name)
                            layer_defn = layer.GetLayerDefn()
                            field_names = [layer_defn.GetFieldDefn(i).GetName() for i in
                                           range(layer_defn.GetFieldCount())]
                            # erase all fish field
                            for fish_num, animal in enumerate(self.data_2d.hvum.hdf5_and_computable_list.habs()):
                                if animal.name in field_names:
                                    field_index = field_names.index(animal.name)
                                    layer.DeleteField(field_index)  # delete all features attribute of specified field
                                    field_names = [layer_defn.GetFieldDefn(i).GetName() for i in
                                                   range(layer_defn.GetFieldCount())]  # refresh list
                            # create all fish field
                            for fish_num, animal in enumerate(self.data_2d.hvum.hdf5_and_computable_list.habs()):
                                new_field = ogr.FieldDefn(animal.name, ogr.OFTReal)
                                layer.CreateField(new_field)
                            # add fish data for each mesh
                            layer.StartTransaction()  # faster
                            for mesh_num in range(0,
                                                  len(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name])):
                                feature = layer.GetFeature(mesh_num + 1)  # 1 because gpkg start at 1
                                for fish_num, animal in enumerate(self.data_2d.hvum.hdf5_and_computable_list.habs()):
                                    data = self.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name][mesh_num]
                                    feature.SetField(animal.name, data)
                                layer.SetFeature(feature)
                            layer.CommitTransaction()  # faster

                    # if layer not exist
                    if not layer_exist or not self.data_2d.hvum.all_final_variable_list.habs():  # not exist or merge case
                        # create layer
                        if not crs.ExportToWkt():  # '' == crs unknown
                            layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPolygon)
                        else:  # crs known
                            layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPolygon)

                        # create fields (no width no precision to be specified with GPKG)
                        for mesh_variable in self.data_2d.hvum.all_final_variable_list.no_habs().meshs():
                            layer.CreateField(ogr.FieldDefn(mesh_variable.name_gui, OGRTypes_dict[mesh_variable.dtype]))

                        defn = layer.GetLayerDefn()
                        if self.hdf5_type == "habitat":
                            # fish
                            if self.data_2d.hvum.all_final_variable_list.habs():
                                for fish_num, animal in enumerate(self.data_2d.hvum.all_final_variable_list.habs()):
                                    layer.CreateField(ogr.FieldDefn(animal.name_gui, OGRTypes_dict[animal.dtype]))
                        layer.StartTransaction()  # faster

                        # for each mesh
                        for mesh_num in range(0, len(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name])):
                            node1 = self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][
                                0]  # node num
                            node2 = self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][1]
                            node3 = self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][2]
                            # data geom (get the triangle coordinates)
                            p1 = list(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][node1].tolist() + [
                                self.data_2d[reach_number][unit_number]["node"]["data"][self.data_2d.hvum.z.name][node1]])
                            p2 = list(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][node2].tolist() + [
                                self.data_2d[reach_number][unit_number]["node"]["data"][self.data_2d.hvum.z.name][node2]])
                            p3 = list(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][node3].tolist() + [
                                self.data_2d[reach_number][unit_number]["node"]["data"][self.data_2d.hvum.z.name][node3]])

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

                            # variables
                            for mesh_variable in self.data_2d.hvum.all_final_variable_list.no_habs().meshs():
                                # convert NumPy values to a native Python type
                                data_field = self.data_2d[reach_number][unit_number][mesh_variable.position]["data"][
                                                     mesh_variable.name][mesh_num].item()
                                feat.SetField(mesh_variable.name_gui, data_field)

                            if self.hdf5_type == "habitat":
                                # fish
                                if self.data_2d.hvum.all_final_variable_list.habs():
                                    for fish_num, animal in enumerate(self.data_2d.hvum.all_final_variable_list.habs()):
                                        feat.SetField(animal.name,
                                                      self.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name][mesh_num])
                            # set geometry
                            feat.SetGeometry(poly)
                            # create
                            layer.CreateFeature(feat)

                        # close layer
                        layer.CommitTransaction()  # faster

            # DATA 2D WHOLE PROFILE point
            if point_whole_profile_tf:  # only on .hyd creation
                # for all units (selected or all)
                for unit_number in range(0, self.data_2d_whole.unit_number):
                    # layer_name
                    if not self.data_2d.hyd_varying_mesh:
                        layer_name = "point_wholeprofile_allunits"
                    else:
                        layer_name = "point_wholeprofile_" + \
                                     self.data_2d_whole.unit_list[reach_number][unit_number]

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
                    for point_num in range(0, len(self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name])):
                        # data geom (get the triangle coordinates)
                        x = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][point_num][0]
                        y = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][point_num][1]
                        z = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name][point_num]
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
                    if not self.data_2d.hyd_varying_mesh:
                        break

            # DATA 2D point
            if point_units_tf:
                # for each unit
                for unit_number in range(0, self.data_2d.unit_number):
                    # name
                    layer_name = "point_" + self.units_name_output[reach_number][unit_number]
                    layer_exist = False

                    # if layer exist
                    if layer_name in layer_names:
                        layer_exist = True

                    # if layer not exist
                    if not layer_exist or not self.data_2d.hvum.all_final_variable_list.habs():  # not exist or merge case
                        # create layer
                        if not crs.ExportToWkt():  # '' == crs unknown
                            layer = ds.CreateLayer(name=layer_name, geom_type=ogr.wkbPoint)
                        else:  # crs known
                            layer = ds.CreateLayer(name=layer_name, srs=crs, geom_type=ogr.wkbPoint)

                        # create fields (no width no precision to be specified with GPKG)
                        for node_variable in self.data_2d.hvum.all_final_variable_list.no_habs().nodes():
                            layer.CreateField(ogr.FieldDefn(node_variable.name_gui, OGRTypes_dict[node_variable.dtype]))

                        defn = layer.GetLayerDefn()
                        layer.StartTransaction()  # faster

                        # for each point
                        for point_num in range(0, len(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name])):
                            # data geom (get the triangle coordinates)
                            x = self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][point_num][0]
                            y = self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][point_num][1]
                            z = self.data_2d[reach_number][unit_number]["node"]["data"][self.data_2d.hvum.z.name][point_num]

                            # Create a point
                            point = ogr.Geometry(ogr.wkbPoint)
                            point.AddPoint(x, y, z)
                            # Create a new feature
                            feat = ogr.Feature(defn)

                            for node_variable in self.data_2d.hvum.all_final_variable_list.no_habs().nodes():
                                feat.SetField(node_variable.name_gui,
                                              self.data_2d[reach_number][unit_number][node_variable.position]["data"][
                                                  node_variable.name][point_num])

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
        index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['elevation_whole_profile'][index]:
            """ create stl whole profile (to see topography) """
            # for all reach
            for reach_number in range(self.data_2d_whole.reach_number):
                # for all units
                for unit_number in range(self.data_2d_whole.unit_number):
                    # get data
                    xy = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name]
                    z = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name] * self.project_preferences[
                        "vertical_exaggeration"]
                    tin = self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name]
                    xyz = np.column_stack([xy, z])
                    # Create the mesh
                    stl_file = mesh.Mesh(np.zeros(tin.shape[0], dtype=mesh.Mesh.dtype))
                    for i, f in enumerate(tin):
                        for j in range(3):
                            stl_file.vectors[i][j] = xyz[f[j], :]
                    # filename
                    name_file = self.basename + "_" + self.data_2d.reach_list[reach_number] + "_" + \
                                self.data_2d_whole.unit_list[reach_number][
                                    unit_number] + "_wholeprofile_mesh.stl"

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
        index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['variables_units'][index]:
            file_names_all = []
            part_timestep_indice = []
            pvd_variable_z = self.data_2d.hvum.all_sys_variable_list.get_from_name_gui(self.project_preferences["pvd_variable_z"])

            # for all reach
            for reach_number in range(self.data_2d.reach_number):
                # for all units
                for unit_number in range(self.data_2d.unit_number):
                    part_timestep_indice.append((reach_number, unit_number))
                    # create one vtu file by time step
                    x = np.ascontiguousarray(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][:, 0])
                    y = np.ascontiguousarray(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][:, 1])
                    z = np.ascontiguousarray(
                        self.data_2d[reach_number][unit_number]["node"]["data"][pvd_variable_z.name].to_numpy() *
                        self.project_preferences["vertical_exaggeration"])
                    connectivity = np.reshape(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name],
                                              (len(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name]) * 3,))
                    offsets = np.arange(3, len(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name]) * 3 + 3,
                                        3)
                    offsets = np.array(list(map(int, offsets)), dtype=np.int64)
                    cell_types = np.zeros(
                        len(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name]), ) + 5  # triangle
                    cell_types = np.array(list((map(int, cell_types))), dtype=np.int64)

                    cellData = {}

                    # hyd variables mesh
                    for mesh_variable in self.data_2d.hvum.all_final_variable_list.meshs():
                        cellData[mesh_variable.name_gui] = \
                            self.data_2d[reach_number][unit_number][mesh_variable.position]["data"][
                                mesh_variable.name].to_numpy()

                    # create the grid and the vtu files
                    name_file = os.path.join(self.path_visualisation,
                                             self.basename_output_reach_unit[reach_number][unit_number] + "_" +
                                             self.project_preferences['pvd_variable_z'])
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
                                                     self.basename_output_reach_unit[reach_number][unit_number] + "_" +
                                                     self.project_preferences['pvd_variable_z']) + "_" + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S")
                    file_names_all.append(name_file + ".vtu")
                    hl_mod.unstructuredGridToVTK(name_file, x, y, z, connectivity, offsets, cell_types,
                                                 cellData)

            # create the "grouping" file to read all time step together
            name_here = self.basename + "_" + self.data_2d.reach_list[reach_number] + "_" + self.project_preferences[
                'pvd_variable_z'] + ".pvd"
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
                    name_here = self.basename + "_" + self.reach_name[reach_number] + "_" + self.project_preferences[
                        'pvd_variable_z'] + "_" + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + '.pvd'
            paraview_mod.writePVD(os.path.join(self.path_visualisation, name_here), file_names_all,
                                  part_timestep_indice)

            if state:
                state.value = 1  # process finished

    # EXPORT TXT
    def export_spu_txt(self, state=None):
        if not os.path.exists(self.path_txt):
            print('Error: ' + qt_tr.translate("hdf5_mod",
                                              'The path to the text file is not found. Text files not created \n'))
        else:
            animal_list = self.data_2d.hvum.hdf5_and_computable_list.habs()
            if animal_list:
                sim_name = self.data_2d.unit_list
                unit_type = self.data_2d.unit_type[self.data_2d.unit_type.find('[') + 1:self.data_2d.unit_type.find(']')]

                if self.project_preferences['language'] == 0:
                    name = self.basename + '_wua.txt'
                else:
                    name = self.basename + '_spu.txt'
                if os.path.isfile(os.path.join(self.path_txt, name)):
                    if not self.project_preferences['erase_id']:
                        if self.project_preferences['language'] == 0:
                            name = self.basename + '_wua_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                        else:
                            name = self.basename + '_spu_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    else:
                        try:
                            os.remove(os.path.join(self.path_txt, name))
                        except PermissionError:
                            print('Error: ' + qt_tr.translate("hdf5_mod",
                                                              'Could not modify text file as it is open in another program. \n'))
                            return

                name = os.path.join(self.path_txt, name)

                # open text to write
                with open(name, 'wt', encoding='utf-8') as f:

                    # header 1
                    if self.project_preferences['language'] == 0:
                        header = 'reach\tunit\treach_area'
                    else:
                        header = 'troncon\tunit\taire_troncon'
                    if self.project_preferences['language'] == 0:
                        header += "".join(['\tHV' for _ in range(len(animal_list))])
                        header += "".join(['\tWUA' for _ in range(len(animal_list))])
                        header += "".join(['\t%unknown' for _ in range(len(animal_list))])
                    else:
                        header += "".join(['\tVH' for _ in range(len(animal_list))])
                        header += "".join(['\tSPU' for _ in range(len(animal_list))])
                        header += "".join(['\t%inconnu' for _ in range(len(animal_list))])
                    header += '\n'
                    f.write(header)
                    # header 2
                    header = '[]\t[' + unit_type + ']\t[m2]'
                    header += "".join(['\t[]' for _ in range(len(animal_list))])
                    header += "".join(['\t[m2]' for _ in range(len(animal_list))])
                    header += "".join(['\t[%m2]' for _ in range(len(animal_list))])
                    header += '\n'
                    f.write(header)
                    # header 3
                    header = 'all\tall\tall '
                    for animal in animal_list * 3:
                        header += '\t' + animal.name.replace(' ', '_')
                    header += '\n'
                    f.write(header)

                    for reach_number in range(self.data_2d.reach_number):
                        for unit_number in range(self.data_2d.unit_number):
                            area_reach = self.data_2d[reach_number][unit_number].total_wet_area
                            if not sim_name:
                                data_here = str(reach_number) + '\t' + str(unit_number) + '\t' + str(area_reach)
                            else:
                                data_here = str(reach_number) + '\t' + str(sim_name[reach_number][unit_number]) + '\t' + str(
                                    area_reach)
                            # HV
                            for animal in animal_list:
                                try:
                                    wua_fish = animal.hv[reach_number][unit_number]
                                    data_here += '\t' + str(float(wua_fish) / float(area_reach))
                                except:
                                    data_here += '\t' + 'NaN'
                            # WUA
                            for animal in animal_list:
                                try:
                                    wua_fish = animal.wua[reach_number][unit_number]
                                    data_here += '\t' + str(wua_fish)
                                except:
                                    data_here += '\t' + 'NaN'
                            # %unknwon
                            for animal in animal_list:
                                wua_fish = animal.percent_area_unknown[reach_number][unit_number]
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
        index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['detailled_text'][index]:
            if not os.path.exists(self.path_txt):
                print('Error: ' + qt_tr.translate("hdf5_mod",
                                                  'The path to the text file is not found. Text files not created \n'))

            # for all reach
            for reach_number in range(self.data_2d.reach_number):
                # for all units
                for unit_number in range(self.data_2d.unit_number):
                    name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate("hdf5_mod",
                                                                                                        "detailled_mesh") + ".txt"
                    if os.path.isfile(os.path.join(self.path_txt, name)):
                        if not self.project_preferences['erase_id']:
                            name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate(
                                "hdf5_mod", "detailled_mesh") + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                        else:
                            try:
                                os.remove(os.path.join(self.path_txt, name))
                            except PermissionError:
                                print('Error: ' + qt_tr.translate("hdf5_mod",
                                                                  'Could not modify text file as it is open in another program. \n'))
                                return
                    name = os.path.join(self.path_txt, name)

                    # open text to write
                    with open(name, 'wt', encoding='utf-8') as f:
                        # header 1
                        text_to_write_str_list = [
                            qt_tr.translate("hdf5_mod", "node1"),
                            qt_tr.translate("hdf5_mod", "node2"),
                            qt_tr.translate("hdf5_mod", "node3")]
                        text_to_write_str_list.extend(self.data_2d.hvum.all_final_variable_list.meshs().names())
                        text_to_write_str = "\t".join(text_to_write_str_list)
                        text_to_write_str += '\n'
                        f.write(text_to_write_str)

                        # header 2
                        text_to_write_str = "[]\t[]\t[]\t["
                        text_to_write_str += ']\t['.join(self.data_2d.hvum.all_final_variable_list.meshs().units())
                        f.write(text_to_write_str)

                        # data
                        text_to_write_str = ""
                        # for each mesh
                        for mesh_num in range(0, len(self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name])):
                            node1 = self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][
                                0]  # node num
                            node2 = self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][1]
                            node3 = self.data_2d[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name][mesh_num][2]
                            text_to_write_str += '\n'
                            text_to_write_str += f"{str(node1)}\t{str(node2)}\t{str(node3)}\t"
                            data_list = []
                            for mesh_variable_name in self.data_2d.hvum.all_final_variable_list.meshs().names():
                                data_list.append(str(
                                    self.data_2d[reach_number][unit_number]["mesh"]["data"][mesh_variable_name][mesh_num]))
                            text_to_write_str += "\t".join(data_list)

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
        index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['detailled_text'][index]:
            if not os.path.exists(self.path_txt):
                print('Error: ' + qt_tr.translate("hdf5_mod",
                                                  'The path to the text file is not found. Text files not created \n'))

            # for all reach
            for reach_number in range(self.data_2d.reach_number):
                # for all units
                for unit_number in range(self.data_2d.unit_number):
                    name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate("hdf5_mod",
                                                                                                        "detailled_point") + ".txt"
                    if os.path.isfile(os.path.join(self.path_txt, name)):
                        if not self.project_preferences['erase_id']:
                            name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate(
                                "hdf5_mod", "detailled_point") + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                        else:
                            try:
                                os.remove(os.path.join(self.path_txt, name))
                            except PermissionError:
                                print('Error: ' + qt_tr.translate("hdf5_mod",
                                                                  'Could not modify text file as it is open in another program. \n'))
                                return
                    name = os.path.join(self.path_txt, name)

                    # open text to write
                    with open(name, 'wt', encoding='utf-8') as f:
                        # header 1
                        text_to_write_str = "x\ty\t"
                        text_to_write_str += "\t".join(self.data_2d.hvum.all_final_variable_list.nodes().names())
                        text_to_write_str += '\n'
                        f.write(text_to_write_str)

                        # header 2 2
                        text_to_write_str = '[m]\t[m]\t['
                        text_to_write_str += "]\t[".join(self.data_2d.hvum.all_final_variable_list.nodes().units())
                        text_to_write_str += "]"
                        f.write(text_to_write_str)

                        # data
                        text_to_write_str = ""
                        # for each point
                        for point_num in range(0, len(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name])):
                            text_to_write_str += '\n'
                            # data geom (get the triangle coordinates)
                            x = str(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][point_num][0])
                            y = str(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][point_num][1])
                            text_to_write_str += f"{x}\t{y}"
                            for node_variable_name in self.data_2d.hvum.all_final_variable_list.nodes().names():
                                text_to_write_str += "\t" + str(
                                    self.data_2d[reach_number][unit_number]["node"]["data"][node_variable_name][point_num])

                        # change decimal point
                        locale = QLocale()
                        if locale.decimalPoint() == ",":
                            text_to_write_str = text_to_write_str.replace('.', ',')

                        # write file
                        f.write(text_to_write_str)

            if state:
                state.value = 1  # process finished

    def export_report(self, state=None):
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
        index = 0
        if self.extension == ".hab":
            index = 1
        if self.project_preferences['fish_information'][index]:
            if self.data_2d.hvum.hdf5_and_computable_list.habs():
                # get data
                xmlfiles = self.data_2d.hvum.hdf5_and_computable_list.habs().pref_files()
                hab_animal_type_list = self.data_2d.hvum.hdf5_and_computable_list.habs().aquatic_animal_types()
                # remove duplicates xml
                prov_list = list(set(list(zip(xmlfiles, hab_animal_type_list))))
                xmlfiles, hab_animal_type_list = ([a for a, b in prov_list], [b for a, b in prov_list])

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
                    fake_value = Value("d", 0)

                    if information_model_dict["ModelType"] != "bivariate suitability index models":
                        # fish
                        if hab_animal_type_list[idx] == "fish":
                            # read pref
                            h_all, vel_all, sub_all, sub_code, code_fish, name_fish, stages = \
                                bio_info_mod.read_pref(xmlfile, hab_animal_type_list[idx])
                            # plot
                            fig, axe_curve = plot_mod.plot_suitability_curve(fake_value,
                                                            h_all,
                                                            vel_all,
                                                            sub_all,
                                                            information_model_dict["CdBiologicalModel"],
                                                            name_fish,
                                                            stages,
                                                            information_model_dict["substrate_type"],
                                                            sub_code,
                                                            self.project_preferences,
                                                            True)
                        # invertebrate
                        else:
                            # open the pref
                            shear_stress_all, hem_all, hv_all, _, code_fish, name_fish, stages = \
                                bio_info_mod.read_pref(xmlfile, hab_animal_type_list[idx])
                            # plot
                            fig, axe_curve = plot_mod.plot_suitability_curve_invertebrate(fake_value,
                                                                         shear_stress_all, hem_all, hv_all,
                                                                         code_fish, name_fish,
                                                                         stages, self.project_preferences, True)
                    else:
                        # open the pref
                        [h_all, vel_all, pref_values_all, _, code_fish, name_fish, stages] = bio_info_mod.read_pref(xmlfile,
                                                                                                                    hab_animal_type_list[
                                                                                                                        idx])
                        state_fake = Value("d", 0)
                        fig, axe_curve = plot_mod.plot_suitability_curve_bivariate(state_fake,
                                                                  h_all,
                                                                  vel_all,
                                                                  pref_values_all,
                                                                  code_fish,
                                                                  name_fish,
                                                                  stages,
                                                                  self.project_preferences,
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
                    text_all = name_fish + '\n\n' + data[0][2] + '\n\n' + information_model_dict[
                        "CdBiologicalModel"] + '\n\n' + code_fish + '\n\n'
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
                    filename = os.path.join(self.path_figure, 'report_' + information_model_dict["CdBiologicalModel"] +
                                            self.project_preferences["format"])

                    # save
                    try:
                        plt.savefig(filename)
                    except PermissionError:
                        print(
                            'Warning: ' + qt_tr.translate("hdf5_mod", 'Close ' + filename + ' to update fish information'))

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
        output_filename = "Estimhab"
        intput_filename = "Estimhab_input"

        # check if exist and erase
        if os.path.exists(os.path.join(self.path_txt, output_filename + '.txt')):
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
            np.savetxt(os.path.join(self.path_txt, output_filename + '.txt'),
                       all_data.T,
                       header=txt_header,
                       fmt='%f',
                       delimiter='\t')  # , newline=os.linesep
        except PermissionError:
            output_filename = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            np.savetxt(os.path.join(self.path_txt, output_filename + '.txt'),
                       all_data.T,
                       header=txt_header,
                       fmt='%f',
                       delimiter='\t')  # , newline=os.linesep
        if len(self.estimhab_dict["targ_q_all"]) != 0:
            f = open(os.path.join(self.path_txt, output_filename + '.txt'), "a+")
            np.savetxt(f,
                       all_data_targ.T,
                       header="target(s) discharge(s)",
                       fmt='%f',
                       delimiter='\t')
            f.close()

        # change decimal point
        locale = QLocale()
        if locale.decimalPoint() == ",":
            txt_file_convert_dot_to_comma(os.path.join(self.path_txt, output_filename + '.txt'))

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
            with open(os.path.join(self.path_txt, intput_filename + '.txt'), 'wt') as f:
                f.write(txtin)
        except PermissionError:
            intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            with open(os.path.join(self.path_txt, intput_filename + '.txt'), 'wt') as f:
                f.write(txtin)
        locale = QLocale()
        if locale.decimalPoint() == ",":
            txt_file_convert_dot_to_comma(os.path.join(self.path_txt, intput_filename + '.txt'))


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
            print('Error ' + qt_tr.translate("hdf5_mod",
                                             'No path to the project given although a relative path was provided'))
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


def get_filename_hs(path):
    filenames = []
    for file in os.listdir(path):
        if file.endswith(".hyd") or file.endswith(".hab"):
            path_prj = os.path.dirname(path)
            try:
                hdf5 = Hdf5Management(path_prj,
                                      file,
                                      new=False)
                hdf5.close_file()
                if hdf5.hs_calculated:
                    filenames.append(file)
            except:
               print("Error: " + file + " file seems to be corrupted. Delete it with HABBY or manually.")

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
        project_preferences = load_project_properties(path_prj)
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
        sub_ini = file.attrs['filename']
    except KeyError:
        sub_ini = ''
    try:
        hydro_ini = file.attrs['filename']
    except KeyError:
        hydro_ini = ''
    file.close()
    return sub_ini, hydro_ini


def get_dataset_names(group):
    # Receives a h5py._hl.files.File or h5py._hl.group.Group object and returns the full names of the dataset objects
    # contained inside
    global dataset_names
    dataset_names = []

    group.visititems(add_if_dataset)
    #visititems applies the add_if_dataset function to each object in the group/file and in each subgroup as well
    return dataset_names


def add_if_dataset(name, object):
    #Function used inside get_dataset_names, called by the visititems routine.
    #Checks if a certain object is an hdf5 dataset and, if so, adds its name to the list dataset_names
    global dataset_names
    if type(object) == h5py._hl.dataset.Dataset:
        dataset_names += [name]


def datasets_are_equal(file1,file2):
    #Evaluates whether the hdf5 file objects file1 and file2 have the same values
    """
    :param file1, file2: h5py._hl.files.File objects whose datasets we want to compare
    :param dataset_names: list containing the full names of every dataset to be evaluated in both files
    :return: True if each dataset listed in dataset_names is identical in file1 and file2,  False otherwise
    """

    dataset_names1=get_dataset_names(file1)
    dataset_names2=get_dataset_names(file2)
    if dataset_names1!=dataset_names2:
        return False
    else:
        equal = True
        for name in dataset_names1:
            if np.any(file1[name][()] != file2[name][()]):
                equal = False
        return equal


def simple_export(data,format):
    # Takes as input the Hdf5management object data and the string format, and exports the data to the output folder
    # of the project
    if data.extension==".hyd":
        data.load_hdf5_hyd(whole_profil=True)
        for name in data.available_export_list:
            data.project_preferences[name]=[True,True]
        data.get_variables_from_dict_and_compute()
        if format in ["gpkg","all"]:
            data.export_gpkg()

        if format in ["stl","all"]:
            data.export_stl()


        if format in ["pvd","stu","all"]:
            data.compute_variables(variables_node=data.hyd_variables_computed_node,
                                   variables_mesh=data.hyd_variables_computed_mesh)
            data.export_paraview()

        if format in ["txt","all"]:
            data.export_detailled_mesh_txt()
            data.export_detailled_point_txt()


    elif data.extension==".hab":
        #TODO: Write specific code for exporting habitat files
        pass

    else:
        raise ValueError
