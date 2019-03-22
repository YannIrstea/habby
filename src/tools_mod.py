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
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime as dt
from copy import deepcopy

from src import plot_mod


def read_chronicle_from_text_file(chronicle_filepath):
    # read discharge chronicle
    #chronicle_filepath = r"C:\Users\quentin.royer\Documents\TAF\DATA\Durance\Hydraulique\QMJ_2018-2019.txt"
    with open(chronicle_filepath, 'rt') as f:
        dataraw = f.read()
    # headers
    headers = dataraw.split("\n")[0].split("\t")
    date_index = None
    q_index = None
    for i in range(len(headers)):
        if 'DATE' in headers[i].upper():  # Date
            date_index = i
        if 'UNITS[' in headers[i].upper() and ']' in headers[i]:  # Q
            q_index = i
    nb_column = len(headers)
    nb_row = len(dataraw.split("\n"))

    # create dict
    if type(date_index) == int and type(q_index) == int:
        chronicle_from_file = dict(date=[], units=[])
    if type(date_index) == int and type(q_index) != int:
        chronicle_from_file = dict(date=[])
    if type(date_index) != int and type(q_index) == int:
        chronicle_from_file = dict(units=[])


    data_row_list = dataraw.split("\n")[1:]
    for line in data_row_list:
        if line == "":
            print("empty line")
            #chronicle_from_file["units"].append(None)
            pass
        else:
            for index in range(2):
                if index == q_index:
                    data = line.split("\t")[index]
                    if not data:
                        chronicle_from_file["units"].append(None)
                    if data:
                        chronicle_from_file["units"].append(float(data))
                if index == date_index:
                    chronicle_from_file["date"].append(line.split("\t")[index])
    chronicle_from_file["units"] = np.array(chronicle_from_file["units"])
    if type(date_index) == int:
        chronicle_from_file["date"] = np.array(
            [dt.strptime(date, '%d/%m/%Y').date() for date in chronicle_from_file["date"]], dtype='datetime64')
    return chronicle_from_file


def compute_interpolation(data_description, fish_names, chronicle, rounddata=True):
    unit_type = data_description["hyd_unit_type"]

    # get all units available
    inter_data_model = dict()
    inter_data_model["unit"] = np.array(list(map(float, data_description["hyd_unit_list"].split(", "))))

    # calc hv known values
    for reach_num in range(int(data_description["hyd_reach_number"])):
        wet_area = np.array(list(map(float, data_description["total_wet_area"][reach_num])))
        # map by fish
        for fish_index, fish_name in enumerate(fish_names):
            spu = np.array(list(map(float, data_description["total_WUA_area"][fish_name][reach_num])))
            inter_data_model["hv_" + fish_name] = spu / wet_area
            inter_data_model["spu_" + fish_name] = spu

    # for each new unit get HV
    for fish_name in fish_names:
        chronicle["hv_" + fish_name] = []
    for fish_name in fish_names:
        chronicle["spu_" + fish_name] = []

    # copy for round for table gui
    chronicle_gui = deepcopy(chronicle)

    # get min max
    q_min = min(inter_data_model["unit"])
    q_max = max(inter_data_model["unit"])

    # interpolation
    for fish_name in fish_names:
        for index_to_est, q_value_to_est in enumerate(chronicle["units"]):
            if q_value_to_est != None:
                if q_value_to_est < q_min or q_value_to_est > q_max:
                    chronicle["hv_" + fish_name].append(None)
                    chronicle_gui["hv_" + fish_name].append("")
                    chronicle["spu_" + fish_name].append(None)
                    chronicle_gui["spu_" + fish_name].append("")
                else:
                    data_interp_hv = np.interp(q_value_to_est,
                                               inter_data_model["unit"],
                                               inter_data_model["hv_" + fish_name])
                    chronicle["hv_" + fish_name].append(data_interp_hv)
                    chronicle_gui["hv_" + fish_name].append("{0:.2f}".format(data_interp_hv))
                    data_interp_spu = np.interp(q_value_to_est,
                                                inter_data_model["unit"],
                                                inter_data_model["spu_" + fish_name])
                    chronicle["spu_" + fish_name].append(data_interp_spu)
                    chronicle_gui["spu_" + fish_name].append("{0:.0f}".format(data_interp_spu))
            if q_value_to_est == None:
                chronicle["hv_" + fish_name].append(None)
                chronicle_gui["hv_" + fish_name].append("")
                chronicle["spu_" + fish_name].append(None)
                chronicle_gui["spu_" + fish_name].append("")

    # round for GUI ?
    if rounddata:
        horiz_headers = list(chronicle_gui.keys())[1:]
        vertical_headers = list(map(str, chronicle_gui["units"]))
        del chronicle_gui["units"]
        data_to_table = list(zip(*chronicle_gui.values()))

    if not rounddata:
        horiz_headers = list(chronicle.keys())[1:]
        vertical_headers = list(map(str, chronicle["units"]))
        data_to_table = chronicle

    return data_to_table, horiz_headers, vertical_headers


def export_text_interpolatevalues(data_to_table, horiz_headers, vertical_headers, data_description):
    filename = data_description["hab_filename"]
    path_prj = data_description["path_projet"]
    unit_type = data_description["hyd_unit_type"]

    # headers
    headers = unit_type
    for fish_name in horiz_headers:
        headers += "\t" + fish_name
    # lines
    linetext = ""
    # for each line
    for row_index in range(len(vertical_headers)):
        # print("line", line)
        linetext += str(vertical_headers[row_index]) + "\t"
        # for each column
        for column_name in horiz_headers:
            data_hv = data_to_table[column_name][row_index]
            if not data_hv:
                linetext += "None" + "\t"
            if data_hv:
                linetext += str(data_hv) + "\t"
        # new line
        linetext += "\n"
    text = headers + "\n" + linetext

    # export
    try:
        output_full_path = os.path.join(path_prj, "output", "text", os.path.splitext(filename)[0] + "_interpolate_chronicle.txt")
        with open(output_full_path, 'wt') as f:
            f.write(text)
            return True
    except:
        return False


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
