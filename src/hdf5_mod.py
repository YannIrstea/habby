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
import traceback
import h5py
import numpy as np
from PyQt5.QtCore import QCoreApplication as qt_tr
from PyQt5.QtCore import QLocale
from stl import mesh
from multiprocessing import Value, Pool, Lock, cpu_count
from pandas import DataFrame

from src.hl_mod import unstructuredGridToVTK
from src.paraview_mod import writePVD
from src.export_manager_mod import export_mesh_layer_to_gpkg, merge_gpkg_to_one, export_node_layer_to_gpkg, export_mesh_txt,\
    setup, export_point_txt, export_report
from src.project_properties_mod import load_project_properties, save_project_properties
from src.dev_tools_mod import copy_shapefiles, copy_hydrau_input_files, txt_file_convert_dot_to_comma, strip_accents
from src.data_2d_mod import Data2d
from src.translator_mod import get_translator
from src.hydrosignature_mod import hsexporttxt


from habby import HABBY_VERSION_STR


class Hdf5Management:
    def __init__(self, path_prj, hdf5_filename, new, edit=False):
        self.new = new
        if self.new:
            self.edit = True
        else:
            self.edit = edit
        # hdf5 version attributes
        self.h5py_version = h5py.version.version
        self.hdf5_version = h5py.version.hdf5_version
        # project attributes
        self.path_prj = path_prj  # relative path to project
        self.path_gis = os.path.join(self.path_prj, "output", "GIS")
        self.path_txt = os.path.join(self.path_prj, "output", "text")
        self.path_3d = os.path.join(self.path_prj, "output", "3D")
        self.path_figure = os.path.join(self.path_prj, "output", "figures")
        self.name_prj = None
        for file in os.listdir(path_prj):
            if ".habby" in file:
                self.name_prj = os.path.splitext(file)[0]
                break
        self.absolute_path_prj_xml = os.path.join(self.path_prj, self.name_prj + '.habby')
        # hdf5 attributes fix
        self.extensions = ('.hyd', '.sub', '.hab')  # all available extensions
        self.export_source = "auto"  # or "manual" if export launched from data explorer
        self.project_properties = load_project_properties(self.path_prj)
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
                                      "mesh_detailled_text",
                                      "point_detailled_text",
                                      "habitat_text",
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
        self.units_index = "all"  # unit to load (all)
        self.user_target_list = "defaut"  # variable to load (defaut==all)
        # required_dict_calc_hab
        self.required_dict_calc_hab = dict(
            dimension_ok=False,
            z_presence_ok=False,
            shear_stress_ok=False,
            percentage_ok=False,
            sub_mapping_method="",
            fish_list=[])
        # hdf5 data attrbutes
        self.hs_calculated = False
        self.hs_mesh = False
        # create_or_open_file
        self.create_or_open_file()

    def __str__(self):
        return self.filename

    def __repr__(self):
        return self.filename

    def create_or_open_file(self):
        # get mode
        if not self.new:
            if self.edit:
                mode_file = 'r+'  # Read/write, file must exist
            else:
                mode_file = 'r'  # Readonly, file must exist
        else:
            mode_file = 'w'  # Create file, truncate if exists

        # extension check
        if self.extension not in self.extensions:
            print("Warning: extension : " + self.extension + f" is unknown. The extension file should be : {self.extensions}.")

        # file presence check
        try:
            # write or open hdf5 file
            self.file_object = h5py.File(name=self.absolute_path_file,
                                         mode=mode_file)
        except OSError:
            print('Error: ' + qt_tr.translate("hdf5_mod", 'the hdf5 file could not be loaded.') + " " + self.absolute_path_file)
            self.file_object = None
            return

        if self.new:  # write + write attributes
            self.file_object.attrs['hdf5_version'] = self.hdf5_version
            self.file_object.attrs['h5py_version'] = self.h5py_version
            self.file_object.attrs['software'] = 'HABBY'
            self.file_object.attrs['software_version'] = HABBY_VERSION_STR
            self.file_object.attrs['path_project'] = self.path_prj
            self.file_object.attrs['name_project'] = self.name_prj
            self.file_object.attrs['filename'] = self.filename
        elif not self.new:
            if self.hdf5_type != "ESTIMHAB":
                self.project_properties = load_project_properties(self.path_prj)
                """ get xml parent element name """
                if self.hdf5_type == "hydraulic":
                    self.input_type = self.file_object.attrs['hyd_model_type']
                elif self.hdf5_type == "substrate":
                    self.input_type = "SUBSTRATE"
                else:
                    self.input_type = "HABITAT"

                # hs
                if self.hdf5_type == "hydraulic" or self.hdf5_type == "habitat":
                    try:
                        self.hs_calculated = self.file_object.attrs["hs_calculated"]
                        self.hs_mesh = self.file_object.attrs["hs_mesh"]
                    except KeyError:
                        self.hs_calculated = False
                        self.hs_mesh = False
                    if self.hs_calculated:
                        try:
                            self.hs_input_class = [self.file_object.attrs["hs_input_class_h"],
                                                   self.file_object.attrs["hs_input_class_v"]]
                        except KeyError:
                            print("Error:", self.filename, "is corrupted. Can't locate attribute: 'hs_input_class'.")

    def close_file(self):
        if self.file_object is not None:
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
            project_properties = load_project_properties(self.path_prj)

            # change values
            if self.filename in project_properties[model_type]["hdf5"]:
                project_properties[model_type]["hdf5"].remove(self.filename)
            project_properties[model_type]["hdf5"].append(self.filename)
            project_properties[model_type]["path"] = input_file_path

            # save_project_properties
            save_project_properties(self.path_prj, project_properties)

    # HDF5 INFORMATIONS
    def set_hdf5_attributes(self):
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
                    # unit_list with different unit by reach
                    self.file_object.attrs[attribute_name] = str(attribute_value)
            elif attribute_name == "unit_index":
                pass
            elif attribute_name in {"hyd_unit_correspondence", "mm_mesh_manager_data"}:
                self.file_object.attrs[attribute_name] = str(attribute_value)
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
        if self.hdf5_type == "habitat":
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
                    if attribute_name == "hyd_min_height":
                        attribute_value = str(attribute_value)
                    else:
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
        if self.hdf5_type != "ESTIMHAB":
            """ get_hdf5_reach_name """
            reach_list = self.file_object.attrs["reach_list"].tolist()
            reach_number = self.file_object.attrs["reach_number"]

            """ get_hdf5_units_name """
            try:
                unit_list = eval(self.file_object.attrs["unit_list"])
            except ValueError:
                unit_list = self.file_object.attrs["unit_list"].tolist()  # old project in numpy array

            unit_type = self.file_object.attrs["unit_type"]

            """ light_data_2d """
            self.data_2d = Data2d(reach_number=reach_number,
                                  unit_list=unit_list)  # with no array data
            self.data_2d.set_unit_list(unit_list)
            self.data_2d.set_reach_list(reach_list)
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
                if "unit_list" == attribute_name:
                    continue
                elif "unit_correspondence" in attribute_name:
                    attribute_value = hdf5_attributes_dict[attribute_name]
                    try:
                        unit_correspondence = eval(attribute_value)
                    except ValueError:
                        unit_correspondence = attribute_value.tolist()  # old project in numpy array
                    setattr(self.data_2d, attribute_name, unit_correspondence)
                elif attribute_name[:4] not in {"mesh", "node"}:
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
                for unit_number in range(self.data_2d[reach_number].unit_number):
                    reach_name = strip_accents(self.data_2d[reach_number][unit_number].reach_name)
                    unit_name = self.data_2d[reach_number][unit_number].unit_name
                    self.basename_output_reach_unit[reach_number].append(self.basename + "_" + reach_name + "_" + unit_name.replace(".", "_"))
                    if unit_type != 'unknown':
                        # ["/", ".", "," and " "] are forbidden for gpkg in ArcMap
                        unit_name2 = unit_name.replace(".", "_")  # + "_" + unit_type.split("[")[1][:-1].replace("/", "")
                    else:
                        unit_name2 = unit_name.replace(".", "_")  # + "_" + unit_type
                    self.units_name_output[reach_number].append(unit_name2)

        if close_file:
            self.close_file()

    def check_if_file_is_valid_for_calc_hab(self):
        # init
        self.required_dict_calc_hab = dict(
            dimension_ok=False,
            z_presence_ok=False,
            shear_stress_ok=False,
            percentage_ok=False,
            sub_mapping_method="",
            fish_list=[])
        if self.data_2d.hyd_model_dimension == "2":
            self.required_dict_calc_hab["dimension_ok"] = True
        # if "z" in hdf5.hdf5_attributes_info_text[hdf5.hdf5_attributes_name_text.index("hyd variables list")]:
        self.required_dict_calc_hab["z_presence_ok"] = True  # TODO : always True ??
        if "percentage" in self.data_2d.sub_classification_method:
            self.required_dict_calc_hab["percentage_ok"] = True
        self.required_dict_calc_hab["fish_list"] = self.data_2d.hvum.hdf5_and_computable_list.meshs().habs().names()
        if self.data_2d.hvum.shear_stress.name in self.data_2d.hvum.hdf5_and_computable_list.names():
            self.required_dict_calc_hab["shear_stress_ok"] = True
        self.required_dict_calc_hab["sub_mapping_method"] = self.data_2d.sub_mapping_method

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
                    group_name = 'unit_' + str(unit_list[unit_index])

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
                        for unit_num2 in range(self.data_2d[reach_number].unit_number):
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
            for unit_number in range(self.data_2d[reach_number].unit_number):
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
            for unit_number in range(self.data_2d[reach_number].unit_number):
                """ unit info """
                unit_group = self.file_object["data_2d/reach_" + str(reach_number) + "/unit_" + str(unit_number)]
                if self.extension == ".hyd" or self.extension == ".hab":
                    unit_group.attrs["whole_profile_corresp"] = self.whole_profile_unit_corresp[reach_number][unit_number]
                    unit_group.attrs['total_wet_area'] = self.data_2d[reach_number][unit_number].total_wet_area

    def load_units_index(self):
        self.units_index = []
        data_2d_group = 'data_2d'
        reach_list = list(self.file_object[data_2d_group].keys())
        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            # group name
            reach_group = data_2d_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(range(len(self.file_object[reach_group].keys())))
            self.units_index.append(available_unit_list)

    def load_whole_profile(self):
        # create dict
        data_2d_whole_profile_group = 'data_2d_whole_profile'
        reach_list = list(self.file_object[data_2d_whole_profile_group].keys())

        unit_list = []
        for reach_number in range(len(reach_list)):
            unit_list.append(self.file_object[data_2d_whole_profile_group + "/" + reach_list[reach_number]].keys())

        self.data_2d_whole = Data2d(reach_number=len(reach_list),
                                    unit_list=unit_list)  # new
        self.data_2d_whole.set_unit_list(self.data_2d.unit_list)
        self.data_2d_whole.unit_list = []

        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            self.data_2d_whole.unit_list.append([])
            reach_group = data_2d_whole_profile_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            if not available_unit_list == ["unit_all"]:
                available_unit_list.sort(key=lambda x: float(x.split('_')[1]))
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
        """
        Full empty data data_2d (light data_2d) previously created with get_hdf5_attributes, is used to be filled with data at specific
        reach and unit, from user choices (units_index arg in load_hdf5).
        """
        data_2d_group = 'data_2d'
        reach_list = list(self.file_object[data_2d_group].keys())

        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            # group name
            reach_group = data_2d_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            available_unit_list.sort(key=lambda x: float(x.split('_')[1]))
            for unit_number, unit_group_name in enumerate(available_unit_list):
                if unit_number in self.units_index[reach_number]:
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

                    # HSI by celle for each fish
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

    def load_data_2d_info(self):
        data_2d_group = 'data_2d'
        reach_list = list(self.file_object[data_2d_group].keys())
        # for each reach
        for reach_number, reach_group_name in enumerate(reach_list):
            # group name
            reach_group = data_2d_group + "/" + reach_group_name
            # for each desired_units
            available_unit_list = list(self.file_object[reach_group].keys())
            available_unit_list.sort(key=lambda x: float(x.split('_')[1]))
            desired_units_list = [available_unit_list[unit_index] for unit_index in self.data_2d.units_index[reach_number]]  # get only desired_units
            self.whole_profile_unit_corresp.append([])
            for unit_number, unit_group_name in enumerate(desired_units_list):
                # group name
                unit_group = reach_group + "/" + unit_group_name
                if self.extension == ".hyd" or self.extension == ".hab":
                    self.data_2d[reach_number][unit_number].total_wet_area = self.file_object[unit_group].attrs[
                        'total_wet_area']
                    self.data_2d[reach_number][unit_number].whole_profile_corresp = self.file_object[unit_group].attrs['whole_profile_corresp']
                    self.whole_profile_unit_corresp[reach_number].append(self.file_object[unit_group].attrs['whole_profile_corresp'])

                if self.extension == ".hab":
                    # group
                    mesh_group = unit_group + "/mesh"
                    mesh_hv_data_group = self.file_object[mesh_group + "/hv_data"]
                    for animal in self.data_2d.hvum.hdf5_and_computable_list.hdf5s().meshs().habs():
                        # dataset
                        fish_data_set = mesh_hv_data_group[animal.name]

                        # get summary data
                        if len(animal.wua) < len(reach_list):
                            animal.wua.append([])
                            animal.osi.append([])
                            animal.percent_area_unknown.append([])
                        animal.wua[reach_number].append(float(fish_data_set.attrs['wua']))
                        animal.osi[reach_number].append(float(fish_data_set.attrs['osi']))
                        animal.percent_area_unknown[reach_number].append(
                            float(fish_data_set.attrs['percent_area_unknown [%m2]']))

                        # add dataset attributes
                        animal.pref_file = fish_data_set.attrs['pref_file']
                        animal.stage = fish_data_set.attrs['stage']
                        animal.name = fish_data_set.attrs['short_name']
                        animal.aquatic_animal_type = fish_data_set.attrs['aquatic_animal_type_list']

                        # replace_variable
                        self.data_2d.hvum.hdf5_and_computable_list.replace_variable(animal)

    # LOAD FILE
    def load_hdf5(self, units_index="all", user_target_list="defaut", whole_profil=False):
        # get_hdf5_attributes
        self.get_hdf5_attributes(close_file=False)

        # save unit_index for computing variables
        self.units_index = units_index
        if self.units_index == "all":
            # load the number of time steps
            self.load_units_index()

        # variables
        self.user_target_list = user_target_list
        if self.user_target_list == "defaut":  # when hdf5 is created (by project preferences)
            self.data_2d.hvum.get_final_variable_list_from_project_properties(self.project_properties,
                                                                              hdf5_type=self.hdf5_type)
        elif type(self.user_target_list) == dict:  # project_properties
            self.project_properties = self.user_target_list
            self.data_2d.hvum.get_final_variable_list_from_project_properties(self.project_properties,
                                                                              hdf5_type=self.hdf5_type)
        elif user_target_list is None:
            pass
        else:  # all
            self.data_2d.hvum.get_final_variable_list_from_wish(self.user_target_list)

        # load_whole_profile
        if whole_profil:
            self.load_whole_profile()

        if user_target_list is not None:
            # load_data_2d
            self.load_data_2d()

        # close file
        self.close_file()

        # compute ?
        if self.data_2d.hvum.all_final_variable_list.to_compute():
            self.data_2d.compute_variables(self.data_2d.hvum.all_final_variable_list.to_compute())

    # HYDRAULIC
    def create_hdf5_hyd(self, data_2d, data_2d_whole, project_properties):
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
        self.project_properties = project_properties

        # save hyd attributes to hdf5 file
        self.set_hdf5_attributes()

        # create_whole_profile to hdf5 file
        self.write_whole_profile()

        # create_data_2d to hdf5 file
        self.write_data_2d()

        # create_data_2d_info
        self.write_data_2d_info()

        # save XML
        self.save_xml(self.data_2d.hyd_model_type,
                      self.data_2d.path_filename_source)

        # close file
        self.close_file()

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
        if not self.project_properties["restarted"]:
            copy_shapefiles(
                os.path.join(self.data_2d.path_filename_source, self.data_2d.filename_source),
                self.filename,
                os.path.join(self.path_prj, "input"),
                remove=False)

        # save XML
        self.save_xml("SUBSTRATE", self.data_2d.path_filename_source)

    def load_hdf5_sub(self, user_target_list="defaut"):
        # get_hdf5_attributes
        self.get_hdf5_attributes(close_file=False)

        # units_index
        if self.data_2d.sub_mapping_method != "constant":
            self.load_units_index()

        # variables
        self.user_target_list = user_target_list
        if self.user_target_list == "defaut":  # when hdf5 is created (by project preferences)
            self.data_2d.hvum.get_final_variable_list_from_project_properties(self.project_properties,
                                                                              hdf5_type=self.hdf5_type)
        elif type(self.user_target_list) == dict:  # project_properties
            self.project_properties = self.user_target_list
            self.data_2d.hvum.get_final_variable_list_from_project_properties(self.project_properties,
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
    def create_hdf5_hab(self, data_2d, data_2d_whole, project_properties):
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
        self.project_properties = project_properties

        # save hyd attributes to hdf5 file
        self.set_hdf5_attributes()

        # create_whole_profile to hdf5 file
        self.write_whole_profile()

        # create_data_2d to hdf5 file
        self.write_data_2d()

        # create_data_2d_info
        self.write_data_2d_info()

        # copy input files to input project folder (only not merged, .hab directly from a input file as ASCII, LAMMI)
        if not project_properties["restarted"] and self.data_2d.hvum.hydraulic_class.name not in self.data_2d.hvum.hdf5_and_computable_list.names():
            if self.data_2d.hyd_model_type in ("ascii", "lammi"):
                if self.data_2d.hyd_model_type == "lammi":
                    # if lammi Transect.txt
                    prj_list_file = [s for s in os.listdir(self.data_2d.hyd_path_filename_source) if s.endswith('.prn')]
                    self.data_2d.hyd_filename_source = self.data_2d.hyd_filename_source + ", " + ", ".join(prj_list_file)
                # copy_hydrau_input_files
                copy_hydrau_input_files(self.data_2d.hyd_path_filename_source,
                                        self.data_2d.hyd_filename_source,
                                        self.filename,
                                        os.path.join(project_properties["path_prj"], "input"))

        # save XML
        self.save_xml("HABITAT", "")

        if self.data_2d.hvum.hdf5_and_computable_list.habs():
            self.add_fish_hab(self.data_2d.hvum.hdf5_and_computable_list.habs(), from_mm=True)
            self.export_osi_wua_txt()  # export_osi_wua_txt

        # close file
        self.close_file()

    def add_fish_hab(self, animal_variable_list, from_mm=False):
        """
        Add habitat computation in an existing .hab file.
        """
        if not from_mm:
            self.create_or_open_file()
            # add variables
            self.data_2d.hvum.hdf5_and_computable_list.extend(animal_variable_list)

        # data_2d
        data_group = self.file_object['data_2d']
        # REACH GROUP
        for reach_number in range(self.data_2d.reach_number):
            reach_group = data_group["reach_" + str(reach_number)]
            # UNIT GROUP
            for unit_number in range(self.data_2d[reach_number].unit_number):
                unit_group = reach_group["unit_" + str(unit_number)]
                # MESH GROUP
                mesh_group = unit_group["mesh"]
                mesh_hv_data_group = mesh_group["hv_data"]

                if from_mm:
                    hab_list = self.data_2d.hvum.hdf5_and_computable_list.meshs().habs()
                else:
                    hab_list = self.data_2d.hvum.hdf5_and_computable_list.meshs().to_compute().habs()

                # HSI by celle for each fish
                for animal_num, animal in enumerate(hab_list):
                    # create
                    if animal.name in mesh_hv_data_group:
                        del mesh_hv_data_group[animal.name]
                    fish_data_set = mesh_hv_data_group.create_dataset(name=animal.name,
                                                                      shape=self.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name].shape,
                                                                      data=self.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name].to_numpy(),
                                                                      dtype=self.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name].dtype)

                    # add dataset attributes
                    fish_data_set.attrs['pref_file'] = animal.pref_file
                    fish_data_set.attrs['stage'] = animal.stage
                    fish_data_set.attrs['short_name'] = animal.name
                    fish_data_set.attrs['aquatic_animal_type_list'] = animal.aquatic_animal_type
                    fish_data_set.attrs['wua'] = str(animal.wua[reach_number][unit_number])
                    fish_data_set.attrs['osi'] = str(animal.osi[reach_number][unit_number])
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
        self.edit = True
        self.create_or_open_file()
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

        # data_2d
        data_group = self.file_object['data_2d']
        # for each reach
        for reach_number in range(self.data_2d.reach_number):
            reach_group = data_group["reach_" + str(reach_number)]
            # for each unit
            for unit_number in range(self.data_2d[reach_number].unit_number):
                unit_group = reach_group["unit_" + str(unit_number)]
                mesh_group = unit_group["mesh"]
                mesh_hv_data_group = mesh_group["hv_data"]
                for fish_name_to_remove in fish_names_to_remove:
                    del mesh_hv_data_group[fish_name_to_remove]

        self.close_file()

    # HYDROSIGNATURE
    def write_hydrosignature(self, hs_export_mesh=False):
        # for each reach
        for reach_number in range(self.data_2d.reach_number):
            # for each unit
            for unit_number in range(self.data_2d[reach_number].unit_number):
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
                    if key in self.file_object[unitpath].attrs.keys():
                        del self.file_object[unitpath].attrs[key]
                    if key == "classhv":
                        pass
                    else:
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

        self.hs_calculated = True
        self.file_object.attrs.create("hs_calculated", True)
        if "hs_input_class_h" in self.file_object.attrs.keys():
            del self.file_object.attrs["hs_input_class_h"]
            del self.file_object.attrs["hs_input_class_v"]
        self.file_object.attrs.create("hs_input_class_h", self.data_2d[0][0].hydrosignature["classhv"][0])
        self.file_object.attrs.create("hs_input_class_v", self.data_2d[0][0].hydrosignature["classhv"][1])
        if hs_export_mesh:
            self.hs_mesh = True
            self.file_object.attrs.create("hs_mesh", True)

    def load_hydrosignature(self):
        self.get_hdf5_attributes(close_file=False)
        for reach_number in range(self.data_2d.reach_number):
            for unit_index in range(self.data_2d[reach_number].unit_number):
                unitpath = "data_2d/reach_" + str(reach_number) + "/unit_" + str(unit_index)
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
                self.data_2d[reach_number][unit_index].hydrosignature = {}
                for key in keylist:
                    if key == "classhv":
                        self.data_2d[reach_number][unit_index].hydrosignature[key] = [self.file_object.attrs["hs_input_class_h"],
                                               self.file_object.attrs["hs_input_class_v"]]
                    else:
                        self.data_2d[reach_number][unit_index].hydrosignature[key] = self.file_object[unitpath].attrs[key]
                self.data_2d[reach_number][unit_index].hydrosignature["hsarea"] = self.file_object[unitpath + "/hsarea"][:]
                self.data_2d[reach_number][unit_index].hydrosignature["hsvolume"] = self.file_object[unitpath + "/hsvolume"][:]

    def export_hydrosignature_txt(self):
        if not os.path.exists(self.path_txt):
            print('Error: ' + qt_tr.translate("hdf5_mod",
                                              'The path to the text file is not found. Text files not created \n'))
        else:
            for reach_number in range(self.data_2d.reach_number):
                name = self.basename + "_" + self.data_2d[reach_number].reach_name + '_HSresult.txt'
                if os.path.isfile(os.path.join(self.path_txt, name)):
                    if not self.project_properties['erase_id']:
                        name = self.basename + "_" + self.data_2d[reach_number].reach_name + '_HSresult_' + \
                               time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    else:
                        try:
                            os.remove(os.path.join(self.path_txt, name))
                        except PermissionError:
                            print('Error: ' + qt_tr.translate("hdf5_mod",
                                                              'Could not modify text file as it is open in another program. \n'))
                            continue
                # hsexporttxt
                for unit_number in range(self.data_2d[reach_number].unit_number):
                    hsexporttxt(self.path_txt,
                                name,
                                self.data_2d[reach_number][unit_number].hydrosignature["classhv"],
                                self.data_2d[reach_number][unit_number].unit_name,
                                self.data_2d[reach_number][unit_number].hydrosignature["nb_mesh"],
                                self.data_2d[reach_number][unit_number].hydrosignature["total_area"],
                                self.data_2d[reach_number][unit_number].hydrosignature["total_volume"],
                                self.data_2d[reach_number][unit_number].hydrosignature["mean_depth"],
                                self.data_2d[reach_number][unit_number].hydrosignature["mean_velocity"],
                                self.data_2d[reach_number][unit_number].hydrosignature["mean_froude"],
                                self.data_2d[reach_number][unit_number].hydrosignature["min_depth"],
                                self.data_2d[reach_number][unit_number].hydrosignature["max_depth"],
                                self.data_2d[reach_number][unit_number].hydrosignature["min_velocity"],
                                self.data_2d[reach_number][unit_number].hydrosignature["max_velocity"],
                                self.data_2d[reach_number][unit_number].hydrosignature["hsarea"],
                                self.data_2d[reach_number][unit_number].hydrosignature["hsvolume"])

    # ESTIMHAB
    def create_hdf5_estimhab(self, estimhab_dict, project_properties):
        # hdf5_type
        self.hdf5_type = "ESTIMHAB"

        # save dict to attribute
        self.project_properties = project_properties

        # intput data
        self.file_object.attrs["path_bio_estimhab"] = estimhab_dict["path_bio"]
        self.file_object.create_dataset('qmes', [2, 1], data=estimhab_dict["q"])
        self.file_object.create_dataset("wmes", [2, 1], data=estimhab_dict["w"])
        self.file_object.create_dataset("hmes", [2, 1], data=estimhab_dict["h"])
        self.file_object.create_dataset("q50", [1, 1], data=estimhab_dict["q50"])
        if type(estimhab_dict["qrange"]) == str:
            self.file_object.create_dataset("qrange", [1, 1], data=estimhab_dict["qrange"])
        else:
            self.file_object.create_dataset("qrange", [3, 1], data=estimhab_dict["qrange"])
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
        self.file_object.create_dataset("OSI", estimhab_dict["OSI"].shape, data=estimhab_dict["OSI"])
        self.file_object.create_dataset("WUA", estimhab_dict["WUA"].shape, data=estimhab_dict["WUA"])

        # close
        self.close_file()

    def load_hdf5_estimhab(self):
        # load dataset
        if type(self.file_object["qrange"][:].flatten().tolist()[0]) == bytes:
            qrange = self.file_object["qrange"][:].flatten().tolist()[0].decode("utf-8")
        else:
            qrange = self.file_object["qrange"][:].flatten().tolist()

        estimhab_dict = dict(q=self.file_object["qmes"][:].flatten().tolist(),
                             w=self.file_object["wmes"][:].flatten().tolist(),
                             h=self.file_object["hmes"][:].flatten().tolist(),
                             q50=self.file_object["q50"][:].flatten().tolist()[0],
                             substrate=self.file_object["substrate"][:].flatten().tolist()[0],
                             path_bio=self.file_object.attrs["path_bio_estimhab"],
                             xml_list=self.file_object["xml_list"][:].flatten().astype(np.str).tolist(),
                             fish_list=self.file_object["fish_list"][:].flatten().astype(np.str).tolist(),
                             qrange=qrange,
                             q_all=self.file_object["q_all"][:],
                             h_all=self.file_object["h_all"][:],
                             w_all=self.file_object["w_all"][:],
                             vel_all=self.file_object["vel_all"][:],
                             OSI=self.file_object["OSI"][:],
                             WUA=self.file_object["WUA"][:])

        # close file
        self.close_file()

        # save attrivbute
        self.estimhab_dict = estimhab_dict

    def export_estimhab_txt(self):
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
        OSI = self.estimhab_dict["OSI"]
        WUA = self.estimhab_dict["WUA"]
        output_filename = "Estimhab"
        intput_filename = "Estimhab_input"

        # check if exist and erase
        if os.path.exists(os.path.join(self.path_txt, output_filename + '.txt')):
            if not self.project_properties["erase_id"]:
                output_filename = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                intput_filename = "Estimhab_input_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")

        # prep data
        all_data = np.vstack((q_all, h_all, w_all, vel_all))
        for f in range(0, len(fish_name)):
            txt_header += '\tOSI_' + fish_name[f] + '\tWUA_' + fish_name[f]
            all_data = np.vstack((all_data, OSI[f]))
            all_data = np.vstack((all_data, WUA[f]))

        txt_header += '\n[m3/s]\t[m]\t[m]\t[m/s]'
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
        if type(qrange) == str:
            txtin += 'Chronicle discharge [m3/sec]:\t' + qrange + '\n'
        else:
            txtin += 'Minimum and maximum discharge [m3/sec]:\t' + str(qrange[0]) + '\t' + str(qrange[1]) + '\n'
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

    """ EXPORT 2D """
    def load_data_to_export(self, user_target_list, whole_profil=False):
        self.create_or_open_file()
        self.load_hdf5(whole_profil=whole_profil,
                        user_target_list=user_target_list)

    def export_gpkg_mesh_whole_profile(self, state=None):
        # load_data_top_export
        self.load_data_to_export(user_target_list=None, whole_profil=True)

        # progress
        delta_reach = 80 / self.data_2d.reach_number

        # for each reach : one gpkg
        for reach_number in range(0, self.data_2d.reach_number):
            # name
            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + ".gpkg"
            filename_path = os.path.join(self.path_gis, filename)

            # for all units
            filename_path_list = []
            layer_name_list = []
            crs_list = []
            unit_data_list = []
            delta_mesh_list = []
            for unit_number in range(0, self.data_2d_whole[reach_number].unit_number):
                # layer_name
                if not self.data_2d.hyd_varying_mesh:
                    # progress
                    delta_unit = delta_reach
                    layer_name = "mesh_wholeprofile_allunits"
                else:
                    # progress
                    delta_unit = delta_reach / self.data_2d[reach_number].unit_number
                    layer_name = "mesh_wholeprofile_" + self.data_2d_whole.unit_list[reach_number][
                        unit_number]

                # hvum copy
                self.data_2d[reach_number][unit_number].hvum = self.data_2d.hvum

                # append args to list
                filename_path_list.append(os.path.splitext(filename_path)[0])
                layer_name_list.append(layer_name)
                crs_list.append(self.data_2d.epsg_code)
                unit_data_list.append(self.data_2d_whole[reach_number][unit_number])
                delta_mesh_list.append(
                    delta_unit / self.data_2d_whole[reach_number][unit_number]["mesh"]["tin"].shape[0])

                # stop loop in this case (if one unit in whole profile)
                if not self.data_2d.hyd_varying_mesh:
                    break

            # conca to Pool
            input_data = zip(filename_path_list,
                             layer_name_list,
                             crs_list,
                             unit_data_list,
                             [True] * len(filename_path_list),
                             delta_mesh_list)

            # Pool
            lock = Lock()  # to share progress_value
            if state is None:
                state = Value("d", 0.0)
            if len(filename_path_list) > cpu_count():
                cpu_value = cpu_count()
            else:
                cpu_value = len(filename_path_list)
            if cpu_value <= 0:
                cpu_value = 1
            pool = Pool(processes=cpu_value, initializer=setup, initargs=[state, lock])
            try:
                pool.starmap(export_mesh_layer_to_gpkg, input_data)
            except OSError:
                print("Error: Insufficient system resources to complete " + "export_gpkg_mesh_whole_profile" ".")

            # merge_gpkg_to_one
            merge_gpkg_to_one(filename_path_list, layer_name_list, filename_path)

        if state is not None:
            state.value = 100.0  # process finished

    def export_gpkg_mesh_units(self, state=None):
        # load_data_top_export
        self.load_data_to_export(user_target_list="all")

        # progress
        delta_reach = 80 / self.data_2d.reach_number
        # for each reach : one gpkg
        for reach_number in range(0, self.data_2d.reach_number):
            # name
            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + ".gpkg"
            filename_path = os.path.join(self.path_gis, filename)

            # for all units
            filename_path_list = []
            layer_name_list = []
            crs_list = []
            unit_data_list = []
            delta_mesh_list = []
            for unit_number in range(0, self.data_2d[reach_number].unit_number):
                # layer_name
                layer_name = "mesh_" + self.units_name_output[reach_number][unit_number]

                # progress
                delta_unit = delta_reach / self.data_2d[reach_number].unit_number

                # hvum copy
                self.data_2d[reach_number][unit_number].hvum = self.data_2d.hvum

                # append args to list
                filename_path_list.append(os.path.splitext(filename_path)[0])
                layer_name_list.append(layer_name)
                crs_list.append(self.data_2d.epsg_code)
                unit_data_list.append(self.data_2d[reach_number][unit_number])
                delta_mesh_list.append(delta_unit / self.data_2d[reach_number][unit_number]["mesh"]["tin"].shape[0])

            # conca to Pool
            input_data = zip(filename_path_list,
                             layer_name_list,
                             crs_list,
                             unit_data_list,
                             [False] * len(filename_path_list),
                             delta_mesh_list)

            # Pool
            lock = Lock()  # to share progress_value
            if state is None:
                state = Value("d", 0.0)
            if len(filename_path_list) > cpu_count():
                cpu_value = int(cpu_count() / 2)
            else:
                cpu_value = int(len(filename_path_list) / 2)
            if cpu_value <= 0:
                cpu_value = 1
            pool = Pool(processes=cpu_value, initializer=setup, initargs=[state, lock])

            try:
                pool.starmap(export_mesh_layer_to_gpkg, input_data)
            except OSError:
                print("Error: Insufficient system resources to complete " + "export_gpkg_mesh_units" ".")

            # merge_gpkg_to_one
            merge_gpkg_to_one(filename_path_list, layer_name_list, filename_path)

        if state is not None:
            state.value = 100.0  # process finished

    def export_gpkg_point_whole_profile(self, state=None):
        # load_data_top_export
        self.load_data_to_export(user_target_list=None, whole_profil=True)

        # progress
        delta_reach = 80 / self.data_2d.reach_number

        # for each reach : one gpkg
        for reach_number in range(0, self.data_2d.reach_number):
            # name
            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + ".gpkg"
            filename_path = os.path.join(self.path_gis, filename)

            # for all units
            filename_path_list = []
            layer_name_list = []
            crs_list = []
            unit_data_list = []
            delta_node_list = []
            for unit_number in range(0, self.data_2d_whole[reach_number].unit_number):
                # layer_name
                if not self.data_2d.hyd_varying_mesh:
                    # progress
                    delta_unit = delta_reach
                    layer_name = "node_wholeprofile_allunits"
                else:
                    # progress
                    delta_unit = delta_reach / self.data_2d[reach_number].unit_number
                    layer_name = "node_wholeprofile_" + self.data_2d_whole.unit_list[reach_number][
                        unit_number]

                # hvum copy
                self.data_2d[reach_number][unit_number].hvum = self.data_2d.hvum

                # append args to list
                filename_path_list.append(os.path.splitext(filename_path)[0])
                layer_name_list.append(layer_name)
                crs_list.append(self.data_2d.epsg_code)
                unit_data_list.append(self.data_2d_whole[reach_number][unit_number])
                delta_node_list.append(
                    delta_unit / self.data_2d_whole[reach_number][unit_number]["node"]["xy"].shape[0])

                # stop loop in this case (if one unit in whole profile)
                if not self.data_2d.hyd_varying_mesh:
                    break

            # conca to Pool
            input_data = zip(filename_path_list,
                             layer_name_list,
                             crs_list,
                             unit_data_list,
                             [True] * len(filename_path_list),
                             delta_node_list)

            # Pool
            lock = Lock()  # to share progress_value
            if state is None:
                state = Value("d", 0.0)
            if len(filename_path_list) > cpu_count():
                cpu_value = cpu_count()
            else:
                cpu_value = len(filename_path_list)
            if cpu_value <= 0:
                cpu_value = 1
            pool = Pool(processes=cpu_value, initializer=setup, initargs=[state, lock])
            try:
                pool.starmap(export_node_layer_to_gpkg, input_data)
            except OSError:
                print("Error: Insufficient system resources to complete " + "export_gpkg_point_whole_profile" ".")
            # merge_gpkg_to_one
            merge_gpkg_to_one(filename_path_list, layer_name_list, filename_path)

        if state is not None:
            state.value = 100.0  # process finished

    def export_gpkg_point_units(self, state=None):
        # load_data_top_export
        self.load_data_to_export(user_target_list="all")

        # progress
        delta_reach = 80 / self.data_2d.reach_number

        # for each reach : one gpkg
        for reach_number in range(0, self.data_2d.reach_number):
            # name
            filename = self.basename + "_" + self.data_2d.reach_list[reach_number] + ".gpkg"
            filename_path = os.path.join(self.path_gis, filename)

            # for all units
            filename_path_list = []
            layer_name_list = []
            crs_list = []
            unit_data_list = []
            delta_node_list = []
            for unit_number in range(0, self.data_2d[reach_number].unit_number):
                # layer_name
                layer_name = "node_" + self.units_name_output[reach_number][unit_number]

                # progress
                delta_unit = delta_reach / self.data_2d[reach_number].unit_number

                # hvum copy
                self.data_2d[reach_number][unit_number].hvum = self.data_2d.hvum

                # append args to list
                filename_path_list.append(os.path.splitext(filename_path)[0])
                layer_name_list.append(layer_name)
                crs_list.append(self.data_2d.epsg_code)
                unit_data_list.append(self.data_2d[reach_number][unit_number])
                delta_node_list.append(delta_unit / self.data_2d[reach_number][unit_number]["node"]["xy"].shape[0])

            # conca to Pool
            input_data = zip(filename_path_list,
                             layer_name_list,
                             crs_list,
                             unit_data_list,
                             [False] * len(filename_path_list),
                             delta_node_list)

            # Pool
            lock = Lock()  # to share progress_value
            if state is None:
                state = Value("d", 0.0)
            if len(filename_path_list) > cpu_count():
                cpu_value = int(cpu_count() / 2)
            else:
                cpu_value = int(len(filename_path_list) / 2)
            if cpu_value <= 0:
                cpu_value = 1
            pool = Pool(processes=cpu_value, initializer=setup, initargs=[state, lock])
            try:
                pool.starmap(export_node_layer_to_gpkg, input_data)
            except OSError:
                print("Error: Insufficient system resources to complete " + "export_gpkg_point_units" ".")

            # merge_gpkg_to_one
            merge_gpkg_to_one(filename_path_list, layer_name_list, filename_path)

        if state is not None:
            state.value = 100.0  # process finished

    def export_stl(self, state=None):
        """ create stl whole profile (to see topography) """
        # load_data_top_export
        self.load_data_to_export(user_target_list=None, whole_profil=True)

        # for all reach
        for reach_number in range(self.data_2d_whole.reach_number):
            # for all units
            for unit_number in range(self.data_2d_whole[reach_number].unit_number):
                # get data
                xy = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name]
                z = self.data_2d_whole[reach_number][unit_number]["node"][self.data_2d.hvum.z.name] * self.project_properties[
                    "vertical_exaggeration"]
                tin = self.data_2d_whole[reach_number][unit_number]["mesh"][self.data_2d.hvum.tin.name]
                xyz = np.column_stack([xy, z])
                # Create the mesh
                stl_file = mesh.Mesh(np.zeros(tin.shape[0], dtype=mesh.Mesh.dtype))
                for i, f in enumerate(tin):
                    for j in range(3):
                        stl_file.vectors[i][j] = xyz[f[j], :]
                # filename
                name_file = strip_accents(self.basename + "_" + self.data_2d.reach_list[reach_number] + "_" + \
                            self.data_2d_whole.unit_list[reach_number][
                                unit_number] + "_wholeprofile_mesh.stl")

                if self.project_properties['erase_id']:  # erase file if exist ?
                    if os.path.isfile(os.path.join(self.path_3d, name_file)):
                        try:
                            os.remove(os.path.join(self.path_3d, name_file))
                        except PermissionError:
                            print(
                                'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                            return
                else:
                    if os.path.isfile(os.path.join(self.path_3d, name_file)):
                        name_file = self.basename + "_whole_profile_point_r0_t0_" + time.strftime(
                            "%d_%m_%Y_at_%H_%M_%S") + '.shp'
                # Write the mesh to file "cube.stl"
                stl_file.save(os.path.join(self.path_3d,
                                           name_file))

        if state is not None:
            state.value = 100.0  # process finished

    def export_paraview(self, state=None):
        # load_data_top_export
        self.load_data_to_export(user_target_list="all")

        file_names_all = []
        part_timestep_indice = []
        pvd_variable_z = self.data_2d.hvum.all_sys_variable_list.get_from_name_gui(self.project_properties["pvd_variable_z"])

        # for all reach
        for reach_number in range(self.data_2d.reach_number):
            # for all units
            for unit_number in range(self.data_2d[reach_number].unit_number):
                part_timestep_indice.append((reach_number, unit_number))
                # create one vtu file by time step
                x = np.ascontiguousarray(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][:, 0])
                y = np.ascontiguousarray(self.data_2d[reach_number][unit_number]["node"][self.data_2d.hvum.xy.name][:, 1])
                z = np.ascontiguousarray(
                    self.data_2d[reach_number][unit_number]["node"]["data"][pvd_variable_z.name].to_numpy() *
                    self.project_properties["vertical_exaggeration"])
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
                name_file = os.path.join(self.path_3d,
                                         self.basename_output_reach_unit[reach_number][unit_number] + "_" +
                                         self.project_properties['pvd_variable_z'])
                if self.project_properties['erase_id']:  # erase file if exist ?
                    if os.path.isfile(os.path.join(self.path_3d, name_file)):
                        try:
                            os.remove(os.path.join(self.path_3d, name_file))
                        except PermissionError:
                            print(
                                'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                            return
                else:
                    if os.path.isfile(os.path.join(self.path_3d, name_file)):
                        name_file = os.path.join(self.path_3d,
                                                 self.basename_output_reach_unit[reach_number][unit_number] + "_" +
                                                 self.project_properties['pvd_variable_z']) + "_" + time.strftime(
                            "%d_%m_%Y_at_%H_%M_%S")
                file_names_all.append(name_file + ".vtu")
                unstructuredGridToVTK(name_file, x, y, z, connectivity, offsets, cell_types,
                                             cellData)

        # create the "grouping" file to read all time step together
        name_here = self.basename + "_" + strip_accents(self.data_2d.reach_list[reach_number]) + "_" + self.project_properties[
            'pvd_variable_z'] + ".pvd"
        file_names_all = list(map(os.path.basename, file_names_all))
        if self.project_properties['erase_id']:  # erase file if exist ?
            if os.path.isfile(os.path.join(self.path_3d, name_here)):
                try:
                    os.remove(os.path.join(self.path_3d, name_here))
                except PermissionError:
                    print(
                        'Error: The file .pvd is currently open in an other program. Could not be re-written \n')
                    return
        else:
            if os.path.isfile(os.path.join(self.path_3d, name_here)):
                name_here = self.basename + "_" + self.reach_name[reach_number] + "_" + self.project_properties[
                    'pvd_variable_z'] + "_" + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + '.pvd'
        writePVD(os.path.join(self.path_3d, name_here), file_names_all,
                 part_timestep_indice)

        if state is not None:
            state.value = 100.0  # process finished

    def export_detailled_mesh_txt(self, state=None):
        """
        detailled mesh
        """
        # load_data_top_export
        self.load_data_to_export(user_target_list="all")

        if not os.path.exists(self.path_txt):
            print('Error: ' + qt_tr.translate("hdf5_mod",
                                              'The path to the text file is not found. Text files not created \n'))
        # progress
        delta_reach = 100 / self.data_2d.reach_number

        # for all reach
        name_list = []
        hvum_list = []
        unit_data_list = []
        delta_mesh_list = []
        for reach_number in range(self.data_2d.reach_number):
            # progress
            delta_unit = delta_reach / self.data_2d[reach_number].unit_number
            # for all units
            for unit_number in range(self.data_2d[reach_number].unit_number):
                name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate("hdf5_mod",
                                                                                                    "detailled_mesh") + ".txt"
                if os.path.isfile(os.path.join(self.path_txt, name)):
                    if not self.project_properties['erase_id']:
                        name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate(
                            "hdf5_mod", "detailled_mesh") + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    else:
                        try:
                            os.remove(os.path.join(self.path_txt, name))
                        except PermissionError:
                            print('Error: ' + qt_tr.translate("hdf5_mod",
                                                              'Could not modify text file as it is open in another program. \n'))
                            return
                name_list.append(os.path.join(self.path_txt, name))
                hvum_list.append(self.data_2d.hvum)
                unit_data_list.append(self.data_2d[reach_number][unit_number]["mesh"])
                delta_mesh_list.append(delta_unit / self.data_2d[reach_number][unit_number]["mesh"]["tin"].shape[0])

        # Pool
        input_data = zip(name_list,
                         hvum_list,
                         unit_data_list,
                         delta_mesh_list)
        lock = Lock()  # to share progress_value
        if state is None:
            state = Value("d", 0.0)

        # part
        cpu_value = cpu_count()
        pool = Pool(processes=cpu_value, initializer=setup, initargs=[state, lock])
        try:
            pool.starmap(export_mesh_txt, input_data)
        except OSError:
            print("Error: Insufficient system resources to complete " + "export_detailled_mesh_txt" ".")

        if state is not None:
            state.value = 100.0  # process finished

    def export_detailled_point_txt(self, state=None):
        """
         detailled mesh
         """
        # load_data_top_export
        self.load_data_to_export(user_target_list="all")

        if not os.path.exists(self.path_txt):
            print('Error: ' + qt_tr.translate("hdf5_mod",
                                              'The path to the text file is not found. Text files not created \n'))
        # progress
        delta_reach = 100 / self.data_2d.reach_number

        # for all reach
        name_list = []
        hvum_list = []
        unit_data_list = []
        delta_node_list = []
        for reach_number in range(self.data_2d.reach_number):
            # progress
            delta_unit = delta_reach / self.data_2d[reach_number].unit_number

            # for all units
            for unit_number in range(self.data_2d[reach_number].unit_number):
                name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate("hdf5_mod",
                                                                                                    "detailled_point") + ".txt"
                if os.path.isfile(os.path.join(self.path_txt, name)):
                    if not self.project_properties['erase_id']:
                        name = self.basename_output_reach_unit[reach_number][unit_number] + "_" + qt_tr.translate(
                            "hdf5_mod", "detailled_point") + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    else:
                        try:
                            os.remove(os.path.join(self.path_txt, name))
                        except PermissionError:
                            print('Error: ' + qt_tr.translate("hdf5_mod",
                                                              'Could not modify text file as it is open in another program. \n'))
                            return
                name_list.append(os.path.join(self.path_txt, name))
                hvum_list.append(self.data_2d.hvum)
                unit_data_list.append(self.data_2d[reach_number][unit_number]["node"])
                delta_node_list.append(delta_unit)

        # Pool
        input_data = zip(name_list,
                         hvum_list,
                         unit_data_list,
                         delta_node_list)
        lock = Lock()  # to share progress_value
        if state is None:
            state = Value("d", 0.0)
        pool = Pool(processes=1, initializer=setup, initargs=[state, lock])
        try:
            pool.starmap(export_point_txt, input_data)
        except OSError:
            print("Error: Insufficient system resources to complete " + "export_detailled_point_txt" ".")

        if state is not None:
            state.value = 100.0  # process finished

    def export_report(self, state=None):
        """
        # xmlfiles, stages_chosen, path_bio, path_im_bio, path_out, self.project_properties
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
        # print(qt_tr.translate("hdf5_mod",
        #                                   'Export report in progress.'))
        qt_tr2 = get_translator(self.path_prj)

        # print('qt_tr2.translate("hdf5_mod",
        #                                   'Export report in progress!.'))
        if state is not None:
            state.value = 1
        # load_data_top_export
        self.load_data_to_export(user_target_list=None, whole_profil=False)

        # remove duplicates xml
        xmlfiles = list(set(self.data_2d.hvum.hdf5_and_computable_list.habs().pref_files()))
        xmlfiles.sort()

        for xmlfile in xmlfiles:
            export_report(xmlfile, self.project_properties, qt_tr2, state, delta_animal=100 / len(xmlfiles))

        # input_data = zip(xmlfiles,
        #     [self.project_properties] * len(xmlfiles),
        #                  [100 / len(xmlfiles)] * len(xmlfiles))
        #
        # lock = Lock()  # to share progress_value
        # if state is None:
        #     state = Value("d", 0.0)
        #
        # if len(xmlfiles) > cpu_count():
        #     cpu_value = cpu_count()
        # else:
        #     cpu_value = len(xmlfiles)
        # pool = Pool(processes=4, initializer=setup, initargs=[state, lock])
        # try:
        #     pool.starmap(export_report, input_data)
        # except OSError:
        #     print("Error: Insufficient system resources to complete " + "export_report" ".")

        if state is not None:
            state.value = 100.0  # process finished

    def export_osi_wua_txt(self, state=None):
        if not os.path.exists(self.path_txt):
            print('Error: ' + qt_tr.translate("hdf5_mod",
                                              'The path to the text file is not found. Text files not created \n'))
        else:
            animal_list = self.data_2d.hvum.hdf5_and_computable_list.habs()
            if animal_list:
                sim_name = self.data_2d.unit_list
                unit_type = self.data_2d.unit_type[self.data_2d.unit_type.find('[') + 1:self.data_2d.unit_type.find(']')]

                name = self.basename + '_wua.txt'
                if os.path.isfile(os.path.join(self.path_txt, name)):
                    if not self.project_properties['erase_id']:
                        name = self.basename + '_wua_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
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
                    if self.project_properties['language'] == 0:
                        header = 'reach\tunit\treach_area'
                    else:
                        header = 'troncon\tunit\taire_troncon'
                    header += "".join(['\tOSI' for _ in range(len(animal_list))])
                    header += "".join(['\tWUA' for _ in range(len(animal_list))])
                    header += "".join(['\tUA' for _ in range(len(animal_list))])
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
                    header = 'all\tall\tall'
                    for animal in animal_list * 3:
                        header += '\t' + animal.name.replace(' ', '_')
                    header += '\n'
                    f.write(header)

                    for reach_number in range(self.data_2d.reach_number):
                        for unit_number in range(self.data_2d[reach_number].unit_number):
                            area_reach = self.data_2d[reach_number][unit_number].total_wet_area
                            if not sim_name:
                                data_here = str(reach_number) + '\t' + str(unit_number) + '\t' + str(area_reach)
                            else:
                                data_here = str(reach_number) + '\t' + str(sim_name[reach_number][unit_number]) + '\t' + str(
                                    area_reach)
                            # OSI
                            for animal in animal_list:
                                try:
                                    data_here += '\t' + str(animal.osi[reach_number][unit_number])
                                except:
                                    data_here += '\t' + 'NaN'
                            # WUA
                            for animal in animal_list:
                                try:
                                    data_here += '\t' + str(animal.wua[reach_number][unit_number])
                                except:
                                    data_here += '\t' + 'NaN'
                            # %unknwon
                            for animal in animal_list:
                                data_here += '\t' + str(animal.percent_area_unknown[reach_number][unit_number])

                            data_here += '\n'

                            # change decimal point
                            locale = QLocale()
                            if locale.decimalPoint() == ",":
                                data_here = data_here.replace('.', ',')

                            # write file
                            f.write(data_here)

        if state is not None:
            state.value = 100.0  # process finished


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
        data.load_hdf5(whole_profil=True)
        for name in data.available_export_list:
            data.project_properties[name]=[True, True]
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
    if os.path.exists(path):
        for file in os.listdir(path):
            if file.endswith(type_and_extension[type]):
                path_prj = os.path.dirname(path)
                try:
                    hdf5_file = Hdf5Management(path_prj, file, new=False, edit=False)
                    hdf5_file.get_hdf5_attributes(close_file=False)
                    if hdf5_file.file_object:
                        filenames.append(file)
                    hdf5_file.close_file()
                except Exception:
                    traceback.print_exc()
                    print("Error: ", file + " seems to be corrupted. Delete it manually.")

    filenames.sort()
    return filenames


def get_filename_hs(path):
    filenames = []

    if os.path.exists(path):
        for file in os.listdir(path):
            if file.endswith(".hyd") or file.endswith(".hab"):
                path_prj = os.path.dirname(path)
                try:
                    hdf5 = Hdf5Management(path_prj, file, new=False, edit=False)
                    if hdf5.file_object and hdf5.hs_calculated:
                        filenames.append(file)
                    hdf5.close_file()
                except Exception:
                    traceback.print_exc()
                    print("Error: HABBY hydrosignature " + file + " seems to be corrupted. Delete it manually.")

    filenames.sort()
    return filenames


def main():
    pass


if __name__ == '__main__':
    main()
