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
from copy import deepcopy
import numpy as np
from PyQt5.QtCore import QLocale

""" INTERPOLATION TOOLS """


def export_empty_text_from_hdf5(unit_type, unit_min, unit_max, filename, path_prj):
    # headers
    headers = unit_type.replace(" ", "")
    headers = headers.replace("discharge", "Q")
    headers = headers.replace(" ", "")

    # lines
    linetext1 = str(unit_min)
    linetext2 = str(unit_max)

    text = headers + "\n" + linetext1 + "\n" + linetext2

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_empty_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            # change decimal point
            locale = QLocale()
            if locale.decimalPoint() == ",":
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
        if 'Q[' in headers[i].upper() and ']' in headers[i]:  # Q
            units_index = i
            unit_type = headers[units_index]

    if units_index is None:
        return False, "Error: Interpolation not done. 'unit[' header not found in " + chronicle_filepath + "."

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


def check_matching_units(unit_type, types):
    unit_chronicle_type = None
    # get units types
    unit_hdf5_type = unit_type[unit_type.find('[') + 1:unit_type.find(']')]
    for key in types.keys():
        if "units" in key:
            unit_chronicle_type = types[key].replace("m<sup>3</sup>/s", "m3/s")
            unit_chronicle_type = unit_chronicle_type[unit_chronicle_type.find('[') + 1:unit_chronicle_type.find(']')]

    # check matching units type ok
    if unit_hdf5_type == unit_chronicle_type:
        return True, ""
    if unit_hdf5_type != unit_chronicle_type:
        return False, " Desired units type is different from available units type : " + unit_chronicle_type + " != " + unit_hdf5_type


def compute_interpolation(data_2d, animal_list, reach_number, chronicle, types, rounddata=True):
    # check if date
    if "date" in types.keys():
        date_presence = True
    else:
        date_presence = False

    # get hdf5 model
    inter_data_model = dict()
    inter_data_model["unit"] = list(map(float, data_2d.unit_list[reach_number]))
    total_wet_area = []
    for unit_number in range(data_2d[reach_number].unit_number):
        total_wet_area.append(data_2d[reach_number][unit_number].total_wet_area)
    wet_area = np.array(total_wet_area)
    # map by fish
    for animal_index, animal in enumerate(animal_list):
        spu = np.array(animal.wua[reach_number])
        inter_data_model["hv_" + animal.name] = spu / wet_area
        inter_data_model["spu_" + animal.name] = spu
        inter_data_model["si_" + animal.name] = animal.percent_area_unknown[reach_number]

    # copy chonicle to interpolated
    chronicle_interpolated = deepcopy(chronicle)
    # Add new column to chronicle_interpolated
    for animal in animal_list:
        chronicle_interpolated["hv_" + animal.name] = []
        chronicle_interpolated["spu_" + animal.name] = []
        chronicle_interpolated["si_" + animal.name] = []
    # copy for round for table gui
    chronicle_gui = deepcopy(chronicle_interpolated)
    # rename unit key and preserve the ordering
    chronicle_gui = {types["units"] if k == "units" else k: v for k, v in chronicle_gui.items()}

    # get min max
    q_min = min(inter_data_model["unit"])
    q_max = max(inter_data_model["unit"])

    # interpolation
    for animal in animal_list:
        for index_to_est, q_value_to_est in enumerate(chronicle_interpolated["units"]):
            if q_value_to_est != None:
                if q_value_to_est < q_min or q_value_to_est > q_max:
                    chronicle_interpolated["hv_" + animal.name].append(None)
                    chronicle_gui["hv_" + animal.name].append("")
                    chronicle_interpolated["spu_" + animal.name].append(None)
                    chronicle_gui["spu_" + animal.name].append("")
                    chronicle_interpolated["si_" + animal.name].append(None)
                    chronicle_gui["si_" + animal.name].append("")
                else:
                    data_interp_hv = np.interp(q_value_to_est,
                                               inter_data_model["unit"],
                                               inter_data_model["hv_" + animal.name])
                    chronicle_interpolated["hv_" + animal.name].append(data_interp_hv)
                    chronicle_gui["hv_" + animal.name].append("{0:.2f}".format(data_interp_hv))

                    data_interp_spu = np.interp(q_value_to_est,
                                                inter_data_model["unit"],
                                                inter_data_model["spu_" + animal.name])
                    chronicle_interpolated["spu_" + animal.name].append(data_interp_spu)
                    chronicle_gui["spu_" + animal.name].append("{0:.0f}".format(data_interp_spu))

                    data_interp_si = np.interp(q_value_to_est,
                                                inter_data_model["unit"],
                                                inter_data_model["si_" + animal.name])
                    chronicle_interpolated["si_" + animal.name].append(data_interp_si)
                    chronicle_gui["si_" + animal.name].append("{0:.1f}".format(data_interp_si))

            if q_value_to_est is None:
                chronicle_interpolated["hv_" + animal.name].append(None)
                chronicle_gui["hv_" + animal.name].append("")
                chronicle_interpolated["spu_" + animal.name].append(None)
                chronicle_gui["spu_" + animal.name].append("")
                chronicle_interpolated["si_" + animal.name].append(None)
                chronicle_gui["si_" + animal.name].append("")

    # alpha order
    # chronicle_gui = {key: value for key, value in sorted(chronicle_gui.items())}
    # chronicle_interpolated = {key: value for key, value in sorted(chronicle_interpolated.items())}

    # round for GUI
    if rounddata:
        if not date_presence:
            horiz_headers = list(chronicle_gui.keys())[1:]
            vertical_headers = list(map(str, chronicle_gui[types["units"]]))
            del chronicle_gui[types["units"]]
            data_to_table = list(zip(*chronicle_gui.values()))
        if date_presence:
            horiz_headers = list(chronicle_gui.keys())[1:]
            vertical_headers = list(map(str, chronicle_gui["date"]))
            del chronicle_gui["date"]
            chronicle_gui[types["units"]] = list(map(str, chronicle_gui[types["units"]]))
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
            chronicle_interpolated[types["units"]] = list(map(str, chronicle_interpolated["units"]))
            data_to_table = chronicle_interpolated

    return data_to_table, horiz_headers, vertical_headers


