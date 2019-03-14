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



def read_chronicle_from_text_file(chronicle_filepath, fish_names):
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
        if 'Q[' in headers[i].upper() and ']' in headers[i]:  # Q
            q_index = i
    nb_column = len(headers)
    nb_row = len(dataraw.split("\n"))
    # get data in dict
    chronicle_from_file = dict(Date=[], Q=[])
    for fish_name in fish_names:
        chronicle_from_file[fish_name] = []
    data_row_list = dataraw.split("\n")[1:]
    for line in data_row_list:
        if line == "":
            print("empty line")
            pass
        else:
            for index in range(2):
                if index == q_index:
                    data = line.split("\t")[index]
                    if not data:
                        chronicle_from_file["Q"].append(None)
                    if data:
                        chronicle_from_file["Q"].append(float(data))
                else:
                    chronicle_from_file["Date"].append(line.split("\t")[index])
    chronicle_from_file["Q"] = np.array(chronicle_from_file["Q"])
    chronicle_from_file["Date"] = np.array(
        [dt.strptime(date, '%d/%m/%Y').date() for date in chronicle_from_file["Date"]], dtype='datetime64')
    return chronicle_from_file


def compute_interpolation(data_description, fish_names, chronicle):
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
            inter_data_model[fish_name] = spu / wet_area

    # for each new unit get HV
    for fish_name in fish_names:
        chronicle[fish_name] = []

    # copy for round for table gui
    # chronicle_gui = dict()
    # chronicle_gui.update(chronicle)

    chronicle_gui = deepcopy(chronicle)

    q_min = min(inter_data_model["unit"])
    q_max = max(inter_data_model["unit"])
    for fish_name in fish_names:
        for index_to_est, q_value_to_est in enumerate(chronicle["units"]):
            if q_value_to_est:
                if q_value_to_est < q_min or q_value_to_est > q_max:
                    chronicle[fish_name].append(None)
                    chronicle_gui[fish_name].append("")
                else:
                    data_interp = np.interp(q_value_to_est, inter_data_model["unit"], inter_data_model[fish_name])
                    chronicle[fish_name].append(data_interp)
                    chronicle_gui[fish_name].append("{0:.2f}".format(data_interp))
            if not q_value_to_est:
                chronicle[fish_name].append(None)
                chronicle_gui[fish_name].append("")

    # filename output txt
    filename_abs_path_output = os.path.join(data_description["path_projet"],
                                            "output",
                                            "text",
                                            os.path.splitext(data_description["hab_filename"])[0] + "_interp.txt")

    # export txt
    #export_text_interpolatevalues(chronicle, fish_names, filename_abs_path_output)

    # plot
    #plot_mod.plot_interpolate_chronicle(chronicle, fish_names)

    horiz_headers = list(chronicle_gui.keys())[1:]
    vertical_headers = list(map(str, chronicle_gui["units"]))
    del chronicle_gui["units"]
    data_to_table = list(zip(*chronicle_gui.values()))

    return data_to_table, horiz_headers, vertical_headers


def export_text_interpolatevalues(chronicle, fish_names, filename_abs_path_output):
    # convert to string
    chronicle["units"] = np.array(np.datetime_as_string(chronicle["units"]))
    # headers
    headers = "units\tQ"
    for fish_name in fish_names:
        headers += "\t" + fish_name
    # lines
    linetext = ""
    # for each line
    for index, line in enumerate(range(len(chronicle["units"]))):
        # print("line", line)
        # for each column
        for key in chronicle.keys():
            # print("key", key)
            linetext += str(chronicle[key][index]) + "\t"
        linetext += "\n"
    text = headers + "\n" + linetext

    # export
    with open(filename_abs_path_output,
              'wt') as f:
        f.write(text)