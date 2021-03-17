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
import os.path
import sys
from time import sleep
from io import StringIO
import numpy as np
from PyQt5.QtCore import QCoreApplication as qt_tr
from pandas import DataFrame
from multiprocessing import Pool, Lock, cpu_count

from src.merge import merge, setup
from src.hydrosignature import hscomparison
from src.tools_mod import sort_homogoeneous_dict_list_by_on_key, get_translator
from src.project_properties_mod import create_default_project_properties_dict
from src import hdf5_mod
from src.hydraulic_results_manager_mod import HydraulicSimulationResultsSelector
from src.data_2d_mod import Data2d


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
            self.warning_list.append("Warning: " + qt_tr.translate("hydro_input_file_mod",
                                                                       "indexHYDRAU.txt doesn't exist. It will be created in the 'input' directory after the creation "
                                                                       "of the .hyd file. The latter will be filled in according to your choices."))

            # more_than_one_file_selected_by_user
            if self.more_than_one_file_selected_by_user:
                if self.model_type == 'rubar2d':  # change mode and remove one of them
                    self.more_than_one_file_selected_by_user = False
                    self.filename_list = self.filename_list[0]
                    self.filename_path_list = self.filename_path_list[0]
                else:
                    for i, file in enumerate(self.filename_path_list):
                        # get units name from file
                        hsr = HydraulicSimulationResultsSelector(file, self.folder_path, self.model_type,
                                                                 self.path_prj)
                        self.warning_list.extend(hsr.warning_list)

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
                                                                unit_list=[list(hsr.timestep_name_list)] * hsr.reach_number,
                                                                unit_list_full=[list(hsr.timestep_name_list)] * hsr.reach_number,
                                                                unit_list_tf=[[True] * hsr.timestep_nb] * hsr.reach_number,
                                                                unit_number=str(hsr.timestep_nb),
                                                                unit_type=hsr.timestep_unit,
                                                                reach_list=["unknown"],
                                                                reach_number=str(1),
                                                                reach_type="river",
                                                                epsg_code="unknown",
                                                                flow_type="unknown",
                                                                index_hydrau="False"))  # continuous flow

            # one file selected_by_user
            if not self.more_than_one_file_selected_by_user:  # don't set elif (because if rubar2d more_than_one_file_selected_by_user set to False)
                filename = os.path.basename(self.filename_list[0])
                hsr = HydraulicSimulationResultsSelector(filename, self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                if self.model_type == 'rubar2d':  # remove extension
                    filename, _ = os.path.splitext(filename)
                if self.model_type == "basement2d":
                    hdf5_name = hsr.simulation_name + ".hyd"
                else:
                    hdf5_name = os.path.splitext(filename)[0].replace(".", "_") + ".hyd"

                if hsr.sub:
                    hdf5_name = os.path.splitext(hdf5_name)[0] + ".hab"

                # if type(hsr.timestep_name_list[0]) == list:  # ASCII case
                #     unit_list = hsr.timestep_name_list
                # else:
                unit_list = [list(hsr.timestep_name_list)] * hsr.reach_number

                self.hydrau_description_list = [dict(path_prj=self.path_prj,
                                                    name_prj=self.name_prj,
                                                    hydrau_case=self.hydrau_case,
                                                    filename_source=filename,
                                                    path_filename_source=self.folder_path,
                                                    hdf5_name=hdf5_name,
                                                    model_type=self.model_type,
                                                    model_dimension=str(self.nb_dim),
                                                    epsg_code=hsr.epsg_code,
                                                    variable_name_unit_dict=hsr.hvum.software_detected_list,
                                                    unit_list=list(unit_list),
                                                    unit_list_full=unit_list,
                                                    unit_list_tf=[[True] * hsr.timestep_nb] * hsr.reach_number,
                                                    unit_number=str(hsr.timestep_nb),
                                                    unit_type=hsr.timestep_unit,
                                                    reach_list=hsr.reach_name_list,
                                                    reach_number=str(hsr.reach_number),
                                                    reach_type="river",
                                                    flow_type="unknown",
                                                    sub=hsr.sub,
                                                    index_hydrau=False)]

        # indexHYDRAU.txt presence
        if self.index_hydrau_file_exist:
            # init variables
            discharge_presence = False  # "Q[" in headers
            time_presence = False  # "T[" in headers
            reach_presence = False  # "reachname" in headers
            selectedfiles_textfiles_matching = False

            # read text file
            with open(self.index_hydrau_file_path, 'rt', encoding="utf-8") as f:
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

            if self.model_type == 'rubar2d':
                self.more_than_one_file_selected_by_user = False
                selectedfiles_textfiles_match = [True] * 2
                if type(self.filename_list) == list:
                    self.filename_list = self.filename_list[0]
                    self.filename_path_list = self.filename_path_list[0]

            elif not self.index_hydrau_file_selected:  # from file
                # self.more_than_one_file_selected_by_user or more_than_one_file_in indexHYDRAU (if from .txt)
                if len(list(set(data_index_file["filename"]))) > 1:
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
                        self.hydrau_description_list = "Error: " + file_from_indexfile + " doesn't exist in " + self.folder_path
                        return
            elif self.index_hydrau_file_selected:  # from indexHYDRAU.txt
                # self.more_than_one_file_selected_by_user or more_than_one_file_in indexHYDRAU (if from .txt)
                if len(list(set(data_index_file["filename"]))) > 1:
                    self.more_than_one_file_selected_by_user = True
                # textfiles filesexisting matching
                selectedfiles_textfiles_match = [False] * len(data_index_file["filename"])
                for i, file_from_indexfile in enumerate(data_index_file["filename"]):
                    if os.path.isfile(os.path.join(self.folder_path, file_from_indexfile)):
                        selectedfiles_textfiles_match[i] = True
                    else:
                        self.hydrau_description_list = "Error: " + file_from_indexfile + " doesn't exist in " + self.folder_path
                        return

            # check conditions
            multi_reach = False
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
                # check if all reachname are equal
                reach_list = data_index_file[headers[reach_index]]
                if len(set(reach_list)) > 1:
                    multi_reach = True

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
                if self.index_hydrau_file_selected:  # from indexHYDRAU.txt
                    namefile = data_index_file["filename"][0]  # source file name
                    name_hdf5 = os.path.splitext(data_index_file["filename"][0])[0].replace(".", "_") + ".hyd"
            if self.model_type == 'rubar2d':
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

            # CASE 1.a """
            if self.hydrau_case == "1.a":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(data_index_file["filename"][0],
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[discharge_index]]
                # check if lenght of two loading units
                if hsr.timestep_nb > len(unit_name_from_index_file):
                    self.hydrau_description_list = "Error: units number from indexHYDRAU inferior than TELEMAC selected."
                    return

                if reach_presence:
                    reach_name = [data_index_file[headers[reach_index]][0]]
                else:
                    reach_name = ["unknown"]

                # items
                if hsr.timestep_nb == len(unit_name_from_index_file):
                    pass
                if hsr.timestep_nb < len(unit_name_from_index_file):
                    index_file = data_index_file[headers[0]].index(self.filename)
                    data_index_file[headers[0]] = [data_index_file[headers[0]][index_file]]
                    data_index_file[headers[discharge_index]] = [data_index_file[headers[discharge_index]][index_file]]

                variable_name_unit_dict = hsr.hvum.software_detected_list

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_full"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_tf"] = [[True] * hsr.timestep_nb] * hsr.reach_number
                self.hydrau_description_list[0]["unit_number"] = str(1)
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            # CASE 1.b """
            if self.hydrau_case == "1.b":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(namefile,
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # get units name from indexHYDRAU.txt file
                unit_name_from_index_file = data_index_file[headers[time_index]][data_index_file[headers[0]].index(namefile)]

                # check if lenght of two loading units
                if unit_name_from_index_file not in hsr.timestep_name_list:
                    self.hydrau_description_list = "Error: " + unit_name_from_index_file + " doesn't exist in file"
                    return

                if reach_presence:
                    reach_name = [data_index_file[headers[reach_index]][0]]
                else:
                    reach_name = ["unknown"]

                variable_name_unit_dict = hsr.hvum.software_detected_list

                if self.model_type == "basement2d":
                    self.hydrau_description_list[0]["hdf5_name"] = hsr.simulation_name + ".hyd"

                # self.hydrau_description_list
                self.hydrau_description_list[0]["unit_list"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_full"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_tf"] = [[True] * len(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_number"] = str(1)
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["timestep_list"] = data_index_file[headers[time_index]]
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            # CASE 2.a """
            elif self.hydrau_case == "2.a":
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
                            self.hydrau_description_list = "Error: file " + file + " contain more than one time step (timestep :" \
                                   + str(hsr.timestep_name_list) + ")"
                            return
                    if file == data_index_file["filename"][-1]:  # last
                        variable_name_unit_dict = hsr.hvum.software_detected_list

                if reach_presence:
                    reach_name = [data_index_file[headers[reach_index]][0]]
                if not reach_presence:
                    reach_name = ["unknown"]

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
                self.hydrau_description_list[0]["unit_list"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_full"] = [list(data_index_file[headers[discharge_index]])]  * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_tf"] = [selectedfiles_textfiles_match] * hsr.reach_number
                self.hydrau_description_list[0]["unit_number"] = str(selectedfiles_textfiles_match.count(True))
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            # CASE 2.b """
            elif self.hydrau_case == "2.b":
                for rowindex, file in enumerate(data_index_file["filename"]):
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    # get units name from indexHYDRAU.txt file
                    unit_name_from_index_file = data_index_file[headers[time_index]][rowindex]
                    # check if lenght of two loading units
                    if unit_name_from_index_file not in hsr.timestep_name_list:
                        self.hydrau_description_list = "Error: " + unit_name_from_index_file + " don't exist in " + file
                        return
                    if file == data_index_file["filename"][-1]:  # last
                        variable_name_unit_dict = hsr.hvum.software_detected_list

                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    self.hydrau_description_list = "Error: selected files are different from indexHYDRAU files"
                    return

                # multi reach from file cases
                filename_list = data_index_file[headers[0]]
                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]]
                    # duplicates filename presence +
                    if len(filename_list) != len(list(set(filename_list))) and len(reach_name) != len(list(set(reach_name))) and \
                        len(list(set(filename_list))) == len(list(set(reach_name))):
                        reach_name = list(set(reach_name))
                        filename_list
                        list(data_index_file[headers[discharge_index]])

                    else:
                        reach_name = [data_index_file[headers[reach_index]][0]]
                else:
                    reach_name = ["unknown"]

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_full"] = [list(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_tf"] = [[True] * len(data_index_file[headers[discharge_index]])] * hsr.reach_number
                self.hydrau_description_list[0]["unit_number"] = str(len(data_index_file[headers[discharge_index]]))
                self.hydrau_description_list[0]["unit_type"] = "discharge [" + discharge_unit + "]"
                self.hydrau_description_list[0]["timestep_list"] = data_index_file[headers[time_index]]
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                self.hydrau_description_list[0]["flow_type"] = "continuous flow"  # transient flow

            # CASE 3.a """
            elif self.hydrau_case == "3.a":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(data_index_file[headers[0]][0],
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    self.hydrau_description_list = "Error: selected files are different from indexHYDRAU files"
                    return

                if reach_presence:
                    reach_name = [data_index_file[headers[reach_index]][0]]
                if not reach_presence:
                    reach_name = ["unknown"]

                variable_name_unit_dict = hsr.hvum.software_detected_list

                if self.model_type == "basement2d":
                    self.hydrau_description_list[0]["hdf5_name"] = hsr.simulation_name + ".hyd"

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = [list(hsr.timestep_name_list)] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_full"] = [list(hsr.timestep_name_list)] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_tf"] = [[True] * hsr.timestep_nb] * hsr.reach_number
                self.hydrau_description_list[0]["unit_number"] = str(hsr.timestep_nb)
                self.hydrau_description_list[0]["unit_type"] = hsr.timestep_unit
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                self.hydrau_description_list[0]["flow_type"] = "transient flow"  # continuous flow

            # CASE 3.b """
            elif self.hydrau_case == "3.b":
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
                                                         hsr.timestep_name_list[from_unit_index:to_unit_index + 1]
                        except ValueError:
                            self.hydrau_description_list = "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                                   data_index_file[headers[0]][0]
                            return
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
                    self.hydrau_description_list = "Error: selected files are different from indexHYDRAU files"
                    return

                if reach_presence:
                    reach_name = [data_index_file[headers[reach_index]][0]]
                if not reach_presence:
                    reach_name = ["unknown"]

                variable_name_unit_dict = hsr.hvum.software_detected_list

                if self.model_type == "basement2d":
                    self.hydrau_description_list[0]["hdf5_name"] = hsr.simulation_name + ".hyd"

                # self.hydrau_description_list
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = [unit_name_from_index_file2] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_full"] = [hsr.timestep_name_list] * hsr.reach_number
                self.hydrau_description_list[0]["unit_list_tf"] = [timestep_to_select] * hsr.reach_number
                self.hydrau_description_list[0]["unit_number"] = str(len(unit_name_from_index_file2))
                self.hydrau_description_list[0]["unit_type"] = "time [" + time_unit + "]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(1)
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                self.hydrau_description_list[0]["flow_type"] = "transient flow"  # continuous flow

            # CASE 4.a """
            elif self.hydrau_case == "4.a":
                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    self.hydrau_description_list = "Error: selected files are different from indexHYDRAU files"
                    return

                self.hydrau_description_list = []
                for i, file in enumerate(data_index_file[headers[0]]):
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)

                    # hdf5 filename
                    blob2, ext = os.path.splitext(file)
                    name_hdf5 = blob2 + ".hyd"

                    # reach name
                    if reach_presence:
                        reach_name = [data_index_file[headers[reach_index]][i]]
                    if not reach_presence:
                        reach_name = ["unknown"]

                    variable_name_unit_dict = hsr.hvum.software_detected_list

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
                                                             unit_list=[list(hsr.timestep_name_list)] * hsr.reach_number,
                                                             unit_list_full=[list(hsr.timestep_name_list)] * hsr.reach_number,
                                                             unit_list_tf=[[True] * hsr.timestep_nb] * hsr.reach_number,
                                                             unit_number=str(hsr.timestep_nb),
                                                             unit_type=hsr.timestep_unit,
                                                             reach_list=reach_name,
                                                             reach_number=str(1),
                                                             reach_type="river",
                                                             variable_name_unit_dict=variable_name_unit_dict,
                                                             flow_type="transient flow",
                                                             index_hydrau=True))  # continuous flow

            # CASE 4.b """
            elif self.hydrau_case == "4.b":
                # selected files same than indexHYDRAU file
                if not selectedfiles_textfiles_matching:
                    self.hydrau_description_list = "Error: selected files are different from indexHYDRAU files"
                    return

                # multi_reach
                if multi_reach:
                    # check if unit nb by reach is equal
                    unit_list_all_reach = []
                    unit_list_full_all_reach = []
                    unit_list_tf_all_reach = []
                    for i, file in enumerate(data_index_file[headers[0]]):
                        # get units name from file
                        hsr = HydraulicSimulationResultsSelector(file,
                                                                 self.folder_path, self.model_type, self.path_prj)
                        self.warning_list.extend(hsr.warning_list)
                        unit_list_full_all_reach.append(hsr.timestep_name_list)
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

                                    self.hydrau_description_list = "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                                           data_index_file[headers[0]][i]
                                    return
                            else:
                                unit_name_from_index_file2.append(element_unit)

                        unit_list_all_reach.append(unit_name_from_index_file2)

                        unit_index_from_file = []
                        for item in hsr.timestep_name_list:
                            if item in unit_name_from_index_file2:
                                unit_index_from_file.append(True)
                            else:
                                unit_index_from_file.append(False)
                        unit_list_tf_all_reach.append(unit_index_from_file)

                        variable_name_unit_dict = hsr.hvum.software_detected_list

                    # check if unit nb by reach is equal
                    unit_nb_list = []
                    for i, file in enumerate(data_index_file[headers[0]]):
                        unit_nb_list.append(len(unit_list_all_reach[i]))
                    if len(set(unit_nb_list)) > 1:
                        self.hydrau_description_list = "Error: Timestep number are not equal for selected reachs."
                        return

                    # self.hydrau_description_list
                    self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                    self.hydrau_description_list[0]["unit_list"] = list(unit_list_all_reach)
                    self.hydrau_description_list[0]["unit_list_full"] = list(unit_list_full_all_reach)
                    self.hydrau_description_list[0]["unit_list_tf"] = unit_list_tf_all_reach
                    self.hydrau_description_list[0]["unit_number"] = str(unit_nb_list[0])
                    self.hydrau_description_list[0]["unit_type"] = hsr.timestep_unit
                    self.hydrau_description_list[0]["reach_list"] = reach_list
                    self.hydrau_description_list[0]["reach_number"] = str(len(reach_list))
                    self.hydrau_description_list[0]["reach_type"] = "river"
                    self.hydrau_description_list[0]["variable_name_unit_dict"] = variable_name_unit_dict
                    self.hydrau_description_list[0]["flow_type"] = "transient flow"  # continuous flow

                # same reach
                else:
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

                                    self.hydrau_description_list = "Error: can't found time step : " + from_unit + " or " + to_unit + " in " + \
                                           data_index_file[headers[0]][i]
                                    return
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
                            reach_name = [data_index_file[headers[reach_index]][i]]
                        else:
                            reach_name = ["unknown"]

                        variable_name_unit_dict = hsr.hvum.software_detected_list

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
                                                                 unit_list=[list(unit_name_from_index_file2)],
                                                                 unit_list_full=[list(hsr.timestep_name_list)],
                                                                 unit_list_tf=[unit_index_from_file] * hsr.reach_number,
                                                                 unit_number=str(len(unit_name_from_index_file2)),
                                                                 unit_type="time [" + time_unit + "]",
                                                                 reach_list=reach_name,
                                                                 reach_number=str(1),
                                                                 reach_type="river",
                                                                 variable_name_unit_dict=variable_name_unit_dict,
                                                                 flow_type="transient flow",
                                                                 index_hydrau=True))  # continuous flow

        # if m3/s
        for hydrau_description_index in range(len(self.hydrau_description_list)):
            if "m3/s" in self.hydrau_description_list[hydrau_description_index]["unit_type"]:
                self.hydrau_description_list[hydrau_description_index]["unit_type"] = \
                self.hydrau_description_list[hydrau_description_index]["unit_type"].replace("m3/s", "m<sup>3</sup>/s")

        #print("------------------------------------------------")
        #print("self.hydrau_case, " + self.hydrau_case)
        # print(self.hydrau_description_list[0]["unit_list"])
        # print(self.hydrau_description_list[0]["unit_list_tf"])
        # print(self.hydrau_description_list[0]["unit_number"])


