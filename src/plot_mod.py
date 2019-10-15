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
import time
from datetime import datetime as dt

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplcursors
import numpy as np
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon

from src import tools_mod
from src.tools_mod import get_translator
from src_GUI import preferences_GUI


def plot_suitability_curve(state, height, vel, sub, code_fish, name_fish, stade, project_preferences, get_fig=False):
    """
    This function is used to plot the preference curves.

    :param height: the height preference data (list of list)
    :param vel: the height preference data (list of list)
    :param sub: the height preference data (list of list)
    :param code_fish: the three letter code which indiate which fish species
        is analyzed
    :param name_fish: the name of the fish analyzed
    :param stade: the name of the stade analyzed (ADU, JUV, ...)
    :param get_fig: usually False, If True return the figure
        (to modfied it more)
    """

    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    if not get_fig:
        #project_preferences = preferences_GUI.create_default_project_preferences()
        plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
        plt.rcParams['font.size'] = project_preferences['font_size']
        if project_preferences['font_size'] > 7:
            plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    plt.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
    if project_preferences['language'] == 0:
        title_plot = 'Suitability curve \n' + name_fish + ' (' + code_fish + ') '
    else:
        title_plot = 'Courbe de préférence \n' + name_fish + ' (' + code_fish + ') '

    if len(stade) > 1:  # if you take this out, the command
        # axarr[x,x] does not work as axarr is only 1D
        # check if sub data exist
        if len(sub[0][0]) > 2:
            f, axarr = plt.subplots(len(stade), 3, sharey='row')
        else:  # no sub
            f, axarr = plt.subplots(len(stade), 2, sharey='row')

        f.canvas.set_window_title(title_plot)
        plt.suptitle(title_plot)
        for s in range(0, len(stade)):
            axarr[s, 0].plot(height[s][0], height[s][1], '-b', marker=mar)
            if project_preferences['language'] == 0:
                axarr[s, 0].set_xlabel('Water height [m]')
                axarr[s, 0].set_ylabel('Coeff. pref. ' + stade[s])
            else:
                axarr[s, 0].set_xlabel("Hauteur d'eau [m]")
                axarr[s, 0].set_ylabel('Coeff. pref. ' + stade[s])
            axarr[s, 0].set_ylim([0, 1.1])

            axarr[s, 1].plot(vel[s][0], vel[s][1], '-r', marker=mar)
            if project_preferences['language'] == 0:
                axarr[s, 1].set_xlabel('Velocity [m/sec]')
            else:
                axarr[s, 1].set_xlabel('Vitesse [m/sec]')
            axarr[s, 1].set_ylabel('Coeff. pref. ' + stade[s])
            axarr[s, 1].set_ylim([0, 1.1])

            if len(sub[0][0]) > 2:  # if substrate is accounted,
                # it is accounted for all stages
                axarr[s, 2].bar(sub[s][0], sub[s][1], facecolor='c',
                                align='center')
                if project_preferences['language'] == 0:
                    axarr[s, 2].set_xlabel('Substrate []')
                else:
                    axarr[s, 2].set_xlabel('Substrat []')
                axarr[s, 2].set_ylabel('Coeff. pref. ' + stade[s])
                axarr[s, 2].set_ylim([0, 1.1])
                axarr[s, 2].set_xlim([0.4, 8.6])

    else:
        # check if sub data exist
        if len(sub[0][0]) > 2:
            f, axarr = plt.subplots(3, 1, sharey='row')
        else:  # no sub
            f, axarr = plt.subplots(2, 1, sharey='row')
        f.canvas.set_window_title(title_plot)
        plt.suptitle(title_plot)
        axarr[0].plot(height[0][0], height[0][1], '-b', marker=mar)
        if project_preferences['language'] == 0:
            axarr[0].set_xlabel('Water height [m]')
            axarr[0].set_ylabel('Coeff. pref. ')
        else:
            axarr[0].set_xlabel("Hauteur d'eau [m]")
            axarr[0].set_ylabel('Coeff. pref. ')
        axarr[0].set_ylim([0, 1.1])
        axarr[1].plot(vel[0][0], vel[0][1], '-r', marker=mar)
        if project_preferences['language'] == 0:
            axarr[1].set_xlabel('Velocity [m/sec]')
        else:
            axarr[1].set_xlabel('Vitesse [m/sec]')
        axarr[1].set_ylabel('Coeff. pref. ')
        axarr[1].set_ylim([0, 1.1])

        # if sub
        if len(sub[0][0]) > 2:
            axarr[2].bar(sub[0][0], sub[0][1], facecolor='c', align='center')
            if project_preferences['language'] == 0:
                axarr[2].set_xlabel('Substrate []')
            else:
                axarr[2].set_xlabel('Substrat []')
            axarr[2].set_ylabel('Coeff. pref. ')
            axarr[2].set_ylim([0, 1.1])
            axarr[2].set_xlim([0.4, 8.6])

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    # output for plot_GUI
    state.value = 1  # process finished
    # fm = plt.get_current_fig_manager()
    # fm.window.showMinimized()
    if get_fig:
        return f, axarr
    else:
        plt.show()


def plot_suitability_curve_invertebrate(state, shear_stress_all, hem_all, hv_all, code_fish, name_fish, stade, get_fig=False, project_preferences=[]):
    """
    This function is used to plot the preference curves.

    :param height: the height preference data (list of list)
    :param vel: the height preference data (list of list)
    :param sub: the height preference data (list of list)
    :param code_fish: the three letter code which indiate which fish species
        is analyzed
    :param name_fish: the name of the fish analyzed
    :param stade: the name of the stade analyzed (ADU, JUV, ...)
    :param get_fig: usually False, If True return the figure
        (to modfied it more)
    """

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['pdf.fonttype'] = 42
    if not get_fig:
        if not project_preferences:
            project_preferences = preferences_GUI.create_default_project_preferences()
        plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
        plt.rcParams['font.size'] = project_preferences['font_size']
        if project_preferences['font_size'] > 7:
            plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    plt.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
    if project_preferences['language'] == 0:
        title_plot = 'Suitability curve \n' + name_fish + ' (' + code_fish + ') '
    else:
        title_plot = 'Courbe de préférence \n' + name_fish + ' (' + code_fish + ') '

    f, axarr = plt.subplots(1, 1, sharey='row')
    f.canvas.set_window_title(title_plot)
    plt.suptitle(title_plot)
    plt.grid()
    # bar plot
    axarr.bar([x + 0.5 for x in hem_all[0]],
                         hv_all[0])
    # HEM number label
    for hem_num in range(len(hem_all[0])):
        axarr.text(hem_all[0][hem_num] + 0.5, y=0, s=str(int(hem_all[0][hem_num])),
                   horizontalalignment='center',
                   verticalalignment='bottom')
    # shearstress stick
    plt.xticks([x for x in hem_all[0]] + [hem_all[0][-1] + 1],
               list(map(str, [0] + shear_stress_all[0])),
               rotation=45)

    #axarr.set_xticklabels(list(map(str, hem_all[0])))
    if project_preferences['language'] == 0:
        axarr.set_xlabel('HEM [HFST] / shear stress [N/m²]')
        axarr.set_ylabel('Coeff. pref. ')
    else:
        axarr.set_xlabel("HEM [HFST] / force tractrice [N/m²]")
        axarr.set_ylabel('Coeff. pref. ')
    axarr.set_ylim([-0.1, 1.1])
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    # output for plot_GUI
    state.value = 1  # process finished
    # fm = plt.get_current_fig_manager()
    # fm.window.showMinimized()
    if get_fig:
        return f, axarr
    else:
        plt.show()


