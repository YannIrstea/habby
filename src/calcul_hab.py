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
                        path_txt, path_out, path_im, q=[], print_cmd=False, fig_opt={}):

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
    :param path_out: the path where to save shapefile and paraview output
    :param path_im: the path where to save the image
    :param q: used in the second thread
    :param print_cmd: if True the print command is directed in the cmd, False if directed to the GUI
    :param fig_opt: the options to crete the figure if save_fig1d is True

    ** Technical comments**

    This function redirect the sys.stdout. The point of doing this is because this function will be call by the GUI or
    by the cmd. If it is called by the GUI, we want the output to be redirected to the windows for the log under HABBY.
    If it is called by the cmd, we want the print function to be sent to the command line. We make the switch here.
    """

    if not print_cmd:
        sys.stdout = mystdout = StringIO()
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    a = time.time()
    # calcuation habitat
    [vh_all_t_sp, vel_c_all_t, height_c_all_t, area_all, spu_all] = \
        calc_hab(hdf5_file, path_hdf5, pref_list, stages_chosen, path_bio, run_choice)
    b = time.time()

    if vh_all_t_sp == [-99]:
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

    # prepare name for the output (there is more or less one form by output)
    for id, n in enumerate(name_fish):
        name_fish[id] = n + '_' + stages_chosen[id]
    if len(hdf5_file) > 25:
        name_base = hdf5_file[: -25]
    else:
        name_base = hdf5_file

    # text output
    if create_text:
        save_hab_txt(hdf5_file, path_hdf5, vh_all_t_sp, vel_c_all_t, height_c_all_t, name_fish, path_txt, name_base)

        save_spu_txt(area_all, spu_all, name_fish, path_txt, name_base)
    c = time.time()

    # shape output
    if create_shape:
        save_hab_shape(hdf5_file, path_hdf5, vh_all_t_sp, vel_c_all_t, height_c_all_t,
                       name_fish_sh, path_out, name_base)

    # paraview outputs
    if create_para:
        new_create_vtk.habitat_to_vtu(name_base, path_out, path_hdf5, hdf5_file, vh_all_t_sp, height_c_all_t,
                                      vel_c_all_t, name_fish)
    d = time.time()


    # figure
    # 2d figure
    timestep = fig_opt['time_step']
    timestep = timestep.split(',')
    print(timestep)
    try:
        timestep = list(map(int, timestep))
    except ValueError:
        print('Error: Time step was not recognized. \n')
        return
    save_vh_fig_2d(hdf5_file, path_hdf5, vh_all_t_sp, path_im, name_fish, name_base, fig_opt, timestep)
    # 1d figure (done on the main thread, so not necessary)
    # save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base, fig_opt)
    e = time.time()

    print('Habitat calculation is finished. \n')
    print("Outputs and 2d figures created from the habitat calculation. 1d figure will be shown. \n")

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
    failload = [-99], [-99], [-99], [-99], [-99]
    vh_all_t_sp = []
    spu_all_t_sp = []
    vel_c_att_t = []
    height_c_all_t = []
    area_all_t = []
    found_stage = 0

    if len(bio_names) != len(stages):
        print('Error: Number of stage and species is not coherent. \n')
        return failload

    if len(bio_names) == 0:
        print('No fish species chosen. \n')
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
                    [vh_all_t,  vel_c_att_t, height_c_all_t, area_all_t, spu_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg,
                                      pref_vel, pref_height, pref_sub)
                elif opt == 1:  # dom
                    [vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all,inter_height_all, substrate_all_dom,
                                      pref_vel, pref_height, pref_sub)
                elif opt == 2:  # percentage
                    sub_per = load_hdf5.load_sub_percent(merge_name, path_merge)
                    if len(sub_per) == 1:
                        print('Error: Substrate data in percentage form is not found. Habitat by percentage cannot be'
                              ' computed. \n')
                        return failload
                    [vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t] = \
                        calc_hab_norm(ikle_all_t, point_all, inter_vel_all, inter_height_all, sub_per,
                                      pref_vel, pref_height, pref_sub, True)
                else:
                    print('Error: the calculation method is not found. \n')
                    return failload
                vh_all_t_sp.append(vh_all_t)
                spu_all_t_sp.append(spu_all_t)

        if found_stage == 0:
            print('Error: the name of the fish stage are not coherent \n')
            return failload

    b = time.time()


    return vh_all_t_sp, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t_sp


def calc_hab_norm(ikle_all_t, point_all_t, vel, height, sub, pref_vel, pref_height, pref_sub, percent=False):
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
    :return: vh of one life stage, area, habitat value

    """

    if len(height) != len(vel) or len(height) != len(sub):
        return [-99],[-99], [-99], [-99], [-99]

    vh_all_t = [[]] # time step 0 is whole profile, no data
    spu_all_t = [[]]
    area_all_t = [[]]
    height_c_all_t = [[[-1]]]
    vel_c_att_t = [[[-1]]]
    for t in range(1, len(height)):  # time step 0 is whole profile
        vh_all = []
        height_c = []
        vel_c = []
        area_all = []
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
        else:
            for r in range(0, len(height_t)):

                # preparation
                ikle = np.array(ikle_t[r])
                h = np.array(height_t[r])
                v = np.array(vel_t[r])
                s = np.array(sub_t[r])
                p = np.array(point_t[r])

                if len(ikle) == 0:
                    print('Error: The connectivity table was not well-formed (1) \n')
                    return [-99], [-99], [-99], [-99], [-99]
                if len(ikle[0]) < 3:
                    print('Error: The connectivity table was not well-formed (2) \n')
                    return  [-99],[-99], [-99], [-99], [-99]

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
                            s_pref_c = s_pref_st *s0/100
                        else:
                            s_pref_c += s0/100*s_pref_st
                else:
                    s_pref_c = find_pref_value(s, pref_sub)

                try:
                    vh = h_pref_c * v_pref_c * s_pref_c
                    vh = np.round(vh, 7)  # necessary for  shapefile, do not get above 8 digits of precision
                except ValueError:
                    print('Error: One time step misses substrate, velocity or water height value \n')
                    vh = [-99]
                spu_reach = np.sum(vh*area)

                vh_all.append(list(vh))
                vel_c.append(v_cell)
                height_c.append(h_cell)
                area_all.append(area_reach)
                spu_all.append(spu_reach)

        vh_all_t.append(vh_all)
        vel_c_att_t.append(vel_c)
        height_c_all_t.append(height_c)
        spu_all_t.append(spu_all)
        area_all_t.append(area_all)

    return vh_all_t, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t


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


