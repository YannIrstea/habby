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
import cProfile
import pstats
import io
import sys

from src.user_preferences_mod import user_preferences


def profileit(func):
    """ Decorator to analyse computational time funtion. Output txt file created in temp folder in user AppData folder.
    For developper, if used (import of this decorator),
    it will recreate/reimport the class and recreate AppData structure. """
    def wrapper(*args, **kwargs):
        path_stat = user_preferences.user_pref_temp_path
        datafn = func.__name__ + ".txt"  # Name the data file sensibly
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(prof, stream=s).sort_stats(sortby)
        ps.print_stats()
        with open(os.path.join(path_stat, datafn), 'w') as perf_file:
            perf_file.write(s.getvalue())
        return retval

    return wrapper


def check_data_2d_dict_size(func):
    def wrapper(*args, **kwargs):
        # before decorated function

        # run decorated function
        data_2d, description_from_file = func(*args)

        # after decorated function
        print_data_2d_size(data_2d)

        return data_2d, description_from_file
    return wrapper


def print_data_2d_size(data_2d):
    # ['mesh', 'node']
    sys.stdout = sys.__stdout__
    for key1 in data_2d.keys():
        for key2 in data_2d[key1].keys():
            # 'data' key
            if type(data_2d[key1][key2]) == dict:
                for key3 in data_2d[key1][key2].keys():
                    print("text3")
                    text3 = key3 + " : " + \
                          str(len(data_2d[key1][key2][key3])) + " reach, " + \
                          str(len(data_2d[key1][key2][key3][0])) + " unit "
                    if len(data_2d[key1][key2][key3][0]) > 1:
                        text3 = text3 + str(len(data_2d[key1][key2][key3][0][0])) + " " + key1 + " " + \
                          str(data_2d[key1][key2][key3][0][0].shape) + \
                          str(data_2d[key1][key2][key3][0][0].dtype)
                    print(text3)
            # tin, xy, z dataset
            if type(data_2d[key1][key2]) == list:
                print("text2")
                text2 = key2 + " : " + \
                       str(len(data_2d[key1][key2])) + " reach, " + \
                       str(len(data_2d[key1][key2][0])) + " unit "
                if len(data_2d[key1][key2][0]) > 1:
                    text2 = text2 + str(len(data_2d[key1][key2][0][0])) + " " + key1 + " " + \
                           str(data_2d[key1][key2][0][0].shape) + \
                           str(data_2d[key1][key2][0][0].dtype)
                print(text2)