def plot_suitability_curve_bivariate(state, height, vel, pref_values, code_fish, name_fish, stade, get_fig=False, project_preferences=[]):
    """
    This function is used to plot the preference curves.

    :param height: the height preference data (list of list)
    :param vel: the height preference data (list of list)
    :param sub: the height preference data (list of list)
    :param code_fish: the three letter code which indiate which fish species
        is analyzed
    :param name_fish: the name of the fish analyzed
    :param stade: the name of the stade analyzed (ADU, JUV, ...)
    :param get_fig: usually False, If True return the figure
        (to modfied it more)
    """

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['pdf.fonttype'] = 42
    if not get_fig:
        if not project_preferences:
            project_preferences = preferences_GUI.create_default_project_preferences()
        plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
        plt.rcParams['font.size'] = project_preferences['font_size']
        if project_preferences['font_size'] > 7:
            plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    plt.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
    if project_preferences['language'] == 0:
        title_plot = 'Suitability curve \n' + name_fish + ' (' + code_fish + ') '
    else:
        title_plot = 'Courbe de préférence \n' + name_fish + ' (' + code_fish + ') '

    if len(stade) > 1:  # if you take this out, the command
        # axarr[x,x] does not work as axarr is only 1D
        f, axarr = plt.subplots(len(stade), 3, sharey='row')
        f.canvas.set_window_title(title_plot)
        plt.suptitle(title_plot)
        for s in range(0, len(stade)):
            axarr[s, 0].plot(height[s][0], height[s][1], '-b', marker=mar)
            if project_preferences['language'] == 0:
                axarr[s, 0].set_xlabel('Water height [m]')
                axarr[s, 0].set_ylabel('Coeff. pref. ' + stade[s])
            else:
                axarr[s, 0].set_xlabel("Hauteur d'eau [m]")
                axarr[s, 0].set_ylabel('Coeff. pref. ' + stade[s])
            axarr[s, 0].set_ylim([0, 1.1])

            axarr[s, 1].plot(vel[s][0], vel[s][1], '-r', marker=mar)
            if project_preferences['language'] == 0:
                axarr[s, 1].set_xlabel('Velocity [m/sec]')
            else:
                axarr[s, 1].set_xlabel('Vitesse [m/sec]')
            axarr[s, 1].set_ylabel('Coeff. pref. ' + stade[s])
            axarr[s, 1].set_ylim([0, 1.1])

            # if len(sub[0][0]) > 2:  # if substrate is accounted,
            #     # it is accounted for all stages
            #     axarr[s, 2].bar(sub[s][0], sub[s][1], facecolor='c',
            #                     align='center')
            # if project_preferences['language'] == 0:
            #     axarr[s, 2].set_xlabel('Substrate []')
            # else:
            #     axarr[s, 2].set_xlabel('Substrat []')
            # axarr[s, 2].set_ylabel('Coeff. pref. ' + stade[s])
            # axarr[s, 2].set_ylim([0, 1.1])
            # axarr[s, 2].set_xlim([0.4, 8.6])

    else:
        # prep data
        X, Y = np.meshgrid(vel[0], height[0])
        Z = np.array(pref_values).reshape((len(height[0]), len(vel[0])))
        # plot
        f, axarr = plt.subplots(1, 1, sharey='row')
        f.canvas.set_window_title(title_plot)
        plt.suptitle(title_plot)
        meshcolor = axarr.pcolormesh(X, Y, Z)

        if project_preferences['language'] == 0:
            axarr.set_ylabel('Water height [m]')
            axarr.set_xlabel('Water velocity [m/s]')
        else:
            axarr.set_ylabel("Hauteur d'eau [m]")
            axarr.set_xlabel("Vitesse de l'eau [m/s]")
        axarr.set_ylim([0, 1.1])
        cbar = plt.colorbar(meshcolor)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    # output for plot_GUI
    state.value = 1  # process finished
    # fm = plt.get_current_fig_manager()
    # fm.window.showMinimized()
    if get_fig:
        return f, axarr
    else:
        plt.show()


def plot_hydrosignature(state, data, vclass, hclass, fishname, project_preferences):
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['pdf.fonttype'] = 42
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    if project_preferences['language'] == 0:
        title_plot = 'Measurement conditions \n' + fishname
    else:
        title_plot = 'Hydrosignature \n' + fishname

    plt.figure(title_plot)
    # cmap should be coherent with text color
    plt.imshow(data, cmap='Blues',
               interpolation='nearest',
               origin='lower')
    ax1 = plt.gca()

    # add percetage number
    maxlab = np.max(data)
    for (j, i), label in np.ndenumerate(data):
        # text in black or white depending on the data
        if label < maxlab / 2:
            ax1.text(i, j, np.round(label, 2), ha='center',
                     va='center', color='black')
        else:
            ax1.text(i, j, np.round(label, 2), ha='center',
                     va='center', color='white')
    ax1.set_xticks(np.arange(-0.5, 8.5, 1).tolist())
    ax1.set_xticklabels(vclass)
    ax1.set_yticks(np.arange(-0.5, 8.5, 1).tolist())
    ax1.set_yticklabels(hclass)
    plt.title(title_plot)
    plt.xlabel('Velocity [m/s]')
    plt.ylabel('Height [m]')
    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Relative area [%]')

    # output for plot_GUI
    state.value = 1  # process finished
    plt.show()


