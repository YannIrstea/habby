import os
import re
import numpy as np
import matplotlib.pyplot as plt
from src import load_hdf5


def load_evha_curve(filename, path):
    """
    This function is used to load the preference curve in the EVHA form . It will be useful to create xml preference
    file, but it is not used direclty by HABBY. This function does not have much control on user input as it is planned
    to be used only by people working on HABBY. The order of the data in the file must be height, velocity, substrate

    :param filename: the name of file containing the preference curve for EVHA
    :param path: the path to this file
    :return: preference for height, vel, sub in a list of list form, name of the fish, code, stade and description
    """

    # load text file
    filename_path = os.path.join(path, filename)
    with open(filename_path, 'rt') as f:
        data = f.read()

    # general info
    exp_reg1 = "\s*(\w\w\w?)\s+(.+)\n"
    re_res = re.findall(exp_reg1, data)[0]
    code_fish = re_res[0]
    name_fish = re_res[1]

    exp_reg2 = "\n(.+)\$(\d)(.+)"
    re_res = re.findall(exp_reg2, data, re.DOTALL)[0]
    descri = re_res[0]
    descri = descri.replace('\n\n\n', '\n')
    descri = descri.replace('\n\n', '\n')
    nb_stade = int(re_res[1])
    data_num = re_res[2]
    data_num = data_num.split('\n')

    # name of stade (ADU, JUV, etc)
    stade = data_num[0]
    stade = stade.strip()
    stade = stade.split()
    if len(stade) != nb_stade:
        print('Error: number of stade are not coherent')
        return

    # height, velocity, substrate
    height = []
    vel = []
    sub = []
    first_point = True
    data_num = data_num[1:]
    new_data1old = -1
    pref_here = []
    for s in range(0, nb_stade):
        ind_hvs = 0
        for l in range(0, len(data_num)):
            data_l = data_num[l]
            data_l = data_l.strip()
            data_l = data_l.split()
            if len(data_l) > 1:  # empty lines
                try:
                    new_data1 = np.float(data_l[2 * s])
                    new_data2 = np.float(data_l[2 * s + 1])
                except ValueError:
                    print('not a float')
                    return
                if new_data1old <= new_data1:
                    new_data1old = new_data1
                    if first_point:
                        pref_here = [[new_data1], [new_data2]]
                        first_point = False
                    else:
                        pref_here[0].extend([new_data1])
                        pref_here[1].extend([new_data2])
                else: # go from height to velocity
                    if ind_hvs == 0:
                        height.append(pref_here)
                    if ind_hvs == 1:
                        vel.append(pref_here)
                    ind_hvs += 1
                    pref_here = []
                    first_point = True
                    new_data1old = -1
        # go from velcoity to substrate
        sub.append(pref_here)

    return height, vel, sub, code_fish, name_fish, stade, descri


def figure_pref(height, vel, sub, code_fish, name_fish, stade):
    """
    This function is used to plot the preference curves.

    :param height: the height preference data (list of list)
    :param vel: the height preference data (list of list)
    :param sub: the height preference data (list of list)
    :param code_fish: the three letter code which indiate which fish species is analyzed
    :param name_fish: the name of the fish analyzed
    :param stade: the name of the stade analyzed (ADU, JUV, ...)
    """

    if len(stade)> 1:  # if you take this out, the commande axarr[x,x] does not work as axarr is only 1D
        f, axarr = plt.subplots(len(stade),3, sharey='row')
        plt.suptitle('Preference curve of ' + name_fish + ' (' + code_fish + ') ')
        for s in range(0, len(stade)):
            axarr[s, 0].plot(height[s][0], height[s][1], 'b')
            axarr[s, 0].set_xlabel('Water height [m]')
            axarr[s, 0].set_ylabel('Coeff. Pref ' + stade[s])
            axarr[s, 0].set_ylim([0,1.1])

            axarr[s, 1].plot(vel[s][0], vel[s][1], 'r')
            axarr[s, 1].set_xlabel('Velocity [m/sec]')
            axarr[s, 1].set_ylabel('Coeff. Pref ' + stade[s])
            axarr[s, 1].set_ylim([0, 1.1])

            axarr[s, 2].plot(sub[s][0], sub[s][1], 'k')
            axarr[s, 2].set_xlabel('Substrate []')
            axarr[s, 2].set_ylabel('Coeff. Pref ' + stade[s])
            axarr[s, 2].set_ylim([0, 1.1])
    else:
        f, axarr = plt.subplots(3, 1, sharey='row')
        plt.suptitle('Preference curve of ' + name_fish + ' (' + code_fish + ') ')
        axarr[0].plot(height[0][0], height[0][1], 'b')
        axarr[0].set_xlabel('Water height [m]')
        axarr[0].set_ylabel('Coeff. Pref ' + stade[0])
        axarr[0].set_ylim([0, 1.1])

        axarr[1].plot(vel[0][0], vel[0][1], 'r')
        axarr[1].set_xlabel('Velocity [m/sec]')
        axarr[1].set_ylim([0, 1.1])

        axarr[2].plot(sub[0][0], sub[0][1], 'k')
        axarr[2].set_xlabel('Substrate []')
        axarr[2].set_ylabel('Coeff. Pref ' + stade[0])
        axarr[2].set_ylim([0, 1.1])


def create_database(path_bio):
    """
    This function checks all xml files in the folder indicated by path_bio. If a change is detected, it create a new
    sqlite database. The goal of creating a database is to avoid freezing the GUI when info on the preference curve are
    asked. So it is possible to select one curve and have information without seeing too much of a delay.

    :param path_bio:
    """

    # get last changed time from Qsettings

    # check last changed time

    # if different

    # erase database

    # create new database




def main():
    """
    Used to test the module on the biological preference
    """
    path = r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF-part1-Multispe1998'
    path = r'D:\Diane_work\pref_curve\EVHA\CourbesPref1\PREF-part2-Lamourouxetal1999'
    filenames = load_hdf5.get_all_filename(path, '.PRF')
    for i in range(0, len(filenames)):
        [height, vel, sub, code_fish, name_fish, stade, descri] = load_evha_curve(filenames[i], path)
        figure_pref(height, vel, sub, code_fish, name_fish, stade)
    plt.show()

if __name__ == '__main__':
    main()