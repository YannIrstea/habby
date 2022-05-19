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
from scipy import stats
from scipy import optimize
from scipy import interpolate
import re
import matplotlib.pyplot as plt
import h5py
from multiprocessing import Value

from lxml import etree as ET

import src.dev_tools_mod
from src_GUI import estimhab_GUI
from src import hdf5_mod
from src.project_properties_mod import load_project_properties, save_project_properties
from src.bio_info_mod import read_pref, copy_or_not_user_pref_curve_to_input_folder
from src.plot_mod import plot_stat_data
from src.user_preferences_mod import user_preferences
from src.variable_unit_mod import HydraulicVariableUnitManagement


class Stathab:
    """
    The class for the Stathab model
    """

    def __init__(self, name_prj, path_prj):
        self.qlist = []  # the list of dicharge for each reach, usually in rivdis.txt
        self.qwh = []  # the discharge, the width and height
        # at least at two different dicharges (rivqvh.txt) a list of np.array
        self.disthmes = []  # the measured distribution of height (rivdist.txt) a list of np.array
        self.qhmoy = []  # the mean height and q (2 first llines of rivdis.txt)
        self.dist_gran = []  # the distribution of granulo (rivgra.txt)-only used by temperate river, a list of np.array
        self.data_ii = []  # only used by tropical river. The slope, waterfall height and length of river
        self.fish_chosen = []  # the name of the fish to be studied, the name should also be in pref.txt
        self.lim_all = []  # the limits or bornes of h,q and granulio (born*.txt)
        self.name_reach = []  # the list with the name of the reaches
        self.j_all = dict()  # habitat values
        self.data_list = list()  # list by reach of dict of all reach data values
        self.granulo_mean_all = []  # average granuloa
        self.vclass_all = []  # volume of each velocity classes
        self.hclass_all = []  # surface height for all classes
        self.rclass_all = []  # granulo surface for all classes
        self.h_all = []  # mean height of all the reaches
        self.v_all = []  # mean velocity of all the reaches
        self.w_all = []  # mean width of all the reaches
        self.q_all = []  # discharge
        self.hborn_Stahabsteep=[]# only for Stahab_steep the mean values of h for each class of height per reach X discharge
        self.vborn_Stahabsteep = []  # only for Stahab_steep the mean values of v for each class of velocity per reach X discharge
        self.dist_hs_all = [] #frequency distribution for height per reach X discharge
        self.dist_vs_all = []  # frequency distribution for velocity per reach X discharge
        self.fish_chosen = []  # the name of the fish
        self.riverint = 0  # the river type (0 stahab, 1 stahtab steep)
        self.path_im = os.path.join(path_prj, "output", "figures")  # path where to save the image
        self.path_hdf5 = os.path.join(path_prj, "hdf5")
        self.load_ok = False  # a boolean to manage the errors
        #  during the load of the files and the hdf5 creation and calculation
        self.path_prj = path_prj
        self.name_prj = name_prj
        # get the option for the figure in a dict
        self.project_properties = []
        self.path_txt = path_prj  # path where to save the text

    def load_stathab_from_txt(self, end_file_reach, name_file_allreach, path):
        """
        A function to read and check the input from stathab based on the text files.
        All files should be in the same folder.
        The file Pref.txt is read in run_stathab.
        If self.fish_chosen is not present, all fish in the preference file are read.

        :param end_file_reach: the ending of the files whose names depends on the reach (with .txt or .csv)
        :param name_file_allreach: the name of the file common to all reaches
        :param path: the path to the file
        :return: the inputs needed for run_stathab
        """
        self.load_ok = False
        # self.name_reach
        self.name_reach = load_namereach(path )
        if self.name_reach == [-99]:
            return
        nb_reach = len(self.name_reach)

        # prep
        self.qwh = []
        self.qlist = []
        self.disthmes = []
        self.qhmoy = []
        self.dist_gran = []
        self.data_ii = []

        # read the txt files reach by reach
        for r in range(0, nb_reach):

            for ef in end_file_reach:
                # open rivself.qwh.txt
                if ef[-7:-4] == 'qhw':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    qwh_r = load_float_stathab(filename, True)
                    if np.array_equal(qwh_r, [-99]):  # if failed
                        return
                    else:
                        self.qwh.append(qwh_r)
                    if len(qwh_r[0]) != 3:
                        print('Error: The file called ' + filename + ' is not in the right format. Three columns '
                                                                     'needed. \n')
                        return
                    if len(qwh_r) < 2:
                        print('Error: The file called ' + filename + ' is not in the right format. Minimum two rows '
                                                                     'needed. \n')
                        return

                # open rivdeb.txt
                if ef[-7:-4] == 'deb':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    qlist_r = load_float_stathab(filename, True)
                    if np.array_equal(qlist_r, [-99]):
                        return
                    else:
                        self.qlist.append(qlist_r)
                    if len(qlist_r) < 2:
                        print('Error: two discharges minimum are needed in ' + filename + '\n')
                        return

                # open riv dis
                if ef[-7:-4] == 'dis':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    dis_r = load_float_stathab(filename, True)
                    if np.array_equal(dis_r, [-99]):  # if failed
                        return
                    if len(dis_r) < 4:
                        print('Error: The file called ' + filename + ' is not in the right format. At least four '
                                                                     'values needed. \n')
                        return
                    else:
                        # 0 = the discharge, 1 = the mean depth
                        if len(dis_r[2:]) != 20:
                            print('Warning: the number of class found is not 20 \n')
                        self.disthmes.append(dis_r[2:])
                        self.qhmoy.append(dis_r[:2])

                # open rivgra.txt
                if ef[-7:-4] == 'gra':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    dist_granulo_r = load_float_stathab(filename, True)
                    if np.array_equal(dist_granulo_r, [-99]):  # if failed
                        return
                    if len(dist_granulo_r) != 12:
                        print('Error: The file called ' + filename +
                              ' is not in the right format. 12 roughness classes are needed.\n')
                        return
                    else:
                        self.dist_gran.append(dist_granulo_r)

                # open data_ii.txt (only for tropical rivers)
                if ef[-6:-4] == 'ii':
                    filename = os.path.join(path, self.name_reach[r] + ef)
                    data_ii_r = load_float_stathab(filename, False)
                    if np.array_equal(data_ii_r, [-99]):  # if failed
                        return
                    if len(data_ii_r) != 3:
                        print(
                            'Error: The file called ' + filename + ' is not in the right format.  Three values needed.\n')
                        return
                    self.data_ii.append(data_ii_r)

        # open the files with the limits of class
        self.lim_all = []
        for b in range(0, len(name_file_allreach)):
            if name_file_allreach[b] != 'Pref.txt':
                filename = name_file_allreach[b]
                filename = os.path.join(path, filename)
                born = load_float_stathab(filename, False)
                if np.array_equal(born, [-99]):
                    return
                if len(born) < 2:
                    print('Error: The file called ' + filename + ' is not in the right format.  '
                                                                 'At least two values needed. \n')
                    return
                else:
                    self.lim_all.append(born)

        # usually not chosen fish if using the txt files
        self.fish_chosen = ['all_fish']
        # but try anyway to find fish
        filename = os.path.join(path, 'fish.txt')
        if os.path.isfile(filename):
            with open(filename, 'rt') as f:
                data = f.read()
            self.fish_chosen = data.split('\n')

        self.load_ok = True

    def load_stathab_from_hdf5(self):
        """
        A function to load the file from an hdf5 whose name is given in the xml project file. If the name of the
        file is a relative path, use the path_prj to create an absolute path.

        It works for tropical and temperate rivers. It checks the river type in the hdf5  files and
        used this river type regardless of the one curently used by the GUI. The method load_hdf5 in stathab_GUI
        get the value of self.riverint from the object mystathab to check the cohrenence between the GUI and the loaded
        hdf5.
        """
        self.load_ok = False
        # find the path to the xml file
        fname = os.path.join(self.path_prj, self.name_prj + '.habby')
        if not os.path.isfile(fname):
            print('Error: The .habby project file was not found. Save the project in the General Tab. \n')
            return
        parser = ET.XMLParser(remove_blank_text=True)
        doc = ET.parse(fname, parser)
        root = doc.getroot()
        child = root.find(".//hdf5Stathab")
        if child is None:  # if there is data for STATHAB
            print("Error: No hdf5 file for Stathab is written in the .habby project file. \n")
            return
        if not child.text:
            print("Error: No hdf5 file is written in the .habby project file. (2) \n")
            return

        # load the h5 file
        fname_h5 = child.text
        blob = estimhab_GUI.StatModUseful()
        blob.path_prj = self.path_prj
        blob.name_prj = self.name_prj
        path_hdf5 = blob.find_path_hdf5_est()
        full_fname_hdf5 = os.path.join(path_hdf5, fname_h5)
        if os.path.isfile(fname_h5) or os.path.isfile(full_fname_hdf5):
            try:
                if os.path.isabs(fname_h5):
                    file_stathab = h5py.File(fname_h5, 'r+')
                else:
                    if self.path_prj:
                        file_stathab = h5py.File(full_fname_hdf5, 'r+')
                    else:
                        print('Error" No path to the project given although a relative path was provided')
                        return
            except OSError:
                print('Error: the hdf5 file could not be loaded.\n')
                return
        else:
            print("Error: The hdf5 file is not found. \n")
            return

        # prepare the data to be found
        basename1 = 'Info_general'

        # find the river type
        rinverint = file_stathab.attrs['riverint']
        try:
            riverint = int(rinverint)
            if riverint > 2:
                print('The river type in the hdf5 should be 0,1,or 2.')
                return
        except ValueError:
            print('The river type in the hdf5 was not well formed')
            file_stathab.close()
            return
        self.riverint = riverint  # careful, must be "send" back to the GUI

        # load reach_name
        try:
            gen_dataset = file_stathab[basename1 + "/reach_name"]
        except KeyError:
            file_stathab.close()
            print(
                'Error: the dataset reach_name is missing from the hdf5 file. Is ' + fname_h5 + ' a stathab input? \n')
            return
        if len(list(gen_dataset.values())) == 0:
            print('Error: The data name_reach could not be read. \n')
            return
        gen_dataset = list(gen_dataset.values())[0]
        gen_dataset = np.array(gen_dataset)
        if len(gen_dataset) == 0:
            print('Error: no reach names found in the hdf5 file. \n')
            file_stathab.close()
            return
        # hdf5 cannot strore string directly, needs conversion
        #  array[3,-2] is needed after bytes to string conversion
        for r in range(0, len(gen_dataset)):
            a = str(gen_dataset[r])
            self.name_reach.append(a[3:-2])

        # load limits
        if self.riverint == 0:
            gen_dataset_name = ['lim_h', 'lim_v', 'lim_g']
            for i in range(0, len(gen_dataset_name)):
                try:
                    gen_dataset = file_stathab[basename1 + "/" + gen_dataset_name[i]]
                except KeyError:
                    print("Error: the dataset" + gen_dataset_name[i] + "is missing from the hdf5 file.\n")
                    file_stathab.close()
                    return
                gen_dataset = list(gen_dataset.values())[0]
                if len(np.array(gen_dataset)) < 2:
                    print('Error: Limits of surface/volume could not be extracted from the hdf5 file. \n')
                    file_stathab.close()
                    return
                self.lim_all.append(np.array(gen_dataset))

            # get the chosen fish
            try:
                gen_dataset = file_stathab[basename1 + "/fish_chosen"]
            except KeyError:
                file_stathab.close()
                print('Error: the dataset fish_chosen is missing from the hdf5 file. \n')
                return
            gen_dataset = list(gen_dataset.values())[0]
            gen_dataset = np.array(gen_dataset)
            if len(gen_dataset) == 0:
                pass
                # print('Warning: no fish names found in the hdf5 file from stathab.\n')
                # file_stathab.close()
                # return
            # hdf5 cannot strore string directly, needs conversion
            #  array[3,-2] is needed after bytes to string conversion
            for f in range(0, len(gen_dataset)):
                a = str(gen_dataset[f])
                np.append(self.fish_chosen, a[3:-2])

        # get the data by reach
        if self.riverint == 0:
            reach_dataset_name = ['qlist', 'qwh', 'disthmes', 'qhmoy', 'dist_gran']
            reach_var = [self.qlist, self.qwh, self.disthmes, self.qhmoy, self.dist_gran]
        elif self.riverint == 1 or self.riverint == 2:
            reach_dataset_name = ['qlist', 'qwh', 'data_ii']
            reach_var = [self.qlist, self.qwh, self.data_ii]
        else:
            print('Error: self.riverint should be lower than two.')
            file_stathab.close()
            return

        for r in range(0, len(self.name_reach)):
            for i in range(0, len(reach_dataset_name)):
                try:
                    reach_dataset = file_stathab[self.name_reach[r] + "/" + reach_dataset_name[i]]
                except KeyError:
                    print("Error: the dataset" + reach_dataset_name[i] + "is missing from the hdf5 file. \n")
                    file_stathab.close()
                    return
                reach_dataset = list(reach_dataset.values())[0]
                if not reach_dataset:
                    print(
                        'Error: The variable ' + reach_dataset_name[r] + 'could not be extracted from the hdf5 file.\n')
                reach_var[i].append(reach_dataset)

        self.load_ok = True
        file_stathab.close()

    def create_hdf5(self):
        """
        A function to create an hdf5 file from the loaded txt. It creates "name_prj"_STATHAB.hab, an hdf5 file with the
        info from stathab
        """
        self.load_ok = False

        # create an empty hdf5 file using all default prop.
        fname_no_path = self.name_prj + '_STATHAB' + '.hab'
        # path_hdf5 = self.find_path_hdf5_stat()
        fname = os.path.join(self.path_hdf5, fname_no_path)
        try:
            file = h5py.File(fname, 'w')
        except OSError:
            print('Error: Stathab file could not be loaded \n')
            return

        # create all datasets and group
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version
        file.attrs['path_prj'] = self.path_prj
        file.attrs['name_prj'] = self.name_prj
        file.attrs['riverint'] = self.riverint

        for r in range(0, len(self.name_reach)):
            try:
                filereach = file.create_group(self.name_reach[r])
            except ValueError:  # unable to create group
                new_name = 'unnamed_reach_' + str(r)
                # if two identical names
                if r > 0:
                    if np.any(self.name_reach[r] == self.name_reach[:r - 1]):
                        print('Warning: two reach with identical names.\n')
                        new_name = self.name_reach[r] + str(r + 1)
                else:
                    print('Warning: Reach name are not compatible with hdf5.\n')
                filereach = file.create_group(new_name)
            # save data for each reach
            try:
                qmesg = filereach.create_group('qlist')
                qmesg.create_dataset(fname_no_path, data=self.qlist[r])
                qwhg = filereach.create_group('qwh')
                qwhg.create_dataset(fname_no_path, data=self.qwh[r])
                if self.riverint == 0:
                    distg = filereach.create_group('disthmes')
                    distg.create_dataset(fname_no_path, data=self.disthmes[r])
                    qhmoyg = filereach.create_group('qhmoy')
                    qhmoyg.create_dataset(fname_no_path, data=self.qhmoy[r])
                    dist_grang = filereach.create_group('dist_gran')
                    dist_grang.create_dataset(fname_no_path, data=self.dist_gran[r])
                if self.riverint > 0:
                    data_iig = filereach.create_group('data_ii')
                    data_iig.create_dataset(fname_no_path, data=self.data_ii[r])
            except IndexError:
                print('Error: the length of the data is not compatible with the number of reach.\n')
                file.close()
                return

        allreach = file.create_group('Info_general')
        reachg = allreach.create_group('reach_name')
        reach_ascii = [n.encode("utf8", "ignore") for n in self.name_reach]  # unicode is not ok with hdf5
        reachg.create_dataset(fname_no_path, (len(reach_ascii), 1), data=reach_ascii)
        if self.riverint == 0:
            limhg = allreach.create_group('lim_h')
            limhg.create_dataset(fname_no_path, [len(self.lim_all[0])], data=self.lim_all[0])
            limvg = allreach.create_group('lim_v')
            limvg.create_dataset(fname_no_path, [len(self.lim_all[1])], data=self.lim_all[1])
            limgg = allreach.create_group('lim_g')
            limgg.create_dataset(fname_no_path, [len(self.lim_all[2])], data=self.lim_all[2])
        fishg = allreach.create_group('fish_chosen')
        fish_chosen_ascii = [n.encode("ascii", "ignore") for n in self.fish_chosen]  # unicode is not ok with hdf5
        fishg.create_dataset(fname_no_path, (len(self.fish_chosen), 1), data=fish_chosen_ascii)
        # close and save hdf5
        file.close()
        self.load_ok = True

    def save_xml_stathab(self, no_hdf5=False):
        """
        The function which saves the function related to stathab in the xml projexct files

        :param no_hdf5: If True, no hdf5 file was created (usually because Stathab crashed at some points)
        """

        fname_no_path = self.name_prj + '_STATHAB' + '.hab'
        if no_hdf5:
            fname_no_path = ''

        # write info in the xml project file
        if not os.path.isfile(os.path.join(self.path_prj, self.name_prj + '.habby')):
            print('Error: No project saved. Please create a project first in the Start tab.\n')
            return
        else:
            # change path_last_file_loaded, model_type (path)
            project_properties = load_project_properties(self.path_prj)  # load_project_properties
            project_properties["path_last_file_loaded"] = self.dir_name  # change value
            project_properties["STATHAB"]["path"] = fname_no_path  # change value
            save_project_properties(self.path_prj, project_properties)  # save_project_properties

    def stathab_calc(self):
        """
        The function to calculate stathab output.


        :return: the biological preferrence index (np.array of [reach, specices, nbclaq] size), surface or volume by class, etc.
        """
        self.load_ok = False
        # various info
        nbclaq = 50  # number of discharge point where the data have to be calculate
        nbclagg = 12  # number of empirical roughness class
        coeff_granu = np.array(
            [0.00001, 0.0001, 0.00028, 0.00125, 0.005, 0.012, 0.024, 0.048, 0.096, 0.192, 0.640, 1.536])  # WHY?
        # coeff = np.zeros((len(self.fish_chosen), coeff_all.shape[1]))


        nb_reach = len(self.name_reach)
        dict_pref_stahab = self.stahab_get_pref()

        nb_models = len(dict_pref_stahab['code_bio_model'])

        hv_hv = np.zeros((nb_reach, nb_models, nbclaq))
        wua_hv = np.zeros((nb_reach, nb_models, nbclaq))

        hv_h = np.zeros((nb_reach, nb_models, nbclaq))
        wua_h = np.zeros((nb_reach, nb_models, nbclaq))

        hv_v = np.zeros((nb_reach, nb_models, nbclaq))
        wua_v = np.zeros((nb_reach, nb_models, nbclaq))

        for r in range(0, nb_reach):

            # data for this reach
            try:
                qwh_r = self.qwh[r]
                qhmoy_r = self.qhmoy[r]
                h0 = qhmoy_r[1]
                disthmes_r = self.disthmes[r]
                qlist_r = self.qlist[r]
                dist_gran_r = np.array(self.dist_gran[r])
            except IndexError:
                print('Error: data not coherent with the number of reach \n')
                return
            hclass = np.zeros((len(self.lim_all[0]) - 1, nbclaq))
            vclass = np.zeros((len(self.lim_all[1]) - 1, nbclaq))
            # rclass = np.zeros((len(self.lim_all[2]) - 1, nbclaq))
            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            vmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))

            # # granulometry
            granulo_mean = np.sum(coeff_granu * dist_gran_r)
            self.granulo_mean_all.append(granulo_mean)
            # lim_g = self.lim_all[2]
            # lim_g[lim_g < 0] = 0
            # lim_g[lim_g > 11] = 11
            # dist_gs = np.zeros(len(lim_g) - 1, )
            # for cg in range(0, len(lim_g) - 1):
            #     lim_cg = [np.int(np.floor(lim_g[cg])), np.floor(lim_g[cg + 1])]
            #     dist_chosen = dist_gran_r[np.int(lim_cg[0]):np.int(lim_cg[1])]
            #     dist_gs[cg] = np.sum(dist_chosen)

            # get the distributions and power law ready
            [h_coeff, w_coeff] = self.power_law(qwh_r)
            sh0 = self.find_sh0_maxvrais(disthmes_r, h0)

            # check if discharge are coherent
            if min(qlist_r) < qwh_r[0, 0] / 10 or max(qlist_r) > qwh_r[-1, 0] * 5:
                print('Warning: Discharge range is far from measured discharge. Results might be unrealisitc. \n')

            # YLC
            h_born = (self.lim_all[0][0: -1] + self.lim_all[0][1:]) / 2
            v_born = (self.lim_all[1][0: -1] + self.lim_all[1][1:]) / 2
            pref_h = np.zeros((nb_models, len(h_born)))
            pref_v = np.zeros((nb_models, len(v_born)))
            for index_habmodel in range(nb_models):
                if dict_pref_stahab['bmono'][index_habmodel]:
                    if dict_pref_stahab['h_data'][index_habmodel]==[]:
                        pref_h[index_habmodel, :] = np.ones((len(h_born)))
                    else:
                        pref_h[index_habmodel, :] = np.interp(h_born, dict_pref_stahab['h_data'][index_habmodel],
                                                          dict_pref_stahab['h_pref_data'][index_habmodel])
                    if dict_pref_stahab['v_data'][index_habmodel] == []:
                        pref_v[index_habmodel, :] = np.ones((len(v_born)))
                    else:
                        pref_v[index_habmodel, :] = np.interp(v_born, dict_pref_stahab['v_data'][index_habmodel],
                                                          dict_pref_stahab['v_pref_data'][index_habmodel])
                else:
                    # TODO bivariate for stathab
                    pref_h[index_habmodel, :] = np.zeros((len(h_born)))
                    pref_v[index_habmodel, :] = np.zeros((len(v_born)))

            # result = np.zeros((nbclaq, 10))
            result_reach_q_hyd = np.zeros((nbclaq, 4))
            dist_hs_reach=[]
            dist_vs_reach = []
            # for all discharge
            for qind in range(0, nbclaq):
                lnqs = np.log(min(qlist_r)) + (qind + 0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs * h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs) / (hs * ws)
                dist_hs = self.dist_h(sh0, h0, self.lim_all[0], hs)
                dist_vs = self.dist_v(hs, granulo_mean, self.lim_all[1], vs)
                dist_hs_reach.append(dist_hs)
                dist_vs_reach.append(dist_vs)
                # multiply by width and surface
                v = ws * hs  # total volume
                vclass[:, qind] = ws * dist_vs * hs
                hclass[:, qind] = dist_hs * ws
                # rclass[:, qind] = dist_gs * ws
                qmod[qind] = qmod[qind][0]
                hmod[qind] = hs
                vmod[qind] = vs
                wmod[qind] = ws
                result_reach_q_hyd[qind, :] = [qmod[qind][0], ws, hs, vs]

                for index_habmodel in range(nb_models):
                    if dict_pref_stahab['bmono'][index_habmodel]:
                        # vh_v	spu_v	vh_h	spu_h	vh_hv	spu_hv
                        vh_h = np.sum(dist_hs * pref_h[index_habmodel, :])
                        spu_h = vh_h * ws * 100
                        vh_v = np.sum(dist_vs * pref_v[index_habmodel, :])
                        spu_v = vh_v * ws * 100
                        vh_hv = vh_h * vh_v
                        spu_hv = vh_hv * ws * 100
                        hv_hv[r, index_habmodel, qind] = vh_hv
                        wua_hv[r, index_habmodel, qind] = spu_hv
                        hv_h[r, index_habmodel, qind] = vh_h
                        wua_h[r, index_habmodel, qind] = spu_h
                        hv_v[r, index_habmodel, qind] = vh_v
                        wua_v[r, index_habmodel, qind] = spu_v
                    else:
                        # TODO bivariate for stathab
                        # TODO simplifier avec ce qui precede
                        hv_hv[r, index_habmodel, qind] = 0
                        wua_hv[r, index_habmodel, qind] = 0
                        hv_h[r, index_habmodel, qind] = 0
                        wua_h[r, index_habmodel, qind] = 0
                        hv_v[r, index_habmodel, qind] = 0
                        wua_v[r, index_habmodel, qind] = 0

            # ************************************************************************************************************
            # Verif Stathab
            # for index_habmodel in range(nb_models):
            #     nomfich = 'C:\\w\\S_' + self.name_reach[r] + '-' + dict_pref_stahab['code_bio_model'][
            #         index_habmodel] + '-' + dict_pref_stahab['stage'][index_habmodel] + '.txt'
            #     f_chk2 = open(nomfich, 'w')
            #     f_chk2.write(
            #         '\t'.join(['q', 'ws', 'hs', 'vs'] + ['vh_v', 'spu_v', 'vh_h', 'spu_h', 'vh_hv', 'spu_hv']) + '\n')
            #     f_chk2.close()
            #     f_chk2 = open(nomfich, 'a')
            #     np.savetxt(f_chk2,
            #                np.concatenate(
            #                    (np.concatenate((qmod, wmod, hmod, vmod), axis=1),
            #                     np.stack((hv_v[r, index_habmodel, :], wua_v[r, index_habmodel, :],
            #                               hv_h[r, index_habmodel, :], wua_h[r, index_habmodel, :],
            #                               hv_hv[r, index_habmodel, :],
            #                               wua_hv[r, index_habmodel, :]), axis=1)), axis=1), delimiter='\t')
            #     f_chk2.close()
            # ************************************************************************************************************

            # adding results by reach
            self.vclass_all.append(vclass)
            self.hclass_all.append(hclass)
            # self.rclass_all.append(rclass)
            self.h_all.append(hmod)
            self.v_all.append(vmod)
            self.w_all.append(wmod)
            self.q_all.append(qmod)
            self.dist_hs_all.append(dist_hs_reach)
            self.dist_vs_all.append(dist_vs_reach)

            # list of dict data for plotting
            self.data_list.append(dict(fish_list=[dict_pref_stahab['code_bio_model'][index_habmodel] + '-' + dict_pref_stahab['stage'][index_habmodel] for index_habmodel in range(nb_models)],
                                       q_all=qmod,
                                       h_all=hmod,
                                       w_all=wmod,
                                       vel_all=vmod,
                                       OSI=hv_hv[r],
                                       WUA=wua_hv[r],
                                        targ_q_all=[]))

        # the biological habitat value and wua for all reach, all species
        self.j_all = {'hv_hv': hv_hv, 'wua_hv': wua_hv, 'hv_h': hv_h, 'wua_h': wua_h, 'hv_v': hv_v, 'wua_v': wua_v}

        self.load_ok = True

    def stathab_steep_calc(self, path_bio, by_vol):
        """
        This function calculate the stathab outputs  for the univariate preference file in the case where the river is
        steep and in the tropical regions (usually the islands of Reunion and Guadeloupe).

        :param path_bio: the path to the preference file usually biology/stathab
        :param by_vol: If True the output is by volum (WUV instead of WUA) from the velcoity pref file
        :return: the WUA or WUV
        """
        # various info
        self.load_ok = False
        nb_reach = len(self.name_reach)
        dict_pref_stahab = self.stahab_get_pref()
        nb_models = len(dict_pref_stahab['code_bio_model'])
        nbclaq = 50  # number of discharge value where the data have to be calculated
        nbclass = 20  # number of height and velcoity class (do not change without changing dist_h_trop and _dist_v_trop)

        # TODO: loop on fishs
        if nb_models == 0:
            print('Error: No fish found \n')
            return

        hv_hv = np.zeros((nb_reach, nb_models, nbclaq))
        wua_hv = np.zeros((nb_reach, nb_models, nbclaq))
        hv_h = np.zeros((nb_reach, nb_models, nbclaq))
        wua_h = np.zeros((nb_reach, nb_models, nbclaq))
        hv_v = np.zeros((nb_reach, nb_models, nbclaq))
        wua_v = np.zeros((nb_reach, nb_models, nbclaq))

        # the biological preference index for all reach, all species
        # self.j_all = np.zeros((nb_reach, len(self.fish_chosen), nbclaq))

        # for each reach
        for r in range(0, nb_reach):

            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            vmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))
            try:
                qwh_r = self.qwh[r]
                qlist_r = self.qlist[r]
            except IndexError:
                print('Error: data not coherent with the number of reach \n')
                return

            # get the power law
            [h_coeff, w_coeff] = self.power_law(qwh_r)

            dist_hs_reach = []
            dist_vs_reach = []
            h_born_reach = []
            v_born_reach = []
            # for all discharge
            for qind in range(0, nbclaq):

                # discharge, height and velcoity data
                lnqs = np.log(min(qlist_r)) + (qind + 0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs * h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs) / (hs * ws)
                vmod[qind] = vs

                # get dist h
                [h_dist, h_born] = self.dist_h_trop(vs, hs, self.data_ii[r][0])
                # get dist v
                [v_dist, v_born] = self.dist_v_trop(vs, hs, self.data_ii[r][1], self.data_ii[r][2])
                dist_hs_reach.append(h_dist)
                dist_vs_reach.append(v_dist)
                h_born_reach.append(h_born)
                v_born_reach.append(v_born)

                # calculate J

                for index_habmodel in range(nb_models):
                    # to be checked
                    if dict_pref_stahab['bmono'][index_habmodel]:
                        if dict_pref_stahab['h_data'][index_habmodel] == []:
                            pref_h= np.ones((len(h_born)))
                        else:
                            pref_h = np.interp(h_born, dict_pref_stahab['h_data'][index_habmodel],
                                               dict_pref_stahab['h_pref_data'][index_habmodel])
                        if dict_pref_stahab['v_data'][index_habmodel] == []:
                            pref_v = np.ones((len(v_born)))
                        else:
                            pref_v = np.interp(v_born, dict_pref_stahab['v_data'][index_habmodel],
                                               dict_pref_stahab['v_pref_data'][index_habmodel])
                    else:
                        # TODO bivariate for StathabSteep
                        pref_h = np.zeros((len(h_born)))
                        pref_v = np.zeros((len(v_born)))
                    hv_dist = np.outer(h_dist, v_dist)
                    pref_hv = np.outer(pref_h, pref_v)
                    hv_hv[r, index_habmodel, qind] = np.sum(hv_dist * pref_hv)
                    wua_hv[r, index_habmodel, qind] = hv_hv[r, index_habmodel, qind] * ws * 100  # WUA/100m of river
                    hv_h[r, index_habmodel, qind] = np.sum(pref_h * h_dist)
                    hv_v[r, index_habmodel, qind] = np.sum(pref_v * v_dist)
                    wua_h[r, index_habmodel, qind] = hv_h[r, index_habmodel, qind] * ws * 100  # WUA/100m of river
                    wua_v[r, index_habmodel, qind] = hv_v[r, index_habmodel, qind] * ws * 100  # WUA/100m of river
            self.h_all.append(hmod)
            self.v_all.append(vmod)
            self.w_all.append(wmod)
            self.q_all.append(qmod)
            self.dist_hs_all.append(dist_hs_reach)
            self.dist_vs_all.append(dist_vs_reach)
            self.hborn_Stahabsteep.append(h_born_reach)
            self.vborn_Stahabsteep.append(v_born_reach)

            # list of dict data for plotting
            self.data_list.append(dict(fish_list=[dict_pref_stahab['code_bio_model'][index_habmodel] + '-' + dict_pref_stahab['stage'][index_habmodel] for index_habmodel in range(nb_models)],
                                       q_all=qmod,
                                       h_all=hmod,
                                       w_all=wmod,
                                       vel_all=vmod,
                                       OSI=hv_hv[r],
                                       WUA=wua_hv[r],
                                        targ_q_all=[]))

            # # ************************************************************************************************************
            # # Verif Stathab
            # for index_habmodel in range(nb_models):
            #     nomfich = 'C:\\w\\Ss_' + self.name_reach[r] + '-' + dict_pref_stahab['code_bio_model'][
            #         index_habmodel] + '-' + dict_pref_stahab['stage'][index_habmodel] + '.txt'
            #     f_chk2 = open(nomfich, 'w')
            #     f_chk2.write(
            #         '\t'.join(['q', 'ws', 'hs', 'vs'] + ['vh_v', 'spu_v', 'vh_h', 'spu_h', 'vh_hv', 'spu_hv']) + '\n')
            #     f_chk2.close()
            #     f_chk2 = open(nomfich, 'a')
            #     np.savetxt(f_chk2,
            #                np.concatenate(
            #                    (np.concatenate((qmod,wmod,hmod,vmod),axis=1), np.stack((hv_v[r, index_habmodel, :], wua_v[r, index_habmodel, :],
            #                                                   hv_h[r, index_habmodel, :], wua_h[r, index_habmodel, :],
            #                                                   hv_hv[r, index_habmodel, :],
            #                                                   wua_hv[r, index_habmodel, :]), axis=1)), axis=1),delimiter='\t')
            #     f_chk2.close()
            # ************************************************************************************************************

        ## the biological habitat value and wua for all reach, all species
        self.j_all = {'hv_hv': hv_hv, 'wua_hv': wua_hv, 'hv_h': hv_h, 'wua_h': wua_h, 'hv_v': hv_v, 'wua_v': wua_v}

        self.load_ok = True

    def stathab_trop_biv(self, path_bio):
        """
        This function calculate the stathab outputs  for the bivariate preference file in the case where the river is
        steep and in the tropical regions (usually the islands of Reunion and Guadeloupe).

        :param path_bio:
        :return:
        """

        # various info
        self.load_ok = False
        nb_reach = len(self.name_reach)
        nbclaq = 50  # number of discharge value where the data have to be calculated

        # get the preference info based on the files known
        code_fish = self.fish_chosen
        data_pref_all = load_pref_trop_biv(code_fish, path_bio)
        nb_fish = len(data_pref_all)
        if nb_fish == 0:
            print('Error: No fish found \n')
            return

        # the biological preference index for all reach, all species
        self.j_all = np.zeros((nb_reach, len(self.fish_chosen), nbclaq))

        # for each  reach
        for r in range(0, nb_reach):

            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            vmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))
            try:
                qwh_r = self.qwh[r]
                qlist_r = self.qlist[r]
            except IndexError:
                print('Error: data not coherent with the number of reach \n')
                return

            # get the power law
            [h_coeff, w_coeff] = self.power_law(qwh_r)

            # for each Q
            for qind in range(0, nbclaq):
                # discharge, height and velcoity data
                lnqs = np.log(min(qlist_r)) + (qind + 0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs * h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs) / (hs * ws)
                vmod[qind] = vs

                # get dist h
                [h_dist, h_born] = self.dist_h_trop(vs, hs, self.data_ii[r][0])
                # get dist v
                [v_dist, v_born] = self.dist_v_trop(vs, hs, self.data_ii[r][1], self.data_ii[r][2])

                # change to the vecloity and heigth distribtion because we are in bivariate
                # we nomalize the height distribution (between 0 and 1 ) and mulitply it with the velocity
                h_dist = h_dist / h_born
                h_dist = h_dist / sum(h_dist)  # normalisation to one, (like getting a mini-volum?)
                rep_num = len(h_dist)
                v_dist = np.repeat(v_dist, rep_num)  # [0,1,2] -> [0,0,1,1,2,2]
                h_vol = np.tile(h_dist, (1, rep_num))  # [0,1,2] -> [0,1,2,0,1,2]
                biv_dist = (h_vol * v_dist).T

                # calculate J
                for f in range(0, nb_fish):
                    # interpolate the preference file to the new point
                    data_pref = data_pref_all[f]
                    v_born2 = np.repeat(v_born, rep_num)
                    h_born2 = np.squeeze(np.tile(h_born, (1, rep_num)))
                    point_vh = np.array([v_born2, h_born2]).T
                    pref_here = interpolate.griddata(data_pref[:, :2], data_pref[:, 2], point_vh, method='linear')
                    hv_hv[r, f, qind] = np.sum(pref_here * biv_dist.T)
                    wua_hv[r, f, qind] = hv_hv[r, f, qind] * ws
                    self.j_all = {'hv_hv': hv_hv, 'wua_hv': wua_hv}
                self.h_all.append(hmod)
                self.v_all.append(vmod)
                self.w_all.append(wmod)
                self.q_all.append(qmod)

        self.load_ok = True

    def stahab_get_pref(self):
        hvum = HydraulicVariableUnitManagement()
        # each animal model
        dict_pref_stahab = {'code_bio_model': [], 'stage': [], 'bmono': [], 'h_data': [], 'v_data': [],
                            'h_pref_data': [], 'v_pref_data': [], 'hv_pref_data': []}
        project_properties = load_project_properties(self.path_prj)  # load_project_properties
        for hab_string_var in self.fish_chosen:
            # get gui informations
            stage = hab_string_var.split(" - ")[-2]
            code_bio_model = hab_string_var.split(" - ")[-1]
            index_fish = user_preferences.biological_models_dict["code_biological_model"].index(code_bio_model)
            # get the preference info based on the files known
            information_model_dict = read_pref(user_preferences.biological_models_dict["path_xml"][index_fish])
            stage_index = information_model_dict["stage_and_size"].index(stage)
            hab_var = information_model_dict["hab_variable_list"][stage_index]
            dict_pref_stahab['code_bio_model'].append(code_bio_model)
            dict_pref_stahab['stage'].append(stage)
            hydraulic_type_available=information_model_dict["hydraulic_type_available"][stage_index]
            # copy_or_not_user_pref_curve_to_input_folder
            copy_or_not_user_pref_curve_to_input_folder(hab_var, project_properties)
            # get data
            if hab_var.model_type == "univariate suitability index curves":
                dict_pref_stahab['bmono'].append(True)
                if ("HV"  in hydraulic_type_available) or ("H"  in hydraulic_type_available):
                    dict_pref_stahab['h_data'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.h.name)].data[0])
                    dict_pref_stahab['h_pref_data'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.h.name)].data[1])
                else:
                    dict_pref_stahab['h_data'].append([])
                    dict_pref_stahab['h_pref_data'].append([])
                if ("HV" in hydraulic_type_available) or ("V" in hydraulic_type_available) :
                    dict_pref_stahab['v_data'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.v.name)].data[0])
                    dict_pref_stahab['v_pref_data'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.v.name)].data[1])
                else:
                    dict_pref_stahab['v_data'].append([])
                    dict_pref_stahab['v_pref_data'].append([])
                dict_pref_stahab['hv_pref_data'].append([])
            if hab_var.model_type == "bivariate suitability index models":
                dict_pref_stahab['bmono'].append(False)
                dict_pref_stahab['h_data'].append(
                    hab_var.variable_list[hab_var.variable_list.names().index(hvum.h.name)].data)
                dict_pref_stahab['v_data'].append(
                    hab_var.variable_list[hab_var.variable_list.names().index(hvum.v.name)].data)
                dict_pref_stahab['hv_pref_data'].append(hab_var.osi)
                dict_pref_stahab['h_pref_data'].append([])
                dict_pref_stahab['v_pref_data'].append([])
        return dict_pref_stahab

    def power_law(self, qwh_r):
        """
        The function to calculate power law for discharge and width
        ln(h) = a1 + a2 ln(Q)=h_coeff[1] +h_coeff[0]*ln(Q)
        ln(w) = w_coeff[1] +w_coeff[0]*ln(Q)

        :param qwh_r: an array where each line in one observatino of Q, width and height
        :return: the coeff of the regression
        """
        # input
        q = qwh_r[:, 0]
        h = qwh_r[:, 1]
        w = qwh_r[:, 2]

        # fit power-law
        h_coeff = np.polyfit(np.log(q), np.log(h), 1)  # h_coeff[1] + ln(Q) *h_coeff[0]
        w_coeff = np.polyfit(np.log(q), np.log(w), 1)

        return h_coeff, w_coeff

    def find_sh0(self, disthmesr, h0):
        """
        the function to find sh0, using a minimzation technique. Not used because the output was string.
        Possibly an error on the bornes? We remplaced this function by the function find_sh0_maxvrais().

        :param disthmesr: the measured distribution of height
        :param h0: the measured mean height
        :return: the optimized sh0
        """

        bornhmes = np.arange(0,
                             len(disthmesr) + 1) * 5 * h0  # in c code, bornes are 1:n, so if we divide by h -> 1:n * h
        # optimization by non-linear least square
        # if start value equal or above one, the optimization fails.
        [sh0_opt, pcov] = optimize.curve_fit(lambda h, sh0: self.dist_h(sh0, h0, bornhmes, h), h0, disthmesr, p0=0.5)
        return sh0_opt

    def find_sh0_maxvrais(self, disthmesr, h0):
        """
        the function to find sh0, using the maximum of vraisemblance.
        This function aims at reproducing the results from the c++ code. Hence, no use of scipy

        :param disthmesr: the measured distribution of height
        :param h0: the measured mean height
        :return: the optimized sh0
        """
        nbclaemp = 20
        vraismax = -np.inf
        clmax = nbclaemp - 1
        sh0 = 0
        for p in range(0, 101):
            sh = p / 100
            if sh == 0:
                sh += 0.00001  # no log(0)
            if sh == 1:
                sh -= 0.00001
            vrais = disthmesr[0] * np.log(
                sh * (1 - np.exp(-(1. / 4.))) + (1 - sh) * (stats.norm.cdf(((1. / 4.) - 1) / 0.419)))
            vrais += disthmesr[clmax] * np.log(sh * np.exp(-(clmax / 4.)) +
                                               (1 - sh) * (1 - stats.norm.cdf(((clmax / 4.) - 1) / 0.419)))
            for cla in range(1, clmax):
                vrais += disthmesr[cla] * np.log(sh * (np.exp(-cla / 4.) - np.exp(-(cla + 1) / 4.)) +
                                                 (1 - sh) * (stats.norm.cdf(((cla + 1) / 4. - 1) / 0.419) -
                                                             stats.norm.cdf((cla / 4. - 1) / 0.419)))
            if vrais > vraismax:
                vraismax = vrais
                sh0 = p / 100
        return sh0

    def dist_h(self, sh0, h0, bornh, h):
        """
        The calculation of height distribution  acrros the river
        The distribution is a mix of an exponential and guassian.

        :param sh0: the sh of the original data
               sh is the parameter of the distribution, gives the relative importance of ganussian and exp distrbution
        :param h: the mean height data
        :param h0: the mean height
        :param bornh: the limits of each class of height
        :return: disth the distribution of heights across the river for the mean height h.

        """
        # sh
        # sh0 = 0.48
        sh = sh0 - 0.7 * np.log(h / h0)
        if sh > 1:
            sh = 1.
        if sh < 0:
            sh = 0.
        # prep
        nbclass = len(bornh) - 1
        disth = np.zeros((nbclass,))
        # all class and calcul
        for cl in range(0, nbclass):
            a = bornh[cl] / h
            b = bornh[cl + 1] / h
            c = a
            # why?
            if a <= 0 and cl == 0:
                c = -np.inf
                a = 0
            # based on Lamouroux, 1998 (Depth probability distribution in stream reaches)
            disth[cl] = sh * (np.exp(-a) - np.exp(-b)) + \
                        (1 - sh) * (stats.norm.cdf((b - 1) / 0.419) - stats.norm.cdf((c - 1) / 0.419))
        return disth

    def dengauss(self, x):
        """
        gaussian density, used only for debugging purposes.
        This is not used in Habby, but can be useful if scipy is not available (remplace all stat.norm.cdf with
        dengauss)

        :param x: the parameter of the gaussian
        :return: the gaussian density
        """
        n = 0
        if x > 3.72:
            return 1
        if x < -3.72:
            return 0.
        if x < 0:
            n = -1
            x = -x
        s3 = x
        t1 = x
        k3 = 0
        while True:  # do loop in python?
            k3 += 1
            t2 = (-1) * t1 * x * x / (2 * k3)
            t1 = t2
            t2 = t2 / (2 * k3 + 1)
            s3 += t2
            if abs(t2) < 0.000001:
                break
        res = 0.5 + 0.398942 * s3
        if n == -1:
            res = 1 - res
        return res

    def dist_v(self, h, d, bornv, v):
        """
        The calculation of velocity distribution across the river
        The distribution is a mix of an exponential and guassian.

        :param h: the height which is related to the mean velocity v
        :param d: granulo moyenne
        :param bornv: the born of the velocity
        :param v: the mean velocity
        :return: the distribution of velocity across the river
        """
        # sv
        fr = v / np.sqrt(9.81 * h)
        relrough = d / h
        sv = -0.275 - 0.237 * np.log(fr) + 0.274 * relrough
        if sv < 0:
            sv = 0
        if sv > 1:
            sv = 1
        # prep
        nbclass = len(bornv) - 1
        distv = np.zeros((nbclass,))
        # all class and calcul
        for cl in range(0, nbclass):
            a = bornv[cl] / v
            b = bornv[cl + 1] / v
            c = a
            if a <= 0 and cl == 0:
                c = -np.inf
                a = 0
            # based on Lamouroux, 1995 (predicting velocity frequency distributions)
            # dist = f1(exp) + f2(gaussian) + f3(gaussian)
            distv[cl] = sv * 0.642 * (np.exp(-a / 0.193) - np.exp(-b / 0.193)) \
                        + sv * 0.358 * (stats.norm.cdf((b - 2.44) / 1.223) - stats.norm.cdf((c - 2.44) / 1.223)) \
                        + (1 - sv) * (stats.norm.cdf((b - 1) / 0.611) - stats.norm.cdf((c - 1) / 0.611))
        return distv

    def dist_h_trop(self, v, h, mean_slope):
        """
        This function calulate the height distribution for steep tropical stream based on the R code from
        Girard et al. (stathab_hyd_steep). The frequency distribution is based on empirical data which
        is given in the list of numbers in the codes below. The final frequency distribution is in the form:
        t xf1 + (1-t) x f where t is a function of the froude number and the mean slope of the station.

        The height limits are considered constant here (constrarily to dist_h where they are given in the parameter
        bornh).

        :param v: the velcoity for this discharge
        :param h: the height for this discharge
        :param mean_slope: the mean slope of the station (usally in the data_ii[0] variable)
        :return: the distribution of height

        """

        # general info
        g = 9.80665  # gravitation constant
        fr = v / np.sqrt(g * h)

        # empirical freq. distributions
        fd_h = [0.221545010, 0.193846678, 0.117355060, 0.110029404, 0.074083455, 0.071369872, 0.054854534,
                0.025952644, 0.024479842, 0.021200121, 0.015840696, 0.018349236, 0.010369520, 0.006917000,
                0.005550880, 0.003432236, 0.001366120, 0.003366120, 0.006118644, 0.013972928]
        fc_h = [0.10786195, 0.12074410, 0.14866942, 0.13869359, 0.16721162, 0.11451288, 0.08924672, 0.05603628,
                0.02442850, 0.02209880, 0.01049615, 0.00000000, 0.00000000, 0.00000000, 0.00000000, 0.00000000,
                0.00000000, 0.00000000, 0.00000000, 0.00000000]

        # get the mixiing parameters
        tmix_lien = -2.775 - 0.838 * np.log(fr) + 0.087 * mean_slope
        tmix = np.exp(tmix_lien) / (1 + np.exp(tmix_lien))

        # height disitrbution
        h_dist = np.zeros((len(fd_h),))
        for i in range(0, len(fd_h)):
            h_dist[i] = tmix * fd_h[i] + (1 - tmix) * fc_h[i]

        h_born = np.arange(0.125, 5, 0.25) * h

        return h_dist, h_born

    def dist_v_trop(self, v, h, h_waterfall, length_stat):
        """
        This function calulate the velocity distribution for steep tropical stream based on the R code from
        Girard et al. (stathab_hyd_steep). The frequency distribution is based on empirical data which
        is given in the list of numbers in the codes below. The final frequency distribution is in the form:
        t x f1 + (1-t) x f where t depends on the ratio of the length of station and the height of the waterfall.

        :param v: the velcoity for this discharge
        :param h: the height for this discharge
        :param h_waterfall: the height of the waterfall
        :param length_stat: the length of the station
        :return: the distribution of velocity

        """

        # prep
        g = 9.80665  # gravitation constant
        ichu = h_waterfall / length_stat
        fr = v / np.sqrt(g * h)

        # empirical freq. distributions
        fd_v = [0.367737038, 0.171825373, 0.070912537, 0.049956434, 0.042982367, 0.037409374, 0.032246954,
                0.025315107, 0.019778008, 0.018990529, 0.011506684, 0.018655122, 0.016300231, 0.012822439,
                0.012222620, 0.006738370, 0.007714692, 0.003348316, 0.006082559, 0.001749545, 0.065705701]
        fc_v = [0.113325663, 0.167094505, 0.104591869, 0.091699585, 0.076272551, 0.076247281, 0.075009649,
                0.066482669, 0.057792617, 0.058358048, 0.036947598, 0.025192247, 0.024107747, 0.014137293,
                0.003300867, 0.006857482, 0.002582328, 0.000000000, 0.000000000, 0.000000000, 0.000000000]

        # get the mixing paramter
        if np.isnan(ichu):
            smix_lien = -3.163 - 1.344 * np.log(fr)
        else:
            smix_lien = -4.53 - 1.58 * np.log(fr) + 0.159 * ichu
        smix = np.exp(smix_lien) / (1 + np.exp(smix_lien))

        # velocity distribution
        v_dist = np.zeros((len(fd_v),))
        for i in range(0, len(fd_v)):
            v_dist[i] = smix * fd_v[i] + (1 - smix) * fc_v[i]

        v_born = np.arange(-0.125, 5, 0.25) * v

        # change the length as needed
        v_born = v_born[1:]
        v_dist[1] = v_dist[0] + v_dist[1]
        v_dist = v_dist[1:]

        return v_dist, v_born

    def savefig_stahab(self, ):
        """
        A function to save the results in text and the figure. If the argument show_class is True,
        it shows an extra figure with the size of the different height, granulo, and velocity classes. The optional
        figure only works when stathab1 for temperate river is used.

        """
        # figure option
        self.project_properties = load_project_properties(self.path_prj)
        if len(self.q_all) < len(self.name_reach):
            print('Error: Could not find discharge data. Figure not plotted. \n')
            return

        # plot
        for r in range(0, len(self.name_reach)):
            self.data_list[r]["name_reach"] = self.name_reach[r]
            progress_value = Value("d", 0)
            plot_stat_data(progress_value, self.data_list[r],
                           "Stathab_steep" if self.riverint == 1 else "Stathab",
                           self.project_properties)

    def savetxt_stathab(self):
        """
        A function to save the stathab result in .txt form
        """
        dict_pref_stahab = self.stahab_get_pref()
        nb_models = len(dict_pref_stahab['code_bio_model'])
        mode_name = "Stathab_steep" if self.riverint == 1 else "Stathab"
        z0namefile = os.path.join(self.path_txt,'z'+ mode_name + '.txt')
        z0header_txt = '\t'.join(['site', 'esp', 'Q', 'W', 'H', 'V', 'vh_v', 'spu_v', 'vh_h', 'spu_h', 'vh_hv', 'spu_hv']) + '\n' + '\t'.join([' ', ' ','[m3/s]', '[m]', '[m]', '[m/s]','[-]', '[m2/100m]','[-]', '[m2/100m]','[-]', '[m2/100m]'])

        # save in txt hydraulic information and habitat results for each reach X biological models selected
        for r in range(0, len(self.name_reach)):
            qmod = self.q_all[r]
            hmod = self.h_all[r]
            vmod = self.v_all[r]
            wmod = self.w_all[r]
            header0_list = ['Q', 'W', 'H', 'V']
            header1_list = ['[m3/s]', '[m]', '[m]', '[m/s]']
            jj0 = np.concatenate((qmod, wmod, hmod, vmod), axis=1)
            jj = np.copy(jj0)
            z0a = np.array([self.name_reach[r] for _ in range(len(qmod))], dtype=object)
            for index_habmodel in range(nb_models):
                codefish = dict_pref_stahab['code_bio_model'][index_habmodel] + '-' + dict_pref_stahab['stage'][
                    index_habmodel]
                header0_list.extend(['hv_hv-' + codefish, 'wua_hv-' + codefish])
                header1_list.extend(['[-]', '[m2/100m]'])
                jj = np.concatenate((jj, np.stack(
                    (self.j_all['hv_hv'][r, index_habmodel, :], self.j_all['wua_hv'][r, index_habmodel, :]),
                    axis=1)), axis=1)
                z0b=np.array([codefish for _ in range(len(qmod))], dtype=object)
                z0c = np.concatenate((np.column_stack((z0a, z0b)), jj0, np.stack(
                    (self.j_all['hv_v'][r, index_habmodel, :], self.j_all['wua_v'][r, index_habmodel, :],
                     self.j_all['hv_h'][r, index_habmodel, :], self.j_all['wua_h'][r, index_habmodel, :],
                     self.j_all['hv_hv'][r, index_habmodel, :], self.j_all['wua_hv'][r, index_habmodel, :]),
                    axis=1)), axis=1)
                if r == 0 and index_habmodel==0:
                    z0jj = np.copy(z0c)
                else:
                    z0jj = np.concatenate((z0jj, z0c), axis=0)
            namefile = os.path.join(self.path_txt, mode_name + '_' + self.name_reach[r] + '.txt')
            header_txt = '\t'.join(header0_list) + '\n' + '\t'.join(header1_list)
            np.savetxt(namefile, jj, delimiter='\t', header=header_txt)

        np.savetxt(z0namefile, z0jj, delimiter='\t', header=z0header_txt, fmt='%s')

        # save in txt stathab calculations of depth and  velocity distribution for each reach X discharge Q
        z1namefile = os.path.join(self.path_txt, 'z' + mode_name + '_dist_h.txt')
        z1header_txt = '\t'.join(['site', 'Q', 'frequency', 'Hmin', 'Hmax']) + '\n' + '\t'.join(
            [' ', '[m3/s]', ' ', '[m]', '[m]'])
        z2namefile = os.path.join(self.path_txt, 'z' + mode_name + '_dist_v.txt')
        z2header_txt = '\t'.join(['site', 'Q', 'frequency', 'Vmin', 'Vmax']) + '\n' + '\t'.join(
            [' ', '[m3/s]', ' ', '[m/s]', '[m/s]'])
        if mode_name == "Stathab":
            nb_h = len(self.lim_all[0]) - 1
            nb_v = len(self.lim_all[1]) - 1
        elif mode_name == "Stathab_steep":
            nb_h = len(self.hborn_Stahabsteep[0][0])
            nb_v = len(self.vborn_Stahabsteep[0][0])
        for r in range(0, len(self.name_reach)):
            qmod = self.q_all[r]
            for iq in range(len(qmod)):
                z1r = np.array([self.name_reach[r] for _ in range(nb_h)], dtype=object)
                z2r = np.array([self.name_reach[r] for _ in range(nb_v)], dtype=object)
                z1q = np.array([qmod[iq] for _ in range(nb_h)])
                z2q = np.array([qmod[iq] for _ in range(nb_v)])
                if mode_name == "Stathab":
                    z1all = np.column_stack(
                        (z1r, z1q, self.dist_hs_all[r][iq], self.lim_all[0][0: -1], self.lim_all[0][1:]))
                    z2all = np.column_stack(
                        (z2r, z2q, self.dist_vs_all[r][iq], self.lim_all[1][0: -1], self.lim_all[1][1:]))
                elif mode_name == "Stathab_steep":
                    deltah,deltav=self.hborn_Stahabsteep[r][iq][0],self.vborn_Stahabsteep[r][iq][0]
                    z1all = np.column_stack(
                        (z1r, z1q, self.dist_hs_all[r][iq], self.hborn_Stahabsteep[r][iq]-deltah, self.hborn_Stahabsteep[r][iq]+deltah))
                    z2all = np.column_stack(
                        (z2r, z2q, self.dist_vs_all[r][iq], self.vborn_Stahabsteep[r][iq]-deltav, self.vborn_Stahabsteep[r][iq]+deltav))
                if r == 0 and iq == 0:
                    z1jj, z2jj = np.copy(z1all), np.copy(z2all)
                else:
                    z1jj, z2jj = np.concatenate((z1jj, z1all), axis=0), np.concatenate((z2jj, z2all), axis=0)
        np.savetxt(z1namefile, z1jj, delimiter='\t', header=z1header_txt, fmt='%s')
        np.savetxt(z2namefile, z2jj, delimiter='\t', header=z2header_txt, fmt='%s')

    def find_path_hdf5_stat(self):
        """
        A function to find the path where to save the hdf5 file. Careful a simialar one is in sub_and_merge_GUI.py
        and in estimhab_GUI. By default,
        path_hdf5 is in the project folder in the folder 'hdf5'.
        """

        path_hdf5 = 'no_path'

        filename_path_pro = os.path.join(self.path_prj, self.name_prj + '.habby')
        if os.path.isfile(filename_path_pro):
            parser = ET.XMLParser(remove_blank_text=True)
            doc = ET.parse(filename_path_pro, parser)
            root = doc.getroot()
            child = root.find(".//path_hdf5")
            if child is None:
                path_hdf5 = os.path.join(self.path_prj, "hdf5")
            else:
                path_hdf5 = os.path.join(self.path_prj, child.text)
        else:
            print('Error: Project file is not found')

        return path_hdf5

    def test_stathab(self, path_ori):
        """
        A short function to test part of the outputs of stathab in temperate rivers against the C++ code,
        It is not used in Habby but it is practical to debug.

        :param path_ori: the path to the files from stathab based on the c++ code
        """

        # stathab.txt
        filename = os.path.join(path_ori, 'stathab.txt')
        if os.path.isfile(filename):
            with open(filename, 'rt') as f:
                data = f.read()
        else:
            print('Error: Stathab.txt was not found.\n')
            return -99
        # granulo_mean
        exp_reg1 = 'average\ssubstrate\ssize\s([\d.,]+)\s*'
        mean_sub_ori = re.findall(exp_reg1, data)
        for r in range(0, len(mean_sub_ori)):
            mean_sub_ori_fl = np.float(mean_sub_ori[r])
            if np.abs(mean_sub_ori_fl - self.granulo_mean_all[r]) < 0.0001:
                print('substrate size: ok')
            else:
                print(mean_sub_ori[r])
                print(self.granulo_mean_all[r])

        # rivrrd.txt
        filename = os.path.join(path_ori, self.name_reach[0] + 'rrd.txt')
        vol_all_orr = np.loadtxt(filename)
        q_orr = np.exp(vol_all_orr[:, 0])
        vclass = self.vclass_all[0]
        hclass = self.hclass_all[0]
        rclass = self.rclass_all[0]
        v = self.h_all[0] * self.w_all[0]

        plt.figure()
        plt.subplot(221)
        plt.title('Volume total')
        plt.plot(q_orr, 1 * vol_all_orr[:, 3] * vol_all_orr[:, 2], '*')
        plt.plot(q_orr, v)
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Volume for 1m reach [m3]')
        plt.legend(('C++ Code', 'new python code'), loc='upper left')
        plt.subplot(222)
        plt.title('Surface by class for the granulometry')
        for g in range(0, len(rclass)):
            plt.plot(q_orr, vol_all_orr[:, 13 + g], '*')
            plt.plot(q_orr, rclass[g], '-')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Surface by Class [m2]')
        plt.subplot(223)
        plt.title('Surface by class for the height')
        for g in range(0, len(hclass)):
            plt.plot(q_orr, vol_all_orr[:, 9 + g], '*')
            plt.plot(q_orr, hclass[g, :], '-')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Surface by Class [m2]')
        plt.subplot(224)
        plt.title('Volume by class for the velocity')
        for g in range(0, len(vclass)):
            plt.plot(q_orr, vol_all_orr[:, 4 + g], '*')
            plt.plot(q_orr, vclass[g], '-')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Volume by Class [m3]')

        # rivrre.txt
        filename = os.path.join(path_ori, self.name_reach[0] + 'rre.txt')
        j_orr = np.loadtxt(filename)
        j = np.squeeze(self.j_all[0, :, :])
        nb_spe = j_orr.shape[1]
        plt.figure()
        for e in range(0, nb_spe):
            plt.plot(q_orr, j_orr[:, e], '*', label=self.fish_chosen[e] + '(C++)')
            plt.plot(q_orr, j[e, :], '-', label=self.fish_chosen[e] + '(Python)')
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('J')
        plt.title('Suitability index J - STATHAB')
        lgd = plt.legend(bbox_to_anchor=(1, 1), loc='upper right', ncol=1)

        plt.show()

    def test_stathab_trop_biv(self, path_ori):
        """
        A short function to test part of the outputs of the stathab tropical rivers against the R code
        in the bivariate mode. It is not used in Habby but it is practical to debug. Stathab_trop+biv should be
        executed before. For the moment only the fish SIC is tested.

        :param path_ori: the path to the output files from stathab based on the R code

        """

        # load the R output data
        filename = os.path.join(path_ori, 'SIC_ind-vh.csv')
        data_r = np.genfromtxt(filename, skip_header=1, delimiter=";")
        q_r = data_r[:, 2]
        vpu = data_r[:, 6]

        # compare result
        plt.figure()
        plt.title('Stathab - Tropical bivariate - SIC')
        plt.plot(self.q_all[0], self.j_all[0, 0, :], '-')
        plt.plot(q_r, vpu, 'x')
        plt.xlabel('Q [m3/sec]')
        plt.ylabel('VPU')
        plt.legend(('Python Code', 'R Code'), loc=2)
        plt.grid('on')
        plt.show()

    def test_stathab_trop_uni(self, path_ori, by_vel=True):
        """
        A short function to test part of the outputs of the stathab tropical rivers against the R code
        in the univariate mode. It is not used in Habby but it is practical to debug. Stathab_trop_uni should be
        executed before. For the moment only the fish SIC is tested.

        :param path_ori: the path to the output files from stathab based on the R code
        :param by_vel: If True, the velcoity-based vpu is used. Otherise, it is height-based wua

        """

        # load the R output data
        if by_vel:
            filename = os.path.join(path_ori, 'SIC_ind-v.csv')
        else:
            filename = os.path.join(path_ori, 'SIC_ind-h.csv')
        data_r = np.genfromtxt(filename, skip_header=1, delimiter=";")
        q_r = data_r[:, 2]
        vpu = data_r[:, 6]

        # compare result
        plt.figure()
        if by_vel:
            plt.title('Stathab - Tropical univariate, based on velocity preference - SIC ')
            plt.ylabel('VPU')
        else:
            plt.title('Stathab - Tropical univariate, based on height preference - SIC ')
            plt.ylabel('WUA')
        plt.plot(self.q_all[0], self.j_all[0, 0, :], '-')
        plt.plot(q_r, vpu, 'x')
        plt.xlabel('Q [m3/sec]')

        plt.legend(('Python Code', 'R Code'), loc=2)
        plt.grid('on')
        plt.show()


