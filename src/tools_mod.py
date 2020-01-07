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
from shutil import rmtree
from shutil import copy as sh_copy
import sys
import urllib
from copy import deepcopy
from glob import glob
from locale import localeconv
from time import sleep
import shutil
import numpy as np
from PyQt5.QtCore import QTranslator, QObject, pyqtSignal, QEvent, QThread, QCoreApplication as qt_tr
from PyQt5.QtWidgets import QApplication, QGroupBox, QFrame
import multiprocessing

from src.project_manag_mod import load_project_preferences

GRAVITY = 9.80665  # [m/s2] standard acceleration due to gravity

""" HYDRAULIC TOOLS """


# mesh
def c_mesh_mean_from_node_values(tin, all_nodes_values):
    """
    Compute mesh values from point values for one unit.
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param all_nodes_values: numpy.ndarray representing all the node values. Shape : (N_points, )
    :return: mesh_values: numpy.ndarray representing all the mesh values. Shape : (N_mesh, ).
    """
    mesh_values = np.mean([all_nodes_values[tin[:, 0]],
                           all_nodes_values[tin[:, 1]],
                           all_nodes_values[tin[:, 2]]], axis=0)
    return mesh_values


def c_mesh_max_slope_bottom(tin, xy, z):
    """
    Compute mesh values from point values for one unit.
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param xy: numpy.ndarray representing all the coordinates points. Shape : (N_points, )
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :return: max_slope_bottom: numpy.ndarray representing all the max_slope_bottom mesh values. Shape : (N_mesh, ).
    """
    xy1 = xy[tin[:, 0]]
    z1 = z[tin[:, 0]]
    xy2 = xy[tin[:, 1]]
    z2 = z[tin[:, 1]]
    xy3 = xy[tin[:, 2]]
    z3 = z[tin[:, 2]]

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

    return max_slope_bottom


def c_mesh_max_slope_energy(tin, xy, z, h, v):
    """
    Compute mesh values from point values for one unit.
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param xy: numpy.ndarray representing all the coordinates points. Shape : (N_points, )
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: max_slope_energy: numpy.ndarray representing all the max_slope_energy mesh values. Shape : (N_mesh, ).
    """
    xy1 = xy[tin[:, 0]]
    z1 = z[tin[:, 0]]
    h1 = h[tin[:, 0]]
    v1 = v[tin[:, 0]]
    xy2 = xy[tin[:, 1]]
    z2 = z[tin[:, 1]]
    h2 = h[tin[:, 1]]
    v2 = v[tin[:, 1]]
    xy3 = xy[tin[:, 2]]
    z3 = z[tin[:, 2]]
    h3 = h[tin[:, 2]]
    v3 = v[tin[:, 2]]

    w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
    zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * GRAVITY), z2 + h2 + v2 ** 2 / (2 * GRAVITY), z3 + h3 + v3 ** 2 / (2 * GRAVITY)
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

    return max_slope_energy


def c_mesh_shear_stress(tin, xy, z, h, v):
    """
    Compute shear_stress mesh values from point values for one unit.
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param xy: numpy.ndarray representing all the coordinates points. Shape : (N_points, )
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: shear_stress: numpy.ndarray representing all the shear_stress mesh values. Shape : (N_mesh, ).
    """
    ro = 999.7  # [kg/m3]  density of water 10Â°C /1 atm

    xy1 = xy[tin[:, 0]]
    z1 = z[tin[:, 0]]
    h1 = h[tin[:, 0]]
    v1 = v[tin[:, 0]]
    xy2 = xy[tin[:, 1]]
    z2 = z[tin[:, 1]]
    h2 = h[tin[:, 1]]
    v2 = v[tin[:, 1]]
    xy3 = xy[tin[:, 2]]
    z3 = z[tin[:, 2]]
    h3 = h[tin[:, 2]]
    v3 = v[tin[:, 2]]

    w = (xy2[:, 0] - xy1[:, 0]) * (xy3[:, 1] - xy1[:, 1]) - (xy2[:, 1] - xy1[:, 1]) * (xy3[:, 0] - xy1[:, 0])
    zz1, zz2, zz3 = z1 + h1 + v1 ** 2 / (2 * GRAVITY), z2 + h2 + v2 ** 2 / (2 * GRAVITY), z3 + h3 + v3 ** 2 / (2 * GRAVITY)
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

    return shear_stress


def c_mesh_froude(tin, h, v):
    """
    Compute mesh froude (mean froude of 3 points)
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: mesh_froude: numpy.ndarray representing all the froude mesh values. Shape : (N_mesh, ).
    """

    # compute froude at nodes
    node_froude = c_node_froude(h, v)

    # compute mesh mean
    mesh_froude = c_mesh_mean_from_node_values(tin, node_froude)

    return mesh_froude


