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
from io import StringIO
from itertools import product
from time import sleep
import numpy as np

from PyQt5.QtCore import QCoreApplication as qt_tr, QThread, pyqtSignal
from multiprocessing import Process, Value

from src.hdf5_mod import Hdf5Management
from src.hydrosignature import hscomparison
from src.tools_mod import sort_homogoeneous_dict_list_by_on_key
from src.project_properties_mod import create_default_project_properties_dict
from src import hdf5_mod
from src.hydraulic_results_manager_mod import HydraulicSimulationResultsSelector
from src.data_2d_mod import Data2d
from src import plot_mod
from src.tools_mod import create_map_plot_string_dict
from src.dev_tools import profileit


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
                                                    unit_list=[list(hsr.timestep_name_list)] * hsr.reach_number,
                                                    unit_list_full=[list(hsr.timestep_name_list)] * hsr.reach_number,
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
        filename_source = hydrau_description[hdf5_file_index]["filename_source"].split(", ")
        data_2d = Data2d()  # data_2d
        hydrau_description[hdf5_file_index]["hyd_unit_correspondence"] = []  # always one reach by file ?
        # for each filename source
        for i, file in enumerate(filename_source):
            # get file informations
            hsr = HydraulicSimulationResultsSelector(file,
                                             hydrau_description[hdf5_file_index]["path_filename_source"],
                                             hydrau_description[hdf5_file_index]["model_type"],
                                             hydrau_description[hdf5_file_index]["path_prj"])
            # get timestep_name_list
            if hydrau_description[hdf5_file_index]["hydrau_case"] in {"1.a", "2.a"}:
                timestep_wish_list = [hsr.timestep_name_list]
            elif hydrau_description[hdf5_file_index]["hydrau_case"] in {"1.b"}:
                timestep_wish_list = [hydrau_description[hdf5_file_index]["timestep_list"]]
            elif hydrau_description[hdf5_file_index]["hydrau_case"] in {"2.b"}:
                timestep_wish_list = [[hydrau_description[hdf5_file_index]["timestep_list"][i]]]
            else:  # {"4.a", "4.b", "3.b", "3.a", "unknown"}:
                timestep_wish_list = hydrau_description[hdf5_file_index]["unit_list"]

            # multi_reach from several files
            if len(hydrau_description[hdf5_file_index]["reach_list"]) > 1 and len(filename_source) > 1:
                # load first reach
                data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[i])
                # check error
                if not data_2d_source and not print_cmd:
                    q.put(mystdout)
                    return
                data_2d.add_reach(data_2d_source, [0])
            # multi_reach from one files (HEC-RAS 2d, ASCII, .. ?)
            elif len(hydrau_description[hdf5_file_index]["reach_list"]) > 1 and len(filename_source) == 1:
                # load data
                data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[i])
                data_2d.add_reach(data_2d_source, list(range(len(hydrau_description[hdf5_file_index]["reach_list"]))))
            # one_reach
            else:
                # load data
                data_2d_source, description_from_source = hsr.load_hydraulic(timestep_wish_list[0])
                # check error
                if not data_2d_source and not print_cmd:
                    q.put(mystdout)
                    return
                for reach_number in range(data_2d_source.reach_number):
                    # data_2d
                    data_2d.add_unit(data_2d_source, reach_number)

        """ get data_2d_whole_profile """
        data_2d_whole_profile = data_2d.get_only_mesh()

        """ set unit_names """
        data_2d.set_unit_names(hydrau_description[hdf5_file_index]["unit_list"])

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
                hydrau_description[hdf5_file_index]["hyd_unit_correspondence"].append(hyd_varying_xy_index[reach_number])
            else:
                hydrau_description[hdf5_file_index]["hyd_unit_correspondence"].append(hyd_varying_xy_index[reach_number])

        """ check_validity """
        data_2d.check_validity()

        """ set_min_height_to_0 """
        data_2d.set_min_height_to_0(project_preferences['min_height_hyd'])

        """ remove_dry_mesh """
        data_2d.remove_dry_mesh()
        if data_2d.unit_number == 0:
            print("Error: All selected units or timestep are entirely dry.")
            if not print_cmd:
                q.put(mystdout)
            return

        """ semi_wetted_mesh_cutting """
        if project_preferences["cut_mesh_partialy_dry"]:
            data_2d.semi_wetted_mesh_cutting(hydrau_description[hdf5_file_index]["unit_list"],
                                             progress_value,
                                             delta_file)
        if data_2d.unit_number == 0:
            print("Error: All selected units or timestep are not hydraulically operable.")
            if not print_cmd:
                q.put(mystdout)
            return

        """ bank hydraulic aberations  """
        # data_2d.fix_aberrations(tolerance=0.001, npasses=5)

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
        data_2d.filename_source = hydrau_description[hdf5_file_index]["filename_source"]
        data_2d.path_filename_source = hydrau_description[hdf5_file_index]["path_filename_source"]
        data_2d.hyd_model_type = hydrau_description[hdf5_file_index]["model_type"]
        data_2d.hyd_model_dimension = hydrau_description[hdf5_file_index]["model_dimension"]
        data_2d.epsg_code = hydrau_description[hdf5_file_index]["epsg_code"]
        data_2d.reach_list = hydrau_description[hdf5_file_index]["reach_list"]
        data_2d.reach_number = int(hydrau_description[hdf5_file_index]["reach_number"])
        data_2d.reach_type = hydrau_description[hdf5_file_index]["reach_type"]
        reach_unit_list_str = []
        for reach_number in range(data_2d.reach_number):
            unit_list_str = []
            for unit_name in hydrau_description[hdf5_file_index]["unit_list"][reach_number]:
                unit_list_str.append(unit_name.replace(":", "_").replace(" ", "_"))
            reach_unit_list_str.append(unit_list_str)
        data_2d.unit_list = reach_unit_list_str
        data_2d.unit_number = len(hydrau_description[hdf5_file_index]["unit_list"][0])
        data_2d.unit_type = hydrau_description[hdf5_file_index]["unit_type"]
        data_2d.hyd_varying_mesh = hyd_varying_mesh
        data_2d.hyd_unit_z_equal = hyd_unit_z_equal
        data_2d.hyd_unit_correspondence = hydrau_description[hdf5_file_index]["hyd_unit_correspondence"]
        data_2d.hyd_cuted_mesh_partialy_dry = project_preferences["cut_mesh_partialy_dry"]
        data_2d.hyd_hydrau_case = hydrau_description[hdf5_file_index]["hydrau_case"]
        if data_2d.hyd_hydrau_case in {"1.b", "2.b"}:
            data_2d.hyd_timestep_source_list = [hydrau_description[hdf5_file_index]["timestep_list"]]
        data_2d.hs_calculated = False

        # create hdf5
        hdf5 = hdf5_mod.Hdf5Management(hydrau_description[hdf5_file_index]["path_prj"],
                                       hydrau_description[hdf5_file_index]["hdf5_name"],
                                       new=True)
        hdf5.create_hdf5_hyd(data_2d,
                             data_2d_whole_profile,
                             project_preferences)

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


