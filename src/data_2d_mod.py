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

from src.manage_grid_mod import is_duplicates_mesh_and_point_on_one_unit, linear_z_cross
from src.variable_unit_mod import HydraulicVariableUnitManagement, HydraulicVariableUnitList


class Data2d(list):
    def __init__(self, reach_num=0, unit_num=0):
        super().__init__()
        self.reach_num = reach_num
        self.unit_num = unit_num
        if self.reach_num and self.unit_num:
            for reach_num in range(self.reach_num):
                unit_list = []
                for unit_num in range(self.unit_num):
                    unit_dict = UnitDict(reach_num,
                                         unit_num)
                    unit_dict["mesh"] = dict(tin=None)
                    unit_dict["node"] = dict(xy=None,
                                             z=None)
                    unit_list.append(unit_dict)
                self.append(unit_list)
        # hvum
        self.hvum = HydraulicVariableUnitManagement()
        # data
        self.data_extent = None
        self.data_height = None
        self.data_width = None

    def get_informations(self):
        self.reach_num = len(self)
        if self.reach_num:
            self.unit_num = len(self[self.reach_num - 1])

        for reach_num in range(self.reach_num):
            for unit_num in range(self.unit_num):
                self[reach_num][unit_num].reach_num = reach_num
                self[reach_num][unit_num].unit_num = unit_num

    def append(self, hydraulic_variable):
        super(Data2d, self).append(hydraulic_variable)
        self.get_informations()

    def add_reach(self, data_2d_new, reach_num):
        self.append(data_2d_new[reach_num])

        # TODO: check if same units number and name

        # update attrs
        self.get_informations()
        self.hvum = data_2d_new.hvum

    def add_unit(self,  data_2d_new, reach_num):
        if not self.reach_num:
            self.append([])
        self[reach_num].extend(data_2d_new[reach_num])

        # TODO: check if same units number and name

        self.get_informations()
        self.hvum = data_2d_new.hvum

    def get_dimension(self):
        # get extent
        xMin = []
        xMax = []
        yMin = []
        yMax = []

        # for each reach
        for reach_num in range(self.reach_num):
            # for each unit
            for unit_num in range(self.unit_num):
                # extent
                xMin.append(min(self[reach_num][unit_num]["node"]["xy"][:, 0]))
                xMax.append(max(self[reach_num][unit_num]["node"]["xy"][:, 0]))
                yMin.append(min(self[reach_num][unit_num]["node"]["xy"][:, 1]))
                yMax.append(max(self[reach_num][unit_num]["node"]["xy"][:, 1]))

        # get extent
        xMin = min(xMin)
        xMax = max(xMax)
        yMin = min(yMin)
        yMax = max(yMax)
        self.data_extent = str(xMin) + ", " + str(yMin) + ", " + str(xMax) + ", " + str(yMax)
        self.data_height = xMax - xMin
        self.data_width = yMax - yMin

    def get_only_mesh(self):
        """
        retrun whole_profile from original data2d
        """
        whole_profile = Data2d()
        for reach_num in range(self.reach_num):
            unit_list = []
            for unit_num in range(self.unit_num):
                unit_dict = UnitDict(reach_num,
                                     unit_num)
                unit_dict["mesh"] = dict(tin=self[reach_num][unit_num]["mesh"]["tin"])
                unit_dict["node"] = dict(xy=self[reach_num][unit_num]["node"]["xy"],
                                         z=self[reach_num][unit_num]["node"]["data"][self.hvum.z.name])
                # append by unit
                unit_list.append(unit_dict)
                # append by reach
            whole_profile.append(unit_list)

        whole_profile.get_informations()

        return whole_profile

    def get_hyd_varying_xy_and_z_index(self):
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

    def reduce_to_first_unit_by_reach(self):
        for reach_num in range(self.reach_num):
            self[reach_num] = [self[reach_num][0]]
        self.get_informations()

    def rename_substrate_column_data(self):
        for reach_num in range(self.reach_num):
            for unit_num in range(self.unit_num):
                self[reach_num][unit_num]["mesh"]["data"].columns = self.hvum.hdf5_and_computable_list.hdf5s().subs().names()

    def set_unit_names(self, unit_name_list):
        self.unit_name_list = unit_name_list
        for reach_num in range(self.reach_num):
            for unit_num in range(self.unit_num):
                self[reach_num][unit_num].unit_name = self.unit_name_list[reach_num][unit_num]

    def remove_unit_from_unit_list(self, unit_index_to_remove_list):
        # unit_dict removed
        for reach_num in range(self.reach_num):
            for unit_index_to_remove in reversed(unit_index_to_remove_list):
                self[reach_num].pop(unit_index_to_remove)
                # unit_name_list updated
                self.unit_name_list[reach_num].pop(unit_index_to_remove)

    def check_validity(self):
        unit_to_remove_list = []
        # for each reach
        for reach_num in range(self.reach_num):
            # for each unit
            for unit_num in range(self.unit_num):
                # is_duplicates_mesh_and_point_on_one_unit?
                if is_duplicates_mesh_and_point_on_one_unit(tin_array=self[reach_num][unit_num]["mesh"]["tin"],
                                                            xyz_array=np.column_stack(
                                                                (self[reach_num][unit_num]["node"][self.hvum.xy.name],
                                                                 self[reach_num][unit_num]["node"]["data"][
                                                                     self.hvum.z.name].to_numpy())),
                                                            unit_num=unit_num,
                                                            case="at reading."):
                    print("Warning: The mesh of unit " + str(unit_num) + " is not loaded.")
                    unit_to_remove_list.append(unit_num)
                    continue

        # remove_unit_from_unit_list
        self.remove_unit_from_unit_list(unit_to_remove_list)

    def set_min_height_to_0(self, min_height):
        # for each reach
        for reach_num in range(self.reach_num):
            # for each unit
            for unit_num in range(self.unit_num):
                """ node (always) """
                self[reach_num][unit_num]["node"]["data"].loc[self[reach_num][unit_num]["node"]["data"][self.hvum.h.name] < min_height, self.hvum.hdf5_and_computable_list.nodes().depend_on_hs().names()] = 0.0

                """ mesh """
                if self.hvum.h.name in self.hvum.hdf5_and_computable_list.meshs().names():
                    self[reach_num][unit_num]["mesh"]["data"].loc[self[reach_num][unit_num]["mesh"]["data"][self.hvum.h.name] < min_height, self.hvum.hdf5_and_computable_list.meshs().depend_on_hs().names()] = 0.0

    def remove_dry_mesh(self):
        self.get_informations()

        unit_to_remove_list = []

        # for each reach
        for reach_num in range(self.reach_num):
            # for each unit
            for unit_num in range(self.unit_num):
                # get data from dict
                ikle = self[reach_num][unit_num]["mesh"]["tin"]
                point_all = np.column_stack((self[reach_num][unit_num]["node"][self.hvum.xy.name],
                                 self[reach_num][unit_num]["node"]["data"][self.hvum.z.name].to_numpy()))
                water_height = self[reach_num][unit_num]["node"]["data"][self.hvum.h.name].to_numpy()
                ind_whole = self[reach_num][unit_num]["mesh"][self.hvum.i_whole_profile.name]

                bhw = (water_height > 0).astype(self.hvum.i_whole_profile.dtype)
                ikle_bit = bhw[ikle]
                ikle_type = np.sum(ikle_bit, axis=1)  # list of meshes characters 0=dry 3=wet 1 or 2 = partially wet
                mikle_keep = ikle_type != 0

                # all meshes are entirely dry
                if not True in mikle_keep:
                    print("Warning: The mesh of unit n°" + unit_num + " is entirely dry.")
                    unit_to_remove_list.append(unit_num)
                    continue

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
                self[reach_num][unit_num]["mesh"][self.hvum.tin.name] = iklekeep
                self[reach_num][unit_num]["mesh"][self.hvum.i_whole_profile.name] = ind_whole
                if not self[reach_num][unit_num]["mesh"]["data"].empty:
                    self[reach_num][unit_num]["mesh"]["data"] = self[reach_num][unit_num]["mesh"]["data"].iloc[mikle_keep]

                # node data
                self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].iloc[ipt_iklenew_unique]
                self[reach_num][unit_num]["node"][self.hvum.xy.name] = point_all_ok[:, :2]

    def semi_wetted_mesh_cutting(self, unit_list, progress_value, delta_file):
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

        unit_to_remove_list = []

        # for each reach
        for reach_num in range(self.reach_num):
            # for each unit
            for unit_num, unit_name in enumerate(unit_list):
                # get data from dict
                ikle = self[reach_num][unit_num]["mesh"]["tin"]
                point_all = np.column_stack((self[reach_num][unit_num]["node"][self.hvum.xy.name],
                                 self[reach_num][unit_num]["node"]["data"][self.hvum.z.name].to_numpy()))
                water_height = self[reach_num][unit_num]["node"]["data"][self.hvum.h.name].to_numpy()
                velocity = self[reach_num][unit_num]["node"]["data"][self.hvum.v.name].to_numpy()

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
                    print("Warning: The mesh of unit " + unit_name + " is entirely wet.")
                    pass
                # we cut the dry meshes and  the partially ones
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
                                    unit_to_remove_list.append(unit_num)
                                    continue
                                jpn += 2

                    iklekeep = ikle[
                        mikle_keep, ...]  # only the original entirely wetted meshes and meshes we can't split( overwetted ones )
                    ind_whole = ind_whole[mikle_keep, ...]
                    ind_whole = np.append(ind_whole, np.asarray(ind_whole2, dtype=self.hvum.tin.dtype), axis=0)
                    i_split = np.repeat(0, ind_whole.shape[0]).astype(self.hvum.i_split.dtype)

                # all cases
                ipt_iklenew_unique = np.unique(iklekeep)

                if ipt_all_ok_wetdry:  # presence of partially wet/dry meshes cutted that we want
                    ipt_iklenew_unique = np.append(ipt_iklenew_unique, np.asarray(ipt_all_ok_wetdry, dtype=self.hvum.tin.dtype), axis=0)
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
                        print("Warning: while the cutting of mesh partially wet of the unit n°" + str(
                            unit_num) + " we have been forced to eliminate " + str(nbdouble) +
                              " duplicate(s) point(s) ")
                    if is_duplicates_mesh_and_point_on_one_unit(tin_array=iklekeep,
                                                                xyz_array=point_all_ok,
                                                                unit_num=unit_num,
                                                                case="after the cutting of mesh partially wet", checkpoint=False):
                        print("Warning: The mesh of unit " + unit_name + " is not loaded.")
                        unit_to_remove_list.append(unit_num)
                        continue

                    # all the new points added have water_height,velocity=0,0   # TODO: v=0 is applicable to torrential flows ?
                    water_height_ok = np.append(water_height_ok, np.zeros(lpns - nbdouble, dtype=water_height.dtype), axis=0)
                    velocity_ok = np.append(velocity_ok, np.zeros(lpns - nbdouble, dtype=velocity.dtype), axis=0)

                    # temp
                    if self.hvum.temp.name in self.hvum.hdf5_and_computable_list.nodes().names():
                        # inter_height = scipy.interpolate.griddata(xy, values, point_p, method='linear')
                        temp_data = griddata(points=self[reach_num][unit_num]["node"][self.hvum.xy.name],
                                             values=self[reach_num][unit_num]["node"]["data"][
                                                 self.hvum.temp.name].to_numpy(),
                                             xi=point_new_single[:, :2],
                                             method="linear")

                    # change all node dataframe
                    self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].iloc[
                        ipt_iklenew_unique]
                    if self.hvum.temp.name in self.hvum.hdf5_and_computable_list.nodes().names():
                        temp_ok = np.append(self[reach_num][unit_num]["node"]["data"][self.hvum.temp.name], temp_data,
                                            axis=0)

                    # new pandas dataframe (to be added to the end)
                    nan_pd = pd.DataFrame(np.nan, index=np.arange(lpns - nbdouble),
                                          columns=self[reach_num][unit_num]["node"]["data"].columns.values)
                    self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].append(nan_pd)
                    self[reach_num][unit_num]["node"]["data"][self.hvum.h.name] = water_height_ok
                    self[reach_num][unit_num]["node"]["data"][self.hvum.v.name] = velocity_ok
                    self[reach_num][unit_num]["node"]["data"][self.hvum.z.name] = point_all_ok[:, 2]
                    if self.hvum.temp.name in self.hvum.hdf5_and_computable_list.nodes().names():
                        self[reach_num][unit_num]["node"]["data"][self.hvum.temp.name] = temp_ok
                else:
                    self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].iloc[
                        ipt_iklenew_unique]

                # mesh data
                if not self[reach_num][unit_num]["mesh"]["data"].empty:
                    self[reach_num][unit_num]["mesh"]["data"] = self[reach_num][unit_num]["mesh"]["data"].iloc[
                        ind_whole]
                self[reach_num][unit_num]["mesh"][self.hvum.tin.name] = iklekeep
                self[reach_num][unit_num]["mesh"][self.hvum.i_whole_profile.name] = np.column_stack(
                    [ind_whole, i_split])
                self[reach_num][unit_num]["mesh"]["data"][self.hvum.i_split.name] = i_split  # i_split
                if not self.hvum.i_split.name in self.hvum.hdf5_and_computable_list.names():
                    self.hvum.i_split.position = "mesh"
                    self.hvum.i_split.hdf5 = True
                    self.hvum.hdf5_and_computable_list.append(self.hvum.i_split)

                # node data
                self[reach_num][unit_num]["node"][self.hvum.xy.name] = point_all_ok[:, :2]
                self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].fillna(
                    0)  # fillna with 0

                # progress
                progress_value.value += int(deltaunit)

        if unit_to_remove_list:
            self.remove_unit_from_unit_list(unit_to_remove_list)

        self.get_informations()

    def set_sub_cst_value(self, hdf5_sub):
        # mixing variables
        self.hvum.hdf5_and_computable_list.extend(hdf5_sub.hvum.hdf5_and_computable_list)

        # for each reach
        for reach_num in range(self.reach_num):
            # for each unit
            for unit_num in range(self.unit_num):
                try:
                    default_data = np.array(list(map(int, hdf5_sub.sub_default_values.split(", "))),
                                            dtype=self.hvum.sub_dom.dtype)
                    sub_array = np.repeat([default_data], self[reach_num][unit_num]["mesh"]["tin"].shape[0], 0)
                except ValueError or TypeError:
                    print(
                        'Error: Merging failed. No numerical data in substrate. (only float or int accepted for now). \n')
                # add sub data to dict
                for sub_class_num, sub_class_name in enumerate(hdf5_sub.hvum.hdf5_and_computable_list.hdf5s().names()):
                    self[reach_num][unit_num]["mesh"]["data"][sub_class_name] = sub_array[:, sub_class_num]

                # area ?
                if self.hvum.area.name not in self[reach_num][unit_num]["mesh"]["data"].columns:
                    pa = self[reach_num][unit_num]["node"]["xy"][
                        self[reach_num][unit_num]["mesh"]["tin"][:, 0]]
                    pb = self[reach_num][unit_num]["node"]["xy"][
                        self[reach_num][unit_num]["mesh"]["tin"][:, 1]]
                    pc = self[reach_num][unit_num]["node"]["xy"][
                        self[reach_num][unit_num]["mesh"]["tin"][:, 2]]
                    area = 0.5 * abs(
                        (pb[:, 0] - pa[:, 0]) * (pc[:, 1] - pa[:, 1]) -
                        (pc[:, 0] - pa[:, 0]) * (pb[:, 1] - pa[:, 1]))  # get area2
                    self[reach_num][unit_num]["mesh"]["data"]["area"] = area
                    # variable
                    self.hvum.area.hdf5 = True
                    self.hvum.hdf5_and_computable_list.append(self.hvum.area)
                else:
                    area = self[reach_num][unit_num]["mesh"]["data"][self.hvum.area.name].to_numpy()

                self[reach_num][unit_num].total_wet_area = np.sum(area)

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
        node_variable_list = variable_computable_list.nodes()
        mesh_variable_list = variable_computable_list.meshs()
        # for all reach
        for reach_num in range(0, self.reach_num):
            # for all units
            for unit_num in range(0, self.unit_num):
                #print("--- compute_variables unit", str(unit_num), " ---")
                """ node """
                if node_variable_list:
                    for node_variable in node_variable_list:
                        # compute water_level
                        if node_variable.name == self.hvum.level.name:
                            self[reach_num][unit_num].c_node_water_level()
                        # compute froude
                        elif node_variable.name == self.hvum.froude.name:
                            self[reach_num][unit_num].c_node_froude()
                        # compute hydraulic_head
                        elif node_variable.name == self.hvum.hydraulic_head.name:
                            self[reach_num][unit_num].c_node_hydraulic_head()
                        # compute conveyance
                        elif node_variable.name == self.hvum.conveyance.name:
                            self[reach_num][unit_num].c_node_conveyance()
                        # compute shear_stress
                        elif node_variable.name == self.hvum.shear_stress.name:
                            self[reach_num][unit_num].c_node_shear_stress()
                """ mesh """
                if mesh_variable_list:
                    for mesh_variable in mesh_variable_list:
                        # c_mesh_elevation
                        if mesh_variable.name == self.hvum.z.name:
                            self[reach_num][unit_num].c_mesh_elevation()
                        # compute height
                        elif mesh_variable.name == self.hvum.h.name:
                            self[reach_num][unit_num].c_mesh_height()
                        # compute velocity
                        elif mesh_variable.name == self.hvum.v.name:
                            self[reach_num][unit_num].c_mesh_velocity()
                        # compute shear_stress
                        elif mesh_variable.name == self.hvum.shear_stress.name:
                            self[reach_num][unit_num].c_mesh_shear_stress()
                        # compute shear_stress_beta
                        elif mesh_variable.name == self.hvum.shear_stress_beta.name:
                            self[reach_num][unit_num].c_mesh_shear_stress_beta()
                        # compute water_level
                        elif mesh_variable.name == self.hvum.level.name:
                            self[reach_num][unit_num].c_mesh_water_level()
                        # compute froude
                        elif mesh_variable.name == self.hvum.froude.name:
                            self[reach_num][unit_num].c_mesh_froude()
                        # compute hydraulic_head
                        elif mesh_variable.name == self.hvum.hydraulic_head.name:
                            self[reach_num][unit_num].c_mesh_hydraulic_head()
                        # compute conveyance
                        elif mesh_variable.name == self.hvum.conveyance.name:
                            self[reach_num][unit_num].c_mesh_conveyance()
                        # compute max_slope_bottom
                        elif mesh_variable.name == self.hvum.max_slope_bottom.name:
                            self[reach_num][unit_num].c_mesh_max_slope_bottom()
                        # compute max_slope_energy
                        elif mesh_variable.name == self.hvum.max_slope_energy.name:
                            self[reach_num][unit_num].c_mesh_max_slope_energy()
                        # compute area
                        elif mesh_variable.name == self.hvum.area.name:
                            self[reach_num][unit_num].c_mesh_area()
                        # compute coarser
                        elif mesh_variable.name == self.hvum.sub_coarser.name:
                            self[reach_num][unit_num].c_mesh_sub_coarser()
                        # compute dominant
                        elif mesh_variable.name == self.hvum.sub_dom.name:
                            self[reach_num][unit_num].c_mesh_sub_dom()
                        # area
                        elif mesh_variable.name == self.hvum.area.name:
                            self[reach_num][unit_num].c_mesh_area()

    def remove_null_area(self):
        # for all reach
        for reach_num in range(0, self.reach_num):
            # for all units
            for unit_num in range(0, self.unit_num):
                self[reach_num][unit_num].remove_null_area()


