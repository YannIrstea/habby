try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import load_hdf5
import h5py
import os
import time
import numpy as np
from src import stathab_c
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib as mpl
from src_GUI import output_fig_GUI


def save_fstress(path_hdf5, path_prj, name_prj, name_bio, path_bio, riv_name, data_hydro, qrange, fish_list):
    """
    This function saves the data related to the fstress model in an hdf5 file and write the name of this hdf5 file
    in the xml project file.

    :param path_hdf5: the path where to sdave the hdf5-> string
    :param path_prj: the path to the project-> string
    :param name_prj: the name of the project-> string
    :param name_bio: the name of the preference file-> string
    :param path_bio: the path to the preference file-> string
    :param riv_name: the name of the river-> string
    :param data_hydro: the hydrological data (q,w,h for each river in riv name) -> list of list
    :param qrange: the qmin and qmax for each river [qmin,qmax] -> list of list
    :param fish_list: the name of the selected invertebrate (! no fish) -> list of string
    """

    # create the hdf5 file
    fname_no_path = 'FStress_'+ name_prj + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")  + '.h5'
    fname = os.path.join(path_hdf5, fname_no_path)
    file = h5py.File(fname, 'w')

    # create general attribute

    file.attrs['HDF5_version'] = h5py.version.hdf5_version
    file.attrs['h5py_version'] = h5py.version.version
    file.attrs['name_prj'] = name_prj
    file.attrs['path_prj'] = path_prj
    file.attrs['path_bio'] = path_bio
    file.attrs['file_bio'] = name_bio

    # write the data in it (similar to save_estimhab in Main_Windows_1.py)
    i = 0
    nb_riv = file.create_group('Nb_river')
    nb_riv.create_dataset(fname_no_path, [1, 1], data=len(riv_name))
    for r in riv_name:
        # hydro data
        [q1, w1, h1] = data_hydro[i][0]
        [q2, w2, h2] = data_hydro[i][1]
        rivhere = file.create_group('River_' + str(i))
        rivname = rivhere.create_group('River_name')
        rivname.create_dataset(fname_no_path, data=r.encode("ascii", "ignore"))
        qmesg = rivhere.create_group(r+'_qmes')
        qmesg.create_dataset(fname_no_path, [2, 1], data=[q1, q2])
        wmesg = rivhere.create_group(r+'_wmes')
        wmesg.create_dataset(fname_no_path, [2, 1], data=[w1, w2])
        hmesg = rivhere.create_group(r+'_hmes')
        hmesg.create_dataset(fname_no_path, [2, 1], data=[h1, h2])
        qrangeg = rivhere.create_group(r+'_qrange')
        if len(qrange[i]) == 2:
            [qmin, qmax] = qrange[i]
            qrangeg.create_dataset(fname_no_path, [2, 1], data=[qmin, qmax])
        i += 1
    # fish data
    ascii_str = [n.encode("ascii", "ignore") for n in fish_list]  # unicode is not ok with hdf5
    fish_typeg = file.create_group('fish_type')
    fish_typeg.create_dataset(fname_no_path, (len(fish_list), 1), data=ascii_str)
    file.close()

    # save the new hdf5 name in the xml project file
    fnamep = os.path.join(path_prj, name_prj + '.xml')
    if not os.path.isfile(fnamep):
        print("The project is not saved. Save the project in the Start tab before saving FStress data")
    else:
        doc = ET.parse(fnamep)
        root = doc.getroot()
        tree = ET.ElementTree(root)
        child = root.find(".//FStress_data")
        # test if there is already estimhab data in the project
        if child is None:
            child = ET.SubElement(root, "FStress_data")
            child.text = fname_no_path
        else:
            child.text = fname_no_path
        tree.write(fnamep)