def create_index_hydrau_text_file(description_from_indexHYDRAU_file):
    if type(description_from_indexHYDRAU_file) == dict:
        """ ONE HDF5 """
        # one case (one hdf5 produced)
        filename_path = os.path.join(description_from_indexHYDRAU_file["path_prj"], "input", "indexHYDRAU.txt")
        # telemac case
        telemac_case = description_from_indexHYDRAU_file["hydrau_case"]

        # column filename
        filename_column = description_from_indexHYDRAU_file["filename_source"].split(", ")

        # nb_row
        nb_row = len(filename_column)

        """ CASE unknown """
        if telemac_case == "unknown":
            unit_type = description_from_indexHYDRAU_file["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            time_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]

            # headers
            headers = "filename" + "\t" + "T[" + time_unit + "]"

            # first line
            if description_from_indexHYDRAU_file["unit_list"] == \
                    description_from_indexHYDRAU_file["unit_list_full"]:
                unit_data = "all"
            else:
                index = [i for i, item in enumerate(description_from_indexHYDRAU_file["unit_list_full"]) if
                         item in description_from_indexHYDRAU_file["unit_list"]]
                my_sequences = []
                for idx, item in enumerate(index):
                    if not idx or item - 1 != my_sequences[-1][-1]:
                        my_sequences.append([item])
                    else:
                        my_sequences[-1].append(item)
                from_to_string_list = []
                for sequence in my_sequences:
                    start = min(sequence)
                    start_string = description_from_indexHYDRAU_file["unit_list_full"][start]
                    end = max(sequence)
                    end_string = description_from_indexHYDRAU_file["unit_list_full"][end]
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
            if description_from_indexHYDRAU_file["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # first line
            linetowrite = filename_column[0] + "\t" + str(description_from_indexHYDRAU_file["unit_list"][0])
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 1.b """
        if telemac_case == "1.b":
            if description_from_indexHYDRAU_file["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]" + "\t" + "T[s]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # first line
            linetowrite = filename_column[0] + "\t" + str(description_from_indexHYDRAU_file["unit_list"][0])
            linetowrite = linetowrite + "\t" + description_from_indexHYDRAU_file["unit_list_full"][0]
            if reach_column_presence:
                linetowrite = linetowrite + "\t" + reach_column
            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

        """ CASE 2.a """
        if telemac_case == "2.a":
            if description_from_indexHYDRAU_file["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # lines
            linetowrite = ""
            for row in range(nb_row):
                if description_from_indexHYDRAU_file["unit_list_tf"][row]:
                    linetowrite += filename_column[row] + "\t" + str(
                        description_from_indexHYDRAU_file["unit_list_full"][row])
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
            if description_from_indexHYDRAU_file["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            discharge_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + "Q[" + discharge_unit + "]" + "\t" + "T[s]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"
            # lines
            linetowrite = ""
            for row in range(nb_row):
                linetowrite += filename_column[row] + "\t" + str(
                    description_from_indexHYDRAU_file["unit_list"][row]) + "\t" + \
                               description_from_indexHYDRAU_file["timestep_list"][row]
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
            if description_from_indexHYDRAU_file["reach_list"] == "unknown":
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"].split(", ")[0]

            unit_type = description_from_indexHYDRAU_file["unit_type"]
            start = unit_type.find('[')
            end = unit_type.find(']')
            time_unit = unit_type[start + 1:end]
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + "T[" + time_unit + "]"
            if reach_column_presence:
                headers = headers + "\t" + "reachname"

            # first line
            if description_from_indexHYDRAU_file["unit_list"] == description_from_indexHYDRAU_file[
                "unit_list_full"]:
                unit_data = "all"
            else:
                index = [i for i, item in enumerate(description_from_indexHYDRAU_file["unit_list_full"]) if
                         item in description_from_indexHYDRAU_file["unit_list"]]
                my_sequences = []
                for idx, item in enumerate(index):
                    if not idx or item - 1 != my_sequences[-1][-1]:
                        my_sequences.append([item])
                    else:
                        my_sequences[-1].append(item)
                from_to_string_list = []
                for sequence in my_sequences:
                    start = min(sequence)
                    start_string = description_from_indexHYDRAU_file["unit_list_full"][start]
                    end = max(sequence)
                    end_string = description_from_indexHYDRAU_file["unit_list_full"][end]
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
        with open(filename_path, 'wt', encoding="utf-8") as f:
            f.write(text)

    else:
        """ MULTI HDF5 """
        # multi case (several hdf5 produced)
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
        with open(filename_path, 'wt', encoding="utf-8") as f:
            f.write(text)


def load_hydraulic_cut_to_hdf5(hydrau_description, progress_value, q, print_cmd=False, project_preferences={}):
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

    filename_source = hydrau_description["filename_source"].split(", ")

    delta_file = 80 / len(filename_source)

    data_2d = Data2d()  # data_2d
    hydrau_description["hyd_unit_correspondence"] = []  # always one reach by file ?
    # for each filename source
    for i, file in enumerate(filename_source):
        # get file informations
        hsr = HydraulicSimulationResultsSelector(file,
                                         hydrau_description["path_filename_source"],
                                         hydrau_description["model_type"],
                                         hydrau_description["path_prj"])
        # get timestep_name_list
        if hydrau_description["hydrau_case"] in {"1.a", "2.a"}:
            timestep_wish_list = [hsr.timestep_name_list]
        elif hydrau_description["hydrau_case"] in {"1.b"}:
            timestep_wish_list = [hydrau_description["timestep_list"]]
        elif hydrau_description["hydrau_case"] in {"2.b"}:
            timestep_wish_list = [[hydrau_description["timestep_list"][i]]]
        else:  # {"4.a", "4.b", "3.b", "3.a", "unknown"}:
            timestep_wish_list = hydrau_description["unit_list"]

        # multi_reach from several files
        if len(hydrau_description["reach_list"]) > 1 and len(filename_source) > 1:
            # load first reach
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[i])
            # check error
            if not data_2d_source:
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q and not print_cmd:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return

            data_2d.add_reach(data_2d_source, [0])
        # multi_reach from one files (HEC-RAS 2d, ASCII, .. ?)
        elif len(hydrau_description["reach_list"]) > 1 and len(filename_source) == 1:
            # load data
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[i])
            data_2d.add_reach(data_2d_source, list(range(len(hydrau_description["reach_list"]))))
        # one_reach
        else:
            # load data
            data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[0])
            # check error
            if not data_2d_source:
                # warnings
                if not print_cmd:
                    sys.stdout = sys.__stdout__
                    if q and not print_cmd:
                        q.put(mystdout)
                        sleep(0.1)  # to wait q.put() ..
                return
            for reach_number in range(data_2d_source.reach_number):
                # data_2d
                data_2d.add_unit(data_2d_source, reach_number)

    """ get data_2d_whole_profile """
    data_2d_whole_profile = data_2d.get_only_mesh()

    """ set unit_names """
    data_2d.set_unit_list(hydrau_description["unit_list"])

    """ varying mesh """
    hyd_varying_xy_index, hyd_varying_z_index = data_2d_whole_profile.get_hyd_varying_xy_and_z_index()
    for reach_number in range(len(hyd_varying_xy_index)):
        if len(set(hyd_varying_xy_index[reach_number])) == 1:  # one tin for all unit
            hyd_varying_mesh = False
            data_2d_whole_profile.reduce_to_first_unit_by_reach()
        else:
            hyd_varying_mesh = True
        # hyd_unit_z_equal ?
        if len(set(hyd_varying_z_index[reach_number])) == 1:
            hyd_unit_z_equal = True
        else:
            hyd_unit_z_equal = True

        # one file : one reach, varying_mesh==False
        if len(filename_source) == 1:
            hydrau_description["hyd_unit_correspondence"].append(hyd_varying_xy_index[reach_number])
        else:
            hydrau_description["hyd_unit_correspondence"].append(hyd_varying_xy_index[reach_number])

    """ check_validity """
    data_2d.check_validity()

    """ set_min_height_to_0 """
    data_2d.set_min_height_to_0(project_preferences['min_height_hyd'])

    """ remove_dry_mesh """
    data_2d.remove_dry_mesh()
    if data_2d.unit_number == 0:
        print("Error: All selected units or timestep are entirely dry.")
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    """ semi_wetted_mesh_cutting """
    if project_preferences["cut_mesh_partialy_dry"]:
        data_2d.semi_wetted_mesh_cutting(hydrau_description["unit_list"],
                                         progress_value,
                                         delta_file)
    if data_2d.unit_number == 0:
        print("Error: All selected units or timestep are not hydraulically operable.")
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    """ bank hydraulic aberations  """
    # data_2d.fix_aberrations(npasses=1, tolerance=0.01, connectedness_criterion=True, bank_depth=0.05)
    # cProfile.runctx("data_2d.fix_aberrations(npasses=1, tolerance=0.01, connectedness_criterion=False, bank_depth=1)",globals={},locals={"data_2d":data_2d},filename="c:/habby_dev/files/cut6.profile")

    """ re compute area """
    if not data_2d.hvum.area.name in data_2d.hvum.hdf5_and_computable_list.names():
        data_2d.hvum.area.hdf5 = True  # variable
        data_2d.hvum.hdf5_and_computable_list.append(data_2d.hvum.area)
    data_2d.compute_variables([data_2d.hvum.area])

    """ remove null area """
    data_2d.remove_null_area()

    """ get_dimension """
    data_2d.get_dimension()

    # hyd description
    data_2d.filename_source = hydrau_description["filename_source"]
    data_2d.path_filename_source = hydrau_description["path_filename_source"]
    data_2d.hyd_model_type = hydrau_description["model_type"]
    data_2d.hyd_model_dimension = hydrau_description["model_dimension"]
    data_2d.epsg_code = hydrau_description["epsg_code"]
    data_2d.reach_list = hydrau_description["reach_list"]
    data_2d.reach_number = int(hydrau_description["reach_number"])
    data_2d.reach_type = hydrau_description["reach_type"]
    reach_unit_list_str = []
    for reach_number in range(data_2d.reach_number):
        unit_list_str = []
        for unit_name in hydrau_description["unit_list"][reach_number]:
            unit_list_str.append(unit_name.replace(":", "_").replace(" ", "_"))
        reach_unit_list_str.append(unit_list_str)
    data_2d.unit_list = reach_unit_list_str
    data_2d.unit_number = len(hydrau_description["unit_list"][0])
    data_2d.unit_type = hydrau_description["unit_type"]
    data_2d.hyd_varying_mesh = hyd_varying_mesh
    data_2d.hyd_unit_z_equal = hyd_unit_z_equal
    data_2d.hyd_unit_correspondence = hydrau_description["hyd_unit_correspondence"]
    data_2d.hyd_cuted_mesh_partialy_dry = project_preferences["cut_mesh_partialy_dry"]
    data_2d.hyd_hydrau_case = hydrau_description["hydrau_case"]
    if data_2d.hyd_hydrau_case in {"1.b", "2.b"}:
        data_2d.hyd_timestep_source_list = [hydrau_description["timestep_list"]]
    data_2d.hs_calculated = False

    # create hdf5
    path_prj = hydrau_description["path_prj"]
    hdf5_name = hydrau_description["hdf5_name"]
    hdf5 = hdf5_mod.Hdf5Management(path_prj, hdf5_name, new=True)
    # HYD
    if not data_2d.hvum.hdf5_and_computable_list.subs():
        project_preferences_index = 0
        hdf5.create_hdf5_hyd(data_2d,
                             data_2d_whole_profile,
                             project_preferences)
    # HAB
    else:
        project_preferences_index = 1
        data_2d.sub_mapping_method = hsr.sub_mapping_method
        data_2d.sub_classification_code = hsr.sub_classification_code
        data_2d.sub_classification_method = hsr.sub_classification_method
        hdf5.create_hdf5_hab(data_2d,
                             data_2d_whole_profile,
                             project_preferences)

    # create_index_hydrau_text_file
    if not hydrau_description["index_hydrau"]:
        create_index_hydrau_text_file(hydrau_description)

    # export
    export_dict = dict()
    nb_export = 0
    for key in hdf5.available_export_list:
        if project_preferences[key][project_preferences_index]:
            nb_export += 1
        export_dict[key + "_" + hdf5.extension[1:]] = project_preferences[key][project_preferences_index]

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    progress_value.value = 100.0


def merge_grid_and_save(hdf5_name_hyd, hdf5_name_sub, hdf5_name_hab, path_prj, progress_value, q=[], print_cmd=False,
                        project_preferences={}):
    """
    This function call the merging of the grid between the grid from the hydrological data and the substrate data.
    It then save the merged data and the substrate data in a common hdf5 file. This function is called in a second
    thread to avoid freezin gthe GUI. This is why we have this extra-function just to call save_hdf5() and
    merge_grid_hydro_sub().

    :param hdf5_name_hyd: the name of the hdf5 file with the hydrological data
    :param hdf5_name_sub: the name of the hdf5 with the substrate data
    :param hdf5_name_hab: the name of the hdf5 merge output
    :param path_hdf5: the path to the hdf5 data
    :param name_prj: the name of the project
    :param path_prj: the path to the project
    :param model_type: the type of the "model". In this case, it is just 'SUBSTRATE'
    :param q: used to share info with the GUI when this thread have finsihed (print_cmd = False)
    :param print_cmd: If False, print to the GUI (usually False)
    :param path_shp: the path where to save the shp file with hydro and subtrate. If empty, the shp file is not saved.
    :param: erase_id should we erase old shapefile from the same model or not.
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # progress
    progress_value.value = 10

    # get_translator
    qt_tr = get_translator(project_preferences['path_prj'])

    # if exists
    if not os.path.exists(os.path.join(path_prj, "hdf5", hdf5_name_hyd)):
        print('Error: ' + qt_tr.translate("mesh_management_mod",
                                          "The specified file : " + hdf5_name_hyd + " don't exist."))
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    if not os.path.exists(os.path.join(path_prj, "hdf5", hdf5_name_sub)):
        print('Error: ' + qt_tr.translate("mesh_management_mod",
                                          "The specified file : " + hdf5_name_sub + " don't exist."))
        # warnings
        if not print_cmd:
            sys.stdout = sys.__stdout__
            if q and not print_cmd:
                q.put(mystdout)
                sleep(0.1)  # to wait q.put() ..
        return

    # load hdf5 hydro
    hdf5_hydro = hdf5_mod.Hdf5Management(path_prj, hdf5_name_hyd, new=False, edit=False)
    hdf5_hydro.load_hdf5_hyd(units_index="all", whole_profil=True)

    # load hdf5 sub
    hdf5_sub = hdf5_mod.Hdf5Management(path_prj, hdf5_name_sub, new=False, edit=False)
    hdf5_sub.load_hdf5_sub()

    # CONSTANT CASE
    if hdf5_sub.data_2d.sub_mapping_method == "constant":  # set default value to all mesh
        data_2d_merge = hdf5_hydro.data_2d
        data_2d_whole_merge = hdf5_hydro.data_2d_whole
        data_2d_merge.set_sub_cst_value(hdf5_sub)

    # POLYGON AND POINTS CASES
    elif hdf5_sub.data_2d.sub_mapping_method != "constant":
        # check if EPSG are integer and if TRUE they must be equal
        epsg_hyd = hdf5_hydro.data_2d.epsg_code
        epsg_sub = hdf5_sub.data_2d.epsg_code
        if epsg_hyd.isdigit() and epsg_sub.isdigit():
            if epsg_hyd == epsg_sub:
                hab_epsg_code = epsg_hyd
            if epsg_hyd != epsg_sub:
                print(
                    "Error : Merging failed. EPSG codes are different between hydraulic and substrate data : " + epsg_hyd + ", " + epsg_sub)
                return
        if not epsg_hyd.isdigit() and epsg_sub.isdigit():
            print(
                "Warning : EPSG code of hydraulic data is unknown (" + epsg_hyd + ") "
                                                                                  "and EPSG code of substrate data is known (" + epsg_sub + "). " +
                "The merging data will still be calculated.")
            hab_epsg_code = epsg_sub
        if epsg_hyd.isdigit() and not epsg_sub.isdigit():
            print(
                "Warning : EPSG code of hydraulic data is known (" + epsg_hyd + ") "
                                                                                "and EPSG code of substrate data is unknown (" + epsg_sub + "). " +
                "The merging data will still be calculated.")
            hab_epsg_code = epsg_hyd
        if not epsg_hyd.isdigit() and not epsg_sub.isdigit():
            print(
                "Warning : EPSG codes of hydraulic and substrate data are unknown : " + epsg_hyd + " ; "
                + epsg_sub + ". The merging data will still be calculated.")
            hab_epsg_code = epsg_hyd

        # check if extent match
        extent_hyd = hdf5_hydro.data_2d.data_extent
        extent_sub = hdf5_sub.data_2d.data_extent
        if (extent_hyd[2] < extent_sub[0] or extent_hyd[0] > extent_sub[2] or
                extent_hyd[3] < extent_sub[1] or extent_hyd[1] > extent_sub[3]):
            print("Warning : No intersection found between hydraulic and substrate data (from extent intersection).")
            extent_intersect = False
        else:
            extent_intersect = True

        # check if whole profile is equal for all timestep
        if not hdf5_hydro.data_2d.hyd_varying_mesh:
            # have to check intersection for only one timestep
            pass
        else:
            # TODO : merge for all time step
            pass

        # no intersect
        if not extent_intersect:  # set default value to all mesh
            data_2d_merge = hdf5_hydro.data_2d
            data_2d_whole_merge = hdf5_hydro.data_2d_whole
            data_2d_merge.set_sub_cst_value(hdf5_sub)
        # intersect
        else:
            data_2d_merge = Data2d(reach_number=hdf5_hydro.data_2d.reach_number,
                                   unit_number=hdf5_hydro.data_2d.unit_number)  # new
            # get hyd attr
            data_2d_merge.__dict__ = hdf5_hydro.data_2d.__dict__.copy()
            data_2d_merge.__dict__["hyd_filename_source"] = data_2d_merge.__dict__.pop("filename_source")
            data_2d_merge.__dict__["hyd_path_filename_source"] = data_2d_merge.__dict__.pop("path_filename_source")
            # get sub attr
            for attribute_name in hdf5_sub.data_2d.__dict__.keys():
                attribute_value = getattr(hdf5_sub.data_2d, attribute_name)
                if attribute_name in {"filename_source", "path_filename_source"}:
                    setattr(data_2d_merge, "sub_" + attribute_name, attribute_value)
                if attribute_name[:3] == "sub":
                    setattr(data_2d_merge, attribute_name, attribute_value)
            data_2d_merge.hab_animal_list = ", ".join([])
            data_2d_merge.hab_animal_number = 0
            data_2d_merge.hab_animal_pref_list = ", ".join([])
            data_2d_merge.hab_animal_stage_list = ", ".join([])

            data_2d_whole_merge = hdf5_hydro.data_2d_whole
            data_2d_merge.epsg_code = hab_epsg_code

            data_2d_merge.hvum = hdf5_hydro.data_2d.hvum  # hyd variables
            data_2d_merge.hvum.hdf5_and_computable_list.extend(hdf5_sub.data_2d.hvum.hdf5_and_computable_list)  # sub variables
            hyd_xy_list = []
            hyd_data_node_list = []
            hyd_tin_list = []
            iwholeprofile_list = []
            hyd_data_mesh_list = []
            sub_xy_list = []
            sub_tin_list = []
            sub_data_list = []
            sub_default_list = []
            coeffgrid_list = []
            delta_mesh_list = []
            # progress
            delta_reach = 80 / hdf5_hydro.data_2d.reach_number
            # for each reach
            for reach_number in range(0, hdf5_hydro.data_2d.reach_number):
                # progress
                delta_unit = delta_reach / hdf5_hydro.data_2d.unit_number
                # for each unit
                for unit_number in range(0, hdf5_hydro.data_2d.unit_number):
                    # progress
                    delta_mesh = delta_unit / hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["tin"].shape[0]

                    # conta args to list to Pool
                    hyd_xy_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["node"]["xy"])
                    hyd_data_node_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["node"]["data"].to_numpy())
                    hyd_tin_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["tin"])
                    iwholeprofile_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"])
                    hyd_data_mesh_list.append(hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["data"].to_numpy())
                    sub_xy_list.append(hdf5_sub.data_2d[0][0]["node"]["xy"])
                    sub_tin_list.append(hdf5_sub.data_2d[0][0]["mesh"]["tin"])
                    sub_data_list.append(hdf5_sub.data_2d[0][0]["mesh"]["data"].to_numpy())
                    sub_default_list.append(np.array(hdf5_sub.data_2d.sub_default_values))
                    coeffgrid_list.append(10)
                    delta_mesh_list.append(delta_mesh)

            # Compute Pool
            input_data = zip(hyd_xy_list,
                             hyd_data_node_list,
                             hyd_tin_list,
                             iwholeprofile_list,
                             hyd_data_mesh_list,
                             sub_xy_list,
                             sub_tin_list,
                             sub_data_list,
                             sub_default_list,
                             coeffgrid_list,
                             delta_mesh_list)

            # start jobs
            lock = Lock()  # to share progress_value
            pool = Pool(processes=2, initializer=setup, initargs=[progress_value, lock])
            results = pool.starmap(merge, input_data)

            # for each reach
            index_loop = -1
            for reach_number in range(0, hdf5_hydro.data_2d.reach_number):
                # for each unit
                for unit_number in range(0, hdf5_hydro.data_2d.unit_number):
                    index_loop = index_loop + 1
                    merge_xy, merge_data_node, merge_tin, merge_i_whole_profile, merge_data_mesh, merge_data_sub = results[index_loop]

                    # get mesh data
                    data_2d_merge[reach_number][unit_number]["mesh"]["tin"] = merge_tin
                    data_2d_merge[reach_number][unit_number]["mesh"]["data"] = DataFrame()
                    for colname_num, colname in enumerate(hdf5_hydro.data_2d[0][0]["mesh"]["data"].columns):
                        if colname == "i_whole_profile":
                            data_2d_merge[reach_number][unit_number]["mesh"]["data"][colname] = merge_i_whole_profile[:, 0]
                        elif colname == "i_split":
                            data_2d_merge[reach_number][unit_number]["mesh"]["data"][colname] = merge_i_whole_profile[:, 1]
                        else:
                            data_2d_merge[reach_number][unit_number]["mesh"]["data"][colname] = merge_data_mesh[:,
                                                                                          colname_num]
                    data_2d_merge[reach_number][unit_number]["mesh"]["i_whole_profile"] = merge_i_whole_profile
                    # sub_defaut
                    data_2d_merge[reach_number][unit_number]["mesh"]["data"][data_2d_merge.hvum.i_sub_defaut.name] = merge_i_whole_profile[:, 2]

                    # get mesh sub data
                    for sub_class_num, sub_class_name in enumerate(
                            hdf5_sub.data_2d.hvum.hdf5_and_computable_list.hdf5s().names()):
                        data_2d_merge[reach_number][unit_number]["mesh"]["data"][sub_class_name] = merge_data_sub[:,
                                                                                             sub_class_num]

                    # get node data
                    data_2d_merge[reach_number][unit_number]["node"]["xy"] = merge_xy
                    data_2d_merge[reach_number][unit_number]["node"]["data"] = DataFrame()
                    for colname_num, colname in enumerate(hdf5_hydro.data_2d[0][0]["node"]["data"].columns):
                        data_2d_merge[reach_number][unit_number]["node"]["data"][colname] = merge_data_node[:, colname_num]

                    # post process merge
                    if data_2d_merge[reach_number][unit_number]["node"]["data"][data_2d_merge.hvum.h.name].min() < 0:
                        print("Error: negative water height values detected after merging with substrate.")

                    # # plot_to_check_mesh_merging
                    # plot_to_check_mesh_merging(hyd_xy=hdf5_hydro.data_2d[reach_number][unit_number]["node"]["xy"],
                    #                            hyd_tin=hdf5_hydro.data_2d[reach_number][unit_number]["mesh"]["tin"],
                    #
                    #                            sub_xy=hdf5_sub.data_2d[reach_number][unit_number]["node"]["xy"],
                    #                            sub_tin=hdf5_sub.data_2d[reach_number][unit_number]["mesh"]["tin"],
                    #                            sub_data=hdf5_sub.data_2d[reach_number][unit_number]["mesh"]["data"]["sub_coarser"].to_numpy(),
                    #
                    #                            merge_xy=data_2d_merge[reach_number][unit_number]["node"]["xy"],
                    #                            merge_tin=data_2d_merge[reach_number][unit_number]["mesh"]["tin"],
                    #                            merge_data=data_2d_merge[reach_number][unit_number]["mesh"]["data"]["sub_coarser"].to_numpy())

            # new variables
            data_2d_merge.hvum.i_sub_defaut.position = "mesh"
            data_2d_merge.hvum.i_sub_defaut.hdf5 = True
            data_2d_merge.hvum.hdf5_and_computable_list.append(data_2d_merge.hvum.i_sub_defaut)

            # compute area (always after merge)
            data_2d_merge.hvum.area.hdf5 = False
            data_2d_merge.hvum.area.position = "mesh"
            data_2d_merge.hvum.all_final_variable_list.append(data_2d_merge.hvum.area)
            data_2d_merge.compute_variables(data_2d_merge.hvum.all_final_variable_list.to_compute())
            if not data_2d_merge.hvum.area.name in data_2d_merge.hvum.hdf5_and_computable_list.names():
                data_2d_merge.hvum.area.hdf5 = True
                data_2d_merge.hvum.hdf5_and_computable_list.append(data_2d_merge.hvum.area)

            # get_dimension
            data_2d_merge.get_dimension()

    # progress
    progress_value.value = 90

    # create hdf5 hab
    data_2d_merge["filename"] = hdf5_name_hab
    hdf5 = hdf5_mod.Hdf5Management(path_prj, hdf5_name_hab, new=True)
    hdf5.create_hdf5_hab(data_2d_merge, data_2d_whole_merge, project_preferences)

    # export
    export_dict = dict()
    nb_export = 0
    for key in hdf5.available_export_list:
        if project_preferences[key][1]:
            nb_export += 1
        export_dict[key + "_" + hdf5.extension[1:]] = project_preferences[key][1]

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0


