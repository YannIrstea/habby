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

from multiprocessing import Value
import os
import numpy as np
from scipy import stats


from src.project_properties_mod import create_default_project_properties_dict, load_project_properties
from src.bio_info_mod import read_pref, copy_or_not_user_pref_curve_to_input_folder
from src.stathab_mod import load_namereach, power_law, check_stahab_files
from src.variable_unit_mod import HydraulicVariableUnitManagement
from src.user_preferences_mod import user_preferences
from src.plot_mod import plot_stat_data


class FStress:
    """
    The class for the Fstress model
    """

    def __init__(self, name_prj, path_prj):

        self.qhw = []  # the discharge, the heigh and width at least at two different dicharges (rivqvh.txt) a list of np.array
        self.qrange = [] #qrange: the qmin and qmax for each river [qmin,qmax] -> list of list
        self.qmod_all=[] # the list of discharges for each reach
        self.dict_pref_fstress = dict() # the relevant information per bio-model
        self.vh_all = [] # the list of (np.array of habitat values per discharge per bio-model ) for each reach
        self.wua_all = []  # the list of (np.array of WUA/100m of river per discharge per bio-model ) for each reach
        self.name_reach = []  # the list with the name of the reaches

        self.data_list = list()  # list by reach of dict of all reach data values



        self.h_all = []  # mean height of all the reaches
        self.v_all = []  # mean velocity of all the reaches
        self.w_all = []  # mean width of all the reaches

        self.path_im = os.path.join(path_prj, "output", "figures")  # path where to save the image

        # TODO supprimer
        self.path_hdf5 = os.path.join(path_prj, "hdf5")

        self.load_ok = False  # a boolean to manage the errors
        #  during the load of the files and the hdf5 creation and calculation
        self.path_prj = path_prj
        self.name_prj = name_prj
        # get the option for the figure in a dict
        self.project_properties = []
        self.path_txt = path_prj  # path where to save the text

    def load_fstress_from_txt(self, end_file_reach, path):
        """
        A function to read and check the input from fstress based on the csv/txt files.
        All files should be in the same folder.
        :param end_file_reach: the ending of the files whose names depends on the reach (with .txt or .csv)
        :param name_file_allreach: the name of the file common to all reaches
        :param path: the path to the file
        :return: the inputs needed for calc_fstress
        """
        self.load_ok = False
        # self.name_reach
        self.name_reach = load_namereach(path)
        if self.name_reach == [-99]:
            return
        nb_reach = len(self.name_reach)

        # prep
        self.qhw = []
        self.qrange = []


        #TODO supprimer
        self.qlist = []
        self.disthmes = []
        self.qhmoy = []
        self.dist_gran = []
        self.data_ii = []

        # read the txt files reach by reach
        # when loading file, python is always case-sensitive because Windows is.
        # so let's insist on this.
        all_file = os.listdir(path)
        for r in range(0, nb_reach):
            for ef in end_file_reach:
                file_found = False
                filename = os.path.join(path, self.name_reach[r] + ef)
                for f in range(0, len(all_file)):
                    if os.path.basename(filename.lower()) == all_file[f].lower():
                        file_found = True
                        filename = os.path.join(path, all_file[f])
                if not file_found:
                    print('Error: The file called ' + filename + ' was not found.\n')
                    return

                # open rivqwh.txt
                if ef[-7:-4] == 'qhw':
                    qhw_r = check_stahab_files(filename, True, ['Q[m3/s]', 'H[m]', 'W[m]'], [],False)
                    if np.array_equal(qhw_r, [-99]):  # if failed
                        return
                    if np.any(qhw_r[:,0]==0):
                        print('Error: The file called ' + filename + ' a 0 value for Q[m3/s] has been found\n')
                        return
                    self.qhw.append(qhw_r)

                # open rivdeb.txt
                elif ef[-7:-4] == 'deb':
                    #to accept old format version of.deb and new format version
                    with open(filename, 'rt') as fi:
                        lines = fi.readlines()
                        if lines[0][0:2].lower()=='qm': # new format version
                            qlist_r = check_stahab_files(filename, True, [], ['Qmin[m3/s]', 'Qmax[m3/s]'], False)
                        else: # old format version
                            qlist_r = check_stahab_files(filename, True, ['Q[m3/s]'], [],False)
                    if np.array_equal(qlist_r, [-99]):
                        return
                    if np.any(qlist_r ==0):
                        print('Error: The file called ' + filename + ' a 0 value for Q[m3/s] has been found\n')
                        return
                    if len(qlist_r) < 2:
                        print('Error: two discharges minimum are needed in ' + filename + '\n')
                        return
                    self.qrange.append(qlist_r)
        self.load_ok = True


    def calc_fstress(self):
        """
        This function run the model FStress for HABBY. FStress is based on the model of Nicolas Lamouroux. This model
        estimates suitability indices for invertebrate in relation with shear stress distributions. However, shear stress
        do not needs to be measured. It is statistically estimated based on velocity and height measurement.

        :param riv_name: the name of the river-> string
        :param data_hydro: the hydrological data (q,w,h for each river in riv name) -> list of list
        :param qrange: the qmin and qmax for each river [qmin,qmax] -> list of list
        :param inv_select: the name of the selected invetebrate
        :param pref_all: the preference data for all invertebrate
        :param name_all: the four letter code of all possible invertebrate
        :param path_prj: the path to the project-> string
        :param name_prj: the name of the project-> string
        """
        self.dict_pref_fstress=self.fstress_get_pref()
        qrange=self.qrange
        qhw=self.qhw


        # initalisation
        nbclaq = 50  # number of discharge point where the data have to be calculate

        self.qmod_all = []

        nb_models = len(self.dict_pref_fstress['code_bio_model'])

        self.vh_all = []


        # for each river
        for reach_i in range(0, len(self.name_reach)):
            vh_riv = np.zeros(( nb_models, nbclaq))  # nbclaq habitat values for each of the invertabrate selected
            wua_riv = np.zeros(( nb_models, nbclaq))  # nbclaq habitat values for each of the invertabrate selected
            qmod = np.zeros(nbclaq, ) # nbclaq discharge values
            hmod = np.zeros(nbclaq, ) # nbclaq mean water depth values
            wmod = np.zeros(nbclaq, ) # nbclaq width values
            vmmod = np.zeros(nbclaq, ) #

            # calculate the rating curve
            [h_coeff, w_coeff] = power_law(qhw[reach_i])

            if self.qrange[reach_i][0] == 0:
                qrange[reach_i][0] = 1e-2
            if qrange[reach_i][1] == 0:
                qrange[reach_i][0] = 1e-2
            # for each discharge
            for qind in range(0, nbclaq):
                # discharge
                lnqs = np.log(min(qrange[reach_i])) + (qind + 0.5) * (np.log(max(qrange[reach_i])) - np.log(min(qrange[reach_i]))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                # height and width and vm
                hs = np.exp(h_coeff[1] + lnqs * h_coeff[0]) # possible aussi hs= h_coeff[1]*(qmod[qind] ** h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
                wmod[qind] = ws
                vm = qmod[qind] / (hs * ws) #mean velocity for the discharge value
                vmmod[qind] = vm
                # stress distribution

                # habitat value
                for model_i in range(0, nb_models):
                    # for using the diststress function for historical reasons the constraint value must be expressed in dyn/cm2 so Pascal_values*10
                    diststress = func_stress(vm, hs,[x * 10 for x in self.dict_pref_fstress ['shearstress'][model_i]])
                    vh_riv[ model_i, qind] = np.sum(diststress * self.dict_pref_fstress['pref_values'][model_i]) # np.sum(diststress * pref_select[model_i, :])
                    wua_riv[ model_i, qind] = vh_riv[ model_i, qind] * ws * 100  # WUA/100m of river

            self.h_all.append(hmod)
            self.v_all.append(vmmod)
            self.w_all.append(wmod)
            self.vh_all.append(vh_riv)
            self.wua_all.append(wua_riv)
            self.qmod_all.append(qmod)

            self.data_list.append(dict(fish_list=[
                self.dict_pref_fstress['code_bio_model'][index_habmodel] + '-' + self.dict_pref_fstress['stage'][index_habmodel] for
                index_habmodel in range(nb_models)],
                                        qrange=qmod,
                                       q_all=qmod,
                                       h_all=hmod,
                                       w_all=wmod,
                                       vel_all=vmmod,
                                       OSI=vh_riv,
                                       WUA=wua_riv))


    def fstress_get_pref(self):
        hvum = HydraulicVariableUnitManagement()
        # each animal model
        dict_pref_fstress = {'code_bio_model': [], 'stage': [],  'codefish': [], 'shearstress': [], 'pref_numbers': [],
                             'pref_values': []}
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
            dict_pref_fstress['code_bio_model'].append(code_bio_model)
            dict_pref_fstress['stage'].append(stage)
            dict_pref_fstress['codefish'].append(code_bio_model+ '-' + stage)
            hydraulic_type_available = information_model_dict["hydraulic_type_available"][stage_index]
            # copy_or_not_user_pref_curve_to_input_folder
            copy_or_not_user_pref_curve_to_input_folder(hab_var, project_properties)
            # get data
            if hab_var.model_type == "univariate suitability index curves":
                if "HEM" in hydraulic_type_available:
                    dict_pref_fstress['shearstress'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.shear_stress.name)].data[0])
                    dict_pref_fstress['pref_numbers'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.shear_stress.name)].data[1])
                    dict_pref_fstress['pref_values'].append(
                        hab_var.variable_list[hab_var.variable_list.names().index(hvum.shear_stress.name)].data[2])
        return dict_pref_fstress


    def savefig_fstress(self):
        """
        """
        # figure option
        self.project_properties = load_project_properties(self.path_prj)
        if len(self.qmod_all) < len(self.name_reach):
            print('Error: Could not find discharge data. Figure not plotted. \n')
            return

        # plot
        for r in range(0, len(self.name_reach)):
            self.data_list[r]["name_reach"] = self.name_reach[r]
            progress_value = Value("d", 0)
            plot_stat_data(progress_value, self.data_list[r],
                           "FStress",
                           self.project_properties)

    def savetxt_fstress(self):
        """
        A function to save the stathab results in .txt form
        """

        nb_models = len(self.dict_pref_fstress['code_bio_model'])


        for r in range(0, len(self.name_reach)):
            namefile = os.path.join(self.path_txt,  'Fstress_' + self.name_reach[r] + '.txt')

            qmod = self.qmod_all[r]
            hmod = self.h_all[r]
            vmod = self.v_all[r]
            wmod = self.w_all[r]
            header0_list = ['Q', 'W', 'H', 'V']
            header1_list = ['[m3/s]', '[m]', '[m]', '[m/s]']
            jj0 = np.stack((qmod, wmod, hmod, vmod), axis=1)
            jj = np.copy(jj0)
        #     z0a = np.array([self.name_reach[r] for _ in range(len(qmod))], dtype=object)
            for index_habmodel in range(nb_models):
                codefish = self.dict_pref_fstress['code_bio_model'][index_habmodel] + '-' + self.dict_pref_fstress['stage'][
                    index_habmodel]
                header0_list.extend(['osi_hv-' + codefish, 'wua_hv-' + codefish])
                header1_list.extend(['[-]', '[m2/100m]'])
                jj = np.concatenate((jj, np.stack(
                    (self.vh_all[r][index_habmodel, :], self.wua_all[r][index_habmodel, :]),
                    axis=1)), axis=1)
            header_txt = '\t'.join(header0_list) + '\n' + '\t'.join(header1_list)
            np.savetxt(namefile, jj, delimiter='\t', header=header_txt)



