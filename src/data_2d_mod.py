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
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
import sys
from copy import deepcopy

from src.manage_grid_mod import linear_z_cross, connectivity_mesh_table
from src.variable_unit_mod import HydraulicVariableUnitManagement, HydraulicVariableUnitList


class Data2d(list):
    """ A Data2d represent a list of reach """

    def __init__(self, reach_number=0, unit_list=[]):
        super().__init__()
        self.reach_number = reach_number
        self.unit_list = unit_list
        if self.reach_number and self.unit_list:
            for reach_number in range(self.reach_number):
                reach = Reach(reach_number, len(unit_list[reach_number]))
                self.append(reach)
        self.reach_list = []
        self.units_index = []
        # hvum
        self.hvum = HydraulicVariableUnitManagement()
        # data
        self.data_extent = (0, 0, 0, 0)
        self.data_height = 0.0
        self.data_width = 0.0
        # hs
        self.hs_summary_data = []
        self.sub_mapping_method = ""
        self.valid = True

    def __str__(self):
        string = self.__class__.__name__ + "\n" + \
                 str(self.__dict__) + "\n"
        for reach_number in range(len(self)):
            string = string + "reach n°" + str(reach_number) + ": unit_number = " + str(
                self[reach_number].unit_number) + " len(reach) = " + str(len(self[reach_number])) + "\n"
            for unit_number in range(len(self[reach_number])):
                string = string + "           unit " + str(unit_number) + " data = " + ", ".join(
                    self[reach_number][unit_number].get_variables_with_data()) + "\n"
        return string

    def __repr__(self):
        string = self.__class__.__name__ + "\n" + \
                 str(self.__dict__) + "\n"
        for reach_number in range(len(self)):
            string = string + "reach n°" + str(reach_number) + ": unit_number = " + str(
                self[reach_number].unit_number) + " len(reach) = " + str(len(self[reach_number])) + "\n"
            for unit_number in range(len(self[reach_number])):
                string = string + "           unit " + str(unit_number) + " data = " + ", ".join(
                    self[reach_number][unit_number].get_variables_with_data()) + "\n"
        return string

    def get_informations(self):
        self.reach_number = len(self)
        for reach_number in range(self.reach_number):
            self[reach_number].unit_number = len(self[reach_number])
            for unit_number in range(len(self[reach_number])):
                self[reach_number][unit_number].reach_number = reach_number
                self[reach_number][unit_number].unit_number = unit_number

    def add_reach(self, data_2d_new, reach_num_list):
        for reach_number in reach_num_list:
            self.append(data_2d_new[reach_num_list[reach_number]])

        # update attrs
        self.get_informations()
        self.hvum = data_2d_new.hvum

    def add_unit(self, data_2d_new, reach_number):
        # if not reach
        if not self.reach_number:
            self.append(Reach())
        self[reach_number].extend(data_2d_new[reach_number])

        self.get_informations()
        self.hvum = data_2d_new.hvum
        self.hyd_equation_type = data_2d_new.hyd_equation_type
        self.hyd_calculation_method = data_2d_new.hyd_calculation_method

    def get_dimension(self):
        # get extent
        xMin = []
        xMax = []
        yMin = []
        yMax = []

        # for each reach
        for reach_number in range(self.reach_number):
            # for each unit
            for unit_number in range(len(self[reach_number])):
                # extent
                xMin.append(min(self[reach_number][unit_number]["node"]["xy"][:, 0]))
                xMax.append(max(self[reach_number][unit_number]["node"]["xy"][:, 0]))
                yMin.append(min(self[reach_number][unit_number]["node"]["xy"][:, 1]))
                yMax.append(max(self[reach_number][unit_number]["node"]["xy"][:, 1]))
                # data min/max
                for variable in self.hvum.hdf5_and_computable_list.no_habs():
                    if variable.hdf5:
                        if min(self[reach_number][unit_number][variable.position]["data"][
                                   variable.name]) < variable.min:
                            variable.min = min(
                                self[reach_number][unit_number][variable.position]["data"][variable.name])
                        if max(self[reach_number][unit_number][variable.position]["data"][
                                   variable.name]) > variable.max:
                            variable.max = max(
                                self[reach_number][unit_number][variable.position]["data"][variable.name])

        # get extent
        xMin = min(xMin)
        xMax = max(xMax)
        yMin = min(yMin)
        yMax = max(yMax)
        self.data_extent = (xMin, yMin, xMax, yMax)
        self.data_height = xMax - xMin
        self.data_width = yMax - yMin

    def get_only_mesh(self):
        """
        retrun whole_profile from original data2d
        """
        whole_profile = Data2d()
        for reach_number in range(self.reach_number):
            reach = Reach()
            for unit_number in range(len(self[reach_number])):
                unit_dict = Unit(reach_number,
                                 unit_number)
                unit_dict["mesh"]["tin"] = self[reach_number][unit_number]["mesh"]["tin"]
                unit_dict["node"]["xy"] = self[reach_number][unit_number]["node"]["xy"]
                unit_dict["node"]["z"] = self[reach_number][unit_number]["node"]["data"][self.hvum.z.name]
                # append by unit
                reach.append(unit_dict)
                # append by reach
            whole_profile.append(reach)

        whole_profile.get_informations()

        return whole_profile

    def get_light_data_2d(self):
        light_data_2d = Data2d(self.reach_number,
                               self.unit_list)
        light_data_2d.__dict__ = self.__dict__.copy()
        # for each reach
        for reach_number in range(self.reach_number):
            # for each unit
            for unit_number in range(len(self[reach_number])):
                light_data_2d[reach_number][unit_number].__dict__ = self[reach_number][unit_number].__dict__.copy()
        return light_data_2d

    def get_hyd_varying_xy_and_z_index(self):
        # hyd_varying_mesh and hyd_unit_z_equal?
        hyd_varying_xy_index = []
        hyd_varying_z_index = []
        for reach_number in range(self.reach_number):
            hyd_varying_xy_index.append([])
            hyd_varying_z_index.append([])
            it_equality = 0
            for unit_number in range(len(self[reach_number])):
                if unit_number == 0:
                    hyd_varying_xy_index[reach_number].append(it_equality)
                    hyd_varying_z_index[reach_number].append(it_equality)
                if unit_number > 0:
                    # xy
                    if np.array_equal(self[reach_number][unit_number]["node"]["xy"],
                                      self[reach_number][it_equality]["node"]["xy"]):  # equal
                        hyd_varying_xy_index[reach_number].append(it_equality)
                    else:
                        it_equality = unit_number
                        hyd_varying_xy_index[reach_number].append(it_equality)  # diff
                    # z
                    if np.array_equal(self[reach_number][unit_number]["node"]["z"],
                                      self[reach_number][it_equality]["node"]["z"]):  # equal
                        hyd_varying_z_index[reach_number].append(it_equality)
                    else:
                        it_equality = unit_number
                        hyd_varying_z_index[reach_number].append(it_equality)  # diff
        return hyd_varying_xy_index, hyd_varying_z_index

    def reduce_to_first_unit_by_reach(self):
        for reach_number in range(self.reach_number):
            new_reach = Reach(reach_number,
                              0)
            new_reach.append(self[reach_number][0])
            self[reach_number] = new_reach
        self.get_informations()

    def rename_substrate_column_data(self):
        for reach_number in range(self.reach_number):
            for unit_number in range(len(self[reach_number])):
                self[reach_number][unit_number]["mesh"][
                    "data"].columns = self.hvum.hdf5_and_computable_list.hdf5s().subs().names()

    def set_sub_cst_value(self, data_2d_sub):
        # mixing variables
        self.hvum.hdf5_and_computable_list.extend(data_2d_sub.hvum.hdf5_and_computable_list)
        self.sub_mapping_method = "constant"
        self.sub_filename_source = data_2d_sub.filename
        self.sub_path_filename_source = data_2d_sub.path_filename_source
        self.sub_classification_code = data_2d_sub.sub_classification_code
        self.sub_classification_method = data_2d_sub.sub_classification_method
        # for each reach
        for reach_number in range(self.reach_number):
            # for each unit
            for unit_number in range(len(self[reach_number])):
                try:
                    default_data = np.array(data_2d_sub.sub_default_values,
                                            dtype=self.hvum.sub_dom.dtype)
                    sub_array = np.repeat([default_data],
                                          self[reach_number][unit_number]["mesh"]["tin"].shape[0],
                                          0)
                except ValueError or TypeError:
                    print(
                        'Error: Merging failed. No numerical data in substrate. (only float or int accepted for now).')
                    return
                try:
                    # add sub data to dict
                    for sub_class_num, sub_class_name in enumerate(
                            data_2d_sub.hvum.hdf5_and_computable_list.hdf5s().names()):
                        self[reach_number][unit_number]["mesh"]["data"][sub_class_name] = sub_array[:, sub_class_num]
                except IndexError:
                    print("Error: Default substrate data is not coherent with the substrate classification code. "
                          "Change it in the text file accompanying the input file.")
                    return

                # area ?
                if self.hvum.area.name not in self[reach_number][unit_number]["mesh"]["data"].columns:
                    pa = self[reach_number][unit_number]["node"]["xy"][
                        self[reach_number][unit_number]["mesh"]["tin"][:, 0]]
                    pb = self[reach_number][unit_number]["node"]["xy"][
                        self[reach_number][unit_number]["mesh"]["tin"][:, 1]]
                    pc = self[reach_number][unit_number]["node"]["xy"][
                        self[reach_number][unit_number]["mesh"]["tin"][:, 2]]
                    area = 0.5 * abs(
                        (pb[:, 0] - pa[:, 0]) * (pc[:, 1] - pa[:, 1]) -
                        (pc[:, 0] - pa[:, 0]) * (pb[:, 1] - pa[:, 1]))  # get area2
                    self[reach_number][unit_number]["mesh"]["data"]["area"] = area
                    # variable
                    self.hvum.area.hdf5 = True
                    self.hvum.hdf5_and_computable_list.append(self.hvum.area)
                else:
                    area = self[reach_number][unit_number]["mesh"]["data"][self.hvum.area.name].to_numpy()

                self[reach_number][unit_number].total_wet_area = np.sum(area)

    def set_reach_list(self, reach_list):
        self.reach_list = reach_list
        for reach_number in range(self.reach_number):
            for unit_number in range(len(self[reach_number])):
                reach_name = self.reach_list[reach_number]
                self[reach_number].reach_name = reach_name
                self[reach_number][unit_number].reach_name = reach_name

    def set_unit_list(self, unit_list):
        self.unit_list = deepcopy(unit_list)
        for reach_number in range(self.reach_number):
            self[reach_number].unit_number = len(self[reach_number])
            for unit_number in range(len(self[reach_number])):
                self[reach_number][unit_number].unit_name = self.unit_list[reach_number][unit_number].replace(":", "_").replace(" ", "_")
                self[reach_number][unit_number].unit_number = unit_number
            self.units_index.append(list(range(len(self[reach_number]))))

    def remove_unit_from_unit_index_list(self, unit_index_to_remove_list, reach_number=0):
        # remove duplicates
        unit_index_to_remove_list = list(set(unit_index_to_remove_list))

        # unit_dict removed
        for unit_index_to_remove in reversed(unit_index_to_remove_list):
            self[reach_number].pop(unit_index_to_remove)
            # unit_name_list updated
            print("Warning: The mesh of unit " + str(self.unit_list[reach_number][unit_index_to_remove]) + " of reach n°" + str(reach_number) + " is entirely dry.")
            self.unit_list[reach_number].pop(unit_index_to_remove)
        self.get_informations()

    def check_duplicates(self):
        # for each reach
        for reach_number in range(self.reach_number):
            unit_to_remove_list = []
            # for each unit
            for unit_number in range(len(self[reach_number])):
                # is_duplicates_mesh_or_point : only in xy are removed (in xyz only warning print)
                if self[reach_number][unit_number].is_duplicates_mesh_or_point(case="at reading",
                                                                               mesh=True,
                                                                               node=True):
                    unit_to_remove_list.append(unit_number)
                    continue

            # remove_unit_from_unit_index_list
            if unit_to_remove_list:
                self.remove_unit_from_unit_index_list(unit_to_remove_list, reach_number)

    def remove_unused_node(self):
        # for each reach
        for reach_number in range(self.reach_number):
            # for each unit
            for unit_number in range(len(self[reach_number])):
                self[reach_number][unit_number].remove_unused_node()

    def set_min_height_to_0(self, min_height):
        self.hyd_min_height = min_height
        # for each reach
        for reach_number in range(self.reach_number):
            # for each unit
            for unit_number in range(len(self[reach_number])):
                """ node (always) """
                self[reach_number][unit_number]["node"]["data"].loc[self[reach_number][unit_number]["node"]["data"][
                                                                        self.hvum.h.name] < min_height, self.hvum.hdf5_and_computable_list.nodes().depend_on_hs().names()] = 0.0

                """ mesh """
                if self.hvum.h.name in self.hvum.hdf5_and_computable_list.meshs().names():
                    self[reach_number][unit_number]["mesh"]["data"].loc[self[reach_number][unit_number]["mesh"]["data"][
                                                                            self.hvum.h.name] < min_height, self.hvum.hdf5_and_computable_list.meshs().depend_on_hs().names()] = 0.0

    def remove_dry_mesh(self):
        self.get_informations()

        # for each reach
        for reach_number in range(self.reach_number):
            unit_to_remove_list = []
            # for each unit
            for unit_number in range(len(self[reach_number])):
                # get data from dict
                ikle = self[reach_number][unit_number]["mesh"]["tin"]
                point_all = np.column_stack((self[reach_number][unit_number]["node"][self.hvum.xy.name],
                                             self[reach_number][unit_number]["node"]["data"][
                                                 self.hvum.z.name].to_numpy()))
                water_height = self[reach_number][unit_number]["node"]["data"][self.hvum.h.name].to_numpy()
                ind_whole = self[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name]

                # Finite volume
                if self.hvum.h.name in self[reach_number][unit_number]["mesh"]["data"].columns:
                    ikle_type = np.array(self[reach_number][unit_number]["mesh"]["data"][self.hvum.h.name] == 0)
                    mikle_keep = ikle_type != True
                # Finite element
                else:
                    bhw = (water_height > 0).astype(self.hvum.i_whole_profile.dtype)
                    ikle_bit = bhw[ikle]
                    ikle_type = np.sum(ikle_bit, axis=1)  # list of meshes characters 0=dry 3=wet 1 or 2 = partially wet
                    mikle_keep = ikle_type != 0

                # all meshes are entirely dry
                if not True in mikle_keep:
                    unit_to_remove_list.append(unit_number)
                    continue

                # mesh_removed_nb
                mesh_removed_nb = np.size(mikle_keep) - np.count_nonzero(mikle_keep)
                if mesh_removed_nb:
                    print("Warning: " + str(mesh_removed_nb) + " dry mesh(s) have been removed in unit " + str(
                        self[reach_number][unit_number].unit_name) + ".")

                # only the wet meshes (and the partially ones)
                iklekeep = ikle[mikle_keep, ...]
                ind_whole = ind_whole[mikle_keep, ...]
                ipt_iklenew_unique = np.unique(iklekeep)
                point_all_ok = point_all[ipt_iklenew_unique]  # select only the point of the selectionned meshes

                ipt_old_new = np.array([-1] * len(point_all), dtype=self.hvum.tin.dtype)
                for i, point_index in enumerate(ipt_iklenew_unique):
                    ipt_old_new[point_index] = i
                iklekeep2 = ipt_old_new[ikle]
                iklekeep = iklekeep2[mikle_keep, ...]  # only the meshes selected with the new point index

                # mesh data
                self[reach_number][unit_number]["mesh"][self.hvum.tin.name] = iklekeep
                self[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name] = ind_whole
                if not self[reach_number][unit_number]["mesh"]["data"].empty:
                    self[reach_number][unit_number]["mesh"]["data"] = \
                        self[reach_number][unit_number]["mesh"]["data"].iloc[
                            mikle_keep]

                # node data
                self[reach_number][unit_number]["node"]["data"] = self[reach_number][unit_number]["node"]["data"].iloc[
                    ipt_iklenew_unique]
                self[reach_number][unit_number]["node"][self.hvum.xy.name] = point_all_ok[:, :2]

            if unit_to_remove_list:
                self.remove_unit_from_unit_index_list(unit_to_remove_list, reach_number)

    def semi_wetted_mesh_cutting(self, progress_value, delta_file):
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
        self.hyd_cuted_mesh_partialy_dry = True
        self.get_informations()

        # progress
        delta_reach = delta_file / self.reach_number

        # for each reach
        for reach_number in range(self.reach_number):

            # progress
            delta_unit = delta_reach / len(self[reach_number])

            unit_to_remove_list = []

            # for each unit
            for unit_number in range(len(self[reach_number])):
                # get data from dict
                ikle = self[reach_number][unit_number]["mesh"]["tin"]
                point_all = np.column_stack((self[reach_number][unit_number]["node"][self.hvum.xy.name],
                                             self[reach_number][unit_number]["node"]["data"][
                                                 self.hvum.z.name].to_numpy()))
                water_height = self[reach_number][unit_number]["node"]["data"][self.hvum.h.name].to_numpy()
                velocity = self[reach_number][unit_number]["node"]["data"][self.hvum.v.name].to_numpy()

                point_new = np.empty((0, 3), dtype=self.hvum.xy.dtype)
                jpn0 = len(point_all) - 1
                iklenew = np.empty((0, 3), dtype=self.hvum.i_whole_profile.dtype)
                ind_whole = np.arange(len(ikle), dtype=self.hvum.i_whole_profile.dtype)

                bhw = (water_height > 0).astype(self.hvum.i_whole_profile.dtype)
                ikle_bit = bhw[ikle]
                ikle_type = np.sum(ikle_bit, axis=1)  # list of meshes characters 0=dry 3=wet 1 or 2 = partially wet
                mikle_keep = ikle_type == 3
                ipt_all_ok_wetdry = []
                # all meshes are entirely wet
                if all(mikle_keep):
                    print("Warning: The mesh of unit " + self[reach_number][unit_number].unit_name + " of reach n°" + str(reach_number) + " doesn't have any mesh partialy wet.")
                    # progress
                    progress_value.value = progress_value.value + delta_unit
                    continue
                # we cut the dry meshes and  the partially ones
                else:
                    jpn = jpn0
                    ind_whole2 = []
                    for i, iklec in enumerate(ikle):
                        # print("delta_ikle", delta_ikle)
                        if ikle_type[i] == 1 or ikle_type[i] == 2:
                            sumk, nboverdry, bkeep = 0, 0, True
                            ia, ib, ic = ikle[i]
                            pa = np.array(point_all[ia])
                            pb = np.array(point_all[ib])
                            pc = np.array(point_all[ic])
                            txyz = np.min((pa, pb, pc), axis=0)  # tranlation in order to reduce numerical problems
                            pa -= txyz
                            pb -= txyz
                            pc -= txyz
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
                                    point_new = np.append(point_new, np.array([p2+txyz, p3+txyz]), axis=0)
                                    if hc == 0:
                                        iklenew = np.append(iklenew,
                                                            np.array([[ia, jpn + 1, jpn + 2], [ia, ib, jpn + 1]]),
                                                            axis=0)
                                        ipt_all_ok_wetdry.extend([ia, ib])
                                        ind_whole2.extend([i, i])
                                    else:
                                        iklenew = np.append(iklenew, np.array([[jpn + 2, jpn + 1, ic]]), axis=0)
                                        ipt_all_ok_wetdry.append(ic)
                                        ind_whole2.append(i)
                                elif sumk == 4:
                                    point_new = np.append(point_new, np.array([p1+txyz, p3+txyz]), axis=0)
                                    if ha == 0:
                                        iklenew = np.append(iklenew,
                                                            np.array([[jpn + 1, ib, jpn + 2], [ib, ic, jpn + 2]]),
                                                            axis=0)
                                        ipt_all_ok_wetdry.extend([ic, ib])
                                        ind_whole2.extend([i, i])
                                    else:
                                        iklenew = np.append(iklenew, np.array([[ia, jpn + 1, jpn + 2]]), axis=0)
                                        ipt_all_ok_wetdry.append(ia)
                                        ind_whole2.append(i)
                                elif sumk == 3:
                                    point_new = np.append(point_new, np.array([p1+txyz, p2+txyz]), axis=0)
                                    if hb == 0:
                                        iklenew = np.append(iklenew,
                                                            np.array([[jpn + 1, jpn + 2, ia], [ia, jpn + 2, ic]]),
                                                            axis=0)
                                        ipt_all_ok_wetdry.extend([ia, ic])
                                        ind_whole2.extend([i, i])
                                    else:
                                        iklenew = np.append(iklenew, np.array([[ib, jpn + 2, jpn + 1]]), axis=0)
                                        ipt_all_ok_wetdry.append(ib)
                                        ind_whole2.append(i)
                                else:
                                    print(
                                        "Error: Impossible case during the cutting of mesh partially wet on the unit " + self[reach_number][
                            unit_number].unit_name + ".")
                                    unit_to_remove_list.append(unit_number)
                                    continue
                                jpn += 2

                    # only the original entirely wetted meshes and meshes we can't split( overwetted ones )
                    iklekeep = ikle[mikle_keep, ...]
                    ind_whole = ind_whole[mikle_keep, ...]
                    ind_whole = np.append(ind_whole, np.asarray(ind_whole2, dtype=self.hvum.tin.dtype), axis=0)
                    i_split = np.repeat(0, ind_whole.shape[0]).astype(self.hvum.i_split.dtype)

                # all cases
                ipt_iklenew_unique = np.unique(iklekeep)

                if ipt_all_ok_wetdry:  # presence of partially wet/dry meshes cutted that we want
                    ipt_iklenew_unique = np.append(ipt_iklenew_unique,
                                                   np.asarray(ipt_all_ok_wetdry, dtype=self.hvum.tin.dtype), axis=0)
                    ipt_iklenew_unique = np.unique(ipt_iklenew_unique)

                point_all_ok = point_all[ipt_iklenew_unique]  # select only the point of the selectionned meshes
                water_height_ok = water_height[ipt_iklenew_unique]
                velocity_ok = velocity[ipt_iklenew_unique]

                ipt_old_new = np.array([-1] * len(point_all), dtype=self.hvum.tin.dtype)
                for i, point_index in enumerate(ipt_iklenew_unique):
                    ipt_old_new[point_index] = i
                iklekeep2 = ipt_old_new[ikle]
                iklekeep = iklekeep2[mikle_keep, ...]  # only the meshes selected with the new point index
                if ipt_all_ok_wetdry:  # in case of partially wet/dry meshes
                    # delete dupplicate of the new point set
                    point_new_single, ipt_new_new2 = np.unique(point_new, axis=0, return_inverse=True)
                    lpns = len(point_new_single)
                    ipt_old_new = np.append(ipt_old_new, ipt_new_new2 + len(point_all_ok), axis=0)
                    i_split = np.append(np.repeat(0, iklekeep.shape[0]).astype(self.hvum.i_split.dtype),
                                        np.repeat(1, ipt_old_new[iklenew].shape[0]).astype(self.hvum.i_split.dtype),
                                        axis=0)
                    iklekeep = np.append(iklekeep, ipt_old_new[iklenew], axis=0)
                    point_all_ok = np.append(point_all_ok, point_new_single, axis=0)
                    # beware that some new points can be doubles of  original ones
                    point_all_ok2, indices2 = np.unique(point_all_ok, axis=0, return_inverse=True)
                    nbdouble = 0
                    if len(point_all_ok2) != len(point_all_ok):
                        nbdouble = len(point_all_ok) - len(point_all_ok2)
                        iklekeep = indices2[iklekeep]
                        point_all_ok = point_all_ok2
                        print("Warning: While the cutting of mesh partially wet of the unit " + self[reach_number][
                            unit_number].unit_name + " of reach n°" + str(
                            reach_number) + " we have been forced to eliminate " + str(nbdouble) +
                              " duplicate(s) point(s) ")

                    # # check if mesh duplicates presence
                    # u, c = np.unique(self[reach_number][unit_number]["mesh"]["tin"], return_counts=True, axis=0)
                    # dup = u[c > 1]
                    # if len(dup) != 0:
                    #     print("Warning: The mesh of unit " + self[reach_number][unit_number].unit_name + " is not loaded (" + str(len(dup)) +
                    #           " duplicate(s) mesh(s) during the cutting of mesh partially wet : " +
                    #           ", ".join([str(mesh_str) for mesh_str in dup.tolist()]) + ").")
                    #     unit_to_remove_list.append(unit_number)
                    #     continue

                    # TODO: v=0 is applicable to torrential flows ?
                    # all the new points added have water_height,velocity=0,0
                    water_height_ok = np.append(water_height_ok, np.zeros(lpns - nbdouble, dtype=water_height.dtype),
                                                axis=0)
                    velocity_ok = np.append(velocity_ok, np.zeros(lpns - nbdouble, dtype=velocity.dtype), axis=0)

                    # temp
                    if self.hvum.temp.name in self.hvum.hdf5_and_computable_list.nodes().names():
                        # inter_height = scipy.interpolate.griddata(xy, values, point_p, method='linear')
                        temp_data = griddata(points=self[reach_number][unit_number]["node"][self.hvum.xy.name],
                                             values=self[reach_number][unit_number]["node"]["data"][
                                                 self.hvum.temp.name].to_numpy(),
                                             xi=point_new_single[:, :2],
                                             method="linear")

                    # change all node dataframe
                    self[reach_number][unit_number]["node"]["data"] = \
                        self[reach_number][unit_number]["node"]["data"].iloc[
                            ipt_iklenew_unique]
                    if self.hvum.temp.name in self.hvum.hdf5_and_computable_list.nodes().names():
                        temp_ok = np.append(self[reach_number][unit_number]["node"]["data"][self.hvum.temp.name],
                                            temp_data,
                                            axis=0)

                    # new pandas dataframe (to be added to the end)
                    nan_pd = pd.DataFrame(np.nan, index=np.arange(lpns - nbdouble),
                                          columns=self[reach_number][unit_number]["node"]["data"].columns.values)
                    self[reach_number][unit_number]["node"]["data"] = self[reach_number][unit_number]["node"][
                        "data"].append(nan_pd)
                    self[reach_number][unit_number]["node"]["data"][self.hvum.h.name] = water_height_ok
                    self[reach_number][unit_number]["node"]["data"][self.hvum.v.name] = velocity_ok
                    self[reach_number][unit_number]["node"]["data"][self.hvum.z.name] = point_all_ok[:, 2]
                    if self.hvum.temp.name in self.hvum.hdf5_and_computable_list.nodes().names():
                        self[reach_number][unit_number]["node"]["data"][self.hvum.temp.name] = temp_ok
                else:
                    self[reach_number][unit_number]["node"]["data"] = \
                        self[reach_number][unit_number]["node"]["data"].iloc[
                            ipt_iklenew_unique]

                # mesh data
                if not self[reach_number][unit_number]["mesh"]["data"].empty:
                    self[reach_number][unit_number]["mesh"]["data"] = \
                        self[reach_number][unit_number]["mesh"]["data"].iloc[ind_whole]
                self[reach_number][unit_number]["mesh"][self.hvum.tin.name] = iklekeep
                self[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name] = \
                self[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name][ind_whole]
                self[reach_number][unit_number]["mesh"]["data"][self.hvum.i_split.name] = i_split  # i_split
                if not self.hvum.i_split.name in self.hvum.hdf5_and_computable_list.names():
                    self.hvum.i_split.position = "mesh"
                    self.hvum.i_split.hdf5 = True
                    self.hvum.hdf5_and_computable_list.append(self.hvum.i_split)

                # node data
                self[reach_number][unit_number]["node"][self.hvum.xy.name] = point_all_ok[:, :2]
                self[reach_number][unit_number]["node"]["data"] = self[reach_number][unit_number]["node"][
                    "data"].fillna(
                    0)  # fillna with 0

                # is_duplicates_mesh_or_point
                if self[reach_number][unit_number].is_duplicates_mesh_or_point(
                        case="after the cutting of mesh partially wet",
                        mesh=True,
                        node=True):
                    unit_to_remove_list.append(unit_number)
                    continue

                # progress
                progress_value.value = progress_value.value + delta_unit

            if unit_to_remove_list:
                self.remove_unit_from_unit_index_list(unit_to_remove_list, reach_number)

        self.get_informations()

    def super_cut(self, level, coeff_std, bremoveisolatedmeshes=True):
        """
        Taking off bank hydraulic aberrations
        Supercut function returns bmeshinvalid (an array of booleans) TRUE for a mesh index that is considered a Hydraulic Aberration
        :param bremoveisolatedmeshes: TRUE to remove isolated mesh
        :param level: to be determined by the user to determine the number of contacts meshes where the research is done (by default 3)
        :param coeff_std : to be determined by the user (by default 3)
        every index of loca represents a mesh index of the tin with 3 values in column indexing the mesh indexes in contact ; -1 if not
        countcontact indicates the number of contacts for each mesh
        """
        unit_to_remove_list = []
        # for all reach
        for reach_number in range(0, self.reach_number):
            # for all units
            for unit_number in range(0, self[reach_number].unit_number):
                # connectivity_mesh_table to get the neighbors of the mesh and the number of contact neighbors
                loca, countcontact = connectivity_mesh_table(self[reach_number][unit_number]["mesh"]["tin"])
                if loca is None and countcontact is None:
                    unit_to_remove_list.append(unit_number)
                    continue

                # note that if the  value for a mesh index in countcontact is 0 the mesh is isolated
                countcontact = countcontact.flatten()
                countcontact12 = (countcontact > 0) & (countcontact != 3)  # to get the information TRUE if the mesh index is on the edge

                # c_mesh_max_slope_surface
                self[reach_number][unit_number].c_mesh_max_slope_surface()
                #standard deviation method
                slope_std = self[reach_number][unit_number]["mesh"]["data"][self.hvum.max_slope_surface.name].std()
                slope_mean = self[reach_number][unit_number]["mesh"]["data"][self.hvum.max_slope_surface.name].mean()
                anomaly_cut_off = slope_std * coeff_std
                limit = slope_mean + anomaly_cut_off
                np_max_slope_surface = self[reach_number][unit_number]["mesh"]["data"][self.hvum.max_slope_surface.name].to_numpy()
                bmeshinvalid = np.full((len(self[reach_number][unit_number]["mesh"]["tin"]),), False)

                if bremoveisolatedmeshes:
                    bmeshinvalid = np.logical_xor(bmeshinvalid, (countcontact == 0))  # TO remove isolated mesh
                for j in range(len(self[reach_number][unit_number]["mesh"]["tin"])):
                    if countcontact12[j]: #only the mesh at the edge
                        a = set(loca[j][:countcontact[j]]) | {j}
                        aa = set(loca[j][:countcontact[j]])
                        for ilevel in range(level):
                            b = set()
                            for ij in aa:
                                b = b | set(loca[ij][:countcontact[ij]])
                            aa = b - a
                            a = a | b
                        surroundingmesh = list(a) # the edge mesh and its neighbors up to the indicated level
                        surroundingmesh3 = np.array(surroundingmesh)
                        penta3 = np_max_slope_surface[surroundingmesh3]
                        for i in range(len(penta3)):
                            if penta3[i] > limit:
                                bmeshinvalid[surroundingmesh3[i]] = True

                # mesh data
                self[reach_number][unit_number]["mesh"][self.hvum.tin.name] = self[reach_number][unit_number]["mesh"][self.hvum.tin.name][~bmeshinvalid]
                self[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name] = self[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name][~bmeshinvalid]
                if not self[reach_number][unit_number]["mesh"]["data"].empty:
                    self[reach_number][unit_number]["mesh"]["data"] = self[reach_number][unit_number]["mesh"]["data"][~bmeshinvalid]

                if np.sum(bmeshinvalid):
                    print("Warning: The mesh of the unit " + self[reach_number][unit_number].unit_name + " has " + str(np.sum(bmeshinvalid)) + " mesh bank hydraulic aberations(s). The latter has been removed.")

            if unit_to_remove_list:
                self.remove_unit_from_unit_index_list(unit_to_remove_list, reach_number)

    def compute_variables(self, variable_computable_list):
        """
        Compute all necessary variables.
        :param node_variable_list:
        :param mesh_variable_list:
        :return:
        """
        if not type(variable_computable_list) == HydraulicVariableUnitList and type(variable_computable_list) == list:
            variable_computable_list2 = HydraulicVariableUnitList()
            variable_computable_list2.extend(variable_computable_list)
            variable_computable_list = variable_computable_list2

        # for variable
        for variable in variable_computable_list:
            # for all reach
            for reach_number in range(self.reach_number):
                # for all units
                for unit_number in range(len(self[reach_number])):
                    # compute only on preloaded data unit
                    if self[reach_number][unit_number].get_variables_with_data():
                        if variable.position == "node":
                            # compute water_level
                            if variable.name == self.hvum.level.name:
                                self[reach_number][unit_number].c_node_water_level()
                            # compute froude
                            elif variable.name == self.hvum.froude.name:
                                self[reach_number][unit_number].c_node_froude()
                            # compute hydraulic_head
                            elif variable.name == self.hvum.hydraulic_head.name:
                                self[reach_number][unit_number].c_node_hydraulic_head()
                            # compute hydraulic_head_level
                            elif variable.name == self.hvum.hydraulic_head_level.name:
                                self[reach_number][unit_number].c_node_hydraulic_head_level()
                            # compute conveyance
                            elif variable.name == self.hvum.conveyance.name:
                                self[reach_number][unit_number].c_node_conveyance()
                            # compute shear_stress
                            elif variable.name == self.hvum.shear_stress.name:
                                self[reach_number][unit_number].c_node_shear_stress()
                        elif variable.position == "mesh":
                            # c_mesh_elevation
                            if variable.name == self.hvum.z.name:
                                self[reach_number][unit_number].c_mesh_elevation()
                            # compute height
                            elif variable.name == self.hvum.h.name:
                                self[reach_number][unit_number].c_mesh_height()
                            # compute velocity
                            elif variable.name == self.hvum.v.name:
                                self[reach_number][unit_number].c_mesh_velocity()
                            # compute shear_stress
                            elif variable.name == self.hvum.shear_stress.name:
                                self[reach_number][unit_number].c_mesh_shear_stress()
                            # compute shear_stress_beta
                            elif variable.name == self.hvum.shear_stress_beta.name:
                                self[reach_number][unit_number].c_mesh_shear_stress_beta()
                            # compute water_level
                            elif variable.name == self.hvum.level.name:
                                self[reach_number][unit_number].c_mesh_water_level()
                            # compute froude
                            elif variable.name == self.hvum.froude.name:
                                self[reach_number][unit_number].c_mesh_froude()
                            # compute hydraulic_head
                            elif variable.name == self.hvum.hydraulic_head.name:
                                self[reach_number][unit_number].c_mesh_hydraulic_head()
                            # compute hydraulic_head_level
                            elif variable.name == self.hvum.hydraulic_head_level.name:
                                self[reach_number][unit_number].c_mesh_hydraulic_head_level()
                            # compute conveyance
                            elif variable.name == self.hvum.conveyance.name:
                                self[reach_number][unit_number].c_mesh_conveyance()
                            # compute max_slope_bottom
                            elif variable.name == self.hvum.max_slope_bottom.name:
                                self[reach_number][unit_number].c_mesh_max_slope_bottom()
                            # compute max_slope_surface
                            elif variable.name == self.hvum.max_slope_surface.name:
                                self[reach_number][unit_number].c_mesh_max_slope_surface()
                            # compute max_slope_energy
                            elif variable.name == self.hvum.max_slope_energy.name:
                                self[reach_number][unit_number].c_mesh_max_slope_energy()
                            # compute area
                            elif variable.name == self.hvum.area.name:
                                self[reach_number][unit_number].c_mesh_area()
                            # compute coarser
                            elif variable.name == self.hvum.sub_coarser.name:
                                self[reach_number][unit_number].c_mesh_sub_coarser()
                            # compute dominant
                            elif variable.name == self.hvum.sub_dom.name:
                                self[reach_number][unit_number].c_mesh_sub_dom()
                            # area
                            elif variable.name == self.hvum.area.name:
                                self[reach_number][unit_number].c_mesh_area()
                            else:
                                self[reach_number][unit_number].c_mesh_mean_from_node_values(variable.name)

    def remove_null_area(self):
        # for all reach
        for reach_number in range(0, self.reach_number):
            # for all units
            for unit_number in range(len(self[reach_number])):
                self[reach_number][unit_number].remove_null_area()

    def neighbouring_triangles(self, tin, interest_mesh_indices=None):
        """
        Accyrately lists the neighbours of each triangle from the subsection of the mesh we are interested in.
        For the rest of the triangles, the returned list will only contain the neighbours which belong to the interesting subsection
        :param tin:
        :param bank_mesh_indices:
        :return:
        """
        if interest_mesh_indices is None:
            interest_mesh_indices = np.array(range(len(tin)))
        # seg1 = tin[:, 0:2].reshape((len(tin), 1, 2))
        # seg2 = tin[:, 1:3].reshape((len(tin), 1, 2))
        # seg3 = tin[:, 0::2].reshape((len(tin), 1, 2))
        # segments = np.concatenate((seg1, seg2, seg3), axis=1)
        interest_tin = tin[interest_mesh_indices]
        seg1 = interest_tin[:, 0:2]
        seg2 = interest_tin[:, 1:3]
        seg3 = interest_tin[:, 0::2]
        triangle_count = len(interest_tin)
        segments = np.concatenate((seg1, seg2, seg3), axis=0)
        segments_unique, inverse_indices, counts = np.unique(segments, axis=0, return_inverse=True, return_counts=True)
        neighbouring_triangles = [[] for _ in range(len(tin))]
        neighbour_count = np.zeros(len(tin), dtype=np.int64)
        for i in range(len(segments_unique)):
            if counts[i] == 2:
                tri_neighbours = interest_mesh_indices[np.where(inverse_indices == i)[0] % triangle_count]
                neighbouring_triangles[tri_neighbours[0]].append(tri_neighbours[1])
                neighbouring_triangles[tri_neighbours[1]].append(tri_neighbours[0])
                neighbour_count[tri_neighbours] += 1

        return neighbouring_triangles, neighbour_count

        segment_to_triangle = {}  # dict where each key is a tuple of vertices (v1,v2) and the content is a list of triangles sharing the segment (v1,v2)
        triangle_count = {}  # dict whose keys are the same as above, and the content is the number of triangles which contain each segment

        segment_sides_found = np.zeros((len(tin), 3), dtype=bool)
        neighbouring_triangles = [[] for _ in range(len(tin))]
        neighbour_count = np.zeros(len(tin), dtype=np.int64)
        for tri_i in interest_mesh_indices:
            for segment_i in range(3):
                if not segment_sides_found[tri_i, segment_i]:
                    neighbour, matching_segment = np.nonzero((segments == segments[tri_i, segment_i]).all(axis=2))
                    if len(neighbour) == 2:
                        neighbouring_triangles[neighbour[0]].append(neighbour[1])
                        neighbouring_triangles[neighbour[1]].append(neighbour[0])
                        segment_sides_found[neighbour, matching_segment] = True
                    elif len(neighbour) != 1:
                        print("ERROR: there is something wrong with the neighbours function")

            neighbour_count[tri_i] = len(neighbouring_triangles[tri_i])
        return neighbouring_triangles, neighbour_count

    def triangle_connectedness(self, neighbours, big_network_size):
        """
        Counts how many triangles each mesh triangle is connected to, and returns whether this 'network' of elements is bigger than big_network_size
        The objective is to identify small islands of elements that are not really connected to the relevant mesh
        :param neighbours: list of lists containing the neighbours of each triangle
        :param big_network_size: int indicating at which size to
        :return: a np boolean array indicating whether each triangle is in a big enough network
        """
        already_counted = np.zeros(len(neighbours), dtype=bool)
        connectedness = np.zeros(len(neighbours), dtype=np.int64)
        for i in range(len(neighbours)):
            if not (already_counted[i]):
                edge_triangles = neighbours[i]
                network = [i] + edge_triangles
                network_is_growing = True

                while network_is_growing and len(network) < big_network_size:
                    network_is_growing = False
                    new_edge_triangles = []
                    for tri in edge_triangles:
                        for neighbour in neighbours[tri]:
                            if not neighbour in network:
                                network.append(neighbour)
                                new_edge_triangles.append(neighbour)
                                network_is_growing = True
                    edge_triangles = new_edge_triangles
                connectedness[network] = len(network)
                already_counted[network] = True
        return connectedness >= big_network_size

    def is_well_connected(self, neighbours, bank_mesh_index):
        """
        returns whether each mesh element is connected to a mesh that is not in the river banks
        :param neighbours: list of lists containing the neighbours of each triangle in the mesh
        :param bank_mesh_index: np array containing the index of each element of the river banks in the tin
        :return: a boolean np array that states wheteher each mesh element in the tin either is a deep (non-bank) element or is connected to a deep element
        """
        is_connected = np.ones(shape=len(neighbours), dtype=bool)
        is_connected[bank_mesh_index] = False
        already_counted = is_connected.copy()
        for tri_index in bank_mesh_index:
            if not already_counted[tri_index]:
                edge_triangles = [tri_index, ]
                network = [tri_index, ]
                expand_network = True
                while expand_network:
                    expand_network = False
                    new_edge_triangles = []
                    for triangle in edge_triangles:
                        for neighbour in neighbours[triangle]:
                            if not neighbour in network:
                                network.append(neighbour)
                                new_edge_triangles.append(neighbour)
                                expand_network = True
                    if is_connected[edge_triangles].any():
                        is_connected[network] = True
                        expand_network = False
                    edge_triangles = new_edge_triangles
                already_counted[network] = True
        return is_connected

    def check_point_pertinence(self, x_adj, y_adj, phi_adj, x_lone, y_lone, phi_lone, max_discrepancy):
        ##Calculating planar a*x+b*y+c approximation of phi from nodes of adjacent triangle
        try:
            A = np.concatenate((x_adj.reshape((3, 1)), y_adj.reshape((3, 1)), np.ones((3, 1))), axis=1)
            a, b, c = np.linalg.solve(A, phi_adj)
            phi_pred = a * x_lone + b * y_lone + c  # phi predicted at the lone node position
            discrepancy = abs(phi_pred - phi_lone)
            return discrepancy <= max_discrepancy
        except np.linalg.LinAlgError:
            print("singular matrix!")
            return True

    def fix_aberrations(self, npasses=10, tolerance=0.01, connectedness_criterion=None, bank_depth=0.5):
        # TODO optimize code to run faster for large meshes
        # TODO find the most appropriate parameters npasses, tolerance, connectedness_criterion
        # t0 = time.time()
        for reach_i in range(self.reach_number):
            for unit_i in range(len(self[reach_i])):
                ##All arrays below are copies, rather than aliases
                node_data = self[reach_i][unit_i]["node"]["data"].copy()
                mesh_data = self[reach_i][unit_i]["mesh"]["data"].copy()
                i_whole_profile = self[reach_i][unit_i]["mesh"]["i_whole_profile"].copy()
                unsorted_tin = self[reach_i][unit_i]["mesh"]["tin"].copy()
                tin = np.sort(unsorted_tin, axis=1)
                x = np.array(self[reach_i][unit_i]["node"]["xy"][:, 0])
                x -= np.mean(x)
                y = np.array(self[reach_i][unit_i]["node"]["xy"][:, 1])
                y -= np.mean(y)
                h = np.array(node_data["h"].array)
                phi = np.array((node_data["z"].array - np.min(
                    node_data["z"].array)) + h)  # water height relative to a point at the bottom of the river bed
                node_number = len(x)

                max_discrepancy = np.mean(phi) * tolerance

                passes = 0
                while passes < npasses:

                    # tl0 = time.time()

                    bank_mesh_index = np.flatnonzero((h[tin] < bank_depth).any(axis=1))
                    bank_mesh = tin[bank_mesh_index]
                    neighbours, neighbour_count = self.neighbouring_triangles(tin, bank_mesh_index)
                    if connectedness_criterion:
                        connectedness = self.is_well_connected(neighbours, bank_mesh_index)
                    else:
                        connectedness = np.ones(len(tin), dtype=bool)

                    triangles_to_remove = []

                    for tri_index in range(len(bank_mesh)):

                        if not connectedness[bank_mesh_index[tri_index]]:
                            triangles_to_remove.append(bank_mesh_index[tri_index])
                        elif neighbour_count[bank_mesh_index[tri_index]] == 0:
                            triangles_to_remove.append(bank_mesh_index[tri_index])
                        elif neighbour_count[bank_mesh_index[tri_index]] == 1:
                            adjacent_triangle = tin[neighbours[bank_mesh_index[tri_index]][0]]
                            x_adj, y_adj, phi_adj = x[adjacent_triangle], y[adjacent_triangle], phi[adjacent_triangle]
                            for node in tin[bank_mesh_index[tri_index]]:
                                if not node in adjacent_triangle:
                                    lone_node = node
                            x_lone, y_lone, phi_lone = x[lone_node], y[lone_node], phi[lone_node]

                            if not self.check_point_pertinence(x_adj, y_adj, phi_adj, x_lone, y_lone, phi_lone,
                                                               max_discrepancy):
                                triangles_to_remove.append(bank_mesh_index[tri_index])


                        elif neighbour_count[bank_mesh_index[tri_index]] == 2:
                            for neighbour in neighbours[bank_mesh_index[tri_index]]:
                                adjacent_triangle = tin[neighbour]
                                x_adj, y_adj, phi_adj = x[adjacent_triangle], y[adjacent_triangle], phi[
                                    adjacent_triangle]
                                for node in tin[bank_mesh_index[tri_index]]:
                                    if not node in adjacent_triangle:
                                        lone_node = node
                                x_lone, y_lone, phi_lone = x[lone_node], y[lone_node], phi[lone_node]

                                if not self.check_point_pertinence(x_adj, y_adj, phi_adj, x_lone, y_lone, phi_lone,
                                                                   max_discrepancy):
                                    triangles_to_remove.append(bank_mesh_index[tri_index])
                                    break

                    tin = np.delete(tin, triangles_to_remove, axis=0)
                    unsorted_tin = np.delete(unsorted_tin, triangles_to_remove, axis=0)
                    i_whole_profile = np.delete(i_whole_profile, triangles_to_remove, axis=0)
                    mesh_data = mesh_data[~np.in1d(np.arange(len(mesh_data)), triangles_to_remove)]
                    # mesh_data.drop(axis=0, labels=mesh_data.index[triangles_to_remove], inplace=True)
                    # tl1 = time.time()
                    # print("Loop " + str(passes) + ", unit", unit_i, "reach", reach_i)
                    # print("looptime=", tl1 - tl0)
                    if len(triangles_to_remove) == 0:
                        passes = npasses  # if no triangles were removed in the loop, stop iterating
                    passes += 1

                nodes_to_delete = []
                for node in range(node_number):
                    if not node in tin:
                        nodes_to_delete.append(node)
                        # node_data.drop(index=node_data.index[node], axis=0, inplace=True)
                        # node_data=node_data[np.arange(len())
                nodes_to_delete = np.array(nodes_to_delete, dtype=np.int64)
                self[reach_i][unit_i]["node"]["xy"] = np.delete(self[reach_i][unit_i]["node"]["xy"], nodes_to_delete,
                                                                axis=0)
                node_data = node_data[~np.in1d(np.arange(len(node_data)), nodes_to_delete)]
                self[reach_i][unit_i]["node"]["data"] = node_data
                # newnodes=np.delete(np.arange(node_number),nodes_to_delete)
                corrected_tin = unsorted_tin.copy()
                for node in nodes_to_delete:
                    corrected_tin -= (unsorted_tin > node)

                self[reach_i][unit_i]["mesh"]["tin"] = corrected_tin
                self[reach_i][unit_i]["mesh"]["data"] = mesh_data
                self[reach_i][unit_i]["mesh"]["i_whole_profile"] = i_whole_profile
        # t1 = time.time()
        # print("runtime=", t1 - t0)

    def get_hs_summary_data(self, reach_num_list, unit_num_list):
        # get hs headers
        self.hs_summary_data = [[]]
        unit_dict = self[0][0]
        for key in unit_dict.hydrosignature.keys():
            element = unit_dict.hydrosignature[key]
            if type(element) != np.ndarray:
                self.hs_summary_data[0].append(key)
        self.hs_summary_data[0].insert(0, "reach")
        self.hs_summary_data[0].insert(1, "unit")

        for r_model_index in reach_num_list:
            for u_model_index in unit_num_list:
                unit_dict = self[r_model_index][u_model_index]
                key_element_list = []
                key_element_list.append(unit_dict.reach_name)
                key_element_list.append(unit_dict.unit_name)
                for key in unit_dict.hydrosignature.keys():
                    element = unit_dict.hydrosignature[key]
                    if type(element) != np.ndarray:
                        # append key
                        if isinstance(element, float):  # float
                            element = "{:.2f}".format(element)
                        else:  # integer or other
                            element = str(element)

                        key_element_list.append(element)
                # key_element_list = list(map(str.format, key_element_list))
                self.hs_summary_data.append(key_element_list)


