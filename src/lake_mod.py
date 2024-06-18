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

import src.manage_grid_mod
from src import manage_grid_mod
from src.dev_tools_mod import isstranumber
from src.hydraulic_results_manager_mod import HydraulicSimulationResultsBase
from src.user_preferences_mod import user_preferences


class HydraulicSimulationResults(HydraulicSimulationResultsBase):
    """Represent Lake hydraulic data.

    Keyword arguments:
    filename -- filename, type: str
    folder_path -- relative path to filename, type: str
    model_type -- type of hydraulic model, type: str
    path_prj -- absolute path to project, type: str
    """
    def __init__(self, filename, folder_path, model_type, path_prj):
        super().__init__(filename, folder_path, model_type, path_prj)
        self.file_type = "lake"

        # is extension ok ?
        if os.path.splitext(self.filename)[1] not in self.extensions_list:
            self.warning_list.append("Error: The extension of file is not : " + ", ".join(self.extensions_list) + ".")
            self.valid_file = False

        # if valid get informations
        if self.valid_file:
            self.get_lake_model_description()
        else:
            self.warning_list.append("Error: Lake file not valid.")

    def get_lake_model_description(self):
        """
        using a text file description of hydraulic outputs from a 2 D model (with or without substrate description)
        several reaches and units (discharges or times )descriptions are allowed

        WARNING this function is parallel with  load_ascii_model function and some integrity tests are similar
        :param file_path:
        :return: the reachname list and the unit description (times or discharges)
        """
        print("get_lake_model_description")

    def load_hydraulic(self, timestep_name_wish_list):
        """
        :param filename: the name of the text file
        :param path_prj:
        :return: data_2d, data_description two dictionnary with elements for writing hdf5 datasets and attribute
        """
        self.load_specific_timestep(timestep_name_wish_list)

        return self.get_data_2d()

