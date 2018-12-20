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
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import mplcursors
import time
import os
from src_GUI import output_fig_GUI
from src import calcul_hab


def plot_map_height(state, point_all_reach, ikle_all, fig_opt, name_hdf5, inter_h_all=[], path_im=[], time_step=0):
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    # plot the grid
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = fig_opt['erase_id']
    types_plot = fig_opt['type_plot']
    if erase1 == 'True':  # xml in text
        erase1 = True
    else:
        erase1 = False

    # title and filename
    if fig_opt['language'] == 0:
        title = name_hdf5[:-3] + " : " + 'Water depth - Time Step: ' + str(time_step)
        filename = name_hdf5[:-3] + "_height_" + str(time_step)
    elif fig_opt['language'] == 1:
        title = name_hdf5[:-3] + " : " + "Hauteur d'eau - Pas de Temps: " + str(time_step)
        filename = name_hdf5[:-3] + "_hauteur_" + str(time_step)
    else:
        title = name_hdf5[:-3] + " : " + "Hauteur d'eau - Pas de Temps: " + str(time_step)
        filename = name_hdf5[:-3] + "_height_" + str(time_step)

    # plot the interpolated height
    if len(inter_h_all) > 0:  # 0
        # plt.subplot(2, 1, 2) # nb_fig, nb_fig, position
        plt.figure(filename)
        plt.ticklabel_format(useOffset=False)
        plt.axis('equal')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title(title)
        # color map (the same for al reach)
        mvc = 0.001
        cm = plt.cm.get_cmap(fig_opt['color_map2'])
        for r in range(0, len(inter_h_all)):
            inter_h = inter_h_all[r]
            if len(inter_h) > 0:
                mv = max(inter_h)
                # mv = np.mean(inter_h[inter_h >= 0]) * 2
                if mv > mvc:
                    mvc = mv
        bounds = np.linspace(0, mvc, 15)
        for r in range(0, len(inter_h_all)):
            point_here = np.array(point_all_reach[r])
            inter_h = inter_h_all[r]
            if len(point_here) == len(inter_h) and len(ikle_all[r]) > 2:
                inter_h[inter_h < 0] = 0
                sc = plt.tricontourf(point_here[:, 0], point_here[:, 1], ikle_all[r], inter_h, cmap=cm,
                                     vmin=0, vmax=mvc, levels=bounds,
                                     extend='both')
                if r == len(inter_h_all) - 1:  # end of loop
                    cbar = plt.colorbar(sc)
                    if fig_opt['language'] == 0:
                        cbar.ax.set_ylabel('Water depth [m]')
                    elif fig_opt['language'] == 1:
                        cbar.ax.set_ylabel("Hauteur d'eau [m]")
                    else:
                        cbar.ax.set_ylabel('Water depth [m]')
            else:
                print('Warning: The river is dry for one time step. The figure created will be empty.\n\n')

        # save figure
        plt.tight_layout()  # remove margin out of plot
        if types_plot == "export" or types_plot == "both":
            if not erase1:
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=fig_opt['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=fig_opt['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=fig_opt['resolution'], transparent=True)
            else:
                test = calcul_hab.remove_image(name_hdf5[:-3] + "_height", path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + ".png"), dpi=fig_opt['resolution'],
                                transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=fig_opt['resolution'],
                                transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=fig_opt['resolution'],
                                transparent=True)

        # output for plot_GUI
        state.value = 1  # process finished
        if types_plot == "display" or types_plot == "both":
            fm = plt.get_current_fig_manager()
            fm.window.showMinimized()
            plt.show()
        if types_plot == "export":
            plt.close()