def c_mesh_hydraulic_head(tin, z, h, v):
    """
    Compute hydraulic_head mesh values from point values for one unit.
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param xy: numpy.ndarray representing all the coordinates points. Shape : (N_points, )
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: shear_stress: numpy.ndarray representing all the shear_stress mesh values. Shape : (N_mesh, ).
    """

    # compute hydraulic_head at nodes
    node_hydraulic_head = c_node_hydraulic_head(z, h, v)

    # compute mesh mean
    mesh_hydraulic_head = c_mesh_mean_from_node_values(tin, node_hydraulic_head)

    return mesh_hydraulic_head


def c_mesh_conveyance(tin, h, v):
    """
    Compute mesh froude (mean froude of 3 points)
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: mesh_froude: numpy.ndarray representing all the froude mesh values. Shape : (N_mesh, ).
    """

    # compute hydraulic_head at nodes
    node_hydraulic_head = c_node_conveyance(h, v)

    # compute mesh mean
    mesh_conveyance = c_mesh_mean_from_node_values(tin, node_hydraulic_head)

    return mesh_conveyance


def c_mesh_water_level(tin, z, h):
    """
    Compute mesh froude (mean froude of 3 points)
    :param tin: numpy.ndarray representing the triangular mesh. Shape : (N_mesh, 3_points).
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :return: mesh_water_level: numpy.ndarray representing all the water_level mesh values. Shape : (N_mesh, ).
    """

    # node_water_level
    node_water_level = c_node_water_level(z, h)

    # compute mesh mean
    mesh_water_level = c_mesh_mean_from_node_values(tin, node_water_level)

    return mesh_water_level


def c_mesh_area(tin, xy):
    # get points coord
    pa = xy[tin[:, 0]]
    pb = xy[tin[:, 1]]
    pc = xy[tin[:, 2]]

    # compute area
    area = 0.5 * abs((pb[:, 0] - pa[:, 0]) * (pc[:, 1] - pa[:, 1]) - (pc[:, 0] - pa[:, 0]) * (
            pb[:, 1] - pa[:, 1]))

    return area


# node
def c_node_froude(h, v):
    """
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: node_froude: numpy.ndarray representing all the froude nodes values. Shape : (N_points, ).
    """
    # compute froude
    null_values = h == 0
    h[null_values] = 100000
    node_froude = v / np.sqrt(GRAVITY * h)
    h[null_values] = 0
    node_froude[null_values] = 0

    return node_froude


def c_node_hydraulic_head(z, h, v):
    """
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: node_hydraulic_head: numpy.ndarray representing all the hydraulic_head nodes values. Shape : (N_points, ).
    """
    # compute hydraulic_head
    #node_hydraulic_head = (z + h) + ((v ** 2) / (2 * GRAVITY))
    node_hydraulic_head = h + ((v ** 2) / (2 * GRAVITY))
    # TODO: add z for 3d pvd

    return node_hydraulic_head


def c_node_conveyance(h, v):
    """
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :param v: numpy.ndarray representing all the v values. Shape : (N_points, ).
    :return: node_conveyance: numpy.ndarray representing all the conveyance nodes values. Shape : (N_points, ).
    """
    node_conveyance = h * v

    return node_conveyance


def c_node_water_level(z, h):
    """
    :param z: numpy.ndarray representing all the z values. Shape : (N_points, ).
    :param h: numpy.ndarray representing all the h values. Shape : (N_points, ).
    :return: node_conveyance: numpy.ndarray representing all the water_level nodes values. Shape : (N_points, ).
    """
    water_level = z + h

    return water_level


""" INTERPOLATION TOOLS """


def export_empty_text_from_hdf5(unit_type, unit_min, unit_max, filename, path_prj):
    # get unit type
    start = unit_type.find('[')
    end = unit_type.find(']')
    unit_type = unit_type[start + 1:end]

    # headers
    headers = "unit[" + unit_type + "]"

    # lines
    linetext1 = str(unit_min)
    linetext2 = str(unit_max)

    text = headers + "\n" + linetext1 + "\n" + linetext2

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_empty_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            # change decimal point
            if localeconv()['decimal_point'] == ",":
                text = text.replace('.', ',')
            f.write(text)
        return True
    except:
        return False