def plot_map_mesh(state, data_xy, data_tin, project_preferences, data_description, path_im=[], reach_name="", unit_name=0, points=False):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    # plot the grid
    plt.rcParams['agg.path.chunksize'] = 10000  # due to "OverflowError: Exceeded cell block limit
    # (set 'agg.path.chunksize' rcparam)" with savefig mesh png big file
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = project_preferences['erase_id']
    types_plot = project_preferences['type_plot']
    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        if not points:
            title = f"{name_hdf5[:-4]} : maillage - {reach_name} - {unit_name} {unit_type}"
            filename = f"{name_hdf5[:-4]}_maillage_{reach_name}_{unit_name}"
        if points:
            title = f"{name_hdf5[:-4]} : maillage et point - {reach_name} - {unit_name} {unit_type}"
            filename = f"{name_hdf5[:-4]}_maillage_points_{reach_name}_{unit_name}"
    else:
        if not points:
            title = f"{name_hdf5[:-4]} : mesh - {reach_name} - {unit_name} {unit_type}"
            filename = f"{name_hdf5[:-4]}_mesh_{reach_name}_{unit_name}"
        if points:
            title = f"{name_hdf5[:-4]} : mesh and points - {reach_name} - {unit_name} {unit_type}"
            filename = f"{name_hdf5[:-4]}_mesh_points_{reach_name}_{unit_name}"

    # plot
    plt.figure(filename)
    # the grid
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    plt.axis('equal')

    # prepare the grid
    if data_tin is not None:  # case empty grid
        xlist = []
        ylist = []
        for i in range(0, len(data_tin)):
            pi = 0
            tin_i = data_tin[i]
            if len(tin_i) == 3:
                while pi < 2:  # we have all sort of xells, max eight sides
                    # The conditions should be tested in this order to avoid to go out of the array
                    p = tin_i[pi]  # we start at 0 in python, careful about -1 or not
                    p2 = tin_i[pi + 1]
                    xlist.extend([data_xy[p, 0], data_xy[p2, 0]])
                    xlist.append(None)
                    ylist.extend([data_xy[p, 1], data_xy[p2, 1]])
                    ylist.append(None)
                    pi += 1

                p = tin_i[pi]
                p2 = tin_i[0]
                xlist.extend([data_xy[p, 0], data_xy[p2, 0]])
                xlist.append(None)
                ylist.extend([data_xy[p, 1], data_xy[p2, 1]])
                ylist.append(None)

        plt.plot(xlist, ylist, '-b', linewidth=0.1, color='blue')
        plt.ticklabel_format(useOffset=False)
        # to add water value on grid point (usualy to debug)
        # for idx, c in enumerate(coord_p):
        #     plt.annotate(str(inter_h_all[r][idx]),c)

    if points:
        # plot
        plt.scatter(x=data_xy[:, 0], y=data_xy[:, 1], s=5, color='black')
        plt.ticklabel_format(useOffset=False)

    # save figures
    plt.tight_layout()  # remove margin out of plot
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:  # [0,1,2,3,4,5] currently existing format
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_map_elevation(state, data_xy, data_tin, data_z, project_preferences, data_description, path_im=[], reach_name="", unit_name=0, ):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams[
        'agg.path.chunksize'] = 10000  # due to "OverflowError: Exceeded cell block limit (set 'agg.path.chunksize' rcparam)" with savefig mesh png big file
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = project_preferences['erase_id']
    types_plot = project_preferences['type_plot']
    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : elevation - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_elevation_{reach_name}_{unit_name}"
    else:
        title = f"{name_hdf5[:-4]} : elevation - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_elevation_{reach_name}_{unit_name}"

    # plot
    plt.figure(filename)
    # the grid
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    plt.axis('equal')

    # plot
    # color map (the same for al reach)
    mvc = 0.001
    cm = plt.cm.get_cmap(project_preferences['color_map2'])
    mv = max(data_z)
    minv = min(data_z)
    if mv > mvc:
        mvc = mv
    bounds = np.linspace(minv, mvc, 50)
    # plot
    sc = plt.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_z,
                         cmap=cm, vmin=minv, vmax=mvc, levels=bounds, extend='both')
    cbar = plt.colorbar(sc)

    cbar.set_label("[m]")
    plt.ticklabel_format(useOffset=False)

    # save figures
    plt.tight_layout()  # remove margin out of plot
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:  # [0,1,2,3,4,5] currently existing format
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_map_height(state, data_xy, data_tin, project_preferences, data_description, data_h=[], path_im=[], reach_name="", unit_name=0):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = project_preferences['erase_id']
    types_plot = project_preferences['type_plot']
    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : hauteur d'eau - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_profondeur_{reach_name}_{unit_name}"
    else:
        title = f"{name_hdf5[:-4]} : water depth - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_depth_{reach_name}_{unit_name}"

    # plot the height
    if len(data_h) > 0:  # 0
        # plt.subplot(2, 1, 2) # nb_fig, nb_fig, position
        plt.figure(filename)
        plt.ticklabel_format(useOffset=False)
        plt.axis('equal')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title(title)
        # color map (the same for al reach)
        mvc = 0.001
        cm = plt.cm.get_cmap(project_preferences['color_map2'])
        mv = max(data_h)
        if mv > mvc:
            mvc = mv
        bounds = np.linspace(0, mvc, 50)
        # negative value ?
        #data_h[data_h < 0] = 0

        sc = plt.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_h,
                             cmap=cm, vmin=0, vmax=mvc, levels=bounds, extend='both')
        cbar = plt.colorbar(sc)
        if project_preferences['language'] == 0:
            cbar.ax.set_ylabel('Water depth [m]')
        elif project_preferences['language'] == 1:
            cbar.ax.set_ylabel("Hauteur d'eau [m]")
        else:
            cbar.ax.set_ylabel('Water depth [m]')

        # save figure
        plt.tight_layout()  # remove margin out of plot
        if types_plot == "image export" or types_plot == "both":
            if not erase1:
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            else:
                test = tools_mod.remove_image(name_hdf5[:-4] + "_height", path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
                                transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                                transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'],
                                transparent=True)

        # output for plot_GUI
        state.value = 1  # process finished
        if types_plot == "interactive" or types_plot == "both":
            # fm = plt.get_current_fig_manager()
            # fm.window.showMinimized()
            plt.show()
        if types_plot == "image export":
            plt.close()