def load_float_stathab(filename, check_neg):
    """
    A function to load float with extra checks

    :param filename: the file to load with the path
    :param check_neg: if true negative value are not allowed in the data
    :return: data if ok, -99 if failed
    """

    myfloatdata = [-99]
    still_val_err = True  # if False at the end, the file could be loaded
    if os.path.isfile(filename):
        try:
            myfloatdata = np.loadtxt(filename)
            still_val_err = False
        except ValueError:
            pass
        try:  # because some people add an header to the files in the csv
            myfloatdata = np.loadtxt(filename, skiprows=1, delimiter=";")
            still_val_err = False
        except ValueError:
            pass
        try:  # because there are csv files without header
            myfloatdata = np.loadtxt(filename, delimiter=';')
            still_val_err = False
        except ValueError:
            pass
        if still_val_err:
            print('Error: The file called ' + filename + ' could not be read.(2)\n')
            return [-99]
    else:  # when loading file, python is always case-sensitive because Windows is.
        # so let's insist on this.
        path_here = os.path.dirname(filename)
        all_file = os.listdir(path_here)
        file_found = False
        for f in range(0, len(all_file)):
            if os.path.basename(filename.lower()) == all_file[f].lower():
                file_found = True
                filename = os.path.join(path_here, all_file[f])
                try:
                    myfloatdata = np.loadtxt(filename)
                    still_val_err = False
                except ValueError:
                    pass
                try:  # because some people add an header to the files in the csv
                    myfloatdata = np.loadtxt(filename, skiprows=1, delimiter=";")
                    still_val_err = False
                except ValueError:
                    pass
                try:  # because ther are csv files without header
                    myfloatdata = np.loadtxt(filename, delimiter=';')
                    still_val_err = False
                except ValueError:
                    pass
                if still_val_err:
                    print('Error: The file called ' + filename + ' could not be read.(2)\n')
                    return [-99]
        if not file_found:
            print('Error: The file called ' + filename + ' was not found.\n')
            return [-99]

    if check_neg:
        if np.sum(np.sign(myfloatdata)) < 0:  # if there is negative value
            print('Error: Negative values found in ' + filename + '.\n')
            return [-99]
    return myfloatdata