def read_chronicle_from_text_file(chronicle_filepath):
    # read discharge chronicle
    with open(chronicle_filepath, 'rt') as f:
        dataraw = f.read()
    # headers
    headers = dataraw.split("\n")[0].split("\t")
    date_index = None
    units_index = None
    for i in range(len(headers)):
        if 'DATE' in headers[i].upper():  # Date
            date_index = i
            date_type = headers[date_index][headers[date_index].find('[') + 1:headers[date_index].find(']')]
        if 'UNIT[' in headers[i].upper() and ']' in headers[i]:  # Q
            units_index = i
            unit_type = headers[units_index][headers[units_index].find('[') + 1:headers[units_index].find(']')]

    if units_index is None:
        return False, "Error : Interpolation not done. 'unit[' header not found in " + chronicle_filepath + "."

    # create dict
    if type(date_index) == int and type(units_index) == int:
        chronicle_from_file = dict(date=[], units=[])
        types_from_file = dict(date=date_type, units=unit_type)
    if type(date_index) == int and type(units_index) != int:
        chronicle_from_file = dict(date=[])
        types_from_file = dict(date=date_type)
    if type(date_index) != int and type(units_index) == int:
        chronicle_from_file = dict(units=[])
        types_from_file = dict(units=unit_type)

    data_row_list = dataraw.split("\n")[1:]
    for line in data_row_list:
        if line == "":
            #print("empty line")
            pass
        else:
            for index in range(2):
                # units presence (time or discharge)
                if index == units_index:
                    data = line.split("\t")[index]
                    if not data:
                        chronicle_from_file["units"].append(None)
                    if data:
                        data = data.replace(",", ".")  # decimal_point_security
                        chronicle_from_file["units"].append(float(data))
                # date presence
                if index == date_index:
                    chronicle_from_file["date"].append(line.split("\t")[index])
    chronicle_from_file["units"] = np.array(chronicle_from_file["units"])
    if type(date_index) == int:
        #chronicle_from_file["date"] = np.array([dt.strptime(date, date_type).date() for date in chronicle_from_file["date"]], dtype='datetime64')
        chronicle_from_file["date"] = np.array(chronicle_from_file["date"])
    return chronicle_from_file, types_from_file


def check_matching_units(data_description, types):
    # get units types
    unit_hdf5_type = data_description["hyd_unit_type"][
                     data_description["hyd_unit_type"].find('[') + 1:data_description["hyd_unit_type"].find(']')]
    for key in types.keys():
        if "units" in key:
            unit_chronicle_type = types[key]

    # check matching units type ok
    if unit_hdf5_type == unit_chronicle_type:
        #print("units type match")
        return True, ""
    if unit_hdf5_type != unit_chronicle_type:
        #print("units type doesn't match")
        return False, " Desired units type is different from available units type : " + unit_chronicle_type + " != " + unit_hdf5_type


def compute_interpolation(data_description, fish_names, reach_num, chronicle, types, rounddata=True):
    # check if date
    if "date" in types.keys():
        date_presence = True
    else:
        date_presence = False

    # get hdf5 model
    inter_data_model = dict()
    inter_data_model["unit"] = data_description["hyd_unit_list"][reach_num]
    wet_area = np.array(list(map(float, data_description["total_wet_area"][reach_num])))
    # map by fish
    for fish_index, fish_name in enumerate(fish_names):
        spu = np.array(list(map(float, data_description["total_WUA_area"][fish_name][reach_num])))
        inter_data_model["hv_" + fish_name] = spu / wet_area
        inter_data_model["spu_" + fish_name] = spu

    # copy chonicle to interpolated
    chronicle_interpolated = deepcopy(chronicle)
    # Add new column to chronicle_interpolated
    for fish_name in fish_names:
        chronicle_interpolated["hv_" + fish_name] = []
    for fish_name in fish_names:
        chronicle_interpolated["spu_" + fish_name] = []
    # copy for round for table gui
    chronicle_gui = deepcopy(chronicle_interpolated)
    # get min max
    q_min = min(inter_data_model["unit"])
    q_max = max(inter_data_model["unit"])

    # interpolation
    for fish_name in fish_names:
        for index_to_est, q_value_to_est in enumerate(chronicle_interpolated["units"]):
            if q_value_to_est != None:
                if q_value_to_est < q_min or q_value_to_est > q_max:
                    chronicle_interpolated["hv_" + fish_name].append(None)
                    chronicle_gui["hv_" + fish_name].append("")
                    chronicle_interpolated["spu_" + fish_name].append(None)
                    chronicle_gui["spu_" + fish_name].append("")
                else:
                    data_interp_hv = np.interp(q_value_to_est,
                                               inter_data_model["unit"],
                                               inter_data_model["hv_" + fish_name])
                    chronicle_interpolated["hv_" + fish_name].append(data_interp_hv)
                    chronicle_gui["hv_" + fish_name].append("{0:.2f}".format(data_interp_hv))
                    data_interp_spu = np.interp(q_value_to_est,
                                                inter_data_model["unit"],
                                                inter_data_model["spu_" + fish_name])
                    chronicle_interpolated["spu_" + fish_name].append(data_interp_spu)
                    chronicle_gui["spu_" + fish_name].append("{0:.0f}".format(data_interp_spu))
            if q_value_to_est == None:
                chronicle_interpolated["hv_" + fish_name].append(None)
                chronicle_gui["hv_" + fish_name].append("")
                chronicle_interpolated["spu_" + fish_name].append(None)
                chronicle_gui["spu_" + fish_name].append("")

    # round for GUI
    if rounddata:
        if not date_presence:
            horiz_headers = list(chronicle_gui.keys())[1:]
            vertical_headers = list(map(str, chronicle_gui["units"]))
            del chronicle_gui["units"]
            data_to_table = list(zip(*chronicle_gui.values()))
        if date_presence:
            horiz_headers = list(chronicle_gui.keys())[1:]
            vertical_headers = list(map(str, chronicle_gui["date"]))
            del chronicle_gui["date"]
            chronicle_gui["units"] = list(map(str, chronicle_gui["units"]))
            data_to_table = list(zip(*chronicle_gui.values()))
    # not round to export text and plot
    if not rounddata:
        if not date_presence:
            horiz_headers = list(chronicle_interpolated.keys())[1:]
            vertical_headers = list(map(str, chronicle_interpolated["units"]))
            data_to_table = chronicle_interpolated
        if date_presence:
            horiz_headers = list(chronicle_interpolated.keys())[1:]
            vertical_headers = list(map(str, chronicle_interpolated["date"]))
            del chronicle_interpolated["date"]
            chronicle_interpolated["units"] = list(map(str, chronicle_interpolated["units"]))
            data_to_table = chronicle_interpolated
    return data_to_table, horiz_headers, vertical_headers