class UnitDict(dict):
    def __init__(self, reach_num, unit_num):
        super().__init__()
        # HydraulicVariableUnit
        self.hvum = HydraulicVariableUnitManagement()
        self.reach_num = reach_num
        self.unit_num = unit_num
        self.unit_name = ""
        # data
        self.total_wet_area = None
        self.data_extent = None
        self.data_height = None
        self.data_width = None

    """ mesh """
    # mean from node variable
    def c_mesh_mean_from_node_values(self, node_variable_name):
        mesh_values = np.mean([self["node"]["data"][node_variable_name].iloc[self["mesh"]["tin"][:, 0]],
                               self["node"]["data"][node_variable_name].iloc[self["mesh"]["tin"][:, 1]],
                               self["node"]["data"][node_variable_name].iloc[self["mesh"]["tin"][:, 2]]], axis=0)
        return mesh_values

    def c_mesh_elevation(self):
        self["mesh"]["data"][self.hvum.z.name] = self.c_mesh_mean_from_node_values(self.hvum.z.name)

    def c_mesh_height(self):
        self["mesh"]["data"][self.hvum.h.name] = self.c_mesh_mean_from_node_values(self.hvum.h.name)

    def c_mesh_velocity(self):
        self["mesh"]["data"][self.hvum.v.name] = self.c_mesh_mean_from_node_values(self.hvum.v.name)

    def c_mesh_shear_stress(self):
        self["mesh"]["data"][self.hvum.shear_stress.name] = self.c_mesh_mean_from_node_values(self.hvum.shear_stress.name)

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
        zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * self.hvum.g.value), z2 + h2 + v2 ** 2 / (2 * self.hvum.g.value), z3 + h3 + v3 ** 2 / (
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
        zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * self.hvum.g.value), z2 + h2 + v2 ** 2 / (2 * self.hvum.g.value), z3 + h3 + v3 ** 2 / (
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
            self["mesh"]["data"][self.hvum.froude.name] = self.c_mesh_mean_from_node_values(self.hvum.froude.name)

    def c_mesh_hydraulic_head(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if v and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.v.name in mesh_colnames:
            # compute hydraulic_head = (z + h) + ((v ** 2) / (2 * self.hvum.g.value))
            self["mesh"]["data"][self.hvum.hydraulic_head.name] = self["mesh"]["data"][self.hvum.h.name] + (
                        (self["mesh"]["data"][self.hvum.v.name] ** 2) / (2 * self.hvum.g.value))
        # compute mesh mean
        else:
            self["mesh"]["data"][self.hvum.hydraulic_head.name] = self.c_mesh_mean_from_node_values(self.hvum.hydraulic_head.name)

    def c_mesh_conveyance(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if v and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.v.name in mesh_colnames:
            self["mesh"]["data"][self.hvum.conveyance.name] = self["mesh"]["data"][self.hvum.h.name] * \
                                                              self["mesh"]["data"][self.hvum.v.name]
        # compute mesh mean
        else:
            self["mesh"]["data"][self.hvum.conveyance.name] = self.c_mesh_mean_from_node_values(self.hvum.conveyance.name)

    def c_mesh_water_level(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if z and h mesh existing
        if self.hvum.h.name in mesh_colnames and self.hvum.z.name in mesh_colnames:
            # mesh_water_level from mesh_h and mesh_z
            self["mesh"]["data"][self.hvum.level.name] = np.sum([self["mesh"]["data"][self.hvum.z.name],
                                                        self["mesh"]["data"][self.hvum.h.name]], axis=0)
        else:
            # mesh_water_level
            self["mesh"]["data"][self.hvum.level.name] = self.c_mesh_mean_from_node_values(self.hvum.level.name)

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
        self["node"]["data"][self.hvum.shear_stress.name] = (self["node"]["data"][self.hvum.v_frict.name] ** 2) * self.hvum.ro.value

    def c_node_froude(self):
        # compute froude
        self["node"]["data"][self.hvum.froude.name] = self["node"]["data"][self.hvum.v.name] / np.sqrt(self.hvum.g.value * self["node"]["data"][self.hvum.h.name])
        with pd.option_context('mode.use_inf_as_na', True):
            self["node"]["data"][self.hvum.froude.name] = self["node"]["data"][self.hvum.froude.name].fillna(0)  # divid by 0 return Nan

    def c_node_hydraulic_head(self):
        # TODO: add z for 3d pvd
        # compute hydraulic_head = (z + h) + ((v ** 2) / (2 * self.hvum.g.value))
        self["node"]["data"][self.hvum.hydraulic_head.name] = self["node"]["data"][self.hvum.h.name] + ((self["node"]["data"][self.hvum.v.name] ** 2) / (2 * self.hvum.g.value))

    def c_node_conveyance(self):
        self["node"]["data"][self.hvum.conveyance.name] = self["node"]["data"][self.hvum.h.name] * self["node"]["data"][self.hvum.v.name]

    def c_node_water_level(self):
        self["node"]["data"][self.hvum.level.name] = self["node"]["data"][self.hvum.z.name] + self["node"]["data"][self.hvum.h.name]

    """ other """
    def remove_null_area(self):
        index_to_remove = self["mesh"]["data"][self.hvum.area.name].to_numpy() == 0.0

        if True in index_to_remove:
            # update tin
            self["mesh"][self.hvum.tin.name] = self["mesh"][self.hvum.tin.name][~index_to_remove]

            # update i_whole_profile
            self["mesh"][self.hvum.i_whole_profile.name] = self["mesh"][self.hvum.i_whole_profile.name][~index_to_remove]

            # update mesh data
            self["mesh"]["data"] = self["mesh"]["data"][~index_to_remove]

            print("Warning: " + str(np.sum(index_to_remove)) + " hydraulic triangle(s) "
                    "detected with a null surface in unit " + str(self.unit_num) + ". This is removed.")
