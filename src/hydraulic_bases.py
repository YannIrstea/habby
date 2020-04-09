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
import numpy as np
import pandas as pd


class HydraulicVariable:
    def __init__(self, value, unit, name, name_gui, dtype):
        self.value = value
        self.unit = unit
        self.name = name
        self.name_gui = name_gui
        self.dtype = dtype
        self.position = None
        self.existing_attributes_list = []
        self.data = [[]]
        self.computable = False


class HydraulicVariableUnitManagement:
    def __init__(self):
        self.final_variable_list = []
        self.usefull_variable_wish_list = []
        self.usefull_variable_detected_list = []
        self.usefull_variable_node_detected_list = []
        self.usefull_variable_mesh_detected_list = []
        self.final_mesh_variable_name_list = []
        self.final_node_variable_name_list = []
        # fixed values
        self.ro = HydraulicVariable(value=999.7,
                                    unit="kg/m3",
                                    name="ro",
                                    name_gui="ρ",
                                    dtype=np.float64)
        self.g = HydraulicVariable(value=9.80665,
                                   unit="m/s2",
                                   name="g",
                                   name_gui="gravity",
                                   dtype=np.float64)
        # coordinate variables
        self.tin = HydraulicVariable(value=None,
                                     unit="",
                                     name="tin",
                                     name_gui="tin",
                                     dtype=np.int64)
        self.xy = HydraulicVariable(value=None,
                                    unit="m",
                                    name="xy",
                                    name_gui="xy",
                                    dtype=np.float64)
        self.z = HydraulicVariable(value=None,
                                   unit="m",
                                   name="z",
                                   name_gui="elevation",
                                   dtype=np.float64)
        # usefull variable values
        self.h = HydraulicVariable(value=None,
                                   unit="m",
                                   name="h",
                                   name_gui="water_height",
                                   dtype=np.float64)
        self.v_u = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_u",
                                     name_gui="water_velocity_u",
                                     dtype=np.float64)
        self.v_v = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_v",
                                     name_gui="water_velocity_v",
                                     dtype=np.float64)
        self.v = HydraulicVariable(value=None,
                                   unit="m/s",
                                   name="v",
                                   name_gui="water_velocity",
                                   dtype=np.float64)
        self.level = HydraulicVariable(value=None,
                                       unit="m",
                                       name="level",
                                       name_gui="water_level",
                                       dtype=np.float64)
        self.froude = HydraulicVariable(value=None,
                                        unit="",
                                        name="froude",
                                        name_gui="froude_number",
                                        dtype=np.float64)
        self.hydraulic_head = HydraulicVariable(value=None,
                                                unit="",
                                                name="hydraulic_head",
                                                name_gui="hydraulic_head",
                                                dtype=np.float64)
        self.conveyance = HydraulicVariable(value=None,
                                            unit="",
                                            name="conveyance",
                                            name_gui="conveyance",
                                            dtype=np.float64)
        self.max_slope_bottom = HydraulicVariable(value=None,
                                                  unit="",
                                                  name="max_slope_bottom",
                                                  name_gui="max_slope_bottom",
                                                  dtype=np.float64)
        self.max_slope_energy = HydraulicVariable(value=None,
                                                  unit="",
                                                  name="max_slope_energy",
                                                  name_gui="max_slope_energy",
                                                  dtype=np.float64)
        self.shear_stress = HydraulicVariable(value=None,
                                              unit="",
                                              name="shear_stress",
                                              name_gui="shear_stress",
                                              dtype=np.float64)
        self.temp = HydraulicVariable(value=None,
                                      unit="",
                                      name="temp",
                                      name_gui="temperature",
                                      dtype=np.float64)
        self.v_frict = HydraulicVariable(value=None,
                                         unit="",
                                         name="v_frict",
                                         name_gui="friction velocity",
                                         dtype=np.float64)
        self.sub = HydraulicVariable(value=None,
                                     unit="",
                                     name="sub",
                                     name_gui="substrate",
                                     dtype=np.int64)

    def set_existing_attributes_list(self, name, attribute_list, position):
        getattr(self, name).existing_attributes_list = attribute_list
        getattr(self, name).position = position
        self.usefull_variable_wish_list.append(getattr(self, name))

    def get_available_variables_from_source(self, varnames):
        # get_available_variables_from_source
        for varname_index, varname in enumerate(varnames):
            for usefull_variable_wish in self.usefull_variable_wish_list:
                for wish_attribute in usefull_variable_wish.existing_attributes_list:
                    if wish_attribute in varname:
                        usefull_variable_wish.varname_index = varname_index
                        self.usefull_variable_detected_list.append(usefull_variable_wish)

        # copy
        self.final_variable_list = list(self.usefull_variable_detected_list)

        # separate node and mesh
        for usefull_variable_detected in self.usefull_variable_detected_list:
            if usefull_variable_detected.position == "node":
                self.usefull_variable_node_detected_list.append(usefull_variable_detected.name)
            elif usefull_variable_detected.position == "mesh":
                self.usefull_variable_mesh_detected_list.append(usefull_variable_detected.name)

        # computed_node_velocity or original ?
        if not self.v.name in self.usefull_variable_node_detected_list:
            self.v.computable = True
            self.v.position = "node"
        self.final_variable_list = self.final_variable_list + [self.v]  # always v

        # computed_node_shear_stress or original ?
        if not self.shear_stress.name in self.usefull_variable_node_detected_list and self.v_frict.name in self.usefull_variable_node_detected_list:
            self.shear_stress.computable = True
            self.shear_stress.position = "node"
            self.final_variable_list = self.final_variable_list + [self.shear_stress]

        self.update_final_variable_list()

    def update_final_variable_list(self):
        # separate node and mesh
        for final_variable in self.final_variable_list:
            if final_variable.position == "node":
                self.final_node_variable_name_list.append(final_variable.name)
            elif final_variable.position == "mesh":
                self.final_mesh_variable_name_list.append(final_variable.name)


