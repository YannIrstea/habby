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
import importlib
import os
import pandas as pd
import numpy as np
from PyQt5.QtCore import QCoreApplication as qt_tr
from shutil import copy as sh_copy

from src.data_2d_mod import Data2d
from src.dev_tools_mod import sort_homogoeneous_dict_list_by_on_key
from src.hydraulic_result_mod import HydraulicModelInformation
from src.variable_unit_mod import HydraulicVariableUnitManagement
from src.project_properties_mod import load_project_properties


class HydraulicSimulationResultsSelector:
    def __new__(self, filename, folder_path, model_type, path_prj):
        hydraulic_model_information = HydraulicModelInformation()
        filename_mod = hydraulic_model_information.get_file_mod_name_from_attribute_name(model_type)

        # Contrived example of generating a module named as a string
        full_module_name = "src." + filename_mod

        # The file gets executed upon import, as expected.
        mymodule = importlib.import_module(full_module_name)

        return mymodule.HydraulicSimulationResults(filename, folder_path, model_type, path_prj)


class HydraulicSimulationResultsBase:
    def __init__(self, filename, folder_path, model_type, path_prj):
        """Represent hydraulic simulation results.

        Keyword arguments:
        filename -- filename, type: str
        folder_path -- relative path to filename, type: str
        model_type -- type of hydraulic model, type: str
        path_prj -- absolute path to project, type: str
        """
        # init
        self.filename = filename
        self.folder_path = folder_path
        self.model_type = model_type
        self.path_prj = path_prj
        self.hvum = HydraulicVariableUnitManagement()
        self.hmi = HydraulicModelInformation()
        self.valid_file = True
        self.warning_list = []  # text warning output
        self.name_prj = os.path.splitext(os.path.basename(path_prj))[0]
        self.hydrau_case = "unknown"
        self.filename_path = os.path.join(self.folder_path, self.filename)
        self.blob, self.ext = os.path.splitext(self.filename)
        self.extensions_list = self.hmi.extensions[self.hmi.attribute_models_list.index(self.model_type)].split(", ")
        self.project_properties = load_project_properties(self.path_prj)
        # index_hydrau
        self.index_hydrau_file_exist = False
        if os.path.isfile(self.filename_path):
            self.index_hydrau_file_exist = True
        self.index_hydrau_file = "indexHYDRAU.txt"
        self.index_hydrau_file_path = os.path.join(self.folder_path, self.index_hydrau_file)
        # hydraulic attributes
        self.hyd_equation_type = self.hmi.equation[self.hmi.attribute_models_list.index(self.model_type)]
        # exist ?
        if not os.path.isfile(self.filename_path) and os.path.splitext(self.filename_path)[1]:
            self.warning_list.append("Error: The file does not exist.")
            self.valid_file = False

        # results_data_file
        self.results_data_file = None

        self.sub = False
        self.sub_mapping_method = ""
        self.sub_classification_method = ""  # "coarser-dominant" / "percentage"
        self.sub_classification_code = ""  # "Cemagref" / "Sandre"
        self.epsg_code = "unknown"

        # reach_number
        self.reach_number = int(self.hmi.reach_number[self.hmi.attribute_models_list.index(self.model_type)])
        if self.reach_number == "n":
            self.reach_number = 1  # init
            self.multi_reach = True
        else:
            self.reach_number = 1  # init
            self.multi_reach = False
        self.reach_name_list = ["unknown"]

        # timestep
        self.timestep_name_list = []
        self.timestep_nb = 1
        self.timestep_unit = ""
        self.timestep_name_wish_list_index = []
        self.timestep_name_wish_list = []
        self.timestep_wish_nb = None

        # coordinates
        self.unit_z_equal = False

    def load_specific_timestep(self, timestep_name_wish_list):
        self.timestep_name_wish_list = timestep_name_wish_list
        for time_step_name_wish in self.timestep_name_wish_list:
            if time_step_name_wish not in self.timestep_name_list:
                print("Error: timestep " + time_step_name_wish + " not found in " + self.filename +
                      ". Change it in indexHYDRAU.txt and retry.")
                break
            else:
                self.timestep_name_wish_list_index.append(self.timestep_name_list.index(time_step_name_wish))
        self.timestep_name_wish_list_index.sort()
        self.timestep_wish_nb = len(self.timestep_name_wish_list_index)

    def get_data_2d(self):
        # create empty list
        data_2d = Data2d(reach_number=len(self.reach_name_list),
                         unit_list=[self.timestep_name_wish_list])
        data_2d.hyd_equation_type = self.hyd_equation_type
        data_2d.hvum = self.hvum
        self.hvum.hdf5_and_computable_list.sort_by_names_gui()
        node_list = self.hvum.hdf5_and_computable_list.nodes()
        mesh_list = self.hvum.hdf5_and_computable_list.meshs()

        for reach_number in range(len(self.reach_name_list)):

            for unit_number in range(self.timestep_wish_nb):
                # node
                data_2d[reach_number][unit_number]["node"][self.hvum.xy.name] = self.hvum.xy.data[reach_number][unit_number]
                data_2d[reach_number][unit_number]["node"]["data"] = pd.DataFrame()
                for node_variable in node_list:
                    try:
                        data_2d[reach_number][unit_number]["node"]["data"][node_variable.name] = node_variable.data[reach_number][unit_number]
                    except IndexError:
                        print("Error: node data not found : " + node_variable.name + " in get_data_2d.")

                # mesh
                data_2d[reach_number][unit_number]["mesh"][self.hvum.tin.name] = self.hvum.tin.data[reach_number][unit_number]
                data_2d[reach_number][unit_number]["mesh"][self.hvum.i_whole_profile.name] = np.column_stack([
                                    np.arange(0, self.hvum.tin.data[reach_number][unit_number].shape[0], dtype=self.hvum.i_whole_profile.dtype),
                                    np.repeat(0, self.hvum.tin.data[reach_number][unit_number].shape[0]).astype(self.hvum.i_split.dtype)])
                data_2d[reach_number][unit_number]["mesh"]["data"] = pd.DataFrame()
                # i_split
                data_2d[reach_number][unit_number]["mesh"]["data"][self.hvum.i_split.name] = data_2d[reach_number][unit_number]["mesh"]["i_whole_profile"][:, 1]
                for mesh_variable in mesh_list:
                    try:
                        data_2d[reach_number][unit_number]["mesh"]["data"][mesh_variable.name] = mesh_variable.data[reach_number][unit_number]
                    except IndexError:
                        print("Error: mesh data not found : " + mesh_variable.name + " in get_data_2d.")

        # i_split
        self.hvum.i_split.position = "mesh"
        self.hvum.i_split.hdf5 = True
        self.hvum.hdf5_and_computable_list.append(self.hvum.i_split)

        # description telemac data_2d dict
        description_from_file = dict()
        description_from_file["filename_source"] = self.filename
        description_from_file["model_type"] = self.model_type
        description_from_file["model_dimension"] = str(2)
        description_from_file["unit_list"] = str(self.timestep_name_wish_list)
        description_from_file["unit_number"] = str(self.timestep_wish_nb)
        description_from_file["unit_type"] = "time [s]"
        description_from_file["unit_z_equal"] = self.unit_z_equal
        description_from_file["variables"] = dict()

        return data_2d, description_from_file


