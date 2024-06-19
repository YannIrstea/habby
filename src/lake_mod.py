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
        self.file_type = "ascii"
        self.hvum.link_unit_with_software_attribute(name=self.hvum.z.name,
                                                    attribute_list=["z"],
                                                    position="node")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.h.name,
                                                    attribute_list=["h"],
                                                    position="node")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.v.name,
                                                    attribute_list=["v"],
                                                    position="node")
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
        self.get_hydraulic_variable_list()
        self.get_time_step()

    def get_hydraulic_variable_list(self):
        """Get hydraulic variable list from file."""
        # get list from source
        varnames = ["z", "h"]

        # check witch variable is available
        self.hvum.detect_variable_from_software_attribute(varnames)

    def get_time_step(self):
        """Get time step information from file."""

        with open(self.index_hydrau_file_path, 'rt', encoding="utf-8") as f:
            # read text file
            dataraw = f.read()
            # get epsg code
            if "EPSG=" not in dataraw.split("\n")[0]:
                self.hydrau_description_list = "Error: indexHYDRAU.txt file is not well formated. 'EPSG=' not found"
                return
            epsg_code = dataraw.split("\n")[0].split("EPSG=")[1].strip()
            # read headers and nb row
            headers = dataraw.split("\n")[1].split()
            nb_row = len(dataraw.split("\n"))
            # create one dict for all column
            data_index_file = dict((key, []) for key in headers)
            data_row_list = dataraw.split("\n")[2:]
            try:
                for line in data_row_list:
                    if line == "":
                        # print("empty line")
                        pass
                    else:
                        for index, column_name in enumerate(headers):
                            # "\t" is the column separator
                            # (if split without arg, date with time is also splitted for hec ras 2D)
                            data_index_file[column_name].append(line.split("\t")[index])
            except IndexError:
                self.hydrau_description_list = "Error: indexHYDRAU.txt file is not well formated. Column separator is a tabulation."
                return

        timestep_float_list = data_index_file[column_name]

        self.timestep_name_list = list(map(str, timestep_float_list))  # always one reach
        self.timestep_nb = len(self.timestep_name_list)
        self.timestep_unit = "water_level [m]"

    def load_hydraulic(self, timestep_name_wish_list):
        """
        :param filename: the name of the text file
        :param path_prj:
        :return: data_2d, data_description two dictionnary with elements for writing hdf5 datasets and attribute
        """
        self.load_specific_timestep(timestep_name_wish_list)

        return self.get_data_2d()

