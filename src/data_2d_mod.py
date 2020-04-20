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
import sys
import pandas as pd

from src.manage_grid_mod import is_duplicates_mesh_and_point_on_one_unit, linear_z_cross
from src.variable_unit_mod import HydraulicVariableUnitManagement


class Data2d(list):
    def __init__(self):
        super().__init__()
        self.reach_num = 0
        self.unit_num = 0
        self.hvum = HydraulicVariableUnitManagement()

    def get_informations(self):
        self.reach_num = len(self)
        if self.reach_num:
            self.unit_num = len(self[self.reach_num - 1])

    def get_only_mesh(self):
        """
        retrun whole_profile from original data2d
        """
        self.get_informations()

        whole_profile = Data2d()
        for reach_num in range(self.reach_num):
            unit_list = []
            for unit_num in range(self.unit_num):
                unit_dict = UnitDict()
                unit_dict["mesh"] = dict(tin=self[reach_num][unit_num]["mesh"]["tin"])
                unit_dict["node"] = dict(xy=self[reach_num][unit_num]["node"]["xy"],
                                         z=self[reach_num][unit_num]["node"]["z"])
                # append by unit
                unit_list.append(unit_dict)
                # append by reach
            whole_profile.append(unit_list)

        whole_profile.get_informations()

        return whole_profile

    def add_reach(self, data_2d_new, reach_num):
        self.get_informations()
        self.append(data_2d_new[reach_num])

        # TODO: check if same units number and name

        # update attrs
        self.get_informations()
        self.hvum = data_2d_new.hvum

    def add_unit(self,  data_2d_new, reach_num):
        self.get_informations()
        if not self.reach_num:
            self.append([])
        self[reach_num].extend(data_2d_new[reach_num])

        # TODO: check if same units number and name

        # update attrs
        self.get_informations()
        self.hvum = data_2d_new.hvum

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

    def cut_2d(self, unit_list, progress_value, delta_file, CutMeshPartialyDry, min_height):
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
                water_height = self[reach_num][unit_num]["node"]["data"]["h"].to_numpy()
                # velocity = self[reach_num][unit_num]["node"]["data"]["v"].to_numpy()

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
                    # velocity_ok = velocity
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
                # change all node dataframe
                # velocity_ok = velocity[ipt_iklenew_unique]
                self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].loc[ipt_iklenew_unique]

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
                    # velocity_ok = np.append(velocity_ok, np.zeros(lpns - nbdouble, dtype=velocity.dtype), axis=0)
                    # new pandas dataframe (to be added to the end)
                    zero_pd = pd.DataFrame(0, index=np.arange(lpns - nbdouble),
                                 columns=self[reach_num][unit_num]["node"]["data"].columns.values)
                    self[reach_num][unit_num]["node"]["data"] = self[reach_num][unit_num]["node"]["data"].append(zero_pd)
                    self[reach_num][unit_num]["node"]["data"]["h"] = water_height_ok

                # erase old data
                self[reach_num][unit_num]["mesh"]["tin"] = iklekeep
                self[reach_num][unit_num]["mesh"]["i_whole_profile"] = ind_whole
                self[reach_num][unit_num]["node"]["xy"] = point_all_ok[:, :2]
                self[reach_num][unit_num]["node"]["z"] = point_all_ok[:, 2]

                #  unit_list_cuted
                self.unit_list_cuted[reach_num].append(unit_name)

                # progress
                progress_value.value += int(deltaunit)

    def compute_variables(self, variable_computable_list):
        """
        Compute all necessary variables.
        :param node_variable_list:
        :param mesh_variable_list:
        :return:
        """
        self.get_informations()

        node_variable_list = variable_computable_list.get_nodes()
        if node_variable_list:
            # for all reach
            for reach_num in range(0, self.reach_num):
                # for all units
                for unit_num in range(0, self.unit_num):
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

        mesh_variable_list = variable_computable_list.get_meshs()
        if mesh_variable_list:
            # for all reach
            for reach_num in range(0, self.reach_num):
                # for all units
                for unit_num in range(0, self.unit_num):
                    """ mesh """
                    for mesh_variable in mesh_variable_list:
                        # compute height mean
                        if mesh_variable.name == self.hvum.h.name:
                            self[reach_num][unit_num].c_mesh_mean_height()
                        # compute velocity mean
                        elif mesh_variable.name == self.hvum.v.name:
                            self[reach_num][unit_num].c_mesh_mean_velocity()
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
                        # compute shear_stress
                        elif mesh_variable.name == self.hvum.shear_stress.name:
                            self[reach_num][unit_num].c_mesh_shear_stress()