class HydraulicSimulationResultsAnalyzer:
    def __init__(self, filename_path_list, path_prj, model_type):
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
        self.nb_dim = HydraulicModelInformation().dimensions[HydraulicModelInformation().attribute_models_list.index(model_type)]
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
        # check if input file exist
        for file_path in self.filename_path_list:
            if not os.path.exists(file_path):
                self.hydrau_description_list = "Error: " + file_path + " doesn't exist."
                return

        # init
        multi_reach = False
        reach_presence = False

        # indexHYDRAU.txt absence
        if not self.index_hydrau_file_exist:
            self.warning_list.append("Warning: " + qt_tr.translate("hydro_input_file_mod",
                                                                       "indexHYDRAU.txt doesn't exist. It will be created in the 'input' directory after the creation "
                                                                       "of the .hyd file. The latter will be filled in according to your choices."))

            # more_than_one_file_selected_by_user
            if self.more_than_one_file_selected_by_user:
                if self.model_type == 'rubar2d':  # change mode and remove one of them
                    self.more_than_one_file_selected_by_user = False
                    self.filename_list = [self.filename_list[0]]
                    self.filename_path_list = [self.filename_path_list[0]]
                else:
                    for i, file in enumerate(self.filename_path_list):
                        # get units name from file
                        hsr = HydraulicSimulationResultsSelector(file, self.folder_path, self.model_type,
                                                                 self.path_prj)
                        self.warning_list.extend(hsr.warning_list)
                        if not hsr.valid_file:
                            continue

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
                if not hsr.valid_file:
                    return
                if self.model_type == 'rubar2d':  # remove extension
                    filename, _ = os.path.splitext(filename)
                if self.model_type == "basement2d":
                    hdf5_name = hsr.simulation_name + ".hyd"
                elif self.model_type == "lammi":
                    hdf5_name = hsr.simulation_name + ".hab"
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
            selectedfiles_textfiles_matching = False

            # read text file
            with open(self.index_hydrau_file_path, 'rt', encoding="utf-8") as f:
                dataraw = f.read()
            # get epsg code
            epsg_code = dataraw.split("\n")[0].split("EPSG=")[1].strip()
            # read headers and nb row
            headers = dataraw.split("\n")[1].split()
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
                        data_index_file[column_name].append(line.split()[index])

            if self.model_type == 'rubar2d':
                self.more_than_one_file_selected_by_user = False
                selectedfiles_textfiles_match = [True] * 2
                if type(self.filename_list) == list:
                    self.filename_list = [self.filename_list[0]]
                    self.filename_path_list = [self.filename_path_list[0]]

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
            if all(selectedfiles_textfiles_match):
                selectedfiles_textfiles_matching = True
                self.filename_list = data_index_file["filename"]
                self.filename_path_list = [os.path.join(self.folder_path, filename) for filename in self.filename_list]
            if any("Q[" in s for s in headers) and self.model_type != "lammi":
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
                if not hsr.valid_file:
                    return
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
            elif self.hydrau_case == "1.b":
                # get units name from file
                hsr = HydraulicSimulationResultsSelector(namefile,
                                                         self.folder_path, self.model_type, self.path_prj)
                self.warning_list.extend(hsr.warning_list)
                if not hsr.valid_file:
                    return
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
                elif self.model_type == "lammi":
                    self.hydrau_description_list[0]["hdf5_name"] = hsr.simulation_name + ".hab"

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
                    if not hsr.valid_file:
                        continue
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
                    if not hsr.valid_file:
                        continue
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
                if not hsr.valid_file:
                    return
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
                elif self.model_type == "lammi":
                    self.hydrau_description_list[0]["hdf5_name"] = hsr.simulation_name + ".hab"

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
                if not hsr.valid_file:
                    return
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
                elif self.model_type == "lammi":
                    self.hydrau_description_list[0]["hdf5_name"] = hsr.simulation_name + ".hab"

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
                    if not hsr.valid_file:
                        continue

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
                if multi_reach and reach_presence:
                    # check if unit nb by reach is equal
                    unit_list_all_reach = []
                    unit_list_full_all_reach = []
                    unit_list_tf_all_reach = []
                    for i, file in enumerate(data_index_file[headers[0]]):
                        # get units name from file
                        hsr = HydraulicSimulationResultsSelector(file,
                                                                 self.folder_path, self.model_type, self.path_prj)
                        self.warning_list.extend(hsr.warning_list)
                        if not hsr.valid_file:
                            continue
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
                            if item in unit_name_from_index_file2 or "all" in unit_name_from_index_file2:
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
                        if not hsr.valid_file:
                            continue
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

            if self.model_type == "lammi":

                if len(data_index_file["filename"]) == 1:
                    self.hydrau_case = "LAMMI"
                elif len(data_index_file["filename"]) > 1:
                    self.hydrau_case = "5.LAMMI"
                hdf5_name_list = []
                unit_name_list = []
                unit_name_full_list = []
                unit_name_full_tf_list = []
                # for each filename (as reach)
                for lammi_ind, lammi_file in enumerate(data_index_file["filename"]):
                    # get units name from file
                    hsr = HydraulicSimulationResultsSelector(lammi_file,
                                                             self.folder_path, self.model_type, self.path_prj)
                    self.warning_list.extend(hsr.warning_list)
                    if not hsr.valid_file:
                        continue
                    # get units name from indexHYDRAU.txt file
                    unit_name_from_index_file = data_index_file[headers[1]][lammi_ind]

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
                    unit_name_list.append(unit_name_from_index_file2)
                    unit_name_full_list.append(hsr.timestep_name_list)
                    unit_name_full_tf_list.append(timestep_to_select)
                    hdf5_name_list.append(hsr.simulation_name)

                    # selected files same than indexHYDRAU file
                    if not selectedfiles_textfiles_matching:
                        self.hydrau_description_list = "Error: selected files are different from indexHYDRAU files"
                        return

                reach_name = ["unknown"]
                if reach_presence:
                    reach_name = data_index_file[headers[reach_index]]
                    hdf5_name = "_".join([os.path.splitext(el)[0] for el in data_index_file[headers[0]]]) + ".hab"
                else:
                    hdf5_name = hsr.simulation_name + ".hab"

                # self.hydrau_description_list
                self.hydrau_description_list[0]["hdf5_name"] = hdf5_name
                self.hydrau_description_list[0]["filename_source"] = ", ".join(data_index_file[headers[0]])
                self.hydrau_description_list[0]["unit_list"] = unit_name_list
                self.hydrau_description_list[0]["unit_list_full"] = unit_name_full_list
                self.hydrau_description_list[0]["unit_list_tf"] = unit_name_full_tf_list
                self.hydrau_description_list[0]["unit_number"] = str(len(unit_name_list[0]))
                self.hydrau_description_list[0]["unit_type"] = "discharge [m3/s]"
                self.hydrau_description_list[0]["reach_list"] = reach_name
                self.hydrau_description_list[0]["reach_number"] = str(len(data_index_file["filename"]))
                self.hydrau_description_list[0]["reach_type"] = "river"
                self.hydrau_description_list[0]["variable_name_unit_dict"] = hsr.hvum.software_detected_list
                self.hydrau_description_list[0]["flow_type"] = "transient flow"  # continuous flow

        # if m3/s
        for hydrau_description_index in range(len(self.hydrau_description_list)):
            if "m3/s" in self.hydrau_description_list[hydrau_description_index]["unit_type"]:
                self.hydrau_description_list[hydrau_description_index]["unit_type"] = \
                self.hydrau_description_list[hydrau_description_index]["unit_type"].replace("m3/s", "m<sup>3</sup>/s")

        # print("------------------------------------------------")
        # print("hydrau_case in : " + self.hydrau_case)
        # print("reach_presence", reach_presence)
        # print("multi_reach", multi_reach)
        # print(self.hydrau_description_list[0]["unit_list"])
        # print(self.hydrau_description_list[0]["unit_list_tf"])
        # print(self.hydrau_description_list[0]["unit_number"])


