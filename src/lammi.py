import os
import numpy as np
import matplotlib.pyplot as plt
import time
from collections import OrderedDict
from src_GUI import output_fig_GUI


def load_lammi(facies_path, transect_path, path_im, new_dir='', fig_opt=[], transect_name='Transect.txt',
               facies_name = 'Facies.txt'):
    """
    This function loads the data from the LAMMI model. A description of the LAMMI model is available in the
    documentation folder (LAMMIGuideMetho.pdf).

    :param transect_path: the path to the transect.txt path
    :param facies_path: the path the facies.txt file
    :param path_im: the path where to save the image
    :param fig_opt: the figure option
    :param new_dir: if necessary, the path to the resultat file (.prn file). Be default, use the one in transect.txt
    :param transect_name: the name of the transect file, usually 'Transect.txt'
    :param facies_name: the name of the facies file, usually 'Facies.txt'
    :return:

    ** Technical Comments **

    LAMMI is organised aroung group of transects. Transect are river profile which describe the river geometry.
    In LAMMI, there are four way of grouping transect. The facies is the a group a transect which is considered by HABBY
    to form a reach. The facies can then begroup in station. HABBY do not considered station directly, but it is possible
    to use the function "load_station" to get the station info if needed. The group Secteur are used in case where
    water is brought to the river.

    To load LAMMI data, we first load the facies file, which gives which transect are in which facies. Then, we use
    the transect file to know the length of each transect (length between transects along the river) and the
    name of the file containing the transect precise data. The name of the file is an absolute path to the file.
    This can be annoying if one want to move the files. Hence, we add the variable new_dir which correct the transect
    file in case the files containing the transect data have been moved (they should however all be in the same
    directory). This is done by the function get_transect_name().

    Then it uses the function load_transect_data to read all this data , file by file. Consequentely, we have
    the data in memory but no(x,y) coordinate. In addition, this data is is in the different form than in the other
    hydraulic model.

    To obtain the coordainte of the river and to put the data is the form usually needed by HABBY for 1.5D model
    (coord_pro, vh_pro, nb_pro_reach), we use the coord_lammi() function.


    """
    if not fig_opt:
        fig_opt = output_fig_GUI.create_default_figoption()

    # get the filename of the transect by facies
    [length_all, fac_filename_all] = get_transect_filename(facies_path, facies_name, transect_path, transect_name,
                                                           new_dir)
    if len(length_all) == 1:
        if length_all[0] == -99:
            return

    # load the transect data
    [dist_all, vel_all, height_all, sub_all, q_step] = load_transect_data(fac_filename_all)
    if len(dist_all) == 1:
        if dist_all[0] == -99:
            return

    # get the (not realistic) coordinates of the rivers
    [coord_pro, vh_pro, nb_pro_reach] = coord_lammi(dist_all, vel_all, height_all, sub_all, length_all)

    # create the figure
    fig_lammi(vh_pro, coord_pro, nb_pro_reach, [0,1,2], 0, fig_opt, path_im)


def load_station(station_path, station_name):
    """
    This function loads the station data from the LAMMI model. This is the data contains in Station.txt. It is not used
    by HABBY but it could be useful.

    :param station_path: the path to the station.txt file
    :param transect_path: the path to the transect.txt path
    :param facies_path: the path the facies.txt file
    :param new_dir: if necessary, the path to the resultat file (.prn file). Be default, use the one in transect.txt
    :param station_name: the name of the station file, usually 'Station.txt'
    :param transect_name: the name of the transect file, usually 'Transect.txt'
    :param facies_name: the name of the facies file, usually 'Facies.txt'
    :return: the length of the station (list of float) and the id of the facies for each station (list of list)
    """
    failload = [-99], [-99]

    filestation = os.path.join(station_path, station_name)

    if not os.path.isfile(filestation):
        print('Error: The station file was not found \n')
        return failload

    # load station data
    try:
        with open(filestation, 'rt') as f:
            data_station = f.read()
    except IOError:
        return failload
    data_station = data_station.split('\n')
    if len(data_station) < 1:
        print('Error: No data was found in the station file (1) \n')
        return failload

    # read station data
    lstat = []
    id_fac_all = []
    id_fac = []
    nbfac = 0

    for idx, l in enumerate(data_station):

        # new station
        if 'Longueur de la station' in l:
            # get the facies id from the station before
            if len(lstat) > 0:
                if nbfac == len(id_fac):
                    id_fac_all.append(id_fac)
                    id_fac = []
                else:
                    print('Error: One station was not well-formed in Station.txt (1) \n')
                    return failload
            # get the length of the station
            try:
                lstat_here = float(data_station[idx+1])
            except ValueError or IndexError:
                print('Error: The length of one station could not be found \n')
                return failload
            lstat.append(lstat_here)
            # get the number of facies to check
            if 'Nombre de faci' in data_station[idx+2]:  # avoid the accent :-)
                try:
                    nbfac = float(data_station[idx + 3])
                except ValueError or IndexError:
                    print('Error: The number of facies of one station could not be found \n')
                    return failload
        # read the info from the station loaded before
        if 'Num' in l and 'ro du faci' in l: # avoid accent
            try:
                id_fac_here = float(data_station[idx + 1])
            except ValueError or IndexError:
                print('Error: The number of facies of one station could not be found \n')
                return failload
            id_fac.append(id_fac_here)
    if nbfac == len(id_fac):
        id_fac_all.append(id_fac)
    else:
        print('Error: One station was not well-formed in Station.txt (1) \n')
        return failload

    if len(lstat) == 0:
        print('Error: No data was found in the station file (1) \n')
        return failload

    return id_fac_all, lstat