def save_hab_txt(name_merge_hdf5, path_hdf5, vh_data, vel_data, height_data, name_fish, path_txt, name_base):
    """
    This function print the text output. We create one set of text file by time step. Each Reach is separated by the
    key work REACH follwoed by the reach number (strating from 0). There are three files by time steps: one file which
    gives the connectivity table (starting at 0), one file with the point coordinates in the
    coordinate systems of the hydraulic models (x,y), one file wiche gives the results.
    In all three files, the first column is the reach number. In the results files, the next columns are velocity,
    height, substrate, habitat value for each species.

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vel_data: the velocity by reach by time step on the cell (not node!)
    :param height_data: the height by reach by time step on the cell (not node!)
    :param vh_data: the habitat value data by speces by reach by tims tep
    :param name_fish: the list of fish latin name + stage
    :param path_txt: the path where to save the text file
    :param name_base: a string on which to base the name of the files
    """

    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle == [-99]:
        return

    # we do not print the first time step with the whole profile
    nb_reach = len(ikle[0])
    for t in range(1, len(ikle)):
        ikle_here = ikle[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            name1 = 'xy_' + 't_' + str(t) + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
            name2 = 'gridcell_' + 't_' + str(t) + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
            name3 = 'result_' + 't_' + str(t) + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'

            if os.path.exists(path_txt):
                name1 = os.path.join(path_txt, name1)
                name2 = os.path.join(path_txt, name2)
                name3 = os.path.join(path_txt, name3)

            # grid
            with open(name2,'wt', encoding='utf-8') as f:
                for r in range(0,  nb_reach):
                    ikle_here = ikle[t][r]
                    f.write('REACH ' + str(r)+'\n')
                    f.write('reach cell1 cell2 cell2'+'\n')
                    for c in ikle_here:
                        f.write(str(r) + ' ' + str(c[0]) + ' ' + str(c[1]) + ' ' + str(c[2]) + '\n')
            # point
            with open(name1, 'wt', encoding='utf-8') as f:
                for r in range(0,  nb_reach):
                    p_here = point[t][r]
                    f.write('REACH ' + str(r)+'\n')
                    f.write('reach x y'+'\n')
                    for p in p_here:
                        f.write(str(r) + ' ' + str(p[0]) + ' ' + str(p[1])+'\n')

            # result
            with open(name3, 'wt', encoding='utf-8') as f:
                for r in range(0, nb_reach):
                    v_here = vel_data[t][r]
                    h_here = height_data[t][r]
                    sub_pg = sub_pg_data[t][r]
                    sub_dom = sub_dom_data[t][r]
                    f.write('REACH ' + str(r) +'\n')
                    # header 1
                    header = 'reach cells velocity height coarser_substrate dominant_substrate'
                    for i in range(0, len(name_fish)):
                        header += ' VH'+str(i)
                    header += '\n'
                    f.write(header)
                    # header 2
                    header = '[] [] [m/s] [m] [Code_Cemagref] [Code_Cemagref]'
                    for i in name_fish:
                        i = i.replace(' ', '_')  # so space is always a separator
                        header += ' ' + i
                    header += '\n'
                    f.write(header)
                    # data
                    for i in range(0, len(v_here)):
                        vh_str = ''
                        for j in range(0, len(name_fish)):
                            try:
                                vh_str += str(vh_data[j][t][r][i]) + ' '
                            except IndexError:
                                print('Error: Results could not be written to text file. \n')
                                return
                        f.write(str(r) + ' ' + str(i) + ' ' + str(v_here[i]) + ' ' + str(h_here[i]) + ' ' +
                                str(sub_pg[i]) + ' ' +str(sub_dom[i]) + ' ' +vh_str + '\n')


def save_spu_txt(area_all, spu_all, name_fish, path_txt, name_base):
    """
    This function create a text files with the folowing columns: the tiem step, the reach number, the area of the
    reach and the spu for each fish species.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_txt: the path where to save the text file
    :param name_base: a string on which to base the name of the files
    """

    name = 'spu_' + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.txt'
    if os.path.exists(path_txt):
        name = os.path.join(path_txt, name)

    # open text to write
    with open(name, 'wt', encoding='utf-8') as f:

        # header
        header = 'time_step reach reach_area'
        for i in range(0, len(name_fish)):
            header += ' WUA' + str(i) + ' HV' + str(i)
        header += '\n'
        f.write(header)
        # header 2
        header = '[] [] [m2] [m2] []'
        for i in name_fish:
            i = i.replace(' ', '_')  # so space is always a separator
            header += ' ' + i + ' ' + i
        header += '\n'
        f.write(header)

        for t in range(0, len(area_all)):
            for r in range(0, len(area_all[t])):
                data_here = str(t) + ' ' + str(r) + ' ' + str(area_all[t][r])
                for i in range(0, len(name_fish)):
                    data_here += ' ' + str(spu_all[i][t][r])
                    data_here += ' ' + str(spu_all[i][t][r]/area_all[t][r])
                data_here += '\n'
                f.write(data_here)


def save_hab_shape(name_merge_hdf5, path_hdf5, vh_data, vel_data, height_data, name_fish_sh, path_shp, name_base):
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
    """
    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle == [[-99]]:
        return

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
                    w.field('hsi'+n, 'F', 10, 8)
                w.field('vel', 'F', 10, 8)
                w.field('water height', 'F', 10, 8)
                w.field('sub_coarser', 'F', 10, 8)
                w.field('sub_dom', 'F', 10, 8)

                # fill attribute
                for r in range(0, nb_reach):
                    vel = vel_data[t][r]
                    height = height_data[t][r]
                    sub_pg = sub_pg_data[t][r]
                    sub_dom = sub_dom_data[t][r]
                    ikle_r = ikle[t][r]
                    for i in range(0, len(ikle_r)):
                        data_here = ()
                        for j in range(0, len(name_fish_sh)):
                            try:
                                data_here +=(vh_data[j][t][r][i],)
                            except IndexError:
                                print('Error: Results could not be written to shape file \n')
                                return
                        data_here += vel[i], height[i], sub_pg[i], sub_dom[i]
                        # the * pass tuple to function argument
                        w.record(*data_here)

            w.autoBalance = 1
            name1 = name_base + 't_' + str(t) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
            w.save(os.path.join(path_shp, name1))


def save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base, fig_opt={}):
    """
    This function creates the figure of the spu as a function of time for each reach. if there is only one
    time step, it reverse to a bar plot. Otherwise it is a line plot.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_im: the path where to save the image
    :param fig_opt: the dictionnary with the figure options
    :param name_base: a string on which to base the name of the files
    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']

    if len(spu_all) != len(name_fish):
        print('Error: Number of fish name and number of WUA data is not coherent \n')
        return

    try:
        nb_reach = len(max(area_all, key=len)) # we might have failed time step
    except TypeError:  # or all failed time steps -99
        # print('Error: No reach found. Is the hdf5 corrupted? \n')
        return

    for id,n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

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
            plt.ylabel('WUA [m^2]')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            plt.title('Weighted Usable Area for the Reach ' + str(r))
            # VH
            fig.add_subplot(212)
            if data_bar:
                data_bar2 = np.array(data_bar)
                plt.bar(y_pos, data_bar2/area_all[-1], 0.5)
                plt.xticks(y_pos + 0.25, name_fish)
            plt.ylabel('HV (WUA/A) []')
            plt.xlim((y_pos[0] - 0.1, y_pos[-1] + 0.8))
            plt.title('Habitat value for the Reach ' + str(r))
            name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            plt.tight_layout()
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name +'.png'), dpi=fig_opt['resolution'])
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'])
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'])

    # many time step - lines
    elif len(area_all) > 2:
        data_plot = []
        for r in range(0, nb_reach):
            # SPU
            fig = plt.figure()
            fig.add_subplot(211)
            for s in range(0, len(spu_all)):
                data_plot = []
                t_all = []
                for t in range(0, len(area_all)):
                    if spu_all[s][t]:
                        data_plot.append(spu_all[s][t][r])
                        t_all.append(t)
                plt.plot(t_all,data_plot, label=name_fish[s])
            plt.xlabel('Time step [ ]')
            plt.ylabel('WUA [m^2]')
            plt.title('Weighted Usable Area for the Reach ' + str(r))
            plt.legend()
            # VH
            fig.add_subplot(212)
            for s in range(0, len(spu_all)):
                data_plot = []
                t_all = []
                for t in range(0, len(area_all)):
                    if spu_all[s][t]:
                        data_plot.append(spu_all[s][t][r]/area_all[t][r])
                        t_all.append(t)
                plt.plot(t_all, data_plot, label=name_fish[s])
            plt.xlabel('Time step [ ]')
            plt.ylabel('HV (WUA/A) []')
            plt.title('Habitat value for the Reach ' + str(r))
            plt.ylim(ymin=-0.02)
            plt.legend()
            plt.tight_layout()
            name = 'WUA_' + name_base + '_Reach_' + str(r) + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S")
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name + '.png'), dpi=fig_opt['resolution'])
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name + '.pdf'), dpi=fig_opt['resolution'])
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name + '.jpg'), dpi=fig_opt['resolution'])