def load_pref(filepref, path):
    """
    The function loads the different pref coeffficient contained in filepref, for the temperate river from Stathab

    :param filepref: the name of the file (usually Pref.txt)
    :param path: the path to this file
    :return: the name of the fish, a np.array with the differen coeff
    """
    filename_path = os.path.join(path, filepref)
    if os.path.isfile(filename_path):
        with open(filename_path, 'rt') as f:
            data = f.read()
    else:
        print('Error:  The file containing biological models was not found (Pref.txt).\n')
        return [-99], [-99]
    if not data:
        print('Error:  The file containing biological models could not be read (Pref.txt).\n')
        return [-99], [-99]
    # get data line by line
    data = data.split('\n')

    # read the data and pass to float
    name_fish = []
    coeff_all = []
    for l in range(0, len(data)):
        # ignore empty line
        if data[l]:
            data_l = data[l].split()
            name_fish.append(data_l[0])
            coeff_l = list(map(float, data_l[1:]))
            coeff_all.append(coeff_l)
    coeff_all = np.array(coeff_all)

    return name_fish, coeff_all


def load_pref_trop_uni(code_fish, path):
    """
    This function loads the preference files for the univariate data. The file with the univariate data should be in the
    form of xuni-h_XXX where XX is the fish code and x is whatever string. The assumption is that the filename for
    velocity is very similar to the filename for height. In more detail that the string uni-h is changed to uni-v in
    the filename. Otherwise, the file are csv file with two columns: First is velocity or height,
    the second is the preference data.

    :param code_fish: the code for the fish name in three letters (such as ASC)
    :param path: the path to files
    :return: the height data and velcoity data (h, pref) and (v,pref)
    """

    datah_all = []
    datav_all = []

    # get all possible file
    all_files = src.dev_tools_mod.get_all_filename(path, '.csv')

    # get the name of univariate height files
    filenamesh = []
    for fi in code_fish:
        for file in all_files:
            if 'uni-h_' + fi in file:
                filenamesh.append(file)

    # load the data
    for fh in filenamesh:
        # get filename with the path
        fv = fh.replace('uni-h', 'uni-v')
        fileh = os.path.join(path, fh)
        filev = os.path.join(path, fv)

        # load file
        if not os.path.isfile(fileh) or not os.path.isfile(filev):
            print('Warning: One preference file was not found.\n')
        else:
            try:
                datah = np.loadtxt(fileh, skiprows=1, delimiter=';')
                datav = np.loadtxt(filev, skiprows=1, delimiter=';')
                datah_all.append(datah)
                datav_all.append(datav)
            except ValueError:
                print('Warning: One preference file could not be read.\n')

    return datah_all, datav_all


