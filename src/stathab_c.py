import os
import numpy as np
from scipy import stats
from scipy import optimize
import re
import time
import matplotlib.pyplot as plt
import h5py
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class Stathab:
    """
    The class for the Stathab model
    """
    
    def __init__(self, name_prj, path_prj):
        self.qlist = []  # the list of dicharge for each reach, usually in rivdis.txt
        self.qwh = []  # the discharge, the width and height
        # at least at two different dicharges (rivqvh.txt) a list of np.array
        self.disthmes = [] # the measured distribution of height (rivdist.txt) a list of np.array
        self.qhmoy = []  # the mean height and q (2 first llines of rivdis.txt)
        self.dist_gran = []  # the distribution of substrate (rivgra.txt), a list of np.array
        self.fish_chosen = []  # the name of the fish to be studied, the name should also be in pref.txt
        self.lim_all = []  # the limits or bornes of h,q and granulio (born*.txt)
        self.name_reach = []  # the list with the name of the reaches
        self.j_all = [] # the suitability indices
        self.granulo_mean_all = []  # average granuloa
        self.vclass_all = []  # volume of each velocity classes
        self.hclass_all = []  # surface height for all classes
        self.rclass_all = []   # granulo surface for all classes
        self.h_all = []  # total height of all thr reaches
        self.w_all = []   # total width of all the reaches
        self.q_all = []   # discharge
        self.fish_chosen = np.array([])   # the name of the fish
        self.name_reach = []  # the name of the reaches of the river
        self.path_im = '.'   # path where to save the image
        self.load_ok = False # a boolean to manage the errors
        #  during the load of the files and the hdf5 creation and calculation
        self.path_prj = path_prj
        self.name_prj = name_prj

    def load_stathab_from_txt(self, reachname_file, end_file_reach, name_file_allreach, path):
        """
        A function to read and check the input from stathab based on the text files.
        All files should be in the same folder.
        The file Pref.txt is read in run_stathab.
        If self.fish_chosen is not present, all fish in the preference file are read.
        :param reachname_file the file with the name of the reaches to study (usually listirv.txt)
        :param end_file_reach the ending of the files whose names depends on the reach
        :param name_file_allreach the name of the file common to all reaches
        :param path the path to the file
        :return: the inputs needed for run_stathab
        """
        self.load_ok = False
        # self.name_reach
        self.name_reach = load_namereach(path, reachname_file)
        if self.name_reach == [-99]:
            return
        nb_reach = len(self.name_reach)

        # prep
        self.qwh = []
        self.qlist = []
        self.disthmes = []
        self.qhmoy = []
        self.dist_gran = []

        # read the txt files reach by reach
        for r in range(0, nb_reach):

            # open rivself.qwh.txt
            filename = os.path.join(path, self.name_reach[r] + end_file_reach[1])
            qwh_r = load_float_stathab(filename, True)
            if np.array_equal(qwh_r, [-99]):  # if failed
                return
            else:
                self.qwh.append(qwh_r)
            if len(qwh_r[0]) != 3:
                print('Error: The file called ' + filename + ' is not in the right format. Three columns needed. \n')
                return
            if len(qwh_r) < 2:
                print('Error: The file called ' + filename + ' is not in the right format. Minimum two rows needed. \n')
                return

            # open rivdeb.txt
            filename = os.path.join(path, self.name_reach[r] + end_file_reach[0])
            qlist_r = load_float_stathab(filename, True)
            if np.array_equal(qlist_r, [-99]):
                return
            else:
                self.qlist.append(qlist_r)
            if len(qlist_r) < 2:
                print('Error: two discharges minimum are needed in ' + filename + '\n')
                return

            # open riv dis
            filename = os.path.join(path, self.name_reach[r] + end_file_reach[3])
            dis_r = load_float_stathab(filename, True)
            if np.array_equal(dis_r, [-99]):  # if failed
                return
            if len(dis_r) < 4:
                print('Error: The file called ' + filename + ' is not in the right format. At least four values needed. \n')
                return
            else:
                self.disthmes.append(dis_r[2:])
                self.qhmoy.append(dis_r[:2])

            # open rivgra.txt
            filename = os.path.join(path, self.name_reach[r] + end_file_reach[2])
            dist_granulo_r = load_float_stathab(filename, True)
            if np.array_equal(dist_granulo_r, [-99]):  # if failed
                return
            if len(dist_granulo_r) != 12:
                print('Error: The file called ' + filename +
                      ' is not in the right format. 12 roughness classes are needed.\n')
                return
            else:
                self.dist_gran.append(dist_granulo_r)

        # open the files with the limits of class
        self.lim_all = []
        for b in range(0, 3):
            filename = name_file_allreach[b]
            filename = os.path.join(path, filename)
            born = load_float_stathab(filename, False)
            if np.array_equal(born, [-99]):
                return
            if len(born) < 2:
                print('Error: The file called ' + filename + ' is not in the right format.  At leat two values needed. \n')
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
        A function to load the file from an hdf5 whose name is given  in the xml project file
        :return:
        """
        self.load_ok = False
        # find the path to the h5 file
        fname = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(fname):
            print('Error: The xml project file was not found. Save the project in the General Tab. \n')
        doc = ET.parse(fname)
        root = doc.getroot()
        child = root.find(".//hdf5Stathab")
        if child is None:  # if there is data for STATHAB
            print("Error: No hdf5 file is written in the xml project file. \n")
            return

        # load the h5 file
        fname_h5 = child.text
        if os.path.isfile(fname_h5):
            file_stathab = h5py.File(fname_h5, 'r+')
        else:
            print("Error: Hdf5 file is not found. \n")
            return

        # prepare the data to be found
        basename1 = 'Info_general'

        # load reach_name
        try:
            gen_dataset = file_stathab[basename1 + "/reach_name"]
        except KeyError:
            print('Error: the dataset reach_name is missing from the hdf5 file. Is ' + fname_h5 +' a stathab input?\n')
            return
        gen_dataset = list(gen_dataset.values())[0]
        gen_dataset = np.array(gen_dataset)
        if len(gen_dataset) == 0:
            print('Error: no reach names found in the hdf5 file. \n')
            return
        # hdf5 cannot strore string directly, needs conversion
        #  array[3,-2] is needed after bytes to string conversion
        for r in range(0, len(gen_dataset)):
            a = str(gen_dataset[r])
            self.name_reach.append(a[3:-2])

        # load limits
        gen_dataset_name = ['lim_h', 'lim_v', 'lim_g']
        for i in range(0, len(gen_dataset_name)):
            try:
                gen_dataset = file_stathab[basename1 + "/" + gen_dataset_name[i]]
            except KeyError:
                print("Error: the dataset" + gen_dataset_name[i] + "is missing from the hdf5 file.\n")
                return
            gen_dataset = list(gen_dataset.values())[0]
            if len(np.array(gen_dataset)) < 2:
                print('Error: Limits of surface/volume could not be extracted from the hdf5 file. \n')
                return
            self.lim_all.append(np.array(gen_dataset))

        # get the chosen fish
        try:
            gen_dataset = file_stathab[basename1 + "/fish_chosen"]
        except KeyError:
            print('Error: the dataset fish_chosen is missing from the hdf5 file. \n')
            return
        gen_dataset = list(gen_dataset.values())[0]
        gen_dataset = np.array(gen_dataset)
        if len(gen_dataset) == 0:
            print('Error: no fish names found in the hdf5 file.\n')
            return
        # hdf5 cannot strore string directly, needs conversion
        #  array[3,-2] is needed after bytes to string conversion
        for f in range(0, len(gen_dataset)):
            a = str(gen_dataset[f])
            np.append(self.fish_chosen, a[3:-2])

        # get the data by reach
        reach_dataset_name = ['qlist', 'qwh', 'disthmes', 'qhmoy', 'dist_gran']
        reach_var = [self.qlist, self.qwh, self.disthmes, self.qhmoy, self.dist_gran]
        for r in range(0, len(self.name_reach)):
            for i in range(0, len(reach_dataset_name)):
                try:
                    reach_dataset = file_stathab[self.name_reach[r] + "/" + reach_dataset_name[i]]
                except KeyError:
                    print("Error: the dataset"+ reach_dataset_name[i]+ "is missing from the hdf5 file. \n")
                    return
                reach_dataset = list(reach_dataset.values())[0]
                if not reach_dataset:
                    print('Error: The variable ' + reach_dataset_name[r] +'could not be extracted from the hdf5 file.\n')
                reach_var[i].append(reach_dataset)

        self.load_ok = True

    def create_hdf5(self):
        """
        A function to create an hdf5 file from the loaded txt
        :return: the "name_prj"_STATHAB.h5 an hdf5 file with the info from stathab
        """
        self.load_ok = False
        # create an empty hdf5 file using all default prop.
        fname_no_path = self.name_prj + '_STATHAB' + '.h5'
        fname = os.path.join(self.path_prj, fname_no_path)
        file = h5py.File(fname, 'w')

        # create all datasets and group
        file.attrs['HDF5_version'] = h5py.version.hdf5_version
        file.attrs['h5py_version'] = h5py.version.version

        for r in range(0, len(self.name_reach)):
            try:
                filereach = file.create_group(self.name_reach[r])
            except ValueError:  # unable to create group
                new_name = 'unnamed_reach_' + str(r)
                # if two identical names
                if r > 0:
                    if np.any(self.name_reach[r] == self.name_reach[:r-1]):
                        print('Warning: two reach with identical names.\n')
                        new_name = self.name_reach[r] + str(r+1)
                else:
                    print('Warning: Reach name are not compatible with hdf5.\n')
                filereach = file.create_group(new_name)
            # save data for each reach
            try:
                qmesg = filereach.create_group('qlist')
                qmesg.create_dataset(fname_no_path, data=self.qlist[r])
                qwhg = filereach.create_group('qwh')
                qwhg.create_dataset(fname_no_path, data=self.qwh[r])
                distg = filereach.create_group('disthmes')
                distg.create_dataset(fname_no_path,  data=self.disthmes[r])
                qhmoyg = filereach.create_group('qhmoy')
                qhmoyg.create_dataset(fname_no_path,  data=self.qhmoy[r])
                dist_grang = filereach.create_group('dist_gran')
                dist_grang.create_dataset(fname_no_path, data=self.dist_gran[r])
            except IndexError:
                print('Error: the length of the data is not compatible with the number of reach.\n')
                return

        allreach = file.create_group('Info_general')
        reachg = allreach.create_group('reach_name')
        reach_ascii = [n.encode("ascii", "ignore") for n in self.name_reach]  # unicode is not ok with hdf5
        reachg.create_dataset(fname_no_path, (len(reach_ascii), 1), data=reach_ascii)
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

        # write info in the xml project file
        filename_prj = os.path.join(self.path_prj, self.name_prj + '.xml')
        if not os.path.isfile(filename_prj):
            print('Error: No project saved. Please create a project first in the General tab.\n')
            return
        else:
            doc = ET.parse(filename_prj)
            root = doc.getroot()
            child = root.find(".//Stathab")
            if child is None:
                stathab_element = ET.SubElement(root, "Stathab")
                hdf5file = ET.SubElement(stathab_element, "hdf5Stathab")
                hdf5file.text = fname
            else:
                hdf5file = root.find(".//hdf5Stathab")
                if hdf5file is None:
                    hdf5file = ET.SubElement(child, "hdf5Stathab")
                    hdf5file.text = fname
                else:
                    hdf5file.text = fname
            doc.write(filename_prj)
        self.load_ok = True

    def stathab_calc(self, path_pref='.', name_pref='Pref.txt'):
        """
        The function to calculate stathab output
        :param path_pref: the path to the preference file
        :param name_pref: the name of the preference file
        :return: the biological preferrence index (np.array of [reach, specices, nbclaq] size)
        , surface or volume by class, etc.
        """

        self.load_ok = False
        # various info
        nbclaq = 50  # number of discharge point where the data have to be calculate
        nbclagg = 12  # number of empirical roughness class
        coeff_granu = np.array([0.00001, 0.0001, 0.00028, 0.00125, 0.005, 0.012, 0.024, 0.048, 0.096, 0.192, 0.640, 1.536])  # WHY?
        nb_reach = len(self.name_reach)
        find_one_fish = False
        [name_fish, coeff_all] = load_pref(name_pref, path_pref)

        # choose which fish are studied
        coeff = np.zeros((len(self.fish_chosen), coeff_all.shape[1]))

        fish_chosen2 = np.array(self.fish_chosen)  # so we can use np.any
        if np.any(fish_chosen2 == 'all_fish'):
            coeff = coeff_all
            self.fish_chosen = name_fish
            find_one_fish = True
        else:
            for f in range(0, len(self.fish_chosen)):
                if self.fish_chosen[f] in name_fish:
                    ind_fish = name_fish.index(self.fish_chosen[f])
                    coeff[f, :] = coeff_all[ind_fish, :]
                    find_one_fish = True
                else:
                    print('Warning: One fish species was not found in the '
                          'Preference file. Fish name: ' + self.fish_chosen[f] +'\n')
        if not find_one_fish:
            print('Error: No fish species have been given or the fish species could not be found.\n')
            return -99
        # the biological preference index for all reach, all species
        self.j_all = np.zeros((nb_reach, len(self.fish_chosen), nbclaq))

        for r in range(0, nb_reach):

            # data for this reach
            qwh_r = self.qwh[r]
            qhmoy_r = self.qhmoy[r]
            h0 = qhmoy_r[1]
            disthmes_r = self.disthmes[r]
            qlist_r = self.qlist[r]
            dist_gran_r = np.array(self.dist_gran[r])
            hclass = np.zeros((len(self.lim_all[0])-1, nbclaq))
            vclass = np.zeros((len(self.lim_all[1])-1, nbclaq))
            rclass = np.zeros((len(self.lim_all[2])-1, nbclaq))
            qmod = np.zeros((nbclaq, 1))
            hmod = np.zeros((nbclaq, 1))
            wmod = np.zeros((nbclaq, 1))

            # granulometry
            granulo_mean = np.sum(coeff_granu * dist_gran_r)
            self.granulo_mean_all.append(granulo_mean)
            lim_g = self.lim_all[2]
            lim_g[lim_g < 0] = 0
            lim_g[lim_g > 11] = 11
            dist_gs = np.zeros(len(lim_g)-1,)
            for cg in range(0, len(lim_g)-1):
                lim_cg = [np.int(np.floor(lim_g[cg])), np.floor(lim_g[cg+1])]
                dist_chosen = dist_gran_r[np.int(lim_cg[0]):np.int(lim_cg[1])]
                dist_gs[cg] = np.sum(dist_chosen)

            # get the distributions and power law ready
            [h_coeff, w_coeff] = self.power_law(qwh_r)
            sh0 = self.find_sh0_maxvrais(disthmes_r, h0)

            # for all discharge
            for qind in range(0, nbclaq):
                lnqs = np.log(min(qlist_r)) + (qind+0.5) * (np.log(max(qlist_r)) - np.log(min(qlist_r))) / nbclaq
                qmod[qind] = np.exp(lnqs)
                hs = np.exp(h_coeff[1] + lnqs*h_coeff[0])
                hmod[qind] = hs
                ws = np.exp(w_coeff[1] + lnqs*w_coeff[0])
                wmod[qind] = ws
                vs = np.exp(lnqs)/(hs*ws)
                dist_hs = self.dist_h(sh0, h0, self.lim_all[0], hs)
                dist_vs = self.dist_v(hs, granulo_mean, self.lim_all[1], vs)
                # multiply by width and surface
                v = ws * hs  # total volume
                vclass[:, qind] = ws*dist_vs*hs
                hclass[:, qind] = dist_hs * ws
                rclass[:, qind] = dist_gs*ws
                # calculate the biological preference index
                j = coeff[:, 0] * v
                for vc in range(0, len(vclass[:, qind])):
                    j += vclass[vc, qind] * coeff[:, vc+1]
                for hc in range(0, len(hclass[:, qind])):
                    j += hclass[hc, qind] * coeff[:, hc + len(vclass[:, qind]) + 1]
                for rc in range(0, len(rclass[:, qind])):
                    j += rclass[rc, qind] * coeff[:, rc + len(hclass[:, qind]) + len(vclass[:, qind])+1]
                self.j_all[r, :, qind] = j
            self.vclass_all.append(vclass)
            self.hclass_all.append(hclass)
            self.rclass_all.append(rclass)
            self.h_all.append(hmod)
            self.w_all.append(wmod)
            self.q_all.append(qmod)

        self.load_ok = True

    def power_law(self, qwh_r):
        """
        The function to calculate power law for discharge and width
        ln(h0 = a1 + a2 ln(Q)
        :param qwh_r, an array where each line in one observatino of Q, width and height
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
        the function to find sh0, using a minimzation technique (NOT USE!!)
        !!!!!! possibly an error on the bornes?!!!!!!
        :param disthmesr: the measured distribution of height
        :param h0 the measured mean height
        :return: the optimized sh0
        """

        bornhmes = np.arange(0, len(disthmesr)+1) * 5*h0  # in c code, bornes are 1:n, so if we divide by h -> 1:n * h
        # optimization by non-linear least square
        # if start value equal or above one, the optimization fails.
        [sh0_opt, pcov] = optimize.curve_fit(lambda h, sh0: self.dist_h(sh0, h0, bornhmes, h), h0, disthmesr, p0=0.5)
        print(sh0_opt)
        return sh0_opt

    def find_sh0_maxvrais(self, disthmesr, h0):
        """
        the function to find sh0, using the maximum of vraisemblance.
        This function aims at reproducing the results from the c++ code. hence, no use of scipy
        :param disthmesr: the measured distribution of height
        :param h0 the measured mean height
        :return: the optimized sh0
        """
        nbclaemp = 20
        vraismax = -np.inf
        clmax = nbclaemp-1
        sh0 = 0
        for p in range(0, 101):
            sh = p/100
            if sh == 0:
                sh += 0.00001  # no log(0)
            if sh == 1:
                sh -= 0.00001
            vrais = disthmesr[0] * np.log(sh * (1-np.exp(-(1./4.))) + (1-sh)*(stats.norm.cdf(((1./4.)-1)/0.419)))
            vrais += disthmesr[clmax] * np.log(sh * np.exp(-(clmax/4.)) +
                                               (1 - sh) * (1 - stats.norm.cdf(((clmax / 4.) - 1) / 0.419)))
            for cla in range(1, clmax):
                vrais += disthmesr[cla] * np.log(sh * (np.exp(-cla / 4.) - np.exp(-(cla + 1) / 4.))+
                                                 (1 - sh) * (stats.norm.cdf(((cla + 1) / 4. - 1) / 0.419) -
                                                             stats.norm.cdf((cla / 4. - 1) / 0.419)))
            if vrais > vraismax:
                vraismax = vrais
                sh0 = p/100
        return sh0

    def dist_h(self, sh0, h0, bornh, h):
        """
        The calculation of height distribution  acrros the river
        The distribution is a mix of an exponential and guassian.
        :param sh0: the sh of the original data
        sh is the parameter of the distribution, gives the relative importance of ganussian and exp distrbution
        :param h the mean height data
        :param h0 the mean height
        :param bornh the limits of each class of height
        :return: disth the distribution of heights across the river for the mean height h.

        """
        # sh
        # sh0 = 0.48
        sh = sh0 - 0.7 * np.log(h/h0)
        if sh > 1:
            sh = 1.
        if sh < 0:
            sh = 0.
        # prep
        nbclass = len(bornh) - 1
        disth = np.zeros((nbclass, ))
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
        NOT USED IN Habby, but can be useful if scipy is not available
        (remplace all stat.norm.cdf with dengauss -> no need for scipy)
        :param x: the parameter of the gaussian
        :return:
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
            t2 = t2/(2 * k3 + 1)
            s3 += t2
            if abs(t2) < 0.000001:
                break
        res = 0.5 + 0.398942 * s3
        if n == -1:
            res = 1-res
        return res

    def dist_v(self, h, d, bornv, v):
        """
        The calculation of velocity distribution  acrros the river
        The distribution is a mix of an exponential and guassian.
        :param h: the height which is related to the mean velocity v
        :param d granulo moyenne
        :param bornv: the born of the velocity
        :param v: the mean velocity
        :return: the distribution of velocity across the river
        """
        # sv
        fr = v/np.sqrt(9.81*h)
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
                + sv * 0.358 * (stats.norm.cdf((b - 2.44) / 1.223) - stats.norm.cdf((c - 2.44) / 1.223))\
                + (1 - sv) * (stats.norm.cdf((b - 1) / 0.611) - stats.norm.cdf((c - 1) / 0.611))
        return distv

    def savefig_stahab(self):
        """
        A fucntion to save the results in ascii and the figure
        :return: 2 figures
        """
        plt.rcParams['figure.figsize'] = 10, 8
        plt.rcParams['font.size'] = 8
        plt.close()

        for r in range(0, len(self.name_reach)):
            rclass = self.rclass_all[r]
            hclass = self.hclass_all[r]
            vclass = self.vclass_all[r]
            vol = self.h_all[0] * self.w_all[0]
            qmod = self.q_all[r]

            fig = plt.figure()
            plt.subplot(221)
            plt.title('Volume total')
            plt.plot(qmod, vol)
            plt.ylabel('Volume for 1m reach [m3]')
            plt.subplot(222)
            plt.title('Surface by class for the granulometry')
            for g in range(0, len(rclass)):
                plt.plot(qmod, rclass[g], '-', label='Class ' + str(g))
            plt.ylabel('Surface by Class [m$^{2}$]')
            lgd = plt.legend(bbox_to_anchor=(1.4, 1), loc='upper right', ncol=1)
            plt.subplot(223)
            plt.title('Surface by class for the height')
            for g in range(0, len(hclass)):
                plt.plot(qmod, hclass[g, :], '-', label='Class ' + str(g))
            plt.xlabel('Q [m$^{3}$/sec]')
            plt.ylabel('Surface by Class [m$^{2}$]')
            lgd = plt.legend()
            plt.subplot(224)
            plt.title('Volume by class for the velocity')
            for g in range(0, len(vclass)):
                plt.plot(qmod, vclass[g], '-', label='Class ' + str(g))
            plt.xlabel('Q [m$^{3}$/sec]')
            plt.ylabel('Volume by Class [m$^{3}$]')
            lgd = plt.legend(bbox_to_anchor=(1.4, 1), loc='upper right', ncol=1)
            name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                    "_vel_h_gran_classes" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png')
            fig.savefig(os.path.join(self.path_im, name_fig), bbox_extra_artists=(lgd,), bbox_inches='tight')
            name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                    "_vel_h_gran_classes" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf')
            fig.savefig(os.path.join(self.path_im, name_fig), bbox_extra_artists=(lgd,), bbox_inches='tight')

            # suitability index
            j = np.squeeze(self.j_all[0, :, :])
            fig = plt.figure()
            for e in range(0, len(self.fish_chosen)):
                plt.plot(qmod, j[e, :], '-', label=self.fish_chosen[e])
            plt.xlabel('Q [m$^{3}$/sec]')
            plt.ylabel('Index J [ ]')
            plt.title('Suitability index J')
            lgd = plt.legend(bbox_to_anchor=(1.2, 1), loc='upper right', ncol=1, borderaxespad=0.)

            name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                    "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S")+'.png')
            fig.savefig(os.path.join(self.path_im, name_fig), bbox_extra_artists=(lgd,), bbox_inches='tight')
            name_fig = os.path.join(self.path_im, self.name_reach[r] +
                                    "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf')
            fig.savefig(os.path.join(self.path_im, name_fig), bbox_extra_artists=(lgd,), bbox_inches='tight')
            # plt.show()

    def savetxt_stathab(self):
        """
        A function to save the stathab result in .txt form
        :return: .txt files
        """

        for r in range(0, len(self.name_reach)):
            j = np.squeeze(self.j_all[r, :, :])
            qmod = self.q_all[r]
            vclass = self.vclass_all[r]
            hclass = self.hclass_all[r]
            rclass = self.rclass_all[r]
            hmod = self.h_all[r]
            wmod = self.w_all[r]
            dummy = np.zeros((len(hmod), 1)) - 99

            # rrd file
            # depth and dist Q should be added
            data = np.hstack((np.log(qmod), dummy, hmod, wmod, vclass.T, hclass.T, rclass.T))
            namefile = os.path.join(self.path_im, self.name_reach[r] +
                                    time.strftime("%d_%m_%Y_at_%H_%M_%S")+'rrd.txt')
            np.savetxt(namefile, data)

            # rre.txt
            namefile = os.path.join(self.path_im, self.name_reach[r] +
                                    time.strftime("%d_%m_%Y_at_%H_%M_%S") + 'rre.txt')
            np.savetxt(namefile, j.T)

    def test_stathab(self, path_ori):
        """
        A short function to test part of the outputs against the C++ code,
        NOT USED in Habby but practical anyways to debug
        :param path_ori: the path to the files from stathab based on the c++ code
        :return:
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
        plt.plot(q_orr, 1*vol_all_orr[:, 3]*vol_all_orr[:, 2], '*')
        plt.plot(q_orr, v)
        plt.xlabel('Q [m$^{3}$3/sec]')
        plt.ylabel('Volume for 1m reach [m3]')
        plt.legend(('C++ Code', 'new python code'), loc='upper left')
        plt.subplot(222)
        plt.title('Surface by class for the granulometry')
        for g in range(0, len(rclass)):
            plt.plot(q_orr, vol_all_orr[:, 13+g], '*')
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
        plt.title('Suitability index J')
        lgd = plt.legend(bbox_to_anchor=(1, 1), loc='upper right', ncol=1)
    
        #plt.show()


def load_float_stathab(filename, check_neg):
    """
    A function to load float with extra checks
    :param filename: the file to load with the path
    :param check_neg, if true negative value are not allowed in the data
    :return: data if ok, -99 if failed
    """
    myfloatdata = [-99]
    if os.path.isfile(filename):
        try:
            myfloatdata = np.loadtxt(filename)
        except ValueError:
            print('Error: The file called ' + filename + ' could not be read.\n')
            return [-99]
    else:  # when loading file, python is always case-sensitive because Windows is.
        # so let's insist on this.
        path_here = os.path.dirname(filename)
        all_file = os.listdir(path_here)
        file_found = False
        for f in range(0, len(all_file)):
            print(all_file[f])
            if os.path.basename(filename.lower()) == all_file[f].lower():
                file_found = True
                filename = os.path.join(path_here, all_file[f])
                try:
                    myfloatdata = np.loadtxt(filename)
                except ValueError:
                    print('Error: The file called ' + filename + ' could not be read.\n')
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
    The function loads the different pref coeffficient contained in filepref
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


def load_namereach(path, name_file_reach='listriv.txt'):
    """
    A function to only load the reach names (useful for the GUI)
    :param path : the path th the listriv.txt
    :param name_file_reach: In case the file name is not listriv.txt
    :return: the list of reach name
    """
    # find the reaches
    filename = os.path.join(path, name_file_reach)
    if os.path.isfile(filename):
        with open(filename, 'rt') as f:
            data = f.read()
    else:
        print('Error:  The file containing the names of the reaches was not found (listriv.txt).\n')
        return [-99]
    if not data:
        print('Error:  The file containing the names of the reaches could not be read (listriv.txt).\n')
        return [-99]
    # get reach name line by line
    name_reach = data.split('\n')  # in case there is a space in the names of the reaches
    return name_reach


def main():

    path = 'D:\Diane_work\model_stat\input_test'
    path_ori = 'D:\Diane_work\model_stat\stathab_t(1)'
    end_file_reach = ['deb.txt', 'qhw.txt', 'gra.txt', 'dis.txt']
    name_file_allreach = ['bornh.txt', 'bornv.txt', 'borng.txt', 'Pref.txt']
    path_habby = r'C:\Users\diane.von-gunten\HABBY'
    path_im = r'C:\Users\diane.von-gunten\HABBY\figures_habby'

    mystathab = Stathab('my_test4', path_habby)
    mystathab.load_stathab_from_txt('listriv.txt', end_file_reach, name_file_allreach, path)
    mystathab.create_hdf5()
    mystathab.load_stathab_from_hdf5()
    mystathab.stathab_calc(path_ori)
    mystathab.path_im = path_im
    mystathab.savefig_stahab()
    mystathab.savetxt_stathab()
    mystathab.test_stathab(path_ori)


if __name__ == '__main__':
    main()