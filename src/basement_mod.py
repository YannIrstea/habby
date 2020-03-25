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
        HydraulicSimulationResults.__init__(self, filename, folder_path, model_type, path_prj)
        # file attributes
        self.extensions_list = [".h5"]
        self.file_type = "hdf5"
        self.valid_file = True
        # simulation attributes
        self.equation_type = ["FV"]
        self.morphology_available = True

        # init
        self.timestep_name_list = None
        self.timestep_nb = None
        self.timestep_unit = None

        # readable file ?
        try:
            self.results_data_file = h5py.File(self.filename_path, 'r')
        except OSError:
            self.warning_list.append("Error: The file can not be opened.")
            self.valid_file = False

        # result_file ?
        if not "RESULTS" in self.results_data_file.keys():
            self.warning_list.append('Error: The file is not BASEMENT results type.')
            self.valid_file = False

        # is extension .h5 ?
        if os.path.splitext(self.filename)[1] not in self.extensions_list:
            self.warning_list.append("Error: The extension of file is not '.h5'.")
            self.valid_file = False

        # if valid get informations
        if self.valid_file:
            # get_time_step ?
            self.get_time_step()

    def get_time_step(self):
        """
        A function which load the telemac time step using the Selafin class.

        :param namefilet: the name of the selafin file (string)
        :param pathfilet: the path to this file (string)
        :return: timestep
        """
        simulation_dict = eval(self.results_data_file[".config"]["simulation"][:].tolist()[0])

        hydraulic_variables = simulation_dict["SIMULATION"]["OUTPUT"]
        timestep_float_list = list(frange(simulation_dict["SIMULATION"]["TIME"]["start"],
                               simulation_dict["SIMULATION"]["TIME"]["end"],
                               simulation_dict["SIMULATION"]["TIME"]["out"]))
        self.timestep_name_list = list(map(str, timestep_float_list))
        self.timestep_nb = len(timestep_float_list)
        self.timestep_unit = "time [s]"

    def load_hydraulic(self):
        """
        A function which load the telemac data using the Selafin class.

        :param namefilet: the name of the selafin file (string)
        :param pathfilet: the path to this file (string)
        :return: the velocity, the height, the coordinate of the points of the grid, the connectivity table.
        """
        # init
        unit_z_equal = True

        # simulation dict
        model_dict = eval(self.results_data_file[".config"]["model"][:].tolist()[0])["SETUP"]
        if "MORPHOLOGY" in model_dict["DOMAIN"]["BASEPLANE_2D"].keys():
            unit_z_equal = False

        # simulation dict
        simulation_dict = eval(self.results_data_file[".config"]["simulation"][:].tolist()[0])["SIMULATION"]
        # variables_available = simulation_dict["OUTPUT"]  # hydraulic_variables
        timestep_float_list = list(frange(simulation_dict["TIME"]["start"],
                               simulation_dict["TIME"]["end"],
                               simulation_dict["TIME"]["out"]))  # timestep_float_list
        nbtimes = len(timestep_float_list)  # nbtimes

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
        if unit_z_equal:
            try:
                mesh_z = CellAll_group["BottomEl"][:].flatten()
            except KeyError:
                print("Error: Can't found 'BottomEl' key in " + self.filename + ".")
        if not unit_z_equal:
            mesh_z = np.zeros((mesh_nb, nbtimes), dtype=np.float64)
            dataset_name_list = list(RESULTS_group["CellsAll"]["BottomEl"])
            try:
                for timestep_num in range(nbtimes):
                    mesh_z[:, timestep_num] = RESULTS_group["CellsAll"]["BottomEl"][dataset_name_list[timestep_num]][:].flatten()
            except KeyError:
                print("Error: Can't found 'BottomEl' key in " + self.filename + ".")
        # result data
        mesh_h = np.zeros((mesh_nb, nbtimes), dtype=np.float64)
        mesh_v = np.zeros((mesh_nb, nbtimes), dtype=np.float64)
        dataset_name_list = list(RESULTS_group["CellsAll"]["HydState"])
        for timestep_num in range(nbtimes):
            result_hyd_array = RESULTS_group["CellsAll"]["HydState"][dataset_name_list[timestep_num]][:]
            # zeau
            mesh_water_level = result_hyd_array[:, 0]
            # h
            if unit_z_equal:
                mesh_water_height = mesh_water_level - mesh_z
            if not unit_z_equal:
                mesh_water_height = mesh_water_level - mesh_z[:, timestep_num]
            # q_x
            mesh_q_x = result_hyd_array[:, 1]
            # q_y
            mesh_q_y = result_hyd_array[:, 2]
            # v (mesh_water_height, mesh_q_x, mesh_q_y can have 0.0 values (invalid value encountered in true_divide))
            with np.errstate(invalid='ignore'):
                mesh_velocity = np.sqrt((mesh_q_x / mesh_water_height) ** 2 + (mesh_q_y / mesh_water_height) ** 2)
            mesh_velocity[mesh_water_height == 0] = 0
            # append
            mesh_h[:, timestep_num] = mesh_water_height
            mesh_v[:, timestep_num] = mesh_velocity

        # finite_volume_to_finite_element_triangularxy
        mesh_tin = np.column_stack([mesh_tin, np.ones(len(mesh_tin), dtype=mesh_tin[0].dtype) * -1])  # add -1 column
        mesh_tin, node_xyz, node_h, node_v = manage_grid_mod.finite_volume_to_finite_element_triangularxy(mesh_tin,
                                                                                                          node_xyz,
                                                                                                          mesh_h,
                                                                                                          mesh_v)

        # return to list
        node_h_list = []
        node_v_list = []
        for unit_num in range(nbtimes):
            node_h_list.append(node_h[:, unit_num])
            node_v_list.append(node_v[:, unit_num])

        # description telemac data dict
        description_from_file = dict()
        description_from_file["filename_source"] = self.filename
        description_from_file["model_type"] = "BASEMENT2D"
        description_from_file["model_dimension"] = str(2)
        description_from_file["unit_list"] = ", ".join(list(map(str, timestep_float_list)))
        description_from_file["unit_number"] = str(nbtimes)
        description_from_file["unit_type"] = "time [s]"
        description_from_file["unit_z_equal"] = True

        # data 2d dict (one reach by file and varying_mesh==False)
        data_2d = create_empty_data_2d_dict(reach_number=1,
                                            node_variables=["h", "v"])
        data_2d["mesh"]["tin"][0] = mesh_tin
        data_2d["node"]["xy"][0] = node_xy
        data_2d["node"]["z"][0] = node_z
        data_2d["node"]["data"]["h"][0] = node_h_list
        data_2d["node"]["data"]["v"][0] = node_v_list
        #     return v, h, coord_p, ikle, coord_c, timestep
        return data_2d, description_from_file

