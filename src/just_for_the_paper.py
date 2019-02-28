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
# this module is used to create the image for the paper with the HSI as a function of time, VH for the last time step and
# substrate impact on the result for the last time step

import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon


def save_vh_fig_2d(ikle, coord_p, vh, name_fish, fig, pos, max_lim=1.0):
    """
    This is a function to create 2d image based on a similar function in calcul_hab_mod.py. This is just copied here
    as this version is much more simple
    :param ikle_all:
    :param point_all:
    :param vh_all_t:
    :param name_fish:
    :return:
    """

    print('Start fig')
    ax = fig.add_subplot(2, 2, pos)
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator

    # create the figure for each species, and each time step
    all_patches = []

    # fig, ax = plt.subplots(1)  # new figure
    norm = mpl.colors.Normalize(vmin=0, vmax=max_lim)

    if len(ikle) < 3:
        pass
    else:

        # plot the habitat value
        cmap = plt.get_cmap('coolwarm')
        colors = cmap(vh)
        n = len(vh)
        patches = []
        for i in range(0, n):
            verts = []
            for j in range(0, 3):
                verts_j = coord_p[int(ikle[i][j]), :]
                verts.append(verts_j)
            polygon = Polygon(verts, closed=True, edgecolor='w')
            patches.append(polygon)
            all_patches.append(patches)

        collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
        # collection.set_color(colors) too slow
        collection.set_array(np.array(vh))
        ax.add_collection(collection)
        ax.autoscale_view()
        ax.ticklabel_format(useOffset=False)

        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title(name_fish)
        ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure

        # colorbar
        # Set norm to correspond to the data for which
        # the colorbar will be used.
        # ColorbarBase derives from ScalarMappable and puts a colorbar
        # in a specified axes, so it has everything needed for a
        # standalone colorbar.  There are many more kwargs, but the
        # following gives a basic continuous colorbar with ticks
        # and labels.
        cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
        cb1.set_label('HSI []')

    print('fig done')
    return fig


