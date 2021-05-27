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
import numpy as np
import matplotlib as mpl
from matplotlib import rc
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from matplotlib.legend_handler import HandlerLine2D
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib.ticker as ticker
from matplotlib import colors
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import mplcursors
from PIL import Image
from copy import copy

from src.translator_mod import get_translator


# other
def plot_suitability_curve(state, information_model_dict, selected_fish_stage, project_preferences, get_fig=False,
                           qt_tr=False):
    """
    This function is used to plot the univariate preference curves of one or all stages.
    """
    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    if not get_fig:
        default_size = plt.rcParams['figure.figsize']
        mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
        mpl.rcParams['font.size'] = project_preferences['font_size']
        if project_preferences['font_size'] > 7:
            mpl.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    # get translation
    # qt_tr = get_translator(project_preferences['path_prj'])
    mpl.rcParams['font.family'] = project_preferences['font_family']
    mpl.rcParams['legend.loc'] = 'best'
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['marker']:
        mar = '.'
    else:
        mar = None

    name_fish = information_model_dict["latin_name"]
    code_fish = information_model_dict["code_biological_model"]
    title_plot = 'HSI' + " : "

    # one stage
    if selected_fish_stage is not None:
        stage_index = information_model_dict["stage_and_size"].index(selected_fish_stage)
        stade = [selected_fish_stage]
        sub_var_list = information_model_dict["hab_variable_list"][stage_index].variable_list.subs()
        # preplot
        if sub_var_list:  # check if sub data exist
            fig, ax = plt.subplots(3, 1)
        else:  # no sub
            fig, ax = plt.subplots(2, 1)
        plt.get_current_fig_manager().set_window_title(title_plot + name_fish + " - " + stade[0] + " - " + code_fish)

        for index_var, hyd_var in enumerate(
                information_model_dict["hab_variable_list"][stage_index].variable_list.no_subs()):
            # height
            ax[index_var].plot(hyd_var.data[0],
                               hyd_var.data[1],
                               color="blue",
                               marker=mar)
            ax[index_var].set_xlabel(hyd_var.name_gui + " [" + hyd_var.unit + "]")
            ax[index_var].set_ylabel('HSI []')
            ax[index_var].set_ylim([-0.1, 1.1])

        # sub
        if sub_var_list:
            ax[2].bar(sub_var_list[0].data[0],
                      sub_var_list[0].data[1],
                      facecolor='c',
                      align='center')
            ax[2].set_xlabel(sub_var_list[0].name_gui + ' [' + sub_var_list[0].unit + ']')
            ax[2].set_ylabel('HSI []')
            ax[2].set_ylim([-0.1, 1.1])
            ax[2].set_xlim([0.4, len(sub_var_list[0].data[0]) + 0.6])

    # multi stage
    else:
        # preplot
        fig, ax = plt.subplots(len(information_model_dict["hab_variable_list"][0].variable_list),
                               len(information_model_dict["stage_and_size"]),
                               sharey='row')
        if ax.ndim == 1:
            ax = np.reshape(ax, (len(information_model_dict["hab_variable_list"][0].variable_list),
                                 len(information_model_dict["stage_and_size"])))

        plt.get_current_fig_manager().set_window_title(title_plot + name_fish + " - " + code_fish)

        # get min and max limits to improve plot readability between stages (value save to the last stage)
        variable_list_copy = copy(information_model_dict["hab_variable_list"][0].variable_list)
        for index_model_var, model_var in enumerate(variable_list_copy):
            for stage_index, stage_var in enumerate(information_model_dict["hab_variable_list"]):
                current_min = min(model_var.data[0])
                current_max = max(model_var.data[0])
                if stage_index == 0:
                    model_var.min = current_min
                    model_var.max = current_max
                if current_min < model_var.min:
                    model_var.min = current_min
                if current_max > model_var.max:
                    model_var.max = current_max

        # plot
        for stage_index, stage_var in enumerate(information_model_dict["hab_variable_list"]):
            for index_model_var, model_var in enumerate(
                    information_model_dict["hab_variable_list"][stage_index].variable_list):
                if not model_var.sub:
                    ax[index_model_var, stage_index].plot(model_var.data[0], model_var.data[1],
                                                          '-b', marker=mar)
                    ax[index_model_var, stage_index].set_xlim(
                        [variable_list_copy[index_model_var].min - 0.1,
                         variable_list_copy[index_model_var].max + 0.1])
                else:
                    ax[index_model_var, stage_index].bar(model_var.data[0], model_var.data[1],
                                                         facecolor='c', align='center')
                    ax[index_model_var, stage_index].set_xlim(
                        [variable_list_copy[index_model_var].min - 1,
                         variable_list_copy[index_model_var].max + 1])

                ax[index_model_var, stage_index].set_xlabel(model_var.name_gui + " [" + model_var.unit + "]")

                ax[index_model_var, stage_index].set_ylabel('HSI []' + "\n" + stage_var.stage)
                ax[index_model_var, stage_index].set_ylim([-0.1, 1.1])

    # all cases
    plt.tight_layout()
    if not get_fig:
        mplcursors.cursor()  # get data with mouse

    # output for plot_GUI
    if state is not None:
        state.value = 100  # process finished

    # show ?
    if not get_fig:
        fig.set_size_inches(default_size[0], default_size[1])
        plt.show()
    else:
        return fig, ax


def plot_suitability_curve_hem(state, information_model_dict, selected_fish_stage, project_preferences, get_fig=False,
                               qt_tr=False):
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

    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['pdf.fonttype'] = 42
    if not get_fig:
        default_size = plt.rcParams['figure.figsize']
        mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
        mpl.rcParams['font.size'] = project_preferences['font_size']
        if project_preferences['font_size'] > 7:
            mpl.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    # get translation
    if not qt_tr:
        qt_tr = get_translator(project_preferences['path_prj'])
    mpl.rcParams['font.family'] = project_preferences['font_family']
    mpl.rcParams['legend.loc'] = 'best'
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None

    # invertebrate one stage
    model_var = information_model_dict["hab_variable_list"][0]

    # title and filename
    title_plot = 'HSI' + " : " + model_var.name

    fig, axarr = plt.subplots(1, 1, sharey='row')
    plt.get_current_fig_manager().set_window_title(title_plot)
    # bar plot
    axarr.bar([x + 0.5 for x in model_var.variable_list[0].data[1]], model_var.variable_list[0].data[2])
    # HEM number label
    for hem_num in range(len(model_var.variable_list[0].data[1])):
        axarr.text(model_var.variable_list[0].data[1][hem_num] + 0.5, y=0,
                   s=str(int(model_var.variable_list[0].data[1][hem_num])),
                   horizontalalignment='center',
                   verticalalignment='bottom')
    # shearstress stick
    plt.xticks([x for x in model_var.variable_list[0].data[1]] + [model_var.variable_list[0].data[1][-1] + 1],
               list(map(str, [0] + model_var.variable_list[0].data[0])),
               rotation=45)

    axarr.set_xlabel(qt_tr.translate("plot_mod", 'HEM [HFST] / shear stress [N/m²]'))
    axarr.set_ylabel(qt_tr.translate("plot_mod", 'HSI []'))
    axarr.set_ylim([0.0, 1.0])

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    if not get_fig:
        mplcursors.cursor()  # get data with mouse

    # output for plot_GUI
    if state is not None:
        state.value = 100  # process finished

    if not get_fig:
        fig.set_size_inches(default_size[0], default_size[1])
        plt.show()
    else:
        return fig, axarr


