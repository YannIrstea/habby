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
import sys
from io import StringIO
from PyQt5.QtCore import QCoreApplication as qt_tr
from osgeo.ogr import GetDriverByName
from osgeo.osr import SpatialReference
from copy import deepcopy
import numpy as np

from src import ascii_mod
from src import hec_ras2D_mod, hec_ras1D_mod
from src import rubar1d2d_mod
from src import basement_mod
from src import telemac_mod
from src.tools_mod import polygon_type_values, point_type_values, sort_homogoeneous_dict_list_by_on_key
from src.project_properties_mod import create_default_project_properties_dict
from src.tools_mod import create_empty_data_2d_dict, create_empty_data_2d_whole_profile_dict
from src import hdf5_mod
from src import manage_grid_mod


def get_hydrau_description_from_source(filename_list, path_prj, model_type, nb_dim):
    """
    :param filename_list: list of absolute path file, type: list of str
    :param path_prj: absolute path to project, type: str
    :param model_type: type of hydraulic model, type: str
    :param nb_dim: dimension number (1D/1.5D/2D), type: int
    :return: hydrau_description, type: dict
    :return: warnings list, type: list of str
    """
    # init
    name_prj = os.path.splitext(os.path.basename(path_prj))[0]
    warning_list = []  # text warning output
    hydrau_description = "Error"
    hydrau_case = "unknown"
    if len(filename_list) == 1:  # one file selected
        more_than_one_file_selected_by_user = False  # one file to read
        filename_path = os.path.normpath(filename_list[0])
        folder_path = os.path.dirname(filename_path)
        filename = [os.path.basename(filename_path)]
        blob, ext = os.path.splitext(filename[0])
    elif len(filename_list) > 1:  # more than one file selected
        more_than_one_file_selected_by_user = True  # several files to read
        filename_path = filename_list
        folder_path = os.path.dirname(filename_path[0])
        filename = [os.path.basename(file) for file in filename_path]
        blob = [os.path.splitext(file)[0] for file in filename]
        ext = [os.path.splitext(file)[1] for file in filename]

    # indexHYDRAU paths
    filename_path_index = os.path.join(folder_path, "indexHYDRAU.txt")

    # indexHYDRAU.txt absence
    if not os.path.isfile(filename_path_index):
        if model_type != "ASCII":
            warning_list.append("Warning: " + qt_tr.translate("hydro_input_file_mod",
                                                              "indexHYDRAU.txt doesn't exist. It will be created in the 'input' directory after the creation "
                                                              "of the .hyd file. The latter will be filled in according to your choices."))

        # more_than_one_file_selected_by_user
        if more_than_one_file_selected_by_user:
            if model_type == 'RUBAR20':  # change mode and remove one of them
                more_than_one_file_selected_by_user = False
                filename = filename[0]
                filename_path = filename_path[0]
            else:
                # hydrau_description for several file
                hydrau_description_multiple = []

                for i, file in enumerate(filename):
                    # get units name from file
                    filename_path = os.path.join(folder_path, file)
                    unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
                    warning_list.extend(warning_list_timestep)
                    unit_index_from_file = [True] * nbtimes
                    # hdf5 filename
                    blob2, ext = os.path.splitext(file)
                    name_hdf5 = blob2.replace(".", "_") + ".hyd"

                    # multi description
                    hydrau_description_multiple.append(dict(path_prj=path_prj,
                                                            name_prj=name_prj,
                                                            hydrau_case=hydrau_case,
                                                            filename_source=file,
                                                            path_filename_source=folder_path,
                                                            hdf5_name=name_hdf5,
                                                            model_type=model_type,
                                                            model_dimension=str(nb_dim),
                                                            unit_list=unit_name_from_file,
                                                            unit_list_full=unit_name_from_file,
                                                            unit_list_tf=unit_index_from_file,
                                                            unit_number=str(nbtimes),
                                                            unit_type=unit_type,
                                                            reach_list="unknown",
                                                            reach_number=str(1),
                                                            reach_type="river",
                                                            epsg_code="unknown",
                                                            flow_type="unknown",
                                                            index_hydrau="False"))  # continuous flow

                # set actual hydrau_description
                hydrau_description = hydrau_description_multiple

        # one file selected_by_user
        if not more_than_one_file_selected_by_user:  # don't set elif (because if rubar20 more_than_one_file_selected_by_user set to False)
            # get units name from file
            if model_type == 'ASCII':
                ascii_description = ascii_mod.get_ascii_model_description(filename_path)
                if type(ascii_description) == str:
                    return ascii_description, None
                else:
                    epsg_code = ascii_description["epsg_code"]
                    unit_type = ascii_description["unit_type"]
                    unit_list = ascii_description["unit_list"]
                    unit_list_tf = [list(map(bool, x)) for x in ascii_description["unit_list"]]
                    reach_number = ascii_description["reach_number"]
                    reach_list = ascii_description["reach_list"]
                    sub = ascii_description["sub"]
                    if sub:
                        warning_list.append("Warning: " + qt_tr.translate("hydro_input_file_mod",
                                                                          "Substrate data present in the ascii input file. "
                                                                          "Data loading will create .hab directly instead of .hyd "
                                                                          "(loading button label changed)"))
                    nbtimes = len(unit_list[0])
            else:
                epsg_code = "unknown"
                reach_number = 1
                reach_list = "unknown"
                sub = False
                unit_type, nbtimes, unit_list, warning_list_timestep = get_time_step(filename_path, model_type)
                warning_list.extend(warning_list_timestep)
                unit_list_tf = list(map(bool, unit_list))
                if model_type == 'RUBAR20':  # remove extension
                    filename, _ = os.path.splitext(filename)

            hydrau_description = dict(path_prj=path_prj,
                                      name_prj=name_prj,
                                      hydrau_case=hydrau_case,
                                      filename_source=filename[0],
                                      path_filename_source=folder_path,
                                      hdf5_name=os.path.splitext(filename[0])[0].replace(".", "_") + ".hyd",
                                      model_type=model_type,
                                      model_dimension=str(nb_dim),
                                      epsg_code=epsg_code,
                                      unit_list=unit_list,
                                      unit_list_full=unit_list,
                                      unit_list_tf=unit_list_tf,
                                      unit_number=str(nbtimes),
                                      unit_type=unit_type,
                                      reach_list=reach_list,
                                      reach_number=str(reach_number),
                                      reach_type="river",
                                      flow_type="unknown",
                                      sub=sub,
                                      index_hydrau=False)

    # indexHYDRAU.txt presence
    if os.path.isfile(filename_path_index):
        # init variables
        discharge_presence = False  # "Q[" in headers
        time_presence = False  # "T[" in headers
        reach_presence = False  # "reachname" in headers
        selectedfiles_textfiles_matching = False

        # read text file
        with open(filename_path_index, 'rt') as f:
            dataraw = f.read()
        # get epsg code
        epsg_code = dataraw.split("\n")[0].split("EPSG=")[1].strip()
        # read headers and nb row
        headers = dataraw.split("\n")[1].split("\t")
        nb_row = len(dataraw.split("\n"))
        # create one dict for all column
        data_index_file = dict((key, []) for key in headers)
        data_row_list = dataraw.split("\n")[2:]
        for line in data_row_list:
            if line == "":
                # print("empty line")
                pass
            else:
                for index, column_name in enumerate(headers):
                    data_index_file[column_name].append(line.split("\t")[index])

        if model_type == 'RUBAR20':
            more_than_one_file_selected_by_user = False
            selectedfiles_textfiles_match = [True] * 2
            if type(filename) == list:
                filename = filename[0]
                filename_path = filename_path[0]

        elif ext != ".txt":  # from file
            # more_than_one_file_selected_by_user or more_than_one_file_in indexHYDRAU (if from .txt)
            if len(data_index_file["filename"]) > 1:
                more_than_one_file_selected_by_user = True
            # textfiles filesexisting matching
            selectedfiles_textfiles_match = [False] * len(data_index_file["filename"])
            for i, file_from_indexfile in enumerate(data_index_file["filename"]):
                if os.path.isfile(os.path.join(folder_path, file_from_indexfile)):
                    if file_from_indexfile in filename:
                        selectedfiles_textfiles_match[i] = True
                    else:
                        selectedfiles_textfiles_match[i] = False
                else:
                    return "Error: " + file_from_indexfile + " doesn't exist in " + folder_path, None
        elif ext == ".txt":  # from indexHYDRAU.txt
            # more_than_one_file_selected_by_user or more_than_one_file_in indexHYDRAU (if from .txt)
            if len(data_index_file["filename"]) > 1:
                more_than_one_file_selected_by_user = True
            # textfiles filesexisting matching
            selectedfiles_textfiles_match = [False] * len(data_index_file["filename"])
            for i, file_from_indexfile in enumerate(data_index_file["filename"]):
                if os.path.isfile(os.path.join(folder_path, file_from_indexfile)):
                    selectedfiles_textfiles_match[i] = True
                else:
                    return "Error: " + file_from_indexfile + " doesn't exist in " + folder_path, None

        # check conditions
        if all(selectedfiles_textfiles_match):
            selectedfiles_textfiles_matching = True
            filename_list = data_index_file["filename"]
        if any("Q[" in s for s in headers):
            discharge_presence = True  # "Q[" in headers
            discharge_index = [i for i, s in enumerate(headers) if 'Q[' in s][0]
            start = headers[discharge_index].find('Q[') + len('Q[')
            end = headers[discharge_index].find(']', start)
            discharge_unit = headers[discharge_index][start:end]
            # sort by discharge if not done
            data_index_file = sort_homogoeneous_dict_list_by_on_key(data_index_file,
                                                  headers[discharge_index], data_type=float)
        if any("T[" in s for s in headers):
            time_presence = True  # "T[" in headers
            time_index = [i for i, s in enumerate(headers) if 'T[' in s][0]
            start = headers[time_index].find('T[') + len('T[')
            end = headers[time_index].find(']', start)
            time_unit = headers[time_index][start:end]
        if any("reachname" in s for s in headers):
            reach_presence = True  # "reachname" in headers
            reach_index = [i for i, s in enumerate(headers) if 'reachname' in s][0]

        """ CHECK CASE """
        if not more_than_one_file_selected_by_user and discharge_presence and not time_presence:
            hydrau_case = "1.a"
        if not more_than_one_file_selected_by_user and discharge_presence and time_presence:
            hydrau_case = "1.b"
        if more_than_one_file_selected_by_user and discharge_presence and not time_presence:
            hydrau_case = "2.a"
        if more_than_one_file_selected_by_user and discharge_presence and time_presence:
            hydrau_case = "2.b"
        if not more_than_one_file_selected_by_user and not discharge_presence and time_presence:
            if data_index_file[headers[time_index]][0] == "all":
                hydrau_case = "3.a"
            if data_index_file[headers[time_index]][0] != "all":
                hydrau_case = "3.b"
        if more_than_one_file_selected_by_user and not discharge_presence and time_presence:
            if data_index_file[headers[time_index]][0] == "all":
                hydrau_case = "4.a"
            if data_index_file[headers[time_index]][0] != "all":
                hydrau_case = "4.b"

        # print("hydrau_case", hydrau_case)

        """ ALL CASE """
        # hdf5 name and source filenames
        if more_than_one_file_selected_by_user:
            # pathfile[0] = folder_path  # source file path
            if ext != ".txt":  # from file
                namefile = ", ".join(filename)  # source file name
                name_hdf5 = "_".join(blob).replace(".", "_") + ".hyd"
            if ext == ".txt":  # from indexHYDRAU.txt
                namefile = ", ".join(data_index_file["filename"])  # source file name
                name_hdf5 = "_".join([os.path.splitext(file)[0].replace(".", "_") for file in data_index_file["filename"]]) + ".hyd"
                if selectedfiles_textfiles_match and len(name_hdf5) > 25:
                    name_hdf5 = os.path.splitext(data_index_file["filename"][0])[0].replace(".", "_")  \
                                + "_to_" + \
                                os.path.splitext(data_index_file["filename"][-1])[0].replace(".", "_") + ".hyd"
        if not more_than_one_file_selected_by_user:
            if ext != ".txt":  # from file
                namefile = filename  # source file name
                name_hdf5 = os.path.splitext(filename)[0].replace(".", "_") + ".hyd"
                # if model_type == 'RUBAR20':
                #     namefile = os.path.splitext(namefile)[0]
            if ext == ".txt":  # from indexHYDRAU.txt
                namefile = data_index_file["filename"][0]  # source file name
                name_hdf5 = os.path.splitext(data_index_file["filename"][0])[0].replace(".", "_") + ".hyd"
        if model_type == 'RUBAR20':
            data_index_file[headers[0]] = [namefile]

        # hydrau_description
        hydrau_description = dict(path_prj=path_prj,
                                  name_prj=name_prj,
                                  hydrau_case=hydrau_case,
                                  filename_source=namefile,
                                  path_filename_source=folder_path,
                                  hdf5_name=name_hdf5,
                                  model_type=model_type,
                                  model_dimension=str(nb_dim),
                                  epsg_code=epsg_code,
                                  index_hydrau=True)

        """ CASE 1.a """
        if hydrau_case == "1.a":
            # get units name from file
            filename_path = os.path.join(folder_path, data_index_file["filename"][0])
            unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
            warning_list.extend(warning_list_timestep)
            # get units name from indexHYDRAU.txt file
            unit_name_from_index_file = data_index_file[headers[discharge_index]]
            # check if lenght of two loading units
            if len(unit_name_from_file) > len(unit_name_from_index_file):
                return "Error: units number from indexHYDRAU inferior than TELEMAC selected.", None

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # items
            if len(unit_name_from_file) == len(unit_name_from_index_file):
                pass
            if len(unit_name_from_file) < len(unit_name_from_index_file):
                index_file = data_index_file[headers[0]].index(filename)
                data_index_file[headers[0]] = [data_index_file[headers[0]][index_file]]
                data_index_file[headers[discharge_index]] = [data_index_file[headers[discharge_index]][index_file]]

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_full"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_tf"] = []
            hydrau_description["unit_number"] = str(1)
            hydrau_description["unit_type"] = "discharge [" + discharge_unit + "]"
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "continuous flow"  # transient flow

        """ CASE 1.b """
        if hydrau_case == "1.b":
            # get units name from file
            filename_path = os.path.join(folder_path, namefile)
            unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
            warning_list.extend(warning_list_timestep)
            # get units name from indexHYDRAU.txt file
            filename = namefile
            unit_name_from_index_file = data_index_file[headers[time_index]][data_index_file[headers[0]].index(filename)]

            # check if lenght of two loading units
            if unit_name_from_index_file not in unit_name_from_file:
                return "Error: " + unit_name_from_index_file + " doesn't exist in telemac file", None
            # else:
            #     unit_index = unit_name_from_file.index(unit_name_from_index_file)
            #     unit_list_tf = [False] * nbtimes
            #     unit_list_tf[unit_index] = True

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            else:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["unit_list"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_full"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_tf"] = [True] * len(data_index_file[headers[discharge_index]])
            hydrau_description["unit_number"] = str(1)
            hydrau_description["unit_type"] = "discharge [" + discharge_unit + "]"
            hydrau_description["timestep_list"] = data_index_file[headers[time_index]]
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "continuous flow"  # transient flow

        """ CASE 2.a """
        if hydrau_case == "2.a":
            # get units name from files (must have only one time step by file)
            for file in data_index_file["filename"]:
                filename_path = os.path.join(folder_path, file)
                unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
                warning_list.extend(warning_list_timestep)
                if unit_name_from_file == ["0.0"] and nbtimes == 1:
                    pass
                else:
                    if nbtimes > 1:
                        return "Error: file " + file + " contain more than one time step (timestep :" \
                               + str(unit_name_from_file) + ")", None

            # selected files same than indexHYDRAU file
            if not selectedfiles_textfiles_matching:

                pass
                # return "Error: selected files are different from indexHYDRAU files", None

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # # check if selected files are equal to data_index_file
            # if len(filename_list) != len(data_index_file["filename"]):
            #     for index, selected_file in enumerate(data_index_file["filename"]):


                # index_to_keep = []
                # for index, selected_file in enumerate(data_index_file["filename"]):
                #     if selected_file in [os.path.basename(element) for element in filename_list]:
                #         index_to_keep.append(index)
                # for header in headers:
                #     data_index_file[header] = [data_index_file[header][index] for index in index_to_keep]

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_full"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_tf"] = selectedfiles_textfiles_match
            hydrau_description["unit_number"] = str(selectedfiles_textfiles_match.count(True))
            hydrau_description["unit_type"] = "discharge [" + discharge_unit + "]"
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "continuous flow"  # transient flow

        """ CASE 2.b """
        if hydrau_case == "2.b":
            for rowindex, file in enumerate(data_index_file["filename"]):
                # get units name from file
                filename_path = os.path.join(folder_path, file)
                unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
                warning_list.extend(warning_list_timestep)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[time_index]][rowindex]
                # check if lenght of two loading units
                if unit_name_from_index_file not in unit_name_from_file:
                    return "Error: " + unit_name_from_index_file + " don't exist in " + file, None

            # selected files same than indexHYDRAU file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexHYDRAU files", None

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_full"] = data_index_file[headers[discharge_index]]
            hydrau_description["unit_list_tf"] = [True] * len(data_index_file[headers[discharge_index]])
            hydrau_description["unit_number"] = str(len(data_index_file[headers[discharge_index]]))
            hydrau_description["unit_type"] = "discharge [" + discharge_unit + "]"
            hydrau_description["timestep_list"] = data_index_file[headers[time_index]]
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "continuous flow"  # transient flow

        """ CASE 3.a """
        if hydrau_case == "3.a":
            # get units name from file
            filename_path = os.path.join(folder_path, data_index_file[headers[0]][0])
            unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
            warning_list.extend(warning_list_timestep)
            # selected files same than indexHYDRAU file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexHYDRAU files", None

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            unit_index_from_file = [True] * nbtimes

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = unit_name_from_file
            hydrau_description["unit_list_full"] = unit_name_from_file
            hydrau_description["unit_list_tf"] = unit_index_from_file
            hydrau_description["unit_number"] = str(nbtimes)
            hydrau_description["unit_type"] = "time [" + time_unit + "]"
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "transient flow"  # continuous flow

        """ CASE 3.b """
        if hydrau_case == "3.b":
            # get units name from file
            filename_path = os.path.join(folder_path, data_index_file[headers[0]][0])
            unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
            warning_list.extend(warning_list_timestep)

            # get units name from indexHYDRAU.txt file
            unit_name_from_index_file = data_index_file[headers[time_index]][0]

            unit_name_from_index_file2 = []
            for element_unit in unit_name_from_index_file.split(";"):
                if "/" in element_unit:  # from to
                    from_unit, to_unit = element_unit.split("/")
                    try:
                        from_unit_index = unit_name_from_file.index(from_unit)
                        to_unit_index = unit_name_from_file.index(to_unit)
                        unit_name_from_index_file2 = unit_name_from_index_file2 + \
                                                     unit_name_from_file[
                                                     from_unit_index:to_unit_index + 1]
                    except ValueError:
                        return "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                               data_index_file[headers[0]][0], None
                else:
                    unit_name_from_index_file2.append(element_unit)
            timestep_to_select = []
            for timestep_value in unit_name_from_file:
                if timestep_value in unit_name_from_index_file2:
                    timestep_to_select.append(True)
                else:
                    timestep_to_select.append(False)

            # selected files same than indexHYDRAU file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexHYDRAU files", None

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = unit_name_from_index_file2
            hydrau_description["unit_list_full"] = unit_name_from_file
            hydrau_description["unit_list_tf"] = timestep_to_select
            hydrau_description["unit_number"] = str(len(unit_name_from_index_file2))
            hydrau_description["unit_type"] = "time [" + time_unit + "]"
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "transient flow"  # continuous flow

        """ CASE 4.a """
        if hydrau_case == "4.a":
            # selected files same than indexHYDRAU file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexHYDRAU files", None

            # hydrau_description for several file
            hydrau_description_multiple = []
            for i, file in enumerate(data_index_file[headers[0]]):
                # get units name from file
                filename_path = os.path.join(folder_path, file)
                unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
                warning_list.extend(warning_list_timestep)
                unit_index_from_file = [True] * nbtimes
                # hdf5 filename
                blob2, ext = os.path.splitext(file)
                name_hdf5 = blob2 + ".hyd"

                # reach name
                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][i]
                if not reach_presence:
                    reach_name = "unknown"
                # multi description
                hydrau_description_multiple.append(dict(path_prj=path_prj,
                                                        name_prj=name_prj,
                                                        hydrau_case=hydrau_case,
                                                        filename_source=file,
                                                        path_filename_source=folder_path,
                                                        hdf5_name=name_hdf5,
                                                        model_type=model_type,
                                                        model_dimension=str(nb_dim),
                                                        epsg_code=epsg_code,
                                                        unit_list=unit_name_from_file,
                                                        unit_list_full=unit_name_from_file,
                                                        unit_list_tf=unit_index_from_file,
                                                        unit_number=str(nbtimes),
                                                        unit_type="time [" + time_unit + "]",
                                                        reach_list=reach_name,
                                                        reach_number=str(1),
                                                        reach_type="river",
                                                        flow_type="transient flow",
                                                        index_hydrau=True))  # continuous flow

            # set actual hydrau_description
            hydrau_description = hydrau_description_multiple

        """ CASE 4.b """
        if hydrau_case == "4.b":
            # selected files same than indexHYDRAU file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexHYDRAU files", None

            # hydrau_description for several file
            hydrau_description_multiple = []

            for i, file in enumerate(data_index_file[headers[0]]):
                # get units name from file
                filename_path = os.path.join(folder_path, file)
                unit_type, nbtimes, unit_name_from_file, warning_list_timestep = get_time_step(filename_path, model_type)
                warning_list.extend(warning_list_timestep)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[time_index]][i]
                unit_name_from_index_file2 = []
                for element_unit in unit_name_from_index_file.split(";"):
                    if "/" in element_unit:  # from to
                        from_unit, to_unit = element_unit.split("/")
                        try:
                            from_unit_index = unit_name_from_file.index(from_unit)
                            to_unit_index = unit_name_from_file.index(to_unit)
                            unit_name_from_index_file2 = unit_name_from_index_file2 + \
                                                         unit_name_from_file[
                                                         from_unit_index:to_unit_index + 1]
                        except ValueError:

                            return "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                                   data_index_file[headers[0]][i], None
                    else:
                        unit_name_from_index_file2.append(element_unit)

                unit_index_from_file = []
                for item in unit_name_from_file:
                    if item in unit_name_from_index_file2:
                        unit_index_from_file.append(True)
                    else:
                        unit_index_from_file.append(False)

                # hdf5 filename
                blob2, ext = os.path.splitext(file)
                name_hdf5 = blob2 + ".hyd"
                # reach name
                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][i]
                if not reach_presence:
                    reach_name = "unknown"
                # multi description
                hydrau_description_multiple.append(dict(path_prj=path_prj,
                                                        name_prj=name_prj,
                                                        hydrau_case=hydrau_case,
                                                        filename_source=file,
                                                        path_filename_source=folder_path,
                                                        hdf5_name=name_hdf5,
                                                        model_type=model_type,
                                                        model_dimension=str(nb_dim),
                                                        epsg_code=epsg_code,
                                                        unit_list=unit_name_from_index_file2,
                                                        unit_list_full=unit_name_from_file,
                                                        unit_list_tf=unit_index_from_file,
                                                        unit_number=str(len(unit_name_from_index_file2)),
                                                        unit_type="time [" + time_unit + "]",
                                                        reach_list=reach_name,
                                                        reach_number=str(1),
                                                        reach_type="river",
                                                        flow_type="transient flow",
                                                        index_hydrau=True))  # continuous flow

            # set actual hydrau_description
            hydrau_description = hydrau_description_multiple

    # if m3/s
    if type(hydrau_description) == list:
        for hydrau_description_index in range(len(hydrau_description)):
            if "m3/s" in hydrau_description[hydrau_description_index]["unit_type"]:
                hydrau_description[hydrau_description_index]["unit_type"] = hydrau_description[hydrau_description_index]["unit_type"].replace("m3/s", "m<sup>3</sup>/s")
    if type(hydrau_description) == dict:
            if "m3/s" in hydrau_description["unit_type"]:
                hydrau_description["unit_type"] = hydrau_description["unit_type"].replace("m3/s", "m<sup>3</sup>/s")

    print("hydrau_case, " + hydrau_case)
    return hydrau_description, warning_list


