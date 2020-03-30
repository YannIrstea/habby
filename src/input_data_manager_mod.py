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

from src.tools_mod import polygon_type_values, point_type_values, sort_homogoeneous_dict_list_by_on_key
from src.project_properties_mod import create_default_project_properties_dict
from src.tools_mod import create_empty_data_2d_whole_profile_dict, create_empty_data_2d_dict
from src import hdf5_mod, ascii_mod, telemac_mod, hec_ras2D_mod, hec_ras1D_mod, rubar1d2d_mod, basement_mod
from src import manage_grid_mod


class HydraulicSimulationResultsAnalyzer:
    def __init__(self, filename_path_list, path_prj, model_type, nb_dim):
        """
        :param filename_path_list: list of absolute path file, type: list of str
        :param path_prj: absolute path to project, type: str
        :param model_type: type of hydraulic model, type: str
        :param nb_dim: dimension number (1D/1.5D/2D), type: int
        """
        # init
        self.warning_list = []  # text warning output
        self.valid_file = False
        self.index_hydrau_file_exist = False
        self.index_hydrau_file_selected = False
        self.more_than_one_file_selected_by_user = False
        self.more_than_one_file_to_read = False
        self.hydrau_description_list = []
        self.hydrau_case = "unknown"
        self.index_hydrau_file_name = "indexHYDRAU.txt"
        # prj
        self.name_prj = os.path.splitext(os.path.basename(path_prj))[0]
        self.path_prj = path_prj
        # input
        self.filename_path_list = filename_path_list
        self.filename_list = [os.path.basename(filename_path) for filename_path in filename_path_list]
        # path
        self.folder_path = os.path.dirname(self.filename_path_list[0])
        self.index_hydrau_file_path = os.path.join(self.folder_path, self.index_hydrau_file_name)
        # hydraulic attributes
        self.model_type = model_type
        self.nb_dim = nb_dim
        # selection_analysis
        self.selection_analysis()
        # get_hydrau_description_from_source
        self.get_hydrau_description_from_source()

    def selection_analysis(self):
        # multi selection ?
        if len(self.filename_path_list) > 1:  # more than one file selected
            self.more_than_one_file_selected_by_user = True  # several files to read

        # index_hydrau exist ?
        if os.path.isfile(self.index_hydrau_file_path):
            self.index_hydrau_file_exist = True

        # index_hydrau selected ?
        if os.path.basename(self.filename_path_list[0]) == self.index_hydrau_file_name:
            self.index_hydrau_file_selected = True

    def get_hydrau_description_from_source(self):
        # indexHYDRAU.txt absence
        if not self.index_hydrau_file_exist:
            if self.model_type != "ASCII":
                self.warning_list.append("Warning: " + qt_tr.translate("hydro_input_file_mod",
                                                                       "indexHYDRAU.txt doesn't exist. It will be created in the 'input' directory after the creation "
                                                                       "of the .hyd file. The latter will be filled in according to your choices."))

            # more_than_one_file_selected_by_user
            if self.more_than_one_file_selected_by_user:
                if self.model_type == 'RUBAR20':  # change mode and remove one of them
                    self.more_than_one_file_selected_by_user = False
                    self.filename = self.filename[0]
                    self.filename_path = self.filename_path[0]
                else:
                    for i, file in enumerate(self.filename_path_list):
                        # get units name from file
                        hsr = HydraulicSimulationResultsSelector(file, self.folder_path, self.model_type,
                                                                 self.path_prj)
                        self.warning_list.extend(hsr.warning_list)
                        unit_index_from_file = [True] * hsr.timestep_nb
                        # hdf5 filename
                        blob2, ext = os.path.splitext(file)
                        name_hdf5 = blob2.replace(".", "_") + ".hyd"

                        # multi description
                        self.hydrau_description_list.append(dict(path_prj=self.path_prj,
                                                                name_prj=self.name_prj,
                                                                hydrau_case=self.hydrau_case,
                                                                filename_source=file,
                                                                path_filename_source=self.folder_path,
                                                                hdf5_name=name_hdf5,
                                                                model_type=self.model_type,
                                                                model_dimension=str(self.nb_dim),
                                                                unit_list=hsr.timestep_name_list,
                                                                unit_list_full=hsr.timestep_name_list,
                                                                unit_list_tf=unit_index_from_file,
                                                                unit_number=str(hsr.timestep_nb),
                                                                unit_type=hsr.timestep_unit,
                                                                reach_list="unknown",
                                                                reach_number=str(1),
                                                                reach_type="river",
                                                                epsg_code="unknown",
                                                                flow_type="unknown",
                                                                index_hydrau="False"))  # continuous flow

            # one file selected_by_user
            if not self.more_than_one_file_selected_by_user:  # don't set elif (because if rubar20 more_than_one_file_selected_by_user set to False)
                # get units name from file
                if self.model_type == 'ASCII':
                    ascii_description = ascii_mod.get_ascii_model_description(self.filename_path)
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
                            self.warning_list.append("Warning: " + qt_tr.translate("hydro_input_file_mod",
                                                                                   "Substrate data present in the ascii input file. "
                                                                                   "Data loading will create .hab directly instead of .hyd "
                                                                                   "(loading button label changed)"))
                        nbtimes = len(unit_list[0])
                else:
                    epsg_code = "unknown"
                    reach_number = 1
                    reach_list = "unknown"
                    sub = False
                    filename = os.path.basename(self.filename_list[0])
                    hsr = HydraulicSimulationResultsSelector(filename, self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    unit_list = hsr.timestep_name_list
                    unit_number = str(hsr.timestep_nb)
                    unit_list_tf = [True] * hsr.timestep_nb
                    unit_type = hsr.timestep_unit
                    if self.model_type == 'RUBAR20':  # remove extension
                        filename, _ = os.path.splitext(filename)

                # two cases
                self.hydrau_description_list = [dict(path_prj=self.path_prj,
                                                    name_prj=self.name_prj,
                                                    hydrau_case=self.hydrau_case,
                                                    filename_source=filename,
                                                    path_filename_source=self.folder_path,
                                                    hdf5_name=os.path.splitext(filename)[0].replace(".", "_") + ".hyd",
                                                    model_type=self.model_type,
                                                    model_dimension=str(self.nb_dim),
                                                    epsg_code=epsg_code,
                                                    unit_list=unit_list,
                                                    unit_list_full=unit_list,
                                                    unit_list_tf=unit_list_tf,
                                                    unit_number=unit_number,
                                                    unit_type=unit_type,
                                                    reach_list=reach_list,
                                                    reach_number=str(reach_number),
                                                    reach_type="river",
                                                    flow_type="unknown",
                                                    sub=sub,
                                                    index_hydrau=False)]

        # indexHYDRAU.txt presence
        if self.index_hydrau_file_exist:
            # init variables
            discharge_presence = False  # "Q[" in headers
            time_presence = False  # "T[" in headers
            reach_presence = False  # "reachname" in headers
            selectedfiles_textfiles_matching = False

            # read text file
            with open(self.index_hydrau_file_path, 'rt') as f:
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

            if self.model_type == 'RUBAR20':
                self.more_than_one_file_selected_by_user = False
                selectedfiles_textfiles_match = [True] * 2
                if type(self.filename) == list:
                    self.filename = self.filename[0]
                    self.filename_path = self.filename_path[0]

            elif not self.index_hydrau_file_selected:  # from file
                # self.more_than_one_file_selected_by_user or more_than_one_file_in indexHYDRAU (if from .txt)
                if len(data_index_file["filename"]) > 1:
                    self.more_than_one_file_selected_by_user = True
                # textfiles filesexisting matching
                selectedfiles_textfiles_match = [False] * len(data_index_file["filename"])
                for i, file_from_indexfile in enumerate(data_index_file["filename"]):
                    if os.path.isfile(os.path.join(self.folder_path, file_from_indexfile)):
                        if file_from_indexfile in self.filename_list:
                            selectedfiles_textfiles_match[i] = True
                        else:
                            selectedfiles_textfiles_match[i] = False
                    else:
                        return "Error: " + file_from_indexfile + " doesn't exist in " + self.folder_path, None
            elif self.index_hydrau_file_selected:  # from indexHYDRAU.txt
                # self.more_than_one_file_selected_by_user or more_than_one_file_in indexHYDRAU (if from .txt)
                if len(data_index_file["filename"]) > 1:
                    self.more_than_one_file_selected_by_user = True
                # textfiles filesexisting matching
                selectedfiles_textfiles_match = [False] * len(data_index_file["filename"])
                for i, file_from_indexfile in enumerate(data_index_file["filename"]):
                    if os.path.isfile(os.path.join(self.folder_path, file_from_indexfile)):
                        selectedfiles_textfiles_match[i] = True
                    else:
                        return "Error: " + file_from_indexfile + " doesn't exist in " + self.folder_path, None

            # check conditions
            if all(selectedfiles_textfiles_match):
                selectedfiles_textfiles_matching = True
                self.filename_list = data_index_file["filename"]
                self.filename_path_list = [os.path.join(self.folder_path, filename) for filename in self.filename_list]
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
            if not self.more_than_one_file_selected_by_user and discharge_presence and not time_presence:
                self.hydrau_case = "1.a"
            if not self.more_than_one_file_selected_by_user and discharge_presence and time_presence:
                self.hydrau_case = "1.b"
            if self.more_than_one_file_selected_by_user and discharge_presence and not time_presence:
                self.hydrau_case = "2.a"
            if self.more_than_one_file_selected_by_user and discharge_presence and time_presence:
                self.hydrau_case = "2.b"
            if not self.more_than_one_file_selected_by_user and not discharge_presence and time_presence:
                if data_index_file[headers[time_index]][0] == "all":
                    self.hydrau_case = "3.a"
                if data_index_file[headers[time_index]][0] != "all":
                    self.hydrau_case = "3.b"
            if self.more_than_one_file_selected_by_user and not discharge_presence and time_presence:
                if data_index_file[headers[time_index]][0] == "all":
                    self.hydrau_case = "4.a"
                if data_index_file[headers[time_index]][0] != "all":
                    self.hydrau_case = "4.b"

            # print("self.hydrau_case", self.hydrau_case)

            """ ALL CASE """
            # hdf5 name and source filenames
            if self.more_than_one_file_selected_by_user:
                # pathfile[0] = self.folder_path  # source file path
                if not self.index_hydrau_file_selected:  # from file
                    namefile = ", ".join(self.filename_list)  # source file name
                    name_hdf5 = "_".join([os.path.splitext(filename)[0] for filename in self.filename_list]).replace(".", "_") + ".hyd"
                if self.index_hydrau_file_selected:  # from indexHYDRAU.txt
                    namefile = ", ".join(data_index_file["filename"])  # source file name
                    name_hdf5 = "_".join(
                        [os.path.splitext(file)[0].replace(".", "_") for file in data_index_file["filename"]]) + ".hyd"
                    if selectedfiles_textfiles_match and len(name_hdf5) > 25:
                        name_hdf5 = os.path.splitext(data_index_file["filename"][0])[0].replace(".", "_") \
                                    + "_to_" + \
                                    os.path.splitext(data_index_file["filename"][-1])[0].replace(".", "_") + ".hyd"
            if not self.more_than_one_file_selected_by_user:
                if not self.index_hydrau_file_selected:  # from file
                    namefile = self.filename_list[0]  # source file name
                    name_hdf5 = os.path.splitext(namefile)[0].replace(".", "_") + ".hyd"
                    # if model_type == 'RUBAR20':
                    #     namefile = os.path.splitext(namefile)[0]
                if self.index_hydrau_file_selected:  # from indexHYDRAU.txt
                    namefile = data_index_file["filename"][0]  # source file name
                    name_hdf5 = os.path.splitext(data_index_file["filename"][0])[0].replace(".", "_") + ".hyd"
            if self.model_type == 'RUBAR20':
                data_index_file[headers[0]] = [namefile]

            # self.hydrau_description_list
            self.hydrau_description_list = [dict(path_prj=self.path_prj,
                                                name_prj=self.name_prj,
                                                hydrau_case=self.hydrau_case,
                                                filename_source=namefile,
                                                path_filename_source=self.folder_path,
                                                hdf5_name=name_hdf5,
                                                model_type=self.model_type,
                                                model_dimension=str(self.nb_dim),
                                                epsg_code=epsg_code,
                                                index_hydrau=True)]

            """ CASE 1.a """
            if self.hydrau_case == "1.a":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(data_index_file["filename"][0],
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[discharge_index]]
                # check if lenght of two loading units
                if len(hsr.timestep_name_list) > len(unit_name_from_index_file):
                    return "Error: units number from indexHYDRAU inferior than TELEMAC selected.", None

                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][0]
                if not reach_presence:
                    reach_name = "unknown"

                # items
                if len(hsr.timestep_name_list) == len(unit_name_from_index_file):
                    pass
                if len(hsr.timestep_name_list) < len(unit_name_from_index_file):
                    index_file = data_index_file[headers[0]].index(self.filename)
                    data_index_file[headers[0]] = [data_index_file[headers[0]][index_file]]
                    data_index_file[headers[discharge_index]] = [data_index_file[headers[discharge_index]][index_file]]

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_full"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_tf"] = []
                self.hydrau_description_list[0]["unit_number"] = str(1)
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            """ CASE 1.b """
            if self.hydrau_case == "1.b":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(namefile,
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[time_index]][
                    data_index_file[headers[0]].index(namefile)]

                # check if lenght of two loading units
                if unit_name_from_index_file not in hsr.timestep_name_list:
                    return "Error: " + unit_name_from_index_file + " doesn't exist in telemac file", None
                # else:
                #     unit_index = unit_name_from_file.index(unit_name_from_index_file)
                #     unit_list_tf = [False] * nbtimes
                #     unit_list_tf[unit_index] = True

                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][0]
                else:
                    reach_name = "unknown"

                # self.hydrau_description_list
                self.hydrau_description_list[0]["unit_list"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_full"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_tf"] = [True] * len(data_index_file[headers[discharge_index]])
                self.hydrau_description_list[0]["unit_number"] = str(1)
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["timestep_list"] = data_index_file[headers[time_index]]
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            """ CASE 2.a """
            if self.hydrau_case == "2.a":
                # get units name from files (must have only one time step by file)
                for file in data_index_file["filename"]:
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    if hsr.timestep_name_list == ["0.0"] and hsr.timestep_nb == 1:
                        pass
                    else:
                        if hsr.timestep_nb > 1:
                            return "Error: file " + file + " contain more than one time step (timestep :" \
                                   + str(hsr.timestep_name_list) + ")", None

                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    pass
                    # return "Error: selected files are different from indexHYDRAU files", None

                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][0]
                if not reach_presence:
                    reach_name = "unknown"

                # # check if selected files are equal to data_index_file
                # if len(self.filename_list) != len(data_index_file["filename"]):
                #     for index, selected_file in enumerate(data_index_file["filename"]):

                # index_to_keep = []
                # for index, selected_file in enumerate(data_index_file["filename"]):
                #     if selected_file in [os.path.basename(element) for element in self.filename_list]:
                #         index_to_keep.append(index)
                # for header in headers:
                #     data_index_file[header] = [data_index_file[header][index] for index in index_to_keep]

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_full"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_tf"] = selectedfiles_textfiles_match
                self.hydrau_description_list[0]["unit_number"] = str(selectedfiles_textfiles_match.count(True))
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            """ CASE 2.b """
            if self.hydrau_case == "2.b":
                for rowindex, file in enumerate(data_index_file["filename"]):
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    # get units name from indexHYDRAU.txt file
                    unit_name_from_index_file = data_index_file[headers[time_index]][rowindex]
                    # check if lenght of two loading units
                    if unit_name_from_index_file not in hsr.timestep_name_list:
                        return "Error: " + unit_name_from_index_file + " don't exist in " + file, None

                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    return "Error: selected files are different from indexHYDRAU files", None

                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][0]
                if not reach_presence:
                    reach_name = "unknown"

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_full"] = data_index_file[headers[discharge_index]]
                self.hydrau_description_list[0]["unit_list_tf"] = [True] * len(data_index_file[headers[discharge_index]])
                self.hydrau_description_list[0]["unit_number"] = str(len(data_index_file[headers[discharge_index]]))
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["timestep_list"] = data_index_file[headers[time_index]]
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            """ CASE 3.a """
            if self.hydrau_case == "3.a":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(data_index_file[headers[0]][0],
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    return "Error: selected files are different from indexHYDRAU files", None

                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]][0]
                if not reach_presence:
                    reach_name = "unknown"

                unit_index_from_file = [True] * hsr.timestep_nb

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = hsr.timestep_name_list
                self.hydrau_description_list[0]["unit_list_full"] = hsr.timestep_name_list
                self.hydrau_description_list[0]["unit_list_tf"] = unit_index_from_file
                self.hydrau_description_list[0]["unit_number"] = str(hsr.timestep_nb)
                self.hydrau_description_list[0]["unit_type"] = "time [" + hsr.timestep_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["flow_type"] = "transient flow"  # continuous flow

            """ CASE 3.b """
            if self.hydrau_case == "3.b":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(data_index_file[headers[0]][0],
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[time_index]][0]

                unit_name_from_index_file2 = []
                for element_unit in unit_name_from_index_file.split(";"):
                    if "/" in element_unit:  # from to
                        from_unit, to_unit = element_unit.split("/")
                        try:
                            from_unit_index = hsr.timestep_name_list.index(from_unit)
                            to_unit_index = hsr.timestep_name_list.index(to_unit)
                            unit_name_from_index_file2 = unit_name_from_index_file2 + \
                                                         hsr.timestep_name_list[
                                                         from_unit_index:to_unit_index + 1]
                        except ValueError:
                            return "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                                   data_index_file[headers[0]][0], None
                    else:
                        unit_name_from_index_file2.append(element_unit)
                timestep_to_select = []
                for timestep_value in hsr.timestep_name_list:
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

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = unit_name_from_index_file2
                self.hydrau_description_list[0]["unit_list_full"] = hsr.timestep_name_list
                self.hydrau_description_list[0]["unit_list_tf"] = timestep_to_select
                self.hydrau_description_list[0]["unit_number"] = str(len(unit_name_from_index_file2))
                self.hydrau_description_list[0]["unit_type"] = "time [" + time_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["flow_type"] = "transient flow"  # continuous flow

            """ CASE 4.a """
            if self.hydrau_case == "4.a":
                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    return "Error: selected files are different from indexHYDRAU files", None

                self.hydrau_description_list = []
                for i, file in enumerate(data_index_file[headers[0]]):
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    unit_index_from_file = [True] * hsr.timestep_nb
                    # hdf5 filename
                    blob2, ext = os.path.splitext(file)
                    name_hdf5 = blob2 + ".hyd"

                    # reach name
                    if reach_presence:
                        reach_name = data_index_file[headers[reach_index]][i]
                    if not reach_presence:
                        reach_name = "unknown"
                    # multi description
                    self.hydrau_description_list.append(dict(path_prj=self.path_prj,
                                                            name_prj=self.name_prj,
                                                            hydrau_case=self.hydrau_case,
                                                            filename_source=file,
                                                            path_filename_source=self.folder_path,
                                                            hdf5_name=name_hdf5,
                                                            model_type=self.model_type,
                                                            model_dimension=str(self.nb_dim),
                                                            epsg_code=epsg_code,
                                                            unit_list=hsr.timestep_name_list,
                                                            unit_list_full=hsr.timestep_name_list,
                                                            unit_list_tf=unit_index_from_file,
                                                            unit_number=str(hsr.timestep_nb),
                                                            unit_type="time [" + hsr.timestep_unit + "]",
                                                            reach_list=reach_name,
                                                            reach_number=str(1),
                                                            reach_type="river",
                                                            flow_type="transient flow",
                                                            index_hydrau=True))  # continuous flow

            """ CASE 4.b """
            if self.hydrau_case == "4.b":
                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    return "Error: selected files are different from indexHYDRAU files", None

                self.hydrau_description_list = []
                for i, file in enumerate(data_index_file[headers[0]]):
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    # get units name from indexHYDRAU.txt file
                    unit_name_from_index_file = data_index_file[headers[time_index]][i]
                    unit_name_from_index_file2 = []
                    for element_unit in unit_name_from_index_file.split(";"):
                        if "/" in element_unit:  # from to
                            from_unit, to_unit = element_unit.split("/")
                            try:
                                from_unit_index = hsr.timestep_name_list.index(from_unit)
                                to_unit_index = hsr.timestep_name_list.index(to_unit)
                                unit_name_from_index_file2 = unit_name_from_index_file2 + \
                                                             hsr.timestep_name_list[
                                                             from_unit_index:to_unit_index + 1]
                            except ValueError:

                                return "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                                       data_index_file[headers[0]][i], None
                        else:
                            unit_name_from_index_file2.append(element_unit)

                    unit_index_from_file = []
                    for item in hsr.timestep_name_list:
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
                    self.hydrau_description_list.append(dict(path_prj=self.path_prj,
                                                            name_prj=self.name_prj,
                                                            hydrau_case=self.hydrau_case,
                                                            filename_source=file,
                                                            path_filename_source=self.folder_path,
                                                            hdf5_name=name_hdf5,
                                                            model_type=self.model_type,
                                                            model_dimension=str(self.nb_dim),
                                                            epsg_code=epsg_code,
                                                            unit_list=unit_name_from_index_file2,
                                                            unit_list_full=hsr.timestep_name_list,
                                                            unit_list_tf=unit_index_from_file,
                                                            unit_number=str(len(unit_name_from_index_file2)),
                                                            unit_type="time [" + time_unit + "]",
                                                            reach_list=reach_name,
                                                            reach_number=str(1),
                                                            reach_type="river",
                                                            flow_type="transient flow",
                                                            index_hydrau=True))  # continuous flow

        # if m3/s
        for hydrau_description_index in range(len(self.hydrau_description_list)):
            if "m3/s" in self.hydrau_description_list[hydrau_description_index]["unit_type"]:
                self.hydrau_description_list[hydrau_description_index]["unit_type"] = \
                self.hydrau_description_list[hydrau_description_index]["unit_type"].replace("m3/s", "m<sup>3</sup>/s")

        print("------------------------------------------------")
        print("self.hydrau_case, " + self.hydrau_case)
        # print(self.hydrau_description_list[0]["unit_list"])
        # print(self.hydrau_description_list[0]["unit_list_tf"])
        # print(self.hydrau_description_list[0]["unit_number"])