def plot_suitability_curve_bivariate(state, information_model_dict, selected_fish_stage, project_preferences,
                                     get_fig=False, qt_tr=False):
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

    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['pdf.fonttype'] = 42
    if not get_fig:
        default_size = plt.rcParams['figure.figsize']
        mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
        mpl.rcParams['font.size'] = project_preferences['font_size']
        if project_preferences['font_size'] > 7:
            mpl.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    # get translation
    # qt_tr = get_translator(project_preferences['path_prj'])
    mpl.rcParams['font.family'] = project_preferences['font_family']
    mpl.rcParams['legend.loc'] = 'best'
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map

    if selected_fish_stage is not None:
        print("Error: No figure for all stages.")
        # TODO : do pcolormesh for each stage
        _ = 1
    else:
        # invertebrate one stage
        model_var = information_model_dict["hab_variable_list"][0]

        # prep data
        pref_values_array = np.array(model_var.hv).reshape((len(model_var.variable_list.get_from_name("h").data),
                                                            len(model_var.variable_list.get_from_name("v").data)))

        # pre plot
        fig, ax = plt.subplots(1, 1)
        plt.get_current_fig_manager().set_window_title('HSI' + " : " + model_var.name)

        # plot
        meshcolor = ax.imshow(pref_values_array,
                              cmap=cmap,
                              origin="lower",
                              aspect="auto",
                              extent=[min(model_var.variable_list.get_from_name("v").data),
                                      max(model_var.variable_list.get_from_name("v").data),
                                      min(model_var.variable_list.get_from_name("h").data),
                                      max(model_var.variable_list.get_from_name("h").data)])

        # axe label
        ax.set_ylabel('Water height [m]')
        ax.set_xlabel('Water velocity [m/s]')

        # color_bar bar
        color_bar = plt.colorbar(meshcolor)
        color_bar.set_label('HSI []')

        ax = [ax]

    plt.tight_layout()
    if not get_fig:
        mplcursors.cursor(meshcolor)  # get data with mouse

    # output for plot_GUI
    if state is not None:
        state.value = 100  # process finished

    if not get_fig:
        fig.set_size_inches(default_size[0], default_size[1])
        plt.show()
    else:
        return fig, ax


def plot_hydrosignature(state, data, vclass, hclass, title, type, project_preferences, axe_mod_choosen=2):
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams['font.family'] = project_preferences['font_family']
    default_size = plt.rcParams['figure.figsize']
    mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
    # get translation
    qt_tr = get_translator(project_preferences['path_prj'])

    # axe_mod_choosen
    if axe_mod_choosen == 1:
        origin = "upper"
        x_labels_position = "top"
    else:
        origin = "lower"
        x_labels_position = "bottom"

    plt.figure(title)

    if data is not None:
        if axe_mod_choosen == 3:
            data = data.T

        # cmap should be coherent with text color
        plt.imshow(data, cmap='Blues',
                   interpolation='nearest',
                   origin=origin)
    else:
        # hs_index
        nb_point = (len(vclass) - 1) * (len(hclass) - 1)
        hs_index = np.arange(1, nb_point + 1)
        if axe_mod_choosen in (1, 2):
            hs_index.resize((len(hclass) - 1, len(vclass) - 1))
        else:
            hs_index.resize((len(vclass) - 1, len(hclass) - 1))
        # cmap should be coherent with text color
        plt.imshow(hs_index, alpha=0,
                   origin=origin)

    ax1 = plt.gca()

    if data is not None:
        # add percetage number
        maxlab = np.max(data)
        for (j, i), label in np.ndenumerate(data):
            if label == 0.0:
                pass
            else:
                # text in black or white depending on the data
                if label < maxlab / 2:
                    ax1.text(i, j, "{0:.1f}".format(label), ha='center',
                             va='center', color='black')
                else:
                    ax1.text(i, j, "{0:.1f}".format(label), ha='center',
                             va='center', color='white')
    else:
        for (j, i), label in np.ndenumerate(hs_index):
            ax1.text(i, j, np.round(label, 2), ha='center',
                     va='center', color='black')

    if axe_mod_choosen == 1:
        ax1.xaxis.tick_top()

    if axe_mod_choosen == 3:
        ax1.set_yticks(np.arange(-0.5, len(vclass) - 0.5, 1).tolist())
        ax1.set_yticklabels(vclass)
    else:
        ax1.set_xticks(np.arange(-0.5, len(vclass) - 0.5, 1).tolist())
        ax1.set_xticklabels(vclass)

    if axe_mod_choosen == 3:
        ax1.set_xticks(np.arange(-0.5, len(hclass) - 0.5, 1).tolist())
        ax1.set_xticklabels(hclass)
        ax1.set_ylabel('Velocity [m/s]')
        ax1.set_xlabel('Height [m]')
    else:
        ax1.set_yticks(np.arange(-0.5, len(hclass) - 0.5, 1).tolist())
        ax1.set_yticklabels(hclass)
        ax1.set_ylabel('Height [m]')
        ax1.set_xlabel('Velocity [m/s]')

    ax1.xaxis.set_label_position(x_labels_position)
    ax1.xaxis.set_label_position(x_labels_position)

    # colorbar
    if data is not None:
        cbar = plt.colorbar()
        cbar.ax.set_ylabel('Relative ' + type + ' [%]')

    plt.tight_layout()
    mplcursors.cursor()  # get data with mouse

    # output for plot_GUI
    state.value = 100  # process finished
    # fig.set_size_inches(default_size[0], default_size[1])
    plt.show()