def create_index_hydrau_text_file(description_from_indexHYDRAU_file):
    """ ONE HDF5 """
    # one case (one hdf5 produced)
    if len(description_from_indexHYDRAU_file) == 1:
        filename_path = os.path.join(description_from_indexHYDRAU_file[0]["path_prj"], "input", "indexHYDRAU.txt")
        # telemac case
        telemac_case = description_from_indexHYDRAU_file[0]["hydrau_case"]

        # column filename
        filename_column = description_from_indexHYDRAU_file[0]["filename_source"].split(", ")

        # nb_row
        nb_row = len(filename_column)

        """ CASE unknown """
        if telemac_case == "unknown":
            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            time_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]

            # headers
            headers = "filename" + "\t" + "T[" + time_unit + "]"

            # first line
            if description_from_indexHYDRAU_file[0]["unit_list"] == \
                    description_from_indexHYDRAU_file[0]["unit_list_full"]:
                unit_data = "all"
            else:
                index = [i for i, item in enumerate(description_from_indexHYDRAU_file[0]["unit_list_full"]) if
                         item in description_from_indexHYDRAU_file[0]["unit_list"]]
                my_sequences = []
                for idx, item in enumerate(index):
                    if not idx or item - 1 != my_sequences[-1][-1]:
                        my_sequences.append([item])
                    else:
                        my_sequences[-1].append(item)
                from_to_string_list = []
                for sequence in my_sequences:
                    start = min(sequence)
                    start_string = description_from_indexHYDRAU_file[0]["unit_list_full"][start]
                    end = max(sequence)
                    end_string = description_from_indexHYDRAU_file[0]["unit_list_full"][end]
                    if start == end:
                        start_end_string = start_string
                    if start != end:
                        start_end_string = start_string + "/" + end_string
                    from_to_string_list.append(start_end_string)
                unit_data = ";".join(from_to_string_list)
            linetowrite = filename_column[0] + "\t" + unit_data

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 1.a """
        if telemac_case == "1.a":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # first line
            linetowrite = filename_column[0] + "\t" + str(description_from_indexHYDRAU_file[0]["unit_list"][0])
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 1.b """
        if telemac_case == "1.b":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]" + "\t" + "T[s]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # first line
            linetowrite = filename_column[0] + "\t" + str(description_from_indexHYDRAU_file[0]["unit_list"][0])
            linetowrite = linetowrite + "\t" + description_from_indexHYDRAU_file[0]["unit_list_full"][0]
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column
            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 2.a """
        if telemac_case == "2.a":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # lines
            linetowrite = ""
            for row in range(nb_row):
                if description_from_indexHYDRAU_file[0]["unit_list_tf"][row]:
                    linetowrite += filename_column[row] + "\t" + str(description_from_indexHYDRAU_file[0]["unit_list_full"][row])
                    if reach_column_presence:
                        linetowrite = linetowrite + "\t" + reach_column + "\n"
                    else:
                        linetowrite = linetowrite + "\n"
            # remove last "\n"
            linetowrite = linetowrite[:-1]

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 2.b """
        if telemac_case == "2.b":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]" + "\t" + "T[s]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # lines
            linetowrite = ""
            for row in range(nb_row):
                linetowrite += filename_column[row] + "\t" + str(
                    description_from_indexHYDRAU_file[0]["unit_list"][row]) + "\t" + description_from_indexHYDRAU_file[0]["timestep_list"][row]
                if reach_column_presence:
                    linetowrite = linetowrite + "\t" + reach_column + "\n"
                else:
                    linetowrite = linetowrite + "\n"
            # remove last "\n"
            linetowrite = linetowrite[:-1]

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 3.a 3.b """
        if telemac_case == "3.a" or telemac_case == "3.b":
            if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            time_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
            # headers
            headers = "filename" + "\t" + "T[" + time_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"

            # first line
            if description_from_indexHYDRAU_file[0]["unit_list"] == description_from_indexHYDRAU_file[0]["unit_list_full"]:
                unit_data = "all"
            else:
                index = [i for i, item in enumerate(description_from_indexHYDRAU_file[0]["unit_list_full"]) if item in description_from_indexHYDRAU_file[0]["unit_list"]]
                my_sequences = []
                for idx, item in enumerate(index):
                    if not idx or item - 1 != my_sequences[-1][-1]:
                        my_sequences.append([item])
                    else:
                        my_sequences[-1].append(item)
                from_to_string_list = []
                for sequence in my_sequences:
                    start = min(sequence)
                    start_string = description_from_indexHYDRAU_file[0]["unit_list_full"][start]
                    end = max(sequence)
                    end_string = description_from_indexHYDRAU_file[0]["unit_list_full"][end]
                    if start == end:
                        start_end_string = start_string
                    if start != end:
                        start_end_string = start_string + "/" + end_string
                    from_to_string_list.append(start_end_string)

                unit_data = ";".join(from_to_string_list)
            linetowrite = filename_column[0] + "\t" + unit_data
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column
            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        # write text file
        with open(filename_path, 'wt') as f:
            f.write(text)

    """ MULTI HDF5 """
    # multi case (several hdf5 produced)
    if len(description_from_indexHYDRAU_file) > 1:
        if description_from_indexHYDRAU_file[0]["reach_list"] == "unknown":
            reach_column_presence = False
        else:
            reach_column_presence = True
            reach_column = description_from_indexHYDRAU_file[0]["reach_list"].split(", ")[0]

        unit_type = description_from_indexHYDRAU_file[0]["unit_type"]
        start = unit_type.find('[')
        end = unit_type.find(']')
        time_unit = unit_type[start + 1:end]
        # epsg_code
        epsg_code = "EPSG=" + description_from_indexHYDRAU_file[0]["epsg_code"]
        # headers
        headers = "filename" + "\t" + "T[" + time_unit + "]"
        if reach_column_presence:
            headers = headers + "\t" + "reachname"

        # text
        text = epsg_code + "\n" + headers

        for i_hdf5, hdf5_file in enumerate(range(len(description_from_indexHYDRAU_file))):
            filename_path = os.path.join(description_from_indexHYDRAU_file[i_hdf5]["path_prj"], "input", "indexHYDRAU.txt")
            # telemac case
            telemac_case = description_from_indexHYDRAU_file[i_hdf5]["hydrau_case"]

            # column filename
            filename_column = description_from_indexHYDRAU_file[i_hdf5]["filename_source"].split(", ")

            if telemac_case == "4.a" or telemac_case == "4.b" or telemac_case == "unknown":
                if description_from_indexHYDRAU_file[i_hdf5]["reach_list"] == "unknown":
                    reach_column_presence = False
                else:
                    reach_column_presence = True
                    reach_column = description_from_indexHYDRAU_file[i_hdf5]["reach_list"].split(", ")[0]

                # first line
                if description_from_indexHYDRAU_file[i_hdf5]["unit_list"] == description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"]:
                    unit_data = "all"
                else:
                    index = [i for i, item in enumerate(description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"]) if item in description_from_indexHYDRAU_file[i_hdf5]["unit_list"]]
                    my_sequences = []
                    for idx, item in enumerate(index):
                        if not idx or item - 1 != my_sequences[-1][-1]:
                            my_sequences.append([item])
                        else:
                            my_sequences[-1].append(item)
                    from_to_string_list = []
                    for sequence in my_sequences:
                        start = min(sequence)
                        start_string = description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"][start]
                        end = max(sequence)
                        end_string = description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"][end]
                        if start == end:
                            start_end_string = start_string
                        if start != end:
                            start_end_string = start_string + "/" + end_string
                        from_to_string_list.append(start_end_string)

                    unit_data = ";".join(from_to_string_list)
                linetowrite = filename_column[0] + "\t" + unit_data
                if reach_column_presence:
                    linetowrite = linetowrite + "\t" + reach_column

                text = text + "\n" + linetowrite

        # write text file
        with open(filename_path, 'wt') as f:
            f.write(text)


def get_sub_description_from_source(filename_path, substrate_mapping_method, path_prj):
    warning_list = []  # text warning output
    name_prj = os.path.splitext(os.path.basename(path_prj))[0]
    substrate_classification_code = None
    substrate_classification_method = None
    substrate_default_values = None
    epsg_code = None
    substrate_classification_codes = ['Cemagref', 'Sandre']
    substrate_classification_methods = ['coarser-dominant', 'percentage']

    dirname = os.path.dirname(filename_path)
    filename = os.path.basename(filename_path)
    blob, ext = os.path.splitext(filename)

    # POLYGON
    if substrate_mapping_method == "polygon":
        # check classification code in .txt (polygon or point shp)
        if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
            warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                            "The selected shapefile is not accompanied by its habby .txt file."))
            return False, warning_list

        if ext == ".shp":
            # get type shapefile
            driver = GetDriverByName('ESRI Shapefile')  # Shapefile
            ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.
        elif ext == ".gpkg":
            # get type shapefile
            driver = GetDriverByName('GPKG')  # GPKG
            ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.

        # get layer
        layer = ds.GetLayer(0)  # one layer in shapefile but can be multiple in gpkg..

        # get geom type
        if layer.GetGeomType() not in polygon_type_values:
            # get the first feature
            feature = layer.GetNextFeature()
            geom_type = feature.GetGeometryRef().GetGeometryName()
            warning_list.append(
                "Error : " + qt_tr.translate("hydro_input_file_mod",
                                             "Selected shapefile is not polygon type. Type : " + geom_type))
            return False, warning_list

        if os.path.isfile(os.path.join(dirname, blob + ".txt")):
            with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                dataraw = f.read()
            substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                "\n")
            if "substrate_classification_code=" in substrate_classification_code_raw:
                substrate_classification_code = \
                    substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                if substrate_classification_code not in substrate_classification_codes:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification code in .txt file is not recognized : ")
                                        + substrate_classification_code)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_code=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "substrate_classification_method=" in substrate_classification_method_raw:
                substrate_classification_method = \
                    substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                if substrate_classification_method not in substrate_classification_methods:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification method in .txt file is not recognized : ")
                                        + substrate_classification_method)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_method=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "default_values=" in substrate_default_values_raw:
                substrate_default_values = substrate_default_values_raw.split("default_values=")[1].strip()
                constant_values_list = substrate_default_values.split(",")
                for value in constant_values_list:
                    try:
                        int(value.strip())
                    except:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "Default values can't be converted to integer : ")
                                            + substrate_default_values)
                        return False, warning_list
            else:
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'default_values=' is not found in"
                                                                        " .txt file."))
                return False, warning_list

        # check EPSG code in .prj
        if not os.path.isfile(os.path.join(dirname, blob + ".prj")) and ext == ".shp":
            warning_list.append(
                "Warning: The selected shapefile is not accompanied by its .prj file. EPSG code is unknwon.")
            epsg_code = "unknown"
        else:
            inSpatialRef = layer.GetSpatialRef()
            sr = SpatialReference(str(inSpatialRef))
            res = sr.AutoIdentifyEPSG()
            epsg_code_str = sr.GetAuthorityCode(None)
            if epsg_code_str:
                epsg_code = epsg_code_str
            else:
                epsg_code = "unknown"

    # POINT
    if substrate_mapping_method == "point":
        # txt case
        if ext == ".txt":
            if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The selected file don't exist."))
                return False, warning_list
            with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                dataraw = f.read()
            if len(dataraw.split("\n")[:4]) < 4:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "This text file is not a valid point substrate."))
                return False, warning_list
            epsg_raw, substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                "\n")[:4]
            # check EPSG in .txt (polygon or point shp)
            if "EPSG=" in epsg_raw:
                epsg_code = epsg_raw.split("EPSG=")[1].strip()
            else:
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'EPSG=' is not found in .txt file."))
                return False, warning_list
            # check classification code in .txt ()
            if "substrate_classification_code=" in substrate_classification_code_raw:
                substrate_classification_code = \
                    substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                if substrate_classification_code not in substrate_classification_codes:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification code in .txt file is not recognized : ")
                                        + substrate_classification_code)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_code=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "substrate_classification_method=" in substrate_classification_method_raw:
                substrate_classification_method = \
                    substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                if substrate_classification_method not in substrate_classification_methods:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The classification method in .txt file is not recognized : ")
                        + substrate_classification_method)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_method=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "default_values=" in substrate_default_values_raw:
                substrate_default_values = substrate_default_values_raw.split("default_values=")[1].strip()
                constant_values_list = substrate_default_values.split(",")
                for value in constant_values_list:
                    try:
                        int(value.strip())
                    except:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "Default values can't be converted to integer : ")
                                            + substrate_default_values)
                        return False, warning_list
            else:
                warning_list.append(
                    "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'default_values=' is not found in"
                                                                        " .txt file."))
                return False, warning_list

        if ext == ".shp" or ext == ".gpkg":
            # check classification code in .txt (polygon or point shp)
            if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The selected shapefile is not accompanied by its habby .txt file."))
                return False, warning_list

            if ext == ".shp":
                # get type shapefile
                driver = GetDriverByName('ESRI Shapefile')  # Shapefile
                ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.
            elif ext == ".gpkg":
                # get type shapefile
                driver = GetDriverByName('GPKG')  # GPKG
                ds = driver.Open(os.path.join(dirname, filename), 0)  # 0 means read-only. 1 means writeable.

            layer = ds.GetLayer(0)  # one layer in shapefile but can be multiple in gpkg..

            # get geom type
            if layer.GetGeomType() not in point_type_values:  # point type
                # get the first feature
                feature = layer.GetNextFeature()
                geom_type = feature.GetGeometryRef().GetGeometryName()
                warning_list.append(
                    "Error : " + qt_tr.translate("hydro_input_file_mod",
                                                 "Selected shapefile is not point type. Type : " + geom_type))
                return False, warning_list

            else:
                with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                    dataraw = f.read()
                substrate_classification_code_raw, substrate_classification_method_raw, substrate_default_values_raw = dataraw.split(
                    "\n")
                if "substrate_classification_code=" in substrate_classification_code_raw:
                    substrate_classification_code = \
                        substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                    if substrate_classification_code not in substrate_classification_codes:
                        warning_list.append(
                            "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                        "The classification code in .txt file is not recognized : ")
                            + substrate_classification_code)
                        return False, warning_list
                else:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The name 'substrate_classification_code=' is not found in"
                                                    " .txt file."))
                    return False, warning_list
                if "substrate_classification_method=" in substrate_classification_method_raw:
                    substrate_classification_method = \
                        substrate_classification_method_raw.split("substrate_classification_method=")[
                            1].strip()
                    if substrate_classification_method not in substrate_classification_methods:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "The classification method in .txt file is not recognized : ")
                                            + substrate_classification_method)
                        return
                else:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The name 'substrate_classification_method=' is not found in"
                                                    " .txt file."))
                    return False, warning_list
                if "default_values=" in substrate_default_values_raw:
                    substrate_default_values = substrate_default_values_raw.split("default_values=")[
                        1].strip()
                    constant_values_list = substrate_default_values.split(",")
                    for value in constant_values_list:
                        try:
                            int(value.strip())
                        except:
                            warning_list.append(
                                "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                            "Default values can't be converted to integer : ")
                                + substrate_default_values)
                            return False, warning_list
                else:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod", "The name 'default_values=' is not found in"
                                                                            " .txt file."))
                    return False, warning_list

            # check EPSG code in .prj
            if not os.path.isfile(os.path.join(dirname, blob + ".prj")) and ext == ".shp":
                warning_list.append(
                    "Warning: The selected shapefile is not accompanied by its .prj file. EPSG code is unknwon.")
                epsg_code = "unknown"
            else:
                inSpatialRef = layer.GetSpatialRef()
                sr = SpatialReference(str(inSpatialRef))
                res = sr.AutoIdentifyEPSG()
                epsg_code_str = sr.GetAuthorityCode(None)
                if epsg_code_str:
                    epsg_code = epsg_code_str
                else:
                    epsg_code = "unknown"

    # CONSTANT
    if substrate_mapping_method == "constant":
        epsg_code = "unknown"
        # txt
        if not os.path.isfile(os.path.join(dirname, blob + ".txt")):
            warning_list.append(
                "Error: " + qt_tr.translate("hydro_input_file_mod", "The selected text file don't exist."))
            return False, warning_list
        if os.path.isfile(os.path.join(dirname, blob + ".txt")):
            with open(os.path.join(dirname, blob + ".txt"), 'rt') as f:
                dataraw = f.read()
            substrate_classification_code_raw, substrate_classification_method_raw, constant_values_raw = dataraw.split(
                "\n")
            # classification code
            if "substrate_classification_code=" in substrate_classification_code_raw:
                substrate_classification_code = \
                    substrate_classification_code_raw.split("substrate_classification_code=")[1].strip()
                if substrate_classification_code not in substrate_classification_codes:
                    warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                    "The classification code in .txt file is not recognized : ")
                                        + substrate_classification_code)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_code=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            if "substrate_classification_method=" in substrate_classification_method_raw:
                substrate_classification_method = \
                    substrate_classification_method_raw.split("substrate_classification_method=")[1].strip()
                if substrate_classification_method not in substrate_classification_methods:
                    warning_list.append(
                        "Error: " + qt_tr.translate("hydro_input_file_mod",
                                                    "The classification method in .txt file is not recognized : ")
                        + substrate_classification_method)
                    return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'substrate_classification_method=' is not found in"
                                                                " .txt file."))
                return False, warning_list
            # constant values
            if "constant_values=" in constant_values_raw:
                substrate_default_values = constant_values_raw.split("constant_values=")[1].strip()
                substrate_default_values_list = substrate_default_values.split(",")
                for value in substrate_default_values_list:
                    try:
                        int(value.strip())
                    except:
                        warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                        "Constant values can't be converted to integer : ")
                                            + substrate_default_values)
                        return False, warning_list
            else:
                warning_list.append("Error: " + qt_tr.translate("hydro_input_file_mod",
                                                                "The name 'constant_values=' is not found in .txt file."))
                return False, warning_list

    # create dict
    sub_description = dict(sub_mapping_method=substrate_mapping_method,
                            sub_classification_code=substrate_classification_code,
                           sub_classification_method=substrate_classification_method,
                           sub_default_values=substrate_default_values,
                           sub_epsg_code=epsg_code,
                           sub_filename_source=filename,
                           sub_path_source=dirname,
                           sub_reach_number="1",
                           sub_reach_list="unknown",
                           sub_unit_number="1",
                           sub_unit_list="0.0",
                           sub_unit_type="unknown",
                           name_prj=name_prj,
                           path_prj=path_prj
                           )

    return sub_description, warning_list


def get_time_step(file_path, model_type):
    """
    models type list : HECRAS1D, RUBAR2D, MASCARET, RIVER2D, RUBAR1D, HECRAS2D, TELEMAC, LAMMI, SW2D, IBER2D
    :param file_path:
    :param model_type:
    :return:
    """
    nbtimes = False
    unit_name_from_file = False
    warning_list = []
    filename = os.path.basename(file_path)
    folder_path = os.path.dirname(file_path)
    if model_type == "TELEMAC":
        unit_type = "time [s]"
        nbtimes, unit_name_from_file = telemac_mod.get_time_step(filename, folder_path)
    elif model_type == "HECRAS2D":
        unit_type = "Date []"
        nbtimes, unit_name_from_file = hec_ras2D_mod.get_time_step(file_path)
    elif model_type == "HECRAS1D":
        unit_type = "Date []"
        nbtimes, unit_name_from_file = hec_ras1D_mod.get_time_step(file_path)
    elif model_type == "RUBAR20":
        unit_type = "time [s]"
        nbtimes, unit_name_from_file, warning_list = rubar1d2d_mod.get_time_step(filename, folder_path)
    elif model_type == "BASEMENT2D":
        unit_type = "time [s]"
        nbtimes, unit_name_from_file, warning_list = basement_mod.get_time_step(filename, folder_path)
    return unit_type, nbtimes, unit_name_from_file, warning_list


def load_hydraulic_cut_to_hdf5(hydrau_description, progress_value, q=[], print_cmd=False, project_preferences={}):
    """
    This function calls the function load_hydraulic and call the function cut_2d_grid()

    :param name_hdf5: the base name of the created hdf5 (string)
    :param namefilet: the name of the selafin file (string)
    :param pathfilet: the path to this file (string)
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param model_type: the name of the model such as Rubar, hec-ras, etc. (string)
    :param nb_dim: the number of dimension (model, 1D, 1,5D, 2D) in a float
    :param path_hdf5: A string which gives the adress to the folder in which to save the hdf5
    :param units_index : List of integer values representing index of units (timestep or discharge). If not specify,
            all timestep are selected (from cmd command).
    :param q: used by the second thread to get the error back to the GUI at the end of the thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param project_preferences: the figure option, used here to get the minimum water height to have a wet node (can be > 0)
    """
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_properties_dict()

    # progress
    progress_value.value = 10

    # check if hydrau_description_multiple
    if type(hydrau_description) == dict:  # hydrau_description simple (one .hyd)
        file_number = 1
        hydrau_description = [hydrau_description]
    elif type(hydrau_description) == list:  # hydrau_description_multiple (several .hyd)
        file_number = len(hydrau_description)

    # for reach .hyd to create
    for hyd_file in range(0, file_number):
        # get filename source (can be several)
        filename_source = hydrau_description[hyd_file]["filename_source"].split(", ")

        # create data_2d_whole_profile
        data_2d_whole_profile = create_empty_data_2d_whole_profile_dict(1)  # always one reach by file
        hydrau_description[hyd_file]["unit_correspondence"] = [[]]  # always one reach by file

        # for each filename source
        for i, file in enumerate(filename_source):
            # load data2d
            data_2d_source, description_from_source = load_hydraulic(file,
                                                                     hydrau_description[hyd_file]["path_filename_source"],
                                                                     hydrau_description[hyd_file]["model_type"])
            if not data_2d_source and not description_from_source:
                q.put(mystdout)
                return
            data_2d_whole_profile["mesh"]["tin"][0].append(data_2d_source["mesh"]["tin"][0])
            data_2d_whole_profile["node"]["xy"][0].append(data_2d_source["node"]["xy"][0])
            if description_from_source["unit_z_equal"]:
                data_2d_whole_profile["node"]["z"][0].append(data_2d_source["node"]["z"][0])
            elif not description_from_source["unit_z_equal"]:
                for unit_num in range(len(hydrau_description[hyd_file]["unit_list"])):
                    data_2d_whole_profile["node"]["z"][0].append(data_2d_source["node"]["z"][0][unit_num])

        # create temporary list sorted to check if the whole profiles are equal to the first one (sort xy_center)
        temp_list = deepcopy(data_2d_whole_profile["node"]["xy"][0])
        for i in range(len(temp_list)):
            temp_list[i].sort(axis=0)
        # TODO: sort function may be unadapted to check TIN equality between units
        whole_profil_egual_index = []
        it_equality = 0
        for i in range(len(temp_list)):
            if i == 0:
                whole_profil_egual_index.append(it_equality)
            if i > 0:
                if np.array_equal(temp_list[i], temp_list[it_equality]):  # equal
                    whole_profil_egual_index.append(it_equality)
                else:
                    it_equality = i
                    whole_profil_egual_index.append(it_equality)  # diff
        hydrau_description[hyd_file]["unit_correspondence"][0] = whole_profil_egual_index
        # one file : one reach, varying_mesh==False
        if len(filename_source) == 1:
            hydrau_description[hyd_file]["unit_correspondence"][0] = whole_profil_egual_index * int(
                hydrau_description[hyd_file]["unit_number"])
        # one tin for all unit
        if len(set(whole_profil_egual_index)) == 1:
            data_2d_whole_profile["mesh"]["tin"][0] = [data_2d_whole_profile["mesh"]["tin"][0][0]]
            data_2d_whole_profile["node"]["xy"][0] = [data_2d_whole_profile["node"]["xy"][0][0]]

        # progress from 10 to 90 : from 0 to len(units_index)
        delta = int(80 / int(hydrau_description[hyd_file]["unit_number"]))

        # cut the grid to have the precise wet area and put data in new form
        data_2d = create_empty_data_2d_dict(1,  # always one reach
                                            mesh_variables=list(data_2d_source["mesh"]["data"].keys()),
                                            node_variables=list(data_2d_source["node"]["data"].keys()))

        # get unit list from filename_source
        file_list = hydrau_description[hyd_file]["filename_source"].split(", ")
        if len(file_list) > 1:
            unit_number_list = []
            unit_list_from_source_file_list = []
            for file_indexHYDRAU in file_list:
                unit_type, unit_number, unit_list_from_source_file, warning_list = get_time_step(
                    os.path.join(hydrau_description[hyd_file]["path_filename_source"], file_indexHYDRAU),
                    hydrau_description[hyd_file]["model_type"])
                unit_number_list.append(unit_number)
                unit_list_from_source_file_list.append(unit_list_from_source_file)
        if len(file_list) == 1:
            unit_type, unit_number, unit_list_from_source_file, warning_list = get_time_step(
                os.path.join(hydrau_description[hyd_file]["path_filename_source"], hydrau_description[hyd_file]["filename_source"]),
                hydrau_description[hyd_file]["model_type"])
        # get unit list from indexHYDRAU file
        if hydrau_description[hyd_file]["hydrau_case"] in {"1.b", "2.b"}:
            if len(hydrau_description[hyd_file]["timestep_list"]) == len(file_list):
                unit_list_from_indexHYDRAU_file = hydrau_description[hyd_file]["timestep_list"]
            else:
                unit_list_from_indexHYDRAU_file = hydrau_description[hyd_file]["timestep_list"]
        else:
            unit_list_from_indexHYDRAU_file = hydrau_description[hyd_file]["unit_list"]
        # get unit index to load
        if len(unit_list_from_source_file) == 1 and len(unit_list_from_indexHYDRAU_file) == 1:
            #unit_index_list = [0]
            unit_index_list = [0] * len(file_list)
            hydrau_description[hyd_file]["unit_list_tf"] = [True] * len(unit_index_list)
        else:
            if len(file_list) > 1:
                if list(set(unit_number_list))[0] == 1:  # one time step by file
                    unit_index_list = [0] * len(file_list)
                if list(set(unit_number_list))[0] > 1:  # several time step by file
                    unit_index_list = []
                    for i, time_step in enumerate(unit_list_from_indexHYDRAU_file):
                        if time_step in unit_list_from_source_file_list[i]:
                            unit_index_list.append(unit_list_from_source_file_list[i].index(time_step))
            else:
                unit_index_list = []  # for all cases with specific timestep indicate
                for unit_wish in unit_list_from_indexHYDRAU_file:
                    if unit_wish in unit_list_from_source_file:
                        unit_index_list.append(unit_list_from_source_file.index(unit_wish))

        # same mesh for all units : conca xy array with first z array
        if len(set(hydrau_description[hyd_file]["unit_correspondence"][0])) == 1:
            # conca xy with z value to facilitate the cutting of the grid (interpolation)
            xyz = np.insert(data_2d_source["node"]["xy"][0],
                           2,
                           values=data_2d_source["node"]["z"][0],
                           axis=1)  # Insert values before column 2
        else:
            data_2d_source, description_from_source = load_hydraulic(file,
                                                                     hydrau_description[hyd_file][
                                                                         "path_filename_source"],
                                                                     hydrau_description[hyd_file]["model_type"])

        for i, unit_num in enumerate(unit_index_list):
            if len(file_list) > 1:
                data_2d_source, description_from_source = load_hydraulic(file_list[i],
                                                                         hydrau_description[hyd_file][
                                                                             "path_filename_source"],
                                                                         hydrau_description[hyd_file]["model_type"])
                # conca xy with z value to facilitate the cutting of the grid (interpolation)
                xyz = np.insert(data_2d_source["node"]["xy"][0],
                               2,
                               values=data_2d_source["node"]["z"][0],  #
                               axis=1)  # Insert values before column 2

            # user GUI selection
            if hydrau_description[hyd_file]["unit_list_tf"][i]:
                tin_data, xyz_cuted, h_data, v_data, i_whole_profile = manage_grid_mod.cut_2d_grid(
                    data_2d_source["mesh"]["tin"][0],
                    xyz,
                    data_2d_source["node"]["data"]["h"][0][unit_num],
                    data_2d_source["node"]["data"]["v"][0][unit_num],
                    progress_value,
                    delta,
                    project_preferences["cut_mesh_partialy_dry"],
                    unit_num,
                    project_preferences['min_height_hyd'])

                if not isinstance(tin_data, np.ndarray):  # error or warning
                    if not tin_data:  # error
                        print("Error: " + qt_tr.translate("hydro_input_file_mod", "cut_2d_grid"))
                        q.put(mystdout)
                        return
                    elif tin_data:  # entierly dry
                        hydrau_description[hyd_file]["unit_list_tf"][unit_num] = False
                        continue  # Continue to next iteration.
                else:
                    # save data in dict
                    data_2d["mesh"]["tin"][0].append(tin_data)
                    data_2d["mesh"]["i_whole_profile"][0].append(i_whole_profile)
                    for mesh_variable in data_2d_source["mesh"]["data"].keys():
                        data_2d["mesh"]["data"][mesh_variable][0].append(
                            data_2d_source["mesh"]["data"][mesh_variable][0][unit_num][i_whole_profile])
                    data_2d["node"]["xy"][0].append(xyz_cuted[:, :2])
                    data_2d["node"]["z"][0].append(xyz_cuted[:, 2])
                    data_2d["node"]["data"]["h"][0].append(h_data)
                    data_2d["node"]["data"]["v"][0].append(v_data)

        # refresh unit (if warning)
        # for reach_num in reversed(range(int(hydrau_description[hyd_file]["reach_number"]))):  # for each reach
        #     for unit_num in reversed(range(len(hydrau_description[hyd_file]["unit_list"][reach_num]))):
        #         if not hydrau_description[hyd_file]["unit_list_tf"][reach_num][unit_num]:
        #             hydrau_description[hyd_file]["unit_list"][reach_num].pop(unit_num)
        # hydrau_description["unit_number"] = str(len(hydrau_description[hyd_file]["unit_list"][0]))

        # ALL CASE SAVE TO HDF5
        progress_value.value = 90  # progress

        # hyd description
        hyd_description = dict()
        hyd_description["hyd_filename_source"] = hydrau_description[hyd_file]["filename_source"]
        hyd_description["hyd_path_filename_source"] = hydrau_description[hyd_file]["path_filename_source"]
        hyd_description["hyd_model_type"] = hydrau_description[hyd_file]["model_type"]
        hyd_description["hyd_2D_numerical_method"] = "FiniteElementMethod"
        hyd_description["hyd_model_dimension"] = hydrau_description[hyd_file]["model_dimension"]
        hyd_description["hyd_mesh_variables_list"] = ", ".join(list(data_2d_source["mesh"]["data"].keys()))
        hyd_description["hyd_node_variables_list"] = ", ".join(list(data_2d_source["node"]["data"].keys()))
        hyd_description["hyd_epsg_code"] = hydrau_description[hyd_file]["epsg_code"]
        hyd_description["hyd_reach_list"] = hydrau_description[hyd_file]["reach_list"]
        hyd_description["hyd_reach_number"] = hydrau_description[hyd_file]["reach_number"]
        hyd_description["hyd_reach_type"] = hydrau_description[hyd_file]["reach_type"]
        hyd_description["hyd_unit_list"] = [[unit_name.replace(":", "_").replace(" ", "_") for unit_name in hydrau_description[hyd_file]["unit_list"]]]
        hyd_description["hyd_unit_number"] = str(len(hydrau_description[hyd_file]["unit_list"]))
        hyd_description["hyd_unit_type"] = hydrau_description[hyd_file]["unit_type"]
        hyd_description["unit_correspondence"] = hydrau_description[hyd_file]["unit_correspondence"]
        hyd_description["hyd_cuted_mesh_partialy_dry"] = project_preferences["cut_mesh_partialy_dry"]
        hyd_description["hyd_hydrau_case"] = hydrau_description[hyd_file]["hydrau_case"]
        if hyd_description["hyd_hydrau_case"] in {"1.b", "2.b"}:
            hyd_description["timestep_source_list"] = [hydrau_description[hyd_file]["timestep_list"]]

        # create hdf5
        hdf5 = hdf5_mod.Hdf5Management(hydrau_description[hyd_file]["path_prj"],
                                       hydrau_description[hyd_file]["hdf5_name"])
        hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description, project_preferences)

        # prog
        progress_value.value = 95

        # create_index_hydrau_text_file
        if not hydrau_description[hyd_file]["index_hydrau"]:
            create_index_hydrau_text_file(hydrau_description)

        # prog
        progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q and not print_cmd:
        q.put(mystdout)
        return
    else:
        return


def load_hydraulic(filename, folder_path, model_type):
    data_2d = None
    description_from_file = None
    if model_type == "TELEMAC":
        data_2d, description_from_file = telemac_mod.load_telemac(filename, folder_path)
    elif model_type == "HECRAS2D":
        data_2d, description_from_file = hec_ras2D_mod.load_hec_ras2d(filename, folder_path)
    elif model_type == "HECRAS1D":
        data_2d, description_from_file = hec_ras1D_mod.load_xml(filename, folder_path)
    elif model_type == "RUBAR20":
        data_2d, description_from_file = rubar1d2d_mod.load_rubar2d(filename, folder_path)
    return data_2d, description_from_file

