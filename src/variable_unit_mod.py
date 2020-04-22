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
from copy import deepcopy
import numpy as np


class HydraulicVariable:
    def __init__(self, value, unit, name, name_gui, dtype):
        self.value = value  # for ro, g, .. (constant but possible varying ?)
        self.unit = unit
        self.name = name  # to manage them
        self.name_gui = name_gui  # to gui
        self.dtype = dtype
        self.position = None  # node, mesh, (possible face ?)
        self.software_attributes_list = []  # software string names list to link with them
        self.data = [[]]
        self.precomputable_tohdf5 = False  # computable at reading original file to save hdf5
        self.hdf5 = False  # hdf5 or computable
        self.habitat = False  # False: hydraulic and substrate (default) True: Habitat


class HydraulicVariableUnitList(list):
    def __init__(self):
        super().__init__()
        self.names = []
        self.names_gui = []
        self.units = []
        self.dtypes = []

    def append(self, hydraulic_variable):
        """
        with copy
        """
        hydraulic_variable = deepcopy(hydraulic_variable)
        super(HydraulicVariableUnitList, self).append(hydraulic_variable)
        self.names.append(hydraulic_variable.name)
        self.names_gui.append(hydraulic_variable.name_gui)
        self.units.append(hydraulic_variable.unit)
        self.dtypes.append(hydraulic_variable.dtype)

    def extend(self, hydraulic_variable_list):
        """
        without copy
        """
        super(HydraulicVariableUnitList, self).extend(hydraulic_variable_list)
        for hydraulic_variable in hydraulic_variable_list:
            self.names.append(hydraulic_variable.name)
            self.names_gui.append(hydraulic_variable.name_gui)
            self.units.append(hydraulic_variable.unit)
            self.dtypes.append(hydraulic_variable.dtype)

    def remove(self, x):
        index = self.index(x)
        super(HydraulicVariableUnitList, self).remove(x)
        self.names.pop(index)
        self.names_gui.pop(index)
        self.units.pop(index)
        self.dtypes.pop(index)

    def pop(self, index):
        super(HydraulicVariableUnitList, self).pop(index)
        self.names.pop(index)
        self.names_gui.pop(index)
        self.units.pop(index)
        self.dtypes.pop(index)

    def get_nodes(self):
        node_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.position == "node":
                node_list.append(hvu)
        return node_list

    def get_meshs(self):
        mesh_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.position == "mesh":
                mesh_list.append(hvu)
        return mesh_list

    def get_hab(self, tf):
        hab_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.habitat == tf:
                hab_list.append(hvu)
        return hab_list

    def get_hdf5(self, tf):
        hdf5_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.hdf5 == tf:
                hdf5_list.append(hvu)
        return hdf5_list

    def get_dict(self):
        variable_name_unit_dict = dict()

        variable_name_unit_dict["variable_mesh_data_name_list"] = self.get_meshs().names
        variable_name_unit_dict["variable_mesh_data_unit_list"] = self.get_meshs().units

        variable_name_unit_dict["variable_node_data_name_list"] = self.get_nodes().names
        variable_name_unit_dict["variable_node_data_unit_list"] = self.get_nodes().units
        return variable_name_unit_dict

    def get_from_name(self, name):
        return self[self.names.index(name)]