def export_text_interpolatevalues(state, data_to_table, horiz_headers, vertical_headers, data_2d, types, project_preferences):
    filename = data_2d.filename
    path_prj = project_preferences["path_prj"]
    unit_type = data_2d.unit_type

    fish_names = list(horiz_headers)

    # prep data
    for fish_num, fish_name in enumerate(fish_names):
        if "hv_" in fish_name:
            fish_names[fish_num] = fish_name.replace("hv_", "")
        if "spu_" in fish_name:
            fish_names[fish_num] = fish_name.replace("spu_", "")
        if "si_" in fish_name:
            fish_names[fish_num] = fish_name.replace("si_", "")

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
        header += "".join(['\tHV' + str(i) for i in range(int(len(fish_names) / 3))])
        header += "".join(['\tWUA' + str(i) for i in range(int(len(fish_names) / 3))])
        header += "".join(['\tUA' + str(i) for i in range(int(len(fish_names) / 3))])
    else:
        header += "".join(['\tVH' + str(i) for i in range(int(len(fish_names) / 3))])
        header += "".join(['\tSPU' + str(i) for i in range(int(len(fish_names) / 3))])
        header += "".join(['\tSI' + str(i) for i in range(int(len(fish_names) / 3))])
    header += '\n'
    # header 2
    if len(types.keys()) > 1:  # date
        header += '[]\t[' + date_type + ']\t[' + unit_type + ']'
    else:
        header += '[]\t[' + unit_type + ']'
    header += "".join(['\t[]' for _ in range(int(len(fish_names) / 3))])
    header += "".join(['\t[m2]' for _ in range(int(len(fish_names) / 3))])
    header += "".join(['\t[%]' for _ in range(int(len(fish_names) / 3))])
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
                locale = QLocale()
                if locale.decimalPoint() == ",":
                    data_hv = str(data_hv).replace('.', ',')
                linetext += str(data_hv) + "\t"
        # new line
        linetext += "\n"
    text = header + "\n" + linetext

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_interpolate_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            f.write(text)
        state.value = 100  # process finished
    except:
        print('Error: ' + 'File not exported as it may be opened by another program.')