class HydraulicModelInformation:
    def __init__(self):
        # models
        self.available_models_tf_list = []
        self.name_models_gui_list = []
        self.attribute_models_list = []
        self.class_gui_models_list = []
        self.class_mod_models_list = []
        self.file_mod_models_list = []
        self.website_models_list = []
        self.filename = os.path.join("model_hydro", "HydraulicModelInformation.txt")
        with open(self.filename, 'r') as f:
            data_read = f.read()
        header_list = data_read.splitlines()[0].split("\t")
        data_splited = data_read.splitlines()[1:]
        for line_index, line in enumerate(data_splited):
            line_splited = line.split("\t")
            for header_index, header_name in enumerate(header_list):
                getattr(self, header_name).append(line_splited[header_index])

        # set TF to bool
        self.available_models_tf_list = [eval(bool_str) for bool_str in self.available_models_tf_list]

    def get_attribute_name_from_class_name(self, class_name):
        if class_name in self.class_gui_models_list:
            return self.attribute_models_list[self.class_gui_models_list.index(class_name)]
        else:
            return None

    def get_class_mod_name_from_attribute_name(self, attribute_name):
        if attribute_name in self.attribute_models_list:
            return self.class_mod_models_list[self.attribute_models_list.index(attribute_name)]
        else:
            return None

    def get_file_mod_name_from_attribute_name(self, attribute_name):
        if attribute_name in self.attribute_models_list:
            return self.file_mod_models_list[self.attribute_models_list.index(attribute_name)]
        else:
            return None


class HydraulicSimulationResults:
    def __init__(self, filename, folder_path, model_type, path_prj):
        """
        :param filename_path_list: list of absolute path file, type: list of str
        :param path_prj: absolute path to project, type: str
        :param model_type: type of hydraulic model, type: str
        :param nb_dim: dimension number (1D/1.5D/2D), type: int
        :return: hydrau_description_list, type: dict
        :return: warnings list, type: list of str
        """
        # HydraulicVariableUnit
        self.hvum = HydraulicVariableUnitManagement()
        # init
        self.valid_file = True
        self.warning_list = []  # text warning output
        self.name_prj = os.path.splitext(os.path.basename(path_prj))[0]
        self.path_prj = path_prj
        self.hydrau_case = "unknown"
        self.filename = filename
        self.folder_path = folder_path
        self.filename_path = os.path.join(self.folder_path, self.filename)
        self.blob, self.ext = os.path.splitext(self.filename)

        # index_hydrau
        self.index_hydrau_file_exist = False
        if os.path.isfile(self.filename_path):
            self.index_hydrau_file_exist = True
        self.index_hydrau_file = "indexHYDRAU.txt"
        self.index_hydrau_file_path = os.path.join(self.folder_path, self.index_hydrau_file)
        # hydraulic attributes
        self.model_type = model_type
        # exist ?
        if not os.path.isfile(self.filename_path):
            self.warning_list.append("Error: The file does not exist.")
            self.valid_file = False

        # reach_num
        self.multi_reach = False
        self.reach_num = 1
        self.reach_name_list = ["unknown"]

        # timestep
        self.timestep_name_list = []
        self.timestep_nb = None
        self.timestep_unit = None
        self.timestep_name_wish_list_index = []
        self.timestep_name_wish_list = []
        self.timestep_wish_nb = None

        # coordinates
        self.unit_z_equal = False

    def get_data_2d_dict(self):
        # create empty dict
        data_2d = dict()

        # mesh
        data_2d["mesh"] = dict()

        # node
        data_2d["node"] = dict()


        for variable in self.hvum.final_variable_list:
            print(variable.position)
            # data_2d[variable.position] =
            data_2d[variable.position]["data"][variable.name] = variable.data

        # description telemac data_2d dict
        description_from_file = dict()
        description_from_file["filename_source"] = self.filename
        description_from_file["model_type"] = self.model_type
        description_from_file["model_dimension"] = str(2)
        description_from_file["unit_list"] = ", ".join(self.timestep_name_wish_list)
        description_from_file["unit_number"] = str(self.timestep_wish_nb)
        description_from_file["unit_type"] = "time [s]"
        description_from_file["unit_z_equal"] = self.unit_z_equal

        return data_2d, description_from_file


    # def get_data_2d_dict(self):
    #     # create empty dict
    #     data_2d = dict()
    #
    #     # mesh
    #     data_2d["mesh"] = dict()
    #     data_2d["mesh"]["tin"] = self.hvum.tin.data
    #     data_2d["mesh"]["data"] = dict()
    #     # node
    #     data_2d["node"] = dict()
    #     data_2d["node"]["xy"] = self.hvum.xy.data
    #     data_2d["node"]["z"] = self.hvum.z.data
    #     data_2d["node"]["data"] = dict()
    #     # variables
    #     for variable in self.hvum.final_variable_list:
    #         data_2d[variable.position]["data"][variable.name] = variable.data
    #
    #     # description telemac data_2d dict
    #     description_from_file = dict()
    #     description_from_file["filename_source"] = self.filename
    #     description_from_file["model_type"] = self.model_type
    #     description_from_file["model_dimension"] = str(2)
    #     description_from_file["unit_list"] = ", ".join(self.timestep_name_wish_list)
    #     description_from_file["unit_number"] = str(self.timestep_wish_nb)
    #     description_from_file["unit_type"] = "time [s]"
    #     description_from_file["unit_z_equal"] = self.unit_z_equal
    #
    #     return data_2d, description_from_file


