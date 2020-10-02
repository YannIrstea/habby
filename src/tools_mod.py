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
import shutil
import numpy as np
from PyQt5.QtCore import QTranslator, QObject, pyqtSignal, QEvent, QCoreApplication as qt_tr
from PyQt5.QtWidgets import QApplication, QGroupBox, QFrame
from PyQt5.QtCore import QLocale
import multiprocessing

from src.project_properties_mod import load_project_properties

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


def check_matching_units(unit_type, types):
    unit_chronicle_type = None
    # get units types
    unit_hdf5_type = unit_type[unit_type.find('[') + 1:unit_type.find(']')]
    for key in types.keys():
        if "units" in key:
            unit_chronicle_type = types[key]
            unit_chronicle_type = unit_chronicle_type.replace("m<sup>3</sup>/s", "m3/s")

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
    for unit_number in range(data_2d.unit_number):
        total_wet_area.append(data_2d[reach_number][unit_number].total_wet_area)
    wet_area = np.array(total_wet_area)
    # map by fish
    for animal_index, animal in enumerate(animal_list):
        spu = np.array(animal.wua[reach_number])
        inter_data_model["hv_" + animal.name] = spu / wet_area
        inter_data_model["spu_" + animal.name] = spu

    # copy chonicle to interpolated
    chronicle_interpolated = deepcopy(chronicle)
    # Add new column to chronicle_interpolated
    for animal in animal_list:
        chronicle_interpolated["hv_" + animal.name] = []
        chronicle_interpolated["spu_" + animal.name] = []
    # copy for round for table gui
    chronicle_gui = deepcopy(chronicle_interpolated)
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
            if q_value_to_est == None:
                chronicle_interpolated["hv_" + animal.name].append(None)
                chronicle_gui["hv_" + animal.name].append("")
                chronicle_interpolated["spu_" + animal.name].append(None)
                chronicle_gui["spu_" + animal.name].append("")

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


def export_text_interpolatevalues(data_to_table, horiz_headers, vertical_headers, data_2d, types, project_preferences):
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
                locale = QLocale()
                if locale.decimalPoint() == ",":
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


def create_map_plot_string_dict(name_hdf5, reach_name, unit_name, unit_type, variable, variable_unit, string_tr, variable_info=""):
    # colorbar_label and variable_info
    if variable_info:
        colorbar_label = variable_info.split(" = ")[0] + " [" + variable_unit + "]"
        variable_info = " (" + variable_info + ")"
    else:
        colorbar_label = "[" + variable_unit + "]"

    # plot_string_dict
    plot_string_dict = dict(reach_name=reach_name,
                            unit_name=unit_name,
                            title=variable + ' - ' + reach_name + ' - ' + unit_name + " [" + unit_type + "]",
                            variable_title=variable.replace("_", " ") + ' [' + variable_unit + ']' + " " + variable_info,
                            reach_title=string_tr[0] + " : " + reach_name,
                            unit_title=string_tr[1] + " : " + unit_name + " [" + unit_type.replace("m3/s", "$m^3$/s") + "]",
                            colorbar_label=colorbar_label,
                            filename=os.path.splitext(name_hdf5)[0] + "_" + reach_name + "_" + unit_name.replace(".", "_") + '_' + variable.replace(" ", "_") + "_map"
                            )
    return plot_string_dict


def copy_shapefiles(input_shapefile_abspath, hdf5_name, dest_folder_path, remove=True):
    """
    get all file with same prefix of input_shapefile_abspath and copy them to dest_folder_path.
    """
    # create folder with hdf5 name in input project folder
    input_hdf5name_folder_path = os.path.join(dest_folder_path, os.path.splitext(hdf5_name)[0])
    if os.path.exists(input_hdf5name_folder_path):
        if remove:
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


def copy_hydrau_input_files(path_filename_source, filename_source_str, hdf5_name, dest_folder_path):
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
    for file in filename_source_str.split(", "):
        if not os.path.splitext(file)[1]:  # no ext (ex: rubar20)
            files_to_copy = [x for x in os.listdir(path_filename_source) if file in x]
            for file_to_copy in files_to_copy:
                sh_copy(os.path.join(path_filename_source, file_to_copy), input_hdf5name_folder_path)
        else:
            sh_copy(os.path.join(path_filename_source, file), input_hdf5name_folder_path)
    if os.path.exists(os.path.join(path_filename_source, "indexHYDRAU.txt")):
        sh_copy(os.path.join(path_filename_source, "indexHYDRAU.txt"), input_hdf5name_folder_path)


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


def create_empty_data_2d_dict(reach_number, mesh_variables=[], node_variables=[]):
    """
    data_2d :
    """
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


def create_empty_data_2d_whole_profile_dict(reach_number, mesh_variables=[], node_variables=[]):
    # create empty dict
    data_2d_whole_profile = dict()

    # mesh
    data_2d_whole_profile["mesh"] = dict()
    data_2d_whole_profile["mesh"]["tin"] = [[] for _ in range(reach_number)]
    data_2d_whole_profile["mesh"]["data"] = dict()
    for mesh_variable in mesh_variables:
        data_2d_whole_profile["mesh"]["data"][mesh_variable] = [[] for _ in range(reach_number)]

    # node
    data_2d_whole_profile["node"] = dict()
    data_2d_whole_profile["node"]["xy"] = [[] for _ in range(reach_number)]
    data_2d_whole_profile["node"]["z"] = [[] for _ in range(reach_number)]
    data_2d_whole_profile["node"]["data"] = dict()
    for node_variable in node_variables:
        data_2d_whole_profile["node"]["data"][node_variable] = [[] for _ in range(reach_number)]
    return data_2d_whole_profile