def load_pref_trop_biv(code_fish, path):
    """
    This function loads the bivariate preference files for tropical rivers. The name of the file must be in the form
    of xbiv_XXX.csv where XXX is the three-letters fish code and x is whatever string.

    :param code_fish: the code for the fish name in three letters (such as ASC)
    :param path: the path to files
    :return: the bivariate preferences
    """
    data_all = []

    # get all possible files
    all_files = src.dev_tools_mod.get_all_filename(path, '.csv')

    # get the name of univariate height files
    filenames = []
    for fi in code_fish:
        for file in all_files:
            if 'biv_' + fi in file:
                filenames.append(file)

    # load the data
    for f in filenames:
        # get filename with the path
        file = os.path.join(path, f)
        if not os.path.isfile(file):
            print('Warning: One preference file was not found.\n')
        else:
            try:
                data = np.loadtxt(file, skiprows=1, delimiter=';')
                data_all.append(data)
            except ValueError:
                print('Warning: One preference file could not be read.\n')

    return data_all


def load_namereach(path):
    """
    A function to only load the reach names (useful for the GUI). The extension must be .txt or .csv

    :param path : the path to the file listriv.txt or listriv.csv
    :param name_file_reach: In case the file name is not listriv
    :return: the list of reach name
    """
    # find the reaches
    # filename = os.path.join(path, name_file_reach + '.txt')
    # filename2 = os.path.join(path, name_file_reach + '.csv')
    # if os.path.isfile(filename):
    #     with open(filename, 'rt') as f:
    #         data = f.read()
    # elif os.path.isfile(filename2):
    #     with open(filename2, 'rt') as f:
    #         data = f.read()
    # else:
    #     print('Error:  The file containing the names of the reaches was not found (listriv).\n')
    #     print(filename2)
    #     return [-99]
    # if not data:
    #     print('Error:  The file containing the names of the reaches could not be read (listriv.txt).\n')
    #     return [-99]
    # # get reach name line by line
    # name_reach = data.split('\n')  # in case there is a space in the names of the reaches
    # # in case we have an empty line between reaches
    # name_reach = [x for x in name_reach if x]

    name_reach = []
    if path !='':
        for file in os.listdir(path):
            if file.endswith('csv'):
                if 'deb.csv'  in file.lower() or 'qhw.csv' in file.lower():
                    reach=file.lower()[:-7]
                    if not(reach in name_reach):
                        name_reach.append(reach)

    return name_reach