def read_fstress_hdf5(hdf5_name, hdf5_path):
    """
    This functions reads an hdf5 file related to FStress and extract the relevant information.

    :param hdf5_name: the name of the hdf5 file with the information realted to FStress
    :param hdf5_path: the path to this file

    :return:[[q,w,h], [q,w,h]] for each river, [qmin,qmax] for each river, the river names, and the selected fish

    """
    failload = [-99], [-99], ['-99'], ['-99']
    river_name = []
    qhw = []
    qrange = []
    fish_name = []

    # open hdf5 with check
    h5_filename_path = os.path.join(hdf5_path, hdf5_name)
    h5file = load_hdf5.open_hdf5(h5_filename_path)
    if h5file is None:
        print('Error: hdf5 file could not be open. \n')
        return failload

    # read the number of rivers
    try:
        gen_dataset = h5file["/Nb_river"]
    except KeyError:
        print('Error: the number of river is missing from the hdf5 file. Is ' + hdf5_name + ' an FStress input? \n')
        return failload
    try:
        nb_riv = list(gen_dataset.values())[0]
        nb_riv = int(np.array(nb_riv))  # you do need the np.array()
    except ValueError:
        print('Error: the number of river is missing from the hdf5 file. Is ' + hdf5_name + ' an FStress input? (2) \n')
        return failload

    # read the hydrological data
    for i in range(0, nb_riv):
        # qhw
        qhw1 = []
        qhw2 = []
        basename = 'River_' + str(i)
        try:
            gen_dataset = h5file[basename + "/River_name"]
        except KeyError:
            print('Error: the river name is missing from the FStress hdf5 file. \n')
            return failload
        try:
            r = list(gen_dataset.values())[0]
            r = str(np.array(r))[2:-1]
            river_name.append(r)
        except IndexError:
            print('Error: the river name is missing from the FStress hdf5 file. (2) \n')
            return failload
        try:
            gen_dataset = h5file[basename + '/' + r+'_qmes']
        except KeyError:
            print('Error: the discharge is missing from the FStress hdf5 file. \n')
            return failload
        qmes = list(gen_dataset.values())[0]
        qhw1.append(float(qmes[0]))
        qhw2.append(float(qmes[1]))
        try:
            gen_dataset = h5file[basename + '/' + r + '_hmes']
        except KeyError:
            print('Error: the height is missing from the FStress hdf5 file. \n')
            return failload
        hmes = list(gen_dataset.values())[0]
        qhw1.append(float(hmes[0]))
        qhw2.append(float(hmes[1]))
        try:
            gen_dataset = h5file[basename + '/' + r +'_wmes']
        except KeyError:
            print('Error: the width is missing from the FStress hdf5 file. \n')
            return failload
        wmes = list(gen_dataset.values())[0]
        qhw1.append(float(wmes[0]))
        qhw2.append(float(wmes[1]))
        qhw.append([qhw1, qhw2])
        # discharge range
        try:
            gen_dataset = h5file[basename + '/' + r + '_qrange']
        except KeyError:
            print('Error: the discharge range is missing from the FStress hdf5 file. \n')
            return failload
        qr = list(gen_dataset.values())[0]
        qrange.append([float(qr[0]), float(qr[1])])

    # read the fish name
    dataset = h5file['fish_type']
    dataset = list(dataset.values())[0]
    for i in range(0, len(dataset)):
        dataset_i = str(dataset[i])
        fish_name.append(dataset_i[3:-2]) # because hdf5 give the string b'sdfsd', no it is not a binary!

    return qhw, qrange, river_name, fish_name