def plot_fish_hv_wua(state, data_2d, reach_number, habitat_variable_list, project_preferences):
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
    qt_tr = get_translator(project_preferences['path_prj'])
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    default_size = plt.rcParams['figure.figsize']
    mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
    mpl.rcParams['font.size'] = project_preferences['font_size']
    if project_preferences['font_size'] > 7:
        mpl.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    mpl.rcParams['font.family'] = project_preferences['font_family']
    mpl.rcParams['legend.loc'] = 'best'
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if project_preferences['marker']:
        mar = '.'
    else:
        mar = None
    mar2 = "2"
    path_im = project_preferences['path_figure']
    erase1 = project_preferences['erase_id']
    types_plot = project_preferences['type_plot']
    # colors
    color_list, style_list = get_colors_styles_line_from_nb_input(len(habitat_variable_list))

    # prep data
    name_hdf5 = data_2d.filename
    area_all = [unit.total_wet_area for unit in data_2d[reach_number]]
    unit_name = data_2d.unit_list[reach_number]
    unit_type = data_2d.unit_type
    unit_type_only = unit_type[unit_type.find('[') + len('['):unit_type.find(']')]
    unit_type_only_scientific = unit_type_only.replace("m3/s", "$m^3$/s")
    unit_type_scientific = unit_type.replace("m3/s", "$m^3$/s")
    reach_name = data_2d[reach_number][0].reach_name

    # plot
    title = qt_tr.translate("plot_mod", "Habitat Value and Weighted Usable Area - Computational Step : ")
    if len(unit_name) == 1:
        plot_window_title = title + str(unit_name[0]) + " " + unit_type_only
    else:
        plot_window_title = title + ", ".join(map(str, unit_name)) + " " + unit_type_only
        plot_window_title = plot_window_title[:80] + "..."

    fig, ax = plt.subplots(3, 1, sharex=True)
    plt.get_current_fig_manager().set_window_title(plot_window_title)

    # name_fish_origin = list(name_fish)
    # for id, n in enumerate(name_fish):
    #     name_fish[id] = n.name.replace('_', ' ')

    # one time step - bar
    if len(unit_name) == 1:
        # SPU
        data_bar = []
        percent = []
        for habitat_variable in habitat_variable_list:
            percent.append(float(habitat_variable.percent_area_unknown[reach_number][0]))
            data_bar.append(float(habitat_variable.wua[reach_number][0]))

        y_pos = np.arange(len(habitat_variable_list))
        data_bar2 = np.array(data_bar)
        ax[0].bar(y_pos, data_bar2)
        ax[0].set_xticks(y_pos)
        ax[0].set_xticklabels([])
        ax[0].set_ylabel(qt_tr.translate("plot_mod", 'WUA [m$^2$]'))
        ax[0].set_title(qt_tr.translate("plot_mod", "Weighted Usable Area - ") + reach_name + " - " + str(
            unit_name[0]) + " " + unit_type_only_scientific)

        # VH
        vh = data_bar2 / area_all[reach_number]
        ax[1].bar(y_pos, vh)
        ax[1].set_xticks(y_pos)
        ax[1].set_ylim([-0.1, 1.1])
        # ax[1].set_xticklabels(name_fish, horizontalalignment="right")
        # ax[1].xaxis.set_tick_params(rotation=15)
        ax[1].set_xticklabels([])
        ax[1].set_ylabel(qt_tr.translate("plot_mod", 'HSI (WUA/A) []'))
        ax[1].set_title(qt_tr.translate("plot_mod", "Habitat value"))

        # %
        percent = np.array(percent)
        ax[2].bar(y_pos, percent)
        ax[2].set_xticks(y_pos)
        ax[2].set_xticklabels(habitat_variable_list.names_gui(), horizontalalignment="right")
        ax[2].xaxis.set_tick_params(rotation=15)
        ax[2].set_ylabel(qt_tr.translate("plot_mod", 'UA [%]'))
        ax[2].set_title(
            qt_tr.translate("plot_mod", "Unknown area"))
        ax[2].set_ylim(bottom=0.0)

        # GENERAL
        mplcursors.cursor()  # get data with mouse
        plt.tight_layout()

        #
        if len(habitat_variable_list) == 1:  # one fish
            filename = name_hdf5 + "_" + reach_name + "_" + str(unit_name[0]).replace(".", "_") + '_' \
                       + habitat_variable_list[0].name_gui.replace(' ', '_')
        else:  # multi fish
            filename = name_hdf5 + "_" + reach_name + "_" + str(unit_name[0]).replace(".", "_") + '_' \
                       + qt_tr.translate("plot_mod", "HSI")

        # export or not
        if types_plot == "image export" or types_plot == "both":
            if not project_preferences['erase_id']:
                filename = filename + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                test = remove_image(filename, path_im, project_preferences['format'])
                if not test:
                    return
            plt.savefig(os.path.join(path_im, filename + project_preferences['format']),
                        dpi=project_preferences['resolution'],
                        transparent=True)

    # many time step - lines
    else:
        # SPU
        x_data = list(map(float, unit_name))
        for fish_index, habitat_variable in enumerate(habitat_variable_list):
            y_data_spu = list(map(float, habitat_variable.wua[reach_number]))
            # plot line
            ax[0].plot(x_data,
                       y_data_spu,
                       label=habitat_variable.name_gui,
                       color=color_list[fish_index],
                       linestyle=style_list[fish_index],
                       marker=mar)
        ax[0].set_ylabel(qt_tr.translate("plot_mod", 'WUA [m$^2$]'))
        ax[0].set_title(qt_tr.translate("plot_mod", "Weighted Usable Area - ") + reach_name)
        if len(unit_name) < 25:
            ax[0].set_xticks(x_data)
        elif len(unit_name) < 100:
            ax[0].set_xticks(x_data[::3])
        else:
            ax[0].set_xticks(x_data[::10])
        ax[0].set_xticklabels([])

        # VH
        for fish_index, habitat_variable in enumerate(habitat_variable_list):
            y_data_hv = list(map(float, habitat_variable.hv[reach_number]))
            # plot line
            ax[1].plot(x_data,
                       y_data_hv,
                       label=habitat_variable.name_gui,
                       color=color_list[fish_index],
                       linestyle=style_list[fish_index],
                       marker=mar)

        ax[1].set_ylim([-0.1, 1.1])
        ax[1].set_ylabel(qt_tr.translate("plot_mod", 'HSI (WUA/A) []'))
        ax[1].set_title(qt_tr.translate("plot_mod", 'Habitat Value'))
        if len(unit_name) < 25:
            ax[1].set_xticks(x_data)
        elif len(unit_name) < 100:
            ax[1].set_xticks(x_data[::3])
        else:
            ax[1].set_xticks(x_data[::10])
        ax[1].set_xticklabels([])

        # % inconnu
        for fish_index, habitat_variable in enumerate(habitat_variable_list):
            y_data_percent = list(map(float, habitat_variable.percent_area_unknown[reach_number]))
            # plot line
            ax[2].plot(x_data,
                       y_data_percent,
                       label=habitat_variable.name_gui,
                       color=color_list[fish_index],
                       linestyle=style_list[fish_index],
                       marker=mar)

        ax[2].set_xlabel(unit_type_scientific)
        ax[2].set_ylabel(qt_tr.translate("plot_mod", 'UA [%]'))
        ax[2].set_title(qt_tr.translate("plot_mod", 'Unknown area'))
        # label
        if len(unit_name) < 25:
            ax[2].set_xticks(x_data)
            ax[2].set_xticklabels(unit_name)
        elif len(unit_name) < 100:
            ax[2].set_xticks(x_data[::3])
            ax[2].set_xticklabels(unit_name[::3])
        else:
            ax[2].set_xticks(x_data[::10])
            ax[2].set_xticklabels(unit_name[::10])
        ax[2].xaxis.set_tick_params(rotation=45)
        ax[2].set_ylim(bottom=0.0)

        # LEGEND
        handles, labels = ax[0].get_legend_handles_labels()
        fig.legend(handles=handles,
                   labels=labels,
                   loc="center right",
                   borderaxespad=0.5,
                   fancybox=True)

        plt.tight_layout()
        plt.subplots_adjust(right=0.71)

        # view data with mouse
        mplcursors.cursor()

        if len(habitat_variable_list) == 1:  # one fish
            filename = name_hdf5 + "_" + reach_name + "_units_" + habitat_variable_list[0].name_gui.replace(' ', '_')
        else:
            filename = name_hdf5 + "_" + reach_name + "_units_" + qt_tr.translate("plot_mod", "HSI")

        if types_plot == "image export" or types_plot == "both":
            if not erase1:
                filename = filename + "_" + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                test = remove_image(filename, path_im, project_preferences['format'])
                if not test:
                    return
            plt.savefig(os.path.join(path_im, filename + project_preferences['format']),
                        dpi=project_preferences['resolution'], transparent=True)

    # output for plot_GUI
    state.value = 100  # process finished
    if types_plot == "interactive" or types_plot == "both":
        # reset original size fig window
        fig.set_size_inches(default_size[0], default_size[1])
        plt.show()
    if types_plot == "image export":
        plt.close(fig)