def plot_map_velocity(state, data_xy, data_tin, project_preferences, data_description, data_v=[], path_im=[], reach_name="", unit_name=0):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    # mpl.rcParams['ps.fonttype'] = 42  # if not commented, not possible to save in eps
    mpl.rcParams['pdf.fonttype'] = 42
    erase1 = project_preferences['erase_id']
    types_plot = project_preferences['type_plot']


    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : vitesse - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_vitesse_{reach_name}_{unit_name}"
    else:
        title = f"{name_hdf5[:-4]} : velocity - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_velocity_{reach_name}_{unit_name}"

    # plot
    if len(data_v) > 0:  # 0
        plt.figure(filename)
        plt.ticklabel_format(useOffset=False)
        plt.axis('equal')
        plt.xlabel('x coord []')
        plt.ylabel('y coord []')
        plt.title(title)
        # get colormap limit
        mvc = 0.001
        cm = plt.cm.get_cmap(project_preferences['color_map2'])
        mv = max(data_v)
        if mv > mvc:
            mvc = mv
        bounds = np.linspace(0, mvc, 50)

        sc = plt.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_v,
                             cmap=cm, levels=bounds, extend='both')
        
        # plt.clim(0, np.nanmax(inter_vel))
        cbar = plt.colorbar(sc)
        if project_preferences['language'] == 0:
            cbar.ax.set_ylabel('Velocity [m/sec]')
        elif project_preferences['language'] == 1:
            cbar.ax.set_ylabel('Vitesse [m/sec]')
        else:
            cbar.ax.set_ylabel('Velocity [m/sec]')

        # save figure
        plt.tight_layout()  # remove margin out of plot
        if types_plot == "image export" or types_plot == "both":
            if not erase1:
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            else:
                test = tools_mod.remove_image(filename, path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0:
                    plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
                                transparent=True)
                if format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                                transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'],
                                transparent=True)
        # output for plot_GUI
        state.value = 1  # process finished
        if types_plot == "interactive" or types_plot == "both":
            # fm = plt.get_current_fig_manager()
            # fm.window.showMinimized()
            plt.show()
        if types_plot == "image export":
            plt.close()