class HydraulicSimulationResultsSelector:
    def __new__(self, filename, folder_path, model_type, path_prj):
        if model_type == "TELEMAC":
            return telemac_mod.TelemacResult(filename, folder_path, model_type, path_prj)
        elif model_type == "HECRAS2D":
            return hec_ras2D_mod.HecRas2dResult(filename, folder_path, model_type, path_prj)
        elif model_type == "HECRAS1D":
            return None  # TODO
        elif model_type == "RUBAR20":
            return rubar1d2d_mod.Rubar2dResult(filename, folder_path, model_type, path_prj)
        elif model_type == "BASEMENT2D":
            return basement_mod.BasementResult(filename, folder_path, model_type, path_prj)


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
                    linetowrite += filename_column[row] + "\t" + str(
                        description_from_indexHYDRAU_file[0]["unit_list_full"][row])
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
                    description_from_indexHYDRAU_file[0]["unit_list"][row]) + "\t" + \
                               description_from_indexHYDRAU_file[0]["timestep_list"][row]
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
            if description_from_indexHYDRAU_file[0]["unit_list"] == description_from_indexHYDRAU_file[0][
                "unit_list_full"]:
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
            filename_path = os.path.join(description_from_indexHYDRAU_file[i_hdf5]["path_prj"], "input",
                                         "indexHYDRAU.txt")
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
                if description_from_indexHYDRAU_file[i_hdf5]["unit_list"] == description_from_indexHYDRAU_file[i_hdf5][
                    "unit_list_full"]:
                    unit_data = "all"
                else:
                    index = [i for i, item in enumerate(description_from_indexHYDRAU_file[i_hdf5]["unit_list_full"]) if
                             item in description_from_indexHYDRAU_file[i_hdf5]["unit_list"]]
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
    delta_file = 80 / len(hydrau_description)

    # for each .hyd (or .hab) to create
    for hdf5_file_index in range(0, len(hydrau_description)):
        # get filename source (can be several)
        filename_source = hydrau_description[hdf5_file_index]["filename_source"].split(", ")
        # data_2d_whole_profile
        data_2d_whole_profile = create_empty_data_2d_whole_profile_dict(1)  # always one reach by file
        hydrau_description[hdf5_file_index]["unit_correspondence"] = [[]]  # always one reach by file
        # data_2d
        data_2d = create_empty_data_2d_dict(1,  # always one reach
                                            mesh_variables=[],
                                            node_variables=["h", "v"])
        # for each filename source
        for i, file in enumerate(filename_source):
            # get timestep_name_list
            hsr = HydraulicSimulationResultsSelector(file,
                                             hydrau_description[hdf5_file_index]["path_filename_source"],
                                             hydrau_description[hdf5_file_index]["model_type"],
                                             hydrau_description[hdf5_file_index]["path_prj"])
            if hydrau_description[hdf5_file_index]["hydrau_case"] in {"1.a", "2.a"}:
                timestep_with_list = hsr.timestep_name_list
            elif hydrau_description[hdf5_file_index]["hydrau_case"] in {"1.b", "2.b"}:
                timestep_with_list = hydrau_description[hdf5_file_index]["timestep_list"]
            else:  # {"4.a", "4.b", "3.b", "3.a", "unknown"}:
                timestep_with_list = hydrau_description[hdf5_file_index]["unit_list"]
            # load data
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_with_list)
            # check error
            if not data_2d_source and not description_from_source:
                q.put(mystdout)
                return
            # data_2d_whole_profile
            data_2d_whole_profile["mesh"]["tin"][0].extend(data_2d_source["mesh"]["tin"][0])
            data_2d_whole_profile["node"]["xy"][0].extend(data_2d_source["node"]["xy"][0])
            data_2d_whole_profile["node"]["z"][0].extend(data_2d_source["node"]["z"][0])
            # data_2d
            data_2d["mesh"]["tin"][0].extend(data_2d_source["mesh"]["tin"][0])
            data_2d["node"]["xy"][0].extend(data_2d_source["node"]["xy"][0])
            data_2d["node"]["z"][0].extend(data_2d_source["node"]["z"][0])
            for mesh_data_key in list(data_2d_source["mesh"]["data"].keys()):
                data_2d["mesh"]["data"][mesh_data_key][0].extend(data_2d_source["mesh"]["data"][mesh_data_key][0])
            for node_data_key in list(data_2d_source["node"]["data"].keys()):
                data_2d["node"]["data"][node_data_key][0].extend(data_2d_source["node"]["data"][node_data_key][0])

        # hyd_varying_mesh and hyd_unit_z_equal?
        hyd_varying_xy_index = []
        hyd_varying_z_index = []
        it_equality = 0
        for i in range(len(data_2d_whole_profile["node"]["xy"][0])):
            if i == 0:
                hyd_varying_xy_index.append(it_equality)
                hyd_varying_z_index.append(it_equality)
            if i > 0:
                # xy
                if np.array_equal(data_2d_whole_profile["node"]["xy"][0][i], data_2d_whole_profile["node"]["xy"][0][it_equality]):  # equal
                    hyd_varying_xy_index.append(it_equality)
                else:
                    it_equality = i
                    hyd_varying_xy_index.append(it_equality)  # diff
                # z
                if np.array_equal(data_2d_whole_profile["node"]["z"][0][i], data_2d_whole_profile["node"]["z"][0][it_equality]):  # equal
                    hyd_varying_z_index.append(it_equality)
                else:
                    it_equality = i
                    hyd_varying_z_index.append(it_equality)  # diff
        if len(set(hyd_varying_xy_index)) == 1:  # one tin for all unit
            hyd_varying_mesh = False
            data_2d_whole_profile["mesh"]["tin"][0] = [data_2d_whole_profile["mesh"]["tin"][0][0]]
            data_2d_whole_profile["node"]["xy"][0] = [data_2d_whole_profile["node"]["xy"][0][0]]
        else:
            hyd_varying_mesh = True
        # hyd_unit_z_equal ?
        if len(set(hyd_varying_z_index)) == 1:
            hyd_unit_z_equal = True
        else:
            hyd_unit_z_equal = True

        # one file : one reach, varying_mesh==False
        if len(filename_source) == 1:
            hydrau_description[hdf5_file_index]["unit_correspondence"][0] = hyd_varying_xy_index * int(hydrau_description[hdf5_file_index]["unit_number"])
        else:
            hydrau_description[hdf5_file_index]["unit_correspondence"][0] = hyd_varying_xy_index

        """ cut_2d_grid_data_2d """
        data_2d, hydrau_description[hdf5_file_index] = manage_grid_mod.cut_2d_grid_data_2d(data_2d,
                                                                                           hydrau_description[
                                                                                               hdf5_file_index],
                                                                                           progress_value,
                                                                                           delta_file,
                                                                                           project_preferences[
                                                                                               "cut_mesh_partialy_dry"],
                                                                                           project_preferences[
                                                                                               'min_height_hyd'])

        # progress
        progress_value.value = 90

        # hyd description
        hyd_description = dict()
        hyd_description["hyd_filename_source"] = hydrau_description[hdf5_file_index]["filename_source"]
        hyd_description["hyd_path_filename_source"] = hydrau_description[hdf5_file_index]["path_filename_source"]
        hyd_description["hyd_model_type"] = hydrau_description[hdf5_file_index]["model_type"]
        hyd_description["hyd_2D_numerical_method"] = "FiniteElementMethod"
        hyd_description["hyd_model_dimension"] = hydrau_description[hdf5_file_index]["model_dimension"]
        hyd_description["hyd_mesh_variables_list"] = ", ".join(list(data_2d_source["mesh"]["data"].keys()))
        hyd_description["hyd_node_variables_list"] = ", ".join(list(data_2d_source["node"]["data"].keys()))
        hyd_description["hyd_epsg_code"] = hydrau_description[hdf5_file_index]["epsg_code"]
        hyd_description["hyd_reach_list"] = hydrau_description[hdf5_file_index]["reach_list"]
        hyd_description["hyd_reach_number"] = hydrau_description[hdf5_file_index]["reach_number"]
        hyd_description["hyd_reach_type"] = hydrau_description[hdf5_file_index]["reach_type"]
        hyd_description["hyd_unit_list"] = [[unit_name.replace(":", "_").replace(" ", "_") for unit_name in
                                             hydrau_description[hdf5_file_index]["unit_list"]]]
        hyd_description["hyd_unit_number"] = str(len(hydrau_description[hdf5_file_index]["unit_list"]))
        hyd_description["hyd_unit_type"] = hydrau_description[hdf5_file_index]["unit_type"]
        hyd_description["hyd_varying_mesh"] = hyd_varying_mesh
        hyd_description["hyd_unit_z_equal"] = hyd_unit_z_equal
        hyd_description["unit_correspondence"] = hydrau_description[hdf5_file_index]["unit_correspondence"]
        hyd_description["hyd_cuted_mesh_partialy_dry"] = project_preferences["cut_mesh_partialy_dry"]
        hyd_description["hyd_hydrau_case"] = hydrau_description[hdf5_file_index]["hydrau_case"]
        if hyd_description["hyd_hydrau_case"] in {"1.b", "2.b"}:
            hyd_description["timestep_source_list"] = [hydrau_description[hdf5_file_index]["timestep_list"]]

        # create hdf5
        hdf5 = hdf5_mod.Hdf5Management(hydrau_description[hdf5_file_index]["path_prj"],
                                       hydrau_description[hdf5_file_index]["hdf5_name"])
        hdf5.create_hdf5_hyd(data_2d, data_2d_whole_profile, hyd_description, project_preferences)

    # prog
    progress_value.value = 90

    # create_index_hydrau_text_file
    if not hydrau_description[hdf5_file_index]["index_hydrau"]:
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