def plot_map_velocity(state, point_all_reach, ikle_all, fig_opt, name_hdf5, inter_vel_all=[], path_im=[], time_step=0):
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    # plot the grid
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = fig_opt['erase_id']
    types_plot = fig_opt['type_plot']
    if erase1 == 'True':  # xml in text
        erase1 = True
    else:
        erase1 = False

    # title and filename
    if fig_opt['language'] == 0:
        title = name_hdf5[:-3] + " : " + 'Velocity - Time Step: ' + str(time_step)
        filename = name_hdf5[:-3] + "_velocity_" + str(time_step)
    elif fig_opt['language'] == 1:
        title = name_hdf5[:-3] + " : " + 'Vitesse - Pas de Temps: ' + str(time_step)
        filename = name_hdf5[:-3] + "_vitesse_" + str(time_step)
    else:
        title = name_hdf5[:-3] + " : " + 'Velocity - Time Step: ' + str(time_step)
        filename = name_hdf5[:-3] + "_velocity_" + str(time_step)

    # plot
    if len(inter_vel_all) > 0:  # 0
        plt.figure(filename)
        plt.ticklabel_format(useOffset=False)
        plt.axis('equal')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title(title)
        # plt.subplot(2, 1, 1)
        # get colormap limit
        cm = plt.cm.get_cmap(fig_opt['color_map1'])
        mvc = 0.001
        for r in range(0, len(inter_vel_all)):
            inter_vel = inter_vel_all[r]
            if len(inter_vel) > 0:
                mv = max(inter_vel)
                if mv > mvc:
                    mvc = mv
        bounds = np.linspace(0, mvc, 15)
        # do the figure for all reach
        for r in range(0, len(inter_vel_all)):
            point_here = np.array(point_all_reach[r])
            inter_vel = inter_vel_all[r]
            if len(point_here[:, 1]) == len(inter_vel) and len(ikle_all[r]) > 2:
                sc = plt.tricontourf(point_here[:, 0], point_here[:, 1],
                                     ikle_all[r], inter_vel, cmap=cm,
                                     levels=bounds, extend='both')
                if r == len(inter_vel_all) - 1:
                    # plt.clim(0, np.nanmax(inter_vel))
                    cbar = plt.colorbar(sc)
                    if fig_opt['language'] == 0:
                        cbar.ax.set_ylabel('Velocity [m/sec]')
                    elif fig_opt['language'] == 1:
                        cbar.ax.set_ylabel('Vitesse [m/sec]')
                    else:
                        cbar.ax.set_ylabel('Velocity [m/sec]')
            else:
                print('Warning: The river is dry for one time step. The figure created will be empty.\n\n')

        # save figure
        plt.tight_layout()  # remove margin out of plot
        if types_plot == "export" or types_plot == "both":
            if not erase1:
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=fig_opt['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=fig_opt['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=fig_opt['resolution'], transparent=True)
            else:
                test = calcul_hab.remove_image(filename, path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + ".png"), dpi=fig_opt['resolution'],
                                transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=fig_opt['resolution'],
                                transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=fig_opt['resolution'],
                                transparent=True)
        # output for plot_GUI
        state.value = 1  # process finished
        if types_plot == "display" or types_plot == "both":
            fm = plt.get_current_fig_manager()
            fm.window.showMinimized()
            plt.show()
        if types_plot == "export":
            plt.close()


