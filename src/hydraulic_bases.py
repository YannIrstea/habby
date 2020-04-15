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
import sys

from src.manage_grid_mod import is_duplicates_mesh_and_point_on_one_unit, linear_z_cross


class HydraulicVariable:
    def __init__(self, value, unit, name, name_gui, dtype):
        self.value = value
        self.unit = unit
        self.name = name
        self.name_gui = name_gui
        self.dtype = dtype
        self.position = None
        self.existing_attributes_list = []
        self.data = [[]]
        self.computable = False


class HydraulicVariableUnitManagement:
    def __init__(self):
        self.final_variable_list = []
        self.usefull_variable_wish_list = []
        self.usefull_variable_detected_list = []
        self.usefull_variable_node_detected_list = []
        self.usefull_variable_mesh_detected_list = []
        self.final_mesh_variable_name_list = []
        self.final_node_variable_name_list = []
        # init
        self.v_x_and_v_y_presence = False


        # fixed values
        self.ro = HydraulicVariable(value=999.7,
                                    unit="kg/m3",
                                    name="ro",
                                    name_gui="ρ",
                                    dtype=np.float64)
        self.g = HydraulicVariable(value=9.80665,
                                   unit="m/s2",
                                   name="g",
                                   name_gui="gravity",
                                   dtype=np.float64)
        # coordinate variables
        self.tin = HydraulicVariable(value=None,
                                     unit="",
                                     name="tin",
                                     name_gui="tin",
                                     dtype=np.int64)
        self.xy = HydraulicVariable(value=None,
                                    unit="m",
                                    name="xy",
                                    name_gui="xy",
                                    dtype=np.float64)
        self.z = HydraulicVariable(value=None,
                                   unit="m",
                                   name="z",
                                   name_gui="elevation",
                                   dtype=np.float64)
        # usefull variable values
        self.h = HydraulicVariable(value=None,
                                   unit="m",
                                   name="h",
                                   name_gui="water_height",
                                   dtype=np.float64)
        self.v_x = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_x",
                                     name_gui="water_velocity_x",
                                     dtype=np.float64)
        self.v_y = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_y",
                                     name_gui="water_velocity_y",
                                     dtype=np.float64)
        self.v = HydraulicVariable(value=None,
                                   unit="m/s",
                                   name="v",
                                   name_gui="water_velocity",
                                   dtype=np.float64)
        self.level = HydraulicVariable(value=None,
                                       unit="m",
                                       name="level",
                                       name_gui="water_level",
                                       dtype=np.float64)
        self.froude = HydraulicVariable(value=None,
                                        unit="",
                                        name="froude",
                                        name_gui="froude_number",
                                        dtype=np.float64)
        self.hydraulic_head = HydraulicVariable(value=None,
                                                unit="",
                                                name="hydraulic_head",
                                                name_gui="hydraulic_head",
                                                dtype=np.float64)
        self.conveyance = HydraulicVariable(value=None,
                                            unit="",
                                            name="conveyance",
                                            name_gui="conveyance",
                                            dtype=np.float64)
        self.max_slope_bottom = HydraulicVariable(value=None,
                                                  unit="",
                                                  name="max_slope_bottom",
                                                  name_gui="max_slope_bottom",
                                                  dtype=np.float64)
        self.max_slope_energy = HydraulicVariable(value=None,
                                                  unit="",
                                                  name="max_slope_energy",
                                                  name_gui="max_slope_energy",
                                                  dtype=np.float64)
        self.shear_stress = HydraulicVariable(value=None,
                                              unit="",
                                              name="shear_stress",
                                              name_gui="shear_stress",
                                              dtype=np.float64)
        self.temp = HydraulicVariable(value=None,
                                      unit="",
                                      name="temp",
                                      name_gui="temperature",
                                      dtype=np.float64)
        self.v_frict = HydraulicVariable(value=None,
                                         unit="",
                                         name="v_frict",
                                         name_gui="friction velocity",
                                         dtype=np.float64)
        self.sub = HydraulicVariable(value=None,
                                     unit="",
                                     name="sub",
                                     name_gui="substrate",
                                     dtype=np.int64)

    def set_existing_attributes_list(self, name, attribute_list, position):
        getattr(self, name).existing_attributes_list = attribute_list
        getattr(self, name).position = position
        self.usefull_variable_wish_list.append(getattr(self, name))

    def remove_variable_from(self, usefull, final, variable_name):
        if usefull:
            variable_name_list = [variable.name for variable in self.usefull_variable_detected_list]
            variable_index = variable_name_list.index(variable_name)
            self.usefull_variable_detected_list.pop(variable_index)
        if final:
            variable_name_list = [variable.name for variable in self.final_variable_list]
            variable_index = variable_name_list.index(variable_name)
            self.final_variable_list.pop(variable_index)

    def get_available_variables_from_source(self, varnames):
        # get_available_variables_from_source
        for varname_index, varname in enumerate(varnames):
            for usefull_variable_wish in self.usefull_variable_wish_list:
                for wish_attribute in usefull_variable_wish.existing_attributes_list:
                    if wish_attribute in varname:
                        usefull_variable_wish.varname_index = varname_index
                        self.usefull_variable_detected_list.append(usefull_variable_wish)

        # separate node and mesh
        for usefull_variable_detected in self.usefull_variable_detected_list:
            if usefull_variable_detected.position == "node":
                self.usefull_variable_node_detected_list.append(usefull_variable_detected.name)
            elif usefull_variable_detected.position == "mesh":
                self.usefull_variable_mesh_detected_list.append(usefull_variable_detected.name)

        # copy
        self.final_variable_list = list(self.usefull_variable_detected_list)

        """ nodes """

        # is v_x and v_y ?
        if self.v_x.name in self.usefull_variable_node_detected_list and self.v_y.name in self.usefull_variable_node_detected_list:
            self.v_x_and_v_y_presence = True

        # computed_node_velocity or original ?
        if self.v.name in self.usefull_variable_node_detected_list:
            self.v.original = True
            self.v.computable = False
        if not self.v.name in self.usefull_variable_node_detected_list and self.v_x_and_v_y_presence:
            self.v.original = False
            self.v.computable = True
            self.final_variable_list = self.final_variable_list + [self.v]  # always v

        # computed_node_shear_stress or original ?
        if not self.shear_stress.name in self.usefull_variable_node_detected_list and self.v_frict.name in self.usefull_variable_node_detected_list:
            self.shear_stress.computable = True
            self.final_variable_list = self.final_variable_list + [self.shear_stress]

        self.update_final_variable_list()

    def update_final_variable_list(self):
        # separate node and mesh
        for final_variable in self.final_variable_list:
            if final_variable.position == "node":
                self.final_node_variable_name_list.append(final_variable.name)
            elif final_variable.position == "mesh":
                self.final_mesh_variable_name_list.append(final_variable.name)


