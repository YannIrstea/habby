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
import urllib
from copy import deepcopy


# INTERPOLATION TOOLS
def export_empty_text_from_hdf5(unit_type, unit_min, unit_max, filename, path_prj):
    # get unit type
    start = unit_type.find('[')
    end = unit_type.find(']')
    unit_type = unit_type[start + 1:end]

    # headers
    headers = "units[" + unit_type + "]"

    # lines
    linetext1 = str(unit_min)
    linetext2 = str(unit_max)

    text = headers + "\n" + linetext1 + "\n" + linetext2

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_empty_chronicle.txt")
        with open(output_full_path, 'wt') as f:
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
            print("empty line")
            pass
        else:
            for index in range(2):
                # units presence (time or discharge)
                if index == units_index:
                    data = line.split("\t")[index]
                    if not data:
                        chronicle_from_file["units"].append(None)
                    if data:
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
        print("units type match")
        return True, ""
    if unit_hdf5_type != unit_chronicle_type:
        print("units type doesn't match")
        return False, " Desired units type is different from available units type : " + unit_chronicle_type + " != " + unit_hdf5_type


def compute_interpolation(data_description, fish_names, chronicle, types, rounddata=True):
    # check if date
    if "date" in types.keys():
        date_presence = True
    else:
        date_presence = False

    # get hdf5 model
    inter_data_model = dict()
    inter_data_model["unit"] = np.array(list(map(float, data_description["hyd_unit_list"].split(", "))))
    for reach_num in range(int(data_description["hyd_reach_number"])):
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


def export_text_interpolatevalues(data_to_table, horiz_headers, vertical_headers, data_description, types, fig_opt):
    filename = data_description["hab_filename"]
    path_prj = data_description["path_projet"]
    unit_type = types["units"]

    fish_names = list(horiz_headers)

    # prep data
    for fish_num, fish_name in enumerate(fish_names):
        if "hv_" in fish_name:
            fish_names[fish_num] = fish_name.replace("hv_", "")
        if "spu_" in fish_name:
            fish_names[fish_num] = fish_name.replace("spu_", "")

    # header 1
    if fig_opt['language'] == 0:
        if len(types.keys()) > 1:  # date
            date_type = types["date"]
            header = 'reach\tdate\tunit'
        else:
            header = 'reach\tunit'
    else:
        if len(types.keys()) > 1:  # date
            header = 'troncon\tdate\tunit'
        else:
            header = 'troncon\tunit'
    if fig_opt['language'] == 0:
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


# OTHERS TOOLS
def get_prj_from_epsg_web(epsg_code):
    wkt = urllib.request.urlopen("http://spatialreference.org/ref/epsg/{0}/prettywkt/".format(epsg_code))
    data_byte = wkt.read()
    data_str = data_byte.decode("utf-8")
    remove_spaces = data_str.replace(" ", "")
    output = remove_spaces.replace("\n", "")
    return output