def plot_interpolate_chronicle(state, data_to_table, _, vertical_headers, data_2d, animal_list, reach_number, types,
                               project_preferences):
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
    # get translation
    qt_tr = get_translator(project_preferences['path_prj'])
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
    mpl.rcParams['font.size'] = project_preferences['font_size']
    if project_preferences['font_size'] > 7:
        mpl.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    mpl.rcParams['font.family'] = project_preferences['font_family']
    mpl.rcParams['legend.loc'] = 'best'
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    if project_preferences['marker']:
        mar = 'o'
    else:
        mar = None
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

    # colors
    color_list, style_list = get_colors_styles_line_from_nb_input(len(animal_list))

    reach_name = data_2d[reach_number][0].reach_name
    unit_type = data_2d.unit_type
    unit_type = unit_type.replace("m3/s", "$m^3$/s")
    data_to_table["units"] = list(map(lambda x: np.nan if x == "None" else float(x), data_to_table["units"]))

    # plot
    title = qt_tr.translate("plot_mod", "Habitat Value and Weighted Usable Area interpolated - Unit : ")
    if len(sim_name) == 1:
        plot_window_title = title + str(sim_name[0]) + " "
    if len(sim_name) > 1:
        plot_window_title = title + ", ".join(
            map(str, sim_name[::10])) + ".. "

    if not is_constant:
        fig, ax = plt.subplots(4, 1, sharex=True)
    else:
        fig, ax = plt.subplots(3, 1, sharex=True)
    plt.get_current_fig_manager().set_window_title(plot_window_title)

    # SPU
    if len(types.keys()) > 1:  # date
        x_data = sim_name
    else:
        x_data = range(len(sim_name))
    for name_fish_num, animal in enumerate(animal_list):
        y_data_spu = data_to_table["spu_" + animal.name]
        ax[0].plot(x_data, y_data_spu,
                   color=color_list[name_fish_num],
                   linestyle=style_list[name_fish_num],
                   label=animal.name.replace('_', ' '),
                   marker=mar)
    ax[0].set_ylabel(qt_tr.translate("plot_mod", 'WUA [m$^2$]'))
    ax[0].set_title(qt_tr.translate("plot_mod", 'Weighted Usable Area interpolated - ') + reach_name)
    if len(sim_name) < 25:
        ax[0].set_xticks(x_data)  # , rotation=rot
    elif len(sim_name) < 100:
        ax[0].set_xticks(x_data[::3])
    elif len(sim_name) < 200:
        ax[0].set_xticks(x_data[::10])
    else:
        ax[0].set_xticks(x_data[::20])
    # remove ticks labels
    ax[0].xaxis.set_ticklabels([])

    # VH
    for name_fish_num, animal in enumerate(animal_list):
        y_data_hv = data_to_table["hv_" + animal.name]
        ax[1].plot(x_data, y_data_hv,
                   color=color_list[name_fish_num],
                   linestyle=style_list[name_fish_num],
                   label=animal.name.replace('_', ' '),
                   marker=mar)
    ax[1].set_ylabel(qt_tr.translate("plot_mod", 'HSI []'))
    ax[1].set_title(qt_tr.translate("plot_mod", 'Habitat Value interpolated'))
    ax[1].set_ylim([-0.1, 1.1])
    if len(sim_name) < 25:
        ax[1].set_xticks(x_data)  # , rotation=rot
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name)
    elif len(sim_name) < 100:
        ax[1].set_xticks(x_data[::3])
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name[::3])
    elif len(sim_name) < 200:
        ax[1].set_xticks(x_data[::10])
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name[::10])
    else:
        ax[1].set_xticks(x_data[::20])
        if not date_presence and is_constant:
            ax[1].set_xticklabels(sim_name[::20])
    if date_presence or not is_constant:
        # remove ticks labels
        ax[1].xaxis.set_ticklabels([])

    # % inconnu
    for name_fish_num, animal in enumerate(animal_list):
        y_data_hv = data_to_table["si_" + animal.name]
        ax[2].plot(x_data, y_data_hv,
                   color=color_list[name_fish_num],
                   linestyle=style_list[name_fish_num],
                   label=animal.name.replace('_', ' '),
                   marker=mar)
    ax[2].set_ylabel(qt_tr.translate("plot_mod", 'UA [%]'))
    ax[2].set_title(qt_tr.translate("plot_mod", 'Unknown area'))
    # all case
    if is_constant:
        ax[2].set_xlabel(qt_tr.translate("plot_mod", 'Desired ') + unit_type)

    # unit
    if not is_constant:
        ax[3].plot(x_data, data_to_table["units"], label=unit_type, marker=mar)
        ax[3].set_title(qt_tr.translate("plot_mod", "Units"))
        if date_presence:
            ax[3].set_xlabel(qt_tr.translate("plot_mod", 'Chronicle [') + date_type + ']')
        if not date_presence:
            if not is_constant:
                ax[3].set_xlabel("")
            if is_constant:
                ax[3].set_xlabel(qt_tr.translate("plot_mod", 'Desired ') + unit_type)

        ax[3].set_ylabel(unit_type)
        if len(sim_name) < 25:
            ax[3].set_xticks(x_data)  # , rotation=45
            ax[3].set_xticklabels(sim_name)
        elif len(sim_name) < 100:
            ax[3].set_xticks(x_data[::3])
            ax[3].set_xticklabels(sim_name[::3])
        elif len(sim_name) < 200:
            ax[3].set_xticks(x_data[::10])
            ax[3].set_xticklabels(sim_name[::10])
        else:
            ax[3].set_xticks(x_data[::20])
            ax[3].set_xticklabels(sim_name[::20])
        ax[3].tick_params(axis='x', rotation=45)
        if not date_presence and not is_constant:
            # remove ticks labels
            ax[3].xaxis.set_ticklabels([])
        if date_presence:
            ax[3].xaxis.set_major_formatter(date_format_mpl)

    # LEGEND
    handles, labels = ax[0].get_legend_handles_labels()
    fig.legend(handles=handles,
               labels=labels,
               loc="center right",
               borderaxespad=0.5,
               fancybox=True)

    plt.tight_layout()
    plt.subplots_adjust(right=0.71)

    # view data with mouse
    mplcursors.cursor()

    # output for plot_GUI
    state.value = 100  # process finished
    plt.show()


