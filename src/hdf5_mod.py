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
import time
import shutil
import shapefile
from stl import mesh
import matplotlib.pyplot as plt
import matplotlib as mpl
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from multiprocessing import Value

from src import bio_info_mod
from src import substrate_mod
from src import plot_mod
from src import hl_mod
from src import paraview_mod
from src.tools_mod import get_prj_from_epsg_web
from src_GUI import preferences_GUI

VERSION = 0.25


class Hdf5Management:
    def __init__(self, path_prj, hdf5_filename):
        # hdf5 version attributes
        self.h5py_version = h5py.version.version
        self.hdf5_version = h5py.version.hdf5_version
        # project attributes
        self.path_prj = path_prj  # relative path to project
        self.path_shp = os.path.join(self.path_prj, r"output\shapefiles")
        self.path_visualisation = os.path.join(self.path_prj, r"output\visualisation")
        self.name_prj = os.path.basename(path_prj)  # name of project
        self.absolute_path_prj_xml = os.path.join(self.path_prj, self.name_prj + '.xml')
        # hdf5 attributes fix
        self.extensions = ('.hyd', '.sub', '.hab')  # all available extensions
        # hdf5 file attributes
        self.path = os.path.join(path_prj, "hdf5")  # relative path
        self.filename = hdf5_filename  # filename with extension
        self.absolute_path_file = os.path.join(self.path, self.filename)  # absolute path of filename with extension
        self.basename = hdf5_filename[:-4]  # filename without extension
        self.extension = hdf5_filename[-4:]  # extension of filename
        self.file_object = None  # file object
        if self.extension == ".hyd":
            self.type_for_xml = "hdf5_hydrodata"  # for save xml
            self.hdf5_type = "hydraulic"
        if self.extension == ".sub":
            self.type_for_xml = "hdf5_substrate"  # for save xml
            self.hdf5_type = "substrate"
        if self.extension == ".hab":
            self.type_for_xml = "hdf5_habitat"  # for save xml
            self.hdf5_type = "habitat"

    def open_hdf5_file(self, new):
        # get mode
        if not new:
            mode_file = 'r+'  # Readonly, file must exist
        if new:
            mode_file = 'w'  # Read/write, file must exist

        # extension check
        if self.extension not in self.extensions:
            print(f"Warning: the extension file should be : {self.extensions}.")

        # file presence check
        try:
            # write or open hdf5 file
            self.file_object = h5py.File(name=self.absolute_path_file,
                                         mode=mode_file)
            if new:  # write + write attributes
                self.file_object.attrs['hdf5_version'] = self.hdf5_version
                self.file_object.attrs['h5py_version'] = self.h5py_version
                self.file_object.attrs['software'] = 'HABBY'
                self.file_object.attrs['software_version'] = str(VERSION)
                self.file_object.attrs['path_projet'] = self.path_prj
                self.file_object.attrs['name_projet'] = self.name_prj
                self.file_object.attrs[self.extension[1:] + '_filename'] = self.filename

        except OSError:
            print('Error: the hdf5 file could not be loaded.')
            self.file_object = None

    def save_xml(self, model_type):
        if not os.path.isfile(self.absolute_path_prj_xml):
            print('Error: No project saved. Please create a project first in the General tab.')
            return
        else:
            doc = ET.parse(self.absolute_path_prj_xml)
            root = doc.getroot()
            child = root.find(".//" + model_type)
            # if the xml attribute do not exist yet, xml name should be saved
            if child is None:
                here_element = ET.SubElement(root, model_type)
                hdf5file = ET.SubElement(here_element, self.type_for_xml)
                hdf5file.text = self.filename
            else:
                child2s = root.findall(".//" + model_type + "/" + self.type_for_xml)
                if child2s is not None:
                    found_att_text = False
                    for i, c in enumerate(child2s):
                        if c.text == self.filename:     # if same : remove/recreate at the end
                                                        # (for the last file create labels)
                            found_att_text = True
                            index_origin = i
                    if found_att_text:
                        # existing element
                        element = child2s[index_origin]
                        # remove existing
                        child.remove(element)
                        # add existing to the end
                        hdf5file = ET.SubElement(child, self.type_for_xml)
                        hdf5file.text = self.filename
                    if not found_att_text:
                        hdf5file = ET.SubElement(child, self.type_for_xml)
                        hdf5file.text = self.filename
                else:
                    hdf5file = ET.SubElement(child, self.type_for_xml)
                    hdf5file.text = self.filename
            # write xml
            doc.write(self.absolute_path_prj_xml)

    # GET HDF5 INFORMATIONS
    def get_hdf5_attributes(self):
        # open an hdf5
        self.open_hdf5_file(new=False)
        # get attributes
        hdf5_attributes_dict = dict(self.file_object.attrs.items())
        hdf5_attributes_dict_keys = sorted(hdf5_attributes_dict.keys())
        attributes_to_the_end = ['name_projet', 'path_projet', 'software', 'software_version', 'h5py_version', 'hdf5_version']
        hdf5_attributes_name_text = []
        hdf5_attributes_info_text = []
        # format attributes
        for attribute_name in hdf5_attributes_dict_keys:
            if attribute_name in attributes_to_the_end:
                pass
            else:
                hdf5_attributes_name_text.append(attribute_name.replace("_", " "))
                hdf5_attributes_info_text.append(hdf5_attributes_dict[attribute_name])

        # set general attributes to the end
        for attribute_name in attributes_to_the_end:
            hdf5_attributes_name_text.extend([attribute_name.replace("_", " ")])
            hdf5_attributes_info_text.extend([hdf5_attributes_dict[attribute_name]])

        # close hdf5 file
        self.file_object.close()

        # to attributes
        self.hdf5_attributes_name_text = hdf5_attributes_name_text
        self.hdf5_attributes_info_text = hdf5_attributes_info_text

    def get_hdf5_variables(self):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # substrate constant ==> nothing to plot
        if self.hdf5_type == "substrate" and self.file_object.attrs["sub_mapping_method"] == "constant":
            # close hdf5 file
            self.file_object.close()
            # to attribute
            self.variables = []

        # hydraulic substrate and habitat variables
        else:
            data_group = list(self.file_object.keys())[0]
            """ MESH GROUP """
            # mesh_group for first reach and first unit
            mesh_group = data_group + "/reach_0/unit_0/mesh"
            variables_mesh = list(self.file_object[mesh_group].keys())
            # remove i_whole_profile
            if "i_whole_profile" in variables_mesh:
                variables_mesh.remove("i_whole_profile")
            # change tin by mesh
            if "tin" in variables_mesh:
                variables_mesh[variables_mesh.index("tin")] = "mesh"
            # change sub by coarser_dominant
            if "sub" in variables_mesh:
                variables_mesh[variables_mesh.index("sub")] = "coarser_dominant"
            """ NODE GROUP """
            # node_group for first reach and first unit
            node_group = data_group + "/reach_0/unit_0/node"
            variables_node = list(self.file_object[node_group].keys())
            # change name for h and v for GUI
            if "h" in variables_node:
                variables_node[variables_node.index("h")] = "height"
            if "v" in variables_node:
                variables_node[variables_node.index("v")] = "velocity"
            # remove xy (not variable)
            if "xy" in variables_node:
                variables_node.remove("xy")
            # merge two variables list
            if variables_mesh and variables_node:
                variables = variables_mesh + variables_node
            if not variables_mesh and variables_node:
                variables = variables_node
            if variables_mesh and not variables_node:
                variables = variables_mesh

            # change names (estithic)
            if "z" in variables:
                variables.remove("z")
                variables.insert(1, "points elevation")
            if "mesh" in variables:
                variables.insert(1, "mesh and points")

            # estithic sort for GUI (classic variables + fish variables (alphanumeric))
            variables.sort(key=str.lower)  # sort alphanumeric
            list_to_gui = ["mesh", "mesh and points", "points elevation", "height", "velocity", "coarser_dominant"]
            list_to_gui = [x for x in list_to_gui if x in variables]  # remove variable not present in hdf5

            for variable_index, variable in enumerate(list_to_gui):
                if variable in variables:  # first
                    variables.insert(variable_index, variables.pop(variables.index(variable)))

            # close hdf5 file
            self.file_object.close()

            # to attribute
            self.variables = variables

    def get_hdf5_fish_names(self):
        self.get_hdf5_variables()
        variables_to_remove = ["mesh", "mesh and points", "points elevation", "height", "velocity", "coarser_dominant"]
        fish_list = [x for x in self.variables if x not in variables_to_remove]  # remove variable not present in hdf5
        self.fish_list = fish_list

    def get_hdf5_units_name(self):
        """
        This function looks for the name of the timesteps in hydrological or merge hdf5. If it find the name
        of the time steps, it returns them. If not, it return an empty list.
        :return: the name of the time step if they exist. Otherwise, an empty list
        """
        # open hdf5 file
        self.open_hdf5_file(new=False)
        # units name
        units_name = []
        # get unit_list
        hdf5_attributes = list(self.file_object.attrs.items())
        for attribute_name, attribute_data in hdf5_attributes:
            if "unit_list" in attribute_name:
                units_name = attribute_data.split(", ")
        # close hdf5 file
        self.file_object.close()

        # to attributes
        self.units_name = units_name

    def get_hdf5_units_number(self):  # ? a changer si on utilise attributs
        # open hdf5 file
        self.open_hdf5_file(new=False)
        # get nb_unit
        hdf5_attributes = list(self.file_object.attrs.items())
        for attribute_name, attribute_data in hdf5_attributes:
            if "nb_unit" in attribute_name:
                nb_unit = int(attribute_data)
        # close hdf5 file
        self.file_object.close()

        # to attributes
        self.nb_unit = nb_unit

    # HYDRAULIC
    def create_hdf5_hyd(self, data_2d, data_2d_whole_profile, hyd_description):
        """
        :param data_2d: data 2d dict with keys :
        'tin' : list by reach, sub list by units and sub list of numpy array type int
        (three values by mesh : triangle points indexes)
        'i_whole_profile', : list by reach, sub list by units and sub list of numpy array type int
        (one value by mesh : whole profile mesh indexes)
        'xy' : list by reach, sub list by units and sub list of numpy array type float
        (two values by point : x and y coordinates)
        'h' : list by reach, sub list by units and sub list of numpy array type float
        (one value by point : water height)
        'v' : list by reach, sub list by units and sub list of numpy array type float
        (one value by point : water velocity)
        'z' : list by reach, sub list by units and sub list of numpy array type float
        (one value by point : bottom elevation)
        :param data_2d_whole_profile: data 2d whole profile dict with keys :
        'tin' : list by reach, sub list by units and sub list of numpy array type int
        (three values by mesh : triangle points indexes)
        'xy_center' : list by reach, sub list by units and sub list of numpy array type float
        (two values by point : x and y center coordinates of triangle)
        'xy' : list by reach, sub list by units and sub list of numpy array type float
        (two values by point : x and y coordinates)
        'z' : list by reach, sub list by units and sub list of numpy array type float
        (one value by point : bottom elevation)
        'unit_correspondence' :
        :param hyd_description: description dict with keys :
        'hyd_filename_source' : str of input filename(s) (sep: ', ')
        'hyd_model_type' : str of hydraulic model type
        'hyd_model_dimension' : str of dimension number
        'hyd_variables_list' : str of variable list (sep: ', ')
        'hyd_epsg_code' : str of EPSG number
        'hyd_reach_list' : str of reach name(s) (sep: ', ')
        'hyd_reach_number' : str of reach total number
        'hyd_reach_type' : str of type of reach
        'hyd_unit_list' : str of list of units (sep: ', ')
        'hyd_unit_number' : str of units total number
        'hyd_unit_type' : str of units type (discharge or time) with between brackets, the unit symbol ([m3/s], [s], ..)
        ex : 'discharge [m3/s]', 'time [s]'
        'hyd_unit_wholeprofile' : str ("all") if same tin for all unit
                                list of integer if tin different between units
        'hyd_unit_z_equal' : str of boolean, 'True' if all z are egual between units, 'False' if the bottom values vary
        """
        # create a new hdf5
        self.open_hdf5_file(new=True)

        # create hyd attributes
        for attribute_name, attribute_value in list(hyd_description.items()):
            self.file_object.attrs[attribute_name] = attribute_value

        # data by type of model (2D)
        if int(hyd_description["hyd_model_dimension"]) <= 2:

            # get extent
            xMin = []
            xMax = []
            yMin = []
            yMax = []

            # whole_profile
            data_whole_profile_group = self.file_object.create_group('data_2D_whole_profile')
            # REACH GROUP
            for reach_num in range(int(hyd_description["hyd_reach_number"])):
                reach_group = data_whole_profile_group.create_group('reach_' + str(reach_num))
                # UNIT GROUP
                nb_whole_profil = int(hyd_description["hyd_unit_number"])
                if hyd_description["hyd_unit_wholeprofile"] == "all":  # one whole profile for all units
                    nb_whole_profil = 1
                for unit_num in range(nb_whole_profil):
                    if hyd_description["hyd_unit_wholeprofile"] == "all":  # one whole profile for all units
                        unit_group = reach_group.create_group('unit_all')
                    else:
                        unit_group = reach_group.create_group('unit_' + str(unit_num))

                    # MESH GROUP
                    mesh_group = unit_group.create_group('mesh')
                    mesh_group.create_dataset(name="tin",
                                              shape=[len(data_2d_whole_profile["tin"][reach_num][unit_num]),
                                                     len(data_2d_whole_profile["tin"][reach_num][unit_num][0])],
                                              data=data_2d_whole_profile["tin"][reach_num][unit_num])
                    # NODE GROUP
                    xMin.append(min(data_2d_whole_profile["xy"][reach_num][unit_num][:, 0]))
                    xMax.append(max(data_2d_whole_profile["xy"][reach_num][unit_num][:, 0]))
                    yMin.append(min(data_2d_whole_profile["xy"][reach_num][unit_num][:, 1]))
                    yMax.append(max(data_2d_whole_profile["xy"][reach_num][unit_num][:, 1]))
                    node_group = unit_group.create_group('node')
                    node_group.create_dataset(name="xy",
                                              shape=[len(data_2d_whole_profile["xy"][reach_num][unit_num]),
                                                     len(data_2d_whole_profile["xy"][reach_num][unit_num][0])],
                                              data=data_2d_whole_profile["xy"][reach_num][unit_num])
                    if hyd_description["hyd_unit_z_equal"] == "True":
                        node_group.create_dataset(name="z",
                                                  shape=[len(data_2d_whole_profile["z"][reach_num][unit_num]), 1],
                                                  data=data_2d_whole_profile["z"][reach_num][unit_num])
            # get extent
            xMin = str(min(xMin))
            xMax = str(max(xMax))
            yMin = str(min(yMin))
            yMax = str(max(yMax))
            extent = [xMin, yMin, xMax, yMax]
            self.file_object.attrs["hyd_extent"] = ", ".join(extent)

            # data_2D
            data_group = self.file_object.create_group('data_2D')
            # REACH GROUP
            for reach_num in range(int(hyd_description["hyd_reach_number"])):
                reach_group = data_group.create_group('reach_' + str(reach_num))
                # UNIT GROUP
                for unit_num in range(int(hyd_description["hyd_unit_number"])):
                    unit_group = reach_group.create_group('unit_' + str(unit_num))
                    # MESH GROUP
                    mesh_group = unit_group.create_group('mesh')
                    mesh_group.create_dataset(name="tin",
                                              shape=[len(data_2d["tin"][reach_num][unit_num]), 3],
                                              data=data_2d["tin"][reach_num][unit_num])
                    mesh_group.create_dataset(name="i_whole_profile",
                                              shape=[len(data_2d["i_whole_profile"][reach_num][unit_num]), 1],
                                              data=data_2d["i_whole_profile"][reach_num][unit_num])
                    # NODE GROUP
                    node_group = unit_group.create_group('node')
                    node_group.create_dataset(name="h",
                                              shape=[len(data_2d["h"][reach_num][unit_num]), 1],
                                              data=data_2d["h"][reach_num][unit_num])
                    node_group.create_dataset(name="v",
                                              shape=[len(data_2d["v"][reach_num][unit_num]), 1],
                                              data=data_2d["v"][reach_num][unit_num])
                    node_group.create_dataset(name="xy",
                                              shape=[len(data_2d["xy"][reach_num][unit_num]),
                                                     len(data_2d["xy"][reach_num][unit_num][0])],
                                              data=data_2d["xy"][reach_num][unit_num])
                    node_group.create_dataset(name="z",
                                              shape=[len(data_2d["z"][reach_num][unit_num]), 1],
                                              data=data_2d["z"][reach_num][unit_num])

        # close file
        self.file_object.close()

        # save XML
        self.save_xml(hyd_description["hyd_model_type"])

        # reload to add new data to attributes
        self.load_hdf5_hyd(whole_profil=True)

    def load_hdf5_hyd(self, units_index="all", whole_profil=False):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # attributes
        if units_index == "all":
            # load the number of time steps
            nb_t = int(self.file_object.attrs['hyd_unit_number'])
            units_index = list(range(nb_t))

        # get attributes
        hyd_description = dict()
        for attribute_name, attribute_value in list(self.file_object.attrs.items()):
            hyd_description[attribute_name] = attribute_value

        # WHOLE PROFIL
        if whole_profil:
            data_2D_whole_profile = dict()
            data_2D_whole_profile["tin"] = []
            data_2D_whole_profile["xy"] = []
            if hyd_description["hyd_unit_z_equal"] == "True":
                data_2D_whole_profile["z"] = []
            data_group = 'data_2D_whole_profile'

            # for all reach
            for reach_num in range(0, int(self.file_object.attrs['hyd_reach_number'])):
                reach_group = data_group + "/reach_" + str(reach_num)
                # for all unit
                tin_list = []
                xy_list = []
                if hyd_description["hyd_unit_z_equal"] == "True":
                    z_list = []

                # for all units (selected or all)
                for unit_num in units_index:
                    if hyd_description['hyd_unit_wholeprofile'] == "all":
                        unit_group = reach_group + "/unit_all"
                    else:
                        unit_group = reach_group + "/unit_" + str(unit_num)
                    mesh_group = unit_group + "/mesh"
                    node_group = unit_group + "/node"
                    try:
                        # mesh
                        tin_list.append(self.file_object[mesh_group + "/tin"][:])
                        # node
                        xy_list.append(self.file_object[node_group + "/xy"][:])
                        if hyd_description["hyd_unit_z_equal"] == "True":
                            z_list.append(self.file_object[node_group + "/z"][:])
                    except KeyError:
                        print(
                            'Warning: the dataset for tin or xy (3) is missing from the hdf5 file for one time step. \n')
                        self.file_object.close()
                        return
                data_2D_whole_profile["tin"].append(tin_list)
                data_2D_whole_profile["xy"].append(xy_list)
                if hyd_description["hyd_unit_z_equal"] == "True":
                    data_2D_whole_profile["z"].append(z_list)

        # DATA 2D
        data_2d = dict()
        data_2d["tin"] = []
        data_2d["i_whole_profile"] = []
        data_2d["xy"] = []
        data_2d["h"] = []
        data_2d["v"] = []
        data_2d["z"] = []
        data_group = 'data_2D'
        # for all reach
        for r in range(0, int(self.file_object.attrs['hyd_reach_number'])):
            reach_group = data_group + "/reach_" + str(r)
            # for all unit
            tin_list = []
            i_whole_profile_list = []
            xy_list = []
            h_list = []
            v_list = []
            z_list = []
            for t in units_index:
                unit_group = reach_group + "/unit_" + str(t)
                mesh_group = unit_group + "/mesh"
                node_group = unit_group + "/node"
                try:
                    # mesh
                    tin_list.append(self.file_object[mesh_group + "/tin"][:])
                    i_whole_profile_list.append(self.file_object[mesh_group + "/i_whole_profile"][:])
                    # node
                    h_list.append(self.file_object[node_group + "/h"][:].flatten())
                    v_list.append(self.file_object[node_group + "/v"][:].flatten())
                    xy_list.append(self.file_object[node_group + "/xy"][:])
                    z_list.append(self.file_object[node_group + "/z"][:].flatten())
                except KeyError:
                    print('Warning: the dataset for tin or xy (3) is missing from the hdf5 file for one time step. \n')
                    self.file_object.close()
                    return
            data_2d["tin"].append(tin_list)
            data_2d["i_whole_profile"].append(i_whole_profile_list)
            data_2d["xy"].append(xy_list)
            data_2d["h"].append(h_list)
            data_2d["v"].append(v_list)
            data_2d["z"].append(z_list)

        # close file
        self.file_object.close()

        # to attributes
        if whole_profil:
            self.data_2d = data_2d
            self.data_2d_whole = data_2D_whole_profile
            self.data_description = hyd_description
        if not whole_profil:
            self.data_2d = data_2d
            self.data_description = hyd_description

    # SUBSTRATE
    def create_hdf5_sub(self, sub_description_system, data_2d):
        # create a new hdf5
        self.open_hdf5_file(new=True)

        # create sub attributes
        for attribute_name, attribute_value in list(sub_description_system.items()):
            self.file_object.attrs[attribute_name] = attribute_value

        # POLYGON or POINT
        if sub_description_system["sub_mapping_method"] in ("polygon", "point"):
            # create specific attributes
            self.file_object.attrs['sub_default_values'] = sub_description_system["sub_default_values"]
            self.file_object.attrs['sub_epsg_code'] = sub_description_system["sub_epsg_code"]

            # get extent
            xMin = []
            xMax = []
            yMin = []
            yMax = []

            # data_2D
            data_group = self.file_object.create_group('data_2D')
            # REACH GROUP
            for reach_num in range(data_2d["nb_reach"]):
                reach_group = data_group.create_group('reach_' + str(reach_num))
                # UNIT GROUP
                for unit_num in range(data_2d["nb_unit"]):
                    unit_group = reach_group.create_group('unit_' + str(unit_num))
                    # MESH GROUP
                    mesh_group = unit_group.create_group('mesh')
                    mesh_group.create_dataset(name="sub",
                                              shape=[len(data_2d["sub"][unit_num][0]),
                                                     int(sub_description_system["sub_class_number"])],
                                              data=list(zip(*data_2d["sub"][unit_num])))
                    mesh_group.create_dataset(name="tin",
                                              shape=[len(data_2d["tin"][unit_num]), 3],
                                              data=data_2d["tin"][unit_num])
                    # NODE GROUP
                    xMin.append(min(data_2d["xy"][unit_num][:, 0]))
                    xMax.append(max(data_2d["xy"][unit_num][:, 0]))
                    yMin.append(min(data_2d["xy"][unit_num][:, 1]))
                    yMax.append(max(data_2d["xy"][unit_num][:, 1]))
                    node_group = unit_group.create_group('node')
                    node_group.create_dataset(name="xy",
                                              shape=[len(data_2d["xy"][unit_num]), 2],
                                              data=data_2d["xy"][unit_num])

            # get extent
            xMin = str(min(xMin))
            xMax = str(max(xMax))
            yMin = str(min(yMin))
            yMax = str(max(yMax))
            extent = [xMin, yMin, xMax, yMax]
            self.file_object.attrs["sub_extent"] = ", ".join(extent)

        # CONSTANT
        if sub_description_system["sub_mapping_method"] == "constant":
            # create attributes
            self.file_object.attrs['sub_constant_values'] = sub_description_system["sub_constant_values"]

            # add the constant value of substrate
            self.file_object.create_dataset(name="sub",
                                            shape=[1, int(sub_description_system["sub_class_number"])],
                                            data=data_2d["sub"][0])

        # close file
        self.file_object.close()

        # save XML
        self.save_xml("SUBSTRATE")

    def load_hdf5_sub(self, convert_to_coarser_dom=False):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # get attributes
        sub_description_system = dict()
        for attribute_name, attribute_value in list(self.file_object.attrs.items()):
            sub_description_system[attribute_name] = attribute_value

        # # get sub attributes
        # sub_description_system = dict()
        # sub_description_system["sub_mapping_method"] = self.file_object.attrs['sub_mapping_method']
        # sub_description_system["sub_classification_code"] = self.file_object.attrs['sub_classification_code']
        # sub_description_system["sub_classification_method"] = self.file_object.attrs['sub_classification_method']
        # sub_description_system["sub_filename_source"] = self.file_object.attrs['sub_filename_source']
        # sub_description_system['sub_class_number'] = self.file_object.attrs['sub_class_number']
        # sub_description_system['sub_reach_number'] = self.file_object.attrs['sub_reach_number']
        # sub_description_system['sub_unit_number'] = self.file_object.attrs['sub_unit_number']
        # sub_description_system['sub_unit_list'] = self.file_object.attrs['sub_unit_list']
        # sub_description_system['sub_unit_type'] = self.file_object.attrs['sub_unit_type']
        # if sub_description_system["sub_mapping_method"] == "constant":
        #     sub_description_system["sub_constant_values"] = self.file_object.attrs['sub_constant_values']
        # if sub_description_system["sub_mapping_method"] != "constant":
        #     sub_description_system["sub_epsg_code"] = self.file_object.attrs['sub_epsg_code']
        #     sub_description_system["sub_default_values"] = self.file_object.attrs['sub_default_values']

        # get data
        data_2d = dict()
        if sub_description_system["sub_mapping_method"] == "constant":
            data_2d["sub"] = self.file_object["sub"][:].tolist()[0]
        if sub_description_system["sub_mapping_method"] != "constant":
            data_2d["tin"] = []
            data_2d["xy"] = []
            data_2d["sub"] = []
            data_2d["nb_unit"] = int(self.file_object.attrs['sub_unit_number'])
            data_2d["nb_reach"] = int(self.file_object.attrs['sub_reach_number'])
            data_group = 'data_2D'
            # for all reach
            for r in range(0, data_2d["nb_reach"]):
                reach_group = data_group + "/reach_" + str(r)
                # for all unit
                tin_list = []
                xy_list = []
                sub_array_list = []
                for t in range(0, data_2d["nb_unit"]):
                    unit_group = reach_group + "/unit_" + str(t)
                    mesh_group = unit_group + "/mesh"
                    node_group = unit_group + "/node"
                    try:
                        # mesh
                        tin_list.append(self.file_object[mesh_group + "/tin"][:])
                        # if convert_to_coarser_dom == True (for plot only)
                        if convert_to_coarser_dom and sub_description_system["sub_classification_method"] != "coarser-dominant":
                            sub_array = self.file_object[mesh_group + "/sub"][:]
                            # dominant case = 1 ==> biggest substrate for plot
                            sub_dominant, sub_coarser = substrate_mod.percentage_to_domcoarse(sub_array, dominant_case=1)
                            sub_array_coarser_dom = np.array(list(zip(sub_coarser, sub_dominant)))
                            sub_array_list.append(sub_array_coarser_dom)
                        else:
                            sub_array_list.append(self.file_object[mesh_group + "/sub"][:])
                        # node
                        xy_list.append(self.file_object[node_group + "/xy"][:])
                    except KeyError:
                        print('Warning: the dataset for tin or xy or sub is missing '
                              'from the hdf5 file for one time step. \n')
                        self.file_object.close()
                        return
                data_2d["tin"].append(tin_list)
                data_2d["xy"].append(xy_list)
                data_2d["sub"].append(sub_array_list)

        self.file_object.close()

        # to attributes
        self.data_2d = data_2d
        self.data_description = sub_description_system

    # HABITAT
    def create_hdf5_hab(self, data_2d, data_2d_whole_profile, merge_description):
        # model_type, nb_dim, sim_name, hyd_filename_source, data_2d_whole_profile, data_2d
        attributes_to_remove = ("sub_unit_list", "sub_unit_number", "sub_reach_number", "sub_unit_type", "hdf5_type")

        # create a new hdf5
        self.open_hdf5_file(new=True)

        # create hab attributes
        for attribute_name, attribute_value in list(merge_description.items()):
            if attribute_name not in attributes_to_remove:
                self.file_object.attrs[attribute_name] = attribute_value
        self.file_object.attrs["hab_fish_list"] = ", ".join([])
        self.file_object.attrs["hab_fish_number"] = str(0)
        self.file_object.attrs["hab_fish_pref_list"] = ", ".join([])
        self.file_object.attrs["hab_fish_stage_list"] = ", ".join([])

        # data_2D_whole_profile profile
        data_whole_profile_group = self.file_object.create_group('data_2D_whole_profile')
        # REACH GROUP
        for reach_num in range(int(merge_description["hyd_reach_number"])):
            reach_group = data_whole_profile_group.create_group('reach_' + str(reach_num))
            # UNIT GROUP
            if merge_description["hyd_unit_wholeprofile"] == "all":  # one whole profile for all units
                nb_whole_profil = 1
            if merge_description["hyd_unit_wholeprofile"] != "all":  # one whole profile by units
                nb_whole_profil = int(merge_description["hyd_unit_number"])
            for unit_num in range(nb_whole_profil):
                if merge_description["hyd_unit_wholeprofile"] == "all":  # one whole profile for all units
                    unit_group = reach_group.create_group('unit_all')
                if merge_description["hyd_unit_wholeprofile"] != "all":  # one whole profile by units
                    unit_group = reach_group.create_group('unit_' + str(unit_num))
                # MESH GROUP
                mesh_group = unit_group.create_group('mesh')
                mesh_group.create_dataset(name="tin",
                                          shape=[len(data_2d_whole_profile["tin"][reach_num][unit_num]),
                                                 3],
                                          data=data_2d_whole_profile["tin"][reach_num][unit_num])
                # mesh_group.create_dataset(name="xy_center",
                #                           shape=[len(data_2d_whole_profile["xy_center"][reach_num][unit_num]),
                #                                  2],
                #                           data=data_2d_whole_profile["xy_center"][reach_num][unit_num])
                # NODE GROUP
                node_group = unit_group.create_group('node')
                node_group.create_dataset(name="xy",
                                          shape=[len(data_2d_whole_profile["xy"][reach_num][unit_num]),
                                                 len(data_2d_whole_profile["xy"][reach_num][unit_num][0])],
                                          data=data_2d_whole_profile["xy"][reach_num][unit_num])
                node_group.create_dataset(name="z",
                                          shape=[len(data_2d_whole_profile["z"][reach_num][unit_num]),
                                                 1],
                                          data=data_2d_whole_profile["z"][reach_num][unit_num])

        # data_2D
        data_group = self.file_object.create_group('data_2D')
        # REACH GROUP
        for reach_num in range(int(merge_description["hyd_reach_number"])):
            reach_group = data_group.create_group('reach_' + str(reach_num))
            # UNIT GROUP
            for unit_num in range(int(merge_description["hyd_unit_number"])):
                unit_group = reach_group.create_group('unit_' + str(unit_num))
                # MESH GROUP
                mesh_group = unit_group.create_group('mesh')
                mesh_group.create_dataset(name="tin",
                                          shape=[len(data_2d["tin"][reach_num][unit_num]),
                                                 3],
                                          data=data_2d["tin"][reach_num][unit_num])
                if "i_whole_profile" in data_2d.keys():
                    mesh_group.create_dataset(name="i_whole_profile",
                                              shape=[len(data_2d["i_whole_profile"][reach_num][unit_num]), 1],
                                              data=data_2d["i_whole_profile"][reach_num][unit_num])
                mesh_group.create_dataset(name="sub",
                                          shape=[len(data_2d["sub"][reach_num][unit_num]),
                                                 len(data_2d["sub"][reach_num][unit_num][0])],
                                          data=data_2d["sub"][reach_num][unit_num])
                # NODE GROUP
                node_group = unit_group.create_group('node')
                node_group.create_dataset(name="h",
                                          shape=[len(data_2d["h"][reach_num][unit_num]),
                                                 1],
                                          data=data_2d["h"][reach_num][unit_num])
                node_group.create_dataset(name="v",
                                          shape=[len(data_2d["v"][reach_num][unit_num]),
                                                 1],
                                          data=data_2d["v"][reach_num][unit_num])
                node_group.create_dataset(name="xy",
                                          shape=[len(data_2d["xy"][reach_num][unit_num]),
                                                 len(data_2d["xy"][reach_num][unit_num][0])],
                                          data=data_2d["xy"][reach_num][unit_num])
                node_group.create_dataset(name="z",
                                          shape=[len(data_2d["z"][reach_num][unit_num]),
                                                 1],
                                          data=data_2d["z"][reach_num][unit_num])
        # close file
        self.file_object.close()

        # save XML
        self.save_xml("Habitat")  # uppercase for xml

        # reload to add new data to attributes
        self.load_hdf5_hab(whole_profil=True)

    def load_hdf5_hab(self, units_index="all", fish_names="all", whole_profil=False, convert_to_coarser_dom=False):
        # open an hdf5
        self.open_hdf5_file(new=False)

        # attributes
        if units_index == "all":
            # load the number of time steps
            nb_t = int(self.file_object.attrs['hyd_unit_number'])
            units_index = list(range(nb_t))

        # get hab attributes
        data_description = dict()
        for attribute_name, attribute_value in list(self.file_object.attrs.items()):
            data_description[attribute_name] = attribute_value

        if fish_names != "all":
            fish_names_existing = data_description["hab_fish_list"].split(", ")
            all_fish_exist = True
            for fish_name in fish_names:
                if fish_name not in fish_names_existing:
                    all_fish_exist = False
                    print("Error :", fish_name, "habitat don't exist in", self.filename)
            if not all_fish_exist:
                return

        # DATA 2D WHOLE PROFIL
        if whole_profil:
            data_2D_whole_profile = dict()
            data_2D_whole_profile["tin"] = []
            data_2D_whole_profile["xy"] = []
            data_2D_whole_profile["z"] = []
            data_group = 'data_2D_whole_profile'
            # for all reach
            for reach_num in range(0, int(data_description['hyd_reach_number'])):
                reach_group = data_group + "/reach_" + str(reach_num)
                # for all unit
                tin_list = []
                xy_list = []
                z_list = []
                for unit_num in units_index:
                    if data_description['hyd_unit_wholeprofile'] == "all":
                        unit_group = reach_group + "/unit_all"
                    else:
                        unit_group = reach_group + "/unit_" + str(unit_num)
                    mesh_group = unit_group + "/mesh"
                    node_group = unit_group + "/node"
                    try:
                        # mesh
                        tin_list.append(self.file_object[mesh_group + "/tin"][:])
                        # node
                        xy_list.append(self.file_object[node_group + "/xy"][:])
                        z_list.append(self.file_object[node_group + "/z"][:].flatten())
                    except KeyError:
                        print(
                            'Warning: the dataset for tin or xy (3) is missing from the hdf5 file for one time step. \n')
                        self.file_object.close()
                        #return
                data_2D_whole_profile["tin"].append(tin_list)
                data_2D_whole_profile["xy"].append(xy_list)
                data_2D_whole_profile["z"].append(z_list)

        # DATA 2D
        data_2d = dict()
        data_2d["tin"] = []
        data_2d["i_whole_profile"] = []
        data_2d["sub"] = []
        data_2d["xy"] = []
        data_2d["z"] = []
        data_2d["h"] = []
        data_2d["v"] = []
        # fish dict
        if fish_names == "all":  # "all"
            fish_names_total_list = self.file_object.attrs["hab_fish_list"].split(", ")
            if fish_names_total_list == ['']:
                fish_names_total_list = []
        elif not fish_names:  # list of fish
            fish_names_total_list = []
        else:  # fish presence
            fish_names_total_list = fish_names
        if fish_names_total_list:
            data_2d["hv_data"] = dict()
            data_description["total_WUA_area"] = dict()
            data_description["total_wet_area"] = []
            for fish_name in fish_names_total_list:
                data_2d["hv_data"][fish_name] = []
                data_description["total_WUA_area"][fish_name] = []

        data_group = 'data_2D'
        # for all reach
        for reach_num in range(0, int(data_description['hyd_reach_number'])):
            reach_group = data_group + "/reach_" + str(reach_num)
            # for all unit
            data_2d["tin"].append([])
            data_2d["i_whole_profile"].append([])
            data_2d["sub"].append([])
            data_2d["xy"].append([])
            data_2d["z"].append([])
            data_2d["h"].append([])
            data_2d["v"].append([])
            if fish_names_total_list:
                data_description["total_wet_area"].append([])
                for fish_name in fish_names_total_list:
                    data_description["total_WUA_area"][fish_name].append([])
                    data_2d["hv_data"][fish_name].append([])
            for unit_index, unit_num in enumerate(units_index):
                unit_group = reach_group + "/unit_" + str(unit_num)
                mesh_group = unit_group + "/mesh"
                node_group = unit_group + "/node"
                try:
                    # mesh
                    data_2d["tin"][reach_num].append(self.file_object[mesh_group + "/tin"][:])
                    data_2d["i_whole_profile"][reach_num].append(self.file_object[mesh_group + "/i_whole_profile"][:])
                    if convert_to_coarser_dom and data_description["sub_classification_method"] != "coarser-dominant":
                        sub_array = self.file_object[mesh_group + "/sub"][:]
                        # dominant case = 1 ==> biggest substrate for plot
                        sub_dominant, sub_coarser = substrate_mod.percentage_to_domcoarse(sub_array, dominant_case=1)
                        data_2d["sub"][reach_num].append(np.array(list(zip(sub_coarser, sub_dominant))))
                    else:
                        data_2d["sub"][reach_num].append(self.file_object[mesh_group + "/sub"][:])
                    if fish_names_total_list:
                        for fish_name in fish_names_total_list:
                            data_2d["hv_data"][fish_name][reach_num].append(self.file_object[mesh_group + "/" + fish_name][:].flatten())
                            data_description["total_WUA_area"][fish_name][reach_num].append(self.file_object[mesh_group + "/" + fish_name].attrs["WUA"])
                        data_description["total_wet_area"][reach_num].append(self.file_object[unit_group].attrs["total_wet_area"])
                    # node
                    data_2d["xy"][reach_num].append(self.file_object[node_group + "/xy"][:])
                    data_2d["z"][reach_num].append(self.file_object[node_group + "/z"][:].flatten())
                    data_2d["h"][reach_num].append(self.file_object[node_group + "/h"][:].flatten())
                    data_2d["v"][reach_num].append(self.file_object[node_group + "/v"][:].flatten())
                except KeyError:
                    print('Warning: the dataset for tin or xy (3) is missing from the hdf5 file for one time step. \n')
                    self.file_object.close()
                    return

        # close file
        self.file_object.close()

        # set to attributes
        if whole_profil:
            self.data_2d = data_2d
            self.data_2d_whole = data_2D_whole_profile
            self.data_description = data_description
        if not whole_profil:
            self.data_2d = data_2d
            self.data_description = data_description

    def add_fish_hab(self, vh_cell, area_all, spu_all, fish_names, pref_list, stages_chosen, name_fish_sh):
        """
        This function takes a merge file and add habitat data to it. The habitat data is given by cell. It also save the
        velocity and the water height by cell (and not by node)

        :param hdf5_name: the name of the merge file
        :param path_hdf5: the path to this file
        :param vh_cell: the habitat value by cell
        :param area_all: total wet area by reach
        :param spu_all: total SPU by reach
        :param fish_name: the name of the fish (with the stage in it)
        """
        # open an hdf5
        self.open_hdf5_file(new=False)

        # load the number of reach
        try:
            nb_r = int(self.file_object.attrs["hyd_reach_number"])
        except KeyError:
            print(
                'Error: the number of time step is missing from :' + self.filename)
            return

        # load the number of time steps
        try:
            nb_t = int(self.file_object.attrs["hyd_unit_number"])
        except KeyError:
            print('Error: the number of time step is missing from :' + self.filename)
            return

        # add name and stage of fish
        if len(vh_cell) != len(fish_names):
            print('Error: length of the list of fish name is not coherent')
            self.file_object.close()
            return

        fish_replaced = []

        # data_2D
        data_group = self.file_object['data_2D']
        # REACH GROUP
        for reach_num in range(nb_r):
            reach_group = data_group["reach_" + str(reach_num)]
            # UNIT GROUP
            for unit_num in range(nb_t):
                unit_group = reach_group["unit_" + str(unit_num)]
                unit_group.attrs['total_wet_area'] = str(area_all[reach_num][unit_num])
                # MESH GROUP
                mesh_group = unit_group["mesh"]
                # HV by celle for each fish
                for fish_num, fish_name in enumerate(fish_names):
                    if fish_name in mesh_group:  # if exist erase it
                        del mesh_group[fish_name]
                        fish_data_set = mesh_group.create_dataset(name=fish_name,
                                                                  shape=[len(vh_cell[fish_num][reach_num][unit_num]),
                                                                         1],
                                                                  data=vh_cell[fish_num][reach_num][unit_num])
                        fish_replaced.append(fish_name)
                    else:  # if not exist create it
                        fish_data_set = mesh_group.create_dataset(name=fish_name,
                                                                  shape=[len(vh_cell[fish_num][reach_num][unit_num]),
                                                                         1],
                                                                  data=vh_cell[fish_num][reach_num][unit_num])
                    fish_data_set.attrs['pref_file'] = pref_list[fish_num]
                    fish_data_set.attrs['stage'] = stages_chosen[fish_num]
                    fish_data_set.attrs['short_name'] = name_fish_sh[fish_num]
                    fish_data_set.attrs['WUA'] = str(spu_all[fish_num][reach_num][unit_num])
                    fish_data_set.attrs['HV'] = str(spu_all[fish_num][reach_num][unit_num] / area_all[reach_num][unit_num])

        # get all fish names and total number
        fish_names_total_list = list(mesh_group.keys())
        if "i_whole_profile" in fish_names_total_list:
            fish_names_total_list.remove("i_whole_profile")
        if "tin" in fish_names_total_list:
            fish_names_total_list.remove("tin")
        if "sub" in fish_names_total_list:
            fish_names_total_list.remove("sub")
        # get xml and stage fish
        xml_names = []
        stage_names = []
        names_short = []
        for fish_name in fish_names_total_list:
            xml_names.append(mesh_group[fish_name].attrs['pref_file'])
            stage_names.append(mesh_group[fish_name].attrs['stage'])
            names_short.append(mesh_group[fish_name].attrs['short_name'])
        # set to attributes
        self.file_object.attrs["hab_fish_list"] = ", ".join(fish_names_total_list)
        self.file_object.attrs["hab_fish_number"] = str(len(fish_names_total_list))
        self.file_object.attrs["hab_fish_pref_list"] = ", ".join(xml_names)
        self.file_object.attrs["hab_fish_stage_list"] = ", ".join(stage_names)
        self.file_object.attrs["hab_fish_shortname_list"] = ", ".join(names_short)

        if fish_replaced:
            fish_replaced = set(fish_replaced)
            fish_replaced = "; ".join(fish_replaced)
            print(f'Warning: fish(s) information replaced in hdf5 file ({fish_replaced}).\n')

        # close file
        self.file_object.close()

        # reload to add new data to attributes
        self.load_hdf5_hab(convert_to_coarser_dom=True)

    # EXPORT SHP
    def export_mesh_whole_profile_shp(self, fig_opt):
        if fig_opt['shape_output'] == "True":

            # for all reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for all units (selected or all)
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    if self.data_description['hyd_unit_wholeprofile'] == "all":
                        unit_names = ["all"]
                        # set name
                        unit_name_str = unit_names[0]
                    else:
                        unit_names = self.data_description['hyd_unit_list'].split(", ")
                        # set name
                        unit_name_str = str(unit_names[unit_num])

                    if "." in unit_name_str:
                        unit_name_str = unit_name_str.replace(".", "%")

                    name_shp = self.basename + "_whole_profile_mesh_r" + str(reach_num) + "_t" + unit_name_str + '.shp'

                    # for each mesh
                    w = shapefile.Writer(shapefile.POLYGONZ)
                    w.autoBalance = 1
                    w.field('ID', 'C')

                    # for each mesh
                    for mesh_num in range(0, len(self.data_2d_whole["tin"][reach_num][unit_num])):
                        node1 = self.data_2d_whole["tin"][reach_num][unit_num][mesh_num][0]  # node num
                        node2 = self.data_2d_whole["tin"][reach_num][unit_num][mesh_num][1]
                        node3 = self.data_2d_whole["tin"][reach_num][unit_num][mesh_num][2]
                        # data geom (get the triangle coordinates)
                        p1 = list(self.data_2d_whole["xy"][reach_num][unit_num][node1].tolist() + [float(self.data_2d_whole["z"][reach_num][unit_num][node1])])
                        p2 = list(self.data_2d_whole["xy"][reach_num][unit_num][node2].tolist() + [float(self.data_2d_whole["z"][reach_num][unit_num][node2])])
                        p3 = list(self.data_2d_whole["xy"][reach_num][unit_num][node3].tolist() + [float(self.data_2d_whole["z"][reach_num][unit_num][node3])])
                        w.poly(parts=[[p1, p2, p3, p1]], shapeType=15)  # the double [[]] is important or it bugs, but why?
                        w.record(mesh_num)

                    # filename
                    if fig_opt['erase_id'] == 'True':  # erase file if exist ?
                        if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                            try:
                                os.remove(os.path.join(self.path_shp, name_shp))
                            except PermissionError:
                                print(
                                    'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                                return
                    else:
                        if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                            name_shp = self.basename + "_r" + str(reach_num) + "_t" + unit_name_str + '_' + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S") + '.shp'

                    # write file
                    w.save(os.path.join(self.path_shp, name_shp))

                    if self.data_description["hyd_epsg_code"] != "unknown":
                        try:
                            string_prj = get_prj_from_epsg_web(int(self.data_description["hyd_epsg_code"]))
                            open(os.path.join(self.path_shp, os.path.splitext(name_shp)[0]) + ".prj", "w").write(string_prj)
                        except:
                            print("Warning : Can't write .prj from EPSG code :", self.data_description["hyd_epsg_code"])

                    # stop loop in this case (if one unit in whole profile)
                    if self.data_description['hyd_unit_wholeprofile'] == "all":
                        break

    def export_mesh_shp(self, fig_opt):
        if fig_opt['shape_output'] == "True":
            # get units list
            unit_names = self.data_description["hyd_unit_list"].split(", ")

            # init
            fish_names = []

            # get fish name
            if self.hdf5_type == "habitat":
                fish_names = self.data_description["hab_fish_list"].split(", ")
                if fish_names != ['']:
                    pref_list = self.data_description["hab_fish_pref_list"].split(", ")
                    stage_list = self.data_description["hab_fish_stage_list"].split(", ")
                else:
                    fish_names = []

            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    # set name
                    unit_name_str = str(unit_names[unit_num])
                    if "." in unit_name_str:
                        unit_name_str = unit_name_str.replace(".", "%")

                    name_shp = self.basename + "_mesh_r" + str(reach_num) + "_t" + unit_name_str + '.shp'
                    shp_exist = False

                    # if exist
                    if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                        shp_exist = True
                        if self.type_for_xml == "hdf5_habitat":
                            if fish_names:
                                # read shapefile
                                w = shapefile.Editor(os.path.join(self.path_shp, name_shp))
                                # remove fish fields
                                w.fields = w.fields[:6]
                                # add fish field
                                for fish_num, _ in enumerate(fish_names):
                                    column_name = os.path.splitext(pref_list[fish_num])[0].upper() + stage_list[fish_num]
                                    w.field(column_name, 'F', 50, 8)
                                # add fish data for each mesh (line in attributes shp)
                                for mesh_num in range(0, len(self.data_2d["tin"][reach_num][unit_num])):
                                    for fish_name in fish_names:
                                        w.records[mesh_num].append(self.data_2d["hv_data"][fish_name][reach_num][unit_num][mesh_num])
                                name_dbf = os.path.splitext(name_shp)[0] + ".dbf"
                                w.saveDbf(os.path.join(self.path_shp, name_dbf))

                    # if not exist
                    if not shp_exist or not fish_names:  # not exist or merge case
                        # for each mesh
                        w = shapefile.Writer(shapefile.POLYGONZ)
                        w.autoBalance = 1
                        w.field('velocity', 'F', 50, 8)
                        w.field('height', 'F', 50, 8)
                        w.field('conveyance', 'F', 50, 8)
                        w.field('i_whole_pro', 'N', 10, 0)
                        if self.type_for_xml == "hdf5_habitat":
                            # sub
                            if self.data_description["sub_classification_method"] == 'coarser-dominant':
                                w.field('coarser', 'N', 10, 0)
                                w.field('dom', 'N', 10, 0)
                            if self.data_description["sub_classification_method"] == 'percentage':
                                if self.data_description["sub_classification_code"] == "Cemagref":
                                    sub_class_number = 8
                                if self.data_description["sub_classification_code"] == "Sandre":
                                    sub_class_number = 12
                                for i in range(sub_class_number):
                                    w.field('S' + str(i + 1), 'N', 10, 0)
                            # fish
                            if fish_names:
                                for fish_num, _ in enumerate(fish_names):
                                    column_name = os.path.splitext(pref_list[fish_num])[0].upper() + stage_list[fish_num]
                                    w.field(column_name, 'F', 50, 8)

                        # for each mesh
                        for mesh_num in range(0, len(self.data_2d["tin"][reach_num][unit_num])):
                            node1 = self.data_2d["tin"][reach_num][unit_num][mesh_num][0]  # node num
                            node2 = self.data_2d["tin"][reach_num][unit_num][mesh_num][1]
                            node3 = self.data_2d["tin"][reach_num][unit_num][mesh_num][2]
                            # V
                            v1 = self.data_2d["v"][reach_num][unit_num][node1]  # velocity
                            v2 = self.data_2d["v"][reach_num][unit_num][node2]
                            v3 = self.data_2d["v"][reach_num][unit_num][node3]
                            v_mean_mesh = 1.0 / 3.0 * (v1 + v2 + v3)
                            # H
                            h1 = self.data_2d["h"][reach_num][unit_num][node1]  # height
                            h2 = self.data_2d["h"][reach_num][unit_num][node2]
                            h3 = self.data_2d["h"][reach_num][unit_num][node3]
                            h_mean_mesh = 1.0 / 3.0 * (h1 + h2 + h3)
                            # conveyance
                            conveyance = v_mean_mesh * h_mean_mesh
                            # i_whole_profile
                            i_whole_profile = self.data_2d["i_whole_profile"][reach_num][unit_num][mesh_num]
                            # data geom (get the triangle coordinates)
                            p1 = list(self.data_2d["xy"][reach_num][unit_num][node1].tolist() + [float(self.data_2d["z"][reach_num][unit_num][node1])])
                            p2 = list(self.data_2d["xy"][reach_num][unit_num][node2].tolist() + [float(self.data_2d["z"][reach_num][unit_num][node2])])
                            p3 = list(self.data_2d["xy"][reach_num][unit_num][node3].tolist() + [float(self.data_2d["z"][reach_num][unit_num][node3])])
                            w.poly(parts=[[p1, p2, p3, p1]], shapeType=15)  # the double [[]] is important or it bugs, but why?
                            if self.type_for_xml == "hdf5_habitat":
                                sub = self.data_2d["sub"][reach_num][unit_num][mesh_num]
                                if not fish_names:
                                    data_here = [v_mean_mesh, h_mean_mesh, conveyance, i_whole_profile, *sub.tolist()]
                                if fish_names:
                                    fish_data = []
                                    for fish_name in fish_names:
                                        fish_data.append(self.data_2d["hv_data"][fish_name][reach_num][unit_num][mesh_num])
                                    data_here = [v_mean_mesh, h_mean_mesh, conveyance, i_whole_profile, *sub.tolist(), *fish_data]
                            else:
                                data_here = [v_mean_mesh, h_mean_mesh, conveyance, i_whole_profile]
                            # the * pass tuple to function argument
                            w.record(*data_here)

                        # filename
                        if fig_opt['erase_id'] == 'True':  # erase file if exist ?
                            if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                                try:
                                    os.remove(os.path.join(self.path_shp, name_shp))
                                except PermissionError:
                                    print(
                                        'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                                    return
                        else:
                            if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                                name_shp = self.basename + "_r" + str(reach_num) + "_t" + unit_name_str + '_' + time.strftime(
                                    "%d_%m_%Y_at_%H_%M_%S") + '.shp'

                        # write file
                        w.save(os.path.join(self.path_shp, name_shp))

                        # write .prj
                        if self.hdf5_type == "habitat":
                            if self.data_description["hab_epsg_code"] != "unknown":
                                try:
                                    string_prj = get_prj_from_epsg_web(int(self.data_description["hab_epsg_code"]))
                                    open(os.path.join(self.path_shp, os.path.splitext(name_shp)[0]) + ".prj", "w").write(string_prj)
                                except:
                                    print("Warning : Can't write .prj from EPSG code :", self.data_description["hab_epsg_code"])
                        if self.hdf5_type == "hydraulic":
                            if self.data_description["hyd_epsg_code"] != "unknown":
                                try:
                                    string_prj = get_prj_from_epsg_web(int(self.data_description["hyd_epsg_code"]))
                                    open(os.path.join(self.path_shp, os.path.splitext(name_shp)[0]) + ".prj", "w").write(string_prj)
                                except:
                                    print("Warning : Can't write .prj from EPSG code :", self.data_description["hyd_epsg_code"])

    def export_point_shp(self, fig_opt):
        if fig_opt['shape_output'] == "True":
            # get units list
            unit_names = self.data_description["hyd_unit_list"].split(", ")

            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    # set name
                    unit_name_str = str(unit_names[unit_num])
                    if "." in unit_name_str:
                        unit_name_str = unit_name_str.replace(".", "%")
                    name_shp = self.basename + "_point_r" + str(reach_num) + "_t" + unit_name_str + '.shp'

                    # for each mesh
                    w = shapefile.Writer(shapefile.POINTZ)
                    w.autoBalance = 1
                    w.field('height', 'F', 50, 8)
                    w.field('velocity', 'F', 50, 8)
                    w.field('elevation', 'F', 50, 8)

                    # for each point
                    for point_num in range(0, len(self.data_2d["xy"][reach_num][unit_num])):
                        # data geom (get the triangle coordinates)
                        x = self.data_2d["xy"][reach_num][unit_num][point_num][0]
                        y = self.data_2d["xy"][reach_num][unit_num][point_num][1]
                        h = self.data_2d["h"][reach_num][unit_num][point_num]
                        v = self.data_2d["v"][reach_num][unit_num][point_num]
                        z = self.data_2d["z"][reach_num][unit_num][point_num]
                        w.point(x=x, y=y, z=z, shapeType=11)  # the double [[]] is important or it bugs, but why?
                        data_here = [h, v, z]
                        w.record(*data_here)

                    # filename
                    if fig_opt['erase_id'] == 'True':  # erase file if exist ?
                        if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                            try:
                                os.remove(os.path.join(self.path_shp, name_shp))
                            except PermissionError:
                                print(
                                    'Error: The shapefile is currently open in an other program. Could not be re-written \n')
                                return
                    else:
                        if os.path.isfile(os.path.join(self.path_shp, name_shp)):
                            name_shp = self.basename + "_r" + str(reach_num) + "_t" + unit_name_str + '_' + time.strftime(
                                "%d_%m_%Y_at_%H_%M_%S") + '.shp'

                    # write file
                    w.save(os.path.join(self.path_shp, name_shp))

                    # write .prj
                    if self.data_description["hyd_epsg_code"] != "unknown":
                        try:
                            string_prj = get_prj_from_epsg_web(int(self.data_description["hyd_epsg_code"]))
                            open(os.path.join(self.path_shp, os.path.splitext(name_shp)[0]) + ".prj", "w").write(string_prj)
                        except:
                            print("Warning : Can't write .prj from EPSG code :", self.data_description["hyd_epsg_code"])

    # EXPORT TXT
    def export_spu_txt(self, fig_opt):
        if fig_opt['text_output'] == "True":
            path_txt = os.path.join(self.data_description["path_projet"], "output", "text")
            if not os.path.exists(path_txt):
                print('Error: the path to the text file is not found. Text files not created \n')

            name_base = os.path.splitext(self.data_description["hab_filename"])[0]
            sim_name = self.data_description["hyd_unit_list"].split(", ")
            fish_names = self.data_description["hab_fish_list"].split(", ")
            unit_type = self.data_description["hyd_unit_type"][
                        self.data_description["hyd_unit_type"].find('[') + 1:self.data_description[
                            "hyd_unit_type"].find(']')]

            if not fig_opt['erase_id'] == "True":
                if fig_opt['language'] == 0:
                    name = 'wua_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                else:
                    name = 'spu_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
            else:
                if fig_opt['language'] == 0:
                    name = 'wua_' + name_base + '.txt'
                else:
                    name = 'spu_' + name_base + '.txt'
                if os.path.isfile(os.path.join(path_txt, name)):
                    try:
                        os.remove(os.path.join(path_txt, name))
                    except PermissionError:
                        print('Error: Could not modify text file as it is open in another program. \n')
                        return

            name = os.path.join(path_txt, name)

            # open text to write
            with open(name, 'wt', encoding='utf-8') as f:

                # header 1
                if fig_opt['language'] == 0:
                    header = 'reach\tunit\treach_area'
                else:
                    header = 'troncon\tunit\taire_troncon'
                if fig_opt['language'] == 0:
                    header += "".join(['\tHV' + str(i) for i in range(len(fish_names))])
                    header += "".join(['\tWUA' + str(i) for i in range(len(fish_names))])
                else:
                    header += "".join(['\tVH' + str(i) for i in range(len(fish_names))])
                    header += "".join(['\tSPU' + str(i) for i in range(len(fish_names))])
                header += '\n'
                f.write(header)
                # header 2
                header = '[]\t[' + unit_type + ']\t[m2]'
                header += "".join(['\t[]' for _ in range(len(fish_names))])
                header += "".join(['\t[m2]' for _ in range(len(fish_names))])
                header += '\n'
                f.write(header)
                # header 3
                header = 'all\tall\tall '
                for fish_name in fish_names * 2:
                    header += '\t' + fish_name.replace(' ', '_')
                header += '\n'
                f.write(header)

                for reach_num in range(0, len(self.data_description["total_wet_area"])):
                    for unit_num in range(0, len(self.data_description["total_wet_area"][reach_num])):
                        area_reach = self.data_description["total_wet_area"][reach_num][unit_num]
                        if not sim_name:
                            data_here = str(reach_num) + '\t' + str(unit_num) + '\t' + str(area_reach)
                        else:
                            data_here = str(reach_num) + '\t' + sim_name[unit_num] + '\t' + str(area_reach)
                        # HV
                        for fish_name in fish_names:
                            try:
                                wua_fish = self.data_description["total_WUA_area"][fish_name][reach_num][unit_num]
                                data_here += '\t' + str(float(wua_fish) / float(area_reach))
                            except TypeError:
                                data_here += '\t' + 'NaN'
                        # WUA
                        for fish_name in fish_names:
                            wua_fish = self.data_description["total_WUA_area"][fish_name][reach_num][unit_num]
                            data_here += '\t' + str(wua_fish)

                        data_here += '\n'
                        f.write(data_here)

    def export_pdf(self, path_bio, fig_opt):
        """
        # xmlfiles, stages_chosen, path_bio, path_im_bio, path_out, fig_opt
        This functionc create a pdf with information about the fish.
        It tries to follow the chosen language, but
        the stage name are not translated and the decription are usually
        only given in French.

        :param xmlfiles: the name of the xmlfile (without the path!)
        :param stages_chosen: the stage chosen (might not be all stages)
        :param path_bio: the path with the biological xml file
        :param path_im_bio: the path with the images of the fish
        :param path_out: the path where to save the .pdf file
            (usually other_outputs)
        :param fig_opt: the figure options (contain the chosen language)
        """
        if fig_opt['fish_info'] == "True":
            # get data
            xmlfiles = self.data_description["hab_fish_pref_list"].split(", ")
            stages_chosen = self.data_description["hab_fish_stage_list"].split(", ")
            path_im_bio = path_bio
            path_out = os.path.join(self.path_prj, "output", "figures")

            plt.close()
            plt.rcParams['figure.figsize'] = 21, 29.7  # a4
            plt.rcParams['font.size'] = 24

            # get the stage chosen for each species and get rid of repetition
            stage_chosen2 = []
            stage_here = []
            xmlold = 'sdfsdfs'
            xmlfiles2 = []
            for idx, f in enumerate(xmlfiles):
                if xmlold != f:
                    xmlfiles2.append(f)
                    if stage_here:
                        stage_chosen2.append(stage_here)
                    stage_here = []
                stage_here.append(stages_chosen[idx])
                xmlold = f
            if stage_here:
                stage_chosen2.append(stage_here)
            xmlfiles = xmlfiles2

            # create the pdf
            for idx, f in enumerate(xmlfiles):

                # read pref
                xmlfile = os.path.join(path_bio, f)
                [h_all, vel_all, sub_all, code_fish, name_fish, stages] = \
                    bio_info_mod.read_pref(xmlfile)

                # read additionnal info
                attributes = ['Description', 'Image', 'French_common_name',
                              'English_common_name', ]
                # careful: description is last data returned
                data = bio_info_mod.load_xml_name(path_bio, attributes, [f])

                # create figure
                fake_value = Value("i", 0)
                [f, axarr] = plot_mod.plot_suitability_curve(fake_value, h_all, vel_all, sub_all, code_fish, name_fish,
                                                             stages, True, fig_opt)

                # modification of the orginal preference fig
                # (0,0) is bottom left - 1 is the end of the page in x and y direction
                plt.tight_layout(rect=[0.05, 0.05, 0.95, 0.53])
                # position for the image

                # add a fish image
                if path_im_bio:
                    fish_im_name = os.path.join(os.getcwd(), path_im_bio, data[0][0])
                    if os.path.isfile(fish_im_name):
                        im = plt.imread(mpl.cbook.get_sample_data(fish_im_name))
                        newax = f.add_axes([0.1, 0.4, 0.25, 0.25], anchor='NE',
                                           zorder=-1)
                        newax.imshow(im)
                        newax.axis('off')

                # move suptitle
                if fig_opt['language'] == 0:
                    f.suptitle('Suitability curve', x=0.5, y=0.55, fontsize=32,
                               weight='bold')
                elif fig_opt['language'] == 1:
                    f.suptitle('Courbe de préférence', x=0.5, y=0.55, fontsize=32,
                               weight='bold')
                else:
                    f.suptitle('Suitability curve', x=0.5, y=0.55, fontsize=32,
                               weight='bold')
                # general info
                if fig_opt['language'] == 0:
                    plt.figtext(0.1, 0.7,
                                "Latin name:\n\nCommon Name:\n\nONEMA fish code:\n\nStage chosen:\n\nDescription:",
                                weight='bold', fontsize=32)
                    text_all = name_fish + '\n\n' + data[0][2] \
                               + '\n\n' + code_fish + '\n\n'
                elif fig_opt['language'] == 1:
                    plt.figtext(0.1, 0.7, "Nom latin :\n\nNom commun :\n\nCode ONEMA:\n\nStade choisi :\n\nDescription :",
                                weight='bold', fontsize=32)
                    text_all = name_fish + '\n\n' + data[0][1] + '\n\n' \
                               + code_fish + '\n\n'
                else:
                    plt.figtext(0.1, 0.7,
                                "Latin name:\n\nCommon Name:\n\nONEMA fish code:\n\nStage chosen:\n\nDescription:",
                                weight='bold', fontsize=32)
                    text_all = name_fish + '\n\n' + data[0][2] \
                               + '\n\n' + code_fish + '\n\n'
                for idx, s in enumerate(stage_chosen2[idx]):
                    text_all += s + ', '
                text_all = text_all[:-2] + '\n\n'
                plt.figtext(0.4, 0.7, text_all, fontsize=32)
                # bbox={'facecolor':'grey', 'alpha':0.07, 'pad':50}

                # descirption
                if len(data[0][-1]) > 250:
                    plt.figtext(0.4, 0.61, data[0][-1][:250] + '...', wrap=True,
                                fontsize=32)
                else:
                    plt.figtext(0.4, 0.61, data[0][-1], wrap=True, fontsize=32)

                # title of the page
                plt.figtext(0.1, 0.9, "REPORT - " + name_fish, fontsize=55,
                            weight='bold',
                            bbox={'facecolor': 'grey', 'alpha': 0.15, 'pad': 50})

                # day
                plt.figtext(0.8, 0.95, 'HABBY - ' + time.strftime("%d %b %Y"))

                # save
                filename = os.path.join(path_out, 'report_' + code_fish + '.pdf')
                try:
                    plt.savefig(filename)
                except PermissionError:
                    print('Warning: Close .pdf to update fish information')

    # EXPORT 3D
    def export_stl(self, fig_opt):
        if fig_opt['stl'] == "True":
            """ create stl whole profile (to see topography) """
            # get data
            xy = self.data_2d_whole["xy"][0][0]
            z = self.data_2d_whole["z"][0][0] * 10
            faces = self.data_2d_whole["tin"][0][0]
            vertices = np.column_stack([xy, z])
            # Create the mesh
            stl_file = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
            for i, f in enumerate(faces):
                for j in range(3):
                    stl_file.vectors[i][j] = vertices[f[j], :]
            # Write the mesh to file "cube.stl"
            stl_file.save(os.path.join(self.path_visualisation,
                                       self.basename + "_wholetopography.stl"))

            """ create stl water level (to see water level on topography) """
            # get units list
            unit_names = self.data_description["hyd_unit_list"].split(", ")
            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    # get data
                    xy = self.data_2d["xy"][reach_num][unit_num]
                    # with warnings.catch_warnings():
                    #     warnings.filterwarnings('error')
                    try:
                        z = (self.data_2d["z"][reach_num][unit_num] + self.data_2d["h"][reach_num][unit_num]) * 10
                    except Warning:
                        print('oh no!')
                    faces = self.data_2d["tin"][reach_num][unit_num]
                    vertices = np.column_stack([xy, z])
                    # Create the mesh
                    stl_file = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
                    for i, f in enumerate(faces):
                        for j in range(3):
                            stl_file.vectors[i][j] = vertices[f[j], :]
                    # Write the mesh to file "cube.stl"
                    stl_file.save(os.path.join(self.path_visualisation,
                                               self.basename + "_waterlevel_" + str(unit_names[unit_num]) + ".stl"))

    def export_paraview(self, fig_opt):
        if fig_opt['paraview'] == "True":
            file_names_all = []
            if len(self.basename) > 60:
                self.basename = os.path.join(self.path_visualisation, self.basename)[:-25]
            else:
                self.basename = os.path.join(self.path_visualisation, self.basename)

            # format the name of species and stage
            name_fish = self.data_description["hab_fish_list"].split(", ")
            for id, n in enumerate(name_fish):
                name_fish[id] = n.replace('_', ' ')

            # for each reach
            for reach_num in range(0, int(self.data_description['hyd_reach_number'])):
                if not fig_opt["erase_id"] == "True":
                    fileName = self.basename + '_' + 'Reach' + str(reach_num) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    fileName = self.basename + '_' + 'Reach' + str(reach_num)

                # for each unit
                for unit_num in range(0, int(self.data_description['hyd_unit_number'])):
                    # create one vtu file by time step
                    x = np.ascontiguousarray(self.data_2d["xy"][reach_num][unit_num][:, 0])
                    y = np.ascontiguousarray(self.data_2d["xy"][reach_num][unit_num][:, 1])
                    try:
                        z = np.ascontiguousarray((self.data_2d["z"][reach_num][unit_num] + self.data_2d["h"][reach_num][unit_num]) * 10)
                    except Warning:
                        print('oh no!')

                    connectivity = np.reshape(self.data_2d["tin"][reach_num][unit_num], (len(self.data_2d["tin"][reach_num][unit_num]) * 3,))
                    offsets = np.arange(3, len(self.data_2d["tin"][reach_num][unit_num]) * 3 + 3, 3)
                    offsets = np.array(list(map(int, offsets)))
                    cell_types = np.zeros(len(self.data_2d["tin"][reach_num][unit_num]), ) + 5  # triangle
                    cell_types = np.array(list((map(int, cell_types))))

                    # fish
                    cellData = {}
                    for fish_name in self.data_description["hab_fish_list"].split(", "):
                        newkey = "HV " + fish_name
                        cellData[newkey] = self.data_2d["hv_data"][fish_name][reach_num][unit_num]

                    # substrate
                    cellData["sub_coarser"] = np.array(list(zip(*self.data_2d["sub"][reach_num][unit_num])))[0]
                    cellData["sub_dominant"] = np.array(list(zip(*self.data_2d["sub"][reach_num][unit_num])))[1]

                    # hydrau data creation for each mesh
                    v_mean_mesh_list = []
                    h_mean_mesh_list = []
                    for mesh_num in range(0, len(self.data_2d["tin"][reach_num][unit_num])):
                        node1 = self.data_2d["tin"][reach_num][unit_num][mesh_num][0]  # node num
                        node2 = self.data_2d["tin"][reach_num][unit_num][mesh_num][1]
                        node3 = self.data_2d["tin"][reach_num][unit_num][mesh_num][2]
                        # data attributes
                        v1 = self.data_2d["v"][reach_num][unit_num][node1]  # velocity
                        v2 = self.data_2d["v"][reach_num][unit_num][node2]
                        v3 = self.data_2d["v"][reach_num][unit_num][node3]
                        v_mean_mesh = 1.0 / 3.0 * (v1 + v2 + v3)
                        v_mean_mesh_list.append(v_mean_mesh)
                        h1 = self.data_2d["h"][reach_num][unit_num][node1]  # height
                        h2 = self.data_2d["h"][reach_num][unit_num][node2]
                        h3 = self.data_2d["h"][reach_num][unit_num][node3]
                        h_mean_mesh = 1.0 / 3.0 * (h1 + h2 + h3)
                        h_mean_mesh_list.append(h_mean_mesh)

                    cellData['height'] = np.array(h_mean_mesh_list)
                    cellData['velocity'] = np.array(v_mean_mesh_list)

                    # create the grid and the vtu files
                    basename = fileName + '_unit' + str(unit_num)
                    basename_ext = basename + '.vtu'
                    if fig_opt["erase_id"] == "True":
                        if os.path.isfile(basename_ext):
                            os.remove(basename_ext)
                    file_names_all.append(basename_ext)
                    hl_mod.unstructuredGridToVTK(basename, x, y, z, connectivity, offsets, cell_types,
                                                 cellData)

                # create the "grouping" file to read all time step together
                name_here = fileName + '.pvd'
                if fig_opt["erase_id"] == "True":
                    if os.path.isfile(name_here):
                        os.remove(name_here)
                paraview_mod.writePVD(name_here, file_names_all)
                file_names_all = []


#################################################################

def open_hdf5(hdf5_name, mode="read"):
    """
    This is a function which opens an hdf5 file and check that it exists. It does not load the data. It only opens the
    files.
    :param hdf5_name: the path and name of the hdf5 file (string)
    :param mode: read or write
    """
    # get mode
    if mode == "read":
        mode_hdf5 = 'r'
    if mode == "write":
        mode_hdf5 = 'r+'

    blob, ext = os.path.splitext(hdf5_name)
    if ext not in ('.hyd', '.sub', '.hab'):
        print("Warning: the file should be of hdf5 type ('.hyd', '.sub', '.hab').")
    if os.path.isfile(hdf5_name):
        try:
            file = h5py.File(hdf5_name, mode_hdf5)
        except OSError:
            print('Error: the hdf5 file could not be loaded.\n')
            return None
    else:
        print("Error: The hdf5 file is not found. \n")
        print('Error: ' + hdf5_name + '\n')
        return None

    return file


def open_hdf5_(hdf5_name, path_hdf5, mode):
    """
    A function to load hdf5 file. If hdf5_name is an absolute path, the path_hdf5 is not used. If it is a relative path,
    the path is composed of the path to the 'hdf5' folder (path_hdf5/hdf5_name) composed with hdf5_name.
    return file object open, false or '', true if error occured

    :param hdf5_name: path and file name to the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :param mode: read or write
    """
    # open the file
    if os.path.isabs(hdf5_name):
        file_ = open_hdf5(hdf5_name, mode)
    else:
        if path_hdf5:
            file_ = open_hdf5(os.path.join(path_hdf5, hdf5_name), mode)
        else:
            print('Error" No path to the project given although a relative path was provided')
            return "", True
    if file_ is None:
        print('Error: hdf5 file could not be open. \n')
        return "", True
    return file_, False


def save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, nb_dim, path_hdf5,
                            ikle_all_t, point_all_t, point_c_all_t, inter_vel_all_t, inter_h_all_t,
                            sub_description_system=[], xhzv_data=[], coord_pro=[], vh_pro=[], nb_pro_reach=[],
                            merge=False, sub_pg_all_t=[], sub_dom_all_t=[], sub_per_all_t=[], sim_name=[],
                            hyd_filename_source='', sub_ini_name='', hydro_ini_name='', save_option=None, hdf5_type=None):
    """
    This function save the hydrological data in the hdf5 format.

    :param name_hdf5: the base name for the hdf5 file to be created (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param ikle_all_t: the connectivity table for all discharge, for all reaches and all time steps
    :param point_all_t: the point forming the grid, for all reaches and all time steps
    :param point_c_all_t: the point at the center of the cells, for all reaches and all time steps
    :param inter_vel_all_t: the velocity for all grid point, for all reaches and all time steps (by node)
    :param inter_h_all_t: the height for all grid point, for all reaches and all time steps (by node)
    :param xhzv_data: data linked with 1D model (only used when a 1D model was transformed to a 2D)
    :param coord_pro: data linked with 1.5D model or data created by dist_vist from a 1D model (profile data)
    :param vh_pro: data linked with 1.5D model or data created by dist_vist from a 1D model (velcoity and height data)
    :param nb_pro_reach: data linked with 1.5D model or data created by dist_vist from a 1D model (nb profile)
    :param merge: If True, the data is coming from the merging of substrate and hydrological data.
    :param sub_pg_all_t: the data of the coarser substrate given on the merged grid by cell. Only used if merge is True.
    :param sub_dom_all_t: the data of the dominant substrate given on the merged grid by cells. Only used if merge is True.
    :param sub_per_all_t: the data of the substreate by percentage. Only used with lammi (mostly)
    :param sim_name: the name of the simulation or the names of the time steps if the names are not [0,1,2,3, etc.]
    :param hyd_filename_source: The name of the substrate file used to create the hdf5 hyd
    :param sub_ini_name: The name of the substrate hdf5 file from which the data originates
    :param hydro_ini_name: the name of the hydraulic hdf5 file from which the data originates
    :param save_option: If save_option is not none, the variable erase_idem which is usually given in the figure option
           is overwritten by save_option which is boolean. This is useful for habby cmd.
    :param version: The version number of HABBY


    **Technical comments**

    This function could look better inside the class SubHydroW where it was before. However, it was not possible
    to use it on the command line and it was not pratical for having two thread (it is impossible to have a method
    as a second thread)

    This function creates an hdf5 file which contains the hydrological data. First it creates an empty hdf5.
    Then it fill the hdf5 with data. For 1D model, it fill the data in 1D (the original data), then the 1.5D data
    created by dist_vitess2.py and finally the 2D data. For model in 2D it only saved 2D data. Hence, the 2D data
    is the data which is common to all model and which can always be loaded from a hydrological hdf5 created by
    HABBY. The 1D and 1.5D data is only present if the model is 1D or 1.5D. Here is some general info about the
    created hdf5:

    *   Name of the file: name_hdf5. If we save all file even if the model is re-run we add a time stamp.
        For example, test4_HEC-RAS_25_10_2016_12_23_23.hab.
    *   Position of the file: in the folder  figure_habby currently (probably in a project folder in the final software)
    *   Format of the hdf5 file:

        *   data_1d:  xhzv_data_all (given profile by profile)
        *   data_15d :  vh_pro, coord_pro (given profile by profile in a dict) and nb_pro_reach.
        *   data_2d : For each time step, for each reach: ikle, point, point_c, inter_h, inter_vel

    If a list has elements with a changing number of variables, it is necessary to create a dictionary to save
    this list in hdf5. For example, a dictionary will be needed to save the following list: [[1,2,3,4], [1,2,3]].
    This is used for example, to save data by profile as we can have profile with more or less points. We also note
    in the hdf5 attribute some important info such as the project name, path to the project, hdf5 version.
    This can be useful if an hdf5 is lost and is not linked with any project. We also add the name of the created
    hdf5 to the xml project file. Now we can load the hydrological data using this hdf5 file and the xml project file.

    When saving habitat data, we add a time stamp so that if re-run an habitat simulation, we do not loos all the data.
    When loading, the last data should be used.

    Hdf5 file do not support unicode. It is necessary to encode string to write them.

    """
    if merge:
        extensionhdf5 = '.hab'
    if not merge:
        extensionhdf5 = '.hyd'

    # to know if we have to save a new hdf5
    if save_option is None:
        save_opt = preferences_GUI.load_fig_option(path_prj, name_prj)
        if save_opt['erase_id'] == 'True':  # xml is all in string
            erase_idem = True
        else:
            erase_idem = False
    else:
        erase_idem = save_option

    # create hdf5 name if we keep all files (need a time stamp)
    if not erase_idem:
        h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + extensionhdf5
    else:
        if name_hdf5[-4:] != extensionhdf5:
            h5name = name_hdf5 + extensionhdf5
        else:
            h5name = name_hdf5
        if os.path.isfile(os.path.join(path_hdf5, h5name)):
            try:
                os.remove(os.path.join(path_hdf5, h5name))
            except PermissionError:
                print("Could not save hdf5 file. It might be used by another program.")
                return

    # create a new hdf5
    fname = os.path.join(path_hdf5, h5name)
    file = h5py.File(fname, 'w')

    # create attributes
    file.attrs['software'] = 'HABBY'
    file.attrs['software_version'] = str(VERSION)
    file.attrs['path_projet'] = path_prj
    file.attrs['name_projet'] = name_prj
    file.attrs['hdf5_version'] = h5py.version.hdf5_version
    file.attrs['h5py_version'] = h5py.version.version
    file.attrs['hdf5_type'] = hdf5_type
    if hyd_filename_source != '':
        file.attrs['hyd_filename_source'] = hyd_filename_source
    if merge:
        file.attrs['hyd_ini_name'] = os.path.basename(hydro_ini_name)
        file.attrs['sub_ini_name'] = sub_ini_name
        file.attrs['sub_mapping_method'] = sub_description_system["sub_mapping_method"]
        file.attrs['sub_classification_code'] = sub_description_system["sub_classification_code"]
        file.attrs['sub_classification_method'] = sub_description_system["sub_classification_method"]
        file.attrs['sub_filename_source'] = sub_description_system["sub_filename_source"]
        if sub_description_system["sub_mapping_method"] != "constant":
            file.attrs['sub_epsg_code'] = sub_description_system["sub_epsg_code"]
            file.attrs['sub_default_values'] = sub_description_system["sub_default_values"]


    # save the name of the units and reach description
    if sim_name:
        # units
        unit_ascii_str = [n.strip().encode("ascii", "ignore") for n in sim_name]  # unicode is not ok with hdf5
        unit_name_dataset = file.create_dataset("description_unit", (len(sim_name),), data=unit_ascii_str)
        unit_name_dataset.attrs['nb'] = len(ikle_all_t) - 1
        unit_name_dataset.attrs['type'] = "timestep"  # TODO : change by discharge if units are discharges
        # reachs
        reach_nb = len(ikle_all_t[0])
        reach_ascii_str = [f"reach_{i}".strip().encode("ascii", "ignore") for i in
                           range(reach_nb)]  # unicode is not ok with hdf5
        reach_name_dataset = file.create_dataset("description_reach", (reach_nb,), data=reach_ascii_str)
        reach_name_dataset.attrs['nb'] = reach_nb

    # data by type of model (1D)
    if nb_dim == 1:
        Data_group = file.create_group('data_1d')
        xhzv_datag = Data_group.create_group('xhzv_data')
        xhzv_datag.create_dataset(h5name, data=xhzv_data)

    # data by type of model (1.5D)
    if nb_dim < 2:
        Data_group = file.create_group('data_15d')
        adict = dict()
        for p in range(0, len(coord_pro)):
            ns = 'p' + str(p)
            adict[ns] = coord_pro[p]
        coord_prog = Data_group.create_group('coord_pro')
        for k, v in adict.items():
            coord_prog.create_dataset(k, data=v)
            # coord_prog.create_dataset(h5name, [4, len(self.coord_pro[p][0])], data=self.coord_pro[p])
        for t in range(0, len(vh_pro)):
            there = Data_group.create_group('unit_' + str(t))
            adict = dict()
            for p in range(0, len(vh_pro[t])):
                ns = 'p' + str(p)
                adict[ns] = vh_pro[t][p]
            for k, v in adict.items():
                there.create_dataset(k, data=v)
        nbproreachg = Data_group.create_group('Number_profile_by_reach')
        nb_pro_reach2 = list(map(float, nb_pro_reach))
        nbproreachg.create_dataset(h5name, [len(nb_pro_reach2), 1], data=nb_pro_reach2)

    # data by type of model (2D)
    if nb_dim <= 2:
        warn_dry = True
        Data_group = file.create_group('data_2d')
        for t in range(0, len(ikle_all_t)):
            if t == 0:  # whole_profile
                there = Data_group.create_group('whole_profile')
            else:  # all units
                there = Data_group.create_group('unit_' + str(t - 1))
            # for all units
            for r in range(0, len(ikle_all_t[t])):
                # REACH GROUP
                rhere = there.create_group('reach_' + str(r))

                # NODE GROUP
                node_group = rhere.create_group('node')
                # coordinates (point_all / XY)
                node_group.create_dataset("xy", [len(point_all_t[t][r]), 2], data=point_all_t[t][r])
                # velocity (inter_vel_all / V)
                if len(inter_vel_all_t) > 0:
                    if len(inter_vel_all_t[t]) > 0 and not isinstance(inter_vel_all_t[t][0], float):
                        node_group.create_dataset("v", [len(inter_vel_all_t[t][r]), 1],
                                                  data=inter_vel_all_t[t][r])
                # height (inter_h_all / H)
                if len(inter_h_all_t) > 0:
                    if len(inter_h_all_t[t]) > 0 and not isinstance(inter_h_all_t[t][0], float):
                        node_group.create_dataset("h", [len(inter_h_all_t[t][r]), 1],
                                                  data=inter_h_all_t[t][r])

                # MESH GROUP
                mesh_group = rhere.create_group('mesh')
                # connectivity table (ikle / tin)
                if len(ikle_all_t[t][r]) > 0:
                    mesh_group.create_dataset("tin", [len(ikle_all_t[t][r]), len(ikle_all_t[t][r][0])],
                                              data=ikle_all_t[t][r])
                else:
                    if warn_dry:
                        print('Warning: Reach number ' + str(r) + ' has an empty grid. It might be entierely dry.')
                        warn_dry = False
                    mesh_group.create_dataset("tin", [len(ikle_all_t[t][r])], data=ikle_all_t[t][r])
                # coordinates center (point_c_all / xy_center)
                if len(point_c_all_t) > 0:
                    if len(point_c_all_t[t]) > 0 and not isinstance(point_c_all_t[t][0], float):
                        if t == 0:  # whole_profile
                            mesh_group.create_dataset("xy_center", [len(point_c_all_t[t][r]), 2],
                                                      data=point_c_all_t[t][r])
                # substrate data in the case it is a merged grid
                if merge:
                    # dominant (data_substrate_dom / sub_dominant)
                    if len(sub_dom_all_t) > 0:
                        if len(sub_dom_all_t[t]) > 0 and not isinstance(sub_dom_all_t[t][0], float):
                            data_sub_ziped = list(zip(sub_pg_all_t[t][r], sub_dom_all_t[t][r]))
                            mesh_group.create_dataset(name="sub", shape=[len(sub_dom_all_t[t][r]), 2],
                                                      data=data_sub_ziped, dtype='i8')
                    # # dominant (data_substrate_dom / sub_dominant)
                    # if len(sub_dom_all_t) > 0:
                    #     if len(sub_dom_all_t[t]) > 0 and not isinstance(sub_dom_all_t[t][0], float):
                    #         mesh_group.create_dataset("sub_dom", [len(sub_dom_all_t[t][r]), 1],
                    #                                   data=sub_dom_all_t[t][r])
                    # # coarser (data_substrate_pg / sub_coarser)
                    # if len(sub_pg_all_t) > 0:
                    #     if len(sub_pg_all_t[t]) > 0 and not isinstance(sub_pg_all_t[t][0], float):
                    #         mesh_group.create_dataset("sub_coarser", [len(sub_pg_all_t[t][r]), 1],
                    #                                   data=sub_pg_all_t[t][r])
                    # # percent (data_substrate_percentage / sub_percent)
                    # if sub_per_all_t:
                    #     if len(sub_per_all_t[t]) > 0:
                    #         mesh_group.create_dataset("sub_percent", [len(sub_per_all_t[t][r]), 8],
                    #                                   data=sub_per_all_t[t][r])

    # close file
    file.close()

    # save the file to the xml of the project
    if merge:
        type_hdf5 = "hdf5_mergedata"
    else:
        type_hdf5 = "hdf5_hydrodata"

    filename_prj = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(filename_prj):
        print('Error: No project saved. Please create a project first in the General tab.\n')
        return
    else:
        doc = ET.parse(filename_prj)
        root = doc.getroot()
        child = root.find(".//" + model_type)
        # if the xml attribute do not exist yet, xml name should be saved
        if child is None:
            here_element = ET.SubElement(root, model_type)
            hdf5file = ET.SubElement(here_element, type_hdf5)
            hdf5file.text = h5name
        else:
            # if we save all files even identical file, we need to save xml
            if not erase_idem:
                hdf5file = ET.SubElement(child, type_hdf5)
                hdf5file.text = h5name
            # if the xml attribute exist and we do not save all file, we should only save attribute if new
            else:
                child2s = root.findall(".//" + model_type + "/" + type_hdf5)
                if child2s is not None:
                    found_att_text = False
                    for i, c in enumerate(child2s):
                        if c.text == h5name:  # if same : remove/recreate at the end (for the last file create labels)
                            found_att_text = True
                            index_origin = i
                    if found_att_text:
                        # existing element
                        element = child2s[index_origin]
                        # remove existing
                        child.remove(element)
                        # add existing to the end
                        hdf5file = ET.SubElement(child, type_hdf5)
                        hdf5file.text = h5name
                    if not found_att_text:
                        hdf5file = ET.SubElement(child, type_hdf5)
                        hdf5file.text = h5name
                else:
                    hdf5file = ET.SubElement(child, type_hdf5)
                    hdf5file.text = h5name

        doc.write(filename_prj)

    return


def save_hdf5_sub(path_hdf5, path_prj, name_prj, sub_array, sub_description_system, ikle_sub=[], coord_p=[],
                  units=[], reach=[], name_hdf5='', model_type='SUBSTRATE', return_name=False):
    """
    This function creates an hdf5 with the substrate data. This hdf5 does not have the same form than the hdf5 file used
    to store hydrological or merge data. This hdf5 store the substrate data alone before it is merged with the
    hydrological info. The substrate info should be given in the cemagref code.

    :param path_hdf5: the path where the hdf5 file should be saved
    :param path_prj: the project path
    :param name_prj: the name of the project
    :param sub_array: List of data by columns (index in list correspond with header)
    :param sub_description_system: info of substrate
    :param sub_epsg_code : code EPSG
    :param ikle_sub: the connectivity table for the substrate (only if constsub = False)
    :param coord_p: the point of the grid of the substrate (only if constsub = False)
    :param name_hdf5: the name of the substrate h5 file (without the timestamp). If not given, a default name is used.
    :param constsub: If True the substrate is a constant value
    :param model_type: the attribute for the xml file (usually SUBSTRATE)
    :param return_name: If True this function return the name of the substrate hdf5 name
    """

    # to know if we have to save a new hdf5
    save_opt = preferences_GUI.load_fig_option(path_prj, name_prj)
    if save_opt['erase_id'] == 'True':  # xml is all in string
        erase_idem = True
    else:
        erase_idem = False
    save_xml = True

    if name_hdf5[-4:] == '.sub':
        name_hdf5 = name_hdf5[:-4]

    # POLYGON
    if sub_description_system["sub_mapping_method"] == "polygon" or sub_description_system["sub_mapping_method"] == "point" :
        # create hdf5 name
        if not erase_idem:
            if name_hdf5:
                h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.sub'
            else:
                h5name = 'Substrate_VAR_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.sub'
        # create hdf5 name if we erase identical files
        else:
            if name_hdf5:
                h5name = name_hdf5 + '.sub'
            else:
                h5name = 'Substrate_VAR.sub'
            if os.path.isfile(os.path.join(path_hdf5, h5name)):
                try:
                    os.remove(os.path.join(path_hdf5, h5name))
                except PermissionError:
                    print('Could not save hdf5 substrate file. It might be used by another program \n')
                    return
                save_xml = True

        # create a new hdf5
        fname = os.path.join(path_hdf5, h5name)
        file = h5py.File(fname, 'w')

        # create attributes
        file.attrs['software'] = 'HABBY'
        file.attrs['software_version'] = str(VERSION)
        file.attrs['path_projet'] = path_prj
        file.attrs['name_projet'] = name_prj
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version
        file.attrs['hdf5_type'] = "substrate"
        file.attrs['sub_mapping_method'] = sub_description_system["sub_mapping_method"]
        file.attrs['sub_classification_code'] = sub_description_system["sub_classification_code"]
        file.attrs['sub_classification_method'] = sub_description_system["sub_classification_method"]
        file.attrs['sub_epsg_code'] = sub_description_system["sub_epsg_code"]
        file.attrs['sub_filename_source'] = sub_description_system["sub_filename_source"]
        file.attrs['sub_default_values'] = sub_description_system["sub_default_values"]

        # save ikle, coordonate and data by timestep and reach
        data_2d = file.create_group('data_2d')
        for t in range(0, len(units) + 1):
            there = data_2d.create_group('unit_' + str(t))
            for r in range(0, len(reach) + 1):
                # REACH GROUP
                rhere = there.create_group('reach_' + str(r))

                # NODE GROUP (XY)
                node_group = rhere.create_group('node')
                node_group.create_dataset("xy", [len(coord_p), 2], data=coord_p) # data : coords (coord_p_sub / xy)

                # MESH GROUP (TIN, SUB)
                mesh_group = rhere.create_group('mesh')
                mesh_group.create_dataset("tin", [len(ikle_sub), len(ikle_sub[0])], data=ikle_sub)  # connectivity table (ikle / tin)
                if len(ikle_sub) == len(sub_array[0]):
                    mesh_group.create_dataset("sub", [len(sub_array[0]), len(sub_array)], data=list(zip(*sub_array)))
                else:
                    print('Error: Substrate data not recognized (1) \n')
        file.close()

    # CONSTANT
    if sub_description_system["sub_mapping_method"] == "constant":
        # create hdf5 name if we keep all the files (need a time stamp)
        if not erase_idem:
            if name_hdf5:
                h5name = name_hdf5 + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.sub'
            else:
                h5name = 'Substrate_CONST_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.sub'
        # create hdf5 name if we erase identical files
        else:
            if name_hdf5:
                h5name = name_hdf5 + '.sub'
            else:
                h5name = 'Substrate_CONST.sub'
            if os.path.isfile(os.path.join(path_hdf5, h5name)):
                try:
                    os.remove(os.path.join(path_hdf5, h5name))
                except PermissionError:
                    print("Could not save hdf5 substrate data. It might be used by another program \n")
                    return
                save_xml = True

        # create a new hdf5
        fname = os.path.join(path_hdf5, h5name)
        file = h5py.File(fname, 'w')

        # create attributes
        file.attrs['software'] = 'HABBY'
        file.attrs['software_version'] = str(VERSION)
        file.attrs['path_projet'] = path_prj
        file.attrs['name_projet'] = name_prj
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version
        file.attrs['hdf5_type'] = "substrate"
        file.attrs['sub_mapping_method'] = sub_description_system["sub_mapping_method"]
        file.attrs['sub_classification_code'] = sub_description_system["sub_classification_code"]
        file.attrs['sub_classification_method'] = sub_description_system["sub_classification_method"]
        file.attrs['sub_filename_source'] = sub_description_system["sub_filename_source"]

        # add the constant value of substrate
        file.create_dataset("sub", [1, len(sub_array)], data=sub_array)

        file.close()

    # save the file to the xml of the project
    filename_prj = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(filename_prj):
        print('Error: No project saved. Please create a project first in the General tab.\n')
        return
    else:
        if save_xml:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//" + model_type)
            if child is None:  # don't exist ==> create it
                stathab_element = ET.SubElement(root, model_type)
                hdf5file = ET.SubElement(stathab_element, "hdf5_substrate")
                hdf5file.text = h5name
            else:  # exist ==> deplace it to the end
                for app in child.findall(".//hdf5_substrate"):
                    if app.text == h5name:
                        child.remove(app)
                hdf5file = ET.SubElement(child, "hdf5_substrate")
                hdf5file.text = h5name
            doc.write(filename_prj)

    if return_name:
        return h5name
    else:
        return


def load_hdf5_hyd_and_merge(hdf5_name_hyd, path_hdf5, units_index="all", merge=False):
    """
    A function to load the 2D hydrological data contained in the hdf5 file in the form required by HABBY. If
    hdf5_name_hyd is an absolute path, the path_hdf5 is not used. If hdf5_name_hyd is a relative path, the path is
    composed of the path to the project (path_hdf5) composed with hdf5_name_hyd.

    :param hdf5_name_hyd: filename of the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :param merge: If merge is True. this is a merge file with substrate data added
    :return: the connectivity table, the coordinates of the point, the height data, the velocity data
             on the coordinates, also substrate if merge is True.

    """

    # correct all change to the hdf5 form in the documentation!
    ikle_all_t = []
    point_all = []
    inter_vel_all = []
    inter_height_all = []
    # substrate_all_pg = []
    # substrate_all_dom = []
    substrate_all = []
    failload = [[-99]], [[-99]], [[-99]], [[-99]]
    if merge:
        failload = [[-99]], [[-99]], [[-99]], [[-99]], [[-99]], [[-99]]

    file_hydro, bfailload = open_hdf5_(hdf5_name_hyd, path_hdf5, "read")
    if bfailload:
        return failload

    if merge:
        sub_description_system = dict()
        sub_description_system["sub_mapping_method"] = file_hydro.attrs['sub_mapping_method']
        sub_description_system["sub_classification_code"] = file_hydro.attrs['sub_classification_code']
        sub_description_system["sub_classification_method"] = file_hydro.attrs['sub_classification_method']
        sub_description_system["sub_filename_source"] = file_hydro.attrs['sub_filename_source']
        if sub_description_system["sub_mapping_method"] != "constant":
            sub_description_system["sub_epsg_code"] = file_hydro.attrs['sub_epsg_code']
            sub_description_system["sub_default_values"] = file_hydro.attrs['sub_default_values']


    if units_index == "all":
        # load the number of time steps
        try:
             nb_t = file_hydro["description_unit"].attrs["nb"]
             units_index = list(range(nb_t))
        except KeyError:
            print(
                'Error: the number of reaches is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload

    # load the number of reach
    try:
        nb_r = file_hydro["description_reach"].attrs["nb"]
    except KeyError:
        print(
            'Error: the number of reaches is missing from the hdf5 file. \n')
        file_hydro.close()
        return failload

    # load the hyd_filename_source
    try:
        hyd_filename_source = file_hydro.attrs['hyd_filename_source']
    except KeyError:
        print(
            'Error: the hyd_filename_source is missing from the hdf5 file. \n')
        file_hydro.close()
        return failload

    # data_2d
    basename1 = 'data_2d'

    # WHOLE PROFIL
    tin_whole_all = []
    xy_whole_all = []
    for r in range(0, nb_r):
        tin_path = basename1 + "/whole_profile/reach_" + str(r) + "/mesh/tin"
        xy_path = basename1 + "/whole_profile/reach_" + str(r) + "/node/xy"
        try:
            tin_dataset = file_hydro[tin_path]
            xy_dataset = file_hydro[xy_path]
        except KeyError:
            print('Error: the dataset for tin or xy (1) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        try:
            tin_whole = tin_dataset[:]
            xy_whole = xy_dataset[:]
        except IndexError:
            print('Error: the dataset for tin or xy (2) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        tin_whole_all.append(tin_whole)
        xy_whole_all.append(xy_whole)
    ikle_all_t.append(tin_whole_all)
    point_all.append(xy_whole_all)

    # UNITS
    inter_vel_all.append([])  # no data for the whole profile case
    inter_height_all.append([])
    if merge:
        # substrate_all_pg.append([])
        # substrate_all_dom.append([])
        substrate_all.append([])
    # for all unit
    for t in units_index:
        tin_all = []
        xy_all = []
        h_all = []
        v_all = []
        if merge:
            # pg_all = []
            # dom_all = []
            sub_all = []
        # for all reach
        for r in range(0, nb_r):
            tin_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/tin"
            if merge:
                # pg_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/sub_coarser"
                # dom_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/sub_dom"
                sub_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/sub"
            xy_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/node/xy"
            h_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/node/h"
            v_path = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/node/v"

            try:
                tin_dataset = file_hydro[tin_path]
                if merge:
                    # pg_dataset = file_hydro[pg_path]
                    # dom_dataset = file_hydro[dom_path]
                    sub_dataset = file_hydro[sub_path]
                xy_dataset = file_hydro[xy_path]
                h_dataset = file_hydro[h_path]
                v_dataset = file_hydro[v_path]

            except KeyError:
                print('Warning: the dataset for tin or xy (3) is missing from the hdf5 file for one time step. \n')
                file_hydro.close()
                return failload
            try:
                tin_data = tin_dataset[:]
                xy_data = xy_dataset[:]
                h_data = h_dataset[:].flatten()
                v_data = v_dataset[:].flatten()
                if merge:
                    # pg_data = pg_dataset[:].flatten()
                    # dom_data = dom_dataset[:].flatten()
                    sub_data = sub_dataset[:]
            except IndexError:
                print('Error: the dataset for tin or xy (4) is missing from the hdf5 file for one time step. \n')
                file_hydro.close()
                return failload
            tin_all.append(tin_data)
            xy_all.append(xy_data)
            h_all.append(h_data)
            v_all.append(v_data)
            if merge:
                # pg_all.append(pg_data)
                # dom_all.append(dom_data)
                sub_all.append(sub_data)
        ikle_all_t.append(tin_all)
        point_all.append(xy_all)
        inter_height_all.append(h_all)
        inter_vel_all.append(v_all)
        if merge:
            # substrate_all_pg.append(pg_all)
            # substrate_all_dom.append(dom_all)
            substrate_all.append(sub_all)
    file_hydro.close()

    if merge:
        return ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all, sub_description_system
    if not merge:
        return ikle_all_t, point_all, inter_vel_all, inter_height_all, hyd_filename_source


def load_hdf5_sub(hdf5_name_sub, path_hdf5):
    """
    A function to load the substrate data contained in the hdf5 file. It also manage
    the constant cases. If hdf5_name_sub is an absolute path, the path_prj is not used. If it is a relative path,
    the path is composed of the path to the 'hdf5' folder (path_prj/hab) composed with hdf5_name_sub. it manages constant and
    vairable (based on a grid) cases. The code should be of cemagref type and the data is given as coarser and dominant.
    :param hdf5_name_sub: path and file name to the hdf5 file (string)
    :param path_prj: the path to the hdf5 file
    """

    # correct all change to the hdf5 form in the doc!
    ikle_sub = []
    point_all_sub = []
    sub_array = []
    failload = [[-99]], [[-99]], [[-99]], [[-99]]

    file_sub, bfailload = open_hdf5_(hdf5_name_sub, path_hdf5, "read")
    if bfailload:
        return failload

    sub_description_system = dict()
    sub_description_system["sub_mapping_method"] = file_sub.attrs['sub_mapping_method']
    sub_description_system["sub_classification_code"] = file_sub.attrs['sub_classification_code']
    sub_description_system["sub_classification_method"] = file_sub.attrs['sub_classification_method']
    sub_description_system["sub_filename_source"] = file_sub.attrs['sub_filename_source']
    if sub_description_system["sub_mapping_method"] != "constant":
        sub_description_system["sub_epsg_code"] = file_sub.attrs['sub_epsg_code']
        sub_description_system["sub_default_values"] = file_sub.attrs['sub_default_values']

    if not sub_description_system["sub_mapping_method"] == "constant":
        # DATA 2D GROUP
        data_2d = file_sub['data_2d']
        for t in range(0, len(list(data_2d.keys()))):
            # UNIT GROUP
            unit_group = data_2d['unit_' + str(t)]
            for r in range(0, len(list(unit_group.keys()))):
                # REACH GROUP
                reach_group = unit_group['reach_' + str(r)]
                # NODE AND MESH GROUP
                node_group = reach_group['node']
                mesh_group = reach_group['mesh']
                # GET DATA FROM GROUPS
                point_all_sub.append(node_group["xy"][:])  # coords (coord_p_sub / xy)
                ikle_sub.append(mesh_group["tin"][:].tolist())  # connectivity table (ikle / tin)
                sub_array.append(mesh_group["sub"][:].tolist())
        ikle_sub = ikle_sub[0]
        point_all_sub = point_all_sub[0]
        sub_array = sub_array[0]

    if sub_description_system["sub_mapping_method"] == "constant":
        sub_array = file_sub["sub"][:].tolist()[0]

    file_sub.close()

    return ikle_sub, point_all_sub, sub_array, sub_description_system


def add_habitat_to_merge(hdf5_name, path_hdf5, vh_cell, area_all, spu_all, fish_name):
    """
    This function takes a merge file and add habitat data to it. The habitat data is given by cell. It also save the
    velocity and the water height by cell (and not by node)

    :param hdf5_name: the name of the merge file
    :param path_hdf5: the path to this file
    :param vh_cell: the habitat value by cell
    :param area_all: total wet area by reach
    :param spu_all: total SPU by reach
    :param fish_name: the name of the fish (with the stage in it)
    """
    file_hydro, bfailload = open_hdf5_(hdf5_name, path_hdf5, "write")
    if bfailload:
        return

    # load the number of time steps
    try:
        nb_t = int(file_hydro["description_unit"].attrs["nb"])
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name
              + ' an hydrological input? \n')
        return

    # load the number of reach
    try:
        nb_r = int(file_hydro["description_reach"].attrs["nb"])
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. \n')
        return

    # add name and stage of fish
    if len(vh_cell) != len(fish_name):
        print('Error: length of the list of fish name is not coherent')
        file_hydro.close()
        return

    # create group habitat
    if "habitat" in file_hydro:  # if exist take it
        habitat_group = file_hydro["habitat"]
    else:  # create it
        habitat_group = file_hydro.create_group("habitat")

    # for all units (timestep or discharge)
    fish_replaced = []
    for t in range(1, nb_t + 1):
        if 'unit_' + str(t - 1) in habitat_group:  # if exist take it
            unit_group = habitat_group['unit_' + str(t - 1)]
        else:  # create it
            unit_group = habitat_group.create_group('unit_' + str(t - 1))
        # for all reach
        for r in range(0, nb_r):
            if 'reach_' + str(r) in unit_group:  # if exist take it
                reach_group = unit_group['reach_' + str(r)]
            else:
                reach_group = unit_group.create_group('reach_' + str(r))
            # add reach attributes
            reach_group.attrs['AREA'] = str(area_all[t][0])
            # for all fish
            for s in range(0, len(fish_name)):
                if fish_name[s] in reach_group:  # if exist erase it
                    del reach_group[fish_name[s]]
                    fish_dataset = reach_group.create_dataset(fish_name[s], [len(vh_cell[s][t][r]), 1],
                                                              data=vh_cell[s][t][r], maxshape=None)
                    fish_replaced.append(fish_name[s])
                else:
                    fish_dataset = reach_group.create_dataset(fish_name[s], [len(vh_cell[s][t][r]), 1],
                                                              data=vh_cell[s][t][r], maxshape=None)
                # add fish attributes
                fish_dataset.attrs['WUA'] = str(spu_all[s][t][0])
                fish_dataset.attrs['HV'] = str(spu_all[s][t][0] / area_all[t][0])
    # info fish replacement
    if fish_replaced:
        fish_replaced = set(fish_replaced)
        fish_replaced = "; ".join(fish_replaced)
        print(f'Warning: fish(s) informations replaced in .hab file ({fish_replaced}).\n')
    file_hydro.attrs['hdf5_type'] = "habitat"
    file_hydro.close()
    time.sleep(1)  # as we need to insure different group of name


def load_hdf5_hab(hdf5_name, path_hdf5, fish_names, units_index):
    """
    A function to load the habitat data contained in the hdf5 file in the form required by HABBY. If
    hdf5_name is an absolute path, the path_hdf5 is not used. If hdf5_name is a relative path, the path is
    composed of the path to the project (path_hdf5) composed with hdf5_name.

    :param hdf5_name: filename of the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :return: the connectivity table, the coordinates of the point, the height data, the velocity data
             on the coordinates, also substrate if merge is True.

    """

    # correct all change to the hdf5 form in the documentation!
    ikle_all_t = []
    point_all = []
    inter_vel_all = []
    inter_height_all = []
    substrate_all_pg = []
    substrate_all_dom = []
    failload = [[-99]], [[-99]], [[-99]], [[-99]], [[-99]], [[-99]]

    file_hydro, bfailload = open_hdf5_(hdf5_name, path_hdf5, "read")

    # load the number of time steps
    try:
        nb_t = int(file_hydro["description_unit"].attrs["nb"])
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name
              + ' an hydrological input? \n')
        return

    # load the number of reach
    try:
        nb_r = int(file_hydro["description_reach"].attrs["nb"])
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. \n')
        return

    # basename
    basename1 = 'data_2d'

    # ikle whole profile #
    ikle_whole_all = []
    for r in range(0, nb_r):
        name_ik = basename1 + "/whole_profile/reach_" + str(r) + "/mesh/tin"
        try:
            gen_dataset = file_hydro[name_ik]
        except KeyError:
            print(
                'Error: the dataset for ikle (1) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        try:
            ikle_whole = gen_dataset[:]
        except IndexError:
            print('Error: the dataset for ikle (3) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        ikle_whole_all.append(ikle_whole)
    ikle_all_t.append(ikle_whole_all)

    # ikle by time step  #
    for t in units_index:
        ikle_whole_all = []
        for r in range(0, nb_r):

            name_ik = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/tin"
            try:
                gen_dataset = file_hydro[name_ik]
            except KeyError:
                print('Warning: the dataset for ikle (2) is missing from the hdf5 file for one time step. \n')
                file_hydro.close()
                return failload
            try:
                ikle_whole = gen_dataset[:]
            except IndexError:
                print('Error: the dataset for ikle (4) is missing from the hdf5 file for one time step. \n')
                file_hydro.close()
                return failload
            ikle_whole_all.append(ikle_whole)
        ikle_all_t.append(ikle_whole_all)

    # coordinate of the point for the  whole profile #
    point_whole_all = []
    for r in range(0, nb_r):
        name_pa = basename1 + "/whole_profile/reach_" + str(r) + "/node/xy"
        try:
            gen_dataset = file_hydro[name_pa]
        except KeyError:
            print(
                'Error: the dataset for coordinates of the points (1) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        try:
            point_whole = gen_dataset[:]
        except IndexError:
            print('Error: the dataset for coordinates of the points (3) is missing from the hdf5 file. \n')
            file_hydro.close()
            return failload
        point_whole_all.append(point_whole)
    point_all.append(point_whole_all)

    # coordinate of the point by time step #
    for t in units_index:
        point_whole_all = []
        for r in range(0, nb_r):
            name_pa = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/node/xy"
            try:
                gen_dataset = file_hydro[name_pa]
            except KeyError:
                print('Error: the dataset for coordinates of the points (2) is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            try:
                point_whole = gen_dataset[:]
            except IndexError:
                print('Error: the dataset for coordinates of the points (4) is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            point_whole_all.append(point_whole)
        point_all.append(point_whole_all)

    # load height and velocity data
    inter_vel_all.append([])  # no data for the whole profile case
    inter_height_all.append([])
    substrate_all_pg.append([])
    substrate_all_dom.append([])
    for t in units_index:
        h_all = []
        vel_all = []
        sub_pg_all = []
        sub_dom_all = []

        for r in range(0, nb_r):
            name_vel = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/node/v"
            name_he = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/node/h"
            name_pg = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/sub_coarser"
            name_dom = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/mesh/sub_dom"
            # velocity
            try:
                gen_dataset = file_hydro[name_vel]
            except KeyError:
                print('Error: the dataset for velocity is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            if len(gen_dataset[:].flatten()) == 0:
                print('Error: No velocity found in the hdf5 file. \n')
                file_hydro.close()
                return failload
            vel = gen_dataset[:].flatten()
            vel_all.append(vel)
            # height
            try:
                gen_dataset = file_hydro[name_he]
            except KeyError:
                print('Error: the dataset for water height is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            if len(gen_dataset[:].flatten()) == 0:
                print('Error: No height found in the hdf5 file. \n')
                file_hydro.close()
                return failload
            heigh = gen_dataset[:].flatten()
            h_all.append(heigh)
            # substrate
            try:
                gen_datasetpg = file_hydro[name_pg]
                gen_datasetdom = file_hydro[name_dom]
            except KeyError:
                print('Error: the dataset for substrate is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            try:
                subpg = gen_datasetpg[:].flatten()

            except IndexError:
                print('Error: the dataset for substrate is missing from the hdf5 file (2). \n')
                file_hydro.close()
                return failload
            try:
                subdom = gen_datasetdom[:].flatten()
            except IndexError:
                print('Error: the dataset for substrate is missing from the hdf5 file (3). \n')
                file_hydro.close()
                return failload
            sub_pg_all.append(subpg)
            sub_dom_all.append(subdom)
        inter_vel_all.append(vel_all)
        inter_height_all.append(h_all)
        substrate_all_dom.append(sub_dom_all)
        substrate_all_pg.append(sub_pg_all)

    # load fish habitat data
    habitat_group = file_hydro["habitat"]

    # create empty list
    HV_data_list_all_t = [[]]
    total_wetarea_all_t = [[]]

    # get vh for map
    # for all units selected (timestep or discharge)
    for t in units_index:
        unit_group = habitat_group['unit_' + str(t)]
        total_wetarea_all = []
        # for all reach
        for r in range(0, nb_r):
            reach_group = unit_group['reach_' + str(r)]
            # get reach attributes
            total_wetarea_all.append(float(reach_group.attrs['AREA']))
            HV_data_list = [[]]
            # for all fish
            for s in range(0, len(fish_names)):
                fish_dataset = reach_group[fish_names[s]]
                HV_data_list.append(np.array(fish_dataset).flatten())
            HV_data_list_all_t.append(HV_data_list)
        total_wetarea_all_t.append(total_wetarea_all)

    # get hv and wua
    total_HV_list = []
    total_WUA_list = []
    fish_unit_reach_marker = []

    # for all fish
    for s in range(0, len(fish_names)):
        total_WUA_list_f = [[]]
        total_HV_list_f = [[]]
        fish_unit_reach_marker_f = [[]]
        # for all timestep
        for t in units_index:
            # for all reach
            total_WUA_list_r = []
            total_HV_list_r = []
            fish_unit_reach_marker_r = []
            for r in range(0, nb_r):
                fish_dataset = habitat_group['unit_' + str(t)]['reach_' + str(r)][fish_names[s]]
                total_WUA_list_r.append(float(fish_dataset.attrs['WUA']))
                total_HV_list_r.append(float(fish_dataset.attrs['HV']))
                fish_unit_reach_marker_r.append('unit_' + str(t) + ' reach_' + str(r) + " " + fish_names[s])
            total_WUA_list_f.append(total_WUA_list_r)
            total_HV_list_f.append(total_HV_list_r)
            fish_unit_reach_marker_f.append(fish_unit_reach_marker_r)
        total_WUA_list.append(total_WUA_list_f)
        total_HV_list.append(total_HV_list_f)
        fish_unit_reach_marker.append(fish_unit_reach_marker_f)

    # stock data in dict
    fish_data_all_t = dict()
    fish_data_all_t["fish_names"] = fish_names
    fish_data_all_t["total_HV"] = total_HV_list
    fish_data_all_t["total_WUA"] = total_WUA_list
    fish_data_all_t["markersforHVandWUA"] = fish_unit_reach_marker
    fish_data_all_t["HV_data"] = HV_data_list_all_t

    # sub_description_system
    sub_description_system = dict()
    sub_description_system["sub_mapping_method"] = file_hydro.attrs['sub_mapping_method']
    sub_description_system["sub_classification_code"] = file_hydro.attrs['sub_classification_code']
    sub_description_system["sub_classification_method"] = file_hydro.attrs['sub_classification_method']
    sub_description_system["sub_epsg_code"] = file_hydro.attrs['sub_epsg_code']
    sub_description_system["sub_filename_source"] = file_hydro.attrs['sub_filename_source']
    sub_description_system["sub_default_values"] = file_hydro.attrs['sub_default_values']

    file_hydro.close()
    return ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom, fish_data_all_t, total_wetarea_all_t, sub_description_system


def load_unit_name(hdf5_name, path_hdf5=''):
    """
    This function looks for the name of the timesteps in hydrological or merge hdf5. If it find the name
    of the time steps, it returns them. If not, it return an empty list.

    :param hdf5_name: the name of the merge or hydrological hdf5 file
    :param path_hdf5: the path to the hdf5
    :return: the name of the time step if they exist. Otherwise, an empty list
    """
    failload = []

    file_hydro, bfailload = open_hdf5_(hdf5_name, path_hdf5, "read")
    if bfailload:
        return failload

    # get the name of the time steps
    try:
        unit_dataset = file_hydro["description_unit"]
    except KeyError:  # in this case it happens often, it is not really an error
        file_hydro.close()
        return []

    # unit_name
    unit_name = unit_dataset[:].tolist()
    # unit_nb
    unit_nb = unit_dataset.attrs["nb"]
    # unit_type
    unit_type = unit_dataset.attrs["type"]

    # bytes to string
    sim_name = []
    for i in range(0, unit_nb):
        sim_name.append(bytes(unit_name[i]).decode('utf-8').replace('\x00', ''))  # why empty byte?
    file_hydro.close()
    return sim_name


def get_unit_number(hdf5_name, path_hdf5):  # ? a changer si on utilise attributs
    """
       This function looks for the number of the timesteps/discharge in hydrological or merge hdf5.

       :param hdf5_name: the name of the merge or hydrological hdf5 file
       :param path_hdf5: the path to the hdf5
       :return: an int, the number of time step/discharge
       """

    failload = -99

    file_hydro, bfailload = open_hdf5_(hdf5_name, path_hdf5, "read")
    if bfailload:
        return failload

    # get timestep number
    try:
        nb_t = file_hydro["description_unit"].attrs["nb"]
    except KeyError:
        print(
            'Error: the number of reaches is missing from the hdf5 file. \n')
        file_hydro.close()
        return failload

    file_hydro.close()
    return nb_t


def load_sub_percent(hdf5_name_hyd, path_hdf5=''):
    """
    This function loads the substrate in percent form, if this info is present in the hdf5 file. It send a warning
    otherwise.

    :param hdf5_name_hyd: filename of the hdf5 file (string)
    :param path_hdf5: the path to the hdf5 file
    :return:
    """
    failload = [-99]
    sub_per_all_t = []

    file_hydro, bfailload = open_hdf5_(hdf5_name_hyd, path_hdf5, "read")
    if bfailload:
        return failload

    # load the number of time steps
    basename1 = 'data_2d'
    try:
        gen_dataset = file_hydro[basename1 + "/unit_name"]
    except KeyError:
        print('Error: the number of time step is missing from the hdf5 file. Is ' + hdf5_name_hyd
              + ' an hydrological input? \n')
        file_hydro.close()
        return failload
    try:
        nb_t = list(gen_dataset.values())[0]
    except IndexError:
        print('Error: Time step are not found')
        file_hydro.close()
        return failload
    nb_t = np.array(nb_t)
    nb_t = int(nb_t)

    # load the number of reach
    try:
        gen_dataset = file_hydro[basename1 + "/Nb_reach"]
    except KeyError:
        print(
            'Error: the number of time step is missing from the hdf5 file. \n')
        file_hydro.close()
        return failload
    nb_r = list(gen_dataset.values())[0]
    nb_r = np.array(nb_r)
    nb_r = int(nb_r)

    # load the data of substrate in percentage
    basename1 = 'data_2d'
    sub_per_all_t.append([])
    for t in range(0, nb_t):
        sub_per_all = []
        for r in range(0, nb_r):
            name_per = basename1 + "/unit_" + str(t) + "/reach_" + str(r) + "/sub_percent"
            try:
                gen_datasetpg = file_hydro[name_per]
            except KeyError:
                print('Error: the dataset for substrate in percentage form is missing from the hdf5 file. \n')
                file_hydro.close()
                return failload
            try:
                sub_per = list(gen_datasetpg.values())[0]
            except IndexError:
                print('Error: the dataset for substrate in precentage is missing from the hdf5 file (2). \n')
                file_hydro.close()
                return failload
            sub_per = np.array(sub_per).flatten()
            sub_per = np.reshape(sub_per, (int(len(sub_per) / 8), 8))
            sub_per_all.append(sub_per)
        sub_per_all_t.append(sub_per_all)
    file_hydro.close()
    return sub_per_all_t


def get_all_filename(dirname, ext):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    filenames = []
    for file in os.listdir(dirname):
        if file.endswith(ext):
            filenames.append(file)
    return filenames


def get_filename_by_type(type, path):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    type_and_extension = dict(hydraulic=".hyd",
                              substrate=".sub",
                              habitat=".hab")
    filenames = []
    for file in os.listdir(path):
        if file.endswith(type_and_extension[type]):
            filenames.append(file)
    return filenames


def get_hdf5_name(model_name, name_prj, path_prj):
    """
    This function get the name of the hdf5 file containg the hydrological data for an hydrological model of type
    model_name. If there is more than one hdf5 file, it choose the last one. The path is the path from the
    project folder. Hence, it is not the absolute path.

    :param model_name: the name of the hydrological model as written in the attribute of the xml project file
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :return: the name of the hdf5 file
    """
    if model_name == 'MERGE':
        model_name2 = 'SUBSTRATE'  # merge data is in the subtrate tag in the xml files
    else:
        model_name2 = model_name

    # open the xml project file
    filename_path_pro = os.path.join(path_prj, name_prj + '.xml')
    if os.path.isfile(filename_path_pro):
        doc = ET.parse(filename_path_pro)
        root = doc.getroot()

        # get the path to hdf5
        pathhdf5 = root.find(".//Path_Hdf5")
        if pathhdf5 is None:
            print('Error: the path to the hdf5 file is not found (1) \n')
            return
        if pathhdf5.text is None:
            print('Error: the path to the hdf5 file is not found (2) \n')
            return
        pathhdf5 = os.path.join(path_prj, pathhdf5.text)
        if not os.path.isdir(pathhdf5):
            print('Error: the path to the hdf5 file is not correct \n')
            return

        # get the hdf5 name
        child = root.find(".//" + model_name2)
        if child is not None:
            if model_name == 'MERGE' or model_name == 'LAMMI':
                child = root.findall(".//" + model_name2 + '/hdf5_mergedata')
            elif model_name == 'SUBSTRATE':
                child = root.findall(".//" + model_name2 + '/hdf5_substrate')
            else:
                child = root.findall(".//" + model_name + '/hdf5_hydrodata')
            if len(child) > 0:
                # get the newest files
                files = []
                for c in child:
                    if c.text is not None and os.path.isfile(os.path.join(pathhdf5, c.text)):
                        files.append(os.path.join(pathhdf5, c.text))
                if len(files) == 0:
                    return
                name_hdf5 = max(files, key=os.path.getmtime)
                if len(name_hdf5) > 3:
                    if model_name == 'MERGE':
                        extensionhdf5 = '.hab'  # merge data is in the subtrate tag in the xml files
                    else:
                        extensionhdf5 = '.hyd'
                    if name_hdf5[:-4] == extensionhdf5:
                        name_hdf5 = name_hdf5[:-4]
                return name_hdf5
            else:
                print('Warning: the hdf5 name for the model ' + model_name + ' was not found (1)')
                return 'default_name'
        else:
            # print('Warning: the data for the model ' + model_name + ' was not found (2)')
            return ''
    else:
        print('Error: no project found by load_hdf5')
        return ''


def get_initial_files(path_hdf5, hdf5_name):
    """
    This function looks into a merge file to find the hydraulic and subtrate file which
    were used to create this file.
    :param path_hdf5: the path to the hdf5 file
    :param hdf5_name: the name fo this hdf5 file
    :return: the name of the substrate and hydraulic file used to create the merge file
    """

    file, bfailload = open_hdf5_(hdf5_name, path_hdf5, "read")
    if bfailload:
        return '', ''

    # get the name
    try:
        sub_ini = file.attrs['sub_ini_name']
    except KeyError:
        sub_ini = ''
    try:
        hydro_ini = file.attrs['hydro_ini_name']
    except KeyError:
        hydro_ini = ''
    file.close()
    return sub_ini, hydro_ini


def get_fish_names_habitat(hdf5_name, path_hdf5):
    """
    This function looks for the name of fish.

    :param hdf5_name: the name of the merge or hydrological hdf5 file
    :param path_hdf5: the path to the hdf5
    :return: the name of the time step if they exist. Otherwise, an empty list
    """
    failload = []
    fish_names_list = []

    file_hydro, bfailload = open_hdf5_(hdf5_name, path_hdf5, "read")
    if bfailload:
        return failload

    try:
        # search in habitat group
        habitat_group = file_hydro["habitat"]
        first_unit_group = habitat_group["unit_0"]
        first_reach_group = first_unit_group["reach_0"]

        # get list of fish names
        fish_names_list = list(first_reach_group.keys())
    except:
        print("No fish habitat in this .hab file.")

    # close file
    file_hydro.close()
    return fish_names_list


def copy_files(names, paths, path_input):
    """
    This function copied the input files to the project file. The input files are usually contains in the input
    project file. It is ususally done on a second thread as it might be long.

    For the moment this function cannot send warning and error to the GUI. As input should have been cheked before
    by HABBY, this should not be a problem.

    :param names: the name of the files to be copied (list of string)
    :param paths: the path to these files (list of string)
    :param path_input: the path where to send the input (string)
    """

    if not os.path.isdir(path_input):
        print('Error: Folder not found to copy inputs \n')
        return

    if len(names) != len(paths):
        print('Error: the number of file to be copied is not equal to the number of paths')
        return

    for i in range(0, len(names)):
        if names[i] != 'unknown file':
            src = os.path.join(paths[i], names[i])
            # if the file is too big, the GUI is freezed
            if os.path.getsize(src) > 200 * 1024 * 1024:
                print('Warning: One input file was larger than 200MB and therefore was not copied to the project'
                      ' folder. It is necessary to copy this file manually to the input folder if one wants to use the '
                      'restart file or the log file to load this data auomatically again. \n')
            else:
                if os.path.isfile(src):
                    dst = os.path.join(path_input, names[i])
                    shutil.copy(src, dst)


def addition_hdf5(path1, hdf51, path2, hdf52, name_prj, path_prj, model_type, path_hdf5, merge=False, erase_id=True,
                  return_name=False, name_out=''):
    """
    This function merge two hdf5 together. The hdf5 files should be of hydrological or merge type and both grid should
    in the same coordinate system. It is not possible to have one merge file and one hydrological hdf5 file. They both
    should be of the same type. The two grid are added as two separeted river reach.

    :param path1: the path to the first hydrological hdf5
    :param hdf51: the name of the first hdf5 file
    :param path2: the path to the second hdf5
    :param hdf52: the name of the second hdf5
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: the type of model (used to save the new file name into the project xml file)
    :param path_hdf5: the path where to save the hdf5 (ususally path_prj, but not always)
    :param merge: If True, this is a merge hdf5 file and not only hydraulic data. Boolean.
    :param erase_id: If true and if a similar hdf5 exist, il will be erased
    :param reteurn_name: If True, it return the name of the created hdf5
    :param name_out: name of the new hdf5 (optional)

    """
    substrate_all_dom1 = []
    substrate_all_dom2 = []
    substrate_all_pg1 = []
    substrate_all_pg2 = []

    # load first hdf5
    if merge:
        [ikle1, point1, inter_vel1, inter_height1, substrate_all_pg1, substrate_all_dom1] \
            = load_hdf5_hyd_and_merge(hdf51, path1, merge=merge)
    else:
        [ikle1, point1, inter_vel1, inter_height1] = load_hdf5_hyd_and_merge(hdf51, path1, merge=merge)

    # load second hdf5
    if merge:
        [ikle2, point2, inter_vel2, inter_height2, substrate_all_pg2, substrate_all_dom2] \
            = load_hdf5_hyd_and_merge(hdf52, path2, merge=merge)
    else:
        [ikle2, point2, inter_vel2, inter_height2] = load_hdf5_hyd_and_merge(hdf52, path2, merge=merge)

    if len(ikle1) == 0 or len(ikle2) == 0:
        return
    if ikle1 == [[-99]] or ikle2 == [[-99]]:
        print('Error: Could not load the chosen hdf5. \n')
        return

    # check time step and load time step name
    if len(ikle1) != len(ikle2):
        print('Error: the number of time step between the two hdf5 is not coherent. \n')
        return
    sim_name = load_unit_name(hdf51, path1)

    # add the second grid as new reach
    # reach grids can intersect in HABBY
    for t in range(0, len(ikle1)):
        ikle1[t].extend(ikle2[t])
        point1[t].extend(point2[t])
        inter_vel1[t].extend(inter_vel2[t])
        inter_height1[t].extend(inter_height2[t])
        if merge:
            substrate_all_pg1[t].extend(substrate_all_pg2[t])
            substrate_all_dom1[t].extend(substrate_all_dom2[t])

    # save the new data

    if merge:
        new_hdf5_name = 'ADDMERGE' + hdf51[5:-3] + '_AND' + hdf52[5:-3]
        if name_out:
            new_hdf5_name = name_out
        save_hdf5_hyd_and_merge(new_hdf5_name, name_prj, path_prj, model_type, 2, path_hdf5, ikle1, point1, [],
                                inter_vel1, inter_height1, merge=merge, sub_pg_all_t=substrate_all_pg1,
                                sub_dom_all_t=substrate_all_dom1, sim_name=sim_name, save_option=erase_id,
                                hdf5_type="merge")
    else:
        new_hdf5_name = 'ADDHYDRO' + hdf51[5:-3] + '_AND' + hdf52[5:-3]
        if name_out:
            new_hdf5_name = name_out
        save_hdf5_hyd_and_merge(new_hdf5_name, name_prj, path_prj, model_type, 2, path_hdf5, ikle1, point1, [],
                                inter_vel1, inter_height1, merge=merge, sim_name=sim_name, save_option=erase_id,
                                hdf5_type="hydraulic")

    # return name if necessary (often used if more than two hdf5 are added at the same time)
    if return_name:
        return new_hdf5_name


def create_shapfile_hydro(name_hdf5, path_hdf5, path_shp, merge=True, erase_id=True):
    """
    This function creates a shapefile with the hydraulic and shapefile data. This can be used to check how the data
    was merged. The shapefile will have the same name than the hdf5 file. There are some similairites between this
    function and the function in calcul_hab_mod.py (save_hab_shape). It might be useful to change both function if
    corrections must be done.

    :param name_hdf5: the name of the hdf5 file (with .hab extension)
    :param path_hdf5: the path to the hdf5 file
    :param path_shp: The path where the shapefile will be created
    :param erase_id: Should we kept all shapefile or erase old files if they comes from the same model
    :param merge: If ture, the hdf5 file is a merge file with substrate data (usually True)
    """

    if not merge:
        [ikle_all_t, point_all_t, vel_nodes, height_node, hyd_filename_source] = load_hdf5_hyd_and_merge(name_hdf5,
                                                                                               path_hdf5,
                                                                                               merge=merge)
    if merge:
        [ikle_all_t, point_all_t, vel_nodes, height_node, sub_array, sub_description_system] = load_hdf5_hyd_and_merge(name_hdf5,
                                                                                               path_hdf5,
                                                                                               merge=merge)

    #sub_dom_data
    if ikle_all_t == [[-99]] or len(ikle_all_t) < 1:
        return
    sim_name = load_unit_name(name_hdf5, path_hdf5)


    # we needs the data by cells and not nodes
    # optmization possibility: save the data in the hdf5 and re-use it for the habitat calculation
    vel_data = [[]]
    height_data = [[]]
    for t in range(1, len(ikle_all_t)):  # ikle_all_t[0] has no velocity
        ikle_all = ikle_all_t[t]
        vel_all = vel_nodes[t]
        he_all = height_node[t]
        vel_data_here = []
        height_data_here = []
        for r in range(0, len(ikle_all)):
            ikle = ikle_all[r]
            try:
                v = vel_all[r]
                h = he_all[r]
            except IndexError:
                print('Velocity data was missing for one time step. Could not create a shapefile to check data. \n')
                return
            # get data by cells
            try:
                v1 = v[ikle[:, 0]]
                v2 = v[ikle[:, 1]]
                v3 = v[ikle[:, 2]]
                v_cell = 1.0 / 3.0 * (v1 + v2 + v3)
                vel_data_here.append(v_cell)

                h1 = h[ikle[:, 0]]
                h2 = h[ikle[:, 1]]
                h3 = h[ikle[:, 2]]
                h_cell = 1.0 / 3.0 * (h1 + h2 + h3)
                height_data_here.append(h_cell)
            except IndexError:
                vel_data_here.append([])
                vel_data_here.append([])
        vel_data.append(vel_data_here)
        height_data.append(height_data_here)

    # we do not print the first time step with the whole profile

    for t in range(1, len(ikle_all_t)):
        ikle_here = ikle_all_t[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            w = shapefile.Writer(shapefile.POLYGON)
            w.autoBalance = 1

            # get the triangle
            nb_reach = len(ikle_all_t[t])
            for r in range(0, nb_reach):
                ikle_r = ikle_all_t[t][r]
                point_here = point_all_t[t][r]
                for i in range(0, len(ikle_r)):
                    p1 = list(point_here[ikle_r[i][0]])
                    p2 = list(point_here[ikle_r[i][1]])
                    p3 = list(point_here[ikle_r[i][2]])
                    w.poly(parts=[[p1, p2, p3, p1]])  # the double [[]] is important or it bugs, but why?

            if t > 0:
                # attribute
                w.field('velocity', 'F', 50, 8)
                w.field('water heig', 'F', 50, 8)
                w.field('conveyance', 'F', 50, 8)
                if merge:
                    if sub_description_system["sub_classification_method"] == 'coarser-dominant':
                        w.field('coarser', 'N', 10, 0)
                        w.field('dom', 'N', 10, 0)
                    if sub_description_system["sub_classification_method"] == 'percentage':
                        if sub_description_system["sub_classification_code"] == "Cemagref":
                            sub_class_number = 8
                        if sub_description_system["sub_classification_code"] == "Sandre":
                            sub_class_number = 12
                        for i in range(sub_class_number):
                            w.field('S' + str(i + 1), 'N', 10, 0)

                # fill attribute
                for r in range(0, nb_reach):
                    vel = vel_data[t][r]
                    height = height_data[t][r]
                    # sub_pg = sub_pg_data[t][r]
                    # sub_dom = sub_dom_data[t][r]
                    sub = sub_array[t][r]
                    ikle_r = ikle_all_t[t][r]
                    for i in range(0, len(ikle_r)):
                        data_here = ()
                        if merge:
                            #data_here += vel[i], height[i], vel[i] * height[i], sub_pg[i], sub_dom[i]
                            data_sub_to_attribute = [item for item in sub[i]]
                            data_here += (vel[i], height[i], vel[i] * height[i], *data_sub_to_attribute)
                            aa = 1
                        else:
                            data_here += vel[i], height[i], vel[i] * height[i]
                        # the * pass tuple to function argument
                        w.record(*data_here)

            w.autoBalance = 1

            # save
            name_base = name_hdf5[:-3]
            if not erase_id:
                if not sim_name:
                    name1 = name_base + '_t_' + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
                else:
                    name1 = name_base + '_t_' + sim_name[t - 1] + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
            else:
                if not sim_name:
                    name1 = name_base + '_t_' + str(t) + '.shp'
                else:
                    name1 = name_base + '_t_' + sim_name[t - 1] + '.shp'
                if os.path.isfile(os.path.join(path_shp, name1)):
                    try:
                        os.remove(os.path.join(path_shp, name1))
                    except PermissionError:
                        print('Error: The shapefile is currently open in an other program. Could not be re-written \n')
                        return

            w.save(os.path.join(path_shp, name1))