class UnitDict(dict):
    def __init__(self):
        super().__init__()
        # HydraulicVariableUnit
        self.hvum = HydraulicVariableUnitManagement()

    # mesh
    """ COMPUTATION """

    def c_mesh_mean_from_node_values(self, node_variable_name):
        mesh_values = np.mean([self["node"]["data"][node_variable_name][self["mesh"]["tin"][:, 0]],
                               self["node"]["data"][node_variable_name][self["mesh"]["tin"][:, 1]],
                               self["node"]["data"][node_variable_name][self["mesh"]["tin"][:, 2]]], axis=0)
        return mesh_values

    def c_mesh_mean_height(self):
        self["mesh"]["data"][self.hvum.h.name] = self.c_mesh_mean_from_node_values(self.hvum.h.name)

    def c_mesh_mean_velocity(self):
        self["mesh"]["data"][self.hvum.v.name] = self.c_mesh_mean_from_node_values(self.hvum.v.name)

    def c_mesh_max_slope_bottom(self):
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"]["z"][self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"]["z"][self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"]["z"][self["mesh"]["tin"][:, 2]]

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
            max_slope_bottom[max_slope_bottom > 0.55] = np.NaN  # 0.55

        self["mesh"]["data"][self.hvum.max_slope_bottom] = max_slope_bottom

    def c_mesh_max_slope_energy(self):
        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"][self.hvum.z.name][self["mesh"]["tin"][:, 0]]
        h1 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        v1 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"][self.hvum.z.name][self["mesh"]["tin"][:, 1]]
        h2 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        v2 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"][self.hvum.z.name][self["mesh"]["tin"][:, 2]]
        h3 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 2]]
        v3 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 2]]

        GRAVITY = HydraulicVariableUnitManagement().g.value

        w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
        zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * GRAVITY), z2 + h2 + v2 ** 2 / (2 * GRAVITY), z3 + h3 + v3 ** 2 / (
                    2 * GRAVITY)
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

    def c_mesh_shear_stress(self):
        ro = HydraulicVariableUnitManagement().ro.value
        GRAVITY = HydraulicVariableUnitManagement().g.value

        xy1 = self["node"]["xy"][self["mesh"]["tin"][:, 0]]
        z1 = self["node"][self.hvum.z.name][self["mesh"]["tin"][:, 0]]
        h1 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        v1 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 0]]
        xy2 = self["node"]["xy"][self["mesh"]["tin"][:, 1]]
        z2 = self["node"][self.hvum.z.name][self["mesh"]["tin"][:, 1]]
        h2 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        v2 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 1]]
        xy3 = self["node"]["xy"][self["mesh"]["tin"][:, 2]]
        z3 = self["node"][self.hvum.z.name][self["mesh"]["tin"][:, 2]]
        h3 = self["node"]["data"][self.hvum.h.name].to_numpy()[self["mesh"]["tin"][:, 2]]
        v3 = self["node"]["data"][self.hvum.v.name].to_numpy()[self["mesh"]["tin"][:, 2]]

        w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
        zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * GRAVITY), z2 + h2 + v2 ** 2 / (2 * GRAVITY), z3 + h3 + v3 ** 2 / (
                    2 * GRAVITY)
        u = (xy2[:, 1] - xy1[:, 1]) * (zz3 - zz1) - (zz2 - zz1) * (xy3[:, 1] - xy1[:, 1])
        v = (xy3[:, 0] - xy1[:, 0]) * (zz2 - zz1) - (zz3 - zz1) * (xy2[:, 0] - xy1[:, 0])
        with np.errstate(divide='ignore', invalid='ignore'):
            max_slope_energy = np.sqrt(u ** 2 + v ** 2) / np.abs(w)
        shear_stress = ro * GRAVITY * (h1 + h2 + h3) * max_slope_energy / 3

        # change inf values to nan
        if np.inf in shear_stress:
            shear_stress[shear_stress == np.inf] = np.NaN

        # change incoherent values to nan
        with np.errstate(invalid='ignore'):  # ignore warning due to NaN values
            shear_stress[shear_stress > 800] = np.NaN  # 800

        self["mesh"]["data"][self.hvum.shear_stress.name] = shear_stress

    def c_mesh_froude(self):
        # if not froud at node
        if not self.hvum.froude.name in self["node"]["data"].columns.tolist():
            # c_node_froude
            self.c_node_froude()

        # compute mesh mean
        self["mesh"]["data"][self.hvum.froude.name] = self.c_mesh_mean_from_node_values(self.hvum.froude.name)

    def c_mesh_hydraulic_head(self):
        # if not hydraulic_head at nodes
        if not self.hvum.hydraulic_head.name in self["node"]["data"].columns.tolist():
            # c_node_hydraulic_head
            self.c_node_hydraulic_head()

        # compute mesh mean
        self["mesh"]["data"][self.hvum.hydraulic_head.name] = self.c_mesh_mean_from_node_values(self.hvum.hydraulic_head.name)

    def c_mesh_conveyance(self):
        # if not hydraulic_head at nodes
        if not self.hvum.conveyance.name in self["node"]["data"].columns.tolist():
            # c_node_conveyance
            self.c_node_conveyance()

        # compute mesh mean
        self["mesh"]["data"][self.hvum.conveyance.name] = self.c_mesh_mean_from_node_values(self.hvum.conveyance.name)

    def c_mesh_water_level(self):
        mesh_colnames = self["mesh"]["data"].columns.tolist()
        # if z and h mesh existing
        if self.hvum.z.name in mesh_colnames and self.hvum.h.name in mesh_colnames:
            # mesh_water_level from mesh_h and mesh_z
            self["mesh"]["data"][self.hvum.level.name] = np.mean([self["mesh"]["data"][self.hvum.z.name],
                                                        self["mesh"]["data"][self.hvum.h.name]], axis=0)
        else:
            # node_water_level
            self.c_node_water_level()
            # mesh_water_level
            self["mesh"]["data"][self.hvum.level.name] = self.c_mesh_mean_from_node_values(self.hvum.level.name)

    def c_mesh_area(self, tin, xy):
        # get points coord
        pa = xy[tin[:, 0]]
        pb = xy[tin[:, 1]]
        pc = xy[tin[:, 2]]

        # compute area
        area = 0.5 * abs((pb[:, 0] - pa[:, 0]) * (pc[:, 1] - pa[:, 1]) - (pc[:, 0] - pa[:, 0]) * (
                pb[:, 1] - pa[:, 1]))

        return area

    # node
    def c_node_froude(self):
        GRAVITY = HydraulicVariableUnitManagement().g.value
        # compute froude
        self["node"]["data"][self.hvum.froude.name] = self["node"]["data"][self.hvum.v.name] / np.sqrt(GRAVITY * self["node"]["data"][self.hvum.h.name])
        self["node"]["data"][self.hvum.froude.name] = self["node"]["data"][self.hvum.froude.name].fillna(0)  # divid by 0 return Nan

    def c_node_hydraulic_head(self):
        GRAVITY = HydraulicVariableUnitManagement().g.value
        # TODO: add z for 3d pvd
        # compute hydraulic_head = (z + h) + ((v ** 2) / (2 * GRAVITY))
        self["node"]["data"][self.hvum.hydraulic_head.name] = self["node"]["data"][self.hvum.h.name] + ((self["node"]["data"][self.hvum.v.name] ** 2) / (2 * GRAVITY))

    def c_node_conveyance(self):
        self["node"]["data"][self.hvum.conveyance.name] = self["node"]["data"][self.hvum.h.name] * self["node"]["data"][self.hvum.v.name]

    def c_node_water_level(self):
        self["node"]["data"][self.hvum.level.name] = self["node"][self.hvum.z.name] + self["node"]["data"][self.hvum.h.name]

    def c_node_shear_stress(self):
        self["node"]["data"][self.hvum.shear_stress.name] = (self["node"]["data"][self.hvum.v_frict.name] ** 2) * self.hvum.ro.value