def plot_map_slope_bottom(state, coord_p, ikle, slope_data, data_description, project_preferences={}, path_im=[], reach_name="", unit_name=0):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator
    types_plot = project_preferences['type_plot']
    erase1 = project_preferences['erase_id']

    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : Pente maximale du fond - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_pente_fond_max_{reach_name}_{unit_name}"

    else:
        title = f"{name_hdf5[:-4]} : Maximum slope bottom - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_max_slope_bottom_{reach_name}_{unit_name}"

    # prep data
    slope_data = slope_data[:, 0]
    # create mask
    masked_array = np.ma.array(slope_data, mask=np.isnan(slope_data))

    # preplot
    fig = plt.figure(filename)
    ax = plt.axes()

    # plot the habitat value
    cmap = plt.get_cmap(project_preferences['color_map2'])
    cmap.set_bad(color='black', alpha=1.0)

    n = len(slope_data)
    norm = mpl.colors.Normalize(vmin=0, vmax=max(slope_data))
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)  # , edgecolor='w'
        patches.append(polygon)

    collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    collection.set_array(masked_array)
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.ticklabel_format(useOffset=False)

    plt.axis('equal')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure

    # colorbar
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
    if project_preferences['language'] == 0:
        cb1.set_label('Maximum slope bottom []')
    elif project_preferences['language'] == 1:
        cb1.set_label('Pente maximale du fond []')
    else:
        cb1.set_label('slope []')

    # save figure
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'],
                            transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_map_slope_energy(state, coord_p, ikle, slope_data, data_description, project_preferences={}, path_im=[], reach_name="", unit_name=0):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator
    types_plot = project_preferences['type_plot']
    erase1 = project_preferences['erase_id']

    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : Pente maximale d'énergie - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_pente_energie_{reach_name}_{unit_name}"

    else:
        title = f"{name_hdf5[:-4]} : Maximum slope energy - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_max_slope_energy_{reach_name}_{unit_name}"

    # prep data
    slope_data = slope_data[:, 0]
    # create mask
    masked_array = np.ma.array(slope_data, mask=np.isnan(slope_data))

    # preplot
    fig = plt.figure(filename)
    ax = plt.axes()

    # plot the habitat value
    cmap = plt.get_cmap(project_preferences['color_map2'])
    cmap.set_bad(color='black', alpha=1.0)

    n = len(slope_data)
    norm = mpl.colors.Normalize(vmin=0, vmax=max(slope_data))
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)  # , edgecolor='w'
        patches.append(polygon)

    collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    collection.set_array(masked_array)
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.ticklabel_format(useOffset=False)

    plt.axis('equal')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure

    # colorbar
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
    if project_preferences['language'] == 0:
        cb1.set_label('Maximum slope energy []')
    elif project_preferences['language'] == 1:
        cb1.set_label("Pente maximale d'énergie []")
    else:
        cb1.set_label('slope []')

    # save figure
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'],
                            transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_map_shear_stress(state, coord_p, ikle, shear_stress, data_description, project_preferences={}, path_im=[], reach_name="", unit_name=0):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator
    types_plot = project_preferences['type_plot']
    erase1 = project_preferences['erase_id']

    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : Contrainte de cisaillement - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_contrainte_cisaillement_{reach_name}_{unit_name}"

    else:
        title = f"{name_hdf5[:-4]} : Shear stress - {reach_name} - {unit_name} {unit_type}"
        filename = f"{name_hdf5[:-4]}_shear_stress_{reach_name}_{unit_name}"

    # prep data
    shear_stress = shear_stress[:, 0]
    # create mask
    masked_array = np.ma.array(shear_stress, mask=np.isnan(shear_stress))

    # preplot
    fig = plt.figure(filename)
    ax = plt.axes()

    # plot the habitat value
    cmap = plt.get_cmap(project_preferences['color_map2'])
    cmap.set_bad(color='black', alpha=1.0)

    n = len(shear_stress)
    norm = mpl.colors.Normalize(vmin=0, vmax=max(shear_stress))
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)  # , edgecolor='w'
        patches.append(polygon)

    collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    collection.set_array(masked_array)
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.ticklabel_format(useOffset=False)

    plt.axis('equal')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure

    # colorbar
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
    if project_preferences['language'] == 0:
        cb1.set_label('Shear stress []')
    elif project_preferences['language'] == 1:
        cb1.set_label("Contraite de cisaillement []")
    else:
        cb1.set_label('Shear stress []')

    # save figure
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'],
                            transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_map_substrate(state, coord_p, ikle, sub_array, data_description, path_im, project_preferences={}, reach_name="", unit_name=0.0):
    """
    The function to plot the substrate data, which was loaded before. This function will only work if the substrate
    data is given using the cemagref code.

    :param coord_p: the coordinate of the point
    :param ikle: the connectivity table
    :param sub_pg: the information on subtrate by element for the "coarser part"
    :param sub_dom: the information on subtrate by element for the "dominant part"
    :param project_preferences: the figure option as a doctionnary
    :param xtxt: if the data was given in txt form, the orignal x data
    :param ytxt: if the data was given in txt form, the orignal y data
    :param subtxt: if the data was given in txt form, the orignal sub data
    :param path_im: the path where to save the figure
    :param reach_num: If we plot more than one reach, this is the reach number
    """
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    types_plot = project_preferences['type_plot']
    erase1 = project_preferences['erase_id']

    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]

    # title and filename
    if project_preferences['language'] == 1:
        title_pg = f"Substrat - Plus Gros - {reach_name} - {unit_name} [{unit_type}]"
        title_dom = f"Substrat - Dominant - {reach_name} - {unit_name} [{unit_type}]"
        filename_pg_dm = f"{name_hdf5[:-4]}_substrat_{reach_name}_{unit_name}"
    else:
        title_pg = f"Substrate - Coarser - {reach_name} - {unit_name} [{unit_type}]"
        title_dom = f"Substrate - Dominant - {reach_name} - {unit_name} [{unit_type}]"
        filename_pg_dm = f"{name_hdf5[:-4]}_substrate_{reach_name}_{unit_name}"

    # prepare data
    unziped = list(zip(*sub_array))
    sub_pg = unziped[0]
    sub_dom = unziped[1]

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

    # general
    fig = plt.figure(name_hdf5[:-4])
    subs = fig.subplots(nrows=2, sharex=True, sharey=True)  #
    plt.setp(subs.flat, aspect='equal')
    sub1, sub2 = subs
    cmap = plt.get_cmap(project_preferences['color_map2'])
    if data_description["sub_classification_code"] == "Cemagref":
        max_class = 8
        listcathegories = list(range(0, max_class + 2))
        norm = mpl.colors.BoundaryNorm(listcathegories, cmap.N)
        # norm = mpl.colors.Normalize(vmin=1, vmax=8)
    if data_description["sub_classification_code"] == "Sandre":
        max_class = 12
        listcathegories = list(range(0, max_class + 2))
        norm = mpl.colors.BoundaryNorm(listcathegories, cmap.N)
        # norm = mpl.colors.Normalize(vmin=1, vmax=12)

    # sub1 substrate coarser
    patches = []
    colors_val = np.array(sub_pg, np.int)  # convert nfloors to colors that we can use later (cemagref)
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
    collection.set_array(colors_val)
    sub1.autoscale_view()
    sub1.set_ylabel('y coord []')
    sub1.set_title(title_pg)

    # sub2 substrate dominant
    patches = []
    colors_val = np.array(sub_dom, np.int)  # convert nfloors to colors that we can use later
    n = len(sub_dom)
    for i in range(0, n):
        verts = []
        for j in range(0, len(ikle[i])):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True, edgecolor='w')
        patches.append(polygon)
    collection = PatchCollection(patches, linewidth=0.0, cmap=cmap, norm=norm)
    sub2.add_collection(collection)
    collection.set_array(colors_val)
    sub1.autoscale_view()
    sub2.set_ylabel('y coord []')
    sub2.set_title(title_dom)
    sub2.set_xlabel('x coord []')
    sub2.xaxis.set_tick_params(rotation=15)

    # colorbar
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure
    listcathegories_stick = [x + 0.5 for x in range(0, max_class + 1)]
    listcathegories_stick_label = [x for x in range(1, max_class + 1)]
    cb1 = mpl.colorbar.ColorbarBase(ax1,
                                    cmap=cmap,
                                    norm=norm,
                                    boundaries=listcathegories_stick_label + [max_class + 1],
                                    orientation='vertical')
    cb1.set_ticks(listcathegories_stick)
    cb1.set_ticklabels(listcathegories_stick_label)
    cb1.set_label(data_description["sub_classification_code"])
    #plt.tight_layout()

    # save the figure
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format == 0:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format == 1:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format == 2:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.jpg'), dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image("substrate_coars_dom", path_im, format)
            if not test:
                return
            if format == 0 or format == 1:
                plt.savefig(os.path.join(path_im, filename_pg_dm + ".png"), dpi=project_preferences['resolution'], transparent=True)
            if format == 0 or format == 3:
                plt.savefig(os.path.join(path_im, filename_pg_dm + ".pdf"), dpi=project_preferences['resolution'], transparent=True)
            if format == 2:
                plt.savefig(os.path.join(path_im, filename_pg_dm + ".jpg"), dpi=project_preferences['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_map_fish_habitat(state, fish_name, coord_p, ikle, vh, percent_unknown, data_description, project_preferences={}, path_im=[], reach_name="", unit_name=0):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator
    types_plot = project_preferences['type_plot']
    erase1 = project_preferences['erase_id']


    name_hdf5 = data_description["name_hdf5"]
    unit_type = data_description["unit_type"][
           data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]
    fish_index = data_description["hab_fish_list"].split(", ").index(fish_name)
    fish_short_name = data_description["hab_fish_shortname_list"].split(", ")[fish_index]

    # title and filename
    if project_preferences['language'] == 1:
        title = f"{name_hdf5[:-4]} : valeur d'habitat\n{fish_name} - {reach_name} - {unit_name} {unit_type}\n" \
            f"surface inconnue : {percent_unknown:3.2f} %"
        filename = f"{name_hdf5[:-4]}_VH_{fish_short_name}_{reach_name}_{unit_name}"
    else:
        title = f"{name_hdf5[:-4]} : habitat value\n{fish_name} - {reach_name} - {unit_name} {unit_type}\n" \
            f"unknwon area : {percent_unknown:3.2f} %"
        filename = f"{name_hdf5[:-4]}_HSI_{fish_short_name}_{reach_name}_{unit_name}"

    # prep data
    masked_array = np.ma.array(vh, mask=np.isnan(vh))  # create mask

    # preplot
    fig = plt.figure(filename)
    ax = plt.axes()
    # fig, ax = plt.subplots(1)  # new figure
    norm = mpl.colors.Normalize(vmin=0, vmax=1)

    # plot the habitat value
    cmap = plt.get_cmap(project_preferences['color_map2'])
    cmap.set_bad(color='black', alpha=1.0)

    n = len(vh)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = coord_p[int(ikle[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)

    collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    # collection.set_color(colors) too slow
    collection.set_array(masked_array)
    ax.add_collection(collection)
    ax.autoscale_view()
    ax.ticklabel_format(useOffset=False)
    plt.axis('equal')
    plt.xlabel('x coord []')
    plt.ylabel('y coord []')
    plt.title(title)
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure

    # colorbar
    cb1 = mpl.colorbar.ColorbarBase(ax1, cmap=cmap, norm=norm, orientation='vertical')
    if project_preferences['language'] == 0:
        cb1.set_label('HV []')
    elif project_preferences['language'] == 1:
        cb1.set_label('VH []')
    else:
        cb1.set_label('HV []')

    # save figure
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + ".jpg"), dpi=project_preferences['resolution'],
                            transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_fish_hv_wua(state, data_description, reach_num, name_fish, path_im, name_hdf5, project_preferences={}):
    """
    This function creates the figure of the spu as a function of time for each reach. if there is only one
    time step, it reverse to a bar plot. Otherwise it is a line plot.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_im: the path where to save the image
    :param project_preferences: the dictionnary with the figure options
    :param name_hdf5: a string on which to base the name of the files
    :param unit_name: the name of the time steps if not 0,1,2,3
    """
    # get translation
    qt_tr = get_translator(project_preferences['path_prj'], project_preferences['name_prj'])

    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    default_size = plt.rcParams['figure.figsize']
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    if project_preferences['font_size'] > 7:
        plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
    mar2 = "2"
    erase1 = project_preferences['erase_id']
    types_plot = project_preferences['type_plot']
    # colors
    color_list, style_list = get_colors_styles_line_from_nb_input(len(name_fish))

    # prep data
    name_hdf5 = name_hdf5[:-4]
    area_all = list(map(float, data_description["total_wet_area"][reach_num]))
    unit_name = []
    if len(area_all) == 1:
        for unit_index in data_description["units_index"]:
            unit_name.append(data_description["hyd_unit_list"][0][unit_index])
    if len(area_all) > 1:
        for unit_index in data_description["units_index"]:
            unit_name.append(str(data_description["hyd_unit_list"][reach_num][unit_index]))
    unit_type = data_description["unit_type"][data_description["unit_type"].find('[') + len('['):data_description["unit_type"].find(']')]
    reach_name = data_description["hyd_reach_list"].split(", ")[reach_num]

    # plot
    title = qt_tr.translate("plot_mod", "Habitat Value and Weighted Usable Area - Computational Step : ")
    if len(unit_name) == 1:
        plot_window_title = title + str(unit_name[0]) + " " + unit_type
    else:
        plot_window_title = title + ", ".join(map(str, unit_name)) + " " + unit_type
        plot_window_title = plot_window_title[:80] + "..."

    # fig = plt.figure(plot_window_title)
    fig, ax = plt.subplots(2, 1, sharey='row')
    fig.canvas.set_window_title(plot_window_title)

    name_fish_origin = list(name_fish)
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # one time step - bar
    if len(area_all) == 1:
        # SPU
        data_bar = []
        for name_fish_value in name_fish_origin:
            data_bar.append(float(data_description["total_WUA_area"][name_fish_value][reach_num][0]))

        y_pos = np.arange(len(name_fish))
        data_bar2 = np.array(data_bar)
        ax[0].bar(y_pos, data_bar2)
        ax[0].set_xticks(y_pos)
        ax[0].set_xticklabels([])
        ax[0].set_ylabel(qt_tr.translate("plot_mod", 'WUA [m$^2$]'))
        ax[0].set_title(qt_tr.translate("plot_mod", "Weighted Usable Area - ") + reach_name + " - " + str(unit_name[0]) + " " + unit_type)

        # VH
        vh = data_bar2 / area_all[reach_num]
        ax[1].bar(y_pos, vh)
        ax[1].set_xticks(y_pos)
        ax[1].set_xticklabels(name_fish, horizontalalignment="right")
        ax[1].xaxis.set_tick_params(rotation=15)
        ax[1].set_ylabel(qt_tr.translate("plot_mod", 'HV (WUA/A) []'))
        ax[1].set_title(qt_tr.translate("plot_mod", "Habitat value - ") + reach_name + " - " + str(unit_name[0]) + " " + unit_type)
        mplcursors.cursor()  # get data with mouse
        plt.tight_layout()
        # export or not
        if types_plot == "image export" or types_plot == "both":
            if not project_preferences['erase_id']:
                name = qt_tr.translate("plot_mod", 'WUA_') + name_hdf5 + '_' + reach_name + "_" + str(unit_name[0]) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = qt_tr.translate("plot_mod", 'WUA_') + name_hdf5 + '_' + reach_name + "_" + str(unit_name[0])
                test = tools_mod.remove_image(name, path_im, format1)
                if not test:
                    return

            if format1 == 0:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

    # many time step - lines
    if len(area_all) > 1:
        # SPU
        x_data = list(map(float, unit_name))
        for fish_index, name_fish_value in enumerate(name_fish_origin):
            y_data_spu = list(map(float, data_description["total_WUA_area"][name_fish_value][reach_num]))
            # plot line
            ax[0].plot(x_data,
                     y_data_spu,
                     label=name_fish_value,
                     color=color_list[fish_index],
                     linestyle=style_list[fish_index])
        handles, labels = ax[0].get_legend_handles_labels()

        for fish_index, name_fish_value in enumerate(name_fish_origin):
            y_data_spu = list(map(float, data_description["total_WUA_area"][name_fish_value][reach_num]))
            # plot points
            for unit_index, percent in enumerate(data_description["percent_area_unknown"][name_fish_value][reach_num]):
                if percent == 0.0:
                    markers = mar
                else:
                    markers = mar2
                ax[0].scatter(x_data[unit_index],
                              y_data_spu[unit_index],
                              color="black",
                              label=name_fish_value,
                              marker=markers) #color_list[fish_index],

        ax[0].set_ylabel(qt_tr.translate("plot_mod", 'WUA [m$^2$]'))
        ax[0].set_title(qt_tr.translate("plot_mod", "Weighted Usable Area - ") + reach_name)
        # LEGEND
        fig.legend(handles=handles,
                   labels=labels,
                   loc="center right",
                   borderaxespad=0.5,
                   fancybox=True)

        # spu_ax.xaxis.set_ticklabels([])
        if len(unit_name[0]) > 5:
            rot = 'vertical'
        else:
            rot = 'horizontal'
        if len(unit_name) < 25:
            ax[0].set_xticks(x_data)
        elif len(unit_name) < 100:
            ax[0].set_xticks(x_data[::3])
        else:
            ax[0].set_xticks(x_data[::10])
        ax[0].set_xticklabels([])

        # VH
        for fish_index, name_fish_value in enumerate(name_fish_origin):
            y_data_hv = [b / m for b, m in zip(list(map(float, data_description["total_WUA_area"][name_fish_value][reach_num])),
                                                        area_all)]
            # plot line
            ax[1].plot(x_data,
                     y_data_hv,
                    label=name_fish_value,
                     color=color_list[fish_index],
                     linestyle=style_list[fish_index])
            # plot points
            for unit_index, percent in enumerate(data_description["percent_area_unknown"][name_fish_value][reach_num]):
                if percent == 0.0:
                    markers = mar
                else:
                    markers = mar2
                ax[1].scatter(x_data[unit_index],
                              y_data_hv[unit_index],
                              color="black",
                              label=name_fish_value,
                              marker=markers)  # color_list[fish_index]
        ax[1].set_xlabel(qt_tr.translate("plot_mod", 'Units [') + unit_type + ']')
        ax[1].set_ylabel(qt_tr.translate("plot_mod", 'HV (WUA/A) []'))
        ax[1].set_title(qt_tr.translate("plot_mod", 'Habitat Value - ') + reach_name)
        #ax[1].set_ylim(0, 1)
        # legend markers
        legend_elements = [Line2D([0], [0], marker=mar, color='black', label=qt_tr.translate("plot_mod", 'Complete'), markerfacecolor='black'),
                           Line2D([0], [0], marker=mar2, color='black', label=qt_tr.translate("plot_mod", 'Incomplete'), markerfacecolor='black')]
        ax[1].legend(handles=legend_elements, fancybox=True, framealpha=0.5)  # make the legend transparent
        # view data with mouse
        mplcursors.cursor()
        # cursorPT = SnaptoCursorPT(fig.canvas, spu_ax, hv_ax, x_data, y_data_spu_list, y_data_hv_list)
        # fig.canvas.mpl_connect('motion_notify_event', cursorPT.mouse_move)
        # label
        if len(unit_name[0]) > 5:
            rot = 'vertical'
        else:
            rot = 'horizontal'
        if len(unit_name) < 25:
            ax[1].set_xticks(x_data)
            ax[1].set_xticklabels(unit_name)
        elif len(unit_name) < 100:
            ax[1].set_xticks(x_data[::3])
            ax[1].set_xticklabels(unit_name[::3])
        else:
            ax[1].set_xticks(x_data[::10])
            ax[1].set_xticklabels(unit_name[::10])
        ax[1].xaxis.set_tick_params(rotation=45)

        plt.tight_layout()
        plt.subplots_adjust(right=0.73)

        if types_plot == "image export" or types_plot == "both":
            if not erase1:
                name = qt_tr.translate("plot_mod", 'WUA_') + name_hdf5 + '_' + reach_name + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = qt_tr.translate("plot_mod", 'WUA_') + name_hdf5 + '_' + reach_name
                test = tools_mod.remove_image(name, path_im, format1)
                if not test:
                    return
            if format1 == 0:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # reset original size fig window
        fig.set_size_inches(default_size[0], default_size[1])
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_interpolate_chronicle(state, data_to_table, horiz_headers, vertical_headers, data_description, name_fish, types, project_preferences):
    """
    This function creates the figure of the spu as a function of time for each reach. if there is only one
    time step, it reverse to a bar plot. Otherwise it is a line plot.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_im: the path where to save the image
    :param project_preferences: the dictionnary with the figure options
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the time steps if not 0,1,2,3
    """
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
    # get translation
    qt_tr = get_translator(project_preferences['path_prj'], project_preferences['name_prj'])
    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    if project_preferences['font_size'] > 7:
        plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
    erase1 = project_preferences['erase_id']
    is_constant = False
    # prep data
    if len(types.keys()) > 1:  # date
        date_presence = True
        date_type = types["date"]
        sim_name = np.array([dt.strptime(date, date_type).date() for date in vertical_headers], dtype='datetime64')
        date_format_mpl = mpl.dates.DateFormatter(date_type)
    else:
        date_presence = False
        sim_name = list(map(float, vertical_headers))
        # get number of decimals
        number_decimal_list = [vertical_headers[i][::-1].find('.') for i in range(len(vertical_headers))]
        number_decimal_mean = int(sum(number_decimal_list) / len(number_decimal_list))
        first_delta = sim_name[1] - sim_name[0]
        # is sim_name constant float
        is_constant = all(round(j - i, number_decimal_mean) == first_delta for i, j in zip(sim_name, sim_name[1:]))


    reach_num = int(data_description["hyd_reach_number"]) - 1
    name_base = data_description["hab_filename"][:-4]
    unit_type = data_description["hyd_unit_type"][data_description["hyd_unit_type"].find('[') + len('['):data_description["hyd_unit_type"].find(']')]
    data_to_table["units"] = list(map(lambda x: np.nan if x == "None" else float(x), data_to_table["units"]))

    if len(str(sim_name[0])) > 5:
        rot = 'vertical'
    else:
        rot = 'horizontal'

    # plot
    title = qt_tr.translate("plot_mod", "Habitat Value and Weighted Usable Area interpolated - Computational Step : ")
    if len(sim_name) == 1:
        plot_window_title = title + str(sim_name[0]) + " " + unit_type
    if len(sim_name) > 1:
        plot_window_title = title + ", ".join(
            map(str, sim_name[::10])) + ".. " + unit_type

    if not is_constant:
        fig, ax = plt.subplots(3, 1, sharey='row')
    if is_constant:
        fig, ax = plt.subplots(2, 1, sharey='row')
    fig.canvas.set_window_title(plot_window_title)

    name_fish_origin = list(name_fish)

    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # SPU
    if len(types.keys()) > 1:  # date
        x_data = sim_name
    else:
        x_data = range(len(sim_name))
    for name_fish_value in name_fish_origin:
        y_data_spu = data_to_table["spu_" + name_fish_value]
        ax[0].plot(x_data, y_data_spu, label=name_fish_value, marker=mar)
    ax[0].set_ylabel(qt_tr.translate("plot_mod", 'WUA [m$^2$]'))
    ax[0].set_title(qt_tr.translate("plot_mod", 'Weighted Usable Area interpolated for the Reach ') + str(0))
    if len(sim_name) < 25:
        ax[0].set_xticks(x_data, [])  #, rotation=rot
    elif len(sim_name) < 100:
        ax[0].set_xticks(x_data[::3], [])
    elif len(sim_name) < 200:
        ax[0].set_xticks(x_data[::10], [])
    else:
        ax[0].set_xticks(x_data[::20], [])
    # remove ticks labels
    ax[0].xaxis.set_ticklabels([])
    ax[0].xaxis.grid()
    ax[0].legend(fancybox=True, framealpha=0.5)  # make the legend transparent

    # VH
    for name_fish_value in name_fish_origin:
        y_data_hv = data_to_table["hv_" + name_fish_value]
        ax[1].plot(x_data, y_data_hv, label=name_fish_value, marker=mar)
    ax[1].set_ylabel(qt_tr.translate("plot_mod", 'HV []'))
    ax[1].set_title(qt_tr.translate("plot_mod", 'Habitat Value interpolated'))
    ax[1].set_ylim(0, 1)
    if len(sim_name) < 25:
        ax[1].set_xticks(x_data, [])  #, rotation=rot
        if not date_presence and is_constant:
            ax[1].set_xticks(x_data, sim_name)
    elif len(sim_name) < 100:
        ax[1].set_xticks(x_data[::3], [])
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name[::3])
    elif len(sim_name) < 200:
        ax[1].set_xticks(x_data[::10], [])
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name[::10])
    else:
        ax[1].set_xticks(x_data[::20], [])
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name[::20])
    if date_presence or not is_constant:
        # remove ticks labels
        ax[1].xaxis.set_ticklabels([])
    # all case
    ax[1].xaxis.grid()
    if is_constant:
        ax[1].set_xlabel(qt_tr.translate("plot_mod", 'Desired units [') + unit_type + ']')

    # unit
    if not is_constant:
        ax[2].plot(x_data, data_to_table["units"], label="unit [" + unit_type + "]", marker=mar)
        ax[2].set_title(qt_tr.translate("plot_mod", "Units"))
        if date_presence:
            ax[2].set_xlabel(qt_tr.translate("plot_mod", 'Chronicle [') + date_type + ']')
        if not date_presence:
            if not is_constant:
                ax[2].set_xlabel("")
            if is_constant:
                ax[2].set_xlabel(qt_tr.translate("plot_mod", 'Desired units [') + unit_type + ']')

        ax[2].set_ylabel(qt_tr.translate("plot_mod", 'units [') + unit_type + ']')
        if len(sim_name) < 25:
            ax[2].set_xticks(x_data, sim_name)  # , rotation=45
        elif len(sim_name) < 100:
            ax[2].set_xticks(x_data[::3])
            ax[2].set_xticklabels(sim_name[::3])
        elif len(sim_name) < 200:
            ax[2].set_xticks(x_data[::10])
            ax[2].set_xticklabels(sim_name[::10])
        else:
            ax[2].set_xticks(x_data[::20])
            ax[2].set_xticklabels(sim_name[::20])
        ax[2].xaxis.grid()
        ax[2].tick_params(axis='x', rotation=45)
        if not date_presence and not is_constant:
            # remove ticks labels
            ax[2].xaxis.set_ticklabels([])
        if date_presence:
            ax[2].xaxis.set_major_formatter(date_format_mpl)
    # get data with mouse
    mplcursors.cursor()

    plt.tight_layout()

    # output for plot_GUI
    state.value = 1  # process finished
    plt.show()