def export_text_interpolatevalues(data_to_table, horiz_headers, vertical_headers, data_description, types, project_preferences):
    filename = data_description["hab_filename"]
    path_prj = data_description["path_project"]
    unit_type = types["units"]

    fish_names = list(horiz_headers)

    # prep data
    for fish_num, fish_name in enumerate(fish_names):
        if "hv_" in fish_name:
            fish_names[fish_num] = fish_name.replace("hv_", "")
        if "spu_" in fish_name:
            fish_names[fish_num] = fish_name.replace("spu_", "")

    # header 1
    if project_preferences['language'] == 0:
        if len(types.keys()) > 1:  # date
            date_type = types["date"]
            header = 'reach\tdate\tunit'
        else:
            header = 'reach\tunit'
    else:
        if len(types.keys()) > 1:  # date
            date_type = types["date"]
            header = 'troncon\tdate\tunit'
        else:
            header = 'troncon\tunit'
    if project_preferences['language'] == 0:
        header += "".join(['\tHV' + str(i) for i in range(int(len(fish_names) / 2))])
        header += "".join(['\tWUA' + str(i) for i in range(int(len(fish_names) / 2))])
    else:
        header += "".join(['\tVH' + str(i) for i in range(int(len(fish_names) / 2))])
        header += "".join(['\tSPU' + str(i) for i in range(int(len(fish_names) / 2))])
    header += '\n'
    # header 2
    if len(types.keys()) > 1:  # date
        header += '[]\t[' + date_type + ']\t[' + unit_type + ']'
    else:
        header += '[]\t[' + unit_type + ']'
    header += "".join(['\t[]' for _ in range(int(len(fish_names) / 2))])
    header += "".join(['\t[m2]' for _ in range(int(len(fish_names) / 2))])
    header += '\n'
    # header 3
    if len(types.keys()) > 1:  # date
        header += 'all\tall\tall'
    else:
        header += 'all\tall'
    for fish_name in fish_names:
        if "units" in fish_name:
            pass
        else:
            header += '\t' + fish_name.replace(' ', '_')
    # lines
    linetext = ""
    # for each line
    for row_index in range(len(vertical_headers)):
        # print("line", line)
        if len(types.keys()) > 1:  # date
            linetext += "0" + "\t" + str(vertical_headers[row_index]) + "\t"
        else:
            linetext += "0" + "\t" + str(vertical_headers[row_index]) + "\t"
        # for each column
        for column_name in horiz_headers:
            data_hv = data_to_table[column_name][row_index]
            if not data_hv:
                linetext += "None" + "\t"
            if data_hv:
                # change decimal point
                if localeconv()['decimal_point'] == ",":
                    data_hv = data_hv.replace('.', ',')
                linetext += str(data_hv) + "\t"
        # new line
        linetext += "\n"
    text = header + "\n" + linetext

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_interpolate_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            f.write(text)
            return True
    except:
        return False


""" OTHERS TOOLS """


