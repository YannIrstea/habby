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
import pandas as pd

from src.hydraulic_results_manager_mod import HydraulicSimulationResultsBase
from src.dev_tools_mod import frange
from src.variable_unit_mod import HydraulicVariableUnitManagement
from src import manage_grid_mod


class HydraulicSimulationResults(HydraulicSimulationResultsBase):
    """Represent Basement hydraulic simulation results.

    Keyword arguments:
    filename -- filename, type: str
    folder_path -- relative path to filename, type: str
    model_type -- type of hydraulic model, type: str
    path_prj -- absolute path to project, type: str
    """
    def __init__(self, filename, folder_path, model_type, path_prj):
        super().__init__(filename, folder_path, model_type, path_prj)
        # HydraulicVariableUnit
        self.hvum = HydraulicVariableUnitManagement()
        # file attributes
        self.extensions_list = [".h5"]
        self.file_type = "hdf5"
        # simulation attributes
        self.hyd_equation_type = "FV"
        self.morphology_available = True
        self.second_file_suffix = "_aux"
        # reach
        self.multi_reach = False # ?
        self.reach_number = 1
        self.reach_name_list = ["unknown"]
        # simulation info
        self.simulation_name = "unknown"
        # hydraulic variables
        self.hvum.link_unit_with_software_attribute(name=self.hvum.z.name,
                                                    attribute_list=["Coordnts"],
                                                    position="node")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.z.name,
                                                    attribute_list=["BottomEl"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.h.name,
                                                    attribute_list=["always h"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.v.name,
                                                    attribute_list=["always v"],
                                                    position="mesh")
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

        if self.results_data_file:
            if not "RESULTS" in self.results_data_file.keys():
                self.warning_list.append('Error: The file is not ' + self.model_type + ' results type.')
                self.valid_file = False

        # is extension ok ?
        if os.path.splitext(self.filename)[1] not in self.extensions_list:
            self.warning_list.append("Error: The extension of file is not : " + ", ".join(self.extensions_list) + ".")
            self.valid_file = False

        # if valid get informations
        if self.valid_file:
            # get_simulation_info
            self.get_simulation_info()
            # get_time_step ?
            self.get_time_step()
            # get hydraulic variables list (mesh and node)
            self.get_hydraulic_variable_list()
        else:
            self.warning_list.append("Error: File not valid.")

    def get_simulation_info(self):
        """Get simulation informations from file."""
        self.simulation_name = eval(self.results_data_file[".config"]["model"][:].tolist()[0])["SETUP"]["simulation_name"]

    def get_hydraulic_variable_list(self):
        """Get hydraulic variable list from file."""
        # #hydraulic_variables = eval(self.results_data_file[".config"]["simulation"][:].tolist()[0])["SIMULATION"]["OUTPUT"]

        # get list from source
        varnames = ["Coordnts", "BottomEl", "always h", "always v"]

        # check witch variable is available
        self.hvum.detect_variable_from_software_attribute(varnames)

    def get_time_step(self):
        """Get time step information from file."""

        simulation_dict = eval(self.results_data_file[".config"]["simulation"][:].tolist()[0])

        timestep_float_list = list(frange(simulation_dict["SIMULATION"]["TIME"]["start"],
                               simulation_dict["SIMULATION"]["TIME"]["end"],
                               simulation_dict["SIMULATION"]["TIME"]["out"]))
        self.timestep_name_list = list(map(str, timestep_float_list))
        self.timestep_nb = len(self.timestep_name_list)
        self.timestep_unit = "time [s]"

    def load_hydraulic(self, timestep_name_wish_list):
        """Retrun Data2d from file.

        Keyword arguments:
        timestep_name_wish_list -- list of targeted timestep to be load, type: list of str
        """

        # load specific timestep
        self.load_specific_timestep(timestep_name_wish_list)

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
            mesh_z = np.zeros((mesh_nb, self.timestep_wish_nb), dtype=np.float64)
            dataset_name_list = list(RESULTS_group["CellsAll"]["BottomEl"])
            try:
                for timestep_index, timestep_num in enumerate(self.timestep_name_wish_list_index):
                    mesh_z[:, timestep_index] = RESULTS_group["CellsAll"]["BottomEl"][dataset_name_list[timestep_num]][:].flatten()
            except KeyError:
                print("Error: Can't found 'BottomEl' key in " + self.filename + ".")
        # result data
        mesh_h = np.zeros((mesh_nb, self.timestep_wish_nb), dtype=np.float64)
        mesh_v = np.zeros((mesh_nb, self.timestep_wish_nb), dtype=np.float64)
        data_mesh_pd = pd.DataFrame()
        dataset_name_list = list(RESULTS_group["CellsAll"]["HydState"])
        for timestep_index, timestep_num in enumerate(self.timestep_name_wish_list_index):
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

        # transform data to pandas
        data_mesh_pd_r_list = []
        for reach_number in range(len(self.reach_name_list)):
            data_mesh_pd_t_list = []
            for timestep_name_wish_index in range(self.timestep_wish_nb):
                data_mesh_pd = pd.DataFrame()
                data_mesh_pd[self.hvum.h.name] = mesh_h[:, timestep_name_wish_index]
                data_mesh_pd[self.hvum.v.name] = mesh_v[:, timestep_name_wish_index]
                data_mesh_pd_t_list.append(data_mesh_pd)
            data_mesh_pd_r_list.append(data_mesh_pd_t_list)

        # finite_volume_to_finite_element_triangularxy
        mesh_tin = np.column_stack([mesh_tin, np.ones(len(mesh_tin), dtype=mesh_tin[0].dtype) * -1])  # add -1 column
        mesh_tin, node_xyz, node_h, data_node_list = manage_grid_mod.finite_volume_to_finite_element_triangularxy(mesh_tin,
                                                                                                          node_xyz,
                                                                                                          mesh_h,
                                                                                                          data_mesh_pd_r_list[0])

        # prepare original and computed data for data_2d
        for reach_number in range(self.reach_number):  # for each reach
            for timestep_index in range(self.timestep_wish_nb):  # for each timestep
                for variables_wish in self.hvum.hdf5_and_computable_list:  # .varunits
                    if variables_wish.position == "mesh":
                        if variables_wish.name == self.hvum.z.name:
                            if self.unit_z_equal:
                                variables_wish.data[reach_number].append(mesh_z.astype(variables_wish.dtype))
                            else:
                                variables_wish.data[reach_number].append(mesh_z[:, timestep_index].astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.h.name:
                            variables_wish.data[reach_number].append(mesh_h[:, timestep_index].astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.v.name:
                            variables_wish.data[reach_number].append(mesh_v[:, timestep_index].astype(variables_wish.dtype))
                    if variables_wish.position == "node":
                        if variables_wish.name == self.hvum.z.name:
                            variables_wish.data[reach_number].append(node_z.astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.h.name:
                            variables_wish.data[reach_number].append(node_h[:, timestep_index].astype(variables_wish.dtype))
                        else:
                            var_node_index = data_mesh_pd_r_list[0][0].columns.values.tolist().index(variables_wish.name)
                            variables_wish.data[reach_number].append(data_node_list[timestep_index][:, var_node_index].astype(variables_wish.dtype))

            # coord
            self.hvum.xy.data[reach_number] = [node_xy] * self.timestep_wish_nb
            self.hvum.tin.data[reach_number] = [mesh_tin] * self.timestep_wish_nb

        del self.results_data_file

        return self.get_data_2d()


