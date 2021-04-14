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
        """
        Hydraulic software informations
        """
        # models
        self.filename = os.path.join("model_hydro", "HydraulicModelInformation.txt")
        with open(self.filename, 'r') as f:
            data_read = f.read()
        header_list = data_read.splitlines()[0].split("\t")
        data_splited = data_read.splitlines()[1:]
        # init_list
        for header_index, header_name in enumerate(header_list):
            setattr(self, header_name, [])
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

    def get_attribute_name_from_name_models_gui(self, name_gui):
        if name_gui in self.name_models_gui_list:
            return self.attribute_models_list[self.name_models_gui_list.index(name_gui)]
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