def plot_estimhab(state, estimhab_dict, project_preferences, path_prj):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    mpl.rcParams["savefig.directory"] = os.path.join(project_preferences["path_prj"], "output", "figures")  # change default path to save
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    default_size = plt.rcParams['figure.figsize']
    plt.rcParams['figure.figsize'] = project_preferences['width'], project_preferences['height']
    plt.rcParams['font.size'] = project_preferences['font_size']
    plt.rcParams['lines.linewidth'] = project_preferences['line_width']
    format1 = int(project_preferences['format'])
    plt.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['font_size'] > 7:
        plt.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    plt.rcParams['legend.loc'] = 'best'
    erase1 = project_preferences['erase_id']
    path_im = os.path.join(path_prj, "output", "figures")
    mpl.rcParams['pdf.fonttype'] = 42

    # prepare figure
    # c = ['b', 'm', 'r', 'c', '#9932CC', '#800000', 'k', 'g', 'y', '#9F81F7', '#BDBDBD', '#F7819F', 'b', 'm', 'r',
    #      'c', '#9932CC', '#800000', 'k', 'g', 'y', '#810D0D', '#810D0D', '#9F81F7']
    color_list, style_list = get_colors_styles_line_from_nb_input(len(estimhab_dict["fish_list"]))

    # plot
    fig, ax = plt.subplots(2, 1, sharey='row')
    fig.canvas.set_window_title('ESTIMHAB - HABBY')

    # VH
    ax[0].set_title("ESTIMHAB - HABBY")
    for fish_index in range(len(estimhab_dict["fish_list"])):
        ax[0].plot(estimhab_dict["q_all"],
                   estimhab_dict["VH"][fish_index],
                   label=estimhab_dict["fish_list"][fish_index],
                   color=color_list[fish_index],
                   linestyle=style_list[fish_index])