def get_transect_filename(facies_path, facies_name, transect_path, transect_name, new_dir):
    """
    For each facies, we obtain the name of the transect file and the length of this reach

    :param facies_path: the path the facies.txt file
    :param facies_name: the name of the facies file, usually 'Facies.txt'
    :param transect_path: the path to the transect.txt path
    :param transect_name: the name of the transect file, usually 'Transect.txt'
    :param new_dir: If the folder with the transect have been moved, this argument allos it to be corrected without
           modification to transect.txt
    :return: the length of each transect (arranged by facies and station) and the filename with the transect info
    """

    failload = [-99], [-99]

    # load facies data
    filefacies = os.path.join(facies_path, facies_name)
    if not os.path.isfile(filefacies):
        print('Error: The facies file was not found \n')
        return failload
    try:
        with open(filefacies, 'rt') as f:
            data_facies = f.read()
    except IOError:
        return failload
    data_facies = data_facies.split('\n')
    if len(data_facies) < 1:
        print('Error: No data was found in the facies file (1) \n')
        return failload

    # read facies data
    lfac = []
    facies_id = []
    for idx,n in enumerate(data_facies):
        # new facies
        if 'Longueur du facies' in n:
            try:
                lfac_here = float(data_facies[idx+1].strip())
                first_fac = float(data_facies[idx+5].strip())
                nb_fac = float(data_facies[idx+3].strip())
            except ValueError or IndexError:
                print('Error: the facies file was not in the right format (1) \n')
                return
            lfac.append(lfac_here)
            id_fac = range(int(first_fac), int(nb_fac+first_fac))
            facies_id.append(id_fac)
    if len(lfac) == 0:
        print('Error: the facies faile was not in the right format \n')
        return

    # load transect file name
    filetrans = os.path.join(transect_path, transect_name)
    if not os.path.isfile(filetrans):
        print('Error: The file transect.txt was not found \n')
        return failload
    try:
        with open(filetrans, 'rt') as f:
            data_trans = f.read()
    except IOError:
        return failload
    data_trans = data_trans.split('\n')
    if len(data_trans) < 1:
        print('Error: No data was found in the transect file (1) \n')
        return failload

    # read transect data transect by transect
    ltrans = []
    file_trans = []
    for idx, n in enumerate(data_trans):
        if 'Longueur de re' in n:  # new transect
            # length of transect
            try:
                ltrans_here = float(data_trans[idx+1].strip())
            except ValueError or IndexError:
                print('Error: the transect file was not in the right format \n')
                return failload
            ltrans.append(ltrans_here)
            # name of the file
            file_trans_here = data_trans[idx+3].strip()
            # in case we have moved the transect file
            if new_dir != '':
                basename = os.path.basename(file_trans_here)
                file_trans_here = os.path.join(new_dir, basename)
            if not os.path.isfile(file_trans_here):
                print('Error: A transect file is missing \n')
                return failload
            file_trans.append(file_trans_here)

    # get the data transect by transect
    fac_filename_all = []
    length_all = []
    for f in range(0, len(lfac)):
        # transect file for this facies
        fac_file_name = []
        for fid in facies_id[f]:
            try:
                fac_file_name.append(file_trans[fid-1])
            except IndexError:
                print('Error: The transect was not found \n')
                return failload
        fac_filename_all.append(fac_file_name)
        # length for this facies
        fac_len = []
        for fid in facies_id[f]:
            try:
                fac_len.append(ltrans[fid-1])
            except IndexError:
                print('Error: The transect was not found. \n')
                return failload
        if not sum(fac_len) == lfac[f]:
            print('Warning: the length of a facies is not coherent with the sum of the length of the transcect. \n')
        length_all.append(fac_len)

    return length_all, fac_filename_all