def create_plot_string_dict(name_hdf5, reach_name, unit_name, unit_type, variable, variable_unit, tr, variable_info=""):
    # plot_string_dict
    plot_string_dict = dict(reach_name=reach_name,
                            unit_name=unit_name,
                            title=variable + ' - ' + reach_name + ' - ' + unit_name + " [" + unit_type + "]",
                            variable_title="variable : " + variable + ' [' + variable_unit + ']' + " " + variable_info,
                            reach_title=tr('reach') + " : " + reach_name,
                            unit_title=tr('unit') + " : " + unit_name + " [" + unit_type + "]",
                            filename=os.path.splitext(name_hdf5)[0] + "_" + variable.replace(" ", "_") + "_" + reach_name + '_' + unit_name
                            )
    return plot_string_dict


def copy_shapefiles(input_shapefile_abspath, hdf5_name, dest_folder_path):
    """
    get all file with same prefix of input_shapefile_abspath and copy them to dest_folder_path.
    """
    # create folder with hdf5 name in input project folder
    input_hdf5name_folder_path = os.path.join(dest_folder_path, os.path.splitext(hdf5_name)[0])
    if os.path.exists(input_hdf5name_folder_path):
        try:
            rmtree(input_hdf5name_folder_path)
            os.mkdir(input_hdf5name_folder_path)
        except PermissionError:
            print("Error: Hydraulic input file can be copied to input project folder"
                  " as it is open in another program.")
            try:
                rmtree(input_hdf5name_folder_path)
                os.mkdir(input_hdf5name_folder_path)
            except PermissionError:
                print("Error: Can't create folder in input project folder.")
                return
    else:
        os.mkdir(input_hdf5name_folder_path)

    # copy input file to input files folder with suffix triangulated
    all_input_files_abspath_list = glob(input_shapefile_abspath[:-4] + "*")
    all_input_files_files_list = [os.path.basename(file_path) for file_path in all_input_files_abspath_list]
    for i in range(len(all_input_files_files_list)):
        sh_copy(all_input_files_abspath_list[i], os.path.join(input_hdf5name_folder_path, all_input_files_files_list[i]))


def copy_hydrau_input_files(input_file_abspath, hdf5_name, dest_folder_path):
    """
    copy input hydraulic files with indexHYDRAU.txt to input project folder in a folder as input
    (if severeral hydraulic with indexHYDRAU.txt, it will not be erased).
    """
    # create folder with hdf5 name in input project folder
    input_hdf5name_folder_path = os.path.join(dest_folder_path, os.path.splitext(hdf5_name)[0])
    if os.path.exists(input_hdf5name_folder_path):
        try:
            rmtree(input_hdf5name_folder_path)
            os.mkdir(input_hdf5name_folder_path)
        except PermissionError:
            print("Error: Hydraulic input file can be copied to input project folder"
                  " as it is open in another program.")
            try:
                rmtree(input_hdf5name_folder_path)
                os.mkdir(input_hdf5name_folder_path)
            except PermissionError:
                print("Error: Can't create folder in input project folder.")
    else:
        os.mkdir(input_hdf5name_folder_path)

    # get input files and copy them
    input_folder_path = os.path.dirname(input_file_abspath)
    sh_copy(input_file_abspath, input_hdf5name_folder_path)
    if os.path.exists(os.path.join(input_folder_path, "indexHYDRAU.txt")):
        sh_copy(os.path.join(input_folder_path, "indexHYDRAU.txt"), input_hdf5name_folder_path)


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
        print('Error: ' + qt_tr.translate("hdf5_mod", 'Folder not found to copy inputs \n'))
        return

    if len(names) != len(paths):
        print('Error: ' + qt_tr.translate("hdf5_mod", 'The number of file to be copied is not equal to the number of paths'))
        return

    for i in range(0, len(names)):
        if names[i] != 'unknown file':
            src = os.path.join(paths[i], names[i])
            # if the file is too big, the GUI is freezed
            # if os.path.getsize(src) > 200 * 1024 * 1024:
            #     print('Warning: One input file was larger than 200MB and therefore was not copied to the project'
            #           ' folder. It is necessary to copy this file manually to the input folder if one wants to use the '
            #           'restart file or the log file to load this data auomatically again. \n')
            # else:
            if os.path.isfile(src):
                dst = os.path.join(path_input, names[i])
                shutil.copy(src, dst)


def create_empty_data_2_dict(reach_number, mesh_variables=[], node_variables=[]):
    # create empty dict
    data_2d = dict()

    # mesh
    data_2d["mesh"] = dict()
    data_2d["mesh"]["tin"] = [[] for _ in range(reach_number)]
    data_2d["mesh"]["i_whole_profile"] = [[] for _ in range(reach_number)]
    data_2d["mesh"]["data"] = dict()
    for mesh_variable in mesh_variables:
        data_2d["mesh"]["data"][mesh_variable] = [[] for _ in range(reach_number)]

    # node
    data_2d["node"] = dict()
    data_2d["node"]["xy"] = [[] for _ in range(reach_number)]
    data_2d["node"]["z"] = [[] for _ in range(reach_number)]
    data_2d["node"]["data"] = dict()
    for node_variable in node_variables:
        data_2d["node"]["data"][node_variable] = [[] for _ in range(reach_number)]

    return data_2d