def main():
    """
    used to test this module.
    """

    # test temperate stathab

    # path = 'D:\Diane_work\model_stat\input_test'
    # path_ori = 'D:\Diane_work\model_stat\stathab_t(1)'
    # #path_ori = r'D:\Diane_work\model_stat\stathab_t(1)\mob_test'
    # end_file_reach = ['deb.txt', 'qhw.txt', 'gra.txt', 'dis.txt']
    # name_file_allreach = ['bornh.txt', 'bornv.txt', 'borng.txt', 'Pref.txt']
    # path_habby = r'C:\Users\diane.von-gunten\HABBY'
    # path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'
    #
    # mystathab = Stathab('my_test4', path_habby)
    # mystathab.load_stathab_from_txt('listriv.txt', end_file_reach, name_file_allreach, path)
    # mystathab.create_hdf5()
    # mystathab.load_stathab_from_hdf5()
    # mystathab.stathab_calc(path_ori)
    # mystathab.path_im = path_im
    # #mystathab.savefig_stahab()
    # #mystathab.savetxt_stathab()
    # mystathab.test_stathab(path_ori)

    # test tropical stathab
    path_ori = r'D:\Diane_work\model_stat\FSTRESSandtathab\fstress_stathab_C\Stathab2_2014 04_R\Stathab2_2014 04\output'
    path = r'C:\Users\diane.von-gunten\HABBY\test_data\input_stathab2'
    path_prj = r'D:\Diane_work\dummy_folder\Projet1'
    name_prj = 'Projet1'
    path_im = r'D:\Diane_work\dummy_folder\cmd_test'
    path_bio = r'C:\Users\diane.von-gunten\HABBY\biology\stathab'
    name_file_allreach_trop = []
    end_file_reach_trop = ['deb.csv', 'qhw.csv', 'ii.csv']  # .txt or .csv
    biv = False

    mystathab = Stathab(name_prj, path_prj)
    mystathab.riverint = 2
    mystathab.load_stathab_from_txt('listriv', end_file_reach_trop, name_file_allreach_trop, path)
    # mystathab.create_hdf5()
    mystathab.fish_chosen = ['SIC']

    if biv:
        mystathab.stathab_trop_biv(path_bio)
        mystathab.test_stathab_trop_biv(path_ori)
    else:
        # False-> height based wua, True-> vpu
        mystathab.stathab_steep_calc(path_bio, False)
        mystathab.test_stathab_trop_uni(path_ori, False)


if __name__ == '__main__':
    main()