def load_transect_data(fac_filename_all):
    """
    This function loads the transect data. In this data, there are the subtrate, the height and the velocity data.

    :param fac_filename_all: the list of transect name organized by facies

    """
    failload = [-99], [-99], [-99], [-99]

    # get the simulation number (like a time step but depends on Q and not t)
    # This is done based on the first transect file (Q might change afterwards, HABBY does not see it)
    tfile = fac_filename_all[0][0]
    q_step = []
    try:
        with open(tfile, 'rt') as f:
            data_trans = f.read()
    except IOError:
        return failload
    data_trans = data_trans.split('\n')
    if len(data_trans) < 1:
        print('Error: No data was found in the transect file' + tfile + '\n')
        return failload
    for d in data_trans[4:]:
        d = d.strip().split()
        if len(d) == 2:
            try:
                data_q = np.float(d[0])
            except ValueError:
                print('Error: Discharge data not understood')
                return failload
            q_step.append(data_q)

    # preparation of the list based on simulation number and number of facies
    nb_sim = len(q_step)
    nb_fac = len(fac_filename_all)
    if nb_sim == 0:
        print('Error: No Simulation was found in the first transect file. \n')
        return failload
    dist_all = []
    height_all = []
    vel_all = []
    sub_all = []
    for n in range(0, nb_sim):
        dist_all.append([[None for x in range(1)] for y in range(nb_fac)])
        height_all.append([[None for x in range(1)] for y in range(nb_fac)])
        vel_all.append([[None for x in range(1)] for y in range(nb_fac)])
        sub_all.append([[None for x in range(1)] for y in range(nb_fac)])
    distt = []
    ht = []
    vt = []
    subt = []

    # reading the files
    # for each facies
    for fa in range(0, len(fac_filename_all)):
        # for each transect file
        for tfile in fac_filename_all[fa]:

            # load the transect data
            try:
                with open(tfile, 'rt') as f:
                    data_trans = f.read()
            except IOError:
                return failload
            data_trans = data_trans.split('\n')
            if len(data_trans) < 1:
                print('Error: No data was found in the transect file' + tfile + '\n')
                return failload
            t = 0

            # check unity
            unl = data_trans[4]
            unl = unl.split()
            if 'm' not in unl or 'm/s' not in unl:
                print('Warning: unity of the transect data not recongnized. \n')

            # read the transect file
            for idx, d in enumerate(data_trans[5:]):

                # for each new time step
                d = d.strip().split()
                if len(d) == 2:
                    if idx > 1:
                        if dist_all[t][fa][0] is not None:
                            dist_all[t][fa].append(distt)
                            height_all[t][fa].append(ht)
                            vel_all[t][fa].append(vt)
                            sub_all[t][fa].append(subt)
                        else:
                            dist_all[t][fa] = [distt]
                            height_all[t][fa] = [ht]
                            vel_all[t][fa] = [vt]
                            sub_all[t][fa] = [subt]
                        t += 1
                    distt = []
                    ht = []
                    vt = []
                    subt = []

                # data line
                if len(d) == 11:
                    # get substrate data
                    try:
                        sub_here = list(map(float, d[:8]))
                    except ValueError:
                        print('Error: Substrate data is not understood (1) \n')
                        return failload
                    if sum(sub_here) != 100:
                        print('Warning: one subtrate point is not coherent in file' + tfile + '\n')
                    subt.append(sub_here)
                    # get height, dist and vecloity data
                    try:
                        # get height data
                        ht.append(float(d[8]))
                        # get velocity
                        vt.append(float(d[9]))
                        # get dist data
                        distt.append(float(d[10]))
                    except ValueError:
                        print('Error: Substrate data is not understood (2) \n')
                        return failload

            # last time step
            if dist_all[t][fa][0] is not None:
                dist_all[t][fa].append(distt)
                height_all[t][fa].append(ht)
                vel_all[t][fa].append(vt)
                sub_all[t][fa].append(subt)
            else:
                dist_all[t][fa] = [distt]
                height_all[t][fa] = [ht]
                vel_all[t][fa] = [vt]
                sub_all[t][fa] = [subt]

    return dist_all, vel_all, height_all, sub_all, q_step


