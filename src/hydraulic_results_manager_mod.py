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
import importlib
import os
import pandas as pd
import sys
import numpy as np
# import trimesh
# from mayavi import mlab

from src.data_2d_mod import Data2d
from src.variable_unit_mod import HydraulicVariableUnitManagement


class HydraulicModelInformation:
    def __init__(self):
        """
        Hydraulic software informations
        """
        # models
        self.available_models_tf_list = []
        self.name_models_gui_list = []
        self.attribute_models_list = []
        self.class_gui_models_list = []
        self.class_mod_models_list = []
        self.file_mod_models_list = []
        self.website_models_list = []
        self.dimensions = []
        self.extensions = []
        self.filename = os.path.join("model_hydro", "HydraulicModelInformation.txt")
        with open(self.filename, 'r') as f:
            data_read = f.read()
        header_list = data_read.splitlines()[0].split("\t")
        data_splited = data_read.splitlines()[1:]
        for line_index, line in enumerate(data_splited):
            line_splited = line.split("\t")
            for header_index, header_name in enumerate(header_list):
                getattr(self, header_name).append(line_splited[header_index])

        # convert to bool
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


class HydraulicSimulationResultsSelector:
    def __new__(self, filename, folder_path, model_type, path_prj):
        hydraulic_model_information = HydraulicModelInformation()
        filename_mod = hydraulic_model_information.get_file_mod_name_from_attribute_name(model_type)

        # Contrived example of generating a module named as a string
        full_module_name = "src." + filename_mod

        # The file gets executed upon import, as expected.
        mymodule = importlib.import_module(full_module_name)

        return mymodule.HydraulicSimulationResults(filename, folder_path, model_type, path_prj)


class HydraulicSimulationResultsBase:
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
        self.equation_type = "unknown"
        # exist ?
        if not os.path.isfile(self.filename_path) and os.path.splitext(self.filename_path)[1]:
            self.warning_list.append("Error: The file does not exist.")
            self.valid_file = False

        self.results_data_file = None

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

    def load_specific_timestep(self, timestep_name_wish_list):
        self.timestep_name_wish_list = timestep_name_wish_list
        for time_step_name_wish in timestep_name_wish_list:
            if time_step_name_wish not in self.timestep_name_list:
                print("Error: timestep " + time_step_name_wish + " not found in " + self.filename +
                      ". Change it in indexHYDRAU.txt and retry.")
            else:
                self.timestep_name_wish_list_index.append(self.timestep_name_list.index(time_step_name_wish))
        self.timestep_name_wish_list_index.sort()
        self.timestep_wish_nb = len(self.timestep_name_wish_list_index)

    def get_data_2d(self):
        # create empty list
        data_2d = Data2d(reach_num=len(self.reach_name_list),
                         unit_num=len(self.timestep_name_wish_list))
        data_2d.equation_type = self.equation_type
        data_2d.hvum = self.hvum
        self.hvum.hdf5_and_computable_list.sort_by_names_gui()
        node_list = self.hvum.hdf5_and_computable_list.nodes()
        mesh_list = self.hvum.hdf5_and_computable_list.meshs()

        for reach_num in range(len(self.reach_name_list)):

            for unit_num in range(len(self.timestep_name_wish_list)):
                # node
                data_2d[reach_num][unit_num]["node"][self.hvum.xy.name] = self.hvum.xy.data[reach_num][unit_num]
                data_2d[reach_num][unit_num]["node"]["data"] = pd.DataFrame()
                for node_variable in node_list:
                    try:
                        data_2d[reach_num][unit_num]["node"]["data"][node_variable.name] = node_variable.data[reach_num][unit_num]
                    except IndexError:
                        print("Error: node data not found : " + node_variable.name + " in get_data_2d.")

                # mesh
                data_2d[reach_num][unit_num]["mesh"][self.hvum.tin.name] = self.hvum.tin.data[reach_num][unit_num]
                data_2d[reach_num][unit_num]["mesh"][self.hvum.i_whole_profile.name] = np.column_stack([
                                    np.arange(0, self.hvum.tin.data[reach_num][unit_num].shape[0], dtype=self.hvum.i_whole_profile.dtype),
                                    np.repeat(0, self.hvum.tin.data[reach_num][unit_num].shape[0]).astype(self.hvum.i_split.dtype)])
                data_2d[reach_num][unit_num]["mesh"]["data"] = pd.DataFrame()
                # i_split
                data_2d[reach_num][unit_num]["mesh"]["data"][self.hvum.i_split.name] = data_2d[reach_num][unit_num]["mesh"]["i_whole_profile"][:, 1]
                for mesh_variable in mesh_list:
                    try:
                        data_2d[reach_num][unit_num]["mesh"]["data"][mesh_variable.name] = mesh_variable.data[reach_num][unit_num]
                    except IndexError:
                        print("Error: mesh data not found : " + mesh_variable.name + " in get_data_2d.")

        # i_split
        self.hvum.i_split.position = "mesh"
        self.hvum.i_split.hdf5 = True
        self.hvum.hdf5_and_computable_list.append(self.hvum.i_split)

        # description telemac data_2d dict
        description_from_file = dict()
        description_from_file["filename_source"] = self.filename
        description_from_file["model_type"] = self.model_type
        description_from_file["model_dimension"] = str(2)
        description_from_file["unit_list"] = str(self.timestep_name_wish_list)
        description_from_file["unit_number"] = str(self.timestep_wish_nb)
        description_from_file["unit_type"] = "time [s]"
        description_from_file["unit_z_equal"] = self.unit_z_equal
        description_from_file["variables"] = dict()

        return data_2d, description_from_file

