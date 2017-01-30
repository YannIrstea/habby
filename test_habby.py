import matplotlib.pyplot as plt
from src import Hec_ras06
from src import rubar
from src import mascaret
from src import manage_grid_8
from src import dist_vistess2
from src import load_hdf5
import os
import time
import colorama
from colorama import Fore

def main():
    """
    the function of this file is to test the grid creating in HABBY
    the idea is to develop it further to test habby in full.
    For hec_ras careful, some output are in feet or feet/sec!!! in can be corrected in hec-ras,
    but you need to change manning value also
    """
    # option pour le test
    which_mod = [True, True, True, True]  # change to False to not test a model type
    max_timestep = 10
    path_im = r"D:\Diane_work\version\file_test\fig_test"
    interp_method = 0 # can be 0 (by block),1 (interpolation linear), 2 interpolation cut gr
    colorama.init()  # for fun color on the cmd
    pro_add = 5

    # test to load and create grid hec-ras v4
    if which_mod[0]:
        dirwithtest = r"D:\Diane_work\version\file_test\hecrasv4"
        output_name = load_hdf5.get_all_filename(dirwithtest, '.xml')
        geo_name1 = load_hdf5.get_all_filename(dirwithtest, '.g01')
        geo_name2 = load_hdf5.get_all_filename(dirwithtest, '.g02')
        geo_name3 = load_hdf5.get_all_filename(dirwithtest, '.g03')
        geo_name4 = load_hdf5.get_all_filename(dirwithtest, '.g04')
        geo_name = geo_name1 + geo_name2 + geo_name3 + geo_name4
        # necassary because of the different ending
        geo_name.sort()
        output_name.sort()

        for i in range(0,len(output_name)):
            print(Fore.GREEN + 'Will be tested: ' + geo_name[i])
            print(Fore.WHITE)
            a =time.time()
            # load data
            [coord_pro, vh_pro, nb_pro_reach] = Hec_ras06.open_hecras(geo_name[i], output_name[i],dirwithtest, dirwithtest,path_im, False)
            for t in range(0, min(max_timestep, len(vh_pro))):
                # create grid
                if interp_method == 0:
                    [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                        manage_grid_8.create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro[t])
                elif interp_method == 1:
                    [point_all_reach, ikle_all, lim_by_reach, hole_all_i, overlap, coord_pro2, point_c_all] = \
                        manage_grid_8.create_grid(coord_pro, pro_add,[],[], nb_pro_reach, vh_pro[t])
                    [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_all_reach, coord_pro2,vh_pro[t])

                # do figure
                manage_grid_8.plot_grid_simple(point_all_reach, ikle_all, inter_vel_all, inter_height_all, path_im)
            b = time.time()
            print('The following test was done: ' + geo_name[i])
            print( 'Time spend: ' + str((b - a)/(t+1)) + 'sec for' + str(len(ikle_all[0])) + ' cells\n')
    plt.show()

    # test to load and create grid hec-ras v5
    if which_mod[1]:
        dirwithtest = r"D:\Diane_work\version\file_test\hecrasv5"
        output_name1 = load_hdf5.get_all_filename(dirwithtest, '.sdf')
        output_name2 = load_hdf5.get_all_filename(dirwithtest, '.rep')
        output_name = output_name1 + output_name2
        geo_name1 = load_hdf5.get_all_filename(dirwithtest, '.g01')
        geo_name2 = load_hdf5.get_all_filename(dirwithtest, '.g02')
        geo_name3 = load_hdf5.get_all_filename(dirwithtest, '.g03')
        geo_name = geo_name1 + geo_name2 + geo_name3
        # necassary because of the different ending
        geo_name.sort()
        output_name.sort()

        for i in range(0, len(output_name)):
            print(Fore.GREEN + 'Will be tested: ' + geo_name[i])
            print(Fore.WHITE)
            a = time.time()
            [coord_pro, vh_pro, nb_pro_reach] = Hec_ras06.open_hecras(geo_name[i], output_name[i], dirwithtest,
                                                                      dirwithtest, path_im, False)
            b = time.time()
            print('Time spend to load data all time step: ' + str(b - a) + 'sec\n')
            for t in range(0, min(max_timestep, len(vh_pro))):
                # create grid
                a = time.time()
                if interp_method == 0:
                    [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                        manage_grid_8.create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro[t])
                elif interp_method == 1:
                    [point_all_reach, ikle_all, lim_by_reach, hole_all_i, overlap, coord_pro2, point_c_all] = \
                        manage_grid_8.create_grid(coord_pro, pro_add, [], [], nb_pro_reach, vh_pro[t])
                    [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_all_reach, coord_pro2,
                                                                                     vh_pro[t])
                manage_grid_8.plot_grid_simple(point_all_reach, ikle_all, inter_vel_all, inter_height_all, path_im)
                print('Time step: ' + str(t))
                if t % 30 == 0:
                    plt.show()
                b = time.time()
                print('Time spend per time step: ' + str((b - a)) + 'sec for ' + str(len(ikle_all[0])) + ' cells\n')
            print('The following test was done: ' + geo_name[i] + '\n')

    plt.show()

    # test to load and create grid mascaret
    if which_mod[2]:
        dirwithtest = r"D:\Diane_work\version\file_test\mascaret"
        output_name = load_hdf5.get_all_filename(dirwithtest, '.opt')
        geo_name = load_hdf5.get_all_filename(dirwithtest, '.geo')
        gen_name1 = load_hdf5.get_all_filename(dirwithtest, '.xcas')
        gen_name2 = load_hdf5.get_all_filename(dirwithtest, '.cas')
        gen_name = gen_name1 + gen_name2
        geo_name.sort()
        output_name.sort()
        gen_name.sort()
        manning = 0.025
        np_point_vel = 50

        for i in range(0, len(output_name)):
            print(Fore.GREEN + 'Will be tested: ' + geo_name[i])
            print(Fore.WHITE)
            a = time.time()
            # load data
            [coord_pro, coord_r, xhzv_data, name_pro, name_reach, on_profile, nb_pro_reach] \
                = mascaret.load_mascaret(gen_name[i], geo_name[i], output_name[i], dirwithtest, \
                                         dirwithtest, dirwithtest)
            # distribute velcoity
            manning_array = dist_vistess2.get_manning(manning, np_point_vel, len(coord_pro), coord_pro)
            vh_pro = dist_vistess2.dist_velocity_hecras(coord_pro, xhzv_data, manning_array, np_point_vel, 1,on_profile)
            # create grid
            for t in range(0, min(max_timestep, len(vh_pro))):
                if interp_method == 0:
                    [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                        manage_grid_8.create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro[t])
                elif interp_method == 1:
                    [point_all_reach, ikle_all, lim_by_reach, hole_all_i, overlap, coord_pro2, point_c_all] = \
                        manage_grid_8.create_grid(coord_pro, pro_add, [], [], nb_pro_reach, vh_pro[t])
                    [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_all_reach, coord_pro2,
                                                                                     vh_pro[t])
                manage_grid_8.plot_grid_simple(point_all_reach, ikle_all, inter_vel_all, inter_height_all, path_im)
            b = time.time()
            print('The following test was done: ' + geo_name[i] + '\n')
            print('Time spend per time step: ' + str((b - a)/(t+1)) + 'sec for ' + str(len(ikle_all[0])) + ' cells\n')
    plt.show()

    # test to load and create grid rubar
    if which_mod[3]:
        dirwithtest = r"D:\Diane_work\version\file_test\rubar"
        geo_name = load_hdf5.get_all_filename(dirwithtest, '.rbe')
        output_name = []
        for file in os.listdir(dirwithtest):
            if file.startswith('profil'):
                output_name.append(file)
        manning = 0.025
        np_point_vel = 50

        for i in range(0, len(output_name)):
            print(Fore.GREEN + 'Will be tested: ' + geo_name[i])
            print(Fore.WHITE)
            a = time.time()
            # load data
            [xhzv_data, coord_pro, lim_riv] = rubar.load_rubar1d(geo_name[i], output_name[i], dirwithtest, dirwithtest,
                                                                 path_im, False)
            nb_pro_reach = [0, len(coord_pro)]
            # distribute velcoity
            manning_array = dist_vistess2.get_manning(manning, np_point_vel, len(coord_pro), coord_pro)
            vh_pro = dist_vistess2.dist_velocity_hecras(coord_pro, xhzv_data, manning_array, np_point_vel, 1)
            if interp_method == 2:
                [point_whole, ikle_whole, lim_by_reach, hole_all_i, overlap, blob, point_c_all] = \
                    manage_grid_8.create_grid(coord_pro, pro_add, [], [], nb_pro_reach,vh_pro[0])
            # create grid
            for t in range(0, min(max_timestep, len(vh_pro))):
                if interp_method == 0:
                    [ikle_all, point_all_reach, point_c_all, inter_vel_all, inter_height_all] = \
                        manage_grid_8.create_grid_only_1_profile(coord_pro, nb_pro_reach, vh_pro[t])
                elif interp_method == 1:
                    [point_all_reach, ikle_all, lim_by_reach, hole_all_i, overlap, coord_pro2, point_c_all] = \
                        manage_grid_8.create_grid(coord_pro, pro_add, [], [], nb_pro_reach, vh_pro[t])
                    [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_all_reach, coord_pro2,
                                                                                     vh_pro[t])
                elif interp_method == 2: # just a random test
                    coord_pro2 = manage_grid_8.update_coord_pro_with_vh_pro(coord_pro, vh_pro[t])
                    [inter_vel_all, inter_height_all] = manage_grid_8.interpo_linear(point_whole, coord_pro2,vh_pro[t])
                    [ikle_all, point_all_reach, inter_height_all, inter_vel_all] = manage_grid_8.cut_2d_grid_all_reach(
                        ikle_whole, point_whole, inter_height_all, inter_vel_all)
                manage_grid_8.plot_grid_simple(point_all_reach, ikle_all, inter_vel_all, inter_height_all, path_im)
            plt.show()
            b = time.time()
            print('The following test was done: ' + geo_name[i] + '\n')
            print('Time spend per time step: ' + str((b - a)/(t+1)) + 'sec for ' + str(len(ikle_all[0])) + ' cells\n')

    plt.show()


if __name__ == '__main__':
    main()