def coord_lammi(dist_all, vel_all, height_all, sub_all, length_all):
    """
    This function takes the data from the lammi outputs and get the coordinate for the river. It also
    reform the data to put it in the needed for HABBY (as the other 1.5D hydraulic model as hec_ras).

    To get the coordinates, we assume that the river is straight, that each facies is one after the other and
    that the river passes by the deepest point of the profile. In addition we assume that the profile are straight
    and perpendicular to the river.

    We loop through all the profiles for all reach all time steps. For each profile, the x coordinate is identical
    for all point of the profile and is calculated using length_all. When a new reach starts, a meter is added to the x
    coordinate. To find the y coordainte, we first pass from cell data (in lammi) to point data. The poitn are in the
    center of the cell. In addtion, one point is added at the start an end of the profile with a water heigth of zero.
    Then, we find the height water height and we assume that the passes there. There is the zeros y-ccordinates.

    :param dist_all: the distance along profile by reach (or facies) and by time step
    :param vel_all: the velocity along profile by reach (or facies) and by time step
    :param height_all: the height along profile by reach (or facies) and by time step
    :param sub_all: the substrate data along profile by reach (or facies) and by time step. Eacu subtrate data is a list
           of eight number representing the percentage of each of the eight subtrate class.
    :param length_all: the distance between profile
    :return: coord_pro, nb_pro_reach and vh_pro in the same form as in hec-ras (final form)
    """

    coord_pro = []
    nb_pro_reach = [0]
    vh_pro = []
    sub_pro = []
    x = 0
    t = 0

    # for each "time" step
    for ti in range(0, len(dist_all)):
        dist_allt = dist_all[ti]
        vel_allt = vel_all[ti]
        height_allt = height_all[ti]
        sub_allt = sub_all[ti]

        coord_prot = []
        vh_prot = []
        t+=1
        f = 0

        # facies/reach
        for fi in range(0, len(dist_allt)):
            f +=1
            dist_allf = dist_allt[fi]
            vel_allf = vel_allt[fi]
            height_allf = height_allt[fi]
            sub_allf = sub_allt[fi]

            # profile
            for pi in range(0, len(dist_allf)):
                dist_allp = dist_allf[pi]
                vel_allp = vel_allf[pi]
                height_allp = height_allf[pi]
                sub_allp = sub_allf[pi]
                rivind = np.argmax(np.array(height_allp))
                dist_here = 0

                # point
                dist_allp_new = [0]
                for di in range(0, len(dist_allp)):
                    # new dist_all at the center of the cell
                    if di == 0:
                        dist_here += dist_allp[di]/2
                    else:
                        dist_here += dist_allp[di-1]/2 + dist_allp[di]/2
                    dist_allp_new.append(dist_here)
                    if di == len(dist_allp)-1:
                        dist_here += dist_allp[di]/2
                        dist_allp_new.append(dist_here)

                # x, y coordinate (0 at the middle of the river for y)
                ypro = [i - dist_allp_new[rivind + 1] for i in dist_allp_new]
                x += length_all[fi][pi]
                xpro = [x] * len(dist_allp_new)
                # data
                vel_allp = [0] + vel_allp + [0]
                height_allp = [0] + height_allp + [0]

                # data for the profile
                vh_prop = [dist_allp_new, height_allp, vel_allp]
                coord_pro_p = [xpro, ypro, dist_allp_new, height_allp]
                coord_prot.append(coord_pro_p)
                vh_prot.append(vh_prop)

            if ti == 0:
                nb_pro_reach.append(nb_pro_reach[-1] + len(dist_allf))
            x += 1  # reach is separated by 1m along the river

        coord_pro.append(coord_prot)
        vh_pro.append(vh_prot)

    return coord_pro, vh_pro, nb_pro_reach