def save_vh_fig_2d(name_merge_hdf5, path_hdf5, vh_all_t_sp, path_im, name_fish, name_base, fig_opt={}, time_step=[-1]):
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

    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()
    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format1 = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']

    b= 0
    # get grid data from hdf5
    [ikle_all_t, point_all_t, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle_all_t == [-99]:
        return
    # format name fish
    for id, n in enumerate(name_fish):
        name_fish[id] = n.replace('_', ' ')

    # create the figure for each species, and each time step
    all_patches = []
    for sp in range(0, len(vh_all_t_sp)):
        vh_all_t = vh_all_t_sp[sp]
        rt = 0

        for t in time_step:
            ikle_t = ikle_all_t[t]
            point_t = point_all_t[t]
            if t > len(vh_all_t):
                vh_t = vh_all_t[t]
            else:
                return
            fig, ax = plt.subplots(1) # new figure
            norm = mpl.colors.Normalize(vmin=0, vmax=1)

            for r in range(0, len(vh_t)):
                ikle = ikle_t[r]
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
                        plt.title('Habitat Value of ' + name_fish[sp] + '- Last Time Step')
                    else:
                        plt.title('Habitat Value of ' + name_fish[sp] + '- Time Step: ' + str(t))
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
                cb1.set_label('HSI []')

            # save figure
            name_fig = 'HSI_' + name_fish[sp] + '_' + name_base + '_t_' + str(t) + \
                       time.strftime("%d_%m_%Y_at_%H_%M_%S")
            if format1 == 0 or format1 == 1:
                plt.savefig(os.path.join(path_im, name_fig + '.png'), dpi=fig_opt['resolution'])
            if format1 == 0 or format1 == 3:
                plt.savefig(os.path.join(path_im, name_fig + '.pdf'), dpi=fig_opt['resolution'])
            if format1 == 2:
                plt.savefig(os.path.join(path_im, name_fig + '.jpg'), dpi=fig_opt['resolution'])


