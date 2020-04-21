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
        self.value = value
        self.unit = unit
        self.name = name
        self.name_gui = name_gui
        self.dtype = dtype
        self.position = None
        self.software_attributes_list = []
        self.data = [[]]
        self.computable = False


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
                                         unit="",
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

        # hydraulic variable
        self.variable_data_detected_list = HydraulicVariableUnitList()

        # original
        self.variable_original_list = HydraulicVariableUnitList()

        # computable
        self.variable_computable_list = HydraulicVariableUnitList()

        # habitat
        self.variable_habitat_list = HydraulicVariableUnitList()

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
        self.variable_data_detected_list.extend(self.variable_detected_list)
        self.variable_data_detected_list.pop(self.variable_data_detected_list.names.index(self.z.name))

        """ nodes """

        # is v_x and v_y ?
        node_names = self.variable_detected_list.get_nodes().names
        if self.v_x.name in node_names and self.v_y.name in node_names:
            self.v_x_and_v_y_presence = True

        # computed_node_velocity or original ?
        if self.v.name in node_names:
            self.v.original = True
            self.v.computable = False
        if not self.v.name in node_names and self.v_x_and_v_y_presence:
            self.v.original = False
            self.v.computable = True
            self.variable_data_detected_list.append(self.v)  # always v

        # computed_node_shear_stress or original ?
        if not self.shear_stress.name in node_names and self.v_frict.name in node_names:
            self.shear_stress.computable = True
            self.variable_data_detected_list.append(self.shear_stress)

    def get_original_computable_mesh_and_node_from_original_name(self, mesh_variable_original_name_list, node_variable_original_name_list):
        """ mesh """
        for mesh_variable_original_name in mesh_variable_original_name_list:
            variable_mesh = getattr(self, mesh_variable_original_name)
            variable_mesh.position = "mesh"
            self.variable_original_list.append(variable_mesh)

        """ node """
        for node_variable_original_name in node_variable_original_name_list:
            variable_node = getattr(self, node_variable_original_name)
            variable_node.position = "node"
            self.variable_original_list.append(variable_node)

        # get_computable_mesh_and_node_from_original
        self.get_computable_mesh_and_node_from_original()

    def get_computable_mesh_and_node_from_original(self):
        """ mesh """
        # fix (always v, h, z at node)
        computable_mesh_list = [self.v, self.h,
                               self.level, self.froude, self.hydraulic_head, self.conveyance,
                               self.max_slope_bottom, self.max_slope_energy, self.shear_stress]
        for computed_mesh in computable_mesh_list:
            computed_mesh.position = "mesh"
            self.variable_computable_list.append(computed_mesh)

        """ node """
        # fix (always v, h, z at node)
        computable_node_list = [self.level, self.froude, self.hydraulic_head, self.conveyance]
        if self.v_frict.name in self.variable_original_list.names:
            computable_node_list.append(self.shear_stress)
        for computed_node in computable_node_list:
            computed_node.position = "node"
            self.variable_computable_list.append(computed_node)

    def get_original_computable_mesh_and_node_from_dict_gui(self, dict_gui):
        # init
        self.variable_original_list.__init__()
        self.variable_computable_list.__init__()

        """ mesh """
        if "mesh_variable_original_list" in dict_gui.keys():
            for mesh_variable_original_namegui in dict_gui["mesh_variable_original_list"]:
                mesh_variable_original = self.all_sys_variable_list[self.all_sys_variable_list.names_gui.index(mesh_variable_original_namegui)]
                mesh_variable_original.position = "mesh"
                self.variable_original_list.append(mesh_variable_original)
        if "mesh_variable_computable_list" in dict_gui.keys():
            for mesh_variable_computable_namegui in dict_gui["mesh_variable_computable_list"]:
                mesh_variable_computable = self.all_sys_variable_list[self.all_sys_variable_list.names_gui.index(mesh_variable_computable_namegui)]
                mesh_variable_computable.position = "mesh"
                self.variable_computable_list.append(mesh_variable_computable)

        """ node """
        if "node_variable_original_list" in dict_gui.keys():
            for node_variable_original_namegui in dict_gui["node_variable_original_list"]:
                node_variable_original = self.all_sys_variable_list[self.all_sys_variable_list.names_gui.index(node_variable_original_namegui)]
                node_variable_original.position = "node"
                self.variable_original_list.append(node_variable_original)
        if "node_variable_computable_list" in dict_gui.keys():
            for node_variable_computable_namegui in dict_gui["node_variable_computable_list"]:
                node_variable_computable = self.all_sys_variable_list[self.all_sys_variable_list.names_gui.index(node_variable_computable_namegui)]
                node_variable_computable.position = "node"
                self.variable_computable_list.append(node_variable_computable)

        # TODO: habitat variables