class Reach(list):
    """ A reach represent a list of units """

    def __init__(self, reach_number=0, unit_number=0):
        super().__init__()
        self.reach_number = reach_number
        self.unit_number = unit_number
        for unit_number in range(self.unit_number):
            unit = Unit(reach_number,
                        unit_number)
            self.append(unit)


class Unit(dict):
    """ A unit represent the mesh """

    def __init__(self, reach_number, unit_number):
        super().__init__()
        # HydraulicVariableUnit
        self.hvum = HydraulicVariableUnitManagement()
        self.reach_number = reach_number
        self.reach_name = ""
        self.unit_number = unit_number
        self.unit_name = ""
        # data
        self.total_wet_area = None
        self.data_extent = None
        self.data_height = None
        self.data_width = None
        self["mesh"] = dict(tin=None)
        self["node"] = dict(xy=None,
                            z=None)
        # hydrosignature
        self.hydrosignature = dict()

    """ manage grid """

    def get_variables_with_data(self):
        data_variable_list = []

        for position in ("node", "mesh"):
            for key in self[position].keys():
                if self[position][key] is not None:
                    if key == "data":
                        for col in self[position][key].columns.tolist():
                            data_variable_list.append(col)
                    else:
                        data_variable_list.append(key)

        return data_variable_list

    def remove_null_area(self):
        index_to_remove = self["mesh"]["data"][self.hvum.area.name].to_numpy() == 0.0

        if True in index_to_remove:
            # update tin
            self["mesh"][self.hvum.tin.name] = self["mesh"][self.hvum.tin.name][~index_to_remove]

            # update i_whole_profile
            self["mesh"][self.hvum.i_whole_profile.name] = self["mesh"][self.hvum.i_whole_profile.name][
                ~index_to_remove]

            # update mesh data
            self["mesh"]["data"] = self["mesh"]["data"][~index_to_remove]

            print("Warning: " + str(np.sum(index_to_remove)) +
                  " mesh(s) with a null surface have been removed in unit " + str(self.unit_name) + ".")

    def remove_unused_node(self):
        shape0 = self["mesh"][self.hvum.tin.name].shape
        i_pt_unique, i2 = np.unique(self["mesh"][self.hvum.tin.name].flatten(), return_inverse=True, axis=0)
        node_unused_nb = len(self["node"]["xy"]) - len(i_pt_unique)
        if node_unused_nb:
            # update tin
            self["mesh"][self.hvum.tin.name] = i2.reshape(shape0)
            # update xy
            self["node"]["xy"] = self["node"]["xy"][i_pt_unique]
            # update node data
            self["node"]["data"] = self["node"]["data"].iloc[i_pt_unique]
            print("Warning: The unit " + self.unit_name + " has " + str(
                node_unused_nb) + " unused node(s). The latter has been removed.")

    def is_duplicates_mesh_or_point(self, case, mesh, node):
        """
        if duplicates node
        :param case: str check case
        :param mesh: bool to check if duplicates mesh
        :param node:bool to check if duplicates node
        :return: True : remove unit, False : keep unit
        """
        # init
        mesh_duplicate_tf = False
        node_xyz_duplicate_tf = False

        if mesh:
            # check if mesh duplicates presence
            u, c = np.unique(self["mesh"]["tin"], return_counts=True, axis=0)
            dup = u[c > 1]
            if len(dup) != 0:
                mesh_duplicate_tf = True
                print("Warning: The mesh of the unit " + self.unit_name + " is not loaded (" + str(len(dup)) +
                      " duplicate(s) mesh(s) " + case + ".")
                # : " + ", ".join([str(mesh_str) for mesh_str in dup.tolist()]) + ").")

        if node:
            # check if points duplicates presence XYZ
            u, c = np.unique(
                np.column_stack((self["node"][self.hvum.xy.name], self["node"]["data"][self.hvum.z.name].to_numpy())),
                return_counts=True, axis=0)
            dup = u[c > 1]
            if len(dup) != 0:
                node_xyz_duplicate_tf = True
                print("Warning: The mesh of the unit " + self.unit_name + " is not loaded (" + str(len(dup)) +
                      " duplicate(s) node(s) in xyz " + case + ".")
                # : " + ", ".join([str(mesh_str) for mesh_str in dup.tolist()]) + ").")
            if not node_xyz_duplicate_tf:
                # check if points duplicates presence
                u, c = np.unique(self["node"][self.hvum.xy.name], return_counts=True, axis=0)
                dup = u[c > 1]
                if len(dup) != 0:
                    # do not block process, only warning (must be removed by mesh null area process)
                    print("Warning: The mesh of the unit " + self.unit_name + " has " + str(len(dup)) +
                          " duplicate(s) node(s) in xy " + case + ".")
                # : " + ", ".join([str(mesh_str) for mesh_str in dup.tolist()]) + ").")
        # return
        if mesh_duplicate_tf or node_xyz_duplicate_tf:
            return True
        else:
            return False

    """ mesh """

    # mean from node variable
    def c_mesh_mean_from_node_values(self, node_variable_name):
        mesh_values = np.mean([self["node"]["data"][node_variable_name].iloc[self["mesh"]["tin"][:, 0]],
                               self["node"]["data"][node_variable_name].iloc[self["mesh"]["tin"][:, 1]],
                               self["node"]["data"][node_variable_name].iloc[self["mesh"]["tin"][:, 2]]], axis=0)
        self["mesh"]["data"][node_variable_name] = mesh_values

    def c_mesh_elevation(self):
        self.c_mesh_mean_from_node_values(self.hvum.z.name)

    def c_mesh_height(self):
        self.c_mesh_mean_from_node_values(self.hvum.h.name)

    def c_mesh_velocity(self):
        self.c_mesh_mean_from_node_values(self.hvum.v.name)

    def c_mesh_shear_stress(self):
        self.c_mesh_mean_from_node_values(self.hvum.shear_stress.name)

    # compute from node variable
    def c_mesh_shear_stress_beta(self):
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"]["data"][self.hvum.z.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        h1 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        v1 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"]["data"][self.hvum.z.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        h2 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        v2 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"]["data"][self.hvum.z.name].to_numpy()[self["mesh"]["tin"][:, 2]]
        h3 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 2]]
        v3 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 2]]

        w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
        zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * self.hvum.g.value), z2 + h2 + v2 ** 2 / (
                2 * self.hvum.g.value), z3 + h3 + v3 ** 2 / (
                                2 * self.hvum.g.value)
        u = (xy2[:, 1] - xy1[:, 1]) * (zz3 - zz1) - (zz2 - zz1) * (xy3[:, 1] - xy1[:, 1])
        v = (xy3[:, 0] - xy1[:, 0]) * (zz2 - zz1) - (zz3 - zz1) * (xy2[:, 0] - xy1[:, 0])
        with np.errstate(divide='ignore', invalid='ignore'):
            max_slope_energy = np.sqrt(u ** 2 + v ** 2) / np.abs(w)
        shear_stress = self.hvum.ro.value * self.hvum.g.value * (h1 + h2 + h3) * max_slope_energy / 3

        # change inf values to nan
        if np.inf in shear_stress:
            shear_stress[shear_stress == np.inf] = np.NaN

        # change incoherent values to nan
        with np.errstate(invalid='ignore'):  # ignore warning due to NaN values
            shear_stress[shear_stress > 800] = np.NaN  # 800

        self["mesh"]["data"][self.hvum.shear_stress_beta.name] = shear_stress

    def c_mesh_max_slope_bottom(self):
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"]["data"]["z"].to_numpy()[self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"]["data"]["z"].to_numpy()[self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"]["data"]["z"].to_numpy()[self["mesh"]["tin"][:, 2]]

        w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
        u = (xy2[:, 1] - xy1[:, 1]) * (z3 - z1) - (z2 - z1) * (xy3[:, 1] - xy1[:, 1])
        v = (xy3[:, 0] - xy1[:, 0]) * (z2 - z1) - (z3 - z1) * (xy2[:, 0] - xy1[:, 0])

        with np.errstate(divide='ignore', invalid='ignore'):
            max_slope_bottom = np.sqrt(u ** 2 + v ** 2) / np.abs(w)

        # change inf values to nan
        if np.inf in max_slope_bottom:
            max_slope_bottom[max_slope_bottom == np.inf] = np.NaN

        # change incoherent values to nan
        with np.errstate(invalid='ignore'):  # ignore warning due to NaN values
            max_slope_bottom[max_slope_bottom > 10] = np.NaN  # 0.55

        self["mesh"]["data"][self.hvum.max_slope_bottom.name] = max_slope_bottom

    def c_mesh_max_slope_surface(self):
        '''
        c_mesh_max_slope_surface
        '''
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"]["data"]["z"].to_numpy()[self["mesh"]["tin"][:, 0]]
        h1 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"]["data"]["z"].to_numpy()[self["mesh"]["tin"][:, 1]]
        h2 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"]["data"]["z"].to_numpy()[self["mesh"]["tin"][:, 2]]
        h3 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 2]]

        w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
        zz1, zz2, zz3 = z1 + h1, z2 + h2, z3 + h3
        u = (xy2[:, 1] - xy1[:, 1]) * (zz3 - zz1) - (zz2 - zz1) * (xy3[:, 1] - xy1[:, 1])
        v = (xy3[:, 0] - xy1[:, 0]) * (zz2 - zz1) - (zz3 - zz1) * (xy2[:, 0] - xy1[:, 0])
        with np.errstate(divide='ignore', invalid='ignore'):
            mesh_max_slope_surface = np.sqrt(u ** 2 + v ** 2) / np.abs(w)

        # change inf values to nan
        if np.inf in mesh_max_slope_surface:
            mesh_max_slope_surface[mesh_max_slope_surface == np.inf] = np.NaN

        # change incoherent values to nan
        # with np.errstate(invalid='ignore'):  # ignore warning due to NaN values
        # mesh_max_slope_surface[mesh_max_slope_surface > 0.08] = np.NaN  # 0.08
        self["mesh"]["data"][self.hvum.max_slope_surface.name] = mesh_max_slope_surface

    def c_mesh_max_slope_energy(self):
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"]["data"][self.hvum.z.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        h1 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        v1 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"]["data"][self.hvum.z.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        h2 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        v2 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"]["data"][self.hvum.z.name].to_numpy()[self["mesh"]["tin"][:, 2]]
        h3 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 2]]
        v3 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 2]]

        w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
        zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * self.hvum.g.value), z2 + h2 + v2 ** 2 / (
                2 * self.hvum.g.value), z3 + h3 + v3 ** 2 / (
                                2 * self.hvum.g.value)
        u = (xy2[:, 1] - xy1[:, 1]) * (zz3 - zz1) - (zz2 - zz1) * (xy3[:, 1] - xy1[:, 1])
        v = (xy3[:, 0] - xy1[:, 0]) * (zz2 - zz1) - (zz3 - zz1) * (xy2[:, 0] - xy1[:, 0])
        with np.errstate(divide='ignore', invalid='ignore'):
            max_slope_energy = np.sqrt(u ** 2 + v ** 2) / np.abs(w)

        # change inf values to nan
        if np.inf in max_slope_energy:
            max_slope_energy[max_slope_energy == np.inf] = np.NaN

        # change incoherent values to nan
        with np.errstate(invalid='ignore'):  # ignore warning due to NaN values
            max_slope_energy[max_slope_energy > 0.08] = np.NaN  # 0.08

        self["mesh"]["data"][self.hvum.max_slope_energy.name] = max_slope_energy

    def c_mesh_froude(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if v and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.v.name in mesh_colnames:
            # froude from mesh h and v
            self["mesh"]["data"][self.hvum.froude.name] = self["mesh"]["data"][self.hvum.v.name] / np.sqrt(
                self.hvum.g.value * self["mesh"]["data"][self.hvum.h.name])
            with pd.option_context('mode.use_inf_as_na', True):
                self["mesh"]["data"][self.hvum.froude.name] = self["mesh"]["data"][self.hvum.froude.name].fillna(
                    0)  # divid by 0 return Nan

        # compute from node
        else:
            self.c_mesh_mean_from_node_values(self.hvum.froude.name)

    def c_mesh_hydraulic_head(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if v and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.v.name in mesh_colnames:
            # compute hydraulic_head = (z + h) + ((v ** 2) / (2 * self.hvum.g.value))
            self["mesh"]["data"][self.hvum.hydraulic_head.name] = self["mesh"]["data"][self.hvum.h.name] + (
                    (self["mesh"]["data"][self.hvum.v.name] ** 2) / (2 * self.hvum.g.value))
        # compute mesh mean
        else:
            self.c_mesh_mean_from_node_values(self.hvum.hydraulic_head.name)

    def c_mesh_hydraulic_head_level(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if v and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.v.name in mesh_colnames:
            # compute hydraulic_head_level = (z + h) + ((v ** 2) / (2 * self.hvum.g.value))
            self["mesh"]["data"][self.hvum.hydraulic_head_level.name] = (self["mesh"]["data"][self.hvum.z.name] +
                                                                         self["mesh"]["data"][self.hvum.h.name]) + (
                                                                                (self["mesh"]["data"][
                                                                                     self.hvum.v.name] ** 2) / (
                                                                                        2 * self.hvum.g.value))
        # compute mesh mean
        else:
            self.c_mesh_mean_from_node_values(self.hvum.hydraulic_head_level.name)

    def c_mesh_conveyance(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if v and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.v.name in mesh_colnames:
            self["mesh"]["data"][self.hvum.conveyance.name] = self["mesh"]["data"][self.hvum.h.name] * \
                                                              self["mesh"]["data"][self.hvum.v.name]
        # compute mesh mean
        else:
            self.c_mesh_mean_from_node_values(self.hvum.conveyance.name)

    def c_mesh_water_level(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if z and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.z.name in mesh_colnames:
            # mesh_water_level from mesh_h and mesh_z
            self["mesh"]["data"][self.hvum.level.name] = np.sum([self["mesh"]["data"][self.hvum.z.name],
                                                                 self["mesh"]["data"][self.hvum.h.name]], axis=0)
        else:
            # mesh_water_level
            self.c_mesh_mean_from_node_values(self.hvum.level.name)

    def c_mesh_area(self):
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]

        # compute area
        area = 0.5 * abs((xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy3[:, 0] - xy1[:, 0]) * (
                xy2[:, 1] - xy1[:, 1]))

        self["mesh"]["data"][self.hvum.area.name] = area
        self.total_wet_area = np.sum(area)

    def c_mesh_sub_coarser(self):
        if self.hvum.sub_s12.name in self["mesh"]["data"].columns:
            sub_percent = np.array([self["mesh"]["data"][self.hvum.sub_s1.name],
                                    self["mesh"]["data"][self.hvum.sub_s2.name],
                                    self["mesh"]["data"][self.hvum.sub_s3.name],
                                    self["mesh"]["data"][self.hvum.sub_s4.name],
                                    self["mesh"]["data"][self.hvum.sub_s5.name],
                                    self["mesh"]["data"][self.hvum.sub_s6.name],
                                    self["mesh"]["data"][self.hvum.sub_s7.name],
                                    self["mesh"]["data"][self.hvum.sub_s8.name],
                                    self["mesh"]["data"][self.hvum.sub_s9.name],
                                    self["mesh"]["data"][self.hvum.sub_s10.name],
                                    self["mesh"]["data"][self.hvum.sub_s11.name],
                                    self["mesh"]["data"][self.hvum.sub_s12.name],
                                    ]).T
        else:
            sub_percent = np.array([self["mesh"]["data"][self.hvum.sub_s1.name],
                                    self["mesh"]["data"][self.hvum.sub_s2.name],
                                    self["mesh"]["data"][self.hvum.sub_s3.name],
                                    self["mesh"]["data"][self.hvum.sub_s4.name],
                                    self["mesh"]["data"][self.hvum.sub_s5.name],
                                    self["mesh"]["data"][self.hvum.sub_s6.name],
                                    self["mesh"]["data"][self.hvum.sub_s7.name],
                                    self["mesh"]["data"][self.hvum.sub_s8.name]
                                    ]).T

        len_sub = len(sub_percent)
        sub_pg = np.empty(len_sub, dtype=np.int64)
        warn = True

        for e in range(0, len_sub):
            record_all_i = sub_percent[e]
            if sum(record_all_i) != 100 and warn:
                print('Warning: Substrate data is given in percentage. However, it does not sum to 100% \n')
                warn = False

            # let find the coarser (the last one not equal to zero)
            ind = np.where(record_all_i[record_all_i != 0])[0]
            if len(ind) > 1:
                sub_pg[e] = ind[-1] + 1
            elif ind:  # just a float
                sub_pg[e] = ind + 1
            else:  # no zeros
                sub_pg[e] = len(record_all_i)

        self["mesh"]["data"][self.hvum.sub_coarser.name] = sub_pg

    def c_mesh_sub_dom(self):
        if self.hvum.sub_s12.name in self["mesh"]["data"].columns:
            sub_percent = np.array([self["mesh"]["data"][self.hvum.sub_s1.name],
                                    self["mesh"]["data"][self.hvum.sub_s2.name],
                                    self["mesh"]["data"][self.hvum.sub_s3.name],
                                    self["mesh"]["data"][self.hvum.sub_s4.name],
                                    self["mesh"]["data"][self.hvum.sub_s5.name],
                                    self["mesh"]["data"][self.hvum.sub_s6.name],
                                    self["mesh"]["data"][self.hvum.sub_s7.name],
                                    self["mesh"]["data"][self.hvum.sub_s8.name],
                                    self["mesh"]["data"][self.hvum.sub_s9.name],
                                    self["mesh"]["data"][self.hvum.sub_s10.name],
                                    self["mesh"]["data"][self.hvum.sub_s11.name],
                                    self["mesh"]["data"][self.hvum.sub_s12.name],
                                    ]).T
        else:
            sub_percent = np.array([self["mesh"]["data"][self.hvum.sub_s1.name],
                                    self["mesh"]["data"][self.hvum.sub_s2.name],
                                    self["mesh"]["data"][self.hvum.sub_s3.name],
                                    self["mesh"]["data"][self.hvum.sub_s4.name],
                                    self["mesh"]["data"][self.hvum.sub_s5.name],
                                    self["mesh"]["data"][self.hvum.sub_s6.name],
                                    self["mesh"]["data"][self.hvum.sub_s7.name],
                                    self["mesh"]["data"][self.hvum.sub_s8.name]
                                    ]).T

        dominant_case = 1
        len_sub = len(sub_percent)
        sub_dom = np.empty(len_sub, dtype=np.int64)
        warn = True

        for e in range(0, len_sub):
            record_all_i = sub_percent[e]
            if sum(record_all_i) != 100 and warn:
                print('Warning: Substrate data is given in percentage. However, it does not sum to 100% \n')
                warn = False
            # let find the dominant
            # we cannot use argmax as we need all maximum value, not only the first
            inds = list(np.argwhere(record_all_i == np.max(record_all_i)).flatten())
            if len(inds) > 1:
                # if we have the same percentage for two dominant we send back the function to the GUI to ask the
                # user. It is called again with the arg dominant_case
                if dominant_case == 1:
                    sub_dom[e] = inds[-1] + 1
                elif dominant_case == -1:
                    # sub_dom[e] = int(attribute_name_all[inds[0]][0][1])
                    sub_dom[e] = inds[0] + 1
            else:
                sub_dom[e] = inds[0] + 1

        self["mesh"]["data"][self.hvum.sub_dom.name] = sub_dom

    """ node """

    def c_node_shear_stress(self):
        self["node"]["data"][self.hvum.shear_stress.name] = (self["node"]["data"][
                                                                 self.hvum.v_frict.name] ** 2) * self.hvum.ro.value

    def c_node_froude(self):
        # compute froude
        self["node"]["data"][self.hvum.froude.name] = self["node"]["data"][self.hvum.v.name] / np.sqrt(
            self.hvum.g.value * self["node"]["data"][self.hvum.h.name])
        with pd.option_context('mode.use_inf_as_na', True):
            self["node"]["data"][self.hvum.froude.name] = self["node"]["data"][self.hvum.froude.name].fillna(
                0)  # divid by 0 return Nan

    def c_node_hydraulic_head(self):
        # compute hydraulic_head = (z + h) + ((v ** 2) / (2 * self.hvum.g.value))
        self["node"]["data"][self.hvum.hydraulic_head.name] = self["node"]["data"][self.hvum.h.name] + (
                (self["node"]["data"][self.hvum.v.name] ** 2) / (2 * self.hvum.g.value))

    def c_node_hydraulic_head_level(self):
        # compute hydraulic_head = (z + h) + ((v ** 2) / (2 * self.hvum.g.value))
        self["node"]["data"][self.hvum.hydraulic_head_level.name] = (self["node"]["data"][self.hvum.z.name] +
                                                                     self["node"]["data"][self.hvum.h.name]) + (
                                                                            (self["node"]["data"][
                                                                                 self.hvum.v.name] ** 2) / (
                                                                                    2 * self.hvum.g.value))

    def c_node_conveyance(self):
        self["node"]["data"][self.hvum.conveyance.name] = self["node"]["data"][self.hvum.h.name] * self["node"]["data"][
            self.hvum.v.name]

    def c_node_water_level(self):
        self["node"]["data"][self.hvum.level.name] = self["node"]["data"][self.hvum.z.name] + self["node"]["data"][
            self.hvum.h.name]
