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
from inspect import currentframe, getframeinfo


class HydraulicVariable:
    """
    Represent one Hydraulic, substrate and habitat variable or value.
    """

    def __init__(self, name="", name_gui="", descr="", dtype=None, unit="", position="", value=None, hdf5=False,
                 sub=False, habitat=False, index_gui=-1, depend_on_h=True):
        self.name = name  # to manage them
        self.name_gui = name_gui  # to gui
        self.descr = descr  # description string
        self.unit = unit  # string unit
        self.dtype = dtype  # float64 or int64
        self.position = position  # node, mesh, (possible face ?)
        self.value = value  # for ro, g, .. (constant but possible varying ?)
        self.hdf5 = hdf5  # hdf5 or computable
        self.sub = sub  # False: hydraulic (default) True: substrate
        self.index_gui = index_gui  # position index in gui
        self.data = [[]]
        self.min = 0.0  # min for all reach and unit
        self.max = 0.0  # max for all reach and unit
        self.software_attributes_list = []  # software string names list to link with them
        self.precomputable_tohdf5 = False  # computable at reading original file to save hdf5
        self.depend_on_h = depend_on_h  # if h set to 0, value also set to 0
        # hab data
        self.habitat = habitat  # False: hydraulic and substrate (default) True: Habitat
        self.wua = [[]]
        self.hv = [[]]
        self.percent_area_unknown = [[]]
        self.pref_file = ""
        self.stage = ""
        self.aquatic_animal_type = ""

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class HydraulicVariableUnitList(list):
    """
    Represent one Hydraulic, substrate and habitat variable or value.
    """

    def __init__(self):
        super().__init__()

    def append(self, hydraulic_variable):
        """
        with copy
        """
        if hydraulic_variable:
            hydraulic_variable2 = deepcopy(hydraulic_variable)
            # set manually attr
            hydraulic_variable2.wua = hydraulic_variable.wua
            hydraulic_variable2.hv = hydraulic_variable.hv
            hydraulic_variable2.percent_area_unknown = hydraulic_variable.percent_area_unknown
            hydraulic_variable2.percent_area_unknown = hydraulic_variable.percent_area_unknown
            hydraulic_variable2.pref_file = hydraulic_variable.pref_file
            hydraulic_variable2.stage = hydraulic_variable.stage
            hydraulic_variable2.name = hydraulic_variable.name
            hydraulic_variable2.aquatic_animal_type = hydraulic_variable.aquatic_animal_type
            hydraulic_variable2.min = hydraulic_variable.min
            hydraulic_variable2.max = hydraulic_variable.max
            super(HydraulicVariableUnitList, self).append(hydraulic_variable2)
            # self.sort_by_names_gui()

    def extend(self, hydraulic_variable_list):
        """
        without copy
        """
        super(HydraulicVariableUnitList, self).extend(hydraulic_variable_list)
        self.sort_by_names_gui()

    def append_new_habitat_variable(self, code_bio_model, stage, hyd_opt, sub_opt, aquatic_animal_type, model_type,
                                    pref_file):
        # animal name
        name = code_bio_model + "_" + stage + "_" + hyd_opt + "_" + sub_opt
        # create variable
        hab_variable = HydraulicVariable(value=None,
                                         unit="HSI",
                                         name=name,
                                         name_gui=name,
                                         position="mesh",
                                         dtype=np.float64,
                                         index_gui=1,
                                         habitat=True)
        # extra attributes
        hab_variable.precomputable_tohdf5 = True
        hab_variable.pref_file = pref_file
        hab_variable.aquatic_animal_type = aquatic_animal_type
        hab_variable.model_type = model_type
        hab_variable.code_alternative = code_bio_model
        hab_variable.stage = stage
        hab_variable.hyd_opt = hyd_opt
        hab_variable.sub_opt = sub_opt
        # append
        super(HydraulicVariableUnitList, self).append(hab_variable)

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

    def pref_files(self):
        pref_files_list = []
        for hvu in self:
            if hvu.habitat:
                pref_files_list.append(hvu.pref_file)
        return pref_files_list

    def stages(self):
        stages_list = []
        for hvu in self:
            if hvu.habitat:
                stages_list.append(hvu.stage)
        return stages_list

    def aquatic_animal_types(self):
        aquatic_animal_types_list = []
        for hvu in self:
            if hvu.habitat:
                aquatic_animal_types_list.append(hvu.aquatic_animal_type)
        return aquatic_animal_types_list

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

    def subs(self):
        sub_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.sub:
                sub_list.append(hvu)
        return sub_list

    def no_subs(self):
        no_sub_list = HydraulicVariableUnitList()
        for hvu in self:
            if not hvu.sub:
                no_sub_list.append(hvu)
        return no_sub_list

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

    def depend_on_hs(self):
        """ variable that depends on h """
        depend_on_h_list = HydraulicVariableUnitList()
        for hvu in self:
            if hvu.depend_on_h:
                depend_on_h_list.append(hvu)
        return depend_on_h_list

    def no_depend_on_hs(self):
        """ variable that does not depend on h """
        no_depend_on_h_list = HydraulicVariableUnitList()
        for hvu in self:
            if not hvu.depend_on_h:
                no_depend_on_h_list.append(hvu)
        return no_depend_on_h_list

    def min(self):
        min = []
        for hvu in self:
            min.append(hvu.min)
        return min

    def max(self):
        max = []
        for hvu in self:
            max.append(hvu.max)
        return max

    """ select """

    def get_from_name(self, name):
        return self[self.names().index(name)]

    def get_from_name_gui(self, name_gui):
        return self[self.names_gui().index(name_gui)]

    def replace_variable(self, hvu):
        self[self.names().index(hvu.name)] = hvu


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
                                   dtype=np.float64,
                                   depend_on_h=False)
        # struct
        self.i_whole_profile = HydraulicVariable(value=None,
                                                 unit="",
                                                 name="i_whole_profile",
                                                 name_gui="i whole profile",
                                                 descr="mesh whole profile index",
                                                 dtype=np.int64,
                                                 index_gui=getframeinfo(currentframe()).lineno,
                                                 depend_on_h=False)
        self.i_split = HydraulicVariable(value=None,
                                         unit="",
                                         name="i_split",
                                         name_gui="i split",
                                         descr="mesh cutting index",
                                         dtype=np.int64,
                                         index_gui=getframeinfo(currentframe()).lineno,
                                         depend_on_h=False)
        # coordinate variables
        self.tin = HydraulicVariable(value=None,
                                     unit="",
                                     name="tin",
                                     name_gui="tin",
                                     descr="Triangular Interpolation Network",
                                     dtype=np.int64,
                                     depend_on_h=False)
        self.xy = HydraulicVariable(value=None,
                                    unit="m",
                                    name="xy",
                                    name_gui="xy",
                                    descr="xy coordinates",
                                    dtype=np.float64,
                                    depend_on_h=False)
        self.z = HydraulicVariable(value=None,
                                   unit="m",
                                   name="z",
                                   name_gui="elevation",
                                   descr="bottom elevation",
                                   dtype=np.float64,
                                   index_gui=getframeinfo(currentframe()).lineno,
                                   depend_on_h=False)
        # hyd variable minimum
        self.h = HydraulicVariable(value=None,
                                   unit="m",
                                   name="h",
                                   name_gui="water depth",
                                   dtype=np.float64,
                                   index_gui=getframeinfo(currentframe()).lineno)
        self.v = HydraulicVariable(value=None,
                                   unit="m/s",
                                   name="v",
                                   name_gui="water velocity",
                                   dtype=np.float64,
                                   index_gui=getframeinfo(currentframe()).lineno)
        # hyd variable other
        self.v_x = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_x",
                                     name_gui="water velocity x",
                                     dtype=np.float64,
                                     index_gui=getframeinfo(currentframe()).lineno)
        self.v_y = HydraulicVariable(value=None,
                                     unit="m/s",
                                     name="v_y",
                                     name_gui="water velocity y",
                                     dtype=np.float64,
                                     index_gui=getframeinfo(currentframe()).lineno)
        self.v_frict = HydraulicVariable(value=None,
                                         unit="m/s",
                                         name="v_frict",
                                         name_gui="water velocity friction",
                                         dtype=np.float64,
                                         index_gui=getframeinfo(currentframe()).lineno)
        self.area = HydraulicVariable(value=None,
                                      unit="m²",
                                      name="area",
                                      name_gui="area",
                                      dtype=np.float64,
                                      position="mesh",
                                      index_gui=getframeinfo(currentframe()).lineno,
                                      depend_on_h=False)
        self.shear_stress = HydraulicVariable(value=None,
                                              unit="N/m²",
                                              name="shear_stress",
                                              name_gui="shear stress",
                                              dtype=np.float64,
                                              index_gui=getframeinfo(currentframe()).lineno)
        self.shear_stress_beta = HydraulicVariable(value=None,
                                                   unit="N/m²",
                                                   name="shear_stress_beta",
                                                   name_gui="shear stress beta",
                                                   dtype=np.float64,
                                                   index_gui=getframeinfo(currentframe()).lineno)
        self.level = HydraulicVariable(value=None,
                                       unit="m",
                                       name="level",
                                       name_gui="water level",
                                       dtype=np.float64,
                                       index_gui=getframeinfo(currentframe()).lineno)
        self.froude = HydraulicVariable(value=None,
                                        unit="",
                                        name="froude",
                                        name_gui="froude number",
                                        dtype=np.float64,
                                        index_gui=getframeinfo(currentframe()).lineno)
        self.hydraulic_head = HydraulicVariable(value=None,
                                                unit="m",
                                                name="hydraulic_head",
                                                name_gui="hydraulic head",
                                                dtype=np.float64,
                                                index_gui=getframeinfo(currentframe()).lineno)
        self.hydraulic_head_level = HydraulicVariable(value=None,
                                                unit="m",
                                                name="hydraulic_head_level",
                                                name_gui="hydraulic_head_level",
                                                dtype=np.float64,
                                                index_gui=getframeinfo(currentframe()).lineno)
        self.conveyance = HydraulicVariable(value=None,
                                            unit="m²/s",
                                            name="conveyance",
                                            name_gui="conveyance",
                                            dtype=np.float64,
                                            index_gui=getframeinfo(currentframe()).lineno)
        self.max_slope_bottom = HydraulicVariable(value=None,
                                                  unit="m/m",
                                                  name="max_slope_bottom",
                                                  name_gui="max slope bottom",
                                                  dtype=np.float64,
                                                  index_gui=getframeinfo(currentframe()).lineno,
                                                  depend_on_h=False)
        self.max_slope_energy = HydraulicVariable(value=None,
                                                  unit="m/m",
                                                  name="max_slope_energy",
                                                  name_gui="max slope energy",
                                                  dtype=np.float64,
                                                  index_gui=getframeinfo(currentframe()).lineno)
        self.temp = HydraulicVariable(value=None,
                                      unit="",
                                      name="temp",
                                      name_gui="temperature",
                                      dtype=np.float64,
                                      index_gui=getframeinfo(currentframe()).lineno,
                                      depend_on_h=False)
        # sub variable
        self.i_sub_defaut = HydraulicVariable(value=None,
                                              unit="",
                                              name="i_sub_defaut",
                                              name_gui="sub defaut value index",
                                              descr="mesh default substrate index",
                                              index_gui=getframeinfo(currentframe()).lineno,
                                              dtype=np.int64,
                                              depend_on_h=False)
        self.sub_coarser = HydraulicVariable(value=None,
                                             unit="",
                                             name="sub_coarser",
                                             name_gui="sub coarser",
                                             dtype=np.int64,
                                             index_gui=getframeinfo(currentframe()).lineno,
                                             sub=True,
                                             depend_on_h=False)
        self.sub_dom = HydraulicVariable(value=None,
                                         unit="",
                                         name="sub_dom",
                                         name_gui="sub dominant",
                                         dtype=np.int64,
                                         index_gui=getframeinfo(currentframe()).lineno,
                                         sub=True,
                                         depend_on_h=False)
        self.sub_s1 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s1",
                                        name_gui="sub S1",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s2 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s2",
                                        name_gui="sub S2",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s3 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s3",
                                        name_gui="sub S3",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s4 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s4",
                                        name_gui="sub S4",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s5 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s5",
                                        name_gui="sub S5",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s6 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s6",
                                        name_gui="sub S6",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s7 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s7",
                                        name_gui="sub S7",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s8 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s8",
                                        name_gui="sub S8",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s9 = HydraulicVariable(value=None,
                                        unit="",
                                        name="sub_s9",
                                        name_gui="sub S9",
                                        dtype=np.int64,
                                        index_gui=getframeinfo(currentframe()).lineno,
                                        sub=True,
                                        depend_on_h=False)
        self.sub_s10 = HydraulicVariable(value=None,
                                         unit="",
                                         name="sub_s10",
                                         name_gui="sub S10",
                                         dtype=np.int64,
                                         index_gui=getframeinfo(currentframe()).lineno,
                                         sub=True,
                                         depend_on_h=False)
        self.sub_s11 = HydraulicVariable(value=None,
                                         unit="",
                                         name="sub_s11",
                                         name_gui="sub S11",
                                         dtype=np.int64,
                                         index_gui=getframeinfo(currentframe()).lineno,
                                         sub=True,
                                         depend_on_h=False)
        self.sub_s12 = HydraulicVariable(value=None,
                                         unit="",
                                         name="sub_s12",
                                         name_gui="sub S12",
                                         dtype=np.int64,
                                         index_gui=getframeinfo(currentframe()).lineno,
                                         sub=True,
                                         depend_on_h=False)

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
                        usefull_variable_wish.hdf5 = True
                        self.software_detected_list.append(usefull_variable_wish)
        self.software_detected_list.sort_by_names_gui()  # sort

        # copy
        self.hdf5_and_computable_list.extend(self.software_detected_list)

        """ required variable nodes """
        node_names = self.hdf5_and_computable_list.nodes().names()

        # always z, if not detect : compute (FV to FE)
        if self.z.name not in node_names:
            self.z.position = "node"
            self.z.hdf5 = True
            self.hdf5_and_computable_list.append(self.z)
        if self.h.name not in node_names:
            self.h.position = "node"
            self.h.precomputable_tohdf5 = True
            self.h.hdf5 = True
            self.hdf5_and_computable_list.append(self.h)
        # always v but computed_node_velocity or original ?
        if self.v.name not in node_names:
            self.v.position = "node"
            self.v.hdf5 = True
            if self.v_x.name in node_names and self.v_y.name in node_names:
                self.v.precomputable_tohdf5 = True
            else:
                self.v.precomputable_tohdf5 = False
            self.hdf5_and_computable_list.append(self.v)

    def detect_variable_from_sub_description(self, sub_description):
        # self.hdf5_and_computable_list = HydraulicVariableUnitList()
        sub_class_number = 2
        if sub_description["sub_classification_method"] == 'coarser-dominant':
            # coarser
            self.sub_coarser.position = "mesh"
            self.sub_coarser.hdf5 = True
            self.sub_coarser.unit = sub_description["sub_classification_code"]
            self.sub_coarser.sub = True
            self.hdf5_and_computable_list.append(self.sub_coarser)
            # dominant
            self.sub_dom.position = "mesh"
            self.sub_dom.hdf5 = True
            self.sub_dom.unit = sub_description["sub_classification_code"]
            self.sub_dom.sub = True
            self.hdf5_and_computable_list.append(self.sub_dom)
        elif sub_description["sub_classification_method"] == 'percentage':
            if sub_description["sub_classification_code"] == "Cemagref":
                sub_class_number = 8
            elif sub_description["sub_classification_code"] == "Sandre":
                sub_class_number = 12
            for i in range(1, sub_class_number + 1):
                sub_sx = getattr(self, "sub_s" + str(i))
                sub_sx.position = "mesh"
                sub_sx.hdf5 = True
                sub_sx.unit = sub_description["sub_classification_code"]
                sub_sx.sub = True
                self.hdf5_and_computable_list.append(sub_sx)
            # computable coarser
            self.sub_coarser.position = "mesh"
            self.sub_coarser.hdf5 = False
            self.sub_coarser.unit = sub_description["sub_classification_code"]
            self.sub_coarser.sub = True
            self.hdf5_and_computable_list.append(self.sub_coarser)
            # computable dominant
            self.sub_dom.position = "mesh"
            self.sub_dom.hdf5 = False
            self.sub_dom.unit = sub_description["sub_classification_code"]
            self.sub_dom.sub = True
            self.hdf5_and_computable_list.append(self.sub_dom)

    def detect_variable_habitat(self, varnames):
        varnames.sort(key=str.lower)  # sort alphanumeric
        # detect_variable_from_software_attribute
        for varname_index, varname in enumerate(varnames):
            variable = HydraulicVariable(value=None,
                                         unit="HSI",
                                         name=varname,
                                         name_gui=varname,
                                         hdf5=True,
                                         position="mesh",
                                         dtype=np.float64,
                                         index_gui=1,
                                         habitat=True)
            self.hdf5_and_computable_list.append(variable)

    def get_original_computable_mesh_and_node_from_hyd(self, mesh_variable_original_name_list,
                                                       mesh_variable_original_min_list,
                                                       mesh_variable_original_max_list,
                                                       node_variable_original_name_list,
                                                       node_variable_original_min_list,
                                                       node_variable_original_max_list):
        """
        no hab.
        """
        # hdf5 mesh
        for mesh_variable_index, mesh_variable_original_name in enumerate(mesh_variable_original_name_list):
            variable_mesh = getattr(self, mesh_variable_original_name)
            variable_mesh.position = "mesh"
            variable_mesh.hdf5 = True
            variable_mesh.min = float(mesh_variable_original_min_list[mesh_variable_index])
            variable_mesh.max = float(mesh_variable_original_max_list[mesh_variable_index])
            if not variable_mesh.sub:
                self.hdf5_and_computable_list.append(variable_mesh)

        # hdf5 node
        for node_variable_index, node_variable_original_name in enumerate(node_variable_original_name_list):
            variable_node = getattr(self, node_variable_original_name)
            variable_node.position = "node"
            variable_node.hdf5 = True
            variable_node.min = float(node_variable_original_min_list[node_variable_index])
            variable_node.max = float(node_variable_original_max_list[node_variable_index])
            if not variable_node.sub:
                self.hdf5_and_computable_list.append(variable_node)

        # computable node
        computable_node_list = [self.level, self.froude, self.hydraulic_head, self.hydraulic_head_level, self.conveyance]
        if self.v_frict.name in self.hdf5_and_computable_list.names():
            self.shear_stress.position = "node"
            self.shear_stress.hdf5 = False
            computable_node_list.append(self.shear_stress)
        for computed_node in computable_node_list:
            if computed_node.name not in node_variable_original_name_list:
                computed_node.position = "node"
                computed_node.hdf5 = False
                self.hdf5_and_computable_list.append(computed_node)

        # computable mesh
        computable_mesh_list = [self.max_slope_bottom, self.max_slope_energy]
        computable_mesh_list = deepcopy(self.hdf5_and_computable_list.nodes()) + computable_mesh_list

        # shear_stress_beta
        computable_mesh_list.append(self.shear_stress_beta)
        for computed_mesh in computable_mesh_list:
            if computed_mesh.name not in mesh_variable_original_name_list:
                computed_mesh.position = "mesh"
                computed_mesh.hdf5 = False
                self.hdf5_and_computable_list.append(computed_mesh)

        # sort_by_names_gui
        self.hdf5_and_computable_list.sort_by_names_gui()

    def set_variable_data_structure(self, reach_number, unit_number):
        # variables
        for variable in self.hdf5_and_computable_list:
            variable.data = []
            for reach_ind in range(reach_number):
                variable.data.append([])
                for _ in range(unit_number):
                    variable.data[reach_ind].append([])
        # struct
        self.xy.data = []
        self.tin.data = []
        for reach_ind in range(reach_number):
            self.xy.data.append([])
            self.tin.data.append([])
            for _ in range(unit_number):
                self.xy.data[reach_ind].append([])
                self.tin.data[reach_ind].append([])

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
        if project_preferences["mesh_detailled_text"][index]:
            mesh = True
        if project_preferences["point_detailled_text"][index]:
            node = True
        if project_preferences["variables_units"][index]:
            mesh = True
            node = True
            # pvd_variable_z ?

        if node and mesh:  # all data
            user_target_list = deepcopy(self.hdf5_and_computable_list)
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
        self.all_final_variable_list = HydraulicVariableUnitList()

        # wish hdf5 (node and mesh)
        for variable_wish in user_target_list.hdf5s():
            self.all_final_variable_list.append(variable_wish)

        """ hab """
        # for each wish mesh variables, witch hdf5 variable to be computed ?
        if user_target_list.habs().to_compute():
            # h and v mesh available
            if self.h.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                # mesh
                if self.h.name not in self.all_final_variable_list.hdf5s().meshs().names():
                    self.h.position = "mesh"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().meshs().names():
                    self.v.position = "mesh"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # h and v node available
            elif self.h.name not in self.hdf5_and_computable_list.hdf5s().meshs().names():
                # mesh
                if self.h.name not in self.all_final_variable_list.hdf5s().meshs().names():
                    self.h.position = "mesh"
                    self.h.hdf5 = False
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().meshs().names():
                    self.v.position = "mesh"
                    self.v.hdf5 = False
                    self.all_final_variable_list.append(self.v)
                # node
                if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.h.position = "node"
                    self.h.hdf5 = True
                    self.all_final_variable_list.append(self.h)
                if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                    self.v.position = "node"
                    self.v.hdf5 = True
                    self.all_final_variable_list.append(self.v)
            # sub mesh available
            for sub_name in self.hdf5_and_computable_list.subs().meshs().hdf5s().names():
                if sub_name not in self.all_final_variable_list.subs().meshs().names():
                    sub_variable = getattr(self, sub_name)
                    sub_variable.position = "mesh"
                    sub_variable.hdf5 = True
                    self.all_final_variable_list.append(sub_variable)
            # area mesh available
            if self.area.name not in self.all_final_variable_list.meshs().names():
                self.area.position = "mesh"
                self.area.hdf5 = True
                self.all_final_variable_list.append(self.area)
            # shear_stress
            for variable_wish in user_target_list.habs():
                if variable_wish.aquatic_animal_type == "invertebrate":
                    if self.shear_stress.name not in self.all_final_variable_list.hdf5s().meshs().names():
                        if self.shear_stress.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                            self.shear_stress.position = "mesh"
                            self.shear_stress.hdf5 = True
                        else:
                            if self.v_frict.name in self.hdf5_and_computable_list.hdf5s().nodes().names():
                                if self.v_frict.name not in self.all_final_variable_list.hdf5s().nodes().names():
                                    self.v_frict.position = "node"
                                    self.v_frict.hdf5 = True
                                    self.all_final_variable_list.append(self.v_frict)
                                if self.shear_stress.name not in self.all_final_variable_list.to_compute().nodes().names():
                                    self.shear_stress.position = "node"
                                    self.shear_stress.hdf5 = False
                                    self.all_final_variable_list.append(self.shear_stress)
                                if self.shear_stress.name not in self.all_final_variable_list.hdf5s().meshs().names():
                                    self.shear_stress.position = "mesh"
                                    self.shear_stress.hdf5 = False
                                    self.all_final_variable_list.append(self.shear_stress)
                        break

        else:
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
                # hydraulic head level node ==> need h and v node
                elif variable_wish.name == self.hydraulic_head_level.name:
                    if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        self.h.position = variable_wish.position
                        self.h.hdf5 = True
                        self.all_final_variable_list.append(self.h)
                    if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        self.v.position = variable_wish.position
                        self.v.hdf5 = True
                        self.all_final_variable_list.append(self.v)
                    if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        self.z.position = variable_wish.position
                        self.z.hdf5 = True
                        self.all_final_variable_list.append(self.z)
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
                elif variable_wish.name == self.v.name:
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
                # subtrate
                elif variable_wish.name == self.sub_coarser.name or variable_wish.name == self.sub_dom.name:
                    # is percentage data or coarser/dom data ?
                    if not variable_wish.hdf5:
                        # # load all sub percentage to compute coarser/dom
                        # class_nb
                        if self.sub_s12.name in self.hdf5_and_computable_list.names():  # Sandre
                            class_nb = 12
                        else:  # Cemagref
                            class_nb = 8
                        for class_num in range(1, class_nb + 1):
                            class_variable = getattr(self, "sub_s" + str(class_num))
                            class_variable.position = "mesh"
                            class_variable.hdf5 = True
                            if class_variable.name not in self.all_final_variable_list.hdf5s().meshs().names():
                                self.all_final_variable_list.append(class_variable)
                    else:
                        # load hdf5 coarser/dom data
                        pass

                # variables never in hdf

                # shear_stress_beta mesh ==> need first : h mesh hdf5 (FinitVolume)
                elif variable_wish.name == self.shear_stress_beta.name:
                    if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
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
                            if self.z.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
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
                # hydraulic_head_level mesh ==> need first : h and v mesh hdf5 (FinitVolume)
                elif variable_wish.name == self.hydraulic_head_level.name:
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

                        if self.z.name not in self.all_final_variable_list.hdf5s().meshs().names():
                            if self.z.name in self.hdf5_and_computable_list.hdf5s().meshs().names():
                                self.z.position = "mesh"
                                self.z.hdf5 = True
                                self.all_final_variable_list.append(self.z)
                    else:
                        if self.z.name not in self.all_final_variable_list.hdf5s().nodes().names():
                            self.z.position = "node"
                            self.z.hdf5 = True
                            self.all_final_variable_list.append(self.z)
                        # compute at node
                        if self.hydraulic_head_level.name not in self.all_final_variable_list.to_compute().nodes().names():
                            self.hydraulic_head_level.position = "node"
                            self.hydraulic_head_level.hdf5 = False
                            self.all_final_variable_list.append(self.hydraulic_head_level)
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
                            if self.h.name not in self.all_final_variable_list.hdf5s().nodes().names():
                                self.h.position = "node"
                                self.h.hdf5 = True
                                self.all_final_variable_list.append(self.h)
                            if self.v.name not in self.all_final_variable_list.hdf5s().nodes().names():
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
                # compute mean from node
                else:
                    if variable_wish.name not in self.all_final_variable_list.hdf5s().nodes().names():
                        class_variable = getattr(self, variable_wish.name)
                        class_variable.position = "node"
                        class_variable.hdf5 = True
                        self.all_final_variable_list.append(class_variable)

                # all cases
                self.all_final_variable_list.append(variable_wish)

        # print("######################################")
        # print("target nodes : ", user_target_list.nodes())
        # print("target meshs : ", user_target_list.meshs())
        # print("------>")
        # print("loaded nodes : ", self.all_final_variable_list.hdf5s().nodes())
        # print("loaded meshs : ", self.all_final_variable_list.hdf5s().meshs())
        # print("computed nodes : ", self.all_final_variable_list.to_compute().nodes())
        # print("computed meshs : ", self.all_final_variable_list.to_compute().meshs())