class HydraulicModelInformation:
    def __init__(self):
        # models
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
        # exist ?
        if not os.path.isfile(self.filename_path):
            self.warning_list.append("Error: The file does not exist.")
            self.valid_file = False

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

    def get_data_2d_dict(self):
        # remove z from final
        self.hvum.final_node_variable_name_list.remove(self.hvum.z.name)

        # create empty list
        data_2d = Data2d()

        for reach_num in range(len(self.reach_name_list)):
            data_2d.append([])
            for unit_num in range(len(self.timestep_name_wish_list)):
                """ node """
                node_total_nb = self.hvum.xy.data[reach_num][unit_num].shape[0]
                if self.hvum.final_node_variable_name_list:
                    # preffix string added to unit (if duplicate numpy don't like it)
                    dtype_list = [((str(node_variable_index) + "_" + getattr(self.hvum, node_variable_name).unit, node_variable_name), getattr(self.hvum, node_variable_name).dtype) for node_variable_index, node_variable_name in enumerate(self.hvum.final_node_variable_name_list)]
                    node_data_array = np.zeros(shape=(node_total_nb,),
                                               dtype=dtype_list)  # structured array
                    for node_variable_name in self.hvum.final_node_variable_name_list:
                        node_data_array[node_variable_name] = getattr(self.hvum, node_variable_name).data[reach_num][unit_num]
                else:
                    node_data_array = None

                """ mesh """
                mesh_total_nb = self.hvum.tin.data[reach_num][unit_num].shape[0]
                if self.hvum.final_mesh_variable_name_list:
                    # preffix string added to unit (if duplicate numpy don't like it)
                    dtype_list = [((str(mesh_variable_index) + "_" + getattr(self.hvum, mesh_variable_name).unit, mesh_variable_name), getattr(self.hvum, mesh_variable_name).dtype) for mesh_variable_index, mesh_variable_name in enumerate(self.hvum.final_mesh_variable_name_list)]
                    mesh_data_array = np.zeros(shape=(mesh_total_nb,),
                                               dtype=dtype_list)  # structured array
                    for mesh_variable_name in self.hvum.final_mesh_variable_name_list:
                        mesh_data_array[mesh_variable_name] = getattr(self.hvum, mesh_variable_name).data[reach_num][unit_num]
                else:
                    mesh_data_array = None

                """ unit_dict """
                unit_dict = dict(mesh=dict(data=mesh_data_array,
                                           whole_profile=None,
                                           tin=self.hvum.tin.data[reach_num][unit_num]),
                                 node=dict(data=node_data_array,
                                           xy=self.hvum.xy.data[reach_num][unit_num],
                                           z=self.hvum.z.data[reach_num][unit_num]))
                data_2d[reach_num].append(unit_dict)

        data_2d.get_informations()

        # description telemac data_2d dict
        description_from_file = dict()
        description_from_file["filename_source"] = self.filename
        description_from_file["model_type"] = self.model_type
        description_from_file["model_dimension"] = str(2)
        description_from_file["unit_list"] = ", ".join(self.timestep_name_wish_list)
        description_from_file["unit_number"] = str(self.timestep_wish_nb)
        description_from_file["unit_type"] = "time [s]"
        description_from_file["unit_z_equal"] = self.unit_z_equal

        return data_2d, description_from_file


