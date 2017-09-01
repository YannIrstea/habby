import os
import numpy as np
import bisect
import time
import sys
from io import StringIO
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
from src import load_hdf5
from src import bio_info
import shapefile
from src import new_create_vtk
from src_GUI import output_fig_GUI


def calc_hab_and_output(hdf5_file, path_hdf5, pref_list, stages_chosen,  name_fish, name_fish_sh, run_choice, path_bio,
                        path_txt, path_shp, path_para, path_im, q=[], print_cmd=False, fig_opt={}, path_im_bio='', xmlfiles=[]):

    """
    This function calculates the habitat and create the outputs for the habitat calculation. The outputs are: text
    output (spu and cells by cells), shapefile, paraview files, one 2d figure by time step. The 1d figure
    is done on the main thread as we want to show it to the user on the GUI. This function is called by bio_info_GUI.py
    on a second thread to minimize the freezing on the GUI.

    :param hdf5_file: the name of the hdf5 with the results
    :param path_hdf5: the path to the merged file
    :param pref_list: the name of the xml biological data
    :param stages_chosen: the stage chosen (youngs, adults, etc.). List with the same length as bio_names.
    :param name_fish: the name of the chosen fish
    :param name_fish_sh: In a shapefile, max 8 character for the column name. Hence, a modified name_fish is needed.
    :param run_choice: an int fron 0 to n. Gives which calculation method should be used
    :param path_bio: The path to the biological folder (with all files given in bio_names)
    :param path_txt: the path where to save the text file
    :param path_shp: the path where to save shapefile
    :param path_para: the path where to save paraview output
    :param path_im: the path where to save the image
    :param path_im_bio: the path where are the image of the fish
    :param q: used in the second thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param fig_opt: the options to crete the figure if save_fig1d is True
    :param xmlfiles: the list of the xml file (only useful to get the preference curve report, so not used by habby_cmd)

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line. We make the switch here.
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    # calcuation habitat
    [vh_all_t_sp, vel_c_all_t, height_c_all_t, area_all, spu_all, area_c_all] = \
        calc_hab(hdf5_file, path_hdf5, pref_list, stages_chosen, path_bio, run_choice)
    b = time.time()

    if vh_all_t_sp == [-99] or isinstance(name_fish[0], int):
        if q:
            sys.stdout = sys.__stdout__
            q.put([mystdout, [-99], [-99], [-99], [-99], [-99]])
            return
        else:
            return

    # to get which output must be created
    if fig_opt['text_output'] == 'True':  # from the xml, string only
        create_text = True
    else:
        create_text = False
    if fig_opt['shape_output'] == 'True':  # from the xml, string only
        create_shape = True
    else:
        create_shape = False
    if fig_opt['paraview'] == 'True':  # from the xml, string only
        create_para = True
    else:
        create_para = False
    if fig_opt['fish_info'] == 'True':  # from the xml, string only
        create_info = True
    else:
        create_info = False
    if fig_opt['erase_id'] == 'True':
        erase_id = True
    else:
        erase_id = False

    # prepare name for the output (there is more or less one form by output)
    all_name = ''
    for id, n in enumerate(name_fish):
        name_fish[id] = n + '_' + stages_chosen[id]
        all_name += name_fish_sh[id]
    if len(hdf5_file) > 25:
        name_base = hdf5_file[:25] + '_' + all_name
    else:
        name_base = hdf5_file[:-3] + '_' + all_name

    # get the time step name
    # get time step name if they exists
    sim_name = load_hdf5.load_timestep_name(hdf5_file, path_hdf5)

    # text output
    if create_text:
        save_hab_txt(hdf5_file, path_hdf5, vh_all_t_sp, vel_c_all_t, height_c_all_t, name_fish, path_txt, name_base,
                     sim_name, erase_id)
    save_spu_txt(area_all, spu_all, name_fish, path_txt, name_base, sim_name, fig_opt['language'], erase_id)

    # shape output
    if create_shape:
        if run_choice == 2:
            perc = True
        else:
            perc = False
        save_hab_shape(hdf5_file, path_hdf5, vh_all_t_sp, vel_c_all_t, height_c_all_t,
                       name_fish_sh, path_shp, name_base, sim_name, save_perc=perc, erase_id=erase_id)

    # paraview outputs
    if create_para:
        new_create_vtk.habitat_to_vtu(name_base, path_para, path_hdf5, hdf5_file, vh_all_t_sp, height_c_all_t,
                                      vel_c_all_t, name_fish, erase_id)

    # pdf with information on the fish
    if create_info and len(xmlfiles) > 0:
        bio_info.create_pdf(xmlfiles, stages_chosen, path_bio, path_im_bio, path_txt, fig_opt)

    # figure done always
    # 2d figure and histogram of hydraulic data for certain timesteps
    timestep = fig_opt['time_step']
    if not isinstance(timestep, (list, tuple)):
        timestep = timestep.split(',')
    try:
        timestep = list(map(int, timestep))
    except ValueError:
        print('Error: Time step was not recognized. \n')
        return
    if -1 in timestep and len(vh_all_t_sp[0]) == 2 and 1 in timestep:
        del timestep[1]
    # figure
    save_vh_fig_2d(hdf5_file, path_hdf5, vh_all_t_sp, path_im, name_fish, name_base, fig_opt, timestep, sim_name,
                   erase_id=erase_id)
    plot_hist_hydro(hdf5_file, path_hdf5, vel_c_all_t, height_c_all_t, area_c_all, fig_opt, path_im, timestep,
                    name_base, sim_name, erase_id)
    # 1d figure (done on the main thread, so not necessary)
    # save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base, fig_opt)

    # saving hdf5 data of the habitat value
    load_hdf5.add_habitat_to_merge(hdf5_file, path_hdf5, vh_all_t_sp, vel_c_all_t, height_c_all_t,
                                   name_fish)

    print('# Habitat calculation is finished. \n')
    if not print_cmd:
        print("Outputs and 2d figures created from the habitat calculation. 1d figure will be shown. \n")
    else:
        print("Outputs and 2d figures created from the habitat calculation. \n")
    if not print_cmd:
        sys.stdout = sys.__stdout__
    if q:
        q.put([mystdout, area_all, spu_all, name_fish, name_base, vh_all_t_sp])
        return
    else:
        return


def calc_hab(merge_name, path_merge, bio_names, stages, path_bio, opt):
    """
    This function calculates the habitat value. It loads substrate and hydrology data from an hdf5 files and it loads
    the biology data from the xml files. It is possible to have more than one stage by xml file (usually the three
    stages are in the xml files). There are more than one method to calculte the habitat so the parameter opt indicate
    which metho to use. 0-> usde coarser substrate, 1 -> use dominant substrate

    :param merge_name: the name of the hdf5 with the results
    :param path_merge: the path to the merged file
    :param bio_names: the name of the xml biological data
    :param stages: the stage chosen (youngs, adults, etc.). List with the same length as bio_names.
    :param path_bio: The path to the biological folder (with all files given in bio_names
    :param opt: an int fron 0 to n. Gives which calculation method should be used
    :return: the habiatat value for all species, all time, all reach, all cells.
    """
    failload = [-99], [-99], [-99], [-99], [-99], [-99]
    vh_all_t_sp = []
    spu_all_t_sp = []
    vel_c_att_t = []
    height_c_all_t = []
    area_all_t = []  # area by reach
    area_c_all_t = []  # area by cell for each reach each time step
    found_stage = 0

    if len(bio_names) != len(stages):
        print('Error: Number of stage and species is not coherent. \n')
        return failload

    if len(bio_names) == 0:
        print('Error: No fish species chosen. \n')
        return failload

    # load merge
    # test if file exists in load_hdf5_hyd
    [ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom] = \
        load_hdf5.load_hdf5_hyd(merge_name, path_merge, True)
    if ikle_all_t == [-99]:
        return failload

    a = time.time()

    for idx, bio_name in enumerate(bio_names):

        # load bio data
        xmlfile = os.path.join(path_bio, bio_name)
        [pref_height, pref_vel, pref_sub, code_fish, name_fish, stade_bios] = bio_info.read_pref(xmlfile)
        if pref_height == [-99]:
            print('Error: preference file could not be loaded. \n')
            return failload

        for idx2, stade_bio in enumerate(stade_bios):

            if stages[idx] == stade_bio:
                found_stage += 1
                pref_height = pref_height[idx2]
                pref_vel = pref_vel[idx2]
                pref_sub = pref_sub[idx2]

                # calcul (one function for each calculation options)
                if opt == 0:  # pg
                    # optmization possibility: feed_back the vel_c_att_t and height_c_all_t and area_all_t
                    [vh_all_t,  vel_c_att_t, height_c_all_t, area_all_t, spu_all_t, area_c_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg,
                                      pref_vel, pref_height, pref_sub)
                elif opt == 1:  # dom
                    [vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t, area_c_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all,inter_height_all, substrate_all_dom,
                                      pref_vel, pref_height, pref_sub)
                elif opt == 2:  # percentage
                    sub_per = load_hdf5.load_sub_percent(merge_name, path_merge)
                    if len(sub_per) == 1:
                        print('Error: Substrate data in percentage form is not found. Habitat by percentage cannot be'
                              ' computed. \n')
                        return failload
                    [vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t, area_c_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all, inter_height_all, sub_per,
                                      pref_vel, pref_height, pref_sub, True)
                elif opt == 3:
                    [vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t, area_c_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_dom,
                                      pref_vel, pref_height, pref_sub, False, False)
                else:
                    print('Error: the calculation method is not found. \n')
                    return failload
                vh_all_t_sp.append(vh_all_t)
                spu_all_t_sp.append(spu_all_t)

        if found_stage == 0:
            print('Error: the name of the fish stage are not coherent \n')
            return failload

    b = time.time()

    return vh_all_t_sp, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t_sp, area_c_all_t


def calc_hab_norm(ikle_all_t, point_all_t, vel, height, sub, pref_vel, pref_height, pref_sub, percent=False,
                  take_sub =True):
    """
    This function calculates the habitat suitiabilty index (f(H)xf(v)xf(sub)) for each and the SPU which is the sum of
    all habitat suitability index weighted by the cell area for each reach. It is called by clac_hab_norm.

    :param ikle_all_t: the connectivity table for all time step, all reach
    :param point_all_t: the point of the grid
    :param vel: the velocity data for all time step, all reach
    :param height: the water height data for all time step, all reach
    :param sub: the substrate data (can be coarser or dominant substrate based on function's call)
    :param pref_vel: the preference index for the velcoity (for one life stage)
    :param pref_sub: the preference index for the substrate  (for one life stage)
    :param pref_height: the preference index for the height  (for one life stage)
    :param percent: If True, the variable sub is in percent form, not in the form dominant/coarser
    :param take_sub: If False, the substrate data is neglected.
    :return: vh of one life stage, area, habitat value

    """

    if len(height) != len(vel) or len(height) != len(sub):
        return [-99], [-99], [-99], [-99], [-99], [-99]
    s_pref_c = 1

    vh_all_t = [[]]  # time step 0 is whole profile, no data
    spu_all_t = [[]]
    area_all_t = [[]]
    height_c_all_t = [[[-1]]]
    vel_c_att_t = [[[-1]]]
    area_c_all_t = [[[-1]]]

    for t in range(1, len(height)):  # time step 0 is whole profile
        vh_all = []
        height_c = []
        vel_c = []
        area_all = []
        area_c_all = []
        spu_all = []
        height_t = height[t]
        vel_t = vel[t]
        sub_t = sub[t]
        ikle_t = ikle_all_t[t]
        point_t = point_all_t[t]
        # if failed before
        if vel_t[0][0] == -99:
            vh_all = [[-99]]
            vel_c = [[-99]]
            height_c = [[-99]]
            area = [[-99]]
        else:
            for r in range(0, len(height_t)):

                # preparation
                ikle = np.array(ikle_t[r])
                h = np.array(height_t[r])
                v = np.array(vel_t[r])
                s = np.array(sub_t[r])
                p = np.array(point_t[r])

                if len(ikle) == 0:
                    print('Warning: The connectivity table was not well-formed for one reach (1) \n')
                    vh = [-99]
                    v_cell = [-99]
                    h_cell = [-99]
                    area_reach = [-99]
                    spu_reach = -99
                    area = [-99]
                elif len(ikle[0]) < 3:
                    print('Warning: The connectivity table was not well-formed for one reach (2) \n')
                    vh = [-99]
                    v_cell = [-99]
                    h_cell = [-99]
                    area_reach = [-99]
                    spu_reach = -99
                    area = [-99]
                else:

                    # get data by cells
                    v1 = v[ikle[:, 0]]
                    v2 = v[ikle[:, 1]]
                    v3 = v[ikle[:, 2]]
                    v_cell = 1.0 / 3.0 * (v1 + v2 + v3)

                    h1 = h[ikle[:, 0]]
                    h2 = h[ikle[:, 1]]
                    h3 = h[ikle[:, 2]]
                    h_cell = 1.0 / 3.0 * (h1 + h2 + h3)

                    # get area (based on Heron's formula)
                    p1 = p[ikle[:, 0], :]
                    p2 = p[ikle[:, 1], :]
                    p3 = p[ikle[:, 2], :]

                    d1 = np.sqrt((p2[:, 0] - p1[:, 0])**2 + (p2[:, 1] - p1[:, 1])**2)
                    d2 = np.sqrt((p3[:, 0] - p2[:, 0])**2 + (p3[:, 1] - p2[:, 1])**2)
                    d3 = np.sqrt((p3[:, 0] - p1[:, 0])**2 + (p3[:, 1] - p1[:, 1])**2)
                    s2 = (d1 + d2 + d3)/2
                    area = s2 * (s2-d1) * (s2-d2) * (s2-d3)
                    area[area < 0] = 0  # -1e-11, -2e-12, etc because some points are so close
                    area = area**0.5
                    area_reach = np.sum(area)
                    # get pref value
                    h_pref_c = find_pref_value(h_cell, pref_height)
                    v_pref_c = find_pref_value(v_cell, pref_vel)
                    if percent:
                        for st in range(0, 8):
                            s0 = s[:, st]
                            sthere = np.zeros((len(s0),)) + st+1
                            s_pref_st = find_pref_value(sthere, pref_sub)
                            if st == 0:
                                s_pref_c = s_pref_st * s0 / 100
                            else:
                                s_pref_c += s0/100*s_pref_st
                    else:
                        s_pref_c = find_pref_value(s, pref_sub)
                    try:
                        if take_sub:
                            vh = h_pref_c * v_pref_c * s_pref_c
                        else:
                            vh = h_pref_c * v_pref_c
                        vh = np.round(vh, 7)  # necessary for  shapefile, do not get above 8 digits of precision
                    except ValueError:
                        print('Error: One time step misses substrate, velocity or water height value \n')
                        vh = [-99]
                    spu_reach = np.sum(vh*area)

                vh_all.append(list(vh))
                vel_c.append(v_cell)
                height_c.append(h_cell)
                area_all.append(area_reach)
                area_c_all.append(area)
                spu_all.append(spu_reach)

        vh_all_t.append(vh_all)
        vel_c_att_t.append(vel_c)
        height_c_all_t.append(height_c)
        spu_all_t.append(spu_all)
        area_all_t.append(area_all)
        area_c_all_t.append(area_c_all)

    return vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t, area_c_all_t


def find_pref_value(data, pref):
    """
    This function finds the preference value associated with the data for each cell. For this, it finds the last
    point of the preference curve under the data and it makes a linear interpolation with the next data to
    find the preference value. As preference value is sorted, it uses the module bisect to accelerate the process.

    :param data: the data on the cells (for one time step, on reach)
    :param pref: the pref data [pref, class data]
    """

    pref = np.array(pref)
    pref_f = pref[1]  # the preferene value
    pref_d = pref[0]  # the data linked with it
    pref_data = []

    for d in data:
        indh = bisect.bisect(pref_d, d) - 1  # about 3 time quicker than max(np.where(x_ini <= x_p[i]))
        if indh < 0:
            indh = 0
        dmin = pref_d[indh]
        prefmin = pref_f[indh]
        if indh < len(pref_d) - 1:
            dmax = pref_d[indh + 1]
            prefmax = pref_f[indh + 1]
            if dmax == dmin:  # does not happen theorically
                pref_data_here = prefmin
            else:
                a1 = (prefmax - prefmin) / (dmax - dmin)
                b1 = prefmin - a1 * dmin
                pref_data_here = a1 * d + b1
                # This is a test to reproduce lammi result as best as possible
                # if pref_data_here > 0.98:
                #     pref_data_here = 1
                # if pref_data_here < 0.02:
                #     pref_data_here = 0
                if pref_data_here < 0 or pref_data_here > 1:
                    # the linear interpolation sometimes creates value like -5.55e-17
                    if -1e-3 < pref_data_here < 0:
                        pref_data_here = 0
                    elif 1 < pref_data_here < 1+1e10:
                        pref_data_here = 1
                    else:
                        print('Warning: preference data is not between 0 and 1. \n')
            pref_data.append(pref_data_here)
        else:
            pref_data.append(pref_f[indh])

    pref_data = np.array(pref_data)

    return pref_data


def save_hab_txt(name_merge_hdf5, path_hdf5, vh_data, vel_data, height_data, name_fish, path_txt, name_base,
                 sim_name=[], erase_id=False):
    """
    This function print the text output. We create one set of text file by time step. Each Reach is separated by the
    key work REACH follwoed by the reach number (strating from 0). There are three files by time steps: one file which
    gives the connectivity table (starting at 0), one file with the point coordinates in the
    coordinate systems of the hydraulic models (x,y), one file wiche gives the results.
    In all three files, the first column is the reach number. In the results files, the next columns are velocity,
    height, substrate, habitat value for each species. Use tab instead of space to help with excel import.

    The name and the form of the files do not change with the chosen language. The idea is that these files are quite big
    and that they will mostly be used by computer program. So it is easier for the user if the name and form is coherent.

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vel_data: the velocity by reach by time step on the cell (not node!)
    :param height_data: the height by reach by time step on the cell (not node!)
    :param vh_data: the habitat value data by speces by reach by tims tep
    :param name_fish: the list of fish latin name + stage
    :param path_txt: the path where to save the text file
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the simulation/time step (list of strings)
    :param erase_id: If True, we erase old text file from identical hydraulic model
    """

    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle == [-99]:
        return

    if not os.path.exists(path_txt):
        print('Error: the path to save the text file do not exists. \n')
        return

    if len(sim_name) > 0 and len(sim_name) != len(ikle) - 1:
        sim_name = []

    # we do not print the first time step with the whole profile
    nb_reach = len(ikle[0])
    for t in range(1, len(ikle)):
        ikle_here = ikle[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            # choose the name of the text file
            if not erase_id:
                if not sim_name:
                    name1 = 'xy_' + 't_' + str(t) + '_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") \
                            + '.txt'
                    name2 = 'gridcell_' + 't_' + str(t)+ '_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") \
                            + '.txt'
                    name3 = 'result_' + 't_' + str(t) + '_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") \
                            + '.txt'
                else:
                    name1 = 'xy_' + 't_' + sim_name[t-1] + '_' + name_base + '_' + \
                            time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    name2 = 'gridcell_' + 't_' + sim_name[t-1] + '_' + name_base + '_' + \
                            time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
                    name3 = 'result_' + 't_' + sim_name[t-1] + '_' + name_base + '_' + \
                            time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
            else:
                if not sim_name:
                    name1 = 'xy_' + 't_' + str(t) + '_' + name_base + '.txt'
                    name2 = 'gridcell_' + 't_' + str(t) + '_' + name_base + '.txt'
                    name3 = 'result_' + 't_' + str(t) + '_' + name_base + '.txt'
                else:
                    name1 = 'xy_' + 't_' + sim_name[t - 1] + '_' + name_base + '.txt'
                    name2 = 'gridcell_' + 't_' + sim_name[t - 1] + '_' + name_base + '.txt'
                    name3 = 'result_' + 't_' + sim_name[t - 1] + '_' + name_base + '.txt'
                if os.path.isfile(os.path.join(path_txt, name1)):
                    os.remove(os.path.join(path_txt, name1))
                if os.path.isfile(os.path.join(path_txt, name2)):
                    os.remove(os.path.join(path_txt, name2))
                if os.path.isfile(os.path.join(path_txt, name3)):
                    os.remove(os.path.join(path_txt, name3))
            name1 = os.path.join(path_txt, name1)
            name2 = os.path.join(path_txt, name2)
            name3 = os.path.join(path_txt, name3)

            # grid
            with open(name2,'wt', encoding='utf-8') as f:
                for r in range(0,  nb_reach):
                    ikle_here = ikle[t][r]
                    f.write('REACH ' + str(r)+'\n')
                    f.write('reach\tcell1\tcell2\tcell3'+'\n')
                    for c in ikle_here:
                        f.write(str(r) + '\t' + str(c[0]) + '\t' + str(c[1]) + '\t' + str(c[2]) + '\n')
            # point
            with open(name1, 'wt', encoding='utf-8') as f:
                for r in range(0,  nb_reach):
                    p_here = point[t][r]
                    f.write('REACH ' + str(r)+'\n')
                    f.write('reach\tx\ty'+'\n')
                    for p in p_here:
                        f.write(str(r) + '\t' + str(p[0]) + '\t' + str(p[1])+'\n')

            # result
            with open(name3, 'wt', encoding='utf-8') as f:
                for r in range(0, nb_reach):
                    v_here = vel_data[t][r]
                    h_here = height_data[t][r]
                    sub_pg = sub_pg_data[t][r]
                    sub_dom = sub_dom_data[t][r]
                    f.write('REACH ' + str(r) + '\n')
                    # header 1
                    header = 'reach\tcells\tvelocity\theight\tcoarser_substrate\tdominant_substrate'
                    for i in range(0, len(name_fish)):
                        header += '\tVH'+str(i)
                    header += '\n'
                    f.write(header)
                    # header 2
                    header = '[]\t[]\t[m/s]\t[m]\t[Code_Cemagref]\t[Code_Cemagref]'
                    for i in name_fish:
                        i = i.replace(' ', '_')  # so space/tab is only a separator
                        header += '\t' + i
                    header += '\n'
                    f.write(header)
                    # data
                    for i in range(0, len(v_here)):
                        vh_str = ''
                        for j in range(0, len(name_fish)):
                            try:
                                vh_str += str(vh_data[j][t][r][i]) + '\t'
                            except IndexError:
                                print('Error: Results could not be written to text file. \n')
                                return
                        f.write(str(r) + '\t' + str(i) + '\t' + str(v_here[i]) + '\t' + str(h_here[i]) + '\t' +
                                str(sub_pg[i]) + '\t' + str(sub_dom[i]) + '\t' + vh_str + '\n')


def save_spu_txt(area_all, spu_all, name_fish, path_txt, name_base, sim_name=[], lang=0, erase_id=False):
    """
    This function create a text files with the folowing columns: the tiem step, the reach number, the area of the
    reach and the spu for each fish species. Use tab instead of space to help with excel import.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_txt: the path where to save the text file
    :param name_base: a string on which to base the name of the files
    :param sim_name: the name of the time step
    :param lang: an int which indicates the chosen language (0 is english)
    :param erase_id: If True, we erase old text file from identical hydraulic model
    """

    if not os.path.exists(path_txt):
        print('Error: the path to the text file is not found. Text files not created \n')

    if not erase_id:
        if lang == 0:
            name = 'wua_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
        else:
            name = 'spu_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
    else:
        if lang == 0:
            name = 'wua_' + name_base + '.txt'
        else:
            name = 'spu_' + name_base + '.txt'
        if os.path.isfile(os.path.join(path_txt, name)):
            os.remove(os.path.join(path_txt, name))

    name = os.path.join(path_txt, name)
    if len(sim_name) > 0 and len(sim_name) != len(area_all)-1:
        sim_name = []

    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:

        # header
        if lang == 0:
            header = 'time_step\treach\treach_area'
        else:
            header = 'pas_de_temps\ttroncon\taire_troncon'
        for i in range(0, len(name_fish)):
            if lang == 0:
                header += '\tWUA' + str(i) + '\tHV' + str(i)
            else:
                header += '\tSPU' + str(i) + '\tVH' + str(i)
        header += '\n'
        f.write(header)
        # header 2
        header = '[?]\t[]\t[m2]'
        for i in name_fish:
            header += '\t[m2]\t[]'
        header +='\n'
        f.write(header)
        # header 3
        header = 'all\tall\tall '
        for i in name_fish:
            i = i.replace(' ', '_')  # so space is always a separator
            header += '\t' + i + '\t' + i
        header += '\n'
        f.write(header)

        for t in range(0, len(area_all)):
            for r in range(0, len(area_all[t])):  # at t=0, whole profile len(area_all[t]) = 0
                if not sim_name:
                    data_here = str(t) + '\t' + str(r) + '\t' + str(area_all[t][r])
                else:
                    data_here = sim_name[t-1] + '\t' + str(r) + '\t' + str(area_all[t][r])
                for i in range(0, len(name_fish)):
                    data_here += '\t' + str(spu_all[i][t][r])
                    data_here += '\t' + str(spu_all[i][t][r]/area_all[t][r])
                data_here += '\n'
                f.write(data_here)


def save_hab_shape(name_merge_hdf5, path_hdf5, vh_data, vel_data, height_data, name_fish_sh, path_shp, name_base,
                   sim_name=[], save_perc=False, erase_id=False):
    """
    This function create the output in the form of a shapefile. It creates one shapefile by time step. It put
    all the reaches together. If there is overlap between reaches, it does not care. It create an attribute table
    with the habitat value, velocity, height, substrate coarser, substrate dominant. It also create a shapefile
    0 with the whole profile without data.

    The name of the column of the attribute table should be less than 10 character. Hence, the variable name_fish
    has been adapted to be shorter. The shorter name_fish is called name_fish_sh.

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vel_data: the velocity by reach by time step on the cell (not node!)
    :param height_data: the height by reach by time step on the cell (not node!)
    :param vh_data: the habitat value data by speces by reach by tims tep
    :param name_fish_sh: the list of fish latin name + stage
    :param path_shp: the path where to save the shpaefile
    :param name_base: a string on which to base the name of the files
    :param sim_name: the time step's name if not 0,1,2,3
    :param save_perc: It true the substrate in percentage will be added to the shapefile
    :param erase_id: If True, we erase old text file from identical hydraulic model
    """
    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle == [[-99]]:
        return

    if len(sim_name) > 0 and len(sim_name) != len(ikle) - 1:
        sim_name = []

    if save_perc:
        sub_per_data = load_hdf5.load_sub_percent(name_merge_hdf5, path_hdf5)

    # we do not print the first time step with the whole profile
    nb_reach = len(ikle[0])
    for t in range(1, len(ikle)):
        ikle_here = ikle[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            w = shapefile.Writer(shapefile.POLYGON)
            w.autoBalance = 1

            # get the triangle
            for r in range(0, nb_reach):
                ikle_r = ikle[t][r]
                point_here = point[t][r]
                for i in range(0, len(ikle_r)):
                    p1 = list(point_here[ikle_r[i][0]])
                    p2 = list(point_here[ikle_r[i][1]])
                    p3 = list(point_here[ikle_r[i][2]])
                    w.poly(parts=[[p1, p2, p3, p1]])  # the double [[]] is important or it bugs, but why?

            if t > 0:
                # attribute
                for n in name_fish_sh:
                    w.field('hsi'+n, 'F')
                w.field('velocity', 'F')
                w.field('water heig', 'F')
                w.field('conveyance', 'F')
                w.field('sub_coarser', 'F')
                w.field('sub_dom', 'F')
                if save_perc:
                    for i in range(0, 8):  # cemagref code
                        w.field('sub_cl_'+str(i+1), 'F')

                # fill attribute
                for r in range(0, nb_reach):
                    vel = vel_data[t][r]
                    height = height_data[t][r]
                    sub_pg = sub_pg_data[t][r]
                    sub_dom = sub_dom_data[t][r]
                    if save_perc:
                        sub_per = sub_per_data[t][r]
                    ikle_r = ikle[t][r]
                    for i in range(0, len(ikle_r)):
                        data_here = ()
                        for j in range(0, len(name_fish_sh)):
                            try:
                                data_here +=(vh_data[j][t][r][i],)
                            except IndexError:
                                print('Error: Results could not be written to shape file \n')
                                return
                        data_here += vel[i], height[i], vel[i]*height[i], sub_pg[i], sub_dom[i]
                        if save_perc:
                            for j in range(0, 8):
                                try:
                                    data_here += (sub_per[i][j],)
                                except IndexError:
                                    print(' Warnign: Substrate data by percentage could not be found. '
                                          'Shapefile not created.\n')
                                    return
                        # the * pass tuple to function argument
                        w.record(*data_here)

            w.autoBalance = 1
            if not erase_id:
                if not sim_name:
                    name1 = name_base + '_t_' + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
                else:
                    name1 = name_base + '_t_' + sim_name[t-1] + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
            else:
                if not sim_name:
                    name1 = name_base + '_t_' + str(t) + '.shp'
                else:
                    name1 = name_base + '_t_' + sim_name[t - 1] + '.shp'
                if os.path.isfile(os.path.join(path_shp,name1)):
                    os.remove(os.path.join(path_shp, name1))

            w.save(os.path.join(path_shp, name1))


def save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base, fig_opt={}, sim_name=[], erase_id=False):
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
    :param erase_id: If True, figure from identical simuation are erased
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

    if len(spu_all) != len(name_fish):
        print('Error: Number of fish name and number of WUA data is not coherent \n')
        return

    try:
        nb_reach = len(max(area_all, key=len)) # we might have failed time step
    except TypeError:  # or all failed time steps -99
        # print('Error: No reach found. Is the hdf5 corrupted? \n')
        return

    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    if sim_name and len(area_all)-1 != len(sim_name):
        sim_name = []

    # one time step - bar
    if len(area_all) == 1 or len(area_all) == 2:
        for r in range(0, nb_reach):
            # SPU
            data_bar = []
            for s in range(0, len(name_fish)):
                data_bar.append(spu_all[s][1][r])
            y_pos = np.arange(len(spu_all))
            fig = plt.figure()
            fig.add_subplot(211)
            if data_bar:
                data_bar2 = np.array(data_bar)
                plt.bar(y_pos, data_bar2, 0.5)
                plt.xticks(y_pos+0.25, name_fish)
            if fig_opt['language'] == 0:
                plt.ylabel('WUA [m^2]')
            if fig_opt['language'] == 1:
                plt.ylabel('SPU [m^2]')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            if fig_opt['language'] == 0:
                plt.title('Weighted Usable Area for the Reach ' + str(r))
            if fig_opt['language'] == 1:
                plt.title('Surface Ponderée Utile pour le Troncon: ' + str(r))
            # VH
            fig.add_subplot(212)
            if data_bar:
                data_bar2 = np.array(data_bar)
                plt.bar(y_pos, data_bar2/area_all[-1], 0.5)
                plt.xticks(y_pos + 0.25, name_fish)
            if fig_opt['language'] == 0:
                plt.ylabel('HV (WUA/A) []')
            if fig_opt['language'] == 1:
                plt.ylabel('HV (SPU/A) []')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            if fig_opt['language'] == 0:
                plt.title('Habitat value for the Reach ' + str(r))
            if fig_opt['language'] == 1:
                plt.title("Valeur d'Habitat:  " + str(r))
            if not erase_id:
                name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_base + '_Reach_' + str(r)
                remove_image(name, path_im, format1)
            plt.tight_layout()
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
            fig = plt.figure()
            fig.add_subplot(211)
            for s in range(0, len(spu_all)):
                data_plot = []
                t_all = []
                for t in range(0, len(area_all)):
                    if spu_all[s][t] and spu_all[s][t][r] != -99:
                        data_plot.append(spu_all[s][t][r])
                        sum_data_spu[s][t] += spu_all[s][t][r]
                        t_all.append(t)
                t_all_s = t_all
                plt.plot(t_all, data_plot, label=name_fish[s], marker=mar)
            if fig_opt['language'] == 0:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('WUA [m^2]')
                plt.title('Weighted Usable Area for the Reach ' + str(r))
            elif fig_opt['language'] == 1:
                plt.xlabel('Pas de temps/débit [ ]')
                plt.ylabel('SPU [m^2]')
                plt.title('Surface Ponderée pour le troncon ' + str(r))
            plt.legend(fancybox=True, framealpha=0.5)  # make the legend transparent
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
            ax = fig.add_subplot(212)
            t_all = []
            for s in range(0, len(spu_all)):
                data_plot = []
                t_all = []
                for t in range(0, len(area_all)):
                    if spu_all[s][t] and spu_all[s][t][r] != -99:
                        data_here = spu_all[s][t][r]/area_all[t][r]
                        data_plot.append(data_here)
                        sum_data_spu_div[s][t] += data_here
                        t_all.append(t)
                plt.plot(t_all, data_plot, label=name_fish[s], marker=mar)
            if fig_opt['language'] == 0:
                plt.xlabel('Computational step [ ]')
                plt.ylabel('HV (WUA/A) []')
                plt.title('Habitat Value for the Reach ' + str(r))
            elif fig_opt['language'] == 1:
                plt.xlabel('Pas de temps/débit [ ]')
                plt.ylabel('HV (SPU/A) []')
                plt.title("Valeur d'habitat pour le troncon " + str(r))
            plt.ylim(ymin=-0.02)
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
            plt.tight_layout()
            if not erase_id:
                name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_base + '_Reach_' + str(r)
                remove_image(name, path_im, format1)
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
            plt.ylim(ymin=-0.02)
            plt.tight_layout()
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
            if not erase_id:
                name = 'WUA_' + name_base + '_All_Reach_'+ time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                name = 'WUA_' + name_base + '_All_Reach_'
                remove_image(name, path_im, format1)
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=fig_opt['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'], transparent=True)


def save_vh_fig_2d(name_merge_hdf5, path_hdf5, vh_all_t_sp, path_im, name_fish, name_base, fig_opt={}, time_step=[-1],
                   sim_name=[], save_fig=True, erase_id=False):
    """
    This function creates 2D map of the habitat value for each species at
    the time step asked. All reaches are ploted on the same figure.

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vh_all_t_sp: the habitat value for all reach all time step all species
    :param path_im: the path where to save the figure
    :param name_fish: the name and stage of the studied species
    :param name_base: the string on which to base the figure name
    :param fig_opt: the dictionnary with the figure options
    :param time_step: which time step should be plotted
    :param sim_name: the name of the time step if not 0,1,2,3
    :param save_fig: If True the figure is saved

    """

    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42  # to make them editable in Adobe Illustrator

    b= 0
    # get grid data from hdf5
    [ikle_all_t, point_all_t, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle_all_t == [-99]:
        return
    # format name fish
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    if max(time_step)-1 > len(sim_name):
        sim_name = []

    # create the figure for each species, and each time step
    all_patches = []
    for sp in range(0, len(vh_all_t_sp)):
        vh_all_t = vh_all_t_sp[sp]
        rt = 0

        for t in time_step:
            try:
                ikle_t = ikle_all_t[t]
            except IndexError:
                print('Warning: Figure not created for one time step as the time step was not found \n')
                continue
            point_t = point_all_t[t]
            if abs(t) < len(vh_all_t):
                vh_t = vh_all_t[t]
                fig, ax = plt.subplots(1)  # new figure
                norm = mpl.colors.Normalize(vmin=0, vmax=1)

                for r in range(0, len(vh_t)):
                    try:
                        ikle = ikle_t[r]
                    except IndexError:
                        print('Number of reach is not coherent. Could not plot figure. \n')
                        return
                    if len(ikle) < 3:
                        pass
                    else:
                        coord_p = point_t[r]
                        vh = vh_t[r]

                        # plot the habitat value
                        cmap = plt.get_cmap(fig_opt['color_map2'])
                        colors = cmap(vh)
                        if sp == 0: # for optimization (the grid is always the same for each species)
                            n = len(vh)
                            patches = []
                            for i in range(0, n):
                                verts = []
                                for j in range(0, 3):
                                    verts_j = coord_p[int(ikle[i][j]), :]
                                    verts.append(verts_j)
                                polygon = Polygon(verts, closed=True, edgecolor='w')
                                patches.append(polygon)
                            if len(vh_all_t_sp) > 1:
                                all_patches.append(patches)
                        else:
                            patches = all_patches[rt]

                        collection = PatchCollection(patches, linewidth=0.0, norm=norm, cmap=cmap)
                        #collection.set_color(colors) too slow
                        collection.set_array(np.array(vh))
                        ax.add_collection(collection)
                        ax.autoscale_view()
                        # cbar = plt.colorbar()
                        # cbar.ax.set_ylabel('Substrate')
                        if r == 0:
                            plt.xlabel('x coord []')
                            plt.ylabel('y coord []')
                            if t == -1:
                                if not sim_name:
                                    if fig_opt['language'] == 0:
                                        plt.title('Habitat Value of ' + name_fish[sp] + '- Last Computational Step')
                                    elif fig_opt['language'] == 1:
                                        plt.title("Valeur d'Habitat pour "+ name_fish[sp] + '- Dernière Simulation')
                                else:
                                    if fig_opt['language'] == 0:
                                        plt.title('Habitat Value of ' + name_fish[sp] + '- Computational Step: ' +
                                                  sim_name[-1])
                                    elif fig_opt['language'] == 1:
                                        plt.title("Valeur d'Habitat pour " + name_fish[sp] + '- Pas de temps/débit: ' +
                                                  sim_name[-1])
                            else:
                                if not sim_name:
                                    if fig_opt['language'] == 0:
                                        plt.title('Habitat Value of ' + name_fish[sp] + '- Computational Step: ' + str(t))
                                    elif fig_opt['language'] == 1:
                                        plt.title("Valeur d'Habitat pour " + name_fish[sp] + '- Pas de temps/débit: '
                                                  + str(t))
                                else:
                                    if fig_opt['language'] == 0:
                                        plt.title('Habitat Value of ' + name_fish[sp] + '- Copmutational Step: '
                                                  + sim_name[t-1])
                                    elif fig_opt['language'] == 1:
                                        plt.title("Valeur d'Habitat pour " + name_fish[sp] + '- Pas de temps/débit: ' +
                                                  sim_name[t-1])
                        ax1 = fig.add_axes([0.92, 0.2, 0.015, 0.7])  # posistion x2, sizex2, 1= top of the figure
                        rt +=1

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
                            cb1.set_label('HSI []')
                        elif fig_opt['language'] == 1:
                            cb1.set_label('VH []')

                # save figure
                if save_fig:
                    if not erase_id:
                        if not sim_name :
                            name_fig = 'HSI_' +  '_' + name_base + '_t_' + str(t) + '_' +\
                                       time.strftime("%d_%m_%Y_at_%H_%M_%S")
                        elif t-1 >= 0 and sim_name[t - 1]:
                            name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + sim_name[t - 1] + '_' +\
                                       time.strftime("%d_%m_%Y_at_%H_%M_%S")
                        elif t == -1:
                            name_fig = 'HSI_' +  '_' + name_base + '_t_' + sim_name[-1] + '_' + \
                                       time.strftime("%d_%m_%Y_at_%H_%M_%S")
                        else:
                            name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + str(t) + '_' + \
                                       time.strftime("%d_%m_%Y_at_%H_%M_%S")
                    else:
                        if not sim_name:
                            name_fig = 'HSI_' +  '_' + name_base + '_t_' + str(t)
                        elif t - 1 >= 0 and sim_name[t - 1]:
                            name_fig = 'HSI_' +  '_' + name_base + '_t_' + sim_name[t - 1]
                        elif t == -1:
                            name_fig = 'HSI_' + '_' + name_base + '_t_' + sim_name[-1]
                        else:
                            name_fig = 'HSI_' + '_' + name_base + '_t_' + str(t)
                        remove_image(name_fig, path_im, format1)

                    if format1 == 0 or format1 == 1:
                        plt.savefig(os.path.join(path_im, name_fig + '.png'), dpi=fig_opt['resolution'],
                                    transparent=True)
                    if format1 == 0 or format1 == 3:
                        plt.savefig(os.path.join(path_im, name_fig + '.pdf'), dpi=fig_opt['resolution'],
                                    transparent=True)
                    if format1 == 2:
                        plt.savefig(os.path.join(path_im, name_fig + '.jpg'), dpi=fig_opt['resolution'],
                                    transparent=True)


def plot_hist_hydro(hdf5_file, path_hdf5, vel_c_all_t, height_c_all_t, area_c_all_t, fig_opt, path_im, timestep,
                    name_base, sim_name=[], erase_id=False):
    """
    This function plots an historgram of the hydraulic and substrate data for the selected timestep. This historgramm
    is weighted by the area of the cell. The data is based on the height and velocity data by cell and not on the node.

    :param hdf5_file: the name of the hdf5 file
    :param path_hdf5: the path to this file
    :param vel_c_all_t: the velcoity for all reach all time step by cell
    :param height_c_all_t: the water height for all reach all time step by cell
    :param area_c_all_t: the aire of cells for all reach, all time step
    :param fig_opt: the figure options
    :param path_im: the path where to save the images
    :param timestep: a list with the time step to be plotted
    :param name_base: the base on which to form the figure name
    :param sim_name: the name of the time steps when not 0,1,2,3
    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']
    mpl.rcParams['pdf.fonttype'] = 42 # to make fifgure ediable in adobe illustrator

    if max(timestep)-1 > len(sim_name):
        sim_name = []

    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(hdf5_file, path_hdf5, True)
    if ikle == [[-99]]:
        return

    # we do not print the first time step with the whole profile

    for t in timestep:
        try:
            ikle_here = ikle[t][0]
        except IndexError:
            print('Error: Figure not created. Number of time step was not coherent with hydrological info.\n')
            return
        if len(ikle_here) < 2:  # time step failed
            pass
        else:
            vel_all = vel_c_all_t[t]
            height_all = height_c_all_t[t]
            sub_pg_all = sub_pg_data[t]
            area_all = area_c_all_t[t]

            for r in range(0, len(vel_all)):  # each reach
                if r == 0:
                    vel_app = list(vel_all[0])
                    height_app = list(height_all[0])
                    sub_pg_app = list(sub_pg_all[0])
                    area_app = list(area_all[0])
                else:
                    vel_app.extend(list(vel_all[r]))
                    height_app.extend(list(height_all[r]))
                    sub_pg_app.extend(list(sub_pg_all[r]))
                    area_app.extend(list(area_all[r]))

            fig = plt.figure()
            # velocity
            fig.add_subplot(221)
            plt.hist(vel_app, 20, weights=area_app, facecolor='blue')
            if fig_opt['language'] == 0:
                if t == -1:
                    plt.suptitle('Last Computational Step')
                else:
                    plt.suptitle('Computational Step: ' + str(t))
                plt.title('Velocity by Cells')
                plt.xlabel('velocity [m/sec]')
                plt.ylabel('number of occurence')
            elif fig_opt['language'] == 1:
                if t == -1:
                    plt.suptitle('Histogramme de Données Hydrauliques - Dernier Pas de Temps/Débit')
                else:
                    plt.suptitle('Histogramme de Données Hydrauliques - Pas de Temps/Débit: ' + str(t))
                plt.title('Vitesse par cellule')
                plt.xlabel('vitesse [m/sec]')
                plt.ylabel('fréquence')
            # height
            fig.add_subplot(222)
            plt.hist(height_app, 20, weights=area_app, facecolor='aquamarine')
            if fig_opt['language'] == 0:
                plt.title('Height by cells')
                plt.xlabel('velocity [m/sec]')
                plt.ylabel('number of occurence')
            elif fig_opt['language'] == 1:
                plt.title("Hauteur d'eau par cellule")
                plt.xlabel('hauteur [m]')
                plt.ylabel('fréquence')
            # substrate
            fig.add_subplot(224)
            plt.hist(sub_pg_app, weights=area_app, facecolor='lightblue', bins=np.arange(0.5, 8.5))
            if fig_opt['language'] == 0:
                plt.title('Coarser substrate data')
                plt.xlabel('substrate - code cemagref')
                plt.ylabel('number of occurence')
            elif fig_opt['language'] == 1:
                plt.title('Données de substrat - Plus gros')
                plt.xlabel('substrat - code cemagref')
                plt.ylabel('fréquence')
            # debit unitaire
            fig.add_subplot(223)
            q_unit = np.array(vel_app) * np.array(height_app)
            plt.hist(q_unit, 20, weights=area_app, facecolor='deepskyblue')
            if fig_opt['language'] == 0:
                plt.title('Elementary flow')
                plt.xlabel('v * h * 1m [m$^{3}$/sec]')
                plt.ylabel('number of occurence')
            elif fig_opt['language'] == 1:
                plt.title('Début unitaire')
                plt.xlabel('v * h * 1m [m$^{3}$/sec]')
                plt.ylabel('fréquence')

            plt.tight_layout(rect=[0., 0., 1, 0.95])
            if not erase_id:
                if not sim_name:
                    name = 'Histogramm_' + name_base + '_t_' + str(t) + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                elif t-1 >=0:
                    name = 'Histogramm_' + name_base + '_t_' + sim_name[t-1] + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                elif t ==-1:
                    name = 'Histogramm_' + name_base + '_t_' + sim_name[-1] + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
                else:
                    name = 'Histogramm_' + name_base + '_t_' + str(t) + '_All_Reach_' + \
                           time.strftime("%d_%m_%Y_at_%H_%M_%S")
            else:
                if not sim_name:
                    name = 'Histogramm_' + name_base + '_t_' + str(t) + '_All_Reach_'
                elif t - 1 >= 0:
                    name = 'Histogramm_' + name_base + '_t_' + sim_name[t - 1] + '_All_Reach_'
                elif t == -1:
                    name = 'Histogramm_' + name_base + '_t_' + sim_name[-1] + '_All_Reach_'
                else:
                    name = 'Histogramm_' + name_base + '_t_' + str(t) + '_All_Reach_'
                remove_image(name, path_im, format1)
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=fig_opt['resolution'], transparent=True)
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'], transparent=True)
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'], transparent=True)


def remove_image(name, path, format1):
    """
    This is a small function used to erase images if erase_id is True. We have a function because different format
    czan be used and because it is done often in the functions above.

    :param name: the name of the file t be erase (without the extension)
    :param path: the path to the file
    :param format1: the type of format
    :return:
    """
    if format1 == 0:
        ext = ['.png', '.pdf']
    elif format1 ==1:
        ext = ['.png']
    elif format1 ==2:
        ext = ['jpg']
    elif format1 ==3:
        ext = ['.pdf']
    else:
        return
    for e in ext:
        if os.path.isfile(os.path.join(path, name+e)):
            os.remove(os.path.join(path, name+e))