def check_data_2d_dict_validity(data_2d, reach_number, unit_number):
    # global
    with_data = True
    reach_validity = True
    unit_validity = True
    # variables
    tin_validity = True
    i_whole_profile_validity = True
    xy_validity = True
    z_validity = True
    data_validity = True
    sub_validity = True

    # warnings_list
    warnings_list = []

    # loop on keys
    for key1 in data_2d.keys():
        if type(data_2d[key1]) == list:
            pass
        else:
            # node or mesh
            for key2 in data_2d[key1].keys():
                    # data
                    if type(data_2d[key1][key2]) == dict:
                        for key3 in data_2d[key1][key2].keys():
                            if data_2d[key1][key2][key3] == [[]] or data_2d[key1][key2][key3] == []:
                                with_data = False
                                warnings_list.append("no data loaded (" + key3 + ")")
                                break
                            if len(data_2d[key1][key2][key3]) != reach_number:
                                reach_validity = False
                                warnings_list.append("reach number : " + str(len(data_2d[key1][key2][key3])) + " != " + str(reach_number))
                            if len(data_2d[key1][key2][key3][0]) != unit_number:
                                unit_validity = False
                                warnings_list.append("unit number : " + str(len(data_2d[key1][key2][key3][0])) + " != " + str(unit_number))
                            if key3 == "sub" and data_2d[key1][key2][key3][0][0].ndim not in (2, 8, 10):
                                sub_validity = False
                                warnings_list.append(key3 + " : " + str(data_2d[key1][key2][key3][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][key3][0][0].dtype))
                            if data_2d[key1][key2][key3][0][0].ndim != 1:
                                data_validity = False
                                warnings_list.append(key3 + " : " + str(data_2d[key1][key2][key3][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][key3][0][0].dtype))
                    # struct (tin, i_whole_profile, xy or z)
                    if type(data_2d[key1][key2]) == list:
                        if data_2d[key1][key2] == [[]] or data_2d[key1][key2] == []:
                            with_data = False
                            warnings_list.append("no data loaded (" + key2 + ")")
                            break
                        if len(data_2d[key1][key2]) != reach_number:
                            reach_validity = False
                            warnings_list.append("reach number : " + str(len(data_2d[key1][key2])) + " != " + str(reach_number))
                        if len(data_2d[key1][key2][0]) != unit_number:
                            unit_validity = False
                            warnings_list.append("unit number : " + str(len(data_2d[key1][key2][0])) + " != " + str(unit_number))
                        if key2 == "tin" and data_2d[key1][key2][0][0].ndim != 2:
                            tin_validity = False
                            warnings_list.append(key2 + " : " + str(data_2d[key1][key2][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][0][0].dtype))
                        if key2 == "xy" and data_2d[key1][key2][0][0].ndim != 2:
                            xy_validity = False
                            warnings_list.append(key2 + " : " + str(data_2d[key1][key2][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][0][0].dtype))
                        if key2 == "i_whole_profile" and data_2d[key1][key2][0][0].ndim != 1:
                            i_whole_profile_validity = False
                            warnings_list.append(key2 + " : " + str(data_2d[key1][key2][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][0][0].dtype))
                        if key2 == "z" and data_2d[key1][key2][0][0].ndim != 1:
                            z_validity = False
                            warnings_list.append(key2 + " : " + str(data_2d[key1][key2][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][0][0].dtype))
                        if key2 not in ("tin", "xy", "i_whole_profile", "z"):
                            data_validity = False
                            warnings_list.append(key2 + " : " + str(data_2d[key1][key2][0][0].ndim) + " ndim" + ", dtype=" + str(data_2d[key1][key2][0][0].dtype))

    if reach_validity and unit_validity and tin_validity and i_whole_profile_validity and xy_validity and z_validity and data_validity and sub_validity and with_data:
        return True, ""
    else:
        return False, "Error: " + ", ".join(warnings_list)


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


def sort_homogoeneous_dict_list_by_on_key(dict_to_sort, key, data_type=str):
    if data_type == str:
        indice_sorted = [dict_to_sort[key].index(x) for x in sorted(dict_to_sort[key])]
    elif data_type == float:
        indice_sorted = np.argsort(list(map(float, dict_to_sort[key]))).tolist()

    if list(set(indice_sorted)) == [0]:
        indice_sorted = list(range(len(indice_sorted)))

    for key in dict_to_sort.keys():
        key_list = []
        for ind_num, ind_ind in enumerate(indice_sorted):
            key_list.append(dict_to_sort[key][ind_ind])
        dict_to_sort[key] = key_list
    return dict_to_sort


def get_translator(path_prj):
    """
    :param language: 0:EN, 1:FR, 2:ES
    :return: application with translate method.
    """
    #print("get_translator")
    # get language from project_preferences['language']
    project_preferences = load_project_properties(path_prj)
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
            self.setFlat(False)
            self.setFixedHeight(self.sizeHint().height())
        else:
            self.setFlat(True)
            self.setFixedHeight(28)


def mp_worker(data_list):
    print(data_list[0])
    state = multiprocessing.Value("d", 0)
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

