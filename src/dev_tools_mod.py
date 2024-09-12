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
import shutil
import unicodedata
from glob import glob
from shutil import rmtree, copy as sh_copy
import numpy as np


def copy_shapefiles(input_shapefile_abspath, hdf5_name, dest_folder_path, remove=True):
    """
    get all file with same prefix of input_shapefile_abspath and copy them to dest_folder_path.
    """
    # create folder with hdf5 name in input project folder
    input_hdf5name_folder_path = os.path.join(dest_folder_path, os.path.splitext(hdf5_name)[0])
    if os.path.exists(input_hdf5name_folder_path):
        if remove:
            try:
                rmtree(input_hdf5name_folder_path)
                os.mkdir(input_hdf5name_folder_path)
            except PermissionError:
                print("Error: Hydraulic input file can be copied to input project folder"
                      " as it is open in another program.")
                try:
                    rmtree(input_hdf5name_folder_path)
                    os.mkdir(input_hdf5name_folder_path)
                except PermissionError:
                    print("Error: Can't create folder in input project folder.")
                    return
    else:
        os.mkdir(input_hdf5name_folder_path)

    # copy input file to input files folder with suffix triangulated
    all_input_files_abspath_list = glob(input_shapefile_abspath[:-4] + "*")
    all_input_files_files_list = [os.path.basename(file_path) for file_path in all_input_files_abspath_list]
    for i in range(len(all_input_files_files_list)):
        sh_copy(all_input_files_abspath_list[i], os.path.join(input_hdf5name_folder_path, all_input_files_files_list[i]))


def copy_hydrau_input_files(path_filename_source, filename_source_str, hdf5_name, dest_folder_path):
    """
    copy input hydraulic files with indexHYDRAU.txt to input project folder in a folder as input
    (if severeral hydraulic with indexHYDRAU.txt, it will not be erased).
    """
    # create folder with hdf5 name in input project folder
    input_hdf5name_folder_path = os.path.join(dest_folder_path, os.path.splitext(hdf5_name)[0])
    if os.path.exists(input_hdf5name_folder_path):
        try:
            rmtree(input_hdf5name_folder_path)
            os.mkdir(input_hdf5name_folder_path)
        except PermissionError:
            print("Error: Hydraulic input file can be copied to input project folder"
                  " as it is open in another program.")
            try:
                rmtree(input_hdf5name_folder_path)
                os.mkdir(input_hdf5name_folder_path)
            except PermissionError:
                print("Error: Can't create folder in input project folder.")
    else:
        os.mkdir(input_hdf5name_folder_path)

    # get input files and copy them
    for file in filename_source_str.split(", "):
        if not os.path.splitext(file)[1]:  # no ext (ex: rubar20)
            files_to_copy = [x for x in os.listdir(path_filename_source) if file in x]
            for file_to_copy in files_to_copy:
                if not os.path.isdir(os.path.join(path_filename_source, file_to_copy)):
                    sh_copy(os.path.join(path_filename_source, file_to_copy), input_hdf5name_folder_path)
        else:
            sh_copy(os.path.join(path_filename_source, file), input_hdf5name_folder_path)


def copy_files(names, paths, path_input):
    """
    This function copied the input files to the project file. The input files are usually contains in the input
    project file. It is ususally done on a second thread as it might be long.

    For the moment this function cannot send warning and error to the GUI. As input should have been cheked before
    by HABBY, this should not be a problem.

    :param names: the name of the files to be copied (list of string)
    :param paths: the path to these files (list of string)
    :param path_input: the path where to send the input (string)
    """

    if not os.path.isdir(path_input):
        print('Error: Folder not found to copy inputs \n')
        return

    if len(names) != len(paths):
        print('Error: The number of file to be copied is not equal to the number of paths')
        return

    for i in range(0, len(names)):
        if names[i] != 'unknown file':
            src = os.path.join(paths[i], names[i])
            # if the file is too big, the GUI is freezed
            # if os.path.getsize(src) > 200 * 1024 * 1024:
            #     print('Warning: One input file was larger than 200MB and therefore was not copied to the project'
            #           ' folder. It is necessary to copy this file manually to the input folder if one wants to use the '
            #           'restart file or the log file to load this data auomatically again. \n')
            # else:
            if os.path.isfile(src):
                dst = os.path.join(path_input, names[i])
                shutil.copy(src, dst)


def isstranumber(a):
    try:
        float(a)
        bool_a = True
    except:
        bool_a = False
    return bool_a


def sort_homogoeneous_dict_list_by_on_key(dict_to_sort, key, data_type=str):
    if data_type == str:
        indice_sorted = [dict_to_sort[key].index(x) for x in sorted(dict_to_sort[key])]
    elif data_type == float:
        indice_sorted = np.argsort(list(map(float, dict_to_sort[key]))).tolist()

    if list(set(indice_sorted)) == [0]:
        indice_sorted = list(range(len(indice_sorted)))

    for key in dict_to_sort.keys():
        key_list = []
        for ind_num, ind_ind in enumerate(indice_sorted):
            key_list.append(dict_to_sort[key][ind_ind])
        dict_to_sort[key] = key_list
    return dict_to_sort


def txt_file_convert_dot_to_comma(filename_full_path):
    # read and convert
    with open(filename_full_path, 'r') as file:
        text_data_with_comma = file.read().replace('.', ',')
    # write converted
    with open(filename_full_path, 'w') as file:
        file.write(text_data_with_comma)


def frange(start, stop, step):
    i = start
    while i <= stop:
        yield i
        i += step


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def get_all_filename(dirname, ext):
    """
    This function gets the name of all file with a particular extension in a folder. Useful to get all the output
    from one hydraulic model.

    :param dirname: the path to the directory (string)
    :param ext: the extension (.txt for example). It is a string, the point needs to be the first character.
    :return: a list with the filename (filename no dir) for each extension
    """
    filenames = []
    for file in os.listdir(dirname):
        if file.endswith(ext):
            filenames.append(file)
    return filenames

def is_int(val):
    if type(val) == int:
        return True
    else:
        if val.is_integer():
            return True
        else:
            return False

def is_number(n):
    try:
        float(n)  # Type-casting the string to `float`.
        # If string is not a valid `float`,
        # it'll raise `ValueError` exception
    except ValueError:
        return False
    return True


polygon_type_values = (3, 2003, 3003, 0x80000003, -2147483645)  # wkbPolygon, wkbPolygonM, wkbPolygonZM, wkbPolygon25D, wkbPolygon25D
point_type_values = (1, 2001, 3001, 0x80000001, -2147483647)  # wkbPoint, wkbPointM, wkbPointZM, wkbPoint25D, wkbPoint25D