def load_data_and_compute_hs(hydrosignature_description, progress_value, q=[], print_cmd=False, project_preferences={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_properties_dict()

    # progress
    progress_value.value = 10

    path_prj = project_preferences["path_prj"]

    # compute
    if hydrosignature_description["hs_export_mesh"]:
        hdf5 = hdf5_mod.Hdf5Management(path_prj, hydrosignature_description["hdf5_name"], new=False, edit=True)
        hdf5.hydrosignature_new_file(progress_value,
                                     hydrosignature_description["classhv"],
                                     hydrosignature_description["hs_export_txt"])
        # load new hs_data to original hdf5
        hdf5_new = hdf5_mod.Hdf5Management(path_prj, hdf5.filename[:-4] + "_HS" + hdf5.extension, new=False, edit=False)
        hdf5_new.load_hydrosignature()
        hdf5.data_2d = hdf5_new.data_2d
        hdf5.write_hydrosignature()
    else:
        hdf5 = hdf5_mod.Hdf5Management(path_prj, hydrosignature_description["hdf5_name"], new=False, edit=True)
        hdf5.add_hs(progress_value,
                    hydrosignature_description["classhv"],
                    False,
                    hydrosignature_description["hs_export_txt"])
        # check error
        if not hdf5.hs_calculated:
            # warnings
            if not print_cmd:
                sys.stdout = sys.__stdout__
                if q and not print_cmd:
                    q.put(mystdout)
                    sleep(0.1)  # to wait q.put() ..
            return

    # warnings
    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            sleep(0.1)  # to wait q.put() ..

    # prog
    progress_value.value = 100.0


def load_hs_and_compare(hdf5name_1, reach_index_list_1, unit_index_list_1,
                        hdf5name_2, reach_index_list_2, unit_index_list_2,
                        all_possibilities, out_filename, path_prj):
    # create hdf5 class
    hdf5_1 = hdf5_mod.Hdf5Management(path_prj, hdf5name_1, new=False, edit=False)
    hdf5_1.load_hydrosignature()
    hdf5_2 = hdf5_mod.Hdf5Management(path_prj, hdf5name_2, new=False, edit=False)
    hdf5_2.load_hydrosignature()

    name_list_1 = [""]
    name_list_2 = [""]
    table_list_1 = []
    table_list_2 = []
    reach_name_1_list = []
    unit_name_1_list = []
    for reach_num_1 in reach_index_list_1:
        for unit_num_1 in unit_index_list_1:
            reach_name_1 = hdf5_1.data_2d[reach_num_1][unit_num_1].reach_name
            unit_name_1 = hdf5_1.data_2d[reach_num_1][unit_num_1].unit_name
            col_name = hdf5name_1 + "_" + reach_name_1 + "_" + unit_name_1
            name_list_1.append(col_name)
            table_list_1.append((hdf5_1, reach_num_1, unit_num_1))
            # templist
            reach_name_1_list.append(reach_name_1)
            unit_name_1_list.append(unit_name_1)
    for reach_num_2 in reach_index_list_2:
        for unit_num_2 in unit_index_list_2:
            reach_name_2 = hdf5_2.data_2d[reach_num_2][unit_num_2].reach_name
            unit_name_2 = hdf5_2.data_2d[reach_num_2][unit_num_2].unit_name
            col_name = hdf5name_2 + "_" + reach_name_2 + "_" + unit_name_2
            # all same
            if not all_possibilities:
                if reach_name_2 in reach_name_1_list and unit_name_2 in unit_name_1_list:
                    name_list_2.append(col_name)
                    table_list_2.append((hdf5_2, reach_num_2, unit_num_2))
            else:
                name_list_2.append(col_name)
                table_list_2.append((hdf5_2, reach_num_2, unit_num_2))

    # compute combination
    combination_list = []
    for i in table_list_1:
        for j in table_list_2:
            combination_list.append((i, j))

    # compute hscomparison area
    data_list = []
    for comb in combination_list:
        # first
        first_comp = comb[0]
        classhv1 = first_comp[0].hs_input_class
        hs1 = first_comp[0].data_2d[first_comp[1]][first_comp[2]].hydrosignature["hsarea"]
        # second
        second_comp = comb[1]
        classhv2 = second_comp[0].hs_input_class
        hs2 = second_comp[0].data_2d[second_comp[1]][second_comp[2]].hydrosignature["hsarea"]
        # comp
        done_tf, hs_comp_value = hscomparison(classhv1=classhv1,
                                              hs1=hs1,
                                              classhv2=classhv2,
                                              hs2=hs2)
        # append
        data_list.append(str(hs_comp_value))

    row_area_list = []
    for ind, x in enumerate(range(0, len(data_list), len(name_list_2) - 1)):
        row_list = [name_list_1[ind + 1]] + data_list[x:x + len(name_list_2) - 1]
        row_area_list.append(row_list)
    row_area_list.insert(0, name_list_2)

    # compute hscomparison volume
    data_list = []
    for comb in combination_list:
        # first
        first_comp = comb[0]
        classhv1 = first_comp[0].hs_input_class
        hs1 = first_comp[0].data_2d[first_comp[1]][first_comp[2]].hydrosignature["hsvolume"]
        # second
        second_comp = comb[1]
        classhv2 = second_comp[0].hs_input_class
        hs2 = second_comp[0].data_2d[second_comp[1]][second_comp[2]].hydrosignature["hsvolume"]
        # comp
        done_tf, hs_comp_value = hscomparison(classhv1=classhv1,
                                              hs1=hs1,
                                              classhv2=classhv2,
                                              hs2=hs2)
        # append
        data_list.append(str(hs_comp_value))

    row_volume_list = []
    for ind, x in enumerate(range(0, len(data_list), len(name_list_2) - 1)):
        row_list = [name_list_1[ind + 1]] + data_list[x:x + len(name_list_2) - 1]
        row_volume_list.append(row_list)
    row_volume_list.insert(0, name_list_2)

    # write file
    f = open(os.path.join(path_prj, "output", "text", out_filename), 'w')
    f.write("area" + '\n')
    for row in row_area_list:
        f.write("\t".join(row) + '\n')
    f.write('\n' + "volume" + '\n')
    for row in row_volume_list:
        f.write("\t".join(row) + '\n')
    f.close()