class HydraulicVariableUnitManagement:
    def __init__(self):
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
                                                unit="m",
                                                name="hydraulic_head",
                                                name_gui="hydraulic_head",
                                                dtype=np.float64)
        self.conveyance = HydraulicVariable(value=None,
                                            unit="m²/s",
                                            name="conveyance",
                                            name_gui="conveyance",
                                            dtype=np.float64)
        self.max_slope_bottom = HydraulicVariable(value=None,
                                                  unit="m/m",
                                                  name="max_slope_bottom",
                                                  name_gui="max_slope_bottom",
                                                  dtype=np.float64)
        self.max_slope_energy = HydraulicVariable(value=None,
                                                  unit="m/m",
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
                                         unit="m/s",
                                         name="v_frict",
                                         name_gui="friction velocity",
                                         dtype=np.float64)
        self.sub = HydraulicVariable(value=None,
                                     unit="",
                                     name="sub",
                                     name_gui="substrate",
                                     dtype=np.int64)

        # all variables (like z, all hydraulic variables)
        self.variable_wish_list = HydraulicVariableUnitList()
        self.variable_detected_list = HydraulicVariableUnitList()

        # original and computable hydraulic substrate and habitat variables (hdf5 and computable)
        self.all_available_variable_list = HydraulicVariableUnitList()

        # all wish variables (from user selection)
        self.all_wish_variable_list = HydraulicVariableUnitList()

        # load to data_2d for calchab/plot/export (depend on wish)
        self.all_final_variable_list = HydraulicVariableUnitList()

        # init
        self.v_x_and_v_y_presence = False

        # all_available_variables_list
        self.all_sys_variable_list = HydraulicVariableUnitList()
        for name in vars(self):
            if type(getattr(self, name)) == HydraulicVariable:
                self.all_sys_variable_list.append(getattr(self, name))

    def link_unit_with_software_attribute(self, name, attribute_list, position):
        getattr(self, name).software_attributes_list = attribute_list
        getattr(self, name).position = position
        self.variable_wish_list.append(getattr(self, name))

    def detect_variable_from_software_attribute(self, varnames):
        # detect_variable_from_software_attribute
        for varname_index, varname in enumerate(varnames):
            for usefull_variable_wish in self.variable_wish_list:
                for wish_attribute in usefull_variable_wish.software_attributes_list:
                    if wish_attribute in varname:
                        usefull_variable_wish.varname_index = varname_index
                        self.variable_detected_list.append(usefull_variable_wish)

        # copy an remove z
        self.all_available_variable_list.extend(self.variable_detected_list)
        self.all_available_variable_list.pop(self.all_available_variable_list.names.index(self.z.name))  # not hydraulic

        """ nodes """

        # is v_x and v_y ?
        node_names = self.variable_detected_list.get_nodes().names
        if self.v_x.name in node_names and self.v_y.name in node_names:
            self.v_x_and_v_y_presence = True

        # computed_node_velocity or original ?
        if self.v.name in node_names:
            self.v.precomputable_tohdf5 = False
        elif not self.v.name in node_names and self.v_x_and_v_y_presence:
            self.v.precomputable_tohdf5 = True

        # computed_node_shear_stress or original ?
        if not self.shear_stress.name in node_names and self.v_frict.name in node_names:
            self.shear_stress.precomputable_tohdf5 = True

    def get_original_computable_mesh_and_node_from_hdf5(self, mesh_variable_original_name_list, node_variable_original_name_list):
        # hdf5
        """ mesh """
        for mesh_variable_original_name in mesh_variable_original_name_list:
            variable_mesh = getattr(self, mesh_variable_original_name)
            variable_mesh.position = "mesh"
            variable_mesh.hdf5 = True
            self.all_available_variable_list.append(variable_mesh)

        """ node """
        for node_variable_original_name in node_variable_original_name_list:
            variable_node = getattr(self, node_variable_original_name)
            variable_node.position = "node"
            variable_node.hdf5 = True
            self.all_available_variable_list.append(variable_node)

        # not hdf5
        """ mesh """
        # fix (always v, h, z at node)
        computable_mesh_list = [self.v, self.h,
                               self.level, self.froude, self.hydraulic_head, self.conveyance,
                               self.max_slope_bottom, self.max_slope_energy, self.shear_stress]
        for computed_mesh in computable_mesh_list:
            computed_mesh.position = "mesh"
            computed_mesh.hdf5 = False
            self.all_available_variable_list.append(computed_mesh)

        """ node """
        # fix (always v, h, z at node)
        computable_node_list = [self.level, self.froude, self.hydraulic_head, self.conveyance]
        if self.v_frict.name in self.all_available_variable_list.names:
            computable_node_list.append(self.shear_stress)
        for computed_node in computable_node_list:
            computed_node.position = "node"
            computed_node.hdf5 = False
            self.all_available_variable_list.append(computed_node)

    def get_final_variable_list_from_wish(self, all_wish_variable_list):
        print("######################################")
        print("--------wish---------")
        print("nodes : ", all_wish_variable_list.get_nodes().names)
        print("meshs : ", all_wish_variable_list.get_meshs().names)

        # wish hdf5 (node and mesh)
        for variable_wish in all_wish_variable_list.get_hdf5(True):
            self.all_final_variable_list.append(variable_wish)

        # for each wish node variables, need hdf5 variable to be computed ?
        for variable_wish in all_wish_variable_list.get_hdf5(False).get_nodes():
            # level node ==> need h node
            if variable_wish.name == self.level.name:
                if self.h.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
            # froud node ==> need h and v node
            if variable_wish.name == self.froude.name:
                if self.h.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # hydraulic head node ==> need h and v node
            if variable_wish.name == self.hydraulic_head.name:
                if self.h.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # conveyance node ==> need h and v node
            if variable_wish.name == self.conveyance.name:
                if self.h.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.get_hdf5(False).get_nodes().names:
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)

            # all cases
            self.all_final_variable_list.append(variable_wish)

        # for each wish mesh variables, need hdf5 variable to be computed ?
        for variable_wish in all_wish_variable_list.get_hdf5(False).get_meshs():
            # v mesh ==> need first : v mesh hdf5 (FinitVolume)
            if variable_wish.name == self.v.name:
                # (FinitVolume)
                if self.v.name in self.all_final_variable_list.get_hdf5(True).get_meshs().names:
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
                # compute mean from node
                elif self.v.name not in self.all_final_variable_list.get_hdf5(True).get_nodes().names:
                    self.v.position = "node"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # h mesh ==> need first : h mesh hdf5 (FinitVolume)
            if variable_wish.name == self.h.name:
                # (FinitVolume)
                if self.h.name in self.all_final_variable_list.get_hdf5(True).get_meshs().names:
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                # compute mean from node
                elif self.h.name not in self.all_final_variable_list.get_hdf5(True).get_nodes().names:
                    self.h.position = "node"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
            # level mesh ==> need first : level mesh hdf5 (FinitVolume)
            if variable_wish.name == self.level.name:
                # (FinitVolume)
                if self.h.name in self.all_final_variable_list.get_hdf5(True).get_meshs().names:
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                # compute mean from node
                elif self.h.name not in self.all_final_variable_list.get_hdf5(True).get_nodes().names:
                    self.h.position = "node"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
            # # level mesh ==> need first : level mesh hdf5 (FinitVolume)
            # if variable_wish.name == self.level.name:
            #     # (FinitVolume)
            #     if self.h.name in self.all_final_variable_list.get_hdf5(True).get_meshs().names:
            #         self.h.position = variable_wish.position
            #         self.h.hdf5 = True
            #         self.all_final_variable_list.append(self.h)
            #     # compute mean from node
            #     elif self.h.name not in self.all_final_variable_list.get_hdf5(True).get_nodes().names:
            #         self.h.position = "node"
            #         self.h.hdf5 = True
            #         self.all_final_variable_list.append(self.h)


            # all cases
            self.all_final_variable_list.append(variable_wish)

        # print final names
        print("--------final---------")
        print("nodes : ", self.all_final_variable_list.get_nodes().names)
        print("meshs : ", self.all_final_variable_list.get_meshs().names)