#                    color=c[fish_index],
    if project_preferences['language'] == 0:
        ax[0].set_ylabel('Habitat Value []')
    elif project_preferences['language'] == 1:
        ax[0].set_ylabel('Valeur habitat []')
    else:
        ax[0].set_ylabel('Habitat Value[]')
    ax[0].set_ylim(0, 1)

    # SPU
    for fish_index in range(len(estimhab_dict["fish_list"])):
        ax[1].plot(estimhab_dict["q_all"],
                   estimhab_dict["SPU"][fish_index],
                   label=estimhab_dict["fish_list"][fish_index],
                   color=color_list[fish_index],
                   linestyle=style_list[fish_index])

    if project_preferences['language'] == 0:
        ax[1].set_xlabel('Discharge [m$^{3}$/sec]')
        ax[1].set_ylabel('WUA by 100 m [m²]')
    elif project_preferences['language'] == 1:
        ax[1].set_xlabel('Débit [m$^{3}$/sec]')
        ax[1].set_ylabel('SPU par 100 m [m²]')
    else:
        ax[1].set_xlabel('Discharge [m$^{3}$/sec]')
        ax[1].set_ylabel('WUA by 100 m [m²]')

    # LEGEND
    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles=handles,
               labels=labels,
               loc="center right",
               borderaxespad=0.5,
               fancybox=True)

    plt.subplots_adjust(right=0.73)

    # name with date and time
    if format1 == 0:
        name_pict = "Estimhab" + ".pdf"
    if format1 == 1:
        name_pict = "Estimhab" + ".png"
    if format1 == 2:
        name_pict = "Estimhab" + ".jpg"

    if os.path.exists(os.path.join(path_im, name_pict)):
        if not erase1:
            name_pict = "Estimhab_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")

    # save image
    plt.savefig(os.path.join(path_im, name_pict), dpi=project_preferences['resolution'], transparent=True)

    # reset original size fig window
    fig.set_size_inches(default_size[0], default_size[1])

    # get data with mouse
    mplcursors.cursor()

    # finish process
    state.value = 1  # process finished

    # show
    plt.show()


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
            for i in range(len(self.y_wua_list)):  # for each fish list
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


def get_colors_styles_line_from_nb_input(input_nb):
    colors_number = 8
    cm = plt.get_cmap('gist_ncar')
    color_base_list = [cm(i/colors_number) for i in range(colors_number)] * input_nb
    color_list = color_base_list[:input_nb]
    line_styles_base_list = ['solid', 'dashed', 'dashdot', 'dotted']
    style_list = []
    style_start = 0
    while len(style_list) < input_nb:
        if len(style_list) > colors_number - 1:
            colors_number = colors_number * 2
            style_start += style_start + 1
        style_list.append(line_styles_base_list[style_start])

    return color_list, style_list