def create_or_copy_index_hydrau_text_file(description_from_indexHYDRAU_file):
    # one case (one hdf5 produced)
    filename_path = os.path.join(description_from_indexHYDRAU_file["path_prj"], "input", os.path.splitext(description_from_indexHYDRAU_file["hdf5_name"])[0], "indexHYDRAU.txt")
    filename_column = description_from_indexHYDRAU_file["filename_source"].split(", ")
    hydrau_case = description_from_indexHYDRAU_file["hydrau_case"]
    """ CASE .a or .b ? user can select specific timesteps or discharges """
    if hydrau_case in {"unknown", "2.a", "2.b", "3.a", "3.b"}:
        for reach_num in range(len(description_from_indexHYDRAU_file["unit_list"])):
            if description_from_indexHYDRAU_file["unit_list"][reach_num] == \
                    description_from_indexHYDRAU_file["unit_list_full"][reach_num]:
                hydrau_case = hydrau_case[:-1] + "a"
            else:
                hydrau_case = hydrau_case[:-1] + "b"
                break

        if hydrau_case == "2.b":
            if "unknown" in description_from_indexHYDRAU_file["reach_list"]:
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"][0]

            unit_type = description_from_indexHYDRAU_file["unit_type"].replace("m<sup>3</sup>/s", "m3/s").replace("discharge", "Q").replace(" ", "")
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + unit_type
            if reach_column_presence:
                headers = headers + "\t" + "reachname"

            # first line
            linetowrite = ""
            filename_list = description_from_indexHYDRAU_file["filename_source"].split(", ")
            for ind, unit_name in enumerate(description_from_indexHYDRAU_file["unit_list"][0]):
                if reach_column_presence:
                    linetowrite = linetowrite + filename_list[ind] + "\t" + unit_name + "\t" + reach_column + "\n"
                else:
                    linetowrite = linetowrite + filename_list[ind] + "\t" + unit_name + "\n"

            # text
            text = epsg_code + "\n" + headers + "\n" + linetowrite

            # write text file
            with open(filename_path, 'wt', encoding="utf-8") as f:
                f.write(text)

        elif hydrau_case == "3.b":
            if "unknown" in description_from_indexHYDRAU_file["reach_list"]:
                reach_column_presence = False
            else:
                reach_column_presence = True
                reach_column = description_from_indexHYDRAU_file["reach_list"][0]

            unit_type = description_from_indexHYDRAU_file["unit_type"].replace("m<sup>3</sup>/s", "m3/s").replace("discharge", "Q")
            # epsg_code
            epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
            # headers
            headers = "filename" + "\t" + unit_type
            if reach_column_presence:
                headers = headers + "\t" + "reachname"

            # first line
            index = [i for i, item in enumerate(description_from_indexHYDRAU_file["unit_list_full"][0]) if
                     item in description_from_indexHYDRAU_file["unit_list"][0]]
            my_sequences = []
            for idx, item in enumerate(index):
                if not idx or item - 1 != my_sequences[-1][-1]:
                    my_sequences.append([item])
                else:
                    my_sequences[-1].append(item)
            from_to_string_list = []
            for sequence in my_sequences:
                start = min(sequence)
                start_string = description_from_indexHYDRAU_file["unit_list_full"][0][start]
                end = max(sequence)
                end_string = description_from_indexHYDRAU_file["unit_list_full"][0][end]
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

        elif description_from_indexHYDRAU_file["model_type"] == "lammi":
            if description_from_indexHYDRAU_file["unit_list"] != description_from_indexHYDRAU_file["unit_list_full"]:
                unit_type = description_from_indexHYDRAU_file["unit_type"].replace("m<sup>3</sup>/s", "m3/s").replace(
                    "discharge", "Q").replace(" ", "")
                # epsg_code
                epsg_code = "EPSG=" + description_from_indexHYDRAU_file["epsg_code"]
                # headers
                headers = "filename" + "\t" + unit_type

                # first line
                linetowrite = ""
                filename_list = description_from_indexHYDRAU_file["filename_source"].split(", ")
                for filename_ind, filename in enumerate(filename_list):
                    unit_name = ";".join(description_from_indexHYDRAU_file["unit_list"][filename_ind])
                    linetowrite = linetowrite + filename_list[filename_ind] + "\t" + unit_name + "\n"

                # text
                text = epsg_code + "\n" + headers + "\n" + linetowrite

                # write text file
                with open(filename_path, 'wt', encoding="utf-8") as f:
                    f.write(text)

        else:
            if os.path.exists(os.path.join(description_from_indexHYDRAU_file["path_filename_source"], "indexHYDRAU.txt")):
                # copy original
                sh_copy(os.path.join(description_from_indexHYDRAU_file["path_filename_source"], "indexHYDRAU.txt"),
                        os.path.join(description_from_indexHYDRAU_file["path_prj"], "input",
                                     os.path.splitext(description_from_indexHYDRAU_file["hdf5_name"])[0]))
    else:
        # copy original
        sh_copy(os.path.join(description_from_indexHYDRAU_file["path_filename_source"], "indexHYDRAU.txt"),
                os.path.join(description_from_indexHYDRAU_file["path_prj"], "input",
                             os.path.splitext(description_from_indexHYDRAU_file["hdf5_name"])[0]))

    # import sys
    # sys.stdout = sys.__stdout__
    # print("hydrau_case out : " + hydrau_case)
