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
from matplotlib.lines import Line2D
import mplcursors
import time
import os
from datetime import datetime as dt

from src_GUI import preferences_GUI
from src import tools_mod


def plot_suitability_curve(state, height, vel, sub, code_fish, name_fish, stade, get_fig=False, project_preferences=[]):
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
        f, axarr = plt.subplots(3, 1, sharey='row')
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


def plot_hydrosignature(state, data, fishname):
    mpl.rcParams['pdf.fonttype'] = 42
    project_preferences = preferences_GUI.create_default_project_preferences()

    if project_preferences['language'] == 0:
        title_plot = 'Measurement conditions \n' + fishname
    else:
        title_plot = 'Hydrosignature \n' + fishname

    plt.figure(title_plot)
    # cmap should be coherent with text color
    plt.imshow(data, cmap='Blues', interpolation='nearest', origin='lower')
    #  extent=[vclass.min(), vclass.max(), hclass.min(), hclass.max()]
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
    plt.title(title_plot)
    plt.xlabel('Velocity [m/s]')
    plt.ylabel('Height [m]')
    plt.locator_params(nticks=3)
    cbar = plt.colorbar()
    cbar.ax.set_ylabel('Relative area [%]')

    # output for plot_GUI
    state.value = 1  # process finished
    # fm = plt.get_current_fig_manager()
    # fm.window.showMinimized()
    plt.show()


def plot_map_mesh(state, data_xy, data_tin, project_preferences, data_description, path_im=[], reach_name="", unit_name=0, points=False):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

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
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:  # [0,1,2,3,4,5] currently existing format
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'], transparent=True)
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