def get_prj_from_epsg_web(epsg_code):
    wkt = urllib.request.urlopen("http://spatialreference.org/ref/epsg/{0}/prettywkt/".format(epsg_code))
    data_byte = wkt.read()
    data_str = data_byte.decode("utf-8")
    remove_spaces = data_str.replace(" ", "")
    output = remove_spaces.replace("\n", "")
    return output


def remove_image(name, path, ext):
    """
    This is a small function used to erase images if erase_id is True. We have a function because different format
    czan be used and because it is done often in the functions above.

    :param name: the name of the file t be erase (without the extension)
    :param path: the path to the file
    :param format1: the type of format
    :return:
    """
    ext = [ext]

    for e in ext:
        if os.path.isfile(os.path.join(path, name + e)):
            try:
                os.remove(os.path.join(path, name + e))
            except PermissionError:
                print('Warning: Figures used by an other program. could not be erased \n')
                return False
    return True


def isstranumber(a):
    try:
        float(a)
        bool_a = True
    except:
        bool_a = False
    return bool_a


def sort_homogoeneous_dict_list_by_on_key(dict_to_sort, key):
    indice_sorted = [dict_to_sort[key].index(x) for x in sorted(dict_to_sort[key])]
    if list(set(indice_sorted)) == [0]:
        indice_sorted = list(range(len(indice_sorted)))

    for key in dict_to_sort.keys():
        key_list = []
        for ind_num, ind_ind in enumerate(indice_sorted):
            key_list.append(dict_to_sort[key][ind_ind])
        dict_to_sort[key] = key_list
    return dict_to_sort


def get_translator(path_prj, name_prj):
    """
    :param language: 0:EN, 1:FR, 2:ES
    :return: application with translate method.
    """
    print("get_translator")
    # get language from project_preferences['language']
    project_preferences = load_project_preferences(path_prj)
    language = project_preferences['language']

    # translator
    app = QApplication(sys.argv)
    languageTranslator = QTranslator(app)
    if language == 0:
        input_file_translation = 'Zen_EN'
        languageTranslator.load(input_file_translation, os.path.join(os.getcwd(), 'translation'))
    if language == 1:
        input_file_translation = 'Zen_FR'
        languageTranslator.load(input_file_translation, os.path.join(os.getcwd(), 'translation'))
    elif language == 2:
        input_file_translation = 'Zen_ES'
        languageTranslator.load(input_file_translation, os.path.join(os.getcwd(), 'translation'))
    app.installTranslator(languageTranslator)
    return app


def txt_file_convert_dot_to_comma(filename_full_path):
    # read and convert
    with open(filename_full_path, 'r') as file:
        text_data_with_comma = file.read().replace('.', ',')
    # write converted
    with open(filename_full_path, 'w') as file:
        file.write(text_data_with_comma)


def frange(start, stop, step):
    i = start
    while i <= stop:
        yield i
        i += step

#
# OGRwkbGeometryType = dict(
#     wkbUnknown=0, wkbPoint=1, wkbLineString=2, wkbPolygon=3,
#     wkbMultiPoint=4, wkbMultiLineString=5, wkbMultiPolygon=6, wkbGeometryCollection=7,
#     wkbCircularString=8, wkbCompoundCurve=9, wkbCurvePolygon=10, wkbMultiCurve=11,
#     wkbMultiSurface=12, wkbCurve=13, wkbSurface=14, wkbPolyhedralSurface=15,
#     wkbTIN=16, wkbTriangle=17, wkbNone=100, wkbLinearRing=101,
#     wkbCircularStringZ=1008, wkbCompoundCurveZ=1009, wkbCurvePolygonZ=1010, wkbMultiCurveZ=1011,
#     wkbMultiSurfaceZ=1012, wkbCurveZ=1013, wkbSurfaceZ=1014, wkbPolyhedralSurfaceZ=1015,
#     wkbTINZ=1016, wkbTriangleZ=1017, wkbPointM=2001, wkbLineStringM=2002,
#     wkbPolygonM=2003, wkbMultiPointM=2004, wkbMultiLineStringM=2005, wkbMultiPolygonM=2006,
#     wkbGeometryCollectionM=2007, wkbCircularStringM=2008, wkbCompoundCurveM=2009, wkbCurvePolygonM=2010,
#     wkbMultiCurveM=2011, wkbMultiSurfaceM=2012, wkbCurveM=2013, wkbSurfaceM=2014,
#     wkbPolyhedralSurfaceM=2015, wkbTINM=2016, wkbTriangleM=2017, wkbPointZM=3001,
#     wkbLineStringZM=3002, wkbPolygonZM=3003, wkbMultiPointZM=3004, wkbMultiLineStringZM=3005,
#     wkbMultiPolygonZM=3006, wkbGeometryCollectionZM=3007, wkbCircularStringZM=3008, wkbCompoundCurveZM=3009,
#     wkbCurvePolygonZM=3010, wkbMultiCurveZM=3011, wkbMultiSurfaceZM=3012, wkbCurveZM=3013,
#     wkbSurfaceZM=3014, wkbPolyhedralSurfaceZM=3015, wkbTINZM=3016, wkbTriangleZM=3017,
#     wkbPoint25D=0x80000001, wkbLineString25D=0x80000002, wkbPolygon25D=0x80000003, wkbMultiPoint25D=0x80000004,
#     wkbMultiLineString25D=0x80000005, wkbMultiPolygon25D=0x80000006, wkbGeometryCollection25D=0x80000007
# )

