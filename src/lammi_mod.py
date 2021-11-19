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
import numpy as np
import matplotlib.pyplot as plt
import time
from io import StringIO
from collections import OrderedDict
from src.project_properties_mod import create_default_project_properties_dict
from src import substrate_mod
from src import manage_grid_mod
from src import hdf5_mod
import matplotlib as mpl

from src.hydraulic_results_manager_mod import HydraulicSimulationResultsBase


class HydraulicSimulationResults(HydraulicSimulationResultsBase):
    """Represent LAMMI simulation results.

    Keyword arguments:
    filename -- filename, type: str
    folder_path -- relative path to filename, type: str
    model_type -- type of hydraulic model, type: str
    path_prj -- absolute path to project, type: str
    """

    def __init__(self, filename, folder_path, model_type, path_prj):
        super().__init__(filename, folder_path, model_type, path_prj)
        # file attributes
        self.file_type = "binary"
        # reach
        self.morphology_available = True
        # hydraulic variables
        self.hvum.link_unit_with_software_attribute(name=self.hvum.z.name,
                                                    attribute_list=["z"],
                                                    position="node")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.h.name,
                                                    attribute_list=["h"],
                                                    position="node")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.v.name,
                                                    attribute_list=["v"],
                                                    position="node")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s1.name,
                                                    attribute_list=["s1"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s2.name,
                                                    attribute_list=["s2"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s3.name,
                                                    attribute_list=["s3"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s4.name,
                                                    attribute_list=["s4"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s5.name,
                                                    attribute_list=["s5"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s6.name,
                                                    attribute_list=["s6"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s7.name,
                                                    attribute_list=["s7"],
                                                    position="mesh")
        self.hvum.link_unit_with_software_attribute(name=self.hvum.sub_s8.name,
                                                    attribute_list=["s8"],
                                                    position="mesh")

        self.sub = True
        self.sub_mapping_method = "point"
        self.sub_classification_method = "percentage"  # "coarser-dominant" / "percentage"
        self.sub_classification_code = "Cemagref"  # "Cemagref" / "Sandre"

        self.hyd_varying_mesh = True

        # readable file ?
        try:
            self.simulation_name, self.lq, self.lqdico = construct_from_lammi(self.filename_path)
            if not self.simulation_name:
                self.warning_list.append("Error: " + self.lqdico)
                self.valid_file = False
        except OSError:
            self.warning_list.append("Error: The file can not be opened.")
            self.valid_file = False

        # if valid get informations
        if self.valid_file:
            # get_time_step ?
            self.get_time_step()
            # get hydraulic variables list (mesh and node)
            self.get_hydraulic_variable_list()
        else:
            self.warning_list.append("Error: File not valid.")

    def get_hydraulic_variable_list(self):
        """Get hydraulic variable list from file."""
        # get list from source
        varnames = ["z", "h", "v", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]

        # check witch variable is available
        self.hvum.detect_variable_from_software_attribute(varnames)

    def get_time_step(self):
        """Get time step information from file."""
        self.timestep_name_list = list(map(str, self.lq))  # always one reach
        self.timestep_nb = len(self.timestep_name_list)
        self.timestep_unit = "discharge [m3/s]"

    def load_hydraulic(self, timestep_name_wish_list):
        """Retrun Data2d from file.

        Keyword arguments:
        timestep_name_wish_list -- list of targeted timestep to be load, type: list of str
        """
        self.load_specific_timestep(timestep_name_wish_list)

        # prepare original data for data_2d
        for reach_number in range(self.reach_number):  # for each reach
            for timestep_index in self.timestep_name_wish_list_index:  # for each timestep
                sub_case = 0
                for variables_wish in self.hvum.software_detected_list:
                    if not variables_wish.precomputable_tohdf5:
                        if variables_wish.position == "node":
                            if variables_wish.name == self.hvum.h.name:
                                index_variable = 0
                            elif variables_wish.name == self.hvum.v.name:
                                index_variable = 1
                            elif variables_wish.name == self.hvum.z.name:
                                index_variable = 2
                            variables_wish.data[reach_number].append(
                                self.lqdico[timestep_index]["node_hvz"][:, index_variable].astype(variables_wish.dtype))
                        if variables_wish.position == "mesh":
                            variables_wish.data[reach_number].append(
                                self.lqdico[timestep_index]["mesh_substrate"][:, sub_case].astype(variables_wish.dtype))
                            sub_case += 1

                # struct
                self.hvum.xy.data[reach_number].append(self.lqdico[timestep_index]["node_xy"])
                self.hvum.tin.data[reach_number].append(self.lqdico[timestep_index]["tin"].astype(np.int64))

        return self.get_data_2d()


def open_lammi_and_create_grid(facies_path, transect_path, path_im, name_hdf5, name_prj, path_prj, path_hdf5,
                               new_dir='', project_preferences=[], savefig1d=False, transect_name='Transect.txt',
                               facies_name='Facies.txt', print_cmd=False, q=[], dominant_case=1, model_type='LAMMI'):
    """
    This function loads the data from the LAMMI model using the load_lammi() function., create the grid and save the
    data in an hdf5 file. A description of the LAMMI model is available in the documentation folder
    (LAMMIGuideMetho.pdf).

    :param transect_path: the path to the transect.txt path
    :param facies_path: the path the facies.txt file
    :param path_im: the path where to save the image
    :param project_preferences: the figure option
    :param savefig1d: create and save the figure related to the loading of the data (profile and so on)
    :param name_hdf5: the name of the hdf5 to be created
    :param name_prj: the name of the project (string)
    :param path_prj: the path of the project
    :param path_hdf5: the path to the hdf5 data
    :param new_dir: if necessary, the path to the resultat file (.prn file). Be default, use the one in transect.txt
    :param transect_name: the name of the transect file, usually 'Transect.txt'
    :param facies_name: the name of the facies file, ususally 'Facies.txt
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param q: used if this function is send using the second thread
    :param dominant_case: an int to manage the case where the transformation form percentage to dominant is unclear (two
           maximum percentage are equal from one element). if -1 take the smallest, if 1 take the biggest,
           if 0, we do not know.
    :param model_type: which type of model (LAMMI in this case). It is as an argument just in case (lammi, Lammi, etc.)
    :return:

    **Technical comments**

    LAMMI has a special way of creating a grid from its data. Because spatial information is not very good in LAMMI,
    we can only used the create_grid_only_1_profile() function. The function which uses triangle to create the grid can
    not be used here as the developer from LAMMI did not wish to introduce an interpolation method in their outputs.
    In addition, LAMMI integrates substrate data which should be directly added to the grid while other hydraulic model
    get their substrate data from another sources.
    """

    # preparation
    mystdout = None
    if not print_cmd:
        sys.stdout = mystdout = StringIO()
        # mystdout = ''
    inter_vel_all_t = []
    inter_h_all_t = []
    ikle_all_t = []
    point_all_t = []
    point_c_all_t = []
    sub_dom_all_t = []
    sub_pg_all_t = []
    sub_per_all_t = []

    # open the data ( and save the 1d figure if needed)
    [coord_pro, vh_pro, nb_pro_reach, sub_pro, div, q_step] = load_lammi(facies_path, transect_path, path_im,
                                                                         new_dir, project_preferences, savefig1d,
                                                                         transect_name,
                                                                         facies_name)

    # manage failed cases
    if coord_pro == [-99] or len(vh_pro) < 1:
        print('Error: LAMMI data not loaded')
        if q:
            sys.stdout = sys.__stdout__
            q.put(mystdout)
            return
        else:
            return

    # create the grid
    # first, create the grid for the whole profile (no need for velcoity and height data)
    [ikle_all, point_all_reach, point_c_all, blob, blob] \
        = manage_grid_mod.create_grid_only_1_profile(coord_pro[0], nb_pro_reach)
    inter_vel_all_t.append([])
    inter_h_all_t.append([])
    sub_dom_all_t.append([])
    sub_pg_all_t.append([])
    sub_per_all_t.append([])
    ikle_all_t.append(ikle_all)
    point_all_t.append(point_all_reach)
    point_c_all_t.append(point_c_all)

    for t in range(0, len(coord_pro)):
        # pass the subtrate data from percentage in edf code to [sub?dom] form in cemagref code
        sub_dom = []
        sub_pg = []
        for ind, subp in enumerate(sub_pro[t]):
            [sub_domp, sub_pgp] = substrate_mod.percentage_to_domcoarse(subp, dominant_case)
            # careful, there are real uncertainties here !!!!
            sub_pro[t][ind] = substrate_mod.edf_to_cemagref_by_percentage(subp)
            sub_domp = substrate_mod.edf_to_cemagref(sub_domp)
            sub_pgp = substrate_mod.edf_to_cemagref(sub_pgp)
            sub_pg.append(sub_pgp)
            sub_dom.append(sub_domp)

        # create the grid for this time step (including substrate data)
        [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all, inter_dom_all, inter_pg_all,
         inter_per_all] = manage_grid_mod.create_grid_only_1_profile(coord_pro[t], nb_pro_reach, vh_pro[t], sub_pg,
                                                                     sub_dom, sub_pro[t], True, div[t], True)
        inter_vel_all_t.append(inter_vel_all)
        inter_h_all_t.append(inter_height_all)
        ikle_all_t.append(ikle_all)
        point_all_t.append(point_all_reach)
        point_c_all_t.append(point_c_all)
        sub_dom_all_t.append(inter_dom_all)
        sub_pg_all_t.append(inter_pg_all)
        sub_per_all_t.append(inter_per_all)

    # save the data in an hdf5 (merge) file with hydro and subtrate data
    hdf5_mod.save_hdf5_hyd_and_merge(name_hdf5, name_prj, path_prj, model_type, 2, path_hdf5, ikle_all_t,
                                     point_all_t, [], inter_vel_all_t, inter_h_all_t, [], [], [], [], True,
                                     sub_pg_all_t, sub_dom_all_t, sub_per_all_t, sim_name=q_step, hdf5_type="merge")

    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put(mystdout)
        return
    else:
        return


def load_lammi(facies_path, transect_path, path_im, new_dir, project_preferences, savefig1d, transect_name,
               facies_name):
    """
    This function loads the data from the LAMMI model. A description of the LAMMI model is available in the
    documentation folder (LAMMIGuideMetho.pdf).

    :param transect_path: the path to the transect.txt path
    :param facies_path: the path the facies.txt file
    :param path_im: the path where to save the image
    :param project_preferences: the figure option
    :param savefig1d: create and save the figure related to the loading of the data (profile and so on)
    :param new_dir: if necessary, the path to the resultat file (.prn file). Be default, use the one in transect.txt
    :param transect_name: the name of the transect file, usually 'Transect.txt'
    :param facies_name: the name of the facies file, usually 'Facies.txt'
    :return:

    **Technical Comments**

    LAMMI is organised aroung group of transects. Transect are river profile which describe the river geometry.
    In LAMMI, there are four way of grouping transect. The facies is the a group a transect which is considered by HABBY
    to form a reach. The facies can then begroup in station. HABBY do not considered station directly, but it is
    possible to use the function "load_station" to get the station info if needed. The group Secteur are used in case
    where water is brought to the river.

    To load LAMMI data, we first load the facies file, which gives which transect are in which facies. Then, we use
    the transect file to know the length of each transect (length between transects along the river) and the
    name of the file containing the transect precise data. The name of the file is an absolute path to the file.
    This can be annoying if one want to move the files. Hence, we add the variable new_dir which correct the transect
    file in case the files containing the transect data have been moved (they should however all be in the same
    directory). This is done by the function get_transect_name().

    Then it uses the function load_transect_data to read all this data , file by file. Consequentely, we have
    the data in memory but no(x,y) coordinate. In addition, this data is is in the different form than in the other
    hydraulic model.

    To obtain the coordainte of the river and to put the data is the form usually needed by HABBY for 1.5D model
    (coord_pro, vh_pro, nb_pro_reach), we use the coord_lammi() function.

    There is also an optionnal check to control that the conversion between lammi and cemagref code is as normal.
    This check is only done if HABBY can find the habitat.txt file where the conversion can be modified by the user.
    Otherwise we assume that the normal conversion is used. Obviously, this check should be modifed if the edf
    to cemagref conversion is modified.


    """
    failload = [-99], [-99], [-99], [-99], [-99], [-99]

    if not project_preferences:
        project_preferences = create_default_project_properties_dict()

    # get the filename of the transect by facies
    [length_all, fac_filename_all] = get_transect_filename(facies_path, facies_name, transect_path, transect_name,
                                                           new_dir)
    if len(length_all) == 1:
        if length_all[0] == -99:
            return failload

    # load the transect data
    [dist_all, vel_all, height_all, sub_all, q_step] = load_transect_data(fac_filename_all)
    if len(dist_all) == 1:
        if dist_all[0] == -99:
            return failload

    # check if habitat.txt exist.
    # This is a lammi file which can be used to change the passage from lammi code to
    # cemagref code. This is very very rarely done and the info can not be transfered to HABBY.
    # Hence we just test if this habitat file and we refuse to execute if the code is not the right one.
    # If we do not find habitat.txt, we carry on
    code_ok = check_code_change(facies_path)
    if not code_ok:
        print('Error: The conversion from the EDF code to the Cemagref code given in habitat.txt was not the one'
              ' known by HABBY. Could not execute. \n')
        return failload

    # get the (not realistic) coordinates of the rivers and  the coordinate of the substrate
    [coord_pro, vh_pro, nb_pro_reach, sub_pro, div] = coord_lammi(dist_all, vel_all, height_all, sub_all, length_all)

    # create the figure
    if savefig1d:
        fig_lammi(vh_pro, coord_pro, nb_pro_reach, [0, 1, 2], 0, project_preferences, path_im)
        # plt.show()
        plt.close()  # avoid problem with matplotlib

    return coord_pro, vh_pro, nb_pro_reach, sub_pro, div, q_step


def check_code_change(facies_path):
    """
    If we can find the habitat.txt file, we check that the conversion from EDF to Cemagref code was done as in HABBY.
    In most case, the habiat.txt file will not be found. This is not a problem.
    :param facies_path: the path to the facies.txt file
    :return: a boolean
    """
    path_hab = os.path.join(os.path.dirname(facies_path), 'Fortran')
    pathname_hab = os.path.join(path_hab, 'Habitat.txt')

    # read habitat.txt
    if os.path.isfile(pathname_hab):
        try:
            with open(pathname_hab, 'rt') as f:
                data_hab = f.read()
        except IOError:
            print('Error: The file Habitat.txt could be found but could not be open. \n')
            return False
        data_hab = data_hab.split('\n')

        # check if we have the same code conversion
        stat_sub = False
        for ind, d in enumerate(data_hab):
            if d[:32] == 'Passage codification Utilisateur':
                try:
                    if int(data_hab[ind + 1]) == 2 and int(data_hab[ind + 2]) == 3 and int(data_hab[ind + 3]) == 4:
                        if int(data_hab[ind + 4]) == 5 and int(data_hab[ind + 5]) == 6 and float(
                                data_hab[ind + 6]) == 6.5:
                            if int(data_hab[ind + 7]) == 7 and int(data_hab[ind + 8]) == 8:
                                return True
                except ValueError:
                    return False
                return False
    else:
        # we do not mind if the file is not found
        return True


def load_station(station_path, station_name):
    """
    This function loads the station data from the LAMMI model. This is the data contains in Station.txt. It is not used
    by HABBY but it could be useful.

    :param station_path: the path to the station.txt file
    :param station_name: the name of the station file, usually 'Station.txt'
    :return: the length of the station (list of float) and the id of the facies for each station (list of list)
    """
    failload = [-99], [-99]

    filestation = os.path.join(station_path, station_name)

    if not os.path.isfile(filestation):
        print('Error: The station file was not found \n')
        return failload

    # load station data
    try:
        with open(filestation, 'rt') as f:
            data_station = f.read()
    except IOError:
        return failload
    data_station = data_station.split('\n')
    if len(data_station) < 1:
        print('Error: No data was found in the station file (1) \n')
        return failload

    # read station data
    lstat = []
    id_fac_all = []
    id_fac = []
    nbfac = 0

    for idx, l in enumerate(data_station):

        # new station
        if 'Longueur de la station' in l:
            # get the facies id from the station before
            if len(lstat) > 0:
                if nbfac == len(id_fac):
                    id_fac_all.append(id_fac)
                    id_fac = []
                else:
                    print('Error: One station was not well-formed in Station.txt (1) \n')
                    return failload
            # get the length of the station
            try:
                lstat_here = float(data_station[idx + 1])
            except ValueError or IndexError:
                print('Error: The length of one station could not be found \n')
                return failload
            lstat.append(lstat_here)
            # get the number of facies to check
            if 'Nombre de faci' in data_station[idx + 2]:  # avoid the accent :-)
                try:
                    nbfac = float(data_station[idx + 3])
                except ValueError or IndexError:
                    print('Error: The number of facies of one station could not be found \n')
                    return failload
        # read the info from the station loaded before
        if 'Num' in l and 'ro du faci' in l:  # avoid accent
            try:
                id_fac_here = float(data_station[idx + 1])
            except ValueError or IndexError:
                print('Error: The number of facies of one station could not be found \n')
                return failload
            id_fac.append(id_fac_here)
    if nbfac == len(id_fac):
        id_fac_all.append(id_fac)
    else:
        print('Error: One station was not well-formed in Station.txt (1) \n')
        return failload

    if len(lstat) == 0:
        print('Error: No data was found in the station file (1) \n')
        return failload

    return id_fac_all, lstat


def get_transect_filename(facies_path, facies_name, transect_path, transect_name, new_dir):
    """
    For each facies, we obtain the name of the transect file and the length of this reach

    :param facies_path: the path the facies.txt file
    :param facies_name: the name of the facies file, usually 'Facies.txt'
    :param transect_path: the path to the transect.txt path
    :param transect_name: the name of the transect file, usually 'Transect.txt'
    :param new_dir: If the folder with the transect have been moved, this argument allos it to be corrected without
           modification to transect.txt
    :return: the length of each transect (arranged by facies and station) and the filename with the transect info
    """

    failload = [-99], [-99]

    # load facies data
    filefacies = os.path.join(facies_path, facies_name)
    if not os.path.isfile(filefacies):
        print('Error: The facies file was not found \n')
        return failload
    try:
        with open(filefacies, 'rt') as f:
            data_facies = f.read()
    except IOError:
        return failload
    data_facies = data_facies.split('\n')
    if len(data_facies) < 1:
        print('Error: No data was found in the facies file (1) \n')
        return failload

    # read facies data
    lfac = []
    facies_id = []
    for idx, n in enumerate(data_facies):
        # new facies
        if 'Longueur du facies' in n:
            try:
                lfac_here = float(data_facies[idx + 1].strip())
                first_fac = float(data_facies[idx + 5].strip())
                nb_fac = float(data_facies[idx + 3].strip())
            except ValueError or IndexError:
                print('Error: the facies file was not in the right format (1) \n')
                return
            lfac.append(lfac_here)
            id_fac = range(int(first_fac), int(nb_fac + first_fac))
            facies_id.append(id_fac)
    if len(lfac) == 0:
        print('Error: the facies file was not in the right format \n')
        return

    # load transect file name
    filetrans = os.path.join(transect_path, transect_name)
    if not os.path.isfile(filetrans):
        print('Error: The file transect.txt was not found \n')
        return failload
    try:
        with open(filetrans, 'rt') as f:
            data_trans = f.read()
    except IOError:
        return failload
    data_trans = data_trans.split('\n')
    if len(data_trans) < 1:
        print('Error: No data was found in the transect file (1) \n')
        return failload

    # read transect data transect by transect
    ltrans = []
    file_trans = []
    for idx, n in enumerate(data_trans):
        if 'Longueur de re' in n:  # new transect
            # length of transect
            try:
                ltrans_here = float(data_trans[idx + 1].strip())
            except ValueError or IndexError:
                print('Error: the transect file was not in the right format \n')
                return failload
            ltrans.append(ltrans_here)
            # name of the file
            file_trans_here = data_trans[idx + 3].strip()
            # in case we have moved the transect file
            if new_dir != '':
                basename = os.path.basename(file_trans_here)
                if "\\" in basename:
                    basename = basename.split('\\')[-1]
                file_trans_here = os.path.join(new_dir, basename)
            if not os.path.isfile(file_trans_here):
                print('Error: A transect file is missing \n')
                return failload
            file_trans.append(file_trans_here)

    # get the data transect by transect
    fac_filename_all = []
    length_all = []
    for f in range(0, len(lfac)):
        # transect file for this facies
        fac_file_name = []
        for fid in facies_id[f]:
            try:
                fac_file_name.append(file_trans[fid - 1])
            except IndexError:
                print('Error: The transect was not found \n')
                return failload
        fac_filename_all.append(fac_file_name)
        # length for this facies
        fac_len = []
        for fid in facies_id[f]:
            try:
                fac_len.append(ltrans[fid - 1])
            except IndexError:
                print('Error: The transect was not found. \n')
                return failload
        if abs(sum(fac_len) - lfac[f]) > 1e-7:  # found a difference of 1e10 sometimes, machine precision
            print('Warning: the length of a facies is not coherent with the sum of the length of the transcect. \n')
        length_all.append(fac_len)

    return length_all, fac_filename_all


def load_transect_data(fac_filename_all):
    """
    This function loads the transect data. In this data, there are the subtrate, the height and the velocity data.

    :param fac_filename_all: the list of transect name organized by facies

    """
    failload = [-99], [-99], [-99], [-99]

    # get the simulation number (like a time step but depends on Q and not t)
    # This is done based on the first transect file (Q might change afterwards, HABBY does not see it)
    tfile = fac_filename_all[0][0]
    q_step = []
    try:
        with open(tfile, 'rt') as f:
            data_trans = f.readlines()[1:-1]
    except IOError:
        return failload
    # data_trans = data_trans.split('\n')
    if len(data_trans) < 1:
        print('Error: No data was found in the transect file' + tfile + '\n')
        return failload
    for d in data_trans[4:]:
        d = d.strip().split()
        if len(d) == 2:
            try:
                data_q = str(np.float(d[0]))
            except ValueError:
                print('Error: Discharge data not understood')
                return failload
            q_step.append(data_q)

    # preparation of the list based on simulation number and number of facies
    nb_sim = len(q_step)
    nb_fac = len(fac_filename_all)
    if nb_sim == 0:
        print('Error: No Simulation was found in the first transect file. \n')
        return failload
    dist_all = []
    height_all = []
    vel_all = []
    sub_all = []
    for n in range(0, nb_sim):
        dist_all.append([[None for x in range(1)] for y in range(nb_fac)])
        height_all.append([[None for x in range(1)] for y in range(nb_fac)])
        vel_all.append([[None for x in range(1)] for y in range(nb_fac)])
        sub_all.append([[None for x in range(1)] for y in range(nb_fac)])
    distt = []
    ht = []
    vt = []
    subt = []

    # reading the files
    # for each facies
    for fa in range(0, len(fac_filename_all)):
        # for each transect file
        for tfile in fac_filename_all[fa]:

            # load the transect data
            try:
                with open(tfile, 'rt') as f:
                    data_trans = f.read()
            except IOError:
                return failload
            data_trans = data_trans.split('\n')
            if len(data_trans) < 1:
                print('Error: No data was found in the transect file' + tfile + '\n')
                return failload
            t = 0

            # check unity
            unl = data_trans[4]
            unl = unl.split()
            if 'm' not in unl or 'm/s' not in unl:
                print('Warning: unity of the transect data not recongnized. \n')

            # read the transect file
            for idx, d in enumerate(data_trans[5:]):

                # for each new time step
                d = d.strip().split()
                if len(d) == 2:
                    if idx > 1:
                        if dist_all[t][fa][0] is not None:
                            dist_all[t][fa].append(distt)
                            height_all[t][fa].append(ht)
                            vel_all[t][fa].append(vt)
                            sub_all[t][fa].append(subt)
                        else:
                            dist_all[t][fa] = [distt]
                            height_all[t][fa] = [ht]
                            vel_all[t][fa] = [vt]
                            sub_all[t][fa] = [subt]
                        t += 1
                    distt = []
                    ht = []
                    vt = []
                    subt = []

                # data line
                if len(d) == 11:
                    # get substrate data
                    try:
                        sub_here = list(map(float, d[:8]))
                    except ValueError:
                        print('Error: Substrate data is not understood (1) \n')
                        return failload
                    if sum(sub_here) != 100:
                        print('Warning: one subtrate point is not coherent in file' + tfile + '\n')
                    subt.append(sub_here)
                    # get height, dist and vecloity data
                    try:
                        # get height data
                        ht.append(float(d[8]))
                        # get velocity
                        vt.append(float(d[9]))
                        # get dist data
                        distt.append(float(d[10]))
                    except ValueError:
                        print('Error: Substrate data is not understood (2) \n')
                        return failload
            # last time step
            if dist_all[t][fa][0] is not None:
                dist_all[t][fa].append(distt)
                height_all[t][fa].append(ht)
                vel_all[t][fa].append(vt)
                sub_all[t][fa].append(subt)
            else:
                dist_all[t][fa] = [distt]
                height_all[t][fa] = [ht]
                vel_all[t][fa] = [vt]
                sub_all[t][fa] = [subt]

    return dist_all, vel_all, height_all, sub_all, q_step


def coord_lammi(dist_all, vel_all, height_all, sub_all, length_all):
    """
    This function takes the data from the lammi outputs and get the coordinate for the river. It also
    reform the data to put it in the needed for HABBY (as the other 1.5D hydraulic model as hec_ras).

    To get the coordinates, we assume that the river is straight, that each facies is one after the other and
    that the river passes by the deepest point of the profile. In addition we assume that the profile are straight
    and perpendicular to the river. We assume that each facies (or reach for HABBY) is separated by a constant value

    We loop through all the profiles for all reach all time steps. For each profile, the x coordinate is identical
    for all point of the profile and is calculated using length_all. When a new reach starts, a x constant distance
    is added to the x coordinate. To find the y coordinate, we first pass from cell data (in lammi) to point data.
    The point are the center of each cell and the border of this cells.  Then, we find the higher water height and
    we assume that the river passes there. Hence, this is the origin of y-coordinate axes.

    We double the last and the first profile of each reach/facies. Indded, in HABBY,the information of a profile are
    given to the cells of the grid before and after the profile. If no cell would be done before or after the last/first
    profile, these profiles would have less wight than the other which is a problem to reproduce lammi results. This
    also avoid the case of a facies with only one profile, which is complicated to maange for the grid creation.

    To keep as much as possible the same data than in Lammi, we create four points for each orginal lammi cells. The
    three first points have the cell value of lammi and the last one is the average of the value of these cells and
    the next. The point are disposed so that the first and last points are close to the end of the cells.

    :param dist_all: the distance along profile by reach (or facies) and by time step
    :param vel_all: the velocity along profile by reach (or facies) and by time step
    :param height_all: the height along profile by reach (or facies) and by time step
    :param sub_all: the substrate data along profile by reach (or facies) and by time step. Eacu subtrate data is a list
           of eight number representing the percentage of each of the eight subtrate class.
    :param length_all: the distance between profile
    :return: coord_pro, nb_pro_reach and vh_pro in the same form as in final form for hec-ras, a variable with the eight
             subtrate data in a percetage form (sub_pro) and a variable to find the position of the middle profile
             (used by manage grid)
    """

    coord_pro = []
    nb_pro_reach = [0]
    vh_pro = []
    sub_pro = []
    div = []
    t = 0

    # for each "time" step
    for ti in range(0, len(dist_all)):
        dist_allt = dist_all[ti]
        vel_allt = vel_all[ti]
        height_allt = height_all[ti]
        sub_allt = sub_all[ti]

        coord_prot = []
        vh_prot = []
        sub_prot = []
        divt = []

        t += 1
        f = 0
        x = 0

        # facies/reach
        for fi in range(0, len(dist_allt)):
            f += 1
            dist_allf = dist_allt[fi]
            vel_allf = vel_allt[fi]
            height_allf = height_allt[fi]
            sub_allf = sub_allt[fi]

            # profile
            for pi in range(0, len(dist_allf)):
                dist_allp = dist_allf[pi]
                vel_allp = vel_allf[pi]
                height_allp = height_allf[pi]
                sub_allp = sub_allf[pi]
                rivind = np.argmax(np.array(height_allp))
                dist_here = 0
                sub_here = []
                vel_here = [0.0]
                height_here = [0.0]
                dist_allp_new = [0.0]
                ind = -1

                # point to get ditance, velocity, height, substrate
                for di in range(0, len(dist_allp) * 4):
                    if di % 4 == 0:
                        ind += 1
                        vel_here.append(vel_allp[ind])
                        height_here.append(height_allp[ind])
                        dist_here += 1 * dist_allp[ind] / 100
                    if di % 4 == 1 or di % 4 == 2:
                        vel_here.append(vel_allp[ind])
                        height_here.append(height_allp[ind])
                        dist_here += 49 * dist_allp[ind] / 100
                    if di % 4 == 3:
                        if di == len(dist_allp) * 4 - 1:
                            vel_here.append(0)
                            height_here.append(0)
                        else:
                            v1 = 0.5 * (vel_allp[ind] + vel_allp[ind + 1])
                            vel_here.append(v1)
                            h1 = 0.5 * (height_allp[ind] + height_allp[ind + 1])
                            height_here.append(h1)
                        dist_here += 1 * dist_allp[ind] / 100

                    # new dist_all at the center of the cell

                    dist_allp_new.append(dist_here)
                    sub_here.append(sub_allp[ind])

                # y coordinate (0 at the middle of the river for y)
                ypro = [i - dist_allp_new[rivind + 1] for i in dist_allp_new]

                # x-coordinates
                # if the first profile, let's doublt it
                if pi == 0:
                    # we will not use the first line of triangle (see maange_grid8, virtualstart)
                    if fi == 0:
                        x -= length_all[fi][pi] * 0.5
                    else:
                        x -= 0.5 * (length_all[fi - 1][-1] + length_all[fi][pi])
                    xpro = [x] * len(dist_allp_new)
                    x += length_all[fi][pi]
                    coord_pro_p = np.array([xpro, ypro, height_here, dist_allp_new])
                    vh_prop = [dist_allp_new, height_here, vel_here]
                    coord_prot.append(coord_pro_p)
                    vh_prot.append(vh_prop)
                    sub_prot.append(sub_here)
                    divt.append(0.5)

                xpro = [x] * len(dist_allp_new)
                if pi != len(dist_allf) - 1:
                    xhere = 0.5 * (length_all[fi][pi] + length_all[fi][pi + 1])
                else:
                    xhere = length_all[fi][pi]
                x += xhere

                # data for the profile
                vh_prop = [dist_allp_new, height_here, vel_here]
                coord_pro_p = np.array([xpro, ypro, height_here, dist_allp_new])
                coord_prot.append(coord_pro_p)
                vh_prot.append(vh_prop)
                sub_prot.append(sub_here)
                divt.append(0.5 * length_all[fi][pi] / xhere)

            # add the last profile to avoid having reach with only one profile
            if len(dist_allf) > 0:
                xpro = [x] * len(dist_allp_new)
                coord_pro_p = np.array([xpro, ypro, height_here, dist_allp_new])
                coord_prot.append(coord_pro_p)
                vh_prot.append(vh_prop)
                sub_prot.append(sub_here)
                divt.append(0.5)

            if ti == 0:
                nb_pro_reach.append(nb_pro_reach[-1] + len(dist_allf) + 2)
            x += 25  # reach is separated by additional 5m along the river

        coord_pro.append(coord_prot)
        vh_pro.append(vh_prot)
        sub_pro.append(sub_prot)
        div.append(divt)

    return coord_pro, vh_pro, nb_pro_reach, sub_pro, div


def fig_lammi(vh_pro, coord_pro, nb_pro_reach, pro_num, sim_num, project_preferences, path_im):
    """
    This function create a figure with the loaded lammi data.
    It work only for one time steps gven by the number sim_num.

    :param vh_pro: dist along the profile, height, vel
    :param coord_pro: x,y, dist along profile, height
    :param nb_pro_reach: the number of profile by reach
    :param pro_num: the profile to plot
    :param sim_num: the time step (or simuation) to plot
    :param project_preferences: the option for the figure
    :param path_im: path path where to save the figure
    """

    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    formate = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['pdf.fonttype'] = 42

    # time step
    coord_pro = coord_pro[sim_num]
    vh_pro = vh_pro[sim_num]

    # get the profile data
    for id, i in enumerate(pro_num):
        dist = coord_pro[i][3, :]
        vel = vh_pro[i][2]
        # vel[0] = vel[1]
        # vel[-1] = vel[-2]
        h = np.array(vh_pro[i][1])
        plt.figure(id)
        plt.suptitle("")
        ax1 = plt.subplot(313)
        # print velocity
        plt.step(dist, vel, where='mid', color='r')
        plt.xlim([dist[0] - 1 * 0.95, np.max(dist) * 1.05])
        if project_preferences['language'] == 0:
            plt.xlabel("Distance along the profile [m]")
            plt.ylabel(" Velocity [m/sec]")
        elif project_preferences['language'] == 1:
            plt.xlabel("Distance le long du profil [m]")
            plt.ylabel(" Vitesse [m/sec]")
        # print water height
        ax1 = plt.subplot(211)
        plt.plot(dist, -h, 'k')  # profile
        plt.fill_between(dist, -h, [0] * len(h), where=h >= [0] * len(h), facecolor='blue', alpha=0.5, interpolate=True)
        if project_preferences['language'] == 0:
            plt.xlabel("Distance along the profile [m]")
            plt.ylabel("Altitude of the profile [m]")
            plt.title("Profile " + str(i))
            plt.legend(("Profile", "Water surface"))
        elif project_preferences['language'] == 1:
            plt.xlabel("Distance le long du profil[m]")
            plt.ylabel("Elevation du profil [m]")
            plt.title("Profil " + str(i))
            plt.legend(("Profil", "Surface de l'eau"))
        plt.xlim([dist[0] - 1 * 0.95, np.max(dist) * 1.05])
        plt.ylim([np.min(-h) * 1.05, np.max(h) / 3])
        # save
        if formate == 0:
            plt.savefig(os.path.join(path_im, "LAMMI_profile_" + str(i) + '_day' +
                                     time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'),
                        dpi=project_preferences['resolution'],
                        transparent=True)
        if formate == 1:
            plt.savefig(os.path.join(path_im, "LAMMI_profile_" + str(i) + '_day' +
                                     time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'),
                        dpi=project_preferences['resolution'],
                        transparent=True)
        if formate == 2:
            plt.savefig(os.path.join(path_im, "LAMMI_profile_" + str(i) + '_day' +
                                     time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.jpg'),
                        dpi=project_preferences['resolution'],
                        transparent=True)

    # get an (x,y) view of the progile position
    plt.figure(len(pro_num))
    color_all = ['-xb', '-xg', '-xr', '-xc', '-xm', '-xy', '-xk']
    col = color_all[0]
    c = 0
    nb_fac = -1
    for j in range(0, len(coord_pro)):
        if j in nb_pro_reach:
            nb_fac += 1
            col = color_all[c]
            if c == len(color_all) - 1:
                c = 0
            else:
                c += 1
        plt.plot(coord_pro[j][0], coord_pro[j][1], col, label="Facies " + str(nb_fac + 1), markersize=3)  # profile
    plt.xlabel("x coord []")
    plt.ylabel("y coord []")
    plt.xlim(coord_pro[0][0][0] - 20, coord_pro[-1][0][0] + 20)
    if project_preferences['language'] == 0:
        plt.title("Position of the profiles (conceptual only)")
    if project_preferences['language'] == 1:
        plt.title("Position des profils (conceptuel)")
    # plt.axis('equal')  # if right angle are needed
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = OrderedDict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(), bbox_to_anchor=(1.1, 1), prop={'size': 10})
    if formate == 0 or formate == 1:
        plt.savefig(os.path.join(path_im, "LAMMI_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                    dpi=project_preferences['resolution'], transparent=True)
    if formate == 0 or formate == 3:
        plt.savefig(os.path.join(path_im, "LAMMI_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                    dpi=project_preferences['resolution'], transparent=True)
    if formate == 2:
        plt.savefig(os.path.join(path_im, "LAMMI_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                    dpi=project_preferences['resolution'], transparent=True)

    # plt.show()


def compare_lammi(filename_habby, filename_lammi, filename_lammi_sur):
    """
    This function compares the SPU for the trut done by lammi and by HABBY (using hydrological lammi output). It is
    not directly used by HABBY, but it can be useful to check the differences.

    :param filename_habby: the name and path of the text file giving the spu from HABBY (spu_xxx.txt)
    :param filename_lammi:  the name and the file of the lammi spu (FaciesTRF.txt)
    :param filename_lammi_sur: the name and the file of the lammi surface
    """
    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['pdf.fonttype'] = 42
    plt.rcParams['legend.loc'] = 'best'

    # load data from habby
    data_habby = np.loadtxt(filename_habby, skiprows=2)
    t_habby = data_habby[:, 0]
    reach_habby = data_habby[:, 1]
    area_habby = data_habby[:, 2]
    spu_habby = data_habby[:, 3]

    # load data from lammi spu
    # order of spu: adu, juv, ale, fray
    with open(filename_lammi, 'rt') as f:
        data_lammi = f.read()
    data_lammi = data_lammi.split('\n')
    data_lammi = data_lammi[5:]
    qnow = -99
    q_lammi = []  # difficult to know the length in advance
    reach_lammi = []
    spu_lammi = []
    for d in data_lammi:
        d = d.split()
        if len(d) == 1:
            try:
                qnow = float(d[0])
            except ValueError:
                print('Error: Could not read lammi output files (1)')
                return
        if len(d) == 9:
            try:
                rnow = float(d[0])
                spuadu = float(d[1])
            except ValueError:
                print('Error: Could not read lammi output files (2)')
                return
            reach_lammi.append(rnow)
            q_lammi.append(qnow)
            spu_lammi.append(spuadu)
    reach_lammi = np.array(reach_lammi)
    q_lammi = np.array(q_lammi)
    spu_lammi = np.array(spu_lammi)

    # load data surface
    with open(filename_lammi_sur, 'rt') as f:
        data_sur = f.read()
    data_sur = data_sur.split('\n')
    data_sur = data_sur[5:]
    area_lammi = np.zeros((len(spu_lammi),))
    ind = 0
    for d in data_sur:
        d = d.split()
        if len(d) == 1:
            try:
                qnow = float(d[0])
            except ValueError:
                print('Error: Could not read lammi output files (1)')
                return
        if len(d) == 2:
            try:
                area_lammi[ind] = float(d[1])
                ind += 1
            except ValueError:
                print('Error: Could not read lammi output files (2)')
                return

    # plot habby_lammi spu
    plot_spu = True
    if plot_spu:
        for r in range(0, int(max(reach_habby))):  # int(max(reach_habby))
            plt.figure()
            plt.plot(q_lammi[reach_lammi == r + 1], spu_habby[reach_habby == r], 'b')
            plt.plot(q_lammi[reach_lammi == r + 1], spu_lammi[reach_lammi == r + 1], 'g')
            # plt.plot(q_lammi[reach_lammi == r + 1], spu_habby[reach_habby == r]/area_habby[reach_habby == r], 'b')
            # plt.plot(q_lammi[reach_lammi == r + 1], spu_lammi[reach_lammi == r + 1]/area_lammi[reach_lammi == r + 1], 'g')
            plt.legend(('habby', 'lammi'), fancybox=True, framealpha=0.5)
            plt.xlabel('discharge [m^3/sec]')
            plt.ylabel('SPU')
            plt.title('Comparaison lammi-habby for the facies ' + str(r + 1))

    # plot the surface of each facies
    plot_sur = True
    if plot_sur:
        for r in range(0, int(max(reach_habby))):  # int(max(reach_habby))
            plt.figure()
            plt.plot(q_lammi[reach_lammi == r + 1], area_habby[reach_habby == r], 'b')
            plt.plot(q_lammi[reach_lammi == r + 1], area_lammi[reach_lammi == r + 1], 'g')
            plt.legend(('habby', 'lammi'), fancybox=True, framealpha=0.5)
            plt.xlabel('discharge [m^3/sec]')
            plt.ylabel('Area')
            plt.title('Comparaison lammi-habby for the facies ' + str(r + 1))

    plt.show()


def main():
    """
    Used to test this module
    """

    # path where the station.txt, transect.txt, secteur.txt
    path = r'E:\Mes docs\Mes emplois\IRSTEA\AIX\TAF\DATA\HABBY\HYDRAULIQUE\LAMMI\Entree'
    new_dir = r'E:\Mes docs\Mes emplois\IRSTEA\AIX\TAF\DATA\HABBY\HYDRAULIQUE\LAMMI\Resu\SimHydro'
    path_im = '.'

    open_lammi_and_create_grid(path, path, path_im, 'test_hdf5', '', '.', '.', new_dir, [], False,
                               'Transect.txt', 'Facies.txt', True)

    filename_habby = r'D:\Diane_work\dummy_folder\prt5\text_output\spu_Merge_LAMMI_04_08_2017_at_10_10_55.txt'
    filename_lammi = r'D:\Diane_work\output_hydro\LAMMI\ExempleDianeYann\Resu\Habitat\Facies\FacTRF.txt'
    # filename_lammi = r'D:\Diane_work\output_hydro\LAMMI\NesteOueil-S1-4Q\Resu\Habitat\Facies\FacTRF.txt'
    # filename_sur = r'D:\Diane_work\output_hydro\LAMMI\ExempleDianeYann\Resu\Habitat\Facies\SurfMouilFac.txt'
    # compare_lammi(filename_habby, filename_lammi, filename_sur)


def is_number(n):
    try:
        float(n)  # Type-casting the string to `float`.
        # If string is not a valid `float`,
        # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True


def is_integer(n):
    try:
        int(n)  # Type-casting the string to `float`.
        # If string is not a valid `float`,
        # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True


def construct_from_lammi(transectsfiledefintion):
    '''
    :param transectsfiledefintion: the file path of the output files from LAMMI Transect.txt which describes the .prn associated files
    :return: stationname : the name of the sation, lq the list of discharges [m3/s], lqdico a list given a dictionnary of numpy arrays for each discharge
    if iq is index of a discharge in lq ( lq[iq]=a discharge in [m3/s] )
    lqdico[iq]={'tin':tin,'mesh_substrate':mesh_substrate,'node_xy':node_xy,'node_hvz':node_hvz}
    tin the connexion table for the Triangular Irregular Network
    mesh_substrate the substrate percentages in the 8 classes Cemagref EVHA classification
    node_xy the x,y coordinate for nodes
    node_hvz the heigth of water, the velocity and the altitude of each node
    '''
    # print('construct_from_lammi')
    quadrangle_to_triangles=4 # chosen by programmer wether he wants 2 or 4 triangles by quadrangle 4, even if 4 is recommanded (for mapping reasons)  the 2 methods produce quite the same results in terms of hydrosignature
    sourcedirectory = os.path.dirname(transectsfiledefintion)
    if not os.path.isfile(transectsfiledefintion):
        return None, None, 'Transect.txt this file is required in the LAMMI input directory ' + sourcedirectory
    transectprn = []  # a list of pair of lists containing the exact [filename of each prn transect, Length of representativeness]
    with open(transectsfiledefintion, 'rt', encoding='utf8') as transectf:

        cheklevel, ldr = 0, 0
        level = ['Longueur de représentativité', '', 'Localisation du fichier de simulation transect']
        cheklevell = [x.split() for x in level]
        lines = transectf.readlines()
        bok = True
        for iline0, line in enumerate(lines):
            iline = iline0 + 1
            if '\n' in line:
                line = line[:-1]
            splline = line.split()
            if len(splline) != 0:
                if cheklevel == 0 or cheklevel == 2:
                    if len(splline) == len(cheklevell[cheklevel]):
                        for i, item in enumerate(splline):
                            if item.lower() != cheklevell[cheklevel][i].lower():
                                bok = False
                                break
                    else:
                        bok = False
                    if not bok:
                        return None, None, 'Transect.txt line ' + str(iline) + ' the mention' + level[
                            cheklevel] + ' is mandatory'
                    else:
                        cheklevel += 1
                elif cheklevel == 1:
                    if len(splline) != 1 or not (is_number(splline[0])):
                        return None, None, 'Transect.txt line ' + str(
                            iline) + ' a single number for the transect length is mandatory'
                    else:
                        ldr = float(line)
                        cheklevel += 1
                elif cheklevel == 3:
                    try:
                        filenameprn = os.path.join(sourcedirectory, os.path.basename(line))
                    except ValueError:
                        return None, None, 'Transect.txt line ' + str(
                            iline) + ' a path with a namefile.prn is mandatory'
                    if not os.path.isfile(filenameprn):
                        return None, None, filenameprn + ' This file is required in the LAMMI input directory ' \
                                                         'according to the Transect.txt file definition ' + sourcedirectory
                    transectprn.append([filenameprn, ldr])
                    cheklevel = 0

    # PHASE2 : reading each prn transect #################################################
    lq = []
    lqdico = []
    newnodeindex = []
    nbiq = 0
    y0, z00, slope = 500, 500, 0.04
    hmoyupstreamq = []
    for iprn in range(len(transectprn)):
        if iprn == 0:  # for a given cross-section  for each discharge the mesh description of the river began at the same xdep
            xdep = 0  # the current upstream abcissa for the current discharge
        else:
            xdep += transectprn[iprn - 1][1]

        if iprn == 1:
            nbiq = iq
        if iprn > 1 and nbiq != iq:
            return None, None, transectprn[iprn][0] + ' the number of discharges provided is less than what was ' \
                                                      'expected in ' + referencefile
        with open(transectprn[iprn][0], 'rt') as prnf:  # , encoding='utf8'
            cheklevel, iq = 0, 0
            level = ['# Rivière NesteOueilStation 1Facies 1Transect 1', '# Hauteur et vitesses moyennes calculees',
                     'S1 S2 S3 S4 S5 S6 S7 S8 Hauteur Vitesse Largeur', 'I3 I3 I3 I3 I3 I3 I3 I3 F7.2 F7.2 F7.2',
                     '.  .  .  .  .  .  .  .   m     m/s  m']
            cheklevell = [x.split() for x in level]
            bok = True
            lines = prnf.readlines()
            for iline0, line in enumerate(lines):
                iline = iline0 + 1
                if '\n' in line:
                    line = line[:-1]
                splline = line.split()
                if len(splline) != 0:
                    if cheklevel < 5:  # Head of the file
                        if len(splline) == len(cheklevell[cheklevel]):
                            for i, item in enumerate(splline):
                                if item.lower() != cheklevell[cheklevel][i].lower():
                                    if not (cheklevel == 0 and i>1):
                                        bok = False
                                        break
                        else:
                            bok = False
                        if cheklevel == 0:
                            if splline[2][-7:].lower() == 'station':
                                stationname2 = splline[2][:-7]
                            else:
                                stationname2 = splline[2]
                        if iprn == 0:
                            stationname = stationname2
                        else:
                            if stationname != stationname2:
                                return None, None, transectprn[iprn][0] + ' line ' + str(
                                    iline) + ' the station Name is not the same as ' + transectprn[0][0]
                        if not bok:
                            return None, None, transectprn[iprn][0] + ' line ' + str(iline) + ' the mention ' + level[
                                cheklevel] + ' is mandatory'
                        else:
                            cheklevel += 1
                    elif cheklevel == 5:  # Q number_of_vertices
                        if len(splline) != 2:
                            bok = False
                        else:
                            if not (is_number(splline[0]) and is_integer(splline[1])):
                                bok = False
                        if not bok:
                            return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                   ' two numbers are required : one for the discharge, the other for the ' \
                                   'vertices number describing the corss-section'
                        else:
                            if iprn == 0:
                                lq.append(splline[0])
                                if iq == 0:
                                    referencefile = transectprn[0][0]
                            else:
                                if splline[0] != lq[iq]:
                                    return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                           ' the discharge value is not the expected one accordign to the ' \
                                           'refererence file : ' + referencefile
                            if iq != 0:
                                if nbvertices != ivertices:
                                    return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                           ' the number of verticals provided previously was not what was expected'
                            nbvertices, ivertices = int(splline[1]), 0
                            cheklevel += 1
                            iq += 1  # next Q index
                            if iprn > 0 and nbiq < iq:
                                return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                       ' the number of discharges provided is more than what was expected in ' + referencefile
                            subpercentagecemagref = np.zeros((nbvertices, 8), dtype=np.int64)
                            hv = np.zeros((nbvertices, 2), dtype=np.float64)
                            la = np.zeros(nbvertices, dtype=np.float64)
                    elif cheklevel == 6:
                        if len(splline) != 11:
                            return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                   ' 11 numbers are required  for a vertical description, eight of percentages of ' \
                                   'substrate Code EDF R&D  then depth ,velocity and represetative width of ' \
                                   'the present vertical'
                        else:
                            for j in range(8):
                                if not (is_number(splline[j])):
                                    bok = False
                                else:
                                    k = j + 1 if j < 5 else j  # substrat transformation Code EDF R&D (Cailleux 1954) to Code Cemagref EVHA
                                    subpercentagecemagref[ivertices][k] += float(splline[j])
                            if not bok:
                                return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                       ' the first eight value must be integer values of percentages of ' \
                                       'substrate Code EDF R&D (Cailleux 1954) '
                            if np.sum(subpercentagecemagref[ivertices, :]) != 100:
                                return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                       ' the sum of the first eight value  describing percentages of ' \
                                       'substrate Code EDF R&D (Cailleux 1954) must be 100%'
                            for j in (8, 9, 10):
                                if not (is_number(splline[j])):
                                    bok = False
                                else:
                                    if float(splline[j]) < 0:
                                        bok = False
                                if not bok:
                                    print()
                                    return None, None, transectprn[iprn][0] + ' line ' + str(iline) + \
                                           ' the last three values must be numericals and positives for ' \
                                           'depth velocity and represetative width of the present vertical '
                            hv[ivertices][0], hv[ivertices][1], la[ivertices] = float(splline[8]), float(
                                splline[9]), float(splline[10])
                            ivertices += 1
                            if nbvertices == ivertices:
                                cheklevel = 5
                                # PHASE A : building one tin for a cross-section at a fixed discharge #################################################
                                ldr = transectprn[iprn][1]

                                if quadrangle_to_triangles==2:
                                    tin = np.zeros((4 * nbvertices, 3), dtype=np.int64)
                                    mesh_substrate = np.zeros((4 * nbvertices, 8), dtype=np.int64)
                                    node_xy = np.zeros((4 * nbvertices + 2, 2), dtype=np.float64)
                                    node_hvz = np.zeros((4 * nbvertices + 2, 3), dtype=np.float64)
                                    for k in range(0, 4 * nbvertices - 1, 2):
                                        tin[k, :] = [k, k + 1, k + 2]
                                        tin[k + 1, :] = [k + 1, k + 3, k + 2]
                                    imesh = 0
                                    for k in range(nbvertices):
                                        for kk in range(4):
                                            mesh_substrate[imesh + kk, :] = subpercentagecemagref[k, :]
                                        imesh += 4
                                    ytop = (y0 + np.sum(la)) / 2
                                    # Defining/calclulating z0 the upstream altitude of the water surface for each discharge
                                    if iprn == 0:
                                        for k in range(nbvertices):
                                            if k == 0:
                                                area = la[k] * (hv[k][0] + (
                                                        hv[k][0] + (hv[k][0] * la[k + 1] + hv[k + 1][0] * la[k]) / (
                                                        la[k] + la[k + 1])) / 2) / 2
                                            elif k == nbvertices - 1:
                                                area += la[k] * (hv[k][0] + (
                                                        hv[k][0] + (hv[k][0] * la[k - 1] + hv[k - 1][0] * la[k]) / (
                                                        la[k] + la[k - 1])) / 2) / 2
                                            else:
                                                area += la[k] * ((hv[k][0] + (
                                                        hv[k][0] * la[k + 1] + hv[k + 1][0] * la[k]) / (
                                                                          la[k] + la[k + 1])) + (
                                                                         hv[k][0] + (
                                                                         hv[k][0] * la[k - 1] + hv[k - 1][0] * la[
                                                                     k]) / (
                                                                                 la[k] + la[k - 1]))) / 4
                                        hmoyupstreamq.append(area / np.sum(la))
                                    iqq = iq - 1
                                    if iqq == 0:
                                        z0 = z00
                                    else:
                                        z0 = z00 + hmoyupstreamq[iqq] - hmoyupstreamq[0]
                                    # left river edge
                                    node_xy[0, :] = [xdep, ytop]
                                    node_xy[1, :] = [xdep + ldr, ytop]
                                    node_hvz[0, :] = [0, 0, z0 - xdep * slope]
                                    node_hvz[1, :] = [0, 0, z0 - (xdep + ldr) * slope]
                                    for k in range(nbvertices):  # inside river
                                        # each vertical build 2 points
                                        ytop -= la[k] / 2
                                        node_xy[4 * k + 2, :] = [xdep, ytop]
                                        node_xy[4 * k + 3, :] = [xdep + ldr, ytop]
                                        node_hvz[4 * k + 2, :] = [hv[k][0], hv[k][1], z0 - xdep * slope - hv[k][0]]
                                        node_hvz[4 * k + 3, :] = [hv[k][0], hv[k][1], z0 - (xdep + ldr) * slope - hv[k][0]]
                                        # interpolated verticals/points
                                        ytop -= la[k] / 2
                                        node_xy[4 * k + 4, :] = [xdep, ytop]
                                        node_xy[4 * k + 5, :] = [xdep + ldr, ytop]
                                        if k != nbvertices - 1:
                                            hi = (hv[k][0] * la[k + 1] + hv[k + 1][0] * la[k]) / (la[k] + la[k + 1])
                                            vi = (hv[k][1] * la[k + 1] + hv[k + 1][1] * la[k]) / (la[k] + la[k + 1])
                                        else:  # right river edge
                                            hi, vi = 0, 0
                                        node_hvz[4 * k + 4, :] = [hi, vi, z0 - xdep * slope - hi]
                                        node_hvz[4 * k + 5, :] = [hi, vi, z0 - (xdep + ldr) * slope - hi]

                                elif quadrangle_to_triangles==4:
                                    tin = np.zeros((8 * nbvertices, 3), dtype=np.int64)
                                    mesh_substrate = np.zeros((8 * nbvertices, 8), dtype=np.int64)
                                    node_xy = np.zeros((6 * nbvertices + 2, 2), dtype=np.float64)
                                    node_hvz = np.zeros((6 * nbvertices + 2, 3), dtype=np.float64)
                                    nbmeshk=0
                                    for k in range(4, 6 * nbvertices +2, 3):
                                        if k==4:
                                            tin[0, :] = [4, 0, 1]
                                            tin[1, :] = [4, 1, 3]
                                            tin[2, :] = [4, 3, 2]
                                            tin[3, :] = [4, 2, 0]
                                        else:
                                            tin[nbmeshk, :] = [k, k -5, k -4]
                                            tin[nbmeshk+1, :] = [k, k -4, k -1]
                                            tin[nbmeshk+2, :] = [k, k -1, k -2]
                                            tin[nbmeshk+3, :] = [k, k -2, k -5]
                                        nbmeshk+=4
                                    imesh = 0
                                    for k in range(nbvertices):
                                        for kk in range(8):
                                            mesh_substrate[imesh + kk, :] = subpercentagecemagref[k, :]
                                        imesh += 8
                                    ytop = (y0 + np.sum(la)) / 2
                                    # Defining/calclulating z0 the upstream altitude of the water surface for each discharge
                                    if iprn == 0:
                                        for k in range(nbvertices):
                                            if k == 0:
                                                area = la[k] * (hv[k][0] + (
                                                        hv[k][0] + (hv[k][0] * la[k + 1] + hv[k + 1][0] * la[k]) / (
                                                        la[k] + la[k + 1])) / 2) / 2
                                            elif k == nbvertices - 1:
                                                area += la[k] * (hv[k][0] + (
                                                        hv[k][0] + (hv[k][0] * la[k - 1] + hv[k - 1][0] * la[k]) / (
                                                        la[k] + la[k - 1])) / 2) / 2
                                            else:
                                                area += la[k] * ((hv[k][0] + (
                                                        hv[k][0] * la[k + 1] + hv[k + 1][0] * la[k]) / (
                                                                          la[k] + la[k + 1])) + (
                                                                         hv[k][0] + (
                                                                         hv[k][0] * la[k - 1] + hv[k - 1][0] * la[
                                                                     k]) / (
                                                                                 la[k] + la[k - 1]))) / 4
                                        hmoyupstreamq.append(area / np.sum(la))
                                    iqq = iq - 1
                                    if iqq == 0:
                                        z0 = z00
                                    else:
                                        z0 = z00 + hmoyupstreamq[iqq] - hmoyupstreamq[0]
                                    # left river edge
                                    node_xy[0, :] = [xdep, ytop]
                                    node_xy[1, :] = [xdep + ldr, ytop]
                                    node_hvz[0, :] = [0, 0, z0 - xdep * slope]
                                    node_hvz[1, :] = [0, 0, z0 - (xdep + ldr) * slope]
                                    for k in range(nbvertices):  # inside river
                                        # each vertical build 2 points
                                        ytop -= la[k] / 2
                                        node_xy[6 * k + 2, :] = [xdep, ytop]
                                        node_xy[6 * k + 3, :] = [xdep + ldr, ytop]
                                        node_hvz[6 * k + 2, :] = [hv[k][0], hv[k][1], z0 - xdep * slope - hv[k][0]]
                                        node_hvz[6 * k + 3, :] = [hv[k][0], hv[k][1], z0 - (xdep + ldr) * slope - hv[k][0]]
                                        # interpolated verticals/points
                                        ytop -= la[k] / 2
                                        node_xy[6 * k + 5, :] = [xdep, ytop]
                                        node_xy[6 * k + 6, :] = [xdep + ldr, ytop]
                                        if k != nbvertices - 1:
                                            hi = (hv[k][0] * la[k + 1] + hv[k + 1][0] * la[k]) / (la[k] + la[k + 1])
                                            vi = (hv[k][1] * la[k + 1] + hv[k + 1][1] * la[k]) / (la[k] + la[k + 1])
                                        else:  # right river edge
                                            hi, vi = 0, 0
                                        node_hvz[6 * k + 5, :] = [hi, vi, z0 - xdep * slope - hi]
                                        node_hvz[6 * k + 6, :] = [hi, vi, z0 - (xdep + ldr) * slope - hi]
                                        if k==0:
                                            node_xy[ 4, :]=(node_xy[0, :]+node_xy[1 , :]+
                                                                   node_xy[2, :]+node_xy[3, :])/4
                                            node_hvz[4, :] = (node_hvz[0, :] + node_hvz[1, :] +
                                                             node_hvz[2, :] + node_hvz[3, :]) / 4
                                        else:
                                            node_xy[6 * k + 4, :] = (node_xy[6 * k - 1, :] + node_xy[6 * k, :] +
                                                                     node_xy[6 * k + 2, :] + node_xy[6 * k + 3, :]) / 4
                                            node_hvz[6 * k + 4, :] = (node_hvz[6 * k - 1, :] + node_hvz[6 * k, :] +
                                                                    node_hvz[6 * k + 2, :] + node_hvz[6 * k + 3, :]) / 4
                                        node_xy[6 * k + 7, :] = (node_xy[6 * k + 2, :]+node_xy[6 * k + 3, :] +
                                                                 node_xy[6 * k + 5, :]+node_xy[6 * k + 6, :])/4
                                        node_hvz[6 * k + 7, :] = (node_hvz[6 * k + 2, :]+node_hvz[6 * k + 3, :] +
                                                                 node_hvz[6 * k + 5, :]+node_hvz[6 * k + 6, :])/4

                                # PHASE B : building a complete set of tin/nodes for each discharge by adding tin/nodes builds for each cross section #################################################
                                if iprn == 0:
                                    lqdico.append({'tin': tin, 'mesh_substrate': mesh_substrate, 'node_xy': node_xy,
                                                   'node_hvz': node_hvz})
                                    newnodeindex.append((quadrangle_to_triangles+2) * nbvertices + 2)
                                else:
                                    lqdico[iq - 1]['tin'] = np.vstack(
                                        (lqdico[iq - 1]['tin'], tin + newnodeindex[iq - 1]))
                                    lqdico[iq - 1]['mesh_substrate'] = np.vstack(
                                        (lqdico[iq - 1]['mesh_substrate'], mesh_substrate))
                                    lqdico[iq - 1]['node_xy'] = np.vstack((lqdico[iq - 1]['node_xy'], node_xy))
                                    lqdico[iq - 1]['node_hvz'] = np.vstack((lqdico[iq - 1]['node_hvz'], node_hvz))
                                    newnodeindex[iq - 1] += (quadrangle_to_triangles+2) * nbvertices + 2

    if nbiq != iq and iprn!=0:
        return None, None, transectprn[iprn][0] + ' the number of discharges provided is less ' \
                                                  'than what was expected in ' + referencefile

    return stationname, lq, lqdico


if __name__ == '__main__':
    # main()
    stationname, lq, lqdico = construct_from_lammi(r'E:\HABBY\LAMMI\2021\Test\Transect.txt')
