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
    def __init__(self, value, unit, name, name_gui, dtype, index_gui=0):
        self.name = name  # to manage them
        self.name_gui = name_gui  # to gui
        self.unit = unit
        self.dtype = dtype  # float64 or int64
        self.software_attributes_list = []  # software string names list to link with them
        self.position = None  # node, mesh, (possible face ?)
        self.value = value  # for ro, g, .. (constant but possible varying ?)
        self.data = [[]]
        self.precomputable_tohdf5 = False  # computable at reading original file to save hdf5
        self.hdf5 = False  # hdf5 or computable
        self.habitat = False  # False: hydraulic and substrate (default) True: Habitat
        self.index_gui = index_gui  # position index in gui


class HydraulicVariableUnitList(list):
    def __init__(self):
        super().__init__()

    def append(self, hydraulic_variable):
        """
        with copy
        """
        hydraulic_variable = deepcopy(hydraulic_variable)
        super(HydraulicVariableUnitList, self).append(hydraulic_variable)
        #self.sort_by_names_gui()

    def extend(self, hydraulic_variable_list):
        """
        without copy
        """
        super(HydraulicVariableUnitList, self).extend(hydraulic_variable_list)
        #self.sort_by_names_gui()

    def sort_by_names_gui(self):
        self.sort(key=lambda el: el.index_gui)  # , reverse=True

    def remove(self, x):
        super(HydraulicVariableUnitList, self).remove(x)

    def pop(self, index):
        super(HydraulicVariableUnitList, self).pop(index)

    """ get attribute list """
    def names(self):
        names_list = []
        for hvu in self:
            names_list.append(hvu.name)
        return names_list

    def names_gui(self):
        names_gui_list = []
        for hvu in self:
            names_gui_list.append(hvu.name_gui)
        return names_gui_list

    def units(self):
        units_list = []
        for hvu in self:
            units_list.append(hvu.unit)
        return units_list

    """ filters """
    def nodes(self):
        node_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.position == "node":
                node_list.append(hvu)
        return node_list

    def meshs(self):
        mesh_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.position == "mesh":
                mesh_list.append(hvu)
        return mesh_list

    def habs(self):
        hab_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.habitat:
                hab_list.append(hvu)
        return hab_list

    def no_habs(self):
        no_hab_list = HydraulicVariableUnitList()
        for hvu in self:
            if not hvu.habitat:
                no_hab_list.append(hvu)
        return no_hab_list

    def hdf5s(self):
        hdf5_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.hdf5:
                hdf5_list.append(hvu)
        return hdf5_list

    def to_compute(self):
        to_compute_list = HydraulicVariableUnitList()
        for hvu in self:
            if not hvu.hdf5:
                to_compute_list.append(hvu)
        return to_compute_list

    """ select """
    def get_from_name(self, name):
        return self[self.names().index(name)]

    def get_from_name_gui(self, name_gui):
        return self[self.names_gui().index(name_gui)]


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
                                   dtype=np.float64,
                                   index_gui=0)
        # usefull variable values
        self.h = HydraulicVariable(value=None,
                                   unit="m",
                                   name="h",
                                   name_gui="water depth",
                                   dtype=np.float64,
                                   index_gui=1)
        self.v = HydraulicVariable(value=None,
                                   unit="m/s",
                                   name="v",
                                   name_gui="water velocity",
                                   dtype=np.float64,
                                   index_gui=2)
        self.sub = HydraulicVariable(value=None,
                                     unit="",
                                     name="sub",
                                     name_gui="substrate",
                                     dtype=np.int64,
                                     index_gui=3)
        self.v_x = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_x",
                                     name_gui="water velocity x",
                                     dtype=np.float64,
                                     index_gui=4)
        self.v_y = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_y",
                                     name_gui="water velocity y",
                                     dtype=np.float64,
                                     index_gui=5)
        self.v_frict = HydraulicVariable(value=None,
                                         unit="m/s",
                                         name="v_frict",
                                         name_gui="water velocity friction",
                                         dtype=np.float64,
                                         index_gui=6)
        self.shear_stress = HydraulicVariable(value=None,
                                              unit="N/m²",
                                              name="shear_stress",
                                              name_gui="shear stress",
                                              dtype=np.float64,
                                              index_gui=7)
        self.shear_stress_beta = HydraulicVariable(value=None,
                                                   unit="N/m²",
                                                   name="shear_stress_beta",
                                                   name_gui="shear stress beta",
                                                   dtype=np.float64,
                                                   index_gui=8)
        self.level = HydraulicVariable(value=None,
                                       unit="m",
                                       name="level",
                                       name_gui="water level",
                                       dtype=np.float64,
                                       index_gui=9)
        self.froude = HydraulicVariable(value=None,
                                        unit="",
                                        name="froude",
                                        name_gui="froude number",
                                        dtype=np.float64,
                                        index_gui=10)
        self.hydraulic_head = HydraulicVariable(value=None,
                                                unit="m",
                                                name="hydraulic_head",
                                                name_gui="hydraulic head",
                                                dtype=np.float64,
                                                index_gui=11)
        self.conveyance = HydraulicVariable(value=None,
                                            unit="m²/s",
                                            name="conveyance",
                                            name_gui="conveyance",
                                            dtype=np.float64,
                                            index_gui=12)
        self.max_slope_bottom = HydraulicVariable(value=None,
                                                  unit="m/m",
                                                  name="max_slope_bottom",
                                                  name_gui="max slope bottom",
                                                  dtype=np.float64,
                                                  index_gui=13)
        self.max_slope_energy = HydraulicVariable(value=None,
                                                  unit="m/m",
                                                  name="max_slope_energy",
                                                  name_gui="max slope energy",
                                                  dtype=np.float64,
                                                  index_gui=14)
        self.temp = HydraulicVariable(value=None,
                                      unit="",
                                      name="temp",
                                      name_gui="temperature",
                                      dtype=np.float64,
                                      index_gui=15)

        # all_available_variables_list
        self.all_sys_variable_list = HydraulicVariableUnitList()
        for name in vars(self):
            if type(getattr(self, name)) == HydraulicVariable:
                self.all_sys_variable_list.append(getattr(self, name))

        # software_target_list
        self.software_target_list = HydraulicVariableUnitList()

        # software_detected_list
        self.software_detected_list = HydraulicVariableUnitList()

        # hdf5_and_computable_list
        self.hdf5_and_computable_list = HydraulicVariableUnitList()

        # user_target_list
        self.user_target_list = HydraulicVariableUnitList()

        # load to data_2d for calchab/plot/export (depend on wish)
        self.all_final_variable_list = HydraulicVariableUnitList()

    def link_unit_with_software_attribute(self, name, attribute_list, position):
        getattr(self, name).software_attributes_list = attribute_list
        getattr(self, name).position = position
        self.software_target_list.append(getattr(self, name))

    def detect_variable_from_software_attribute(self, varnames):
        # detect_variable_from_software_attribute
        for varname_index, varname in enumerate(varnames):
            for usefull_variable_wish in self.software_target_list:
                for wish_attribute in usefull_variable_wish.software_attributes_list:
                    if wish_attribute in varname:
                        usefull_variable_wish.varname_index = varname_index
                        self.software_detected_list.append(usefull_variable_wish)
        self.software_detected_list.sort_by_names_gui()  # sort

        # copy
        self.hdf5_and_computable_list.extend(self.software_detected_list)

        """ required variable nodes """
        node_names = self.hdf5_and_computable_list.nodes().names()

        # always z, if not detect : compute (FV to FE)
        if self.z.name not in node_names:
            self.z.position = "node"
            self.z.precomputable_tohdf5 = True
            self.hdf5_and_computable_list.append(self.z)
        if self.h.name not in node_names:
            self.h.position = "node"
            self.h.precomputable_tohdf5 = True
            self.hdf5_and_computable_list.append(self.h)
        # always v but computed_node_velocity or original ?
        if self.v.name not in node_names:
            self.v.position = "node"
            if self.v_x.name in node_names and self.v_y.name in node_names:
                self.v.precomputable_tohdf5 = True
            else:
                self.v.precomputable_tohdf5 = False
            self.hdf5_and_computable_list.append(self.v)

    def get_original_computable_mesh_and_node_from_hdf5(self, mesh_variable_original_name_list, node_variable_original_name_list):
        # hdf5
        """ mesh """
        for mesh_variable_original_name in mesh_variable_original_name_list:
            variable_mesh = getattr(self, mesh_variable_original_name)
            variable_mesh.position = "mesh"
            variable_mesh.hdf5 = True
            self.hdf5_and_computable_list.append(variable_mesh)

        """ node """
        for node_variable_original_name in node_variable_original_name_list:
            variable_node = getattr(self, node_variable_original_name)
            variable_node.position = "node"
            variable_node.hdf5 = True
            self.hdf5_and_computable_list.append(variable_node)

        # computable
        """ mesh """
        computable_mesh_list = [self.v, self.h, self.z, self.level, self.froude, self.hydraulic_head,
                                self.conveyance, self.max_slope_bottom, self.max_slope_energy]
        # shear_stress
        if self.v_frict.name in self.hdf5_and_computable_list.names():
            computable_mesh_list.append(self.shear_stress)
        # shear_stress_beta
        computable_mesh_list.append(self.shear_stress_beta)
        for computed_mesh in computable_mesh_list:
            if computed_mesh.name not in mesh_variable_original_name_list:
                computed_mesh.position = "mesh"
                computed_mesh.hdf5 = False
                self.hdf5_and_computable_list.append(computed_mesh)

        """ node """
        computable_node_list = [self.level, self.froude, self.hydraulic_head, self.conveyance]
        if self.v_frict.name in self.hdf5_and_computable_list.names():
            self.shear_stress.position = "node"
            self.shear_stress.hdf5 = False
            computable_node_list.append(self.shear_stress)
        for computed_node in computable_node_list:
            if computed_node.name not in node_variable_original_name_list:
                computed_node.position = "node"
                computed_node.hdf5 = False
                self.hdf5_and_computable_list.append(computed_node)

        # sort_by_names_gui
        self.hdf5_and_computable_list.sort_by_names_gui()

    def get_final_variable_list_from_project_preferences(self, project_preferences, hdf5_type):
        """
        Get all variables to compute from dict (project_preferences) for exports.
        :return:
        """
        # INDEX IF HYD OR HAB
        if hdf5_type == "hydraulic":
            index = 0
        else:
            index = 1

        mesh = False
        node = False
        # get_variables_from_dict
        if project_preferences["mesh_units"][index]:
            mesh = True
        if project_preferences["point_units"][index]:
            node = True
        if project_preferences["detailled_text"][index]:
            mesh = True
            node = True
        if project_preferences["variables_units"][index]:
            mesh = True
            node = True
            # pvd_variable_z ?

        if node and mesh:
            user_target_list = self.hdf5_and_computable_list
        else:
            if mesh:
                user_target_list = self.hdf5_and_computable_list.meshs()
            elif node:
                user_target_list = self.hdf5_and_computable_list.nodes()
            else:  # whole profile == no data
                user_target_list = None

        if user_target_list is not None:
            self.get_final_variable_list_from_wish(user_target_list)

    def get_final_variable_list_from_wish(self, user_target_list):
        """
        load hdf5 or compute ? Depend on user wish selection
        """
        print("######################################")
        print("-------- variables wish ---------")
        print("nodes : ", user_target_list.nodes().names())
        print("meshs : ", user_target_list.meshs().names())

        # wish hdf5 (node and mesh)
        for variable_wish in user_target_list.hdf5s():
            self.all_final_variable_list.append(variable_wish)

        """ node """
        # for each wish node variables, need hdf5 variable to be computed ?
        for variable_wish in user_target_list.to_compute().nodes():
            # shear_stress node ==> need v_frict node
            if variable_wish.name == self.shear_stress.name:
                if self.v_frict.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v_frict.position = variable_wish.position
                    self.v_frict.hdf5 = True
                    self.all_final_variable_list.append(self.v_frict)

            # variables never in hdf

            # level node ==> need h node
            elif variable_wish.name == self.level.name:
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.z.position = variable_wish.position
                    self.z.hdf5 = True
                    self.all_final_variable_list.append(self.z)
            # froud node ==> need h and v node
            elif variable_wish.name == self.froude.name:
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # hydraulic head node ==> need h and v node
            elif variable_wish.name == self.hydraulic_head.name:
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # conveyance node ==> need h and v node
            elif variable_wish.name == self.conveyance.name:
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = variable_wish.position
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = variable_wish.position
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)

            # all cases
            self.all_final_variable_list.append(variable_wish)

        """ mesh """
        # for each wish mesh variables, need hdf5 variable to be computed ?
        for variable_wish in user_target_list.to_compute().meshs():
            # z
            if variable_wish.name == self.z.name:
                # hec-ras ?
                if self.z.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                    pass
                else:
                    # already added?
                    if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        self.z.position = "node"
                        self.z.hdf5 = True
                        self.all_final_variable_list.append(self.z)
            # v mesh ==> need first : v mesh hdf5 (FinitVolume)
            if variable_wish.name == self.v.name:
                # (FinitVolume)
                if self.v.name in self.all_final_variable_list.hdf5s().meshs().names():
                    self.v.position = "mesh"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
                # compute mean from node
                elif self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = "node"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # h mesh ==> need first : h mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.h.name:
                # (FinitVolume)
                if self.h.name in self.all_final_variable_list.hdf5s().meshs().names():
                    self.h.position = "mesh"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                # compute mean from node
                elif self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = "node"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
            # shear_stress mesh ==> need first : h mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.shear_stress.name:
                # shear_stress at mesh ?
                if self.shear_stress.name not in self.hdf5_and_computable_list.hdf5s().meshs().names():
                    if self.v_frict.name in self.hdf5_and_computable_list.hdf5s().nodes().names():
                        if self.shear_stress.name not in self.all_final_variable_list.to_compute().nodes().names():
                            self.shear_stress.position = "node"
                            self.shear_stress.hdf5 = False
                            self.all_final_variable_list.append(self.shear_stress)
                        if self.v_frict.name not in self.all_final_variable_list.hdf5s().nodes().names():
                            self.v_frict.position = "node"
                            self.v_frict.hdf5 = True
                            self.all_final_variable_list.append(self.v_frict)

            # variables never in hdf

            # shear_stress_beta mesh ==> need first : h mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.shear_stress_beta.name:
                if self.z.name not in self.all_final_variable_list.to_compute().nodes().names():
                    self.z.position = "node"
                    self.z.hdf5 = True
                    self.all_final_variable_list.append(self.z)
                if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = "node"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = "node"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)

            # level mesh ==> need first : h mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.level.name:
                # (FinitVolume)
                if self.h.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                    if self.h.name not in self.all_final_variable_list.hdf5s().meshs().names():
                        self.h.position = "mesh"
                        self.h.hdf5 = True
                        self.all_final_variable_list.append(self.h)
                    if self.z.name not in self.all_final_variable_list.hdf5s().meshs().names():
                        self.z.position = "mesh"
                        self.z.hdf5 = True
                        self.all_final_variable_list.append(self.z)
                else:
                    # compute mean from node (need h node)
                    if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        self.h.position = "node"
                        self.h.hdf5 = True
                        self.all_final_variable_list.append(self.h)
                    if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        self.z.position = "node"
                        self.z.hdf5 = True
                        self.all_final_variable_list.append(self.z)
                    # compute mean from node (need level node)
                    if self.level.name not in self.all_final_variable_list.to_compute().nodes().names():
                        self.level.position = "node"
                        self.level.hdf5 = False
                        self.all_final_variable_list.append(self.level)
            # froude mesh ==> need first : h and v mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.froude.name:
                # FinitVolume ?
                if self.h.name in self.hdf5_and_computable_list.hdf5s().meshs().names() and self.v.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                    # already added?
                    if self.h.name not in self.all_final_variable_list.hdf5s().meshs().names() and not self.v.name in self.all_final_variable_list.hdf5s().meshs().names():
                        self.h.position = "mesh"
                        self.h.hdf5 = True
                        self.all_final_variable_list.append(self.h)
                        self.v.position = "mesh"
                        self.v.hdf5 = True
                        self.all_final_variable_list.append(self.v)
                else:
                    # compute at node
                    if self.froude.name not in self.all_final_variable_list.to_compute().nodes().names():
                        self.froude.position = "node"
                        self.froude.hdf5 = False
                        self.all_final_variable_list.append(self.froude)
                        if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names() and self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                            self.h.position = "node"
                            self.h.hdf5 = True
                            self.all_final_variable_list.append(self.h)
                            self.v.position = "node"
                            self.v.hdf5 = True
                            self.all_final_variable_list.append(self.v)
            # hydraulic_head mesh ==> need first : h and v mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.hydraulic_head.name:
                # FinitVolume ?
                if self.h.name in self.hdf5_and_computable_list.hdf5s().meshs().names() and self.v.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                    # already added?
                    if self.h.name not in self.all_final_variable_list.hdf5s().meshs().names() and not self.v.name in self.all_final_variable_list.hdf5s().meshs().names():
                        self.h.position = "mesh"
                        self.h.hdf5 = True
                        self.all_final_variable_list.append(self.h)
                        self.v.position = "mesh"
                        self.v.hdf5 = True
                        self.all_final_variable_list.append(self.v)
                else:
                    # compute at node
                    if self.hydraulic_head.name not in self.all_final_variable_list.to_compute().nodes().names():
                        self.hydraulic_head.position = "node"
                        self.hydraulic_head.hdf5 = False
                        self.all_final_variable_list.append(self.hydraulic_head)
                        if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names() and self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                            self.h.position = "node"
                            self.h.hdf5 = True
                            self.all_final_variable_list.append(self.h)
                            self.v.position = "node"
                            self.v.hdf5 = True
                            self.all_final_variable_list.append(self.v)
            # conveyance mesh ==> need first : h and v mesh hdf5 (FinitVolume)
            elif variable_wish.name == self.conveyance.name:
                # FinitVolume ?
                if self.h.name in self.hdf5_and_computable_list.hdf5s().meshs().names() and self.v.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                    # already added?
                    if self.h.name not in self.all_final_variable_list.hdf5s().meshs().names() and not self.v.name in self.all_final_variable_list.hdf5s().meshs().names():
                        self.h.position = "mesh"
                        self.h.hdf5 = True
                        self.all_final_variable_list.append(self.h)
                        self.v.position = "mesh"
                        self.v.hdf5 = True
                        self.all_final_variable_list.append(self.v)
                else:
                    # compute at node
                    if self.conveyance.name not in self.all_final_variable_list.to_compute().nodes().names():
                        self.conveyance.position = "node"
                        self.conveyance.hdf5 = False
                        self.all_final_variable_list.append(self.conveyance)
                        if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names() and self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                            self.h.position = "node"
                            self.h.hdf5 = True
                            self.all_final_variable_list.append(self.h)
                            self.v.position = "node"
                            self.v.hdf5 = True
                            self.all_final_variable_list.append(self.v)
            # max_slope_bottom mesh ==> need : z
            elif variable_wish.name == self.max_slope_bottom.name:
                if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.z.position = "node"
                    self.z.hdf5 = True
                    self.all_final_variable_list.append(self.z)
            # max_slope_energy mesh ==> need first : h and v node hdf5 (FinitVolume)
            elif variable_wish.name == self.max_slope_energy.name:
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = "node"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = "node"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
                if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.z.position = "node"
                    self.z.hdf5 = True
                    self.all_final_variable_list.append(self.z)

            # all cases
            self.all_final_variable_list.append(variable_wish)

        # print final names
        print("-------- variables final ---------")
        print("loaded nodes : ", self.all_final_variable_list.hdf5s().nodes().names())
        print("loaded meshs : ", self.all_final_variable_list.hdf5s().meshs().names())
        print("computed nodes : ", self.all_final_variable_list.to_compute().nodes().names())
        print("computed meshs : ", self.all_final_variable_list.to_compute().meshs().names())

