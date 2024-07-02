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
from osgeo import ogr
import triangle

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
        varnames = ["z", "h", "v"]

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
        blob, ext = os.path.splitext(self.filename)
        tin, xyz = [], []
        if "shp" in ext or "gpkg" in ext:
            tin, xyz = self.load_polygonz_from_sig()
        elif "txt" in ext:
            tin, xyz = self.load_polygonz_from_txt()

        # check if water_level values arer inside z range
        z_min = xyz[:, 2].min()
        for water_level_str  in self.timestep_name_wish_list:
            water_level_float = float(water_level_str)
            if water_level_float < z_min:
                print("Warning: water level value (" + water_level_str + ") is under minimum elevation value (" + str(z_min) + ").")

        # prepare original data for data_2d
        for reach_number in range(self.reach_number):  # for each reach
            for timestep_index in self.timestep_name_wish_list_index:  # for each timestep
                hv_value = self.compute_mesh_from_water_level(xyz[:, 2], timestep_name_wish_list[timestep_index])
                for variables_wish in self.hvum.software_detected_list:  # .varunits
                    if not variables_wish.precomputable_tohdf5:
                        if variables_wish.name == "z":
                            variables_wish.data[reach_number].append(xyz[:, 2])
                        elif variables_wish.name == "h":
                            variables_wish.data[reach_number].append(hv_value[0, :])
                        elif variables_wish.name == "v":
                            variables_wish.data[reach_number].append(hv_value[1, :])

                # struct
                self.hvum.xy.data[reach_number] = [xyz[:, (0, 1)]] * self.timestep_wish_nb
                self.hvum.tin.data[reach_number] = [np.array(tin, np.int64)] * self.timestep_wish_nb

        return self.get_data_2d()

    def load_polygonz_from_sig(self):
        blob, ext = os.path.splitext(self.filename)
        # open shape file (think about zero or one to start! )
        if "shp" in ext:
            driver = ogr.GetDriverByName('ESRI Shapefile')
        elif "gpkg" in ext:
            driver = ogr.GetDriverByName('GPKG')
        else:
            print("Error: Extension file not recognized :", ext)
            return False

        ds = driver.Open(self.filename_path, 0)  # 0 means read-only. 1 means writeable.

        layer_num = 0
        layer = ds.GetLayer(layer_num)
        xyz = []  # point
        tin = []  # connectivity table
        for feature_ind, feature in enumerate(layer):
            # progress_value.value = progress_value.value + delta_poly
            shape_geom = feature.geometry()
            shape_geom.SetCoordinateDimension(3)  # never z values
            geom_part = shape_geom.GetGeometryRef(0)  # only one if triangular mesh
            p_all = geom_part.GetPoints()
            tin_i = []
            for j in range(0, len(p_all) - 1):  # last point of shapefile is the first point
                try:
                    tin_i.append(int(xyz.index(p_all[j])))
                except ValueError:
                    tin_i.append(int(len(xyz)))
                    xyz.append(p_all[j])
            tin.append(tin_i)
        xyz = np.array(xyz)
        tin = np.array(tin)

        return tin, xyz

    def load_polygonz_from_txt(self):
        try:
            xyz_raw = np.genfromtxt(self.filename_path,
                                    delimiter='\t',
                                    dtype=np.float64,
                                    skip_header=True,
                                    encoding="utf-8",
                                    autostrip=True)
        except:
            print("Error: xyz file reading crash.")
            return False

        polygon_from_shp = dict(vertices=xyz_raw[:, (0, 1)])
        polygon_triangle = triangle.triangulate(polygon_from_shp)
        return polygon_triangle["triangles"], xyz_raw

    def compute_mesh_from_water_level(self, z, water_level_value):
        try:
            water_level_float = float(water_level_value)
        except SyntaxError:
            print("Error: Water level floating conversion not possible :", water_level_value)
            return False

        h_data = water_level_float - z
        v_data = [0.0] * len(z)

        hv_data = np.array([h_data, v_data], np.float64)

        return hv_data