def load_data_and_compute_hs(hydrosignature_description, progress_value, q=[], print_cmd=False, project_preferences={}):
    if not print_cmd:
        sys.stdout = mystdout = StringIO()

    # minimum water height
    if not project_preferences:
        project_preferences = create_default_project_properties_dict()

    # progress
    progress_value.value = 10

    # compute
    hdf5 = hdf5_mod.Hdf5Management(project_preferences["path_prj"],
                                   hydrosignature_description["hdf5_name"],
                                   new=False)

    if hydrosignature_description["hs_export_mesh"]:
        hdf5.hydrosignature_new_file(progress_value,
                                     hydrosignature_description["classhv"],
                                     hydrosignature_description["hs_export_txt"])
    else:
        hdf5.add_hs(progress_value,
                    hydrosignature_description["classhv"],
                    False,
                    hydrosignature_description["hs_export_txt"])

    # prog
    progress_value.value = 100

    if not print_cmd:
        sys.stdout = sys.__stdout__
        if q and not print_cmd:
            q.put(mystdout)
            return
        else:
            return


def load_hs_and_compare(hdf5name_1, reach_index_list_1, unit_index_list_1,
                        hdf5name_2, reach_index_list_2, unit_index_list_2,
                        all_possibilities, out_filename, path_prj):
    # create hdf5 class
    hdf5_1 = hdf5_mod.Hdf5Management(path_prj, hdf5name_1)
    hdf5_1.create_or_open_file(False)
    hdf5_1.load_hydrosignature()
    hdf5_2 = hdf5_mod.Hdf5Management(path_prj, hdf5name_2)
    hdf5_2.create_or_open_file(False)
    hdf5_2.load_hydrosignature()

    col_row_name_list = [""]
    table_list = []
    reach_name_1_list = []
    unit_name_1_list = []
    for reach_num_1 in reach_index_list_1:
        for unit_num_1 in unit_index_list_1:
            reach_name_1 = hdf5_1.data_2d[reach_num_1][unit_num_1].reach_name
            unit_name_1 = hdf5_1.data_2d[reach_num_1][unit_num_1].unit_name
            col_name = hdf5name_1 + "_" + reach_name_1 + "_" + unit_name_1
            col_row_name_list.append(col_name)
            table_list.append((hdf5_1, reach_num_1, unit_num_1))
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
                    col_row_name_list.append(col_name)
                    table_list.append((hdf5_2, reach_num_2, unit_num_2))
            else:
                col_row_name_list.append(col_name)
                table_list.append((hdf5_2, reach_num_2, unit_num_2))

    # compute combination
    combination_list = list(product(table_list, repeat=2))

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
    for ind, x in enumerate(range(0, len(data_list), len(col_row_name_list) - 1)):
        row_list = [col_row_name_list[ind + 1]] + data_list[x:x + len(col_row_name_list) - 1]
        row_area_list.append(row_list)
    row_area_list.insert(0, col_row_name_list)

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
    for ind, x in enumerate(range(0, len(data_list), len(col_row_name_list) - 1)):
        row_list = [col_row_name_list[ind + 1]] + data_list[x:x + len(col_row_name_list) - 1]
        row_volume_list.append(row_list)
    row_volume_list.insert(0, col_row_name_list)

    # write file
    f = open(os.path.join(path_prj, "output", "text", out_filename), 'w')
    f.write("area" + '\n')
    for row in row_area_list:
        f.write("\t".join(row) + '\n')
    f.write('\n' + "volume" + '\n')
    for row in row_volume_list:
        f.write("\t".join(row) + '\n')
    f.close()


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
        self.plot_finished = False
        self.nb_export_total = 0
        self.export_finished = False
        self.export_production_stoped = False
        self.process_type = type  # cal or plot or export
        self.process_list = []
        self.save_process = []
        self.plot_hdf5_mode = False
        self.export_hdf5_mode = False

    def set_export_hdf5_mode(self, path_prj, names_hdf5, export_dict, project_preferences):
        self.path_prj = path_prj
        self.names_hdf5 = names_hdf5
        self.project_preferences = project_preferences
        self.export_hdf5_mode = True
        self.export_dict = export_dict
        self.nb_export_total = export_dict["nb_export"]

    def set_plot_hdf5_mode(self, path_prj, names_hdf5, plot_attr, project_preferences):
        self.path_prj = path_prj
        self.names_hdf5 = names_hdf5
        self.project_preferences = project_preferences
        self.plot_hdf5_mode = True
        self.plot_attr = plot_attr

    def load_data_and_append_plot_process(self):
        reach = self.plot_attr.reach
        plot_type = self.plot_attr.plot_type
        units_index = self.plot_attr.units_index
        units = self.plot_attr.units

        # load hydraulic data
        if self.hdf5.hdf5_type == "hydraulic":
            self.hdf5.load_hdf5_hyd(units_index=units_index,
                                    user_target_list=self.hvum.user_target_list,
                                    whole_profil=True)

        # load substrate data
        elif self.hdf5.hdf5_type == "substrate":
            self.hdf5.load_hdf5_sub(user_target_list=self.hvum.user_target_list)

        # load habitat data
        elif self.hdf5.hdf5_type == "habitat":
            self.hdf5.load_hdf5_hab(units_index=units_index,
                                    user_target_list=self.hvum.user_target_list,
                                    whole_profil=False)

        habitat_variable_list = self.hdf5.data_2d.hvum.all_final_variable_list.habs()
        light_data_2d = self.hdf5.data_2d.get_light_data_2d()

        # all cases
        unit_type = light_data_2d.unit_type[light_data_2d.unit_type.find('[') + len('['):light_data_2d.unit_type.find(
                        ']')]

        # for each reach
        for reach_name in reach:
            reach_number = light_data_2d.reach_list.index(reach_name)
            # for one or more desired units ==> habitat data (HV and WUA)
            if habitat_variable_list and plot_type != ["map"] and not self.plot_production_stoped:
                state = Value("d", 0)
                plot_hab_fig_spu_process = Process(target=plot_mod.plot_fish_hv_wua,
                                                   args=(state,
                                                         self.hdf5.data_2d,
                                                         reach_number,
                                                         habitat_variable_list,
                                                         self.project_preferences),
                                                   name="plot_fish_hv_wua")
                self.process_list.append([plot_hab_fig_spu_process, state])

            # for each desired units ==> maps
            if plot_type != ["result"]:
                for unit_number, t in enumerate(units_index):
                    # string_tr
                    string_tr = [self.tr("reach"), self.tr("unit")]
                    """ MAP """
                    if self.plot_attr.plot_map_QCheckBoxisChecked:
                        # plot
                        for variable in self.hvum.user_target_list.no_habs():
                            if not self.plot_production_stoped:
                                    plot_string_dict = create_map_plot_string_dict(light_data_2d.filename,
                                                                                   reach_name,
                                                                                   units[unit_number],
                                                                                   unit_type,
                                                                                   self.tr(variable.name_gui),
                                                                                   variable.unit,
                                                                                   string_tr)
                                    state = Value("i", 0)
                                    process = Process(target=getattr(plot_mod, "plot_map_" + variable.position),
                                                               args=(
                                                                   state,
                                                                   self.hdf5.data_2d[reach_number][unit_number]["node"]["xy"],
                                                                   self.hdf5.data_2d[reach_number][unit_number]["mesh"]["tin"],
                                                                   self.hdf5.data_2d[reach_number][unit_number][variable.position]["data"][variable.name].to_numpy(),
                                                                   plot_string_dict,
                                                                   light_data_2d,
                                                                   self.project_preferences
                                                               ),
                                                               name=variable.name)
                                    self.process_list.append([process, state])

                        # plot animal map
                        for animal in habitat_variable_list:
                            if not self.plot_production_stoped:
                                plot_string_dict = create_map_plot_string_dict(light_data_2d.filename,
                                                                               reach_name,
                                                                               units[unit_number],
                                                                               unit_type,
                                                                               animal.name,
                                                                                "",
                                                                               string_tr,
                                                                               self.tr('HSI = ') + '{0:3.2f}'.format(animal.hv[reach_number][unit_number]) + " / " + self.tr('unknown area') + " = " + '{0:3.2f}'.format(animal.percent_area_unknown[reach_number][unit_number]) + " %")
                                state = Value("i", 0)
                                habitat_map_process = Process(target=plot_mod.plot_map_fish_habitat,
                                                              args=(
                                                                  state,
                                                                  self.hdf5.data_2d[reach_number][unit_number]["node"]["xy"],
                                                                  self.hdf5.data_2d[reach_number][unit_number]["mesh"]["tin"],
                                                                  self.hdf5.data_2d[reach_number][unit_number]["mesh"]["data"][animal.name],
                                                                  plot_string_dict,
                                                                  light_data_2d,
                                                                  self.project_preferences
                                                              ),
                                                              name="plot_map_fish_habitat")
                                self.process_list.append([habitat_map_process, state])

        self.nb_plot_total = len(self.process_list)

    def load_data_and_append_export_process(self):
        # hydraulic
        if self.hdf5.hdf5_type == "hydraulic":  # load hydraulic data
            self.hdf5.load_hdf5_hyd(whole_profil=True,
                                    user_target_list=self.project_preferences)
            total_gpkg_export = sum(
                [self.export_dict["mesh_whole_profile_hyd"], self.export_dict["point_whole_profile_hyd"],
                 self.export_dict["mesh_units_hyd"], self.export_dict["point_units_hyd"]])
            if self.export_dict["mesh_whole_profile_hyd"] or self.export_dict["point_whole_profile_hyd"] or \
                    self.export_dict["mesh_units_hyd"] or self.export_dict["point_units_hyd"]:
                # append fake first
                for fake_num in range(1, total_gpkg_export):
                    self.process_list.append([Process(name="fake" + str(fake_num)), Value("i", 1)])
                state = Value("i", 0)
                export_gpkg_process = Process(target=self.hdf5.export_gpkg,
                                              args=(state,),
                                              name="export_gpkg")
                self.process_list.append([export_gpkg_process, state])
            if self.export_dict["elevation_whole_profile_hyd"]:
                state = Value("i", 0)
                export_stl_process = Process(target=self.hdf5.export_stl,
                                             args=(state,),
                                             name="export_stl")
                self.process_list.append([export_stl_process, state])
            if self.export_dict["variables_units_hyd"]:
                state = Value("i", 0)
                export_paraview_process = Process(target=self.hdf5.export_paraview,
                                                  args=(state,),
                                                  name="export_paraview")
                self.process_list.append([export_paraview_process, state])
            if self.export_dict["detailled_text_hyd"]:
                state = Value("i", 0)
                export_detailled_mesh_txt_process = Process(target=self.hdf5.export_detailled_txt,
                                                            args=(state,),
                                                            name="export_detailled_txt")
                self.process_list.append([export_detailled_mesh_txt_process, state])

        # substrate
        elif self.hdf5.hdf5_type == "substrate":  # load substrate data
            self.hdf5.load_hdf5_sub()

        # habitat
        elif self.hdf5.hdf5_type == "habitat":  # load habitat data
            self.hdf5.load_hdf5_hab(whole_profil=True,
                                    user_target_list=self.project_preferences)
            total_gpkg_export = sum([self.export_dict["mesh_units_hab"], self.export_dict["point_units_hab"]])
            if self.export_dict["mesh_units_hab"] or self.export_dict["point_units_hab"]:
                # append fake first
                for fake_num in range(1, total_gpkg_export):
                    self.process_list.append([Process(name="fake_gpkg" + str(fake_num)), Value("i", 1)])
                state = Value("i", 0)
                export_gpkg_process = Process(target=self.hdf5.export_gpkg,
                                              args=(state,),
                                              name="export_gpkg")
                self.process_list.append([export_gpkg_process, state])
            if self.export_dict["elevation_whole_profile_hab"]:
                state = Value("i", 0)
                export_stl_process = Process(target=self.hdf5.export_stl,
                                             args=(state,),
                                             name="export_stl")
                self.process_list.append([export_stl_process, state])
            if self.export_dict["variables_units_hab"]:
                state = Value("i", 0)
                export_paraview_process = Process(target=self.hdf5.export_paraview,
                                                  args=(state,),
                                                  name="export_paraview")
                self.process_list.append([export_paraview_process, state])
            if self.export_dict["habitat_text_hab"]:
                state = Value("i", 0)
                export_spu_txt_process = Process(target=self.hdf5.export_spu_txt,
                                                 args=(state,),
                                                 name="export_spu_txt")
                self.process_list.append([export_spu_txt_process, state])
            if self.export_dict["detailled_text_hab"]:
                state = Value("i", 0)
                export_detailled_mesh_txt_process = Process(target=self.hdf5.export_detailled_txt,
                                                            args=(state,),
                                                            name="export_detailled_txt")
                self.process_list.append([export_detailled_mesh_txt_process, state])
            if self.export_dict["fish_information_hab"]:
                if self.hdf5.data_2d.hvum.hdf5_and_computable_list.habs():
                    state = Value("i", 0)
                    export_pdf_process = Process(target=self.hdf5.export_report,
                                                 args=(state,),
                                                 name="export_report")
                    self.process_list.append([export_pdf_process, state])
                else:
                    # append fake first
                    self.process_list.append([Process(name="fake_fish_information_hab"), Value("i", 1)])
                    print('Warning: ' + 'No habitat data in this .hab file to export Fish informations report.')

    def new_plots(self):
        self.nb_finished = 0
        self.add_plots_state = False
        self.save_process = []
        self.process_list = []

    def add_plots(self, plus):
        #print("add_plots")
        self.add_plots_state = True
        self.plot_production_stoped = False
        # remove plots not started
        self.remove_process_not_started()
        self.nb_plot_total = self.nb_plot_total + plus

    def append(self, process):
        self.process_list.append(process)

    def run(self):
        self.thread_started = True
        self.plot_production_stoped = False
        if self.process_type == "plot":
            self.plot_finished = False
            self.all_process_runned = False
            if self.plot_hdf5_mode:  # from hdf5 data
                for name_hdf5 in self.names_hdf5:
                    self.hdf5 = Hdf5Management(self.path_prj,
                                               name_hdf5,
                                               new=False)
                    self.hvum = self.plot_attr.hvum
                    self.load_data_and_append_plot_process()
            # Process mod
            for i in range(len(self.process_list)):
                if not self.plot_production_stoped:
                    if self.process_list[i][1].value == 0 and not self.process_list[i][0].is_alive():
                        self.process_list[i][0].start()
            self.all_process_runned = True
            self.check_all_plot_produced()

        if self.process_type == "export":
            self.export_finished = False
            self.all_process_runned = False
            if self.export_hdf5_mode:
                for name_hdf5 in self.names_hdf5:
                    self.hdf5 = Hdf5Management(self.path_prj,
                                               name_hdf5,
                                               new=False)
                    self.load_data_and_append_export_process()
            # Process mod
            for i in range(len(self.process_list)):
                if not self.export_production_stoped:
                    self.process_list[i][0].start()
            self.all_process_runned = True
            self.check_all_export_produced()

    def stop_plot_production(self):
        #print("stop_plot_production")
        self.plot_production_stoped = True
        self.plot_finished = True

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
                #print("waiting", self.all_process_runned)
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
            self.export_finished = True
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
                # self.progress_signal.emit(self.nb_finished)
                #print("emit 1")
            if state == 0:
                if i == self.nb_plot_total - 1:  # last of all plot
                    while 0 in state_list:
                        for j in [k for k, l in enumerate(state_list) if l == 0]:
                            state = self.process_list[j][1].value
                            state_list[j] = state
                            if state == 1:
                                self.nb_finished = self.nb_finished + 1
                                # self.progress_signal.emit(self.nb_finished)
                                #print("emit 2")
                        if self.plot_production_stoped:
                            sleep(1)
                            for j in [k for k, l in enumerate(state_list) if l == 0]:
                                state = self.process_list[j][1].value
                                state_list[j] = state
                                if state == 1:
                                    self.nb_finished = self.nb_finished + 1
                                    # self.progress_signal.emit(self.nb_finished)
                                    #print("emit 3")
                            sleep(1)
                            for j in [k for k, l in enumerate(state_list) if l == 0]:
                                try:
                                    self.process_list[j][0].terminate()
                                except AttributeError:
                                    continue
                            break
        self.plot_finished = True

    def check_all_export_produced(self):
        # print("check_all_export_produced")
        self.nb_finished = 0
        self.nb_export_total = len(self.process_list)
        state_list = [self.process_list[i][1].value for i in range(len(self.process_list))]
        self.nb_finished = state_list.count(1)
        while 0 in state_list:
            if self.export_production_stoped:
                break
            state_list = [self.process_list[i][1].value for i in range(len(self.process_list))]
            if state_list.count(1) != self.nb_finished:
                self.nb_finished = state_list.count(1)
        self.export_finished = True

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