class Data2d(list):
    def __init__(self):
        super().__init__()
        self.reach_num = 0
        self.unit_num = 0

    def get_informations(self):
        self.reach_num = len(self)
        self.unit_num = len(self[self.reach_num - 1])

    def get_whole_profile(self):
        """
        retrun whole_profile from original data2d
        """
        self.get_informations()

        whole_profile = Data2d()
        for reach_num in range(self.reach_num):
            whole_profile.append([])
            for unit_num in range(self.unit_num):
                whole_profile[reach_num].append(dict(mesh=dict(tin=self[reach_num][unit_num]["mesh"]["tin"]),
                                 node=dict(xy=self[reach_num][unit_num]["node"]["xy"],
                                           z=self[reach_num][unit_num]["node"]["z"])))
        return whole_profile

    def get_hyd_varying_xy_and_z_index(self):
        self.get_informations()
        # hyd_varying_mesh and hyd_unit_z_equal?
        hyd_varying_xy_index = []
        hyd_varying_z_index = []
        for reach_num in range(self.reach_num):
            hyd_varying_xy_index.append([])
            hyd_varying_z_index.append([])
            it_equality = 0
            for unit_num in range(self.unit_num):
                if unit_num == 0:
                    hyd_varying_xy_index[reach_num].append(it_equality)
                    hyd_varying_z_index[reach_num].append(it_equality)
                if unit_num > 0:
                    # xy
                    if np.array_equal(self[reach_num][unit_num]["node"]["xy"],
                                      self[reach_num][it_equality]["node"]["xy"]):  # equal
                        hyd_varying_xy_index[reach_num].append(it_equality)
                    else:
                        it_equality = unit_num
                        hyd_varying_xy_index[reach_num].append(it_equality)  # diff
                    # z
                    if np.array_equal(self[reach_num][unit_num]["node"]["z"],
                                      self[reach_num][it_equality]["node"]["z"]):  # equal
                        hyd_varying_z_index[reach_num].append(it_equality)
                    else:
                        it_equality = unit_num
                        hyd_varying_z_index[reach_num].append(it_equality)  # diff
        return hyd_varying_xy_index, hyd_varying_z_index

    def cut_2d_grid_data_2d(self, unit_list, progress_value, delta_file, CutMeshPartialyDry, min_height):
        """
        This function cut the grid of the 2D model to have correct wet surface. If we have a node with h<0 and other node(s)
        with h>0, this function cut the cells to find the wetted part, assuming a constant water elevation in the mesh.
        All mesh entierly dry are always cuted. if CutMeshPartialyDry is True, partialy dry mesh are also cuted.
        This function works for one unit of a reach.

        :param ikle: the connectivity table of the 2D grid
        :param point_all: the coordinate x,y,z of the points
        :param water_height: the water height data given on the nodes
        :param velocity: the velocity given on the nodes
        :param min_height: the minimum water height considered (as model sometime have cell with very low water height)
        :param CutMeshPartialyDry: If True partialy dry mesh are cuted
        :return: the update connectivity table, the coordinates of the point, the height of the water and the
                 velocity on the updated grid and the indices of the old connectivity table in the new cell orders.
        """
        self.get_informations()
        # prog
        deltaunit = delta_file / len(unit_list)

        # for each reach
        self.unit_list_cuted = []
        for reach_num in range(self.reach_num):
            self.unit_list_cuted.append([])
            # for each unit
            for unit_num, unit_name in enumerate(unit_list):
                # get data from dict
                ikle = self[reach_num][unit_num]["mesh"]["tin"]
                point_all = np.column_stack((self[reach_num][unit_num]["node"]["xy"],
                                 self[reach_num][unit_num]["node"]["z"]))
                water_height = self[reach_num][unit_num]["node"]["data"]["h"]
                velocity = self[reach_num][unit_num]["node"]["data"]["v"]

                # is_duplicates_mesh_and_point_on_one_unit?
                if is_duplicates_mesh_and_point_on_one_unit(tin_array=ikle,
                                                            xyz_array=point_all,
                                                            unit_num=unit_num,
                                                            case="before the deletion of dry mesh"):
                    print("Warning: The mesh of unit " + unit_name + " is not loaded")
                    continue

                typeikle = ikle.dtype
                typepoint = point_all.dtype
                point_new = np.empty((0, 3), dtype=typepoint)
                jpn0 = len(point_all) - 1
                iklenew = np.empty((0, 3), dtype=typeikle)
                ind_whole = np.arange(len(ikle), dtype=typeikle)

                water_height[water_height < min_height] = 0  # correcting the height of water  hw<0 or hw <min_height=> hw=0
                bhw = (water_height > 0).astype(np.int)
                ikle_bit = bhw[ikle]
                ikle_type = np.sum(ikle_bit, axis=1)  # list of meshes characters 0=dry 3=wet 1 or 2 = partially wet
                mikle_keep = ikle_type == 3
                mikle_keep2 = ikle_type != 0
                ipt_all_ok_wetdry = []
                # all meshes are entirely wet
                if all(mikle_keep):
                    print("Warning: The mesh of unit " + unit_name + " is entirely wet.")
                    iklekeep = ikle
                    point_all_ok = point_all
                    water_height_ok = water_height
                    velocity_ok = velocity
                    ind_whole = ind_whole  # TODO: full whole profile
                # all meshes are entirely dry
                elif not True in mikle_keep2:
                    print("Warning: The mesh of unit " + unit_name + " is entirely dry.")
                    continue
                # only the dry meshes are cut (but not the partially ones)
                elif not CutMeshPartialyDry:
                    mikle_keep = ikle_type != 0
                    iklekeep = ikle[mikle_keep, ...]
                    ind_whole = ind_whole[mikle_keep, ...]
                # we cut  the dry meshes and  the partially ones
                else:
                    jpn = jpn0
                    ind_whole2 = []
                    for i, iklec in enumerate(ikle):
                        #print("delta_ikle", delta_ikle)
                        if ikle_type[i] == 1 or ikle_type[i] == 2:
                            sumk, nboverdry, bkeep = 0, 0, True
                            ia, ib, ic = ikle[i]
                            pa = point_all[ia]
                            pb = point_all[ib]
                            pc = point_all[ic]
                            ha = water_height[ia]
                            hb = water_height[ib]
                            hc = water_height[ic]
                            p1, overdry, koverdry = linear_z_cross(pa, pb, ha, hb)
                            if overdry > 0:
                                nboverdry = nboverdry + 1
                                if koverdry > 1: bkeep = False
                            if len(p1) > 0:
                                sumk = sumk + 1
                            p2, overdry, koverdry = linear_z_cross(pb, pc, hb, hc)
                            if overdry > 0:
                                nboverdry = nboverdry + 1
                                if koverdry > 1: bkeep = False
                            if len(p2) > 0:
                                sumk = sumk + 2
                            p3, overdry, koverdry = linear_z_cross(pc, pa, hc, ha)
                            if overdry > 0:
                                nboverdry = nboverdry + 1
                                if koverdry > 1: bkeep = False
                            if len(p3) > 0:
                                sumk = sumk + 3
                            if nboverdry > 0:
                                if bkeep: mikle_keep[i] = True  # keeping the mesh we can't split
                            else:
                                if sumk == 5:
                                    point_new = np.append(point_new, np.array([p2, p3]), axis=0)
                                    if hc == 0:
                                        iklenew = np.append(iklenew, np.array([[ia, jpn + 1, jpn + 2], [ia, ib, jpn + 1]]), axis=0)
                                        ipt_all_ok_wetdry.extend([ia, ib])
                                        ind_whole2.extend([i, i])
                                    else:
                                        iklenew = np.append(iklenew, np.array([[jpn + 2, jpn + 1, ic]]), axis=0)
                                        ipt_all_ok_wetdry.append(ic)
                                        ind_whole2.append(i)
                                elif sumk == 4:
                                    point_new = np.append(point_new, np.array([p1, p3]), axis=0)
                                    if ha == 0:
                                        iklenew = np.append(iklenew, np.array([[jpn + 1, ib, jpn + 2], [ib, ic, jpn + 2]]), axis=0)
                                        ipt_all_ok_wetdry.extend([ic, ib])
                                        ind_whole2.extend([i, i])
                                    else:
                                        iklenew = np.append(iklenew, np.array([[ia, jpn + 1, jpn + 2]]), axis=0)
                                        ipt_all_ok_wetdry.append(ia)
                                        ind_whole2.append(i)
                                elif sumk == 3:
                                    point_new = np.append(point_new, np.array([p1, p2]), axis=0)
                                    if hb == 0:
                                        iklenew = np.append(iklenew, np.array([[jpn + 1, jpn + 2, ia], [ia, jpn + 2, ic]]), axis=0)
                                        ipt_all_ok_wetdry.extend([ia, ic])
                                        ind_whole2.extend([i, i])
                                    else:
                                        iklenew = np.append(iklenew, np.array([[ib, jpn + 2, jpn + 1]]), axis=0)
                                        ipt_all_ok_wetdry.append(ib)
                                        ind_whole2.append(i)
                                else:
                                    print(
                                        "Error: Impossible case during the cutting of mesh partially wet on the unit " + unit_name + ".")
                                    continue
                                jpn += 2

                    iklekeep = ikle[
                        mikle_keep, ...]  # only the original entirely wetted meshes and meshes we can't split( overwetted ones )
                    ind_whole = ind_whole[mikle_keep, ...]
                    ind_whole = np.append(ind_whole, np.asarray(ind_whole2, dtype=typeikle), axis=0)

                # all cases
                ipt_iklenew_unique = np.unique(iklekeep)

                if ipt_all_ok_wetdry:  # presence of partially wet/dry meshes cutted that we want
                    ipt_iklenew_unique = np.append(ipt_iklenew_unique, np.asarray(ipt_all_ok_wetdry, dtype=typeikle), axis=0)
                    ipt_iklenew_unique = np.unique(ipt_iklenew_unique)

                point_all_ok = point_all[ipt_iklenew_unique]  # select only the point of the selectionned meshes
                water_height_ok = water_height[ipt_iklenew_unique]
                velocity_ok = velocity[ipt_iklenew_unique]
                ipt_old_new = np.array([-1] * len(point_all), dtype=typeikle)
                for i, point_index in enumerate(ipt_iklenew_unique):
                    ipt_old_new[point_index] = i
                iklekeep2 = ipt_old_new[ikle]
                iklekeep = iklekeep2[mikle_keep, ...]  # only the meshes selected with the new point index
                if ipt_all_ok_wetdry:  # in case of partially wet/dry meshes
                    # delete dupplicate of the new point set
                    point_new_single, ipt_new_new2 = np.unique(point_new, axis=0, return_inverse=True)
                    lpns = len(point_new_single)
                    ipt_old_new = np.append(ipt_old_new, ipt_new_new2 + len(point_all_ok), axis=0)
                    iklekeep = np.append(iklekeep, ipt_old_new[iklenew], axis=0)
                    point_all_ok = np.append(point_all_ok, point_new_single, axis=0)
                    # beware that some new points can be doubles of  original ones
                    point_all_ok2, indices2 = np.unique(point_all_ok, axis=0, return_inverse=True)
                    nbdouble = 0
                    if len(point_all_ok2) != len(point_all_ok):
                        nbdouble = len(point_all_ok) - len(point_all_ok2)
                        iklekeep = indices2[iklekeep]
                        point_all_ok = point_all_ok2
                        print("Warning: while the cutting of mesh partially wet of the unit n°" + str(
                            unit_num) + " we have been forced to eliminate " + str(nbdouble) +
                              " duplicate(s) point(s) ")
                    if is_duplicates_mesh_and_point_on_one_unit(tin_array=iklekeep,
                                                                xyz_array=point_all_ok,
                                                                unit_num=unit_num,
                                                                case="after the cutting of mesh partially wet", checkpoint=False):
                        print("Warning: The mesh of unit " + unit_name + " is not loaded.")
                        continue

                    # all the new points added have water_height,velocity=0,0
                    water_height_ok = np.append(water_height_ok, np.zeros(lpns - nbdouble, dtype=water_height.dtype), axis=0)
                    velocity_ok = np.append(velocity_ok, np.zeros(lpns - nbdouble, dtype=velocity.dtype), axis=0)

                # erase old data
                self[reach_num][unit_num]["mesh"]["tin"] = iklekeep
                self[reach_num][unit_num]["mesh"]["i_whole_profile"] = ind_whole
                self[reach_num][unit_num]["node"]["xy"] = point_all_ok[:, :2]
                self[reach_num][unit_num]["node"]["z"] = point_all_ok[:, 2]

                # recreate new structured array
                nodes_dtypes_list = self[reach_num][unit_num]["node"]["data"].dtype
                node_data_array = np.zeros(shape=(water_height_ok.shape[0],),
                                           dtype=nodes_dtypes_list)  # structured array

                # TODO: remove specific variables replacement
                node_data_array["h"] = water_height_ok
                node_data_array["v"] = velocity_ok
                # # TODO: loop on variables
                # nodes_name_list = [element_list[0][1] for element_list in nodes_dtypes_list.descr]
                # for node_variable_name in nodes_name_list:
                #     node_data_array[node_variable_name] = array..

                # replace old by new structured array
                self[reach_num][unit_num]["node"]["data"] = node_data_array

                #  unit_list_cuted
                self.unit_list_cuted[reach_num].append(unit_name)

                # progress
                progress_value.value += int(deltaunit)

