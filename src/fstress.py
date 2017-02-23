try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from src import load_hdf5
import h5py
import os
import time
import numpy as np


def save_fstress(path_prj, name_prj, name_bio, path_bio, riv_name, data_hydro, qrange, fish_list):
    """
    This function saves the data related to the fstress model in an hdf5 file and write the name of this hdf5 file
    in the xml project file.

    :param path_prj: the path to the project-> string
    :param name_prj: the name of the project-> string
    :param name_bio: the name of the preference file-> string
    :param path_bio: the path to the preference file-> string
    :param riv_name: the name of the river-> string
    :param data_hydro: the hydrological data (q,w,h for each river in riv name) -> list of list
    :param qrange: the qmin and qmax for each river [qmin,qmax] -> list of list
    :param fish_list: the name of the selected fish -> list of string
    """

    # create the hdf5 file
    fname_no_path = 'FStress_'+ name_prj + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")  + '.h5'
    fname = os.path.join(path_prj, fname_no_path)
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
    print(len(riv_name))
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
        fish_name.append(dataset_i[2:-1]) # because hdf5 give the string b'sdfsd', no it is not a binary!

    return qhw, qrange, river_name, fish_name



