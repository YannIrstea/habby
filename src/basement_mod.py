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
import h5py

from src.hydraulic_bases import HydraulicSimulationResults
from src.tools_mod import create_empty_data_2d_dict, frange
from src import manage_grid_mod


class BasementResult(HydraulicSimulationResults):
    """
    """
    def __init__(self, filename, folder_path, model_type, path_prj):
        super().__init__(filename, folder_path, model_type, path_prj)
        # file attributes
        self.extensions_list = [".h5"]
        self.file_type = "hdf5"
        # simulation attributes
        self.equation_type = ["FV"]
        self.morphology_available = True
        self.second_file_suffix = "_aux"

        # readable file ?
        try:
            self.results_data_file = h5py.File(self.filename_path, 'r')
        except OSError:
            self.warning_list.append("Error: The file can not be opened.")
            self.valid_file = False

        # # check second file
        # if self.second_file_suffix in self.filename:
        #     self.filename_aux = self.filename
        # else:
        #     self.filename_aux = os.path.splitext(self.filename)[0] + self.second_file_suffix + os.path.splitext(self.filename)[1]
        #     self.filename_path_aux = os.path.join(self.folder_path, self.filename_aux)
        #     # exist ?
        #     if not os.path.isfile(self.filename_path_aux):
        #         self.warning_list.append("Error: The second file '" + self.filename_aux + "' not exist. Please create it exporting result with Basement software.")
        #         self.valid_file = False
        #     else:
        #         # second readable file ?
        #         try:
        #             self.results_data_file2 = h5py.File(self.filename_path, 'r')
        #         except OSError:
        #             self.warning_list.append("Error: The file can not be opened.")
        #         self.valid_file = False
        #
        #         # second result_file ?
        #         if not "RESULTS" in self.results_data_file.keys():
        #             self.warning_list.append('Error: The file is not ' + self.model_type + ' results type.')
        #             self.valid_file = False

        # first result_file ?
        if not "RESULTS" in self.results_data_file.keys():
            self.warning_list.append('Error: The file is not ' + self.model_type + ' results type.')
            self.valid_file = False

        # is extension ok ?
        if os.path.splitext(self.filename)[1] not in self.extensions_list:
            self.warning_list.append("Error: The extension of file is not : " + ", ".join(self.extensions_list) + ".")
            self.valid_file = False

        # if valid get informations
        if self.valid_file:
            # get_time_step ?
            self.get_time_step()
        else:
            self.warning_list.append("Error: File not valid.")

    def get_hydraulic_variable_list(self):
        #hydraulic_variables = eval(self.results_data_file[".config"]["simulation"][:].tolist()[0])["SIMULATION"]["OUTPUT"]
        self.hydraulic_variables_node_list = []
        self.hydraulic_variables_mesh_list = ["h", "v"]

    def get_time_step(self):
        """
        A function which load the telemac time step using the Selafin class.

        :param namefilet: the name of the selafin file (string)
        :param pathfilet: the path to this file (string)
        :return: timestep
        """
        simulation_dict = eval(self.results_data_file[".config"]["simulation"][:].tolist()[0])

        timestep_float_list = list(frange(simulation_dict["SIMULATION"]["TIME"]["start"],
                               simulation_dict["SIMULATION"]["TIME"]["end"],
                               simulation_dict["SIMULATION"]["TIME"]["out"]))
        self.timestep_name_list = list(map(str, timestep_float_list))
        self.timestep_nb = len(timestep_float_list)
        self.timestep_unit = "time [s]"

    def load_hydraulic(self, timestep_name_wish_list):
        """
        A function which load the telemac data using the Selafin class.

        :param namefilet: the name of the selafin file (string)
        :param pathfilet: the path to this file (string)
        :return: the velocity, the height, the coordinate of the points of the grid, the connectivity table.
        """
        # load specific timestep
        timestep_name_wish_list_index = []
        for time_step_name_wish in timestep_name_wish_list:
            timestep_name_wish_list_index.append(self.timestep_name_list.index(time_step_name_wish))
        timestep_name_wish_list_index.sort()
        timestep_wish_nb = len(timestep_name_wish_list_index)

        # simulation dict
        model_dict = eval(self.results_data_file[".config"]["model"][:].tolist()[0])["SETUP"]
        if "MORPHOLOGY" in model_dict["DOMAIN"]["BASEPLANE_2D"].keys():
            self.unit_z_equal = False
        else:
            self.unit_z_equal = True

        # get group
        CellAll_group = self.results_data_file["CellsAll"]  # CellAll_group
        NodesAll_group = self.results_data_file["NodesAll"]  # NodesAll_group
        RESULTS_group = self.results_data_file["RESULTS"]  # CellAll_group

        """ get node data """
        # total
        node_nb = NodesAll_group["set"][:][0]
        # xyz
        node_xyz = NodesAll_group["Coordnts"][:]
        # xy
        node_xy = node_xyz[:, (0, 1)]
        # z
        node_z = node_xyz[:, 2]
        if node_z.min() == 0 and node_z.max() == 0:
            print("Warning: All elevation nodes data are aqual to 0.")

        """ get mesh data """
        # total
        mesh_nb = CellAll_group["set"][:][0]
        # tin
        mesh_tin = CellAll_group["Topology"][:].astype(np.int64)
        # z
        if self.unit_z_equal:
            try:
                mesh_z = CellAll_group["BottomEl"][:].flatten()
            except KeyError:
                print("Error: Can't found 'BottomEl' key in " + self.filename + ".")
        if not self.unit_z_equal:
            mesh_z = np.zeros((mesh_nb, timestep_wish_nb), dtype=np.float64)
            dataset_name_list = list(RESULTS_group["CellsAll"]["BottomEl"])
            try:
                for timestep_index, timestep_num in enumerate(timestep_name_wish_list_index):
                    mesh_z[:, timestep_index] = RESULTS_group["CellsAll"]["BottomEl"][dataset_name_list[timestep_num]][:].flatten()
            except KeyError:
                print("Error: Can't found 'BottomEl' key in " + self.filename + ".")
        # result data
        mesh_h = np.zeros((mesh_nb, timestep_wish_nb), dtype=np.float64)
        mesh_v = np.zeros((mesh_nb, timestep_wish_nb), dtype=np.float64)
        dataset_name_list = list(RESULTS_group["CellsAll"]["HydState"])
        for timestep_index, timestep_num in enumerate(timestep_name_wish_list_index):
            result_hyd_array = RESULTS_group["CellsAll"]["HydState"][dataset_name_list[timestep_num]][:]
            # zeau
            mesh_water_level = result_hyd_array[:, 0]
            # h
            if self.unit_z_equal:
                mesh_water_height = mesh_water_level - mesh_z
            else:
                mesh_water_height = mesh_water_level - mesh_z[:, timestep_index]
            # q_x
            mesh_q_x = result_hyd_array[:, 1]
            # q_y
            mesh_q_y = result_hyd_array[:, 2]
            # v (mesh_water_height, mesh_q_x, mesh_q_y can have 0.0 values (invalid value encountered in true_divide))
            with np.errstate(invalid='ignore'):
                mesh_velocity = np.sqrt((mesh_q_x / mesh_water_height) ** 2 + (mesh_q_y / mesh_water_height) ** 2)
            mesh_velocity[mesh_water_height == 0] = 0
            # append
            mesh_h[:, timestep_index] = mesh_water_height
            mesh_v[:, timestep_index] = mesh_velocity

        # finite_volume_to_finite_element_triangularxy
        mesh_tin = np.column_stack([mesh_tin, np.ones(len(mesh_tin), dtype=mesh_tin[0].dtype) * -1])  # add -1 column
        mesh_tin, node_xyz, node_h, node_v = manage_grid_mod.finite_volume_to_finite_element_triangularxy(mesh_tin,
                                                                                                          node_xyz,
                                                                                                          mesh_h,
                                                                                                          mesh_v)

        # return to list
        node_h_list = []
        node_v_list = []
        for unit_num in range(timestep_wish_nb):
            node_h_list.append(node_h[:, unit_num])
            node_v_list.append(node_v[:, unit_num])

        # description data dict
        description_from_file = dict()
        description_from_file["filename_source"] = self.filename
        description_from_file["model_type"] = self.model_type
        description_from_file["model_dimension"] = str(2)
        description_from_file["unit_list"] = ", ".join(list(map(str, timestep_name_wish_list_index)))
        description_from_file["unit_number"] = str(timestep_wish_nb)
        description_from_file["unit_type"] = "time [s]"
        description_from_file["unit_z_equal"] = self.unit_z_equal

        # data 2d dict (one reach by file and varying_mesh==False)
        data_2d = create_empty_data_2d_dict(reach_number=1,
                                            node_variables=["h", "v"])
        data_2d["mesh"]["tin"][0] = [mesh_tin] * timestep_wish_nb
        data_2d["node"]["xy"][0] = [node_xy] * timestep_wish_nb
        if self.unit_z_equal:
            data_2d["node"]["z"][0] = [node_z] * timestep_wish_nb
        else:
            data_2d["node"]["z"][0] = node_z
        data_2d["node"]["data"]["h"][0] = node_h_list
        data_2d["node"]["data"]["v"][0] = node_v_list

        del self.results_data_file

        return data_2d, description_from_file