# https://gdal.org/doxygen/ogr__core_8h.html
polygon_type_values = (3, 2003, 3003, 0x80000003, -2147483645)  # wkbPolygon, wkbPolygonM, wkbPolygonZM, wkbPolygon25D, wkbPolygon25D
point_type_values = (1, 2001, 3001, 0x80000001, -2147483647)  # wkbPoint, wkbPointM, wkbPointZM, wkbPoint25D, wkbPoint25D


""" GUI """


class QGroupBoxCollapsible(QGroupBox):
    def __init__(self):
        super().__init__()
        # group title
        self.setCheckable(True)
        self.setStyleSheet('QGroupBox::indicator {width: 20px; height: 20px;}'
            'QGroupBox::indicator:unchecked {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:hover {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:unchecked:pressed {image: url(translation//icon//triangle_black_closed_50_50.png);}'
            'QGroupBox::indicator:checked {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:checked:hover {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:checked:pressed {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:indeterminate:hover {image: url(translation//icon//triangle_black_open_50_50.png);}'
            'QGroupBox::indicator:indeterminate:pressed {image: url(translation//icon//triangle_black_open_50_50.png);}'
        )
        #'QGroupBox::indicator:checked:hover {image: url(translation//triangle_black_closed.png);}'
        self.toggled.connect(self.toggle_group)
        self.setChecked(True)

    def toggle_group(self, checked):
        if checked:
            self.setFixedHeight(self.sizeHint().height())
        else:
            self.setFixedHeight(30)