def func_stress(vm, h, tau):
    """
    This functions calculates the distrbution of stress on the bottom of the river based of height and velocity
    at one discharge. In other word, it calculate the distrbution of the "hemispheres".
    This function is mainly a copy of stress function contains in the vitess2.c of the C source of FStress.

    :param vm: the velocity for this diacharge value
    :param h: the height for this discharge value
    :param tau: the constraint values
    :return: the stress distribution for this discharge

    """
    # froude and other parameters
    fr2 = vm ** 2. / (9.81 * h)
    k = -0.123 * np.log(fr2) - 0.132  # the first parameter of the stress distribution
    if k > 1:
        k = 1
    if k < 0:
        k = 0
    lntaum = 2.61 + 0.319 * np.log(fr2)
    nbst = len(tau)

    # estimate the m parameter by dichotomy m is between 2 and 18 (why?)
    # m is the second parameter fo the stress distribution
    mmin = 2.
    msup = 18.
    for p in range(1, 20):
        m = (mmin + msup) / 2.0
        diststress = denstress(k, m, nbst)
        fit = np.sum(tau * diststress)
        if np.log(fit) > lntaum:
            msup = m
        else:
            mmin = m
    diststress = denstress(k, m, nbst)

    return diststress

def denstress(k, m, nbst):
    """
    This function calulates the stress distrbution function for FStress. This distribution has generally the form
    of k*exp() + (1-k)* \Sigma(x-m)

    :param k: the first parameter of the distribution
    :param m: the second parameter of the disitribution
    :param nbst: the number of stress class in the distribution
    :return: the stress disitrbution for the (m,k) parameters
    """

    diststress = np.zeros(nbst, )

    # the first and the last class takes all until the end of the distribution
    diststress[0] = k * (1. - np.exp(-1.)) + (1. - k) * stats.norm.cdf((1. - m) / 2.5)
    diststress[-1] = k * np.exp(-nbst + 1) + (1. - k) * (1. - stats.norm.cdf((nbst - 1. - m) / 2.5))

    for cla in range(1, nbst - 1):
        diststress[cla] = k * (np.exp(-cla) - np.exp(-(cla + 1.))) + (1. - k) * (stats.norm.cdf((cla + 1. - m) / 2.5) -
                                                                                 stats.norm.cdf((cla - m) / 2.5))

    return diststress


