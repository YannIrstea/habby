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
from src import telemac_mod
from src import hec_ras2D_mod
from src import ascii_mod

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
    more_than_one_file_selected_by_user = False  # one file to read
    if len(filename_list) == 1:  # one file selected
        filename_path = os.path.normpath(filename_list[0])
        folder_path = os.path.dirname(filename_path)
        filename = os.path.basename(filename_path)
        blob, ext = os.path.splitext(filename)
    if len(filename_list) > 1:  # more than one file selected
        more_than_one_file_selected_by_user = True  # several files to read
        filename_path = filename_list
        folder_path = os.path.dirname(filename_path[0])
        filename = [os.path.basename(file) for file in filename_path]
        blob = [os.path.splitext(file)[0] for file in filename]
        ext = [os.path.splitext(file)[1] for file in filename]

    # indexTELEMAC paths
    filename_path_index = os.path.join(folder_path, "indexTELEMAC.txt")

    # indexTELEMAC.txt absence
    if not os.path.isfile(filename_path_index):
        warning_list.append("Warning: indexTELEMAC.txt doesn't exist. It will be created in the 'input' directory after the creation "
              "of the .hyd file. The latter will be filled in according to your choices.")

        # more_than_one_file_selected_by_user
        if more_than_one_file_selected_by_user:
            # hydrau_description for several file
            hydrau_description_multiple = []

            for i, file in enumerate(filename):
                # get units name from file
                filename_path = os.path.join(folder_path, file)
                nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
                unit_index_from_file = [True] * nbtimes
                # hdf5 filename
                blob2, ext = os.path.splitext(file)
                name_hdf5 = blob2 + ".hyd"

                # multi description
                hydrau_description_multiple.append(dict(path_prj=path_prj,
                                                         name_prj=name_prj,
                                                         hydrau_case=hydrau_case,
                                                         filename_source=file,
                                                         path_filename_source=folder_path,
                                                         hdf5_name=name_hdf5,
                                                         model_type=model_type,
                                                         model_dimension=str(nb_dim),
                                                         unit_list=", ".join(unit_name_from_file),
                                                         unit_list_full=", ".join(unit_name_from_file),
                                                         unit_list_tf=unit_index_from_file,
                                                         unit_number=str(nbtimes),
                                                         unit_type="time [s]",
                                                         reach_list="unknown",
                                                         reach_number=str(1),
                                                         reach_type="river",
                                                         epsg_code="unknown",
                                                         flow_type="unknown"))  # continuous flow

            # set actual hydrau_description
            hydrau_description = hydrau_description_multiple

        # one file selected_by_user
        if not more_than_one_file_selected_by_user:
            # get units name from file
            nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
            hydrau_description = dict(path_prj=path_prj,
                                       name_prj=name_prj,
                                       hydrau_case=hydrau_case,
                                       filename_source=filename,
                                       path_filename_source=folder_path,
                                       hdf5_name=filename.split('.')[0] + ".hyd",
                                       model_type=model_type,
                                       model_dimension=str(nb_dim),
                                       epsg_code="unknown")
            # hydrau_description
            hydrau_description["unit_list"] = ", ".join(unit_name_from_file)
            hydrau_description["unit_list_full"] = ", ".join(unit_name_from_file)
            hydrau_description["unit_list_tf"] = []
            hydrau_description["unit_number"] = str(nbtimes)
            hydrau_description["unit_type"] = "time [s]"
            hydrau_description["reach_list"] = "unknown"
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "unknown"

    # indexTELEMAC.txt presence
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

        if ext != ".txt":  # from file
            # selectedfiles textfiles matching
            selectedfiles_textfiles_match = [False] * len(filename_list)
            for i, file_path in enumerate(filename_list):
                if os.path.basename(file_path) in data_index_file["filename"]:
                    selectedfiles_textfiles_match[i] = True
        if ext == ".txt":  # from indexTELEMAC.txt
            # more_than_one_file_selected_by_user or more_than_one_file_in indextelemac (if from .txt)
            if len(data_index_file["filename"]) > 1:
                more_than_one_file_selected_by_user = True
            # textfiles filesexisting matching
            selectedfiles_textfiles_match = [False] * len(data_index_file["filename"])
            for i, file_from_indexfile in enumerate(data_index_file["filename"]):
                if os.path.isfile(os.path.join(folder_path, file_from_indexfile)):
                    selectedfiles_textfiles_match[i] = True
                else:
                    return "Error: " + file_from_indexfile + " doesn't exist in " + folder_path

        # check conditions
        if all(selectedfiles_textfiles_match):
            selectedfiles_textfiles_matching = True
        if any("Q[" in s for s in headers):
            discharge_presence = True  # "Q[" in headers
            discharge_index = [i for i, s in enumerate(headers) if 'Q[' in s][0]
            start = headers[discharge_index].find('Q[') + len('Q[')
            end = headers[discharge_index].find(']', start)
            discharge_unit = headers[discharge_index][start:end]
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
        """ ALL CASE """
        # hdf5 name and source filenames
        if more_than_one_file_selected_by_user:
            # pathfile[0] = folder_path  # source file path
            if ext != ".txt":  # from file
                namefile = ", ".join(filename)  # source file name
                name_hdf5 = "_".join(blob) + ".hyd"
            if ext == ".txt":  # from indexTELEMAC.txt
                namefile = ", ".join(data_index_file["filename"])  # source file name
                name_hdf5 = "_".join(
                    [os.path.splitext(file)[0] for file in data_index_file["filename"]]) + ".hyd"
        if not more_than_one_file_selected_by_user:
            if ext != ".txt":  # from file
                namefile = filename  # source file name
                name_hdf5 = filename.split('.')[0] + ".hyd"
            if ext == ".txt":  # from indexTELEMAC.txt
                namefile = data_index_file["filename"][0]  # source file name
                name_hdf5 = os.path.splitext(data_index_file["filename"][0])[0] + ".hyd"

        # hydrau_description
        hydrau_description = dict(path_prj=path_prj,
                                   name_prj=name_prj,
                                   hydrau_case=hydrau_case,
                                   filename_source=namefile,
                                   path_filename_source=folder_path,
                                   hdf5_name=name_hdf5,
                                   model_type=model_type,
                                   model_dimension=str(nb_dim),
                                   epsg_code=epsg_code)

        """ CASE 1.a """
        if hydrau_case == "1.a":
            # get units name from TELEMAC file
            filename_path = os.path.join(folder_path, data_index_file["filename"][0])
            nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
            # get units name from indexTELEMAC.txt file
            unit_name_from_index_file = data_index_file[headers[discharge_index]]
            # check if lenght of two loading units
            if len(unit_name_from_file) > len(unit_name_from_index_file):
                return "Error: units number from indexTELEMAC inferior than TELEMAC selected."

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
            hydrau_description["unit_list"] = ", ".join(data_index_file[headers[discharge_index]])
            hydrau_description["unit_list_full"] = ", ".join(unit_name_from_file)
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
            filename_path = os.path.join(folder_path, data_index_file["filename"][0])
            nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
            # get units name from indexTELEMAC.txt file
            unit_name_from_index_file = data_index_file[headers[time_index]][0]

            # check if lenght of two loading units
            if unit_name_from_index_file not in unit_name_from_file:
                return "Error: " + unit_name_from_index_file + " doesn't exist in telemac file"

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = ", ".join(data_index_file[headers[discharge_index]])
            hydrau_description["unit_list_full"] = unit_name_from_index_file
            hydrau_description["unit_list_tf"] = []
            hydrau_description["unit_number"] = str(1)
            hydrau_description["unit_type"] = "discharge [" + discharge_unit + "]"
            hydrau_description["timestep_list"] = ", ".join(data_index_file[headers[time_index]])
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "continuous flow"  # transient flow

        """ CASE 2.a """
        if hydrau_case == "2.a":
            # get units name from files (must have only one time step by file)
            for file in data_index_file["filename"]:
                filename_path = os.path.join(folder_path, file)
                nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
                if unit_name_from_file == ["0.0"] and nbtimes == 1:
                    pass
                else:
                    if nbtimes > 1:
                        return "Error: file " + file + " contain more than one time step (timestep :" \
                               + str(unit_name_from_file) + ")"

            # selected files same than indexTELEMAC file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexTELEMAC files"

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = ", ".join(data_index_file[headers[discharge_index]])
            hydrau_description["unit_list_full"] = ", ".join(data_index_file[headers[discharge_index]])
            hydrau_description["unit_list_tf"] = []
            hydrau_description["unit_number"] = str(len(data_index_file[headers[discharge_index]]))
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
                nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
                # get units name from indexTELEMAC.txt file
                unit_name_from_index_file = data_index_file[headers[time_index]][rowindex]
                # check if lenght of two loading units
                if unit_name_from_index_file not in unit_name_from_file:
                    return "Error: " + unit_name_from_index_file + "don't exist in" + file

            # selected files same than indexTELEMAC file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexTELEMAC files"

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = ", ".join(data_index_file[headers[discharge_index]])
            hydrau_description["unit_list_full"] = ", ".join(data_index_file[headers[discharge_index]])
            hydrau_description["unit_list_tf"] = []
            hydrau_description["unit_number"] = str(len(data_index_file[headers[discharge_index]]))
            hydrau_description["unit_type"] = "discharge [" + discharge_unit + "]"
            hydrau_description["timestep_list"] = ", ".join(data_index_file[headers[time_index]])
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "continuous flow"  # transient flow

        """ CASE 3.a """
        if hydrau_case == "3.a":
            # get units name from file
            filename_path = os.path.join(folder_path, data_index_file[headers[0]][0])
            nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)

            # selected files same than indexTELEMAC file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexTELEMAC files"

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            unit_index_from_file = [True] * nbtimes

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = ", ".join(unit_name_from_file)
            hydrau_description["unit_list_full"] = ", ".join(unit_name_from_file)
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
            nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)

            # get units name from indexTELEMAC.txt file
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
                               data_index_file[headers[0]][0]
                else:
                    unit_name_from_index_file2.append(element_unit)
            timestep_to_select = []
            for timestep_value in unit_name_from_file:
                if timestep_value in unit_name_from_index_file2:
                    timestep_to_select.append(True)
                else:
                    timestep_to_select.append(False)

            # selected files same than indexTELEMAC file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexTELEMAC files"

            if reach_presence:
                reach_name = data_index_file[headers[reach_index]][0]
            if not reach_presence:
                reach_name = "unknown"

            # hydrau_description
            hydrau_description["filename_source"] = ", ".join(data_index_file[headers[0]])
            hydrau_description["unit_list"] = ", ".join(unit_name_from_index_file2)
            hydrau_description["unit_list_full"] = ", ".join(unit_name_from_file)
            hydrau_description["unit_list_tf"] = timestep_to_select
            hydrau_description["unit_number"] = str(len(unit_name_from_index_file2))
            hydrau_description["unit_type"] = "time [" + time_unit + "]"
            hydrau_description["reach_list"] = reach_name
            hydrau_description["reach_number"] = str(1)
            hydrau_description["reach_type"] = "river"
            hydrau_description["flow_type"] = "transient flow"  # continuous flow

        """ CASE 4.a """
        if hydrau_case == "4.a":
            # selected files same than indexTELEMAC file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexTELEMAC files"

            # hydrau_description for several file
            hydrau_description_multiple = []
            for i, file in enumerate(data_index_file[headers[0]]):
                # get units name from file
                filename_path = os.path.join(folder_path, file)
                nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
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
                                                         unit_list=", ".join(unit_name_from_file),
                                                         unit_list_full=", ".join(unit_name_from_file),
                                                         unit_list_tf=unit_index_from_file,
                                                         unit_number=str(nbtimes),
                                                         unit_type="time [" + time_unit + "]",
                                                         reach_list=reach_name,
                                                         reach_number=str(1),
                                                         reach_type="river",
                                                         flow_type="transient flow"))  # continuous flow

            # set actual hydrau_description
            hydrau_description = hydrau_description_multiple

        """ CASE 4.b """
        if hydrau_case == "4.b":
            # selected files same than indexTELEMAC file
            if not selectedfiles_textfiles_matching:
                return "Error: selected files are different from indexTELEMAC files"

            # hydrau_description for several file
            hydrau_description_multiple = []

            for i, file in enumerate(data_index_file[headers[0]]):
                # get units name from file
                filename_path = os.path.join(folder_path, file)
                nbtimes, unit_name_from_file = get_time_step(filename_path, model_type)
                # get units name from indexTELEMAC.txt file
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
                                   data_index_file[headers[0]][i]
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
                                                         unit_list=", ".join(unit_name_from_index_file2),
                                                         unit_list_full=", ".join(unit_name_from_file),
                                                         unit_list_tf=unit_index_from_file,
                                                         unit_number=str(len(unit_name_from_index_file2)),
                                                         unit_type="time [" + time_unit + "]",
                                                         reach_list=reach_name,
                                                         reach_number=str(1),
                                                         reach_type="river",
                                                         flow_type="transient flow"))  # continuous flow

            # set actual hydrau_description
            hydrau_description = hydrau_description_multiple

    print("hydrau_case, " + hydrau_case)
    return hydrau_description, warning_list


def get_time_step(file_path, model_type):
    """
    models type list : HECRAS1D, RUBAR2D, MASCARET, RIVER2D, RUBAR1D, HECRAS2D, TELEMAC, LAMMI, SW2D, IBER2D
    :param file_path:
    :param model_type:
    :return:
    """
    nbtimes = False
    unit_name_from_file = False
    filename = os.path.basename(file_path)
    folder_path = os.path.dirname(file_path)
    if model_type == "TELEMAC":
        nbtimes, unit_name_from_file = telemac_mod.get_time_step(filename, folder_path)
    if model_type == "HECRAS2D":
        nbtimes, unit_name_from_file = hec_ras2D_mod.get_time_step(file_path)
    if model_type == "ASCII":
        nbtimes, unit_name_from_file = ascii_mod.get_time_step(file_path)
    return nbtimes, unit_name_from_file