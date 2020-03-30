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


class HydraulicModelInformation:
    def __init__(self):
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

        # init
        self.timestep_name_list = None
        self.timestep_nb = None
        self.timestep_unit = None

        self.unit_z_equal = True

        self.reach_name_list = []