def fig_lammi(vh_pro, coord_pro, nb_pro_reach, pro_num, sim_num, fig_opt, path_im):
    """
    This function create a figure with the loaded lammi data.
    It work only for one time steps gven by the number sim_num.

    :param vh_pro: dist along the profile, height, vel
    :param coord_pro: x,y, dist along profile, height
    :param nb_pro_reach: the number of profile by reach
    :param pro_num: the profile to plot
    :param sim_num: the time step (or simuation) to plot
    :param fig_opt: the option for the figure
    :param path_im: path path where to save the figure
    """

    plt.rcParams['figure.figsize'] = fig_opt['width'], fig_opt['height']
    plt.rcParams['font.size'] = fig_opt['font_size']
    plt.rcParams['lines.linewidth'] = fig_opt['line_width']
    format = int(fig_opt['format'])
    plt.rcParams['axes.grid'] = fig_opt['grid']

    # time step
    coord_pro = coord_pro[sim_num]
    vh_pro = vh_pro[sim_num]

    # get the profile data
    for id,i in enumerate(pro_num):
        dist = coord_pro[i][2]
        vel = vh_pro[i][2]
        vel[0] = vel[1]
        vel[-1] = vel[-2]
        h = np.array(vh_pro[i][1])
        fig = plt.figure(id)
        plt.suptitle("")
        ax1 = plt.subplot(313)
        # print velocity
        plt.step(dist, vel,  where='mid', color='r')
        plt.xlim([dist[0] - 1 * 0.95, np.max(dist) * 1.05])
        plt.xlabel("distance along the profile [m]")
        plt.ylabel(" Velocity [m/sec]")
        # print water height
        ax1 = plt.subplot(211)
        plt.plot(dist, -h, 'k')  # profile
        plt.fill_between(dist, -h, [0]*len(h), where=h>=[0]*len(h), facecolor='blue', alpha=0.5, interpolate=True)
        plt.xlabel("distance along the profile [m]")
        plt.ylabel("altitude of the profile [m]")
        plt.title("Profile " + str(i))
        plt.legend(("Profile", "Water surface"))
        plt.xlim([dist[0] - 1 * 0.95, np.max(dist) * 1.05])
        plt.ylim([np.min(-h) * 1.05, np.max(h)/3])
        # save
        # if format == 0 or format == 1:
        #     plt.savefig(os.path.join(path_im, "HEC_profile_" + str(i) + '_day' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
        #                          '.png'), dpi=fig_opt['resolution'])
        # if format == 0 or format == 3:
        #     plt.savefig(os.path.join(path_im, "HEC_profile_" + str(i) + '_day' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
        #                          '.pdf'), dpi=fig_opt['resolution'])
        # if format == 2:
        #     plt.savefig(os.path.join(path_im, "HEC_profile_" + str(i) + '_day' + time.strftime("%d_%m_%Y_at_%H_%M_%S") +
        #                          '.jpg'), dpi=fig_opt['resolution'])

    # get an (x,y) view of the progile position
    fig2 = plt.figure(len(pro_num))
    color_all = ['-xb', '-xg', '-xr', '-xc', '-xm', '-xy', '-xk']
    col = color_all[0]
    c = 0
    nb_fac = -1
    for j in range(0, len(coord_pro)):
        if j in nb_pro_reach:
            nb_fac +=1
            col = color_all[c]
            if c == len(color_all)-1:
                c = 0
            else:
                c +=1
        plt.plot(coord_pro[j][0], coord_pro[j][1],  col, label="Facies " + str(nb_fac +1), markersize=3)  # profile
    plt.xlabel("x coord []")
    plt.ylabel("y coord []")
    plt.title("Position of the profiles (conceptual only)")
    #plt.axis('equal')  # if right angle are needed
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = OrderedDict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys(),bbox_to_anchor=(1.1, 1), prop={'size': 10})
    # if format == 0 or format == 1:
    #     plt.savefig(os.path.join(path_im, "HEC_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".png"),
    #             dpi=fig_opt['resolution'])
    # if format == 0 or format == 3:
    #     plt.savefig(os.path.join(path_im, "HEC_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".pdf"),
    #             dpi=fig_opt['resolution'])
    # if format == 2:
    #     plt.savefig(os.path.join(path_im, "HEC_all_pro_" + time.strftime("%d_%m_%Y_at_%H_%M_%S") + ".jpg"),
    #             dpi=fig_opt['resolution'])


    plt.show()


def main():
    """
    Used to test this module
    """

    # path where the station.txt, transect.txt, secteur.txt
    path = r'D:\Diane_work\output_hydro\LAMMI\ExempleDianeYann\Entree'
    new_dir = r'D:\Diane_work\output_hydro\LAMMI\ExempleDianeYann\Resu\SimHydro'
    path_im = '.'
    load_lammi(path, path, path_im, new_dir)


if __name__ == '__main__':
    main()