def main():
    # prep
    path1 = r'D:\Diane_work\presentationInfo\paper1\projetpaper\restart'
    file_grid_base = 'gridcell_t_1_MERGE_Hydro_TELEMAC_a'
    file_point_base = 'xy_t_1_MERGE_Hydro_TELEMAC_a'
    file_vh_base = 'result_t_1_MERGE_Hydro_TELEMAC_a'
    file_hsi_base = 'wua_MERGE_Hydro_TELEMAC_a'
    discharge = [9.2, 21.2, 35, 48.4, 74.7, 110, 150, 175, 259]

    # load grid
    grid_all = []
    for t in range(1, 10):
        grid_all_s = []
        for file in os.listdir(path1):
            if file.endswith(".txt"):
                if file[:len(file_grid_base) + 1] == file_grid_base + str(t):
                    # work only with one reach
                    grid_here = np.loadtxt(os.path.join(path1, file), skiprows=2)

                    grid_all_s.append(grid_here[:, 1:])  # no need for the reach
        grid_all.append(grid_all_s)
    grid_all = np.array(grid_all)
    print(grid_all.shape)

    print('grid loaded')

    # load point
    point_all = []
    for t in range(1, 10):
        point_all_s = []
        for file in os.listdir(path1):
            if file.endswith(".txt"):
                if file[:len(file_point_base) + 1] == file_point_base + str(t):
                    # work only with one reach
                    point_here = np.loadtxt(os.path.join(path1, file), skiprows=2)
                    point_all_s.append(point_here[:, 1:])  # no need for the reach
        point_all.append(point_all_s)
    point_all = np.array(point_all)
    print(point_all.shape)
    print('point loaded')

    # load VH by cell
    vh_all = []
    for t in range(1, 10):
        vh_all_s = []
        for file in os.listdir(path1):
            if file.endswith(".txt"):
                if file[:len(file_vh_base) + 1] == file_vh_base + str(t):
                    # work only with one reach
                    vh_here = np.loadtxt(os.path.join(path1, file), skiprows=3)
                    vh_all_s.append(vh_here[:, 6:])  # no need for the reach
        vh_all.append(vh_all_s)
    # vh_all = np.array(vh_all)
    # print(vh_all.shape)

    print('habitat value loaded')

    # load HSI
    hsi_all = []
    for t in range(1, 10):
        hsi_all_s = []
        for file in os.listdir(path1):
            if file.endswith(".txt"):
                if file[:len(file_hsi_base) + 1] == file_hsi_base + str(t):
                    # work only with one reach
                    hsi_here = np.loadtxt(os.path.join(path1, file), skiprows=3)
                    hsi_all_s.append(hsi_here[3:])  # no need for the reach
        hsi_all.append(hsi_all_s)
    hsi_all = np.array(hsi_all)

    # plot all
    fig = plt.figure()

    # plot hsi
    colo = ['^-g', '^-g', '^-g', '^-g', '^-b', '^-m', '^-r', '^-k']
    labelleg = ['Clay/Silt/Sand', '', '', 'Gravel', 'Pebble', 'Cobble', 'Small boulders', 'Large boulders']
    fig.add_subplot(311)
    for s in range(0, 8):
        if s != 1 or s != 2:
            plt.plot(discharge, hsi_all[:, s, 1], colo[s], label=labelleg[s])
    plt.ylabel('HSI Fry []')
    # plt.xlabel('Discharge [m$^{3}$/s]')
    plt.ylim([0, 0.4])
    plt.xlim([0, 280])
    plt.title('Habitat Suitability Index')
    leg = plt.legend(fontsize=10, loc=1, fancybox=True, ncol=2)
    leg.get_frame().set_alpha(0.5)
    fig.add_subplot(312)
    for s in range(0, 8):
        if s != 1 or s != 2:
            plt.plot(discharge, hsi_all[:, s, 3], colo[s])
    plt.ylabel('HSI Juvenile []')
    # plt.title('Habitat Suitability Index')
    # plt.xlabel('Discharge [m$^{3}$/s]')
    plt.ylim([0, 0.4])
    plt.xlim([0, 280])
    fig.add_subplot(313)
    for s in range(0, 8):
        if s != 1 or s != 2:
            plt.plot(discharge, hsi_all[:, s, 5], colo[s])
    plt.ylabel('HSI Adult []')
    # plt.title('Habitat Suitability Index')
    plt.xlabel('Discharge [m$^{3}$/s]')
    plt.ylim([0, 0.4])
    plt.xlim([0, 280])
    plt.tight_layout()

    # plot HSI last time step, pebble substrate
    # fig = plt.figure()
    # vh_here =  vh_all[0][4]
    # fig = save_vh_fig_2d(grid_all[0, 0], point_all[0,0],vh_here[:,0], 'Habitat value - Fry - Q=9.2m$^3$/s', fig, 2)
    # fig = save_vh_fig_2d(grid_all[0, 0], point_all[0, 0], vh_here[:, 1], 'Habitat value - Juvenile- Q=9.2m$^3$/s', fig, 5)
    # fig = save_vh_fig_2d(grid_all[0, 0], point_all[0, 0], vh_here[:, 2], 'Habitat value - Adult- Q=9.2m$^3$/s', fig, 8)
    #
    # # plot HSI fist  time step
    # vh_here = vh_all[-1][4]
    # fig = save_vh_fig_2d(grid_all[-1, 0], point_all[-1, 0], vh_here[:, 0], 'Habitat value - Fry- Q=259m$^3$/s', fig, 3)
    # fig = save_vh_fig_2d(grid_all[-1, 0], point_all[-1, 0], vh_here[:, 1], 'Habitat value - Juvenile- Q=259m$^3$/s', fig, 6)
    # fig = save_vh_fig_2d(grid_all[-1, 0], point_all[-1, 0], vh_here[:, 2], 'Habitat value - Adult- Q=259m$^3$/s', fig, 9)

    # plot HV for different time step
    fig = plt.figure()
    vh_here = vh_all[0][4]
    fig = save_vh_fig_2d(grid_all[0, 0], point_all[0, 0], vh_here[:, 2], 'Habitat value - Q=9.2m$^3$/s', fig, 1, 0.5)
    vh_here = vh_all[2][4]
    fig = save_vh_fig_2d(grid_all[2, 0], point_all[2, 0], vh_here[:, 2], 'Habitat value - Q=35m$^3$/s', fig, 2, 0.5)
    vh_here = vh_all[5][4]
    fig = save_vh_fig_2d(grid_all[5, 0], point_all[5, 0], vh_here[:, 2], 'Habitat value - Q=110m$^3$/s', fig, 3, 0.5)
    vh_here = vh_all[-1][4]
    fig = save_vh_fig_2d(grid_all[-1, 0], point_all[-1, 0], vh_here[:, 2], 'Habitat value - Q=259m$^3$/s', fig, 4, 0.5)

    # #plot diff substrate last time step
    # vh1 = []
    # vh2 = []
    # vh3 = []
    # for i in range(0,8):
    #     vh1.append(vh_all[-1][i][:, 0])
    #     vh2.append(vh_all[-1][i][:, 1])
    #     vh3.append(vh_all[-1][i][:, 2])
    #
    #
    # diff1 = np.max(vh1, axis=0) - np.min(vh1, axis=0)
    # diff2 = np.max(vh2, axis=0) - np.min(vh2, axis=0)
    # diff3 = np.max(vh3, axis=0) - np.min(vh3, axis=0)
    #
    # fig = save_vh_fig_2d(grid_all[-1, 5], point_all[-1, 5], diff1, 'Substrate influence - Fry', fig, 3, 0.5)
    # fig = save_vh_fig_2d(grid_all[-1, 5], point_all[-1, 5], diff2, 'Substrate influence - Juvenile', fig, 6, 0.5)
    # fig = save_vh_fig_2d(grid_all[-1, 5], point_all[-1, 5], diff3, 'Substrate influence - Adult', fig, 9, 0.5)

    # plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