def read_pref(path_bio, name_bio):
    """
    This function loads and read the preference file for FStress.

    :param path_bio: the path to the preference file
    :param name_bio: the name of the preference file
    :return: the name invertebrate and their preference coefficient
    """
    failload = [-99], [-99]
    pref_inver = []
    all_inv_name= []
    # open file
    filenamebio = os.path.join(path_bio, name_bio)
    if os.path.isfile(filenamebio):
        with open(filenamebio, 'rt') as f:
            data_inv = f.read()
    else:
        print('Error: No preference file for FStress. To use FStress, add a preference file and restart '
                          'HABBY.')
        return failload
    data_inv = data_inv.split('\n')

    # get the data by invertebrate species
    if len(data_inv) == 0:
        print('Error: No invertebrate found in the preference file for FStress. To use FStress, add a '
                          'correct preference file and restart HABBY.')
        return failload
    for i in range(0, len(data_inv)):
        data_this_inv = data_inv[i]
        if len(data_this_inv) > 0:
            data_this_inv = data_this_inv.split()
            if len(data_this_inv) != 21:  # number of FStress point + name
                print('Warning: A preference curve for FStress is not composed of 20 data')
            # get the invertebrate name
            all_inv_name.append(data_this_inv[0].strip())
            # get the pref
            try:
                data_this_inv = list(map(float, data_this_inv[1:]))
            except ValueError:
                print(
                    'Error: The preference file for FStress could not be read. To use FStress, add a correct '
                    'preference file and restart HABBY.')
                return failload
            pref_inver.append(data_this_inv)

    return pref_inver, all_inv_name


def run_fstress(data_hydro, qrange, riv_name, inv_select, pref_all, name_all, name_prj, path_prj):
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
    # initalisation
    nbclaq = 50  # number of discharge point where the data have to be calculate
    data_hydro = np.array(data_hydro) # qhw
    pref_all = np.array(pref_all)
    # this is the constraint value on dyn/cm2, empirical data probably
    tau = [0.771, 0.828, 0.945, 1.18, 1.41, 1.66, 2.18, 2.72, 3.93, 5.29, 6.82, 8.26, 10.9, 15.9, 22.7, 31.7, 44.8, 63.4
           , 89.5, 127.]
    qmod_all = []
    nb_inv = len(inv_select)
    vh = []
    pref_select = np.zeros((nb_inv, len(tau)))# preference coeff for the selected invertebrate
    find_one_inv = False

    # there are some functions from FStress which have already be done by Stathab.
    # so we create a 'dummy" instance of Stathab to be able to use the methods of Stathab when useful
    blob_stathab = stathab_c.Stathab(name_prj, path_prj)

    # get the fish name
    for f in range(0, nb_inv):
        # if invertebrate exist
        if inv_select[f] in name_all:
            ind_fish = name_all.index(inv_select[f])
            pref_select[f, :] = pref_all[ind_fish, :]
            find_one_inv = True
        # if not found
        else:
            nb_inv -= 1
            vh = np.delete(vh, (f),axis=1)
            pref_select = np.delete(pref_select, (f), axis=0)
            del inv_select[f]
            print('Warning: One fish species was not found in the '
                  'Preference file. Fish name: ' + inv_select[f] + '\n')
    if not find_one_inv:
        print('Error: No fish species have been given or the fish species could not be found.\n')
        return -99

    # for each river
    for i in range(0, len(riv_name)):
        vh_riv = np.zeros((nbclaq, nb_inv))
        qmod = np.zeros(nbclaq, )
        hmod = np.zeros(nbclaq, )
        wmod = np.zeros(nbclaq, )

        # calculate the rating curve
        # CAREFUL, we exchange here between h and w
        [w_coeff, h_coeff] = blob_stathab.power_law(data_hydro[i])

        # for each discharge
        for qind in range(0, nbclaq):
            # discharge
            lnqs = np.log(min(qrange[i])) + (qind + 0.5) * (np.log(max(qrange[i])) - np.log(min(qrange[i]))) / nbclaq
            qmod[qind] = np.exp(lnqs)
            # height and width and vm
            hs = np.exp(h_coeff[1] + lnqs * h_coeff[0])
            hmod[qind] = hs
            ws = np.exp(w_coeff[1] + lnqs * w_coeff[0])
            wmod[qind] = ws
            vm = np.exp(lnqs) / (hs * ws)
            # stress distribution
            diststress = func_stress(vm, hs, tau)
            # habitat value
            for ii in range(0, nb_inv):
                vh_riv[qind,ii] = np.sum(diststress * pref_select[ii, :])
        vh.append(vh_riv)
        qmod_all.append(qmod)

    return vh, qmod_all, inv_select


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
    fr2 = vm**2. / (9.81*h)
    k = -0.123 * np.log(fr2) - 0.132 # the first parameter of the stress distribution
    if k>1:
        k = 1
    if k < 0:
        k = 0
    lntaum = 2.61 + 0.319* np.log(fr2)
    nbst = len(tau)

    # estimate the m parameter by dichotomy m is between 2 and 18 (why?)
    # m is the seconc parameter fo the stress distribution
    mmin = 2.
    msup = 18.
    for p in range(1, 20):
        m = (mmin + msup)/2.0
        diststress = denstress(k, m, nbst)
        fit = np.sum(tau*diststress)
        if np.log(fit) > lntaum:
            msup = m
        else:
            mmin = m
    diststress = denstress(k, m, nbst)

    return diststress