def plot_map_elevation(state, data_xy, data_z, project_preferences, data_description, path_im=[], reach_name="", unit_name=0, ):
    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()

    # plot the grid
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
    plt.scatter(x=data_xy[:, 0], y=data_xy[:, 1], c=data_z, s=5, cmap="rainbow")
    cbar = plt.colorbar()
    cbar.set_label("elevation")
    plt.ticklabel_format(useOffset=False)

    # save figures
    plt.tight_layout()  # remove margin out of plot
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:  # [0,1,2,3,4,5] currently existing format
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'], transparent=True)
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

    # plot the grid
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
        bounds = np.linspace(0, mvc, 15)
        # negative value ?
        data_h[data_h < 0] = 0

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
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            else:
                test = tools_mod.remove_image(name_hdf5[:-4] + "_height", path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                                transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
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

    # plot the grid
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
        bounds = np.linspace(0, mvc, 15)

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
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                                dpi=project_preferences['resolution'], transparent=True)
                if format1 == 2:
                    plt.savefig(os.path.join(path_im, filename + time.strftime(
                        "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                                dpi=project_preferences['resolution'], transparent=True)
            else:
                test = tools_mod.remove_image(filename, path_im, format1)
                if not test and format1 in [0, 1, 2, 3, 4, 5]:
                    return
                if format1 == 0 or format1 == 1:
                    plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                                transparent=True)
                if format1 == 0 or format1 == 3:
                    plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
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
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
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
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
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
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
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
        title_pg = f"Substrate - Plus Gros - {reach_name} - {unit_name} {unit_type}"
        title_dom = f"Substrate - Dominant - {reach_name} - {unit_name} {unit_type}"
        filename_pg_dm = f"{name_hdf5[:-4]}_substrate_{reach_name}_{unit_name}"
    else:
        title_pg = f"Substrate - Coarser - {reach_name} - {unit_name} {unit_type}"
        title_dom = f"Substrate - Dominant - {reach_name} - {unit_name} {unit_type}"
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

    # substrate coarser
    fig = plt.figure(name_hdf5[:-4])
    subs = fig.subplots(nrows=2, sharex=True, sharey=True)  #
    plt.setp(subs.flat, aspect='equal')
    sub1, sub2 = subs
    patches = []
    cmap = plt.get_cmap(project_preferences['color_map1'])
    colors_val = np.array(sub_pg)  # convert nfloors to colors that we can use later (cemagref)
    # Set norm to correspond to the data for which
    # the colorbar will be used.
    if data_description["sub_classification_code"] == "Cemagref":
        max_class = 8
        norm = mpl.colors.Normalize(vmin=1, vmax=8)
    if data_description["sub_classification_code"] == "Sandre":
        max_class = 12
        norm = mpl.colors.Normalize(vmin=1, vmax=12)
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
    sub1.set_ylabel('y coord []')
    sub1.set_title(title_pg)

    # substrate dominant
    patches = []
    colors_val = np.array(sub_dom)  # convert nfloors to colors that we can use later
    # Set norm to correspond to the data for which
    # the colorbar will be used.
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
    # cbar = plt.colorbar()
    # cbar.ax.set_ylabel('Substrate')
    # sub2.plot(xlist, ylist, c='b', linewidth=0.2)
    sub2.set_xlabel('x coord []')
    sub2.set_ylabel('y coord []')
    sub2.set_title(title_dom)

    # colorbar
    ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure
    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    listcathegories = list(range(0, max_class + 1))
    cb1 = mpl.colorbar.ColorbarBase(ax1,
                                    cmap=cmap,
                                    norm=norm,
                                    boundaries=listcathegories,
                                    orientation='vertical')
    cb1.set_label(data_description["sub_classification_code"])
    plt.tight_layout()

    # save the figure
    if types_plot == "image export" or types_plot == "both":
        if not erase1:
            if format == 0 or format == 1:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format == 0 or format == 3:
                plt.savefig(os.path.join(path_im, filename_pg_dm + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
                                         '.pdf'), dpi=project_preferences['resolution'], transparent=True)
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
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".png"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
                            dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, filename + time.strftime(
                    "%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
                            dpi=project_preferences['resolution'], transparent=True)
        else:
            test = tools_mod.remove_image(filename, path_im, format1)
            if not test and format1 in [0, 1, 2, 3, 4, 5]:
                return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, filename + ".png"), dpi=project_preferences['resolution'],
                            transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, filename + ".pdf"), dpi=project_preferences['resolution'],
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

    if not project_preferences:
        project_preferences = preferences_GUI.create_default_project_preferences()
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
    color_list = plt.rcParams['axes.prop_cycle'].by_key()['color']

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
    if len(unit_name) == 1:
        plot_window_title = f"Habitat Value and Weighted Usable Area - Computational Step : {unit_name[0]}" + " " + unit_type
    if len(unit_name) > 1:
        plot_window_title = f"Habitat Value and Weighted Usable Area - Computational Steps : " + ", ".join(
            map(str, unit_name)) + " " + unit_type
    fig = plt.figure(plot_window_title)

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
        fig.add_subplot(211)
        data_bar2 = np.array(data_bar)
        plt.bar(y_pos, data_bar2)
        plt.xticks(y_pos, [])
        if project_preferences['language'] == 0:
            plt.ylabel('WUA [m^2]')
        elif project_preferences['language'] == 1:
            plt.ylabel('SPU [m^2]')
        else:
            plt.ylabel('WUA [m^2]')
        #plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
        if project_preferences['language'] == 0:
            plt.title(f'Weighted Usable Area - {reach_name} - {unit_name[0]} {unit_type}')
        elif project_preferences['language'] == 1:
            plt.title(f'Surface Ponderée Utile - {reach_name} - {unit_name[0]} {unit_type}')
        else:
            plt.title(f'Weighted Usable Area -  {reach_name} - {unit_name[0]} {unit_type}')
        # VH
        fig.add_subplot(212)
        vh = data_bar2 / area_all[reach_num]
        plt.bar(y_pos, vh)
        plt.xticks(y_pos, name_fish, rotation=10)

        if project_preferences['language'] == 0:
            plt.ylabel('HV (WUA/A) []')
        elif project_preferences['language'] == 1:
            plt.ylabel('VH (SPU/A) []')
        else:
            plt.ylabel('HV (WUA/A) []')
        #plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
        plt.ylim(0, 1)
        if project_preferences['language'] == 0:
            plt.title(f'Habitat value - {reach_name} - {unit_name[0]} {unit_type}')
        elif project_preferences['language'] == 1:
            plt.title(f"Valeur d'Habitat - {reach_name} - {unit_name[0]} {unit_type}")
        else:
            plt.title(f'Habitat value -  - {reach_name} - {unit_name[0]} {unit_type}')
        # get data with mouse
        mplcursors.cursor()
        plt.tight_layout()
        # export or not
        if types_plot == "image export" or types_plot == "both":
            if not project_preferences['erase_id']:
                name = 'WUA_' + name_hdf5 + '_' + reach_name + "_" + unit_name[0] + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_hdf5 + '_' + reach_name + "_" + unit_name[0]
                test = tools_mod.remove_image(name, path_im, format1)
                if not test:
                    return

            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

    # many time step - lines
    if len(area_all) > 1:
        # SPU
        spu_ax = fig.add_subplot(211)
        x_data = list(map(float, unit_name))
        for fish_index, name_fish_value in enumerate(name_fish_origin):
            y_data_spu = list(map(float, data_description["total_WUA_area"][name_fish_value][reach_num]))
            # plot line
            plt.plot(x_data, y_data_spu, c=color_list[fish_index], label=name_fish_value, marker=None)
            # plot points
            for unit_index, percent in enumerate(data_description["percent_area_unknown"][name_fish_value][reach_num]):
                if percent == 0.0:
                    markers = mar
                else:
                    markers = mar2
                plt.scatter(x_data[unit_index], y_data_spu[unit_index], c=color_list[fish_index], label=name_fish_value, marker=markers)

        if project_preferences['language'] == 0:
            # plt.xlabel('Computational step [ ]')
            plt.ylabel('WUA [m$^2$]')
            plt.title(f'Weighted Usable Area - {reach_name}')
        elif project_preferences['language'] == 1:
            plt.ylabel('SPU [m$^2$]')
            plt.title(f'Surface Ponderée Utile - {reach_name}')
        else:
            # plt.xlabel('Computational step [ ]')
            plt.ylabel('WUA [m$^2$]')
            plt.title(f'Weighted Usable Area - {reach_name}')
        plt.legend(name_fish_origin, fancybox=True, framealpha=0.5)  # make the legend transparent
        # spu_ax.xaxis.set_ticklabels([])
        if len(unit_name[0]) > 5:
            rot = 'vertical'
        else:
            rot = 'horizontal'
        if len(unit_name) < 25:
            plt.xticks(x_data, [], rotation=rot)
        elif len(unit_name) < 100:
            plt.xticks(x_data[::3], [], rotation=rot)
        else:
            plt.xticks(x_data[::10], [], rotation=rot)
        # VH
        hv_ax = fig.add_subplot(212)
        for fish_index, name_fish_value in enumerate(name_fish_origin):
            y_data_hv = [b / m for b, m in zip(list(map(float, data_description["total_WUA_area"][name_fish_value][reach_num])),
                                                        area_all)]
            # plot line
            plt.plot(x_data, y_data_hv, c=color_list[fish_index], label=name_fish_value, marker=None)
            # plot points
            for unit_index, percent in enumerate(data_description["percent_area_unknown"][name_fish_value][reach_num]):
                if percent == 0.0:
                    markers = mar
                else:
                    markers = mar2
                plt.scatter(x_data[unit_index], y_data_hv[unit_index], c=color_list[fish_index], label=name_fish_value, marker=markers)

        if project_preferences['language'] == 0:
            plt.xlabel('Computational step [' + unit_type + ']')
            plt.ylabel('HV (WUA/A) []')
            plt.title(f'Habitat Value - {reach_name}')
        elif project_preferences['language'] == 1:
            plt.xlabel('Unité [' + unit_type + ']')
            plt.ylabel('HV (SPU/A) []')
            plt.title(f"Valeur d'habitat - {reach_name}")
        else:
            plt.xlabel('Computational step [' + unit_type + ']')
            plt.ylabel('HV (WUA/A) []')
            plt.title(f'Habitat Value - {reach_name}')
        plt.ylim(0, 1)
        # legend markers
        legend_elements = [Line2D([0], [0], marker=mar, color='black', label='Complete', markerfacecolor='black'),
                           Line2D([0], [0], marker=mar2, color='black', label='Incomplete', markerfacecolor='black')]
        plt.legend(handles=legend_elements, fancybox=True, framealpha=0.5)  # make the legend transparent
        # view data with mouse
        # get data with mouse
        mplcursors.cursor()
        # cursorPT = SnaptoCursorPT(fig.canvas, spu_ax, hv_ax, x_data, y_data_spu_list, y_data_hv_list)
        # fig.canvas.mpl_connect('motion_notify_event', cursorPT.mouse_move)
        # label
        if unit_name:
            if len(unit_name[0]) > 5:
                rot = 'vertical'
            else:
                rot = 'horizontal'
            if len(unit_name) < 25:
                plt.xticks(x_data, unit_name, rotation=45)
            elif len(unit_name) < 100:
                plt.xticks(x_data[::3], unit_name[::3], rotation=45)
            else:
                plt.xticks(x_data[::10], unit_name[::10], rotation=45)
        plt.tight_layout()
        if types_plot == "image export" or types_plot == "both":
            if not erase1:
                name = 'WUA_' + name_hdf5 + '_' + reach_name + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_hdf5 + '_' + reach_name
                test = tools_mod.remove_image(name, path_im, format1)
                if not test:
                    return
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 1  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # fm = plt.get_current_fig_manager()
        # fm.window.showMinimized()
        plt.show()
    if types_plot == "image export":
        plt.close()