class MyProcessList(QThread):
    """
    This class is a subclass of class list created in order to analyze the status of the processes and the refresh of the progress bar in real time.

    :param nb_plot_total: integer value representing the total number of graphs to be produced.
    :param progress_bar: Qprogressbar of DataExplorerFrame to be refreshed
    """
    progress_signal = pyqtSignal(int)

    def __init__(self, type, parent=None):
        QThread.__init__(self, parent)
        self.plot_production_stoped = False
        self.add_plots_state = False
        self.thread_started = False
        self.all_process_runned = False
        self.nb_finished = 0
        self.nb_plot_total = 0
        self.export_production_stoped = False
        self.process_type = type  # cal or plot or export
        self.process_list = []
        self.save_process = []

    def new_plots(self):
        self.add_plots_state = False
        self.save_process = []
        self.process_list = []

    def add_plots(self):
        #print("add_plots")
        self.add_plots_state = True
        self.plot_production_stoped = False
        # remove plots not started
        self.remove_process_not_started()

    def append(self, process):
        self.process_list.append(process)

    def run(self):
        self.thread_started = True
        self.plot_production_stoped = False
        self.nb_plot_total = len(self.process_list)
        if self.process_type == "plot":
            # Process mod
            for i in range(len(self.process_list)):
                if not self.plot_production_stoped:
                    if self.process_list[i][1].value == 0:
                        self.process_list[i][0].start()
                        #print("start", i)
            print("!!!!!!!!!!! all plot started !!!!!!!!!!!")
            self.check_all_plot_produced()

            # # Pool map mod
            # data_list = []
            # for i in range(len(self.process_list)):
            #     data_list.append(self.process_list[i])
            # p = multiprocessing.Pool()
            # result = p.map(mp_worker, data_list)
            # print("result", result)
            # #self.check_all_plot_produced_map()
            # print("before2")
            # p.close()
            # print("before3")
            # self.progress_signal.emit(len(data_list))
        if self.process_type == "export":
            self.all_process_runned = False
            for i in range(len(self.process_list)):
                self.process_list[i][0].start()
            print("!!!!!!!!!!! all exports started !!!!!!!!!!!")
            self.all_process_runned = True
            self.check_all_export_produced()

    def stop_plot_production(self):
        #print("stop_plot_production")
        self.plot_production_stoped = True

    def stop_export_production(self):
        self.export_production_stoped = True

    def close_all_plot(self):
        #print("close_all_plot")
        # remove plots not started
        self.remove_process_not_started()
        for i in range(len(self.process_list)):
            #print(self.process_list[i][0].name, "terminate !!")
            self.process_list[i][0].terminate()
        self.process_list = []

    def close_all_export(self):
        """
        Close all plot process. usefull for button close all figure and for closeevent of Main_windows_1.
        """
        #print("close_all_export")
        if self.thread_started:
            self.export_production_stoped = True
            while not self.all_process_runned:
                print("waiting", self.all_process_runned)
                pass

            for i in range(len(self.process_list)):
                # print(self.process_list[i][0].name,
                #       self.process_list[i][0].exitcode,
                #       self.process_list[i][0].is_alive(),
                #       self.process_list[i][1].value)
                if self.process_list[i][0].is_alive() or self.process_list[i][1].value == 1:
                    #print(self.process_list[i][0].name, "terminate !!")
                    self.process_list[i][0].terminate()
            self.thread_started = False
            self.process_list = []

    def check_all_plot_produced(self):
        """
        State is analysed and progress bar refreshed.
        """
        #print("check_all_plot_produced")
        self.nb_finished = 0
        self.nb_plot_total = len(self.process_list)
        state_list = []
        for i in range(len(self.process_list)):
            state = self.process_list[i][1].value
            state_list.append(state)
            if state == 1:
                self.nb_finished = self.nb_finished + 1
                self.progress_signal.emit(self.nb_finished)
                #print("emit 1")
            if state == 0:
                if i == self.nb_plot_total - 1:  # last of all plot
                    while 0 in state_list:
                        for j in [k for k, l in enumerate(state_list) if l == 0]:
                            state = self.process_list[j][1].value
                            state_list[j] = state
                            if state == 1:
                                self.nb_finished = self.nb_finished + 1
                                self.progress_signal.emit(self.nb_finished)
                                #print("emit 2")
                        if self.plot_production_stoped:
                            sleep(1)
                            for j in [k for k, l in enumerate(state_list) if l == 0]:
                                state = self.process_list[j][1].value
                                state_list[j] = state
                                if state == 1:
                                    self.nb_finished = self.nb_finished + 1
                                    self.progress_signal.emit(self.nb_finished)
                                    #print("emit 3")
                            break

    # def check_all_export_produced(self):
    #     self.nb_finished = 0
    #     self.nb_export_total = len(self.process_list)
    #     state_list = []
    #     for i in range(len(self.process_list)):
    #         state = self.process_list[i][1].value
    #         state_list.append(state)
    #         if state == 1:
    #             self.nb_finished = self.nb_finished + 1
    #             self.progress_signal.emit(self.nb_finished)
    #             #print("emit")
    #         if state == 0:
    #             if i == self.nb_export_total - 1:  # last of all plot
    #                 while 0 in state_list:
    #                     for j in [k for k, l in enumerate(state_list) if l == 0]:
    #                         state = self.process_list[j][1].value
    #                         state_list[j] = state
    #                         if state == 1:
    #                             self.nb_finished = self.nb_finished + 1
    #                             self.progress_signal.emit(self.nb_finished)
    #                             #print("emit")
    #                     if self.export_production_stoped:
    #                         break

    def check_all_export_produced(self):
        self.nb_finished = 0
        self.nb_export_total = len(self.process_list)
        state_list = [self.process_list[i][1].value for i in range(len(self.process_list))]
        self.nb_finished = state_list.count(1)
        self.progress_signal.emit(self.nb_finished)
        while 0 in state_list:
            if self.export_production_stoped:
                break
            state_list = [self.process_list[i][1].value for i in range(len(self.process_list))]
            if state_list.count(1) != self.nb_finished:
                self.nb_finished = state_list.count(1)
                self.progress_signal.emit(self.nb_finished)

    def check_all_process_closed(self):
        """
        Check if a process is alive (plot window open)
        """
        #print("check_all_process_closed")
        if any([self.process_list[i][0].is_alive() for i in range(len(self.process_list))]):  # plot window open or plot not finished
            return False
        else:
            return True

    def remove_process_not_started(self):
        #print("remove_process_not_started")
        for i in reversed(range(len(self.process_list))):
            if not self.process_list[i][0].is_alive():
                #print(self.process_list[i][0].name, "removed from list")
                self.process_list.pop(i)
        self.nb_plot_total = len(self.process_list)


def mp_worker(data_list):
    print(data_list[0])
    state = multiprocessing.Value("i", 0)
    done = data_list[0](state, *data_list[1:])
    print("done,", state)
    return state


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class DoubleClicOutputGroup(QObject):
    double_clic_signal = pyqtSignal()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick:
            self.double_clic_signal.emit()
            return True  # eat double click
        else:
            # standard event processing
            return QObject.eventFilter(self, obj, event)