def plot_map_mesh(state, point_all_reach, ikle_all, fig_opt, name_hdf5, path_im=[], time_step=0):
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    # plot the grid
    plt.rcParams[
        'agg.path.chunksize'] = 10000  # due to "OverflowError: Exceeded cell block limit (set 'agg.path.chunksize' rcparam)" with savefig mesh png big file
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = fig_opt['erase_id']
    types_plot = fig_opt['type_plot']
    if erase1 == 'True':  # xml in text
        erase1 = True
    else:
        erase1 = False

    # title and filename
    if fig_opt['language'] == 0:
        title = name_hdf5[:-3] + " : " + 'Computational Grid - Time Step ' + str(time_step)
        filename = name_hdf5[:-3] + "_mesh_" + str(time_step)
    elif fig_opt['language'] == 1:
        title = name_hdf5[:-3] + " : " + 'Maillage - Pas de Temps: ' + str(time_step)
        filename = name_hdf5[:-3] + "_maillage_" + str(time_step)
    else:
        title = name_hdf5[:-3] + " : " + 'Computational Grid - Time Step ' + str(time_step)
        filename = name_hdf5[:-3] + "_mesh_" + str(time_step)

    # plot
    plt.figure(filename)
    # the grid
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    plt.axis('equal')
    for r in range(0, len(ikle_all)):
        # get data for this reach
        ikle = ikle_all[r]
        coord_p = point_all_reach[r]

        # prepare the grid
        if ikle is not None:  # case empty grid
            xlist = []
            ylist = []
            for i in range(0, len(ikle)):
                pi = 0
                ikle_i = ikle[i]
                if len(ikle_i) == 3:
                    while pi < 2:  # we have all sort of xells, max eight sides
                        # The conditions should be tested in this order to avoid to go out of the array
                        p = ikle_i[pi]  # we start at 0 in python, careful about -1 or not
                        p2 = ikle_i[pi + 1]
                        xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
                        xlist.append(None)
                        ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
                        ylist.append(None)
                        pi += 1

                    p = ikle_i[pi]
                    p2 = ikle_i[0]
                    xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
                    xlist.append(None)
                    ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
                    ylist.append(None)

            plt.plot(xlist, ylist, '-b', linewidth=0.1)
            plt.ticklabel_format(useOffset=False)
            # to add water value on grid point (usualy to debug)
            # for idx, c in enumerate(coord_p):
            #     plt.annotate(str(inter_h_all[r][idx]),c)

    # save figures
    plt.tight_layout()  # remove margin out of plot
    if types_plot == "export" or types_plot == "both":
        if not erase1:
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=fig_opt['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=fig_opt['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=fig_opt['resolution'], transparent=True)
        else:
            test = calcul_hab.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:  # [0,1,2,3,4,5] currently existing format
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=fig_opt['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=fig_opt['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=fig_opt['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "display" or types_plot == "both":
        fm = plt.get_current_fig_manager()
        fm.window.showMinimized()
        plt.show()
    if types_plot == "export":
        plt.close()


def plot_map_substrate(state, coord_p, ikle, sub_pg, sub_dom, path_im, name_hdf5, fig_opt={}, time_step=0.0, xtxt=[-99],
                       ytxt=[-99], subtxt=[-99],
                       reach_num=-99):
    """
    The function to plot the substrate data, which was loaded before. This function will only work if the substrate
    data is given using the cemagref code.

    :param coord_p: the coordinate of the point
    :param ikle: the connectivity table
    :param sub_pg: the information on subtrate by element for the "coarser part"
    :param sub_dom: the information on subtrate by element for the "dominant part"
    :param fig_opt: the figure option as a doctionnary
    :param xtxt: if the data was given in txt form, the orignal x data
    :param ytxt: if the data was given in txt form, the orignal y data
    :param subtxt: if the data was given in txt form, the orignal sub data
    :param path_im: the path where to save the figure
    :param reach_num: If we plot more than one reach, this is the reach number
    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    types_plot = fig_opt['type_plot']
    erase1 = fig_opt['erase_id']
    if erase1 == 'True':  # xml in text
        erase1 = True
    else:
        erase1 = False

    if fig_opt['language'] == 0:
        title_pg = 'Substrate Grid - Coarser Data - Time Step ' + str(time_step)
        title_dom = 'Substrate Grid - Dominant - Time Step ' + str(time_step)
        filename_pg_dm = name_hdf5[:-3] + "_substrate_" + str(time_step)
    elif fig_opt['language'] == 1:
        title_pg = 'Maillaige substrat - Plus Gros - Time Step ' + str(time_step)
        title_dom = 'Maillaige substrat - Dominant - Time Step ' + str(time_step)
        filename_pg_dm = name_hdf5[:-3] + "_substrate_" + str(time_step)
    else:
        title_pg = 'Substrate Grid - Coarser Data - Time Step ' + str(time_step)
        title_dom = 'Substrate Grid - Dominant - Time Step ' + str(time_step)
        filename_pg_dm = name_hdf5[:-3] + "_substrate_" + str(time_step)

    # prepare grid (to optimize)
    xlist = []
    ylist = []
    coord_p = np.array(coord_p)
    for i in range(0, len(ikle)):
        pi = 0
        while pi < len(ikle[i]) - 1:  # we have all sort of xells, max eight sides
            p = int(ikle[i][pi])  # we start at 0 in python, careful about -1 or not
            p2 = int(ikle[i][pi + 1])
            xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
            xlist.append(None)
            ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
            ylist.append(None)
            pi += 1

        p = int(ikle[i][pi])
        p2 = int(ikle[i][0])
        xlist.extend([coord_p[p, 0], coord_p[p2, 0]])
        xlist.append(None)
        ylist.extend([coord_p[p, 1], coord_p[p2, 1]])
        ylist.append(None)

    # substrate coarser
    fig = plt.figure(name_hdf5[:-3])
    sub1 = fig.add_subplot(211)
    patches = []
    cmap = plt.get_cmap(fig_opt['color_map1'])
    plt.axis('equal')
    colors_val = np.array(sub_pg)  # convert nfloors to colors that we can use later (cemagref)
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    norm = mpl.colors.Normalize(vmin=1, vmax=8)
    n = len(sub_pg)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True, edgecolor='w')
        patches.append(polygon)
    collection = PatchCollection(patches, linewidth=0.0, cmap=cmap, norm=norm)
    sub1.add_collection(collection)
    # collection.set_color(colors)
    collection.set_array(colors_val)
    sub1.autoscale_view()
    # sub1.plot(xlist, ylist, c='b', linewidth=0.2)
    # plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title_pg)

    # substrate dominant
    sub2 = fig.add_subplot(212)
    patches = []
    colors_val = np.array(sub_dom)  # convert nfloors to colors that we can use later
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    norm = mpl.colors.Normalize(vmin=1, vmax=8)
    n = len(sub_dom)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    collection = PatchCollection(patches, linewidth=0.0, cmap=cmap, norm=norm)
    sub2.add_collection(collection)
    collection.set_array(colors_val)
    sub2.autoscale_view()
    plt.axis('equal')
    # cbar = plt.colorbar()
    # cbar.ax.set_ylabel('Substrate')
    # sub2.plot(xlist, ylist, c='b', linewidth=0.2)
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title_dom)

    # colorbar
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure
    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
    cb1.set_label('Code Cemagref')
    # plt.tight_layout()

    # save the figure
    if types_plot == "export" or types_plot == "both":
        if not erase1:
            if format == 0 or format == 1:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.png'), dpi=fig_opt['resolution'], transparent=True)
            if format == 0 or format == 3:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.pdf'), dpi=fig_opt['resolution'], transparent=True)
            if format == 2:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.jpg'), dpi=fig_opt['resolution'], transparent=True)
        else:
            test = calcul_hab.remove_image("substrate_coars_dom", path_im, format)
            if not test:
                return
            if format == 0 or format == 1:
                plt.savefig(os.path.join(path_im, filename_pg_dm + ".png"), dpi=fig_opt['resolution'], transparent=True)
            if format == 0 or format == 3:
                plt.savefig(os.path.join(path_im, filename_pg_dm + ".pdf"), dpi=fig_opt['resolution'], transparent=True)
            if format == 2:
                plt.savefig(os.path.join(path_im, filename_pg_dm + ".jpg"), dpi=fig_opt['resolution'], transparent=True)

    # if we start with txt data, plot the original data
    # not done usually, but we let it here to debug
    if xtxt != [-99]:
        plt.figure()
        subtxt = list(map(float, subtxt))
        # size of the marker (to avoid having to pale, unclear figure)
        # this is a rough estimation, no need for precise number here
        d1 = 0.5 * np.sqrt((xtxt[1] - xtxt[0]) ** 2 + (ytxt[1] - xtxt[1]) ** 2)  # dist in coordinate
        dist_data = np.mean([np.max(xtxt) - np.min(xtxt), np.max(ytxt) - np.min(ytxt)])
        f_len = 5 * 72  # point is 1/72 inch, figure is 5 inch large
        transf = f_len / dist_data
        s1 = 3.1 * (d1 * transf) ** 2 / 2  # markersize is given as an area

        cm = plt.cm.get_cmap('gist_rainbow')
        sc = plt.scatter(xtxt, ytxt, c=subtxt, vmin=np.nanmin(subtxt), vmax=np.nanmax(subtxt), s=34, cmap=cm,
                         edgecolors='none')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        if fig_opt['language'] == 0:
            plt.title('Original Substrate Data (x,y)')
        elif fig_opt['language'] == 1:
            plt.title('Données Substrat Original (x,y)')
        else:
            plt.title('Original Substrate Data (x,y)')
        if types_plot == "export" or types_plot == "both":
            if not erase1:
                plt.savefig(os.path.join(path_im, "substrate_txtdata" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.png'),
                            fig_opt['resolution'], transparent=True)
                plt.savefig(os.path.join(path_im, "substrate_txtdata" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.pdf'),
                            fig_opt['resolution'], transparent=True)
            else:
                test = calcul_hab.remove_image("substrate_txtdata", path_im, format)
                if not test:
                    return
                plt.savefig(os.path.join(path_im, "substrate_txtdata.png"), fig_opt['resolution'], transparent=True)
                plt.savefig(os.path.join(path_im, "substrate_txtdata.pdf"), fig_opt['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "display" or types_plot == "both":
        fm = plt.get_current_fig_manager()
        fm.window.showMinimized()
        plt.show()
    if types_plot == "export":
        plt.close()


def plot_map_fish_habitat(state, fish_name, coord_p, ikle, vh, name_hdf5, fig_opt={}, path_im=[], time_step=0):
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator
    types_plot = fig_opt['type_plot']
    erase1 = fig_opt['erase_id']
    if erase1 == 'True':  # xml in text
        erase1 = True
    else:
        erase1 = False

    # title and filename
    if fig_opt['language'] == 0:
        title = 'Habitat Value of ' + fish_name + ' - Computational Step: ' + time_step
        filename = name_hdf5[:-3] + '_HSI_' + fish_name + '_' + str(time_step)
    elif fig_opt['language'] == 1:
        title = "Valeur d'Habitat pour " + fish_name + '- Pas de temps/débit: ' + time_step
        filename = name_hdf5[:-3] + "_VH_" + fish_name + '_' + str(time_step)
    else:
        title = 'Habitat Value of ' + fish_name + '- Computational Step: ' + time_step
        filename = name_hdf5[:-3] + '_HSI_' + fish_name + '_' + str(time_step)

    # preplot
    fig = plt.figure(filename)
    ax = plt.axes()
    # fig, ax = plt.subplots(1)  # new figure
    norm = mpl.colors.Normalize(vmin=0, vmax=1)

    # plot the habitat value
    cmap = plt.get_cmap(fig_opt['color_map2'])
    # colors = cmap(vh.tolist())

    n = len(vh)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True, edgecolor='w')
        patches.append(polygon)

    collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    # collection.set_color(colors) too slow
    collection.set_array(vh)
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.ticklabel_format(useOffset=False)
    plt.axis('equal')
    # cbar = plt.colorbar()
    # cbar.ax.set_ylabel('Substrate')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
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
    if fig_opt['language'] == 0:
        cb1.set_label('HV []')
    elif fig_opt['language'] == 1:
        cb1.set_label('VH []')
    else:
        cb1.set_label('HV []')

    # save figure
    if types_plot == "export" or types_plot == "both":
        if not erase1:
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=fig_opt['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=fig_opt['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=fig_opt['resolution'], transparent=True)
        else:
            test = calcul_hab.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=fig_opt['resolution'],
                            transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=fig_opt['resolution'],
                            transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=fig_opt['resolution'],
                            transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "display" or types_plot == "both":
        fm = plt.get_current_fig_manager()
        fm.window.showMinimized()
        plt.show()
    if types_plot == "export":
        plt.close()


def plot_fish_hv_wua(state, area_all, spu_all, name_fish, path_im, name_base, fig_opt={}, sim_name=[]):
    """
    This function creates the figure of the spu as a function of time for each reach. if there is only one
    time step, it reverse to a bar plot. Otherwise it is a line plot.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_im: the path where to save the image
    :param fig_opt: the dictionnary with the figure options
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the time steps if not 0,1,2,3
    """

    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    if fig_opt['font_size'] > 7:
        plt.rcParams['legend.fontsize'] = fig_opt['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if fig_opt['marker'] == 'True':
        mar = 'o'
    else:
        mar = None
    erase1 = fig_opt['erase_id']
    types_plot = fig_opt['type_plot']
    if erase1 == 'True':  # xml in text
        erase_id = True
    else:
        erase_id = False

    # prep data
    name_base = name_base[:-3]

    # plot
    if len(sim_name) == 1:
        plot_window_title = f"Habitat Value and Weighted Usable Area - Computational Step : {sim_name[0]}"
    if len(sim_name) > 1:
        plot_window_title = f"Habitat Value and Weighted Usable Area - Computational Steps : " + ", ".join(
            map(str, sim_name))
    fig = plt.figure(plot_window_title)

    if len(spu_all) != len(name_fish):
        print('Error: Number of fish name and number of WUA data is not coherent \n')
        return

    try:
        nb_reach = len(max(area_all, key=len))  # we might have failed time step
    except TypeError:  # or all failed time steps -99
        # print('Error: No reach found. Is the hdf5 corrupted? \n')
        return

    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    if sim_name and len(area_all) - 1 != len(sim_name):
        sim_name = []

    # one time step - bar
    if len(area_all) == 1 or len(area_all) == 2:
        for r in range(0, nb_reach):
            # SPU
            data_bar = []
            for s in range(0, len(name_fish)):
                data_bar.append(spu_all[s][1][r])
            y_pos = np.arange(len(spu_all))
            if r > 0:
                fig = plt.figure()
            fig.add_subplot(211)
            if data_bar:
                #spu_string = '{:0.0f}'.format(data_bar[0])
                data_bar2 = np.array(data_bar)
                plt.bar(y_pos, data_bar2, 0.5)
                #plt.text(x=y_pos, y=data_bar2 / 2, s=spu_string + " m²", horizontalalignment='left')
                plt.xticks(y_pos + 0.25, name_fish)
            if fig_opt['language'] == 0:
                plt.ylabel('WUA [m^2]')
            elif fig_opt['language'] == 1:
                plt.ylabel('SPU [m^2]')
            else:
                plt.ylabel('WUA [m^2]')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            if fig_opt['language'] == 0:
                plt.title(f'Weighted Usable Area - Computational Step : {sim_name[0]}')
            elif fig_opt['language'] == 1:
                plt.title(f'Surface Ponderée Utile - unité : {sim_name[0]}')
            else:
                plt.title(f'Weighted Usable Area - Computational Step : {sim_name[0]}')
            # VH
            fig.add_subplot(212)
            if data_bar:
                area = area_all[-1][r]
                vh = np.array(data_bar[0] / area)
                #vh_string = '{:0.2f}'.format(vh)
                plt.bar(y_pos, vh, 0.5)
                #plt.text(x=y_pos, y=0.5, s=vh_string, horizontalalignment='left')
                plt.xticks(y_pos + 0.25, name_fish)
            if fig_opt['language'] == 0:
                plt.ylabel('HV (WUA/A) []')
            elif fig_opt['language'] == 1:
                plt.ylabel('VH (SPU/A) []')
            else:
                plt.ylabel('HV (WUA/A) []')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            plt.ylim(0, 1)
            if fig_opt['language'] == 0:
                plt.title(f'Habitat value - Computational Step : {sim_name[0]}')
            elif fig_opt['language'] == 1:
                plt.title(f"Valeur d'Habitat - unité : {sim_name[0]}")
            else:
                plt.title(f'Habitat value - Computational Step : {sim_name[0]}')
            # get data with mouse
            mplcursors.cursor()
            # export or not
            if types_plot == "export" or types_plot == "both":
                if not erase_id:
                    name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    name = 'WUA_' + name_base + '_Reach_' + str(r)
                    test = calcul_hab.remove_image(name, path_im, format1)
                    if not test:
                        return
                #plt.tight_layout()
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, name + '.png'), dpi=fig_opt['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'], transparent=True)

    # many time step - lines
    elif len(area_all) > 2:
        sum_data_spu = np.zeros((len(spu_all), len(area_all)))
        sum_data_spu_div = np.zeros((len(spu_all), len(area_all)))

        t_all = []
        for r in range(0, nb_reach):
            # SPU
            if r > 0:
                fig = plt.figure("Habitat Value and Weighted Usable Area for the reach " + str(r))
            spu_ax = fig.add_subplot(211)
            data_wua_list = []
            for s in range(0, len(spu_all)):
                data_plot_spu = []
                t_all = []
                for t in range(0, len(area_all)):
                    if spu_all[s][t] and spu_all[s][t][r] != -99:
                        data_plot_spu.append(spu_all[s][t][r])
                        sum_data_spu[s][t] += spu_all[s][t][r]
                        t_all.append(t)
                t_all_s = t_all
                data_wua_list.append(data_plot_spu)
                plt.plot(t_all, data_plot_spu, label=name_fish[s], marker=mar)
            if fig_opt['language'] == 0:
                # plt.xlabel('Computational step [ ]')
                plt.ylabel('WUA [m$^2$]')
                plt.title('Weighted Usable Area for the Reach ' + str(r))
            elif fig_opt['language'] == 1:
                # plt.xlabel('Pas de temps/débit [ ]')
                plt.ylabel('SPU [m$^2$]')
                plt.title('Surface Ponderée pour le troncon ' + str(r))
            else:
                # plt.xlabel('Computational step [ ]')
                plt.ylabel('WUA [m$^2$]')
                plt.title('Weighted Usable Area for the Reach ' + str(r))
            plt.legend(fancybox=True, framealpha=0.5)  # make the legend transparent
            # spu_ax.xaxis.set_ticklabels([])
            if len(sim_name[0]) > 5:
                rot = 'vertical'
            else:
                rot = 'horizontal'
            if len(sim_name) < 25:
                plt.xticks(t_all, [], rotation=rot)
            elif len(sim_name) < 100:
                plt.xticks(t_all[::3], [], rotation=rot)
            else:
                plt.xticks(t_all[::10], [], rotation=rot)
            # VH
            hv_ax = fig.add_subplot(212)
            data_hv_list = []
            for s in range(0, len(spu_all)):
                data_plot_hv = []
                t_all = []
                for t in range(0, len(area_all)):
                    if spu_all[s][t] and spu_all[s][t][r] != -99:
                        data_here = spu_all[s][t][r] / area_all[t][r]
                        data_plot_hv.append(data_here)
                        sum_data_spu_div[s][t] += data_here
                        t_all.append(t)
                data_hv_list.append(data_plot_hv)
                plt.plot(t_all, data_plot_hv, label=name_fish[s], marker=mar)
            if fig_opt['language'] == 0:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value for the Reach ' + str(r))
            elif fig_opt['language'] == 1:
                plt.xlabel('Pas de temps/débit [ ]')
                plt.ylabel('HV (SPU/A) []')
                plt.title("Valeur d'habitat pour le troncon " + str(r))
            else:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value for the Reach ' + str(r))
            plt.ylim(0, 1)
            # view data with mouse
            cursorPT = SnaptoCursorPT(fig.canvas, spu_ax, hv_ax, t_all, data_wua_list, data_hv_list)
            fig.canvas.mpl_connect('motion_notify_event', cursorPT.mouse_move)
            # label
            if sim_name:
                if len(sim_name[0]) > 5:
                    rot = 'vertical'
                else:
                    rot = 'horizontal'
                if len(sim_name) < 25:
                    plt.xticks(t_all, sim_name, rotation=45)
                elif len(sim_name) < 100:
                    plt.xticks(t_all[::3], sim_name[::3], rotation=45)
                else:
                    plt.xticks(t_all[::10], sim_name[::10], rotation=45)
            # plt.tight_layout()
            if types_plot == "export" or types_plot == "both":
                if not erase_id:
                    name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    name = 'WUA_' + name_base + '_Reach_' + str(r)
                    test = calcul_hab.remove_image(name, path_im, format1)
                    if not test:
                        return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, name + '.png'), dpi=fig_opt['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'], transparent=True)

        # all reach
        if nb_reach > 1:
            plt.close('all')  # only show the last reach
            fig = plt.figure()
            fig.add_subplot(211)
            for s in range(0, len(spu_all)):
                plt.plot(t_all_s, sum_data_spu[s][t_all_s], label=name_fish[s], marker=mar)
            if fig_opt['language'] == 0:
                plt.xlabel('Computational step or discharge')
                plt.ylabel('WUA [m^2]')
                plt.title('Weighted Usable Area for All Reaches')
            elif fig_opt['language'] == 1:
                plt.xlabel('Pas de temps/débit')
                plt.ylabel('SPU [m^2]')
                plt.title('Surface Ponderée pour tous les Troncons')
            else:
                plt.xlabel('Computational step or discharge')
                plt.ylabel('WUA [m^2]')
                plt.title('Weighted Usable Area for All Reaches')
            plt.legend(fancybox=True, framealpha=0.5)
            if sim_name:
                if len(sim_name[0]) > 5:
                    rot = 'vertical'
                else:
                    rot = 'horizontal'
                if len(sim_name) < 25:
                    plt.xticks(t_all, sim_name, rotation=rot)
                elif len(sim_name) < 100:
                    plt.xticks(t_all[::3], sim_name[::3], rotation=rot)
                else:
                    plt.xticks(t_all[::10], sim_name[::10], rotation=rot)
            # VH
            fig.add_subplot(212)
            for s in range(0, len(spu_all)):
                plt.plot(t_all, sum_data_spu_div[s][t_all], label=name_fish[s], marker=mar)
            if fig_opt['language'] == 0:
                plt.xlabel('Computational step or discharge ')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value For All Reaches')
            elif fig_opt['language'] == 1:
                plt.xlabel('Pas de temps/débit')
                plt.ylabel('HV (SPU/A) []')
                plt.title("Valeurs d'Habitat Pour Tous Les Troncons")
            else:
                plt.xlabel('Computational step or discharge ')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value For All Reaches')
            plt.ylim(0, 1)
            plt.tight_layout()
            if sim_name:
                if len(sim_name[0]) > 5:
                    rot = 'vertical'
                else:
                    rot = 'horizontal'
                if len(sim_name) < 25:
                    plt.xticks(t_all, sim_name, rotation=45)
                elif len(sim_name) < 100:
                    plt.xticks(t_all[::3], sim_name[::3], rotation=45)
                else:
                    plt.xticks(t_all[::10], sim_name[::10], rotation=45)
            if types_plot == "export" or types_plot == "both":
                if not erase_id:
                    name = 'WUA_' + name_base + '_All_Reach_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    name = 'WUA_' + name_base + '_All_Reach_'
                    test = calcul_hab.remove_image(name, path_im, format1)
                    if not test:
                        return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, name + '.png'), dpi=fig_opt['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "display" or types_plot == "both":
        # mplcursors.cursor()
        fm = plt.get_current_fig_manager()
        fm.window.showMinimized()
        plt.show()
    if types_plot == "export":
        plt.close()


class SnaptoCursorPT(object):
    """
    Display nearest data from x mouse position of matplotlib canvas.
    """

    def __init__(self, mpl_canvas, ax_wua, ax_hv, x, y_wua_list, y_hv_list):
        self.x_loc = None
        self.mpl_canvas = mpl_canvas
        self.ax_wua = ax_wua
        self.ax_hv = ax_hv
        self.x = x
        self.y_wua_list = y_wua_list
        self.y_hv_list = y_hv_list
        self.text_wua_list_mpl = []
        self.text_hv_list_mpl = []
        # prep text object in list
        for i in range(len(self.y_wua_list)):
            self.text_wua_list_mpl.append(self.ax_wua.text(x=self.x[0],
                                                           y=self.y_wua_list[i][0],
                                                           s="2 m²", horizontalalignment='center'))
            self.text_hv_list_mpl.append(self.ax_hv.text(x=self.x[0],
                                                         y=self.y_hv_list[i][0],
                                                         s="2 m²", horizontalalignment='center'))
            self.text_wua_list_mpl[i].set_alpha(0)
            self.text_hv_list_mpl[i].set_alpha(0)

    def mouse_move(self, event):
        if event.inaxes:
            # LOCATE
            self.take_closest(event.xdata, self.x)
            for i in range(len(self.y_wua_list)):
                # PLOT WUA
                y_wua = self.y_wua_list[i][self.x.index(self.x_loc)]
                text_wua = '{:0.0f}'.format(y_wua) + " m²"
                self.text_wua_list_mpl[i].set_alpha(1)
                self.text_wua_list_mpl[i].set_text(text_wua)
                self.text_wua_list_mpl[i].set_position((self.x_loc, y_wua))
                # PLOT HV
                y_hv = self.y_hv_list[i][self.x.index(self.x_loc)]
                text_hv = '{:0.2f}'.format(y_hv)
                self.text_hv_list_mpl[i].set_alpha(1)
                self.text_hv_list_mpl[i].set_text(text_hv)
                self.text_hv_list_mpl[i].set_position((self.x_loc, y_hv))
        if not event.inaxes:
            # HIDE
            for i in range(len(self.y_wua_list)):
                self.text_wua_list_mpl[i].set_alpha(0)
                self.text_hv_list_mpl[i].set_alpha(0)
        self.mpl_canvas.draw()

    def take_closest(self, num, collection):
        self.x_loc = min(collection, key=lambda x: abs(x - num))