def denstress(k,m, nbst):
    """
    This function calulates the stress distrbution function for FStress. This distribution has generally the form
    of k*exp() + (1-k)* \Sigma(x-m)

    :param k: the first parameter of the distribution
    :param m: the second parameter of the disitribution
    :param nbst: the number of stress class in the distribution
    :return: the stress disitrbution for the (m,k) parameters
    """

    diststress = np.zeros(nbst,)

    # the first and the last class takes all until the end of the distribution
    diststress[0] = k * (1. - np.exp(-1.)) + (1.-k) * stats.norm.cdf((1.-m)/2.5)
    diststress[-1] = k * np.exp(-nbst+1) + (1.-k) * (1.-stats.norm.cdf((nbst-1.-m)/2.5))

    for cla in range(1, nbst-1):
        diststress[cla] = k * (np.exp(-cla) - np.exp(-(cla+1.))) + (1.-k) * (stats.norm.cdf((cla+1.-m)/2.5) -
                                                                           stats.norm.cdf((cla-m)/2.5))

    return diststress


def write_txt(qmod_all, vh_all, name_inv, path_txt, name_river):
    """
    This function writes the txt outputs for FStress

    :param qmod_all: the modelled discharge for each river
    :param vh_all: the suitability indoex for each invertebrate species for each river
    :param name_inv: The four letter code of each selected invetebrate
    :param path_txt: the path where to save the text file
    :param name_river: the name of the river

    """
    i = 0
    r = 'Default River'
    for r in name_river:
        qmod = qmod_all[i]
        vh = vh_all[i]
        fname = os.path.join(path_txt, 'Fstress_'+ r+ time.strftime("%d_%m_%Y_at_%H_%M_%S") +'_rre.txt')
        np.savetxt(fname, vh)
        fname = os.path.join(path_txt, 'Fstress_' + r + time.strftime("%d_%m_%Y_at_%H_%M_%S")+ '_discharge.txt')
        np.savetxt(fname, qmod)
    fname = os.path.join(path_txt, 'Fstress_' + r + time.strftime("%d_%m_%Y_at_%H_%M_%S")+ '_code_inv.txt')
    name_inv_str = ''
    for i in range(0, len(name_inv)):
        name_inv_str += name_inv[i] + "\n"
    with open(fname,'w') as f:
        f.write(name_inv_str)


