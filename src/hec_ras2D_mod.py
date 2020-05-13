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
import h5py
import os
import numpy as np
import matplotlib.pyplot as plt
import time
from scipy.interpolate import griddata
import pandas as pd

from src import manage_grid_mod
from src.hydraulic_results_manager_mod import HydraulicSimulationResultsBase


class HydraulicSimulationResults(HydraulicSimulationResultsBase):
    """
    """
    def __init__(self, filename, folder_path, model_type, path_prj):
        super().__init__(filename, folder_path, model_type, path_prj)
        # file attributes
        self.extensions_list = [".hdf", ".h5"]
        self.file_type = "hdf5"
        # simulation attributes
        self.equation_type = ["FV"]
        self.morphology_available = True  # TODO ?
        # hydraulic variables
        self.hvum.link_unit_with_software_attribute(name=self.hvum.z.name,
                                                    attribute_list=["Cells Minimum Elevation"],
                                                    position="mesh")  # after FV to FE conversion
        self.hvum.link_unit_with_software_attribute(name=self.hvum.h.name,
                                                    attribute_list=["Depth"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.v.name,
                                                    attribute_list=["Face Velocity"],
                                                    position="mesh")  # after face to mesh conversion
        self.hvum.link_unit_with_software_attribute(name=self.hvum.shear_stress.name,
                                                    attribute_list=["Face Shear Stress"],
                                                    position="mesh")  # after face to mesh conversion

        # readable file ?
        try:
            self.results_data_file = h5py.File(self.filename_path, 'r')
        except OSError:
            self.warning_list.append("Error: The file can not be opened.")
            self.valid_file = False

        # result_file ?
        if not "Results" in self.results_data_file.keys():
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
            # get_reach_names ?
            self.get_reach_names()
            # get_hydraulic_variable_list ?
            self.get_hydraulic_variable_list()
        else:
            self.warning_list.append("Error: File not valid.")

    def get_hydraulic_variable_list(self):
        # result_path
        self.results_path = "/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/"
        # get variables from first reach
        varnames = []
        for dataset_name in self.results_data_file[self.results_path][self.reach_name_list[0]].keys():
            # get list from source
            varnames.append(dataset_name)

        # add z
        varnames = varnames + [self.hvum.z.software_attributes_list[0]]

        # check witch variable is available
        self.hvum.detect_variable_from_software_attribute(varnames)

    def get_time_step(self):
        """
        """
        timestep_path = "/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time Date Stamp"
        self.timestep_name_list = [t.decode('utf-8') for idx, t in enumerate(list(self.results_data_file[timestep_path]))]
        self.timestep_nb = len(self.timestep_name_list)
        self.timestep_unit = "Date [d/m/Y h:m:s]"

    def get_reach_names(self):
        """
        """
        # Old version of HEC-RAS2D ?
        try:
            self.reach_name_list = self.results_data_file["Geometry/2D Flow Areas"]["Names"][:].astype(str).tolist()
        except KeyError:
            # New version of HEC-RAS2D ?
            try:
                self.reach_name_list = self.results_data_file["Geometry/2D Flow Areas"]["Attributes"]["Name"].astype(str).tolist()
            except KeyError:
                print('Error: Reach names not found.')
        self.reach_num = len(self.reach_name_list)

    def load_hydraulic(self, timestep_name_wish_list):
        """
        """
        # load specific timestep
        self.load_specific_timestep(timestep_name_wish_list)

        # get group
        geometry_flow_areas_group = self.results_data_file["Geometry/2D Flow Areas"]
        result_flow_areas_group = self.results_data_file["Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas"] # TODO : steadyflow case

        # initialization
        coord_p_all = []
        coord_p_xyz_all = []
        coord_c_all = []
        coord_c_xyz_all = []
        elev_p_all = []
        elev_c_all = []
        ikle_all = []
        vel_c_all = []
        shear_stress_c_all = []
        water_depth_c_all = []
        vel_t_all = []
        shear_stress_t_all = []
        water_depth_t_all = []

        # for each reach
        for reach_index, reach_name in enumerate(self.reach_name_list):
            # get group
            reach_name_geometry_group = geometry_flow_areas_group[reach_name]
            reach_name_result_group = result_flow_areas_group[reach_name]

            # basic geometry
            coord_p = reach_name_geometry_group["FacePoints Coordinate"][:]
            coord_c = reach_name_geometry_group["Cells Center Coordinate"][:]
            ikle = np.array(reach_name_geometry_group["Cells FacePoint Indexes"], dtype=np.int64)
            elev_c = reach_name_geometry_group[self.hvum.z.software_attributes_list[0]][:]
            coord_p_all.append(coord_p)
            coord_c_all.append(coord_c)
            ikle_all.append(ikle)
            elev_c_all.append(elev_c)
            # water depth by mesh
            water_depth = reach_name_result_group['Depth'][self.timestep_name_wish_list_index, :]
            water_depth_c_all.append(water_depth)

            # velocity is given on the side of the cells.
            # It is to be averaged to find the norm of speed in the middle of the cells.
            cells_face_all = reach_name_geometry_group["Cells Face and Orientation Values"][:]
            cells_face = cells_face_all[:, 0]
            where_is_cells_face = reach_name_geometry_group["Cells Face and Orientation Info"][:]
            where_is_cells_face1 = where_is_cells_face[:, 1]
            face_unit_vec = reach_name_geometry_group["Faces NormalUnitVector and Length"][:]
            face_unit_vec = face_unit_vec[:, :2]
            # face_variables
            velocity = reach_name_result_group[self.hvum.v.software_attributes_list[0]][self.timestep_name_wish_list_index, :].T  # timestep_name_wish_list_index
            shear_stress = reach_name_result_group[self.hvum.shear_stress.software_attributes_list[0]][self.timestep_name_wish_list_index, :].T  # timestep_name_wish_list_index
            new_shear_stress = np.hstack((face_unit_vec, shear_stress))  # for optimization (looking for face is slow)
            new_vel = np.hstack((face_unit_vec, velocity))  # for optimization (looking for face is slow)
            # new_elev = np.hstack((face_unit_vec, elevation.reshape(elevation.shape[0], 1)))
            lim_b = 0
            nbtstep = self.timestep_wish_nb
            vel_c = np.zeros((len(coord_c_all[reach_index]), nbtstep))
            shear_stress_c = np.zeros((len(coord_c_all[reach_index]), nbtstep))
            # for each mesh
            for c in range(len(coord_c_all[reach_index])):
                # find face
                nb_face = where_is_cells_face1[c]
                lim_a = lim_b
                lim_b = lim_a + nb_face
                face = cells_face[lim_a:lim_b]
                # vel
                data_face = new_vel[face, :]
                data_face_t = data_face[:, 2:].T
                add_vec_x = np.sum(data_face_t * data_face[:, 0], axis=1)
                add_vec_y = np.sum(data_face_t * data_face[:, 1], axis=1)
                vel_c[c, :] = np.sqrt(add_vec_x ** 2 + add_vec_y ** 2) / nb_face
                # shear_stress
                data2_face = new_shear_stress[face, :]
                data2_face_t = data2_face[:, 2:].T
                add_vec_x2 = np.sum(data2_face_t * data2_face[:, 0], axis=1)
                add_vec_y2 = np.sum(data2_face_t * data2_face[:, 1], axis=1)
                shear_stress_c[c, :] = np.sqrt(add_vec_x2 ** 2 + add_vec_y2 ** 2) / nb_face
            vel_c_all.append(vel_c)
            shear_stress_c_all.append(shear_stress_c)

            # important ther are 'flat cells'  all along on the edge/perimeter of the river  whith only 2 nodes/cell  and the center elevation of these cells is unknown (nan from HECRAS)
            # for habby we will destroy all those cells  afterwards
            # if np.isnan(elev_c_all[reach_index]).any():
            #     print('Warning: '+str(name_area[reach_index])+'there are cells where the center elevation is unknown  we are using Faces Minimum Elevation to calculate them')
            #     # elevation FacePoints
            #     faces_facepoint_indexes = reach_name_geometry_group["Faces FacePoint Indexes"][:]
            #     face_center_point = np.mean([coord_p_all[reach_index][faces_facepoint_indexes[:, 0]], coord_p_all[reach_index][faces_facepoint_indexes[:, 1]]], axis=0)
            #     elev_f = reach_name_geometry_group["Faces Minimum Elevation"][:]
            #     elev_c_all3 = griddata(face_center_point, elev_f, coord_c_all[reach_index])
            #     elev_c_all[reach_index][np.isnan(elev_c_all[reach_index])] = elev_c_all3[np.isnan(elev_c_all[reach_index])]
            #     if np.isnan(elev_c_all[reach_index]).any():
            #         print('Warning: there are still cells where the center elevation is unknown')

            elev_p = interpolator_test(coord_c_all[reach_index],
                                       elev_c_all[reach_index],
                                       coord_p_all[reach_index])
            # elev_p = griddata(points=coord_c_all[reach_index],
            #                   values=elev_c_all[reach_index],
            #                   xi=coord_p_all[reach_index],
            #                   method="linear")

            # elev_f = reach_name_geometry_group["Faces Minimum Elevation"][:]
            # elev_p3 = griddata(face_center_point, elev_f, coord_p_all[reach_index])
            # elev_p[np.isnan(elev_p)] = elev_p3[np.isnan(elev_p)]
            # elev_p = griddata(coord_c_all[reach_index], elev_c_all[reach_index], coord_p_all[reach_index])
            # elev_f = reach_name_geometry_group["Faces Minimum Elevation"][:]
            # faces_facepoint_indexes = reach_name_geometry_group["Faces FacePoint Indexes"][:]
            # elev_p2 = np.zeros((len(coord_p_all[reach_index])))
            # for point_index in range(len(coord_p_all[reach_index])):
            #     first_bool = faces_facepoint_indexes[:, 0] == point_index
            #     second_bool = faces_facepoint_indexes[:, 1] == point_index
            #     elev_p2[point_index] = (np.sum(elev_f[first_bool]) + np.sum(elev_f[second_bool])) / \
            #                           (np.sum(first_bool) + np.sum(second_bool))
            # elev_p[np.isnan(elev_p)] = elev_p2[np.isnan(elev_p)]
            if np.isnan(elev_p).any():
                # elevation FacePoints
                faces_facepoint_indexes = reach_name_geometry_group["Faces FacePoint Indexes"][:]
                face_center_point = np.mean(
                    [coord_p_all[reach_index][faces_facepoint_indexes[:, 0]], coord_p_all[reach_index][faces_facepoint_indexes[:, 1]]],
                    axis=0)
                elev_f = reach_name_geometry_group["Faces Minimum Elevation"][:]
                for point_index in np.where(np.isnan(elev_p))[0]:  # for point_index in range(len(coord_p_all[reach_index]))
                    first_bool = faces_facepoint_indexes[:, 0] == point_index
                    second_bool = faces_facepoint_indexes[:, 1] == point_index
                    elev_p[point_index] = (np.sum(elev_f[first_bool]) + np.sum(elev_f[second_bool])) / \
                                          (np.sum(first_bool) + np.sum(second_bool))
            if np.isnan(elev_p).any():
                print('Warning: there are points/nodes where the elevation is unknown not calculated by HABBY')

            elev_p_all.append(elev_p)

            # get data time step by time step
            water_depth_t = []
            vel_t = []
            shear_stress_t = []
            for timestep_name_wish_index in range(self.timestep_wish_nb):
                water_depth_t.append(water_depth_c_all[reach_index][timestep_name_wish_index])
                vel_t.append(vel_c_all[reach_index][:, timestep_name_wish_index])
                shear_stress_t.append(shear_stress_c_all[reach_index][:, timestep_name_wish_index])
            water_depth_t_all.append(water_depth_t)
            vel_t_all.append(vel_t)
            shear_stress_t_all.append(shear_stress_t)
            # xyz
            coord_p_xyz_all.append(np.column_stack([coord_p_all[reach_index], elev_p_all[reach_index]]))
            coord_c_xyz_all.append(np.column_stack([coord_c_all[reach_index], elev_c_all[reach_index]]))

        # get a triangular grid as hec-ras output are not triangular
        ikle_all, coord_p_xyz_all, water_depth_t_all, vel_t_all, shear_stress_t_all, z_all = get_triangular_grid_hecras(
            ikle_all, coord_c_xyz_all, coord_p_xyz_all, water_depth_t_all, vel_t_all, shear_stress_t_all)

        # transform data to pandas
        data_mesh_pd_r_list = []
        for reach_num in range(len(self.reach_name_list)):
            data_mesh_pd_t_list = []
            for timestep_name_wish_index in range(self.timestep_wish_nb):
                data_mesh_pd = pd.DataFrame()
                data_mesh_pd[self.hvum.v.name] = vel_t_all[reach_num][:, timestep_name_wish_index]
                data_mesh_pd[self.hvum.shear_stress.name] = shear_stress_t_all[reach_num][:, timestep_name_wish_index]
                data_mesh_pd_t_list.append(data_mesh_pd)
            data_mesh_pd_r_list.append(data_mesh_pd_t_list)

        # finite_volume_to_finite_element_triangularxy
        tin = []
        xy = []
        z = []
        h = []
        # v = []
        # shear_stress = []
        data_node_list = []
        for reach_num in range(len(self.reach_name_list)):
            ikle_reach = np.column_stack(
                [ikle_all[reach_num], np.ones(len(ikle_all[0]), dtype=ikle_all[0].dtype) * -1])  # add -1 column
            ikle_reach, xyz_reach, h_reach, data_node_pd = manage_grid_mod.finite_volume_to_finite_element_triangularxy(
                                                                                    ikle_reach,
                                                                                    coord_p_xyz_all[reach_num],
                                                                                    water_depth_t_all[reach_num],
                                                                                    # vel_t_all[reach_num],
                                                                                    # shear_stress_t_all[reach_num]
                                                                                    data_mesh_pd_r_list[reach_num])
            tin.append(ikle_reach)
            xy.append(xyz_reach[:, (0, 1)])
            z.append(xyz_reach[:, 2])

            h_unit = []
            # v_unit = []
            # shear_stress_unit = []
            data_node_list_unit = []
            for unit_num in range(len(self.timestep_name_wish_list_index)):
                h_unit.append(h_reach[:, unit_num])
                h_unit.append(h_reach[:, unit_num])
                # v_unit.append(v_reach[:, unit_num])
                # shear_stress_unit.append(shear_stress_reach[:, unit_num])
                data_node_list_unit.append(data_node_pd[unit_num])
            h.append(h_unit)
            # v.append(v_unit)
            # shear_stress.append(shear_stress_unit)
            data_node_list.append(data_node_list_unit)

        # prepare original and computed data for data_2d
        for reach_num in range(self.reach_num):  # for each reach
            for timestep_index in range(self.timestep_wish_nb):  # for each timestep
                for variables_wish in self.hvum.hdf5_and_computable_list:  # .varunits
                    if variables_wish.position == "mesh":
                        if variables_wish.name == self.hvum.z.name:
                            variables_wish.data[reach_num].append(z_all[reach_num][:, timestep_index].astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.h.name:
                            variables_wish.data[reach_num].append(water_depth_t_all[reach_num][:, timestep_index].astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.v.name:
                            variables_wish.data[reach_num].append(vel_t_all[reach_num][:, timestep_index].astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.shear_stress.name:
                            variables_wish.data[reach_num].append(shear_stress_t_all[reach_num][:, timestep_index].astype(variables_wish.dtype))
                    if variables_wish.position == "node":
                        if variables_wish.name == self.hvum.z.name:
                            variables_wish.data[reach_num].append(z[reach_num].astype(variables_wish.dtype))
                        elif variables_wish.name == self.hvum.h.name:
                            variables_wish.data[reach_num].append(h[reach_num][timestep_index].astype(variables_wish.dtype))

                        else:
                            var_node_index = data_mesh_pd_r_list[0][0].columns.values.tolist().index(variables_wish.name)
                            variables_wish.data[reach_num].append(data_node_list[reach_num][timestep_index][:, var_node_index].astype(variables_wish.dtype))

                        # elif variables_wish.name == self.hvum.v.name:
                        #     variables_wish.data[reach_num].append(v[reach_num][timestep_index].astype(variables_wish.dtype))
                        # elif variables_wish.name == self.hvum.shear_stress.name:
                        #     variables_wish.data[reach_num].append(shear_stress[reach_num][timestep_index].astype(variables_wish.dtype))

            # coord
            self.hvum.xy.data[reach_num] = [xy[reach_num]] * self.timestep_wish_nb
            self.hvum.tin.data[reach_num] = [tin[reach_num]] * self.timestep_wish_nb

        return self.get_data_2d()


#@profileit
def interpolator_test(coord_c_all, elev_c_all, coord_p_all):
    # TODO : compare result array between griddata and matplotlib.tri.LinearTriInterpolator
    # # griddata
    elev_p = griddata(points=coord_c_all,
                      values=elev_c_all,
                      xi=coord_p_all,
                      method="linear")

    # # MPL
    # triang = mtri.Triangulation(coord_c_all[:, 0], coord_c_all[:, 1])
    # interp_lin = mtri.LinearTriInterpolator(triang, elev_c_all)  # somevalues = hauteur d'eau par exemple
    #
    # # Interpolate sur de nouvelles coordonnees
    # elev_p = np.ma.getdata(interp_lin(coord_p_all[:, 0], coord_p_all[:, 1])) # xi et yi definissent une nouvelle grille​

    return elev_p


def get_discharges(filename_path):
    # open file
    if os.path.isfile(filename_path):
        try:
            file2D = h5py.File(filename_path, 'r')
        except OSError:
            print("Error: unable to open the hdf file.")

    # find discharges
    discharge_path = "/Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/2D_AREA/Boundary Conditions"
    flow_dataset_names = None
    try:
        boundary_conditions = list(file2D[discharge_path].keys())
        flow_dataset_names = [boundary_condition for boundary_condition in boundary_conditions if "flow" in boundary_condition.lower()]
    except:
        print("Error: Can't find boundary conditions datasets in ", filename_path)

    if flow_dataset_names:
        nb_timesteps, timesteps = get_time_step(filename_path)
        for flow_dataset_name in flow_dataset_names:
            discharge_list = np.sum(file2D[discharge_path + "/" + flow_dataset_name][:], axis=1).astype(np.str).tolist()
            if len(discharge_list) == len(timesteps):
                for timestep_num, timestep in enumerate(timesteps):
                    timesteps[timestep_num] = timestep + " - " + discharge_list[timestep_num]
    return timesteps


def get_triangular_grid_hecras(ikle_all, coord_c_all, point_all, h, v, shear_stress):
    """
    In Hec-ras, it is possible to have non-triangular cells, often rectangular cells This function transform the
    "mixed" grid to a triangular grid. For this,
    it uses the centroid of each cell with more than three side and it create a triangle by side (linked with the
    center of the cell). A similar function exists in rubar1d2d_mod.py, but, as there are only one reach in rubar
    and because ikle is different in hec-ras, it was hard to merge both functions together.

    This function can only be used if the original grid is the same for all time steps. The grid created is different
    for each time steps.

    :param ikle_all: cell definition ie the connectivity table by reach (list of np.array)[by reach
    :param coord_c_all: the coordinate of the centroid of the cell (list of xyz np.array) [by reach
    :param point_all: the points/nodes of the grid (list of xyz np.array) [by reach
    :param h: data on cell water height  (list of np.array)[by time step [by reach
    :param v: data on cell velocity (list of np.array) [by time step [by reach
    :return: the updated ikle_all,  point_all, h_all, v_all with only triangles
    """

    nb_reach = len(ikle_all)

    v_all = []
    shear_stress_all = []
    z_all = []
    h_all = []

    nbtime = len(v[0])  #TODO : if multi reach : nbtime can vary by reach ? We said nbtime can't vary by reach ...

    # create the new grid for each reach
    for r in range(nb_reach):
        # store the hydraulic data of the reach
        hr = np.zeros((len(ikle_all[r]), nbtime), dtype=np.float64)
        vr = np.zeros((len(ikle_all[r]), nbtime), dtype=np.float64)
        shear_stressr = np.zeros((len(ikle_all[r]), nbtime), dtype=np.float64)
        zr = np.zeros((len(ikle_all[r]), nbtime), dtype=np.float64)

        # add data by time step
        for t in range(nbtime):
            hr[:, t] = h[r][t]  # list of np.array
            vr[:, t] = v[r][t]
            shear_stressr[:, t] = shear_stress[r][t]
            zr[:, t] = coord_c_all[r][:, 2]

        ikle = np.copy(ikle_all[r])
        iklesum = np.copy(ikle)
        iklesum[iklesum != -1] = 1
        iklesum[iklesum == -1] = 0
        iklesum = np.sum(iklesum, axis=1)  # storing the number of points/nodes defining each cell/polygon
        bmeshmore2 = iklesum > 2  # bmeshmore2 np array to determine the 'valid' cells/polygons with more than 2 nodes; np.sum(~bmesh2) the number of these invalid meshes
        # now calculate nbmeshsup= the increase of the total cells/polygons number after transforming cells with more than 3 nodes into triangles
        # eg we will keep a triangle, a quadrangle will be split in 4 triangles and the increase will be +3, etc...
        iklemore3 = np.copy(iklesum)
        iklemore3[iklemore3 < 4] = 1
        nbmeshsup = np.sum(iklemore3 - 1)
        # calculating the number of point (cell centers) that we will add as node for triangles after splinting cells with more than 3 nodes into triangles
        npxyzsup = np.sum(iklemore3 != 1)
        # ikle3 to store only the valid triangles
        ikle3 = np.concatenate((ikle[bmeshmore2][..., :3], np.empty((nbmeshsup, 3), dtype=ikle.dtype)),
                                   axis=0)
        # xyz3  the nodes of the new set of triangles we will add to the nodes cells all the cells centers with more than 3 nodes
        xyz3 = np.concatenate((point_all[r], np.empty((npxyzsup, point_all[r].shape[1]), dtype=point_all[r].dtype)),
                              axis=0)

        hr3 = np.concatenate((hr[bmeshmore2], np.empty((nbmeshsup, nbtime), dtype=np.float64)), axis=0)
        vr3 = np.concatenate((vr[bmeshmore2], np.empty((nbmeshsup, nbtime), dtype=np.float64)), axis=0)
        shear_stressr3 = np.concatenate((shear_stressr[bmeshmore2], np.empty((nbmeshsup, nbtime), dtype=np.float64)), axis=0)
        zr3 = np.concatenate((zr[bmeshmore2], np.empty((nbmeshsup, nbtime), dtype=np.float64)), axis=0)
        likle = len(ikle)
        c3, cc3, ixyz3 = 0, np.sum(bmeshmore2) - 1, len(
            point_all[r]) - 1  # c3 index for the beginning of ikle3 cc3 index for new triangle
        for c in range(likle):
            if iklesum[c] == 3:
                c3 += 1  # ikle3 already OK by construction
            if iklesum[
                c] > 3:  # splitting the cell into triangles with the common node = cell center respecting the rotational direction
                ixyz3 += 1
                xyz3[ixyz3, :] = coord_c_all[r][c, :]  # adding the center cell as a point node
                ikle3[c3][2] = ixyz3  # first triangle
                c3 += 1
                for s in range(1, iklesum[c] - 1):
                    cc3 += 1
                    ikle3[cc3, :] = ikle[c][s], ikle[c][s + 1], ixyz3  # others triangle
                    hr3[cc3, :] = hr[c, :]
                    vr3[cc3, :] = vr[c, :]
                    shear_stressr3[cc3, :] = shear_stressr[c, :]
                    zr3[cc3, :] = zr[c, :]
                cc3 += 1
                ikle3[cc3, :] = ikle[c][iklesum[c] - 1], ikle[c][0], ixyz3  # last triangle
                hr3[cc3, :] = hr[c, :]
                vr3[cc3, :] = vr[c, :]
                shear_stressr3[cc3, :] = shear_stressr[c, :]
                zr3[cc3, :] = zr[c, :]
        # add grid by reach
        ikle_all[r] = ikle3
        point_all[r] = xyz3

        # add data by time step
        h_all.append(hr3)
        v_all.append(vr3)
        shear_stress_all.append(shear_stressr3)
        z_all.append(zr3)

    return ikle_all, point_all, h_all, v_all, shear_stress_all, z_all


def figure_hec_ras2d(v_all, h_all, elev_all, coord_p_all, coord_c_all, ikle_all, path_im, time_step=[0], flow_area=[0],
                     max_point=-99):
    """
    This is a function to plot figure of the output from hec-ras 2D. This function is only used to debug, not directly by HABBY.

    :param v_all: a list of np array representing the velocity at the center of the cells
    :param h_all:  a list of np array representing the water depth at the center of the cells
    :param elev_all: a list of np array representing the mimium elevation of each cells
    :param coord_p_all: a list of np array representing the coordinates of the points of the grid
    :param coord_c_all: a list of np array representing the coordinates of the centers of the grid
    :param ikle_all: a list of np array representing the connectivity table
           one array by flow area
    :param time_step: which time_step should be plotted (default, the first one)
    :param flow_area: which flow_area should be plotted (default, the first one)
    :param max_point: the number of cell to be drawn when reconstructing the grid (it might long)
    :param path_im: the path where the figure should be saved

    **Technical comment**

    This function creates three figures which represent: a) the grid of the loaded models b) the water height and
    c) the velocity.

    The two last figures will be modified when the data will be loaded by node and not by cells. So we will not explai
    n them here as they should be re-written.

    The first figure is used to plot the gird. If we would plot the grid by drawing one side of each triangle
    separately, it would be very long to draw. To optimize the process, we use the prepare_grid function.
    """
    # figure size
    # plt.close()
    fig_size_inch = (8, 6)
    # plt.rcParams['figure.figsize'] = 7, 3
    plt.rcParams['font.size'] = 10

    # for each chosen flow_area
    for f in flow_area:
        ikle = ikle_all[f]
        coord_p = coord_p_all[f]
        coord_c = coord_c_all[f]
        elev = elev_all[f]

        # plot grid
        [xlist, ylist] = prepare_grid(ikle, coord_p)
        fig = plt.figure()
        # sc2 = plt.scatter(coord_p[:, 0], coord_p[:, 1], s=0.07, color='r')
        # sc1 = plt.scatter(point_dam_levee[:, 0], point_dam_levee[:, 1], s=0.07, color='k')
        plt.plot(xlist, ylist, c='b', linewidth=0.2)
        plt.plot(coord_c[:, 0], coord_c[:, 1], '*b')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title('Grid ')
        plt.savefig(os.path.join(path_im, "HEC2D_grid_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        plt.savefig(os.path.join(path_im, "HEC2D_grid" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        # plt.close()

        # size of the marker (to avoid having to pale, unclear figure)
        # this is a rough estimation, no need for precise number here
        d1 = 0.5 * np.sqrt(
            (coord_c[1, 0] - coord_c[0, 0]) ** 2 + (coord_c[1, 1] - coord_c[0, 1]) ** 2)  # dist in coordinate
        dist_data = np.mean(
            [np.max(coord_c[:, 0]) - np.min(coord_c[:, 0]), np.max(coord_c[:, 1]) - np.min(coord_c[:, 1])])
        f_len = fig_size_inch[0] * 72  # point is 1/72 inch
        transf = f_len / dist_data
        s1 = 3.1 * (d1 * transf) ** 2 / 2  # markersize is given as an area
        s2 = s1 / 10

        # # elevation
        # fig = plt.figure()
        # cm = plt.cm.get_cmap('terrain')
        # sc = plt.scatter(coord_c[:, 0], coord_c[:, 1], c=elev, vmin=np.nanmin(elev), vmax=np.nanmax(elev), s=s1,cmap=cm, edgecolors='none')
        # cbar = plt.colorbar(sc)
        # cbar.ax.set_ylabel('Elev. [m]')
        # plt.xlabel('x coord []')
        # plt.ylabel('y coord []')
        # plt.title('Elevation above sea level')
        # plt.savefig(os.path.join(path_im, "HEC2D_elev_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
        # plt.savefig(os.path.join(path_im, "HEC2D_elev_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
        # #plt.close()

        # for each chosen time step
        for t in time_step:
            vel_c = v_all[t][f]
            water_depth = h_all[t][f]
            # plot water depth
            # water_deptht = np.squeeze(water_depth[t, :])
            scatter_plot(coord_c, water_depth, 'Water Depth [m]', 'terrain', 8, t)
            plt.savefig(os.path.join(path_im, "HEC2D_waterdepth_t" + str(t) + '_' + time.strftime(
                "%d_%m_%Y_at_%H_%M_%S") + '.png'))
            plt.savefig(os.path.join(path_im, "HEC2D_waterdepth_t" + str(t) + '_' + time.strftime(
                "%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
            # plt.close()

            # plot velocity
            # vel_c0 = vel_c[:, t]
            scatter_plot(coord_c, vel_c, 'Vel. [m3/sec]', 'gist_ncar', 8, t)
            plt.savefig(
                os.path.join(path_im, "HEC2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'))
            plt.savefig(
                os.path.join(path_im, "HEC2D_vel_t" + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'))
            # plt.close()

    plt.show()


def prepare_grid(ikle, coord_p, max_point=-99):
    """
    This is a function to put in the new form the data forming the grid to accelerate the plotting of the grid. This function creates
    a list of points of the grid which are re-ordered compared to the usual list of grid point (the variable coord_p
    here). These points are reordered so that it is possible to draw only one line to form the grid (one point can
    appears more than once). The grid is drawn as one long line and not as a succession of small lines, which is
    quicker. When this new list is created by prepare_function(), it is send back to figure-hec_ras_2D and plotted.

    :param ikle: the connectivity table
    :param coord_p: the coordinates of the point
    :param max_point: if the grid is very big, it is possible to only plot the first points, up to max_points (int)
    :return: a list of x and y coordinates ordered.
    """
    if max_point < 0 or max_point > len(ikle):
        max_point = len(ikle)

    # prepare grid
    xlist = []
    ylist = []
    for i in range(0, max_point):
        pi = 0
        # get rid of the minus 1 in ikle useful to plot the initial squared grid
        # ikle2 = [item for item in ikle[i] if item >= 0]
        while pi < len(ikle[i]) - 1:
            # The conditions should be tested in this order to avoid to go out of the array
            p = ikle[i][pi]  # we start at 0 in python, careful about -1 or not
            p2 = ikle[i][pi + 1]
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = ikle[i][pi]
        p2 = ikle[i][0]
        xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
        xlist.append(None)
        ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
        ylist.append(None)

    return xlist, ylist


def scatter_plot(coord, data, data_name, my_cmap, s1, t):
    """
    The function to plot the scatter of the data. Will not be used in the final version, but can be useful to
    plot data by cells.

    :param coord: the coordinates of the point
    :param data: the data to be plotted (np.array)
    :param data_name: the name of the data (string)
    :param my_cmap: the color map (string with matplotlib colormap name)
    :param s1: the size of the dot for the scatter
    :param t: the time step being plotted
    """
    s2 = s1 / 10
    fig = plt.figure()
    cm = plt.cm.get_cmap(my_cmap)
    # cm = plt.cm.get_cmap('plasma')

    data_big = data[data > 0]
    # sc = plt.hexbin(coord_c[:, 0], coord_c[:, 1], C=vel_c0, gridsize=70, cmap=cm)
    if np.sum(data_big) > 0:
        sc = plt.scatter(coord[data > 0, 0], coord[data > 0, 1], c=data_big, vmin=np.nanmin(data_big), \
                         vmax=np.nanmax(data_big), s=s1, cmap=cm, edgecolors='none')
        cbar = plt.colorbar(sc)
        cbar.ax.set_ylabel(data_name)
    else:
        plt.text(np.mean(coord[:, 0]), np.mean(coord[:, 1]), 'Data is null. No plotting possible')
    sc = plt.scatter(coord[data == 0, 0], coord[data == 0, 1], c='0.5', s=s2, cmap=cm, edgecolors='none')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')

    if t == -1:
        plt.title(data_name + ' at the last time step')
    else:
        plt.title(data_name + ' at time step ' + str(t))


def main():
    """
    Used to test this module independantly of HABBY.
    """
    path = r'C:\Users\diane.von-gunten\HABBY\test_data'
    filename = 'Muncie.p04.hdf'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    a = time.clock()
    [v, h, elev, coord_p, coord_c, ikle] = load_hec_ras2d(filename, path)
    b = time.clock()
    print('Time to load data:' + str(b - a) + 'sec')
    figure_hec_ras2d(v, h, elev, coord_p, coord_c, ikle, path_im, [50], [0])


if __name__ == '__main__':
    main()
