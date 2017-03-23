import os
import numpy as np
import bisect
import time
import matplotlib.pyplot as plt
from src import load_hdf5
from src import bio_info
import shapefile


def calc_hab(merge_name, path_merge, bio_names, stages, path_bio, opt):
    """
    This function calculates the habitat value. It loads substrate and hydrology datqa from an hdf5 files and it loads
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

    if len(bio_names) != len(stages):
        print('Error: Number of stage and species is not coherent. \n')
        return failload

    # load merge
    # test if file exists in load_hdf5_hyd
    [ikle_all_t, point_all, inter_vel_all, inter_height_all, substrate_all_pg, substrate_all_dom] = \
        load_hdf5.load_hdf5_hyd(merge_name, path_merge, True)
    if ikle_all_t == [-99]:
        return failload

    for idx, bio_name in enumerate(bio_names):

        # load bio data
        xmlfile = os.path.join(path_bio, bio_name)
        [pref_height, pref_vel, pref_sub, code_fish, name_fish, stade_bios] = bio_info.read_pref(xmlfile)
        if pref_height == [-99]:
            return

        for idx2, stade_bio in enumerate(stade_bios):
            if stages[idx] == stade_bio:
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
                else:
                    print('Error: the calculation method is not found. \n')
                    return failload
                vh_all_t_sp.append(vh_all_t)
                spu_all_t_sp.append(spu_all_t)

    return vh_all_t_sp, vel_c_att_t, height_c_all_t, area_all_t, spu_all_t_sp


def calc_hab_norm(ikle_all_t, point_all_t, vel, height, sub, pref_vel, pref_height, pref_sub):
    """
    This function calculates the habitat suitiabilty index (f(H)*f(v)*f(sub)) for each and the SPU which is the sum of
    all hbitat suitability index weighted by the cell area for each reach

    :param ikle_all_t: the connectivity table for all time step, all reach
    :param point_all_t: the point of the grid
    :param vel: the velocity data for all time step, all reach
    :param height: the water height data for all time step, all reach
    :param sub: the substrate data (can be coarser or dominant substrate based on function's call)
    :param pref_vel: the preference index for the velcoity (for one life stage)
    :param pref_sub: the preference index for the substrate  (for one life stage)
    :param pref_height:the preference index for the height  (for one life stage)
    :return: vh of one life stage, area, habitat value
    """

    if len(height) != len(vel) or len(height) != len(sub):
        return [-99],[-99], [-99], [-99], [-99]

    vh_all_t = [[]] # time step 0 is whole profile
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
                area = (s2 * (s2-d1) * (s2-d2) * (s2-d3))
                area[area < 0] = 0  # -1e-11, -2e-12, etc because some points are so close
                area = area**0.5
                area_reach = np.sum(area)
                # get pref value
                h_pref_c = find_pref_value(h_cell, pref_height)
                v_pref_c = find_pref_value(v_cell, pref_vel)
                s_pref_c = find_pref_value(s, pref_sub)
                vh = h_pref_c * v_pref_c * s_pref_c
                spu_reach = 1/area_reach * np.sum(vh*area)

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

    :param data: the data on the cell
    :param pref: the pref data [pref, class data]
    """

    pref = np.array(pref)
    pref_f = pref[1]  # the preferene value
    pref_d = pref[0]  # the data linked with it
    pref_data = []

    for d in data:
        indh = bisect.bisect(pref_d, d) - 1  # about 3 time quicker than max(np.where(x_ini <= x_p[i]))
        dmin = pref_d[indh]
        prefmin = pref_f[indh]
        if indh < len(pref_d) - 1:
            dmax = pref_d[indh + 1]
            prefmax = pref_f[indh + 1]
            if dmax == dmin:  # does not happen theorically
                pref_data_here = prefmin
            else:
                a1 = (prefmax - prefmin) / (dmax - dmin)
                b1 = prefmax - a1 * dmax
                pref_data_here = a1 * d + b1
                if pref_data_here < 0 or pref_data_here >1+1e-10:
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
                            vh_str += str(vh_data[j][t][r][i]) + ' '
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
            header += ' WUA' + str(i)
        header += '\n'
        f.write(header)
        # header 2
        header = '[] [] [m2] '
        for i in name_fish:
            i = i.replace(' ', '_')  # so space is always a separator
            header += ' ' + i
        header += '\n'
        f.write(header)

        for t in range(0, len(area_all)):
            for r in range(0, len(area_all[t])):
                data_here = str(t) + ' ' + str(r) + ' ' + str(area_all[t][r])
                for i in range(0, len(name_fish)):
                    data_here += ' ' + str(spu_all[i][t][r])
                data_here += '\n'
                f.write(data_here)


def save_hab_shape(name_merge_hdf5, path_hdf5, vh_data, vel_data, height_data, name_fish, path_shp, name_base):
    """
    This function create the output in the form of a shapefile. It creates one shapefile by time step. It put
    all the reaches together. If there is overlap between reaches, it does not care. It create an attribute table
    with the habitat value, velocity, height, substrate coarser, substrate dominant. It also create a shapefile
    0 with the whole profile without data

    :param name_merge_hdf5: the name of the hdf5 merged file
    :param path_hdf5: the path to the hydrological hdf5 data
    :param vel_data: the velocity by reach by time step on the cell (not node!)
    :param height_data: the height by reach by time step on the cell (not node!)
    :param vh_data: the habitat value data by speces by reach by tims tep
    :param name_fish: the list of fish latin name + stage
    :param path_shp: the path where to save the shpaefile
    :param name_base: a string on which to base the name of the files
    """
    [ikle, point, blob, blob, sub_pg_data, sub_dom_data] = \
        load_hdf5.load_hdf5_hyd(name_merge_hdf5, path_hdf5, True)
    if ikle == [-99]:
        return

        # we do not print the first time step with the whole profile
    nb_reach = len(ikle[0])
    for t in range(0, len(ikle)):
        ikle_here = ikle[t][0]
        if len(ikle_here) < 2:
            print('Warning: One time step failed. \n')
        else:
            w = shapefile.Writer(shapefile.POLYGON)

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
                for n in name_fish:
                    n = n.replace(' ', '_')
                    w.field('hsi_'+n, 'F', 10, 8)
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
                    for i in range(0, len(ikle_r)):
                        data_here = ()
                        for j in range(0, len(name_fish)):
                           data_here +=(vh_data[j][t][r][i],)
                        data_here += vel[i], height[i], sub_pg[i], sub_dom[i]
                        # the * pass tuple to function argument
                        w.record(*data_here)

            w.autoBalance = 1
            name1 = name_base + 't_' + str(t) + name_base + '_' + time.strftime("%d_%m_%Y_at_%H_%M_%S") + '.shp'
            w.save(os.path.join(path_shp, name1))


def save_hab_paraview():
    pass


def save_hab_fig_spu(area_all, spu_all, name_fish, path_im, name_base):
    """
    This function creates the figure of the spu as a function of time for each reach. if there is only one
    time step, it reverse to a bar plot. Otherwise it is a line plot.

    :param area_all: the area for all reach
    :param spu_all: the "surface pondere utile" (SPU) for each reach
    :param name_fish: the list of fish latin name + stage
    :param path_imt: the path where to save the image
    :param name_base: a string on which to base the name of the files
    """


    # one time step - bar
    if len(area_all) == 1:
        data_bar = []
        for r in range(0, len(area_all[0])):
            data_bar = []
            for s in range(0, len(spu_all)):
                data_bar.append(spu_all[s][0][r])
        y_pos = np.arange(len(spu_all))
        plt.figure()
        plt.bar(y_pos, data_bar)
        plt.xticks(y_pos, name_fish)
        plt.ylabel('WUA []')
        plt.title('Weighted Usable Area for the Reach ' +str(r))
        name = 'WUA_' + name_base

    # many time step - lines
    else:
        data_plot = []
        for r in range(0, len(area_all[0])):
            plt.figure()
            for s in range(0, len(spu_all)):
                data_plot = []
                for t in range(0, len(area_all)):
                    data_plot.append(spu_all[s][t][r], label=name_fish[s])
                plt.plot(data_plot)
            plt.xlabel('Time step [ ]')
            plt.ylabel('WUA []')
            plt.title('Weighted Usable Area for the Reach ' + str(r))