def figure_fstress(qmod_all, vh_all, name_inv, path_im, name_river, fig_opt = {}):
    """
    This function creates the figures for Fstress, notably the suitability index as a function of discharge for all
    rivers

    :param qmod_all: the modelled discharge for each river
    :param vh_all: the suitability indoex for each invertebrate species for each river
    :param name_inv: The four letter code of each selected invetebrate
    :param path_im: the path where to save the figure
    :param name_river: the name of the river
    :param fig_opt: the figure option in a dictionnary

    """

    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['pdf.fonttype'] = 42

    i = 0
    for r in name_river:
        qmod = qmod_all[i]
        j = vh_all[i].T
        fig = plt.figure()
        ax = plt.subplot(111)
        for e in range(0, len(name_inv)):
            plt.plot(qmod, j[e, :], '-', label=name_inv[e])
        plt.xlabel('Q [m$^{3}$/sec]')
        plt.ylabel('Index J [ ]')
        plt.title('Suitability index J - FStress -River: ' + r)
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        lgd = plt.legend(bbox_to_anchor=(1.4, 1), loc='upper right', ncol=1)
        if format == 0 or format == 1:
            name_fig = os.path.join(path_im, 'Fstress_' + r +
                                    "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png')
        if format == 0 or format == 3:
            name_fig = os.path.join(path_im, 'Fstress_' + r +
                                    "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf')
        if format == 2:
            name_fig = os.path.join(path_im, 'Fstress_' + r +
                                    "_suitability_index" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.jpg')
        fig.savefig(os.path.join(path_im, name_fig), bbox_extra_artists=(lgd,), bbox_inches='tight',
                    dpi=fig_opt['resolution'], transparent=True)
        i += 1


def fstress_test(qmod_all, vh_all, name_inv, name_river,  path_rre):
    """
    This functions compares the output of the C programm of FStress and the output of this script. it is not used
    by HABBY, but it is practical to debug.

    :param qmod_all: the modelled discharge for each river
    :param vh_all: the suitability indoex for each invertebrate species for each river
    :param name_inv: The four letter code of each selected invetebrate
    :param name_river: the name of the river
    :param path_rre: the path to the C output
    """
    mpl.rcParams['ps.fonttype'] = 42
    mpl.rcParams['pdf.fonttype'] = 42

    i = 0
    for r in name_river:
        # get the C data for this river
        namefile = os.path.join(path_rre, r + 'rre.txt')
        c_data = np.loadtxt(namefile)
        namefile = os.path.join(path_rre, r + 'rrd.txt')
        dis_data = np.loadtxt(namefile)

        # modelled by python data
        qmod = qmod_all[i]
        j = vh_all[i].T

        # plot for this river
        fig = plt.figure()
        ax = plt.subplot(111)
        dis_c = np.exp(dis_data[:,0])
        for e in range(0, min(len(name_inv),5)):
            plt.plot(qmod, j[e, :], '-', label=name_inv[e] + '_Python')
            plt.plot(dis_c, c_data[:,e], 'x', label=name_inv[e]+ '_C')
        plt.xlabel('Q [m$^{3}$/sec]')
        plt.ylabel('Index J [ ]')
        plt.title('Suitability index J - FStress')
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        lgd = plt.legend(bbox_to_anchor=(1.4, 1), loc='upper right', ncol=1)
        i += 1


def main():
    """
    This is not the main() of HABBY. This local function is used to test the Fstress model.
    """

    path_prj = r'D:\Diane_work\dummy_folder\DefaultProj'
    name_prj = 'blob'
    path_im = path_prj
    path_bio = r'C:\Users\diane.von-gunten\HABBY\biology'
    name_bio = 'pref_fstress.txt'
    riv_name = ['riv1','riv2']
    hdf5_name = r'FStress_DefaultProj_23_02_2017_at_13_31_08.h5'
    hdf5_path = r'D:\Diane_work\dummy_folder\DefaultProj'
    path_rre = r'D:\Diane_work\model_stat\FSTRESSandtathab\fstress_stathab_C\FSTRESSDiane'

    [qhw, qrange, riv_name, name_inv] =read_fstress_hdf5(hdf5_name, hdf5_path)

    [pref_all, name_all] = read_pref(path_bio, name_bio)
    # all inv selected -> name_allx2
    [vh, qmod, inv_select] = run_fstress(qhw, qrange, riv_name, name_all, pref_all, name_all, name_prj, path_prj)
    # figure_fstress(qmod, vh, inv_select, path_im, riv_name)
    fstress_test(qmod, vh, inv_select, riv_name, path_rre)
    plt.show()

if __name__ == '__main__':
    main()