def plot_stat_data(state, stat_data_dict, stat_mod, project_preferences):
    # get translation
    # qt_tr = get_translator(project_preferences['path_prj'])
    path_prj = project_preferences['path_prj']
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
    mpl.rcParams['font.size'] = project_preferences['font_size']
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    if project_preferences['font_size'] > 7:
        mpl.rcParams['legend.fontsize'] = project_preferences['font_size'] - 2
    mpl.rcParams['font.family'] = project_preferences['font_family']
    mpl.rcParams['legend.loc'] = 'best'
    erase1 = project_preferences['erase_id']
    path_im = os.path.join(path_prj, "output", "figures")
    mpl.rcParams['pdf.fonttype'] = 42

    # prepare color
    color_list, style_list = get_colors_styles_line_from_nb_input(len(stat_data_dict["fish_list"]))

    """ plot hyd data """
    fig2, (ax_h, ax_w, ax_v) = plt.subplots(ncols=1, nrows=3,
                                            sharex="all",
                                            gridspec_kw={'height_ratios': [1, 1, 1]})
    plt.get_current_fig_manager().set_window_title(stat_mod + ' hydraulic data - HABBY')  # set windows title
    ax_h.set_title(stat_mod + ' hydraulic data - HABBY')
    # H
    if stat_data_dict["targ_q_all"]:
        for q_tar in stat_data_dict["targ_q_all"]:
            ax_h.axvline(x=q_tar,
                         linestyle=":",
                         color="black")
    ax_h.plot(stat_data_dict["q_all"],
              stat_data_dict["h_all"],
              color="black")
    ax_h.set_ylabel("height\n[m]")
    ax_h.yaxis.set_label_coords(-0.1, 0.5)  # adjust/align ylabel position

    # W
    if stat_data_dict["targ_q_all"]:
        for q_tar in stat_data_dict["targ_q_all"]:
            ax_w.axvline(x=q_tar,
                         linestyle=":",
                         color="black")
    ax_w.plot(stat_data_dict["q_all"],
              stat_data_dict["w_all"],
              color="black")
    ax_w.set_ylabel("width\n[m]")
    ax_w.yaxis.set_label_coords(-0.1, 0.5)  # adjust/align ylabel position

    # V
    if stat_data_dict["targ_q_all"]:
        for q_tar in stat_data_dict["targ_q_all"]:
            ax_v.axvline(x=q_tar,
                         linestyle=":",
                         color="black")
    ax_v.plot(stat_data_dict["q_all"],
              stat_data_dict["vel_all"],
              color="black")
    ax_v.set_ylabel("velocity\n[m/s]")
    ax_v.yaxis.set_label_coords(-0.1, 0.5)  # adjust/align ylabel position
    ax_v.set_xlabel("Discharge [m$^{3}$/sec]")

    # targ_q_all
    if stat_data_dict["targ_q_all"]:
        labels = ["Qtarg [m$^{3}$/sec]"]
        fig2.legend(handler_map={plt.Line2D: HandlerLine2D(update_func=update_prop)},
                    labels=labels,
                    loc="lower left",
                    borderaxespad=0.5,
                    fancybox=False,
                    bbox_to_anchor=(0.73, 0.1))

    plt.subplots_adjust(right=0.73)

    # save image
    name_pict = stat_mod + "_hydraulic" + project_preferences['format']
    if os.path.exists(os.path.join(path_im, name_pict)):
        if not erase1:
            name_pict = stat_mod + "_hydraulic" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + project_preferences['format']
    plt.savefig(os.path.join(path_im, name_pict),
                dpi=project_preferences['resolution'],
                transparent=True)

    """ plot hv """
    fig, (ax_vh, ax_spu) = plt.subplots(ncols=1, nrows=2,
                                        sharex="all",
                                        gridspec_kw={'height_ratios': [3, 3]})
    plt.get_current_fig_manager().set_window_title(stat_mod + ' output - HABBY')

    # VH
    ax_vh.set_title(stat_mod + " output - HABBY")
    if stat_data_dict["targ_q_all"]:
        for q_tar in stat_data_dict["targ_q_all"]:
            ax_vh.axvline(x=q_tar,
                          linestyle=":",
                          color="black")
    for fish_index in range(len(stat_data_dict["fish_list"])):
        ax_vh.plot(stat_data_dict["q_all"],
                   stat_data_dict["VH"][fish_index],
                   label=stat_data_dict["fish_list"][fish_index],
                   color=color_list[fish_index],
                   linestyle=style_list[fish_index])
    ax_vh.set_ylim([-0.1, 1.1])
    ax_vh.set_ylabel("Habitat Value\n[]")
    ax_vh.yaxis.set_label_coords(-0.1, 0.5)  # adjust/align ylabel position

    # SPU
    if stat_data_dict["targ_q_all"]:
        for q_tar in stat_data_dict["targ_q_all"]:
            ax_spu.axvline(x=q_tar,
                           linestyle=":",
                           color="black")
    for fish_index in range(len(stat_data_dict["fish_list"])):
        ax_spu.plot(stat_data_dict["q_all"],
                    stat_data_dict["SPU"][fish_index],
                    label=stat_data_dict["fish_list"][fish_index],
                    color=color_list[fish_index],
                    linestyle=style_list[fish_index])
    ax_spu.set_ylabel("WUA by 100 m\n[m²]")
    ax_spu.yaxis.set_label_coords(-0.1, 0.5)  # adjust/align ylabel position
    ax_spu.set_xlabel("Discharge [m$^{3}$/sec]")

    # targ_q_all
    if stat_data_dict["targ_q_all"]:
        labels = ["Qtarg [m$^{3}$/sec]"]
        fig.legend(handler_map={plt.Line2D: HandlerLine2D(update_func=update_prop)},
                   labels=labels,
                   loc="lower left",
                   borderaxespad=0.5,
                   fancybox=False,
                   bbox_to_anchor=(0.73, 0.1))

    # LEGEND
    handles, labels = ax_vh.get_legend_handles_labels()
    fig.legend(handles=handles,
               labels=labels,
               loc="center left",
               borderaxespad=0.5,
               fancybox=False,
               bbox_to_anchor=(0.73, 0.5))

    plt.subplots_adjust(right=0.73)

    # save image
    name_pict = stat_mod + "_hv" + project_preferences['format']
    if os.path.exists(os.path.join(path_im, name_pict)):
        if not erase1:
            name_pict = stat_mod + "_hv" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + project_preferences['format']
    plt.savefig(os.path.join(path_im, name_pict),
                dpi=project_preferences['resolution'],
                transparent=True)

    # get data with mouse
    mplcursors.cursor()

    # finish process
    state.value = 100  # process finished

    # show
    plt.show()

    # remove file
    file_hdf5_path = os.path.join(path_prj, "hdf5", os.path.basename(path_prj) + '_' + stat_mod + '.hab')
    if os.path.exists(file_hdf5_path):
        os.remove(file_hdf5_path)


# all cases
def plot_map_node(state, data_xy, data_tin, data_plot, plot_string_dict, light_data_2d, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = light_data_2d.data_extent  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_mesh(state, data_xy, data_tin, data_plot, plot_string_dict, light_data_2d, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = light_data_2d.data_extent  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    n = len(data_plot)
    norm = mpl.colors.Normalize(vmin=data_min,
                                vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = data_xy[int(data_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    ax_map.add_collection(data_ploted)

    # color_bar
    color_bar = fig.colorbar(data_ploted,
                             cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_to_check_mesh_merging(hyd_xy, hyd_tin, sub_xy, sub_tin, sub_data, merge_xy, merge_tin, merge_data):
    """
    hyd : hydraulic
    sub : substrate
    merge : hyd + sub merging
    all numpy array
    xy = coordinates by nodes (2d numpy array of float)
    tin = connectivity table by mesh (3d numpy array of int)
    data = data by mesh (1d numpy array)
    """
    fig, axs = plt.subplots(2, 2, sharex=True, sharey=True)

    linewidth = 0.2
    hyd_edgecolor = "blue"
    sub_edgecolor = "orange"
    merge_edgecolor = "black"

    data_min = min(min(sub_data), min(merge_data))
    data_max = max(max(sub_data), max(merge_data))
    # hyd
    axs[0, 0].set_title("hydraulic")
    xlist = []
    ylist = []
    for i in range(0, len(hyd_tin)):
        pi = 0
        tin_i = hyd_tin[i]
        if len(tin_i) == 3:
            while pi < 2:  # we have all sort of xells, max eight sides
                # The conditions should be tested in this order to avoid to go out of the array
                p = tin_i[pi]  # we start at 0 in python, careful about -1 or not
                p2 = tin_i[pi + 1]
                xlist.extend([hyd_xy[p, 0], hyd_xy[p2, 0]])
                xlist.append(None)
                ylist.extend([hyd_xy[p, 1], hyd_xy[p2, 1]])
                ylist.append(None)
                pi += 1
            p = tin_i[pi]
            p2 = tin_i[0]
            xlist.extend([hyd_xy[p, 0], hyd_xy[p2, 0]])
            xlist.append(None)
            ylist.extend([hyd_xy[p, 1], hyd_xy[p2, 1]])
            ylist.append(None)
    axs[0, 0].plot(xlist, ylist, '-b', linewidth=linewidth, color=hyd_edgecolor)
    axs[0, 0].axis("scaled")  # x and y axes have same proportions

    # sub
    axs[0, 1].set_title("substrate")
    masked_array = np.ma.array(sub_data, mask=np.isnan(sub_data))  # create nan mask
    # data_min = masked_array.min()
    # data_max = masked_array.max()
    cmap = mpl.cm.get_cmap("jet")
    cmap.set_bad(color='black', alpha=1.0)
    n = len(sub_data)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = sub_xy[int(sub_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=linewidth, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    data_ploted.set_edgecolor(sub_edgecolor)
    axs[0, 1].add_collection(data_ploted)
    axs[0, 1].axis("scaled")  # x and y axes have same proportions

    # merge only mesh
    axs[1, 0].set_title("merge")
    xlist = []
    ylist = []
    for i in range(0, len(merge_tin)):
        pi = 0
        tin_i = merge_tin[i]
        if len(tin_i) == 3:
            while pi < 2:  # we have all sort of xells, max eight sides
                # The conditions should be tested in this order to avoid to go out of the array
                p = tin_i[pi]  # we start at 0 in python, careful about -1 or not
                p2 = tin_i[pi + 1]
                xlist.extend([merge_xy[p, 0], merge_xy[p2, 0]])
                xlist.append(None)
                ylist.extend([merge_xy[p, 1], merge_xy[p2, 1]])
                ylist.append(None)
                pi += 1
            p = tin_i[pi]
            p2 = tin_i[0]
            xlist.extend([merge_xy[p, 0], merge_xy[p2, 0]])
            xlist.append(None)
            ylist.extend([merge_xy[p, 1], merge_xy[p2, 1]])
            ylist.append(None)
    axs[1, 0].plot(xlist, ylist, '-b', linewidth=linewidth, color=merge_edgecolor)
    axs[1, 0].axis("scaled")  # x and y axes have same proportions

    # mesh with color
    axs[1, 1].set_title("merge (with color)")
    masked_array = np.ma.array(merge_data, mask=np.isnan(merge_data))  # create nan mask
    # data_min = masked_array.min()
    # data_max = masked_array.max()
    cmap = mpl.cm.get_cmap("jet")
    cmap.set_bad(color='black', alpha=1.0)
    n = len(merge_data)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = merge_xy[int(merge_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=linewidth, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    data_ploted.set_edgecolor(merge_edgecolor)
    axs[1, 1].add_collection(data_ploted)
    axs[1, 1].axis("scaled")  # x and y axes have same proportions

    plt.show()


# 3d
def view_mayavi(state, data_2d, data_2d_whole, varname, reach_number, unit_number, data_description,
                project_preferences):
    state.value = 100  # process finished
    # BOTOM
    bottom_mesh = mlab.triangular_mesh(data_2d_whole[reach_number][unit_number]["node"]["xy"][:, 0],
                                       data_2d_whole[reach_number][unit_number]["node"]["xy"][:, 1],
                                       data_2d_whole[reach_number][unit_number]["node"]["z"] * project_preferences[
                                           "vertical_exaggeration"],
                                       data_2d_whole[reach_number][unit_number]["mesh"]["tin"],
                                       representation="surface")  # , scalars=t

    # OTHER
    other_mesh = mlab.triangular_mesh(data_2d[reach_number][unit_number]["node"]["xy"][:, 0],
                                      data_2d[reach_number][unit_number]["node"]["xy"][:, 1],
                                      data_2d[reach_number][unit_number]["node"]["data"][varname].to_numpy() *
                                      project_preferences["vertical_exaggeration"],
                                      data_2d[reach_number][unit_number]["mesh"]["tin"],
                                      color=(0, 0, 1),
                                      representation="surface")  # , scalars=t

    # SHOW
    mlab.show()


# map node
def plot_map_elevation(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    data_min_str = len(str(data_min).split(".")[0])
    data_max_str = len(str(data_max).split(".")[0])
    if data_min_str > 2 or data_max_str > 2:  # two before decimal
        color_bar.ax.tick_params(labelsize=6)
    elif data_min_str > 1 or data_max_str > 1:  # two before decimal
        color_bar.ax.tick_params(labelsize=8)
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_height(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_velocity(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_conveyance(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_froude_number(state, data_xy, data_tin, data_plot, plot_string_dict, data_description,
                           project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_hydraulic_head(state, data_xy, data_tin, data_plot, plot_string_dict, data_description,
                            project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_water_level(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    bounds_nb = 50  # number of bound (color level)
    bounds = np.linspace(data_min, data_max, bounds_nb)  # create sequence list of bounds
    while not np.all(np.diff(bounds) > 0):  # check if constant or null
        bounds_nb += - 1  # remove one bound
        bounds = np.linspace(data_min, data_max, bounds_nb)  # recreate sequence list of bounds
    # all values are null
    if data_min == data_max and bounds_nb == 1:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         colors=colors.rgb2hex(cmap(0)), vmin=data_min, vmax=0.1,
                                         levels=np.array([0.0, 0.1]))
    # normal case
    else:
        data_ploted = ax_map.tricontourf(data_xy[:, 0], data_xy[:, 1], data_tin, data_plot,
                                         cmap=cmap, vmin=data_min, vmax=data_max, levels=bounds)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    data_min_str = len(str(data_min).split(".")[0])
    data_max_str = len(str(data_max).split(".")[0])
    if data_min_str > 2 or data_max_str > 2:  # two before decimal
        color_bar.ax.tick_params(labelsize=6)
    elif data_min_str > 1 or data_max_str > 1:  # two before decimal
        color_bar.ax.tick_params(labelsize=8)
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


# map mesh
def plot_map_onlymesh(state, data_xy, data_tin, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]

    # data
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # plot
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
    ax_map.plot(xlist, ylist, '-b', linewidth=0.1, color='blue')

    # color_bar
    ax_legend.remove()

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_slope_bottom(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    n = len(data_plot)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = data_xy[int(data_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    ax_map.add_collection(data_ploted)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_slope_energy(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 2
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    n = len(data_plot)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = data_xy[int(data_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    ax_map.add_collection(data_ploted)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_shear_stress(state, data_xy, data_tin, data_plot, plot_string_dict, data_description, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = masked_array.min()
    data_max = masked_array.max()
    decimal_nb = 0
    extent_list = list(map(float, data_description["data_extent"].split(", ")))  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))  # get color map
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    n = len(data_plot)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = data_xy[int(data_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    ax_map.add_collection(data_ploted)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_substrate(state, data_xy, data_tin, data_plot, plot_string_dict, light_data_2d, project_preferences):
    """
    The function to plot the substrate data, which was loaded before. This function will only work if the substrate
    data is given using the cemagref code.

    :param data_xy: the coordinate of the point
    :param data_tin: the connectivity table
    :param sub_pg: the information on subtrate by element for the "coarser part"
    :param sub_dom: the information on subtrate by element for the "dominant part"
    :param project_preferences: the figure option as a doctionnary
    :param xtxt: if the data was given in txt form, the orignal x data
    :param ytxt: if the data was given in txt form, the orignal y data
    :param subtxt: if the data was given in txt form, the orignal sub data
    :param path_im: the path where to save the figure
    :param reach_number: If we plot more than one reach, this is the reach number
    """
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # prepare data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    decimal_nb = 0
    extent_list = light_data_2d.data_extent  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = mpl.cm.get_cmap(project_preferences['color_map'])
    if light_data_2d.sub_classification_code == "Cemagref":
        max_class = 8
        listcathegories = list(range(1, max_class + 2))
    if light_data_2d.sub_classification_code == "Sandre":
        max_class = 12
        listcathegories = list(range(1, max_class + 2))

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    n = len(data_plot)
    norm = mpl.colors.BoundaryNorm(listcathegories, cmap.N)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = data_xy[int(data_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    ax_map.add_collection(data_ploted)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    listcathegories_stick = [x + 0.5 for x in range(1, color_bar.vmax)]
    listcathegories_stick_label = [x for x in range(1, color_bar.vmax)]
    color_bar.set_ticks(listcathegories_stick)
    color_bar.set_ticklabels(listcathegories_stick_label)
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


def plot_map_fish_habitat(state, data_xy, data_tin, data_plot, plot_string_dict, light_data_2d, project_preferences):
    mpl_map_change_parameters(project_preferences)

    # title and filename
    title = plot_string_dict["title"]
    variable_title = plot_string_dict["variable_title"]
    reach_title = plot_string_dict["reach_title"]
    unit_title = plot_string_dict["unit_title"]
    filename = plot_string_dict["filename"]
    colorbar_label = plot_string_dict["colorbar_label"]

    # data
    masked_array = np.ma.array(data_plot, mask=np.isnan(data_plot))  # create nan mask
    data_min = 0
    data_max = 1
    decimal_nb = 2
    extent_list = light_data_2d.data_extent  # get extent [xMin, yMin, xMax, yMax]

    # colors
    cmap = copy(mpl.cm.get_cmap(project_preferences['color_map']))
    cmap.set_bad(color='black', alpha=1.0)

    # pre_plot_map
    fig, ax_map, ax_legend = pre_plot_map(title, variable_title, reach_title, unit_title)

    # ax_map plot
    n = len(data_plot)
    norm = mpl.colors.Normalize(vmin=data_min, vmax=data_max)
    patches = []
    for i in range(0, n):
        verts = []
        for j in range(0, 3):
            verts_j = data_xy[int(data_tin[i][j]), :]
            verts.append(verts_j)
        polygon = Polygon(verts, closed=True)
        patches.append(polygon)
    data_ploted = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
    data_ploted.set_array(masked_array)
    ax_map.add_collection(data_ploted)

    # color_bar
    color_bar = fig.colorbar(data_ploted, cax=ax_legend,
                             format=ticker.FuncFormatter(lambda x_val, tick_pos: '%.*f' % (decimal_nb, x_val)))
    color_bar.set_label(colorbar_label)

    # post_plot_map
    post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state)


# plot tool
right_limit_position = 0.88
top_limit_position = 0.90
banner_position = (0.00, top_limit_position,  # x0, y0
                   right_limit_position, 1.00 - top_limit_position)  # width, height
north_position = (right_limit_position, top_limit_position,  # x0, y0
                  1.00 - right_limit_position, 1.00 - top_limit_position)  # width, height
legend_position = (right_limit_position, 1.00 - top_limit_position,  # x0, y0
                   1.00 - right_limit_position, 1.00 - (1.00 - top_limit_position) * 2)  # width, height
scale_position = (right_limit_position, 0.00,  # x0, y0
                  1.00 - right_limit_position, 1.00 - top_limit_position)  # width, height
map_position = (0.00, 0.00,  # x0, y0
                right_limit_position, top_limit_position)  # width, height
lwd_rect = 1.0


def mpl_map_change_parameters(project_preferences):
    mpl.rcParams["savefig.dpi"] = project_preferences["resolution"]  # change default resolution to save
    mpl.rcParams['agg.path.chunksize'] = 10000  # Exceeded cell block limit (set 'agg.path.chunksize' rcparam)"
    mpl.rcParams['figure.figsize'] = project_preferences['width'] / 2.54, project_preferences['height'] / 2.54
    mpl.rcParams['font.size'] = project_preferences['font_size']
    rc('font', **{'family': 'sans-serif', 'sans-serif': [project_preferences['font_family']]})
    mpl.rcParams['lines.linewidth'] = project_preferences['line_width']
    mpl.rcParams['axes.grid'] = project_preferences['grid']
    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams['axes.linewidth'] = 0.5  # set the value globally


def pre_plot_map(title, variable_title, reach_title, unit_title):
    # to debug/update plot after show (need fig.canvas.draw() and fig.canvas.flush_events() instead of plt.show())
    # plt.ion()
    # plot
    fig, ax_border = plt.subplots(1, 1)  # plot creation
    plt.get_current_fig_manager().set_window_title(title)  # set windows title

    # ax_border
    ax_border.name = "border"
    ax_border.set_position((0.0, 0.0, 1.0, 1.0))  # add axe
    rect = plt.Rectangle(
        (0.0, 0.0),
        1.0, 1.0,
        transform=ax_border.transAxes,
        color="black",
        fill=None
    )
    fig.patches.append(rect)

    # ax_banner
    ax_banner = fig.add_axes(banner_position)  # add axe
    ax_banner.name = "banner"
    ax_banner.xaxis.set_ticks([])  # remove ticks
    ax_banner.yaxis.set_ticks([])  # remove ticks
    ax_banner.text(0.01, 0.7, variable_title)  # variable_str
    ax_banner.text(0.01, 0.4, reach_title)  # reach
    ax_banner.text(0.01, 0.1, unit_title)  # unit

    # ax_north
    ax_north = fig.add_axes(north_position, frameon=False)
    ax_north.name = "north"
    ax_north.xaxis.set_ticks([])  # remove ticks
    ax_north.yaxis.set_ticks([])  # remove ticks
    north_im = plt.imread(os.path.join(os.getcwd(), "file_dep", "north.png"))
    ax_north.imshow(north_im)

    # ax_legend_border
    ax_legend_border = fig.add_axes(legend_position)
    ax_legend_border.name = "legend_border"
    ax_legend_border.xaxis.set_ticks([])  # remove ticks
    ax_legend_border.yaxis.set_ticks([])  # remove ticks
    ax_legend = inset_axes(ax_legend_border, width="20%", height="95%", loc=6)
    ax_legend.name = "legend"

    # ax_map
    ax_map = fig.add_axes(map_position, frameon=False)
    ax_map.name = "map"
    ax_map.xaxis.set_ticks([])  # remove ticks
    ax_map.yaxis.set_ticks([])  # remove ticks

    return fig, ax_map, ax_legend


def post_plot_map(fig, ax_map, extent_list, filename, project_preferences, state):
    """
    dataLim = data bbox minimum
    viewLim = data bbox set
    """
    # ax_map
    ax_map.axis("scaled")  # x and y axes have same proportions

    # compute axe_real_height and axe_real_width
    axe_real_height = project_preferences['height'] * top_limit_position / 100  # axe_real_height [meter]
    axe_real_width = project_preferences['width'] * right_limit_position / 100  # axe_real_width [meter]

    # compute data_height and data_width
    data_height = extent_list[3] - extent_list[1]  # data_height [meter]
    data_width = extent_list[2] - extent_list[0]  # data_width [meter]

    # add margin
    delta_x = data_height * 0.01  # +- margin
    delta_y = data_width * 0.01  # +- margin
    extent_list[0] = extent_list[0] - delta_x
    extent_list[2] = extent_list[2] + delta_x
    extent_list[1] = extent_list[1] - delta_y
    extent_list[3] = extent_list[3] + delta_y
    view_data_height = extent_list[3] - extent_list[1]  # view_data_height [meter]
    view_data_width = extent_list[2] - extent_list[0]  # view_data_width [meter]

    # change data extent size to fit the axe
    if view_data_height / view_data_width < axe_real_height / axe_real_width:
        view_data_height_wish = (view_data_width * axe_real_height) / axe_real_width
        delta_height = (view_data_height_wish - view_data_height) / 2
        view_data_height = view_data_height_wish
        extent_list[1] = extent_list[1] - delta_height
        extent_list[3] = extent_list[3] + delta_height
    elif view_data_height / view_data_width > axe_real_height / axe_real_width:
        view_data_width_wish = (view_data_height * axe_real_width) / axe_real_height
        delta_width = (view_data_width_wish - view_data_width) / 2
        view_data_width = view_data_width_wish
        extent_list[0] = extent_list[0] - delta_width
        extent_list[2] = extent_list[2] + delta_width

    # print("axe_real_height / axe_real_width", axe_real_height / axe_real_width)
    # print("view_data_height / view_data_width", view_data_height / view_data_width)
    # print("equality", axe_real_height / axe_real_width == view_data_height / view_data_width)

    # get extent
    xlim = (extent_list[0], extent_list[2])
    ylim = (extent_list[1], extent_list[3])

    # set extent
    ax_map.set_xlim(xlim)
    ax_map.set_ylim(ylim)

    # auto update size
    ax_map.callbacks.connect('xlim_changed', update_scalebar)
    # fig.canvas.mpl_connect('draw_event', update_scalebar)

    # ax_scale
    ax_scale = fig.add_axes(scale_position)
    ax_scale.name = "scale"
    ax_scale.xaxis.set_ticks([])  # remove ticks
    ax_scale.yaxis.set_ticks([])  # remove ticks
    scale_computed_int, scale_computed_str = compute_scale_value(fig, ax_map)  # compute_scale_value

    scale_computed_vertivcal_int = int(scale_computed_int / 10)  # scale_computed_vertivcal_int
    scalebar = AnchoredSizeBar(transform=ax_map.transData,
                               size=scale_computed_int,
                               label=str(scale_computed_int) + ' m',
                               loc=10,
                               sep=4,
                               frameon=False,
                               size_vertical=scale_computed_vertivcal_int,
                               fill_bar=False)  # AnchoredSizeBar
    ax_scale.add_artist(scalebar)

    # export
    if project_preferences['type_plot'] == "image export" or project_preferences['type_plot'] == "both":
        if not project_preferences['erase_id']:
            plt.savefig(os.path.join(project_preferences['path_figure'],
                                     filename + time.strftime("%d_%m_%Y_at_%H_%M_%S") + project_preferences['format']),
                        dpi=project_preferences['resolution'], transparent=True)

        else:
            test = remove_image(filename, project_preferences['path_figure'], project_preferences['format'])
            if not test:
                return
            plt.savefig(os.path.join(project_preferences['path_figure'], filename + project_preferences['format']),
                        dpi=project_preferences['resolution'],
                        transparent=True)
        state.value = 100  # process finished

    # output for plot_GUI
    state.value = 100  # process finished
    if project_preferences['type_plot'] == "interactive" or project_preferences['type_plot'] == "both":
        # fig.canvas.draw()
        # fig.canvas.flush_events()
        plt.show()
    if project_preferences['type_plot'] == "image export":
        plt.close(fig)


def update_scalebar(event):
    scale_computed_int, scale_computed_str = compute_scale_value(event.figure, event)  # compute_scale_value
    scale_computed_vertivcal_int = int(scale_computed_int / 10)  # scale_computed_vertivcal_int
    # ax_list
    ax_list = event.figure.get_axes()
    # get axe names
    ax_names_list = [ax.name for ax in ax_list]
    # get ax_scale
    ax_scale = ax_list[ax_names_list.index("scale")]
    # remove scalebar_old
    _ = ax_scale.artists[0].remove()
    # get ax_map
    ax_map = ax_list[ax_names_list.index("map")]
    # AnchoredSizeBar
    scalebar = AnchoredSizeBar(transform=ax_map.transData,
                               size=scale_computed_int,
                               label=str(scale_computed_int) + ' m',
                               loc=10,
                               sep=4,
                               frameon=False,
                               size_vertical=scale_computed_vertivcal_int,
                               fill_bar=False)
    ax_scale.add_artist(scalebar)


def compute_scale_value(fig, ax_map):
    bbox = ax_map.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    # measured
    axe_real_width, axe_real_height = bbox.width * 2.54 / 100, bbox.height * 2.54 / 100

    # display
    data_view_width = ax_map.viewLim.bounds[2]

    # compute scale int for one meter
    scale_computed_int_m = int(data_view_width / axe_real_width)

    # compute scale int for one centimeter
    if scale_computed_int_m * 0.01 < 1.0:
        scale_computed_num_cm = round(scale_computed_int_m * 0.01, 2)
    else:
        scale_computed_num_cm = int(scale_computed_int_m * 0.01)

    # compute scale str
    scale_computed_str = "1:" + str(scale_computed_int_m)

    return scale_computed_num_cm, scale_computed_str


def create_gif_from_files(state, variable, reach_name, unit_names, name_hdf5, project_preferences):
    path_im = project_preferences['path_figure']

    list_of_file_path = [os.path.join(path_im, name_hdf5[:-4] + "_" + reach_name + '_' + unit_name.replace(".",
                                                                                                           "_") + "_" + variable.replace(
        " ", "_") + "_map" + project_preferences['format']) for unit_name in unit_names]
    print("list_of_file_path", list_of_file_path)
    list_of_exist_tf = [False] * len(list_of_file_path)

    while not all(list_of_exist_tf):
        for file_index, file_path in enumerate(list_of_file_path):
            if os.path.isfile(file_path) and not list_of_exist_tf[file_index]:
                try:
                    Image.open(file_path)  # to wait the end of file creation
                    list_of_exist_tf[file_index] = True
                except OSError:
                    pass

    # old
    img, *imgs = [Image.open(file_path) for file_path in list_of_file_path]

    img.save(fp=os.path.join(path_im,
                             name_hdf5[:-4] + "_" + reach_name + "_" + variable.replace(" ", "_") + "_map" + ".gif"),
             format='GIF',
             append_images=imgs,
             save_all=True,
             duration=800,
             loop=0)

    # prog
    state.value = 100  # process finished


def get_colors_styles_line_from_nb_input(input_nb):
    """
    Get color_list and style_list for a given number of input.
    Total number of available color and style = colors_number * line_styles_base_list : 8 * 4 = 32
    :param input_nb: total number of input to plot.
    :return: color_list: by input
    :return: style_list: by input
    """
    colors_number = 8
    cm = mpl.cm.get_cmap('gist_ncar')
    color_base_list = [cm(i / colors_number) for i in range(colors_number)] * input_nb
    color_list = color_base_list[:input_nb]
    line_styles_base_list = ['solid', 'dotted', 'dashed', 'dashdot']  # 4 style
    style_list = []
    style_start = 0
    while len(style_list) < input_nb:
        if len(style_list) > colors_number - 1:
            colors_number = colors_number * 2
            style_start += style_start + 1
        style_list.append(line_styles_base_list[style_start])

    return color_list, style_list


def update_prop(handle, orig):
    handle.update_from(orig)
    x, y = handle.get_data()
    handle.set_data([np.mean(x)] * 2, [0, 2 * y[0]])


def main():
    print("aaa")


if __name__ == '__main__':
    main()


def create_map_plot_string_dict(name_hdf5, reach_name, unit_name, unit_type, variable, variable_unit, string_tr,
                                variable_info=""):
    # colorbar_label and variable_info
    if variable_info:
        colorbar_label = variable_info.split(" = ")[0] + " [" + variable_unit + "]"
        variable_info = " (" + variable_info + ")"
    else:
        colorbar_label = "[" + variable_unit + "]"

    # plot_string_dict
    plot_string_dict = dict(reach_name=reach_name,
                            unit_name=unit_name,
                            title=variable + ' - ' + reach_name + ' - ' + unit_name + " [" + unit_type + "]",
                            variable_title=variable.replace("_",
                                                            " ") + ' [' + variable_unit + ']' + " " + variable_info,
                            reach_title=string_tr[0] + " : " + reach_name,
                            unit_title=string_tr[1] + " : " + unit_name + " [" + unit_type.replace("m3/s",
                                                                                                   "$m^3$/s") + "]",
                            colorbar_label=colorbar_label,
                            filename=os.path.splitext(name_hdf5)[0] + "_" + reach_name + "_" + unit_name.replace(".",
                                                                                                                 "_") + '_' + variable.replace(
                                " ", "_") + "_map"
                            )
    return plot_string_dict


def create_biomodel_plot_string_dict(name_hdf5, reach_name, unit_name, unit_type, variable, variable_unit, string_tr,
                                     variable_info=""):
    # colorbar_label and variable_info
    if variable_info:
        colorbar_label = variable_info.split(" = ")[0] + " [" + variable_unit + "]"
        variable_info = " (" + variable_info + ")"
    else:
        colorbar_label = "[" + variable_unit + "]"

    # plot_string_dict
    plot_string_dict = dict(reach_name=reach_name,
                            unit_name=unit_name,
                            title=variable + ' - ' + reach_name + ' - ' + unit_name + " [" + unit_type + "]",
                            variable_title=variable.replace("_",
                                                            " ") + ' [' + variable_unit + ']' + " " + variable_info,
                            reach_title=string_tr[0] + " : " + reach_name,
                            unit_title=string_tr[1] + " : " + unit_name + " [" + unit_type.replace("m3/s",
                                                                                                   "$m^3$/s") + "]",
                            colorbar_label=colorbar_label,
                            filename=os.path.splitext(name_hdf5)[0] + "_" + reach_name + "_" + unit_name.replace(".",
                                                                                                                 "_") + '_' + variable.replace(
                                " ", "_") + "_map"
                            )
    return plot_string_dict


def remove_image(name, path, ext):
    """
    This is a small function used to erase images if erase_id is True. We have a function because different format
    czan be used and because it is done often in the functions above.

    :param name: the name of the file t be erase (without the extension)
    :param path: the path to the file
    :param format1: the type of format
    :return:
    """
    ext = [ext]

    for e in ext:
        if os.path.isfile(os.path.join(path, name + e)):
            try:
                os.remove(os.path.join(path, name + e))
            except PermissionError:
                print('Warning: Figures used by an other program. could not be erased \n')
                return False
    return True


def main():
    pass


if __name__ == '__main__':
    main()