def plot_interpolate_chronicle(data_to_table, horiz_headers, vertical_headers, data_description, name_fish, types, project_preferences):
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
    #types_plot = project_preferences['type_plot']
    # prep data
    if len(types.keys()) > 1:  # date
        data_presence = True
        date_type = types["date"]
        sim_name = np.array([dt.strptime(date, date_type).date() for date in vertical_headers], dtype='datetime64')
    else:
        data_presence = False
        sim_name = list(map(float, vertical_headers))

    reach_num = int(data_description["hyd_reach_number"]) - 1
    name_base = data_description["hab_filename"][:-4]
    unit_type = data_description["hyd_unit_type"][data_description["hyd_unit_type"].find('[') + len('['):data_description["hyd_unit_type"].find(']')]
    data_to_table["units"] = list(map(lambda x: np.nan if x == "None" else float(x), data_to_table["units"]))

    # plot
    if len(sim_name) == 1:
        plot_window_title = f"Habitat Value and Weighted Usable Area interpolated - Computational Step : {sim_name[0]}" + " " + unit_type
    if len(sim_name) > 1:
        plot_window_title = f"Habitat Value and Weighted Usable Area interpolated  - Computational Steps : " + ", ".join(
            map(str, sim_name)) + " " + unit_type
    fig = plt.figure(plot_window_title)

    name_fish_origin = list(name_fish)
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # one time step - bar
    if len(vertical_headers) == 1:
        # SPU
        data_bar = []
        for name_fish_value in name_fish_origin:
            data_bar.append(float(data_description["total_WUA_area"][name_fish_value][reach_num][0]))

        y_pos = np.arange(len(name_fish))
        fig.add_subplot(211)
        data_bar2 = np.array(data_bar)
        plt.bar(y_pos, data_bar2)
        plt.xticks(y_pos, [])
        if project_preferences['language'] == 0:
            plt.ylabel('WUA [m^2]')
        elif project_preferences['language'] == 1:
            plt.ylabel('SPU [m^2]')
        else:
            plt.ylabel('WUA [m^2]')
        #plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
        if project_preferences['language'] == 0:
            plt.title(f'Weighted Usable Area - Computational Step : {sim_name[0]}' + " " + unit_type)
        elif project_preferences['language'] == 1:
            plt.title(f'Surface Ponderée Utile - unité : {sim_name[0]}' + " " + unit_type)
        else:
            plt.title(f'Weighted Usable Area - Computational Step : {sim_name[0]}' + " " + unit_type)
        # VH
        fig.add_subplot(212)
        vh = data_bar2 / area_all[reach_num]
        plt.bar(y_pos, vh)
        plt.xticks(y_pos, name_fish, rotation=10)

        if project_preferences['language'] == 0:
            plt.ylabel('HV (WUA/A) []')
        elif project_preferences['language'] == 1:
            plt.ylabel('VH (SPU/A) []')
        else:
            plt.ylabel('HV (WUA/A) []')
        #plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
        plt.ylim(0, 1)
        if project_preferences['language'] == 0:
            plt.title(f'Habitat value - Computational Step : {sim_name[0]}' + " " + unit_type)
        elif project_preferences['language'] == 1:
            plt.title(f"Valeur d'Habitat - unité : {sim_name[0]}" + " " + unit_type)
        else:
            plt.title(f'Habitat value - Computational Step : {sim_name[0]}' + " " + unit_type)
        # get data with mouse
        mplcursors.cursor()
        plt.tight_layout()
        # export or not
        if types_plot == "image export" or types_plot == "both":
            if not erase_id:
                name = 'WUA_' + name_base + '_Reach_' + str(0) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_base + '_Reach_' + str(0)
                test = tools_mod.remove_image(name, path_im, format1)
                if not test:
                    return

            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=project_preferences['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=project_preferences['resolution'], transparent=True)

    # many time step - lines
    if len(vertical_headers) > 1:
        # if not sorted(data_to_table["units"]) == data_to_table["units"]:
        #     idx = np.argsort(data_to_table["units"])
        #     for key in data_to_table.keys():
        #         data_provi = np.array(data_to_table[key])[idx].tolist()
        #         aa = np.delete(data_provi, data_provi != np.array(None))
        #


        # SPU
        spu_ax = fig.add_subplot(211)
        if len(types.keys()) > 1:  # date
            x_data = sim_name
        else:
            x_data = range(len(sim_name))
        for name_fish_value in name_fish_origin:
            y_data_spu = data_to_table["spu_" + name_fish_value]
            plt.plot(x_data, y_data_spu, label=name_fish_value, marker=mar)
        if project_preferences['language'] == 0:
            plt.ylabel('WUA [m$^2$]')
            plt.title('Weighted Usable Area interpolated for the Reach ' + str(0))
        elif project_preferences['language'] == 1:
            plt.ylabel('SPU [m$^2$]')
            plt.title(u'Surface Ponderée interpolées pour le troncon ' + str(0))
        else:
            # plt.xlabel('Computational step [ ]')
            plt.ylabel('WUA [m$^2$]')
            plt.title('Weighted Usable Area interpolated for the Reach ' + str(0))
        plt.legend(fancybox=True, framealpha=0.5)  # make the legend transparent
        if len(str(sim_name[0])) > 5:
            rot = 'vertical'
        else:
            rot = 'horizontal'
        if len(sim_name) < 25:
            plt.xticks(x_data, [], rotation=rot)
        elif len(sim_name) < 100:
            plt.xticks(x_data[::3], [], rotation=rot)
        elif len(sim_name) < 200:
            plt.xticks(x_data[::10], [], rotation=rot)
        else:
            plt.xticks(x_data[::20], [], rotation=rot)
        # VH
        hv_ax = fig.add_subplot(212)
        for name_fish_value in name_fish_origin:
            y_data_hv = data_to_table["hv_" + name_fish_value]
            plt.plot(x_data, y_data_hv, label=name_fish_value, marker=mar)
        if project_preferences['language'] == 0:
            plt.xlabel('Desired units [' + unit_type + ']')
            plt.ylabel('HV (WUA/A) []')
            plt.title('Habitat Value interpolated for the Reach ' + str(0))
        elif project_preferences['language'] == 1:
            plt.xlabel(u'Unité souhaitées [' + unit_type + ']')
            plt.ylabel('HV (SPU/A) []')
            plt.title("Valeur d'habitat interpolée pour le troncon " + str(0))
        else:
            plt.xlabel('Desired units [' + unit_type + ']')
            plt.ylabel('HV (WUA/A) []')
            plt.title('Habitat Value interpolated for the Reach ' + str(0))
        plt.ylim(0, 1)
        # get data with mouse
        mplcursors.cursor()
        # label
        if len(str(sim_name[0])) > 5:
            rot = 'vertical'
        else:
            rot = 'horizontal'

        if len(sim_name) < 25:
            plt.xticks(x_data, sim_name, rotation=45)
        elif len(sim_name) < 100:
            plt.xticks(x_data[::3], sim_name[::3], rotation=45)
        elif len(sim_name) < 200:
            plt.xticks(x_data[::10], sim_name[::10], rotation=rot)
        else:
            plt.xticks(x_data[::20], sim_name[::20], rotation=90)
        plt.tight_